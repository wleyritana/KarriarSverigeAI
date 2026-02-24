def apply_hard_gate_caps(score, hard_gate_status):
    try:
        score = int(score)
    except:
        return score
    if hard_gate_status == "fail":
        return min(score, 25)
    if hard_gate_status == "risk":
        return min(score, 45)
    return score

import json

def compute_hard_gate_status(hard_gates_output):
    """Derive hard gate status from LLM JSON output.
    Returns: 'clear' | 'risk' | 'fail'
    """
    if hard_gates_output is None:
        return "clear"
    data = None
    if isinstance(hard_gates_output, dict):
        data = hard_gates_output
    else:
        s = str(hard_gates_output)
        try:
            data = json.loads(s)
        except Exception:
            # Fallback heuristic if output isn't valid JSON
            if '"cv_evidence_status": "missing"' in s or '"cv_evidence_status":"missing"' in s:
                return "fail"
            if '"cv_evidence_status": "unclear"' in s or '"cv_evidence_status":"unclear"' in s:
                return "risk"
            return "clear"

    gates = data.get("hard_gates") or []
    status = "clear"
    for g in gates:
        sev = (g.get("severity") or "").lower()
        ev = (g.get("cv_evidence_status") or "").lower()
        # Only hard gates drive fail/risk
        if sev == "hard_gate":
            if ev == "missing":
                return "fail"
            if ev == "unclear":
                status = "risk"
    return status

import os, re
from io import BytesIO
from flask import Flask, render_template, request, session, send_file
from job_fetcher import fetch_job_from_url, fetch_job_preview
from dotenv import load_dotenv
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from translations import translations
from agents import *
from report_generator import build_report
from pdf_report import build_pdf_report

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY","dev")

limiter = Limiter(get_remote_address, app=app, storage_uri="memory://")

def parse_json_with_repair(raw: str) -> dict:
    """Parse JSON from LLM. If invalid, try a lightweight repair prompt via regex heuristics.
    We avoid an extra LLM call here for stability/cost; fallback to empty dict.
    """
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return raw
    s = str(raw).strip()
    try:
        return json.loads(s)
    except Exception:
        # Common issue: trailing text. Try to extract first {...} block.
        m = re.search(r"\{.*\}", s, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                return {}
        return {}

def compute_penalties(match_data: dict) -> tuple[int, dict]:
    """Return (total_penalty, breakdown dict)."""
    critical = match_data.get("critical_gaps") or []
    moderate = match_data.get("moderate_gaps") or []
    minor = match_data.get("minor_gaps") or []

    # Weights (tunable)
    crit_pen = 15 * len(critical)
    mod_pen = 7 * len(moderate)
    min_pen = 3 * len(minor)

    evq = (match_data.get("evidence_quality") or "medium").lower()
    tl = (match_data.get("timeline_risk") or "low").lower()

    ev_pen = 0 if evq == "strong" else (5 if evq == "medium" else 10)
    tl_pen = 0 if tl == "low" else (5 if tl == "medium" else 10)

    total = crit_pen + mod_pen + min_pen + ev_pen + tl_pen
    # keep within reasonable bounds
    total = max(0, min(total, 90))

    return total, {
        "critical_gaps": len(critical),
        "moderate_gaps": len(moderate),
        "minor_gaps": len(minor),
        "critical_penalty": crit_pen,
        "moderate_penalty": mod_pen,
        "minor_penalty": min_pen,
        "evidence_quality": evq,
        "evidence_penalty": ev_pen,
        "timeline_risk": tl,
        "timeline_penalty": tl_pen,
        "total_penalty": total,
    }

def compute_hireability_from_match(match_score: int, match_data: dict, hard_gate_status: str) -> tuple[int, str]:
    """Hireability = Match - penalties, then apply hard-gate caps."""
    penalties, breakdown = compute_penalties(match_data)
    raw = max(0, min(100, int(match_score) - penalties))

    capped = raw
    cap_note = ""
    if hard_gate_status == "fail":
        capped = min(capped, 25)
        cap_note = "Hard gate status = FAIL → hireability capped at 25."
    elif hard_gate_status == "risk":
        capped = min(capped, 45)
        cap_note = "Hard gate status = RISK → hireability capped at 45."

    explanation = []
    explanation.append(f"Hireability model: Hireability = Match ({match_score}) − Penalties ({breakdown['total_penalty']}) = {raw}.")
    explanation.append(f"Penalty breakdown: critical({breakdown['critical_gaps']}×15)={breakdown['critical_penalty']}, moderate({breakdown['moderate_gaps']}×7)={breakdown['moderate_penalty']}, minor({breakdown['minor_gaps']}×3)={breakdown['minor_penalty']}, evidence({breakdown['evidence_quality']})={breakdown['evidence_penalty']}, timeline({breakdown['timeline_risk']})={breakdown['timeline_penalty']}.")
    if cap_note:
        explanation.append(cap_note)
    return capped, "\n".join(explanation)




def extract_score(text: str, kind: str = "generic") -> int:
    """Extract a 0-100 score from model text robustly.
    Avoids picking up years (e.g., 2024) by preferring labeled patterns.
    kind: 'match' | 'hire' | 'generic'
    """
    if not text:
        return 60

    t = str(text)

    # Label patterns by kind (Swedish + English)
    if kind == "match":
        labels = [
            r"Matchningspoäng",
            r"Matching\s*score",
            r"Match\s*score",
            r"Score\s*for\s*the\s*role",
        ]
    elif kind == "hire":
        labels = [
            r"Anställningsbarhets?poäng",
            r"Hireability\s*score",
            r"Employability\s*score",
        ]
    else:
        labels = [r"Score"]

    # 1) Labeled "X/100"
    for lab in labels:
        m = re.search(rf"{lab}[^\d]{{0,20}}(\d{{1,3}})\s*/\s*100", t, re.IGNORECASE)
        if m:
            return max(0, min(int(m.group(1)), 100))

    # 2) Labeled "X%"
    for lab in labels:
        m = re.search(rf"{lab}[^\d]{{0,20}}(\d{{1,3}})\s*%", t, re.IGNORECASE)
        if m:
            return max(0, min(int(m.group(1)), 100))

    # 3) Any "X/100" (unlabeled)
    m = re.search(r"(\d{1,3})\s*/\s*100", t)
    if m:
        return max(0, min(int(m.group(1)), 100))

    # 4) Any "X%" (unlabeled)
    m = re.search(r"(\d{1,3})\s*%", t)
    if m:
        return max(0, min(int(m.group(1)), 100))

    # 5) Fallback: choose first plausible 0-100 number, skipping years (1900-2099)
    nums = [int(x) for x in re.findall(r"\b\d{1,4}\b", t)]
    for n in nums:
        if 0 <= n <= 100:
            return n
        if 1900 <= n <= 2099:
            continue

    return 60

def score_color(score):
    if score < 70:
        return "red"
    elif score < 85:
        return "amber"
    return "green"

@app.route("/")
def home():
    lang = session.get("lang","sv")
    t = translations.get(lang, translations["sv"])
    return render_template("index.html", t=t, lang=lang)

@app.route("/run", methods=["POST"])
@limiter.limit("3/hour")
def run():
    lang = request.form.get("lang","sv")
    session["lang"] = lang
    t = translations.get(lang, translations["sv"])

    cv = request.form["cv"]
    job_url = request.form["job_url"]
    job_text_fallback = request.form.get("job_text_fallback", "")

    try:
        job = fetch_job_from_url(job_url)
        fetch_meta = None
    except Exception as e:
        # Best-effort preview for debugging / user feedback
        preview = None
        try:
            preview = fetch_job_preview(job_url)
        except Exception:
            preview = None

        # If user provided manual job text fallback, proceed with that
        if job_text_fallback and job_text_fallback.strip():
            job = job_text_fallback.strip()
            fetch_meta = preview
        else:
            # Render the form again with a friendly error and preview snippet
            return render_template(
                "index.html",
                t=t,
                lang=lang,
                error=str(e),
                job_url=job_url,
                preview=preview
            )

    role = request.form.get("role")
    company = request.form.get("company")
    culture = request.form.get("culture")
    reviews = request.form.get("reviews")    

    # Hard gates (eligibility / knockout requirements) — LLM extracts from JOB and checks CV evidence
    hard_gate_status = "clear"
    hard_gates_json = None
    hard_gates = []

    try:
        hard_gates_json = hard_gate_extract(cv, job, role, lang)
    except Exception:
        hard_gates_json = None

    try:
        hard_data = json.loads(hard_gates_json) if isinstance(hard_gates_json, str) else (hard_gates_json or {})
        hard_gates = hard_data.get("hard_gates") or []
    except Exception:
        hard_gates = []

    hard_gate_status = compute_hard_gate_status(hard_gates)
    match = recruiter_match(cv, job, role, lang, hard_gates_json)
    optimized = optimize_cv(cv, match, lang)
    ats = ats_audit(optimized, job, role, lang, hard_gates_json)
    ats_cv = ats_submission(optimized, job, role, lang, hard_gates_json)
    interview = interview_pack(optimized, job, role, lang)
    deep = requirement_intelligence(cv, job, role, lang)
    hire = None  # computed deterministically from match + gaps + hard gates
    psyche = recruiter_psychology(cv, job, role, lang)
    culture_report = culture_analysis(company, culture, reviews, lang)

    


    # Parse recruiter match JSON (strict) and compute scores
    match_data = parse_json_with_repair(match)
    match_display = match
    try:
        match_display = json.dumps(match_data, indent=2, ensure_ascii=False)
    except Exception:
        match_display = match
    match_score = match_data.get("match_score")
    if match_score is None:
        match_score = extract_score(match, kind="match")
    try:
        match_score = int(match_score)
    except Exception:
        match_score = extract_score(match, kind="match")

    # Apply hard-gate caps to match score (realistic screening)
    match_score = apply_hard_gate_caps(match_score, hard_gate_status)

    # Compute hireability from match + gaps + hard gates (job-specific offer likelihood)
    hire_score, hire_expl = compute_hireability_from_match(match_score, match_data, hard_gate_status)
    hire = hire_expl

    session["hire_score"] = hire_score
    session["match_score"] = match_score

    return render_template("dashboard.html",
        hard_gate_status=hard_gate_status,

        hard_gates=hard_gates_json,
        hard_gates_eval=hard_gates,


        t=t,
        hire_score=hire_score,
        match_score=match_score,
        hire_color=score_color(hire_score),
        match_color=score_color(match_score),
        match=match_display,
        optimized=optimized,
        ats=ats,
        ats_cv=ats_cv,
        interview=interview,
        deep=deep,
        hire=hire,
        psyche=psyche,
        culture_report=culture_report
    )

@app.route("/health")
def health():
    return {"status":"ok"}

@app.route("/download_pdf")
def download_pdf():
    from flask import session, send_file
    report_data = {
        "Hireability Score": str(session.get("hire_score", "")),
        "Match Score": str(session.get("match_score", "")),
    }
    pdf = build_pdf_report(report_data)
    return send_file(pdf,
        as_attachment=True,
        download_name="AI_Job_Hunt_Executive_Report.pdf",
        mimetype="application/pdf")

from flask import redirect, url_for

ACCESS_PASSWORD = os.getenv("ACCESS_PASSWORD", "1234")

@app.before_request
def require_login():
    allowed_paths = ["/login", "/health", "/static"]
    if request.path.startswith("/static"):
        return
    if request.path not in allowed_paths and not session.get("authenticated"):
        return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        if request.form.get("password") == ACCESS_PASSWORD:
            session["authenticated"] = True
            return redirect(url_for("home"))
        else:
            error = "Incorrect password"
    return render_template("login.html", error=error)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

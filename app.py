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
from openai_client import llm

def compute_hard_gate_status(hard_gates_output) -> str:
    """Compute hard-gate status from LLM output.

    Accepts:
      - list of gate dicts
      - dict with key 'hard_gates'
      - raw JSON string
      - None

    Returns: 'clear' | 'risk' | 'fail'
    """
    if hard_gates_output is None:
        return "clear"

    # Normalize to list[dict]
    gates = []
    if isinstance(hard_gates_output, list):
        gates = hard_gates_output
    elif isinstance(hard_gates_output, dict):
        gates = hard_gates_output.get("hard_gates") or []
    else:
        s = str(hard_gates_output)
        try:
            data = json.loads(s)
            if isinstance(data, list):
                gates = data
            elif isinstance(data, dict):
                gates = data.get("hard_gates") or []
        except Exception:
            # Heuristic fallback
            if '"cv_evidence_status": "missing"' in s or '"cv_evidence_status":"missing"' in s:
                return "fail"
            if '"cv_evidence_status": "unclear"' in s or '"cv_evidence_status":"unclear"' in s:
                return "risk"
            return "clear"

    status = "clear"
    for g in gates:
        if not isinstance(g, dict):
            continue
        sev = (g.get("severity") or "").lower()
        ev = (g.get("cv_evidence_status") or "").lower()
        if sev == "hard_gate":
            if ev == "missing":
                return "fail"
            if ev == "unclear":
                status = "risk"
    return status

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
    return capped, "\n".join(explanation), breakdown




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


    def build_hireability_sections(match_score: int, hire_score: int, match_data: dict, hard_gate_status: str, penalties_breakdown: dict) -> str:
        """Deterministic narrative base (Section A + Section B)."""
        crit = penalties_breakdown.get("critical_gaps", 0)
        mod = penalties_breakdown.get("moderate_gaps", 0)
        minor = penalties_breakdown.get("minor_gaps", 0)
        evq = penalties_breakdown.get("evidence_quality", "medium")
        tlr = penalties_breakdown.get("timeline_risk", "low")
        total_pen = penalties_breakdown.get("total_penalty", 0)

        if hire_score >= 75:
            summary_line = "Overall likelihood of progressing is strong."
        elif hire_score >= 50:
            summary_line = "Overall likelihood of progressing is moderate."
        elif hire_score >= 30:
            summary_line = "Overall likelihood of progressing is limited due to significant gaps."
        else:
            summary_line = "Overall likelihood of progressing is low due to major misalignment or blockers."

        hard_gate_note = ""
        if hard_gate_status == "fail":
            hard_gate_note = "Eligibility hard gate status is FAIL. This will typically stop the application from progressing regardless of fit."
        elif hard_gate_status == "risk":
            hard_gate_note = "Eligibility hard gate status is RISK (unclear). This can materially reduce the chance of progressing until clarified."

        critical_list = match_data.get("critical_gaps") or []
        moderate_list = match_data.get("moderate_gaps") or []
        minor_list = match_data.get("minor_gaps") or []
        blockers = match_data.get("blockers") or []

        def bullets(items, maxn=4):
            items = [str(x).strip() for x in items if str(x).strip()]
            return "\n".join([f"- {x}" for x in items[:maxn]]) if items else "- None identified"

        section_a = []
        section_a.append("Section A: Executive Summary (Narrative)")
        section_a.append("")
        section_a.append(f"The Recruiter Match Score for this role is {match_score}/100, indicating alignment between the job requirements and the CV evidence.")
        section_a.append(f"The Hireability Score for this role is {hire_score}/100.")
        section_a.append("")
        section_a.append(f"Key drivers: {crit} critical gap(s), {mod} moderate gap(s), and {minor} minor issue(s). Evidence quality is {evq} and timeline risk is {tlr}.")
        if blockers:
            section_a.append("Notable blockers identified by the recruiter assessment:")
            section_a.append(bullets(blockers, 4))
        if hard_gate_note:
            section_a.append("")
            section_a.append(hard_gate_note)
        section_a.append("")
        section_a.append(summary_line)

        section_b = []
        section_b.append("Section B: Scoring Breakdown (Technical)")
        section_b.append("")
        section_b.append(f"Base fit (Recruiter Match): {match_score}/100")
        section_b.append(f"Total penalties applied: {total_pen}")
        section_b.append("")
        section_b.append("Penalty breakdown:")
        section_b.append(f"- Critical gaps: {crit} × 15 = {penalties_breakdown.get('critical_penalty', 0)}")
        section_b.append(f"- Moderate gaps: {mod} × 7 = {penalties_breakdown.get('moderate_penalty', 0)}")
        section_b.append(f"- Minor issues: {minor} × 3 = {penalties_breakdown.get('minor_penalty', 0)}")
        section_b.append(f"- Evidence quality ({evq}): {penalties_breakdown.get('evidence_penalty', 0)}")
        section_b.append(f"- Timeline risk ({tlr}): {penalties_breakdown.get('timeline_penalty', 0)}")
        section_b.append("")
        section_b.append(f"Hireability = Match ({match_score}) − Penalties ({total_pen}) (then hard-gate caps if applicable).")

        section_b.append("")
        section_b.append("Critical gaps:")
        section_b.append(bullets(critical_list, 6))
        section_b.append("")
        section_b.append("Moderate gaps:")
        section_b.append(bullets(moderate_list, 6))
        section_b.append("")
        section_b.append("Minor issues:")
        section_b.append(bullets(minor_list, 6))

        return "\n".join(section_a + ["", ""] + section_b)

    def _numbers_in_text(s: str) -> set[str]:
        return set(re.findall(r"\b\d{1,3}\b", s or ""))

    def validate_rewriter_output(output_text: str, allowed_numbers: set[str]) -> bool:
        if not output_text:
            return False
        if "Section A:" not in output_text or "Section B:" not in output_text:
            return False
        found = _numbers_in_text(output_text)
        return found.issubset(allowed_numbers)

    def polish_narrative_with_llm(structured: dict, draft_text: str, lang: str) -> str | None:
        system = (
            "You are a scoring explanation rewriter. "
            "You MUST only use the structured data provided. "
            "You MUST NOT add new facts, skills, requirements, certifications, languages, citizenship, or assumptions. "
            "You MUST NOT change any numeric values. "
            "If information is not in the JSON, you must not mention it. "
            "Rewrite for clarity and executive tone. Output plain text only with the same two sections."
        )
        user = f"""Using ONLY this structured scoring data and the draft explanation, rewrite the text to be clearer and more executive.
Do not add any facts not present below.

Structured scoring data (JSON):
{json.dumps(structured, ensure_ascii=False)}

Draft explanation:
{draft_text}
"""
        try:
            return llm(system, user)
        except Exception:
            return None

@app.route("/")
def home():
    lang = session.get("lang","sv")
    t = translations.get(lang, translations["sv"])
    return render_template("index.html", t=t, lang=lang, job_input_mode="url", job_url="", job_text="", role="", company="", culture="", reviews="")

@app.route("/run", methods=["POST"])
@limiter.limit("3/hour")
def run():
    lang = request.form.get("lang","sv")
    session["lang"] = lang
    t = translations.get(lang, translations["sv"])

    

    cv = request.form.get("cv", "")
    role = request.form.get("role","").strip()
    company = request.form.get("company","").strip()
    culture = request.form.get("culture","").strip()
    reviews = request.form.get("reviews","").strip()

    job_input_mode = request.form.get("job_input_mode","url").strip()
    job_url = request.form.get("job_url","").strip()
    job_text = request.form.get("job_text","").strip()

    preview = None
    error = None
    job = ""

    if job_input_mode == "text":
        if not job_text:
            error = "Please paste the job description / requirements."
        else:
            job = job_text
    else:
        # URL mode (default)
        if not job_url:
            error = "Please provide a job posting URL."
        else:
            try:
                job = fetch_job_from_url(job_url)
            except Exception as e:
                error = str(e)
                try:
                    preview = fetch_job_preview(job_url)
                except Exception:
                    preview = None

    if error:
        return render_template(
            "index.html",
            t=t,
            lang=lang,
            error=error,
            preview=preview,
            job_url=job_url,
            job_text=job_text,
            job_input_mode=job_input_mode,
            role=role,
            company=company,
            culture=culture,
            reviews=reviews,
        )

    if not role:
        error = "Please enter the target job role/title."
        return render_template(
            "index.html",
            t=t,
            lang=lang,
            error=error,
            preview=preview,
            job_url=job_url,
            job_text=job_text,
            job_input_mode=job_input_mode,
            role=role,
            company=company,
            culture=culture,
            reviews=reviews,
        )

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
    hire_score, hire_expl, hire_breakdown = compute_hireability_from_match(match_score, match_data, hard_gate_status)
    
    # 3-layer explanation:
    # Layer 2: deterministic base narrative + technical breakdown
    base_text = build_hireability_sections(match_score, hire_score, match_data, hard_gate_status, hire_breakdown)

    # Layer 3: optional safe LLM rewriter (polish only), guarded by validation + fallback
    structured_for_rewriter = {
    "match_score": match_score,
    "hireability_score": hire_score,
    "hard_gate_status": hard_gate_status,
    "critical_gaps_count": hire_breakdown.get("critical_gaps", 0),
    "moderate_gaps_count": hire_breakdown.get("moderate_gaps", 0),
    "minor_gaps_count": hire_breakdown.get("minor_gaps", 0),
    "evidence_quality": hire_breakdown.get("evidence_quality", "medium"),
    "timeline_risk": hire_breakdown.get("timeline_risk", "low"),
    "total_penalty": hire_breakdown.get("total_penalty", 0),
    }

    allowed_numbers = {str(v) for v in [
    structured_for_rewriter["match_score"],
    structured_for_rewriter["hireability_score"],
    structured_for_rewriter["critical_gaps_count"],
    structured_for_rewriter["moderate_gaps_count"],
    structured_for_rewriter["minor_gaps_count"],
    structured_for_rewriter["total_penalty"],
    hire_breakdown.get("critical_penalty", 0),
    hire_breakdown.get("moderate_penalty", 0),
    hire_breakdown.get("minor_penalty", 0),
    hire_breakdown.get("evidence_penalty", 0),
    hire_breakdown.get("timeline_penalty", 0),
    ]}

    use_rewriter = (os.getenv("LLM_REWRITER_MODE", "false").strip().lower() == "true")
    polished = None
    if use_rewriter:
        polished = polish_narrative_with_llm(structured_for_rewriter, base_text, lang)
        if polished and not validate_rewriter_output(polished, allowed_numbers):
            polished = None

    hire = polished if polished else base_text

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

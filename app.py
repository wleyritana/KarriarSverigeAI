import os
import re
import json
from io import BytesIO
from typing import Any, Dict, Tuple, Optional

from flask import Flask, render_template, request, session, redirect, url_for, send_file
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from translations import translations
from job_fetcher import fetch_job_from_url, fetch_job_preview
from pdf_report import build_pdf_report

from agents import (
    requirement_intelligence,
    ats_audit,
    recruiter_match,
    recruiter_psychology,
    optimize_cv,
    ats_submission,
    interview_pack,
    culture_analysis,
    hard_gate_extract,
)

from openai_client import llm


# -----------------------------
# Helpers: language + parsing
# -----------------------------

ACCESS_PASSWORD = os.getenv("ACCESS_PASSWORD", "1234")


def get_t(lang: str) -> dict:
    lang = (lang or "en").lower()
    return translations.get(lang, translations["en"])


def parse_json_with_repair(raw: Any) -> dict:
    """Parse JSON from LLM. Lightweight repair: extract first {...} block."""
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return raw
    s = str(raw).strip()
    try:
        return json.loads(s)
    except Exception:
        m = re.search(r"\{.*\}", s, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                return {}
        return {}


def apply_hard_gate_caps(score: int, hard_gate_status: str) -> int:
    try:
        score = int(score)
    except Exception:
        return score
    if hard_gate_status == "fail":
        return min(score, 25)
    if hard_gate_status == "risk":
        return min(score, 45)
    return score


def compute_hard_gate_status(hard_gates_output: Any) -> str:
    """Return 'clear' | 'risk' | 'fail' from hard-gates output."""
    if hard_gates_output is None:
        return "clear"

    gates = []
    if isinstance(hard_gates_output, list):
        gates = hard_gates_output
    elif isinstance(hard_gates_output, dict):
        gates = hard_gates_output.get("hard_gates") or []
    else:
        data = parse_json_with_repair(hard_gates_output)
        if isinstance(data, dict):
            gates = data.get("hard_gates") or []
        elif isinstance(data, list):
            gates = data

    # gates are dicts like {"gate": "...", "status":"pass|risk|fail", ...}
    status_rank = {"clear": 0, "pass": 0, "risk": 1, "fail": 2}
    worst = 0
    for g in gates or []:
        if not isinstance(g, dict):
            continue
        s = (g.get("status") or "").lower().strip()
        worst = max(worst, status_rank.get(s, 0))
    return "fail" if worst == 2 else ("risk" if worst == 1 else "clear")


def extract_score_fallback(text: str, kind: str = "match") -> int:
    """Fallback extraction if JSON missing; avoids crashing."""
    if not text:
        return 0
    # Find last percentage-like number
    nums = re.findall(r"\b(\d{1,3})\b", str(text))
    for n in reversed(nums):
        try:
            v = int(n)
            if 0 <= v <= 100:
                return v
        except Exception:
            continue
    return 0


# -----------------------------
# Deterministic hireability model
# -----------------------------

def compute_penalties(match_data: dict) -> Tuple[int, dict]:
    critical = match_data.get("critical_gaps") or []
    moderate = match_data.get("moderate_gaps") or []
    minor = match_data.get("minor_gaps") or []

    crit_pen = 15 * len(critical)
    mod_pen = 7 * len(moderate)
    min_pen = 3 * len(minor)

    evq = (match_data.get("evidence_quality") or "medium").lower()
    tl = (match_data.get("timeline_risk") or "low").lower()

    ev_pen = 0 if evq == "strong" else (5 if evq == "medium" else 10)
    tl_pen = 0 if tl == "low" else (5 if tl == "medium" else 10)

    total = crit_pen + mod_pen + min_pen + ev_pen + tl_pen
    total = max(0, min(total, 90))

    breakdown = {
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
    return total, breakdown


def compute_hireability_from_match(match_score: int, match_data: dict, hard_gate_status: str) -> Tuple[int, dict]:
    penalties, breakdown = compute_penalties(match_data)
    raw = max(0, min(100, int(match_score) - penalties))

    capped = raw
    if hard_gate_status == "fail":
        capped = min(capped, 25)
    elif hard_gate_status == "risk":
        capped = min(capped, 45)

    breakdown["raw_hireability"] = raw
    breakdown["final_hireability"] = capped
    breakdown["hard_gate_status"] = hard_gate_status
    return capped, breakdown


# -----------------------------
# Layer 2: deterministic explanation (A + B)
# -----------------------------

def build_hireability_sections(match_score: int, hire_score: int, match_data: dict, breakdown: dict) -> str:
    crit = breakdown.get("critical_gaps", 0)
    mod = breakdown.get("moderate_gaps", 0)
    minor = breakdown.get("minor_gaps", 0)
    evq = breakdown.get("evidence_quality", "medium")
    tlr = breakdown.get("timeline_risk", "low")
    total_pen = breakdown.get("total_penalty", 0)
    hard_gate_status = breakdown.get("hard_gate_status", "clear")

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
        hard_gate_note = "Eligibility hard gate status is FAIL. This typically stops the application from progressing regardless of fit."
    elif hard_gate_status == "risk":
        hard_gate_note = "Eligibility hard gate status is RISK (unclear). This can materially reduce the chance of progressing until clarified."

    def bullets(items, maxn=6):
        items = [str(x).strip() for x in (items or []) if str(x).strip()]
        return "\n".join([f"- {x}" for x in items[:maxn]]) if items else "- None identified"

    blockers = match_data.get("blockers") or []
    critical_list = match_data.get("critical_gaps") or []
    moderate_list = match_data.get("moderate_gaps") or []
    minor_list = match_data.get("minor_gaps") or []

    a = []
    a.append("Section A: Executive Summary (Narrative)")
    a.append("")
    a.append(f"The Recruiter Match Score for this role is {match_score}/100, indicating alignment between job requirements and CV evidence.")
    a.append(f"The Hireability Score for this role is {hire_score}/100.")
    a.append("")
    a.append(f"Key drivers: {crit} critical gap(s), {mod} moderate gap(s), and {minor} minor issue(s). Evidence quality is {evq} and timeline risk is {tlr}.")
    if blockers:
        a.append("Notable blockers identified by the recruiter assessment:")
        a.append(bullets(blockers, 4))
    if hard_gate_note:
        a.append("")
        a.append(hard_gate_note)
    a.append("")
    a.append(summary_line)

    b = []
    b.append("Section B: Scoring Breakdown (Technical)")
    b.append("")
    b.append(f"Base fit (Recruiter Match): {match_score}/100")
    b.append(f"Total penalties applied: {total_pen}")
    b.append("")
    b.append("Penalty breakdown:")
    b.append(f"- Critical gaps: {crit} × 15 = {breakdown.get('critical_penalty', 0)}")
    b.append(f"- Moderate gaps: {mod} × 7 = {breakdown.get('moderate_penalty', 0)}")
    b.append(f"- Minor issues: {minor} × 3 = {breakdown.get('minor_penalty', 0)}")
    b.append(f"- Evidence quality ({evq}): {breakdown.get('evidence_penalty', 0)}")
    b.append(f"- Timeline risk ({tlr}): {breakdown.get('timeline_penalty', 0)}")
    b.append("")
    b.append(f"Hireability = Match ({match_score}) − Penalties ({total_pen}) (then hard-gate caps if applicable).")
    b.append("")
    b.append("Critical gaps:")
    b.append(bullets(critical_list))
    b.append("")
    b.append("Moderate gaps:")
    b.append(bullets(moderate_list))
    b.append("")
    b.append("Minor issues:")
    b.append(bullets(minor_list))

    return "\n".join(a + ["", ""] + b)


# -----------------------------
# Layer 3: optional safe LLM rewriter
# -----------------------------

def _numbers_in_text(s: str) -> set[str]:
    return set(re.findall(r"\b\d{1,3}\b", s or ""))


def validate_rewriter_output(output_text: str, allowed_numbers: set[str]) -> bool:
    if not output_text:
        return False
    if "Section A:" not in output_text or "Section B:" not in output_text:
        return False
    found = _numbers_in_text(output_text)
    return found.issubset(allowed_numbers)


def polish_narrative_with_llm(structured: dict, draft_text: str) -> Optional[str]:
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


# -----------------------------
# Flask app + auth gate
# -----------------------------

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", os.urandom(24))

limiter = Limiter(get_remote_address, app=app, default_limits=["60 per hour"])


@app.before_request
def require_login():
    allowed_paths = ["/login", "/health"]
    if request.path.startswith("/static"):
        return None
    if request.path in allowed_paths:
        return None
    if not session.get("authenticated"):
        return redirect(url_for("login"))
    return None


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        if request.form.get("password") == ACCESS_PASSWORD:
            session["authenticated"] = True
            return redirect(url_for("home"))
        error = "Incorrect password"
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# -----------------------------
# Routes
# -----------------------------

@app.route("/")
def home():
    lang = request.args.get("lang", "en")
    t = get_t(lang)
    return render_template(
        "index.html",
        t=t,
        lang=lang,
        job_input_mode="url",
        job_url="",
        job_text="",
        role="",
        company="",
        culture="",
        reviews="",
        error=None,
        preview=None,
    )


@app.route("/health")
def health():
    return {"status": "ok"}


@app.route("/download_pdf")
def download_pdf():
    report_data = {
        "Hireability Score": str(session.get("hire_score", "")),
        "Match Score": str(session.get("match_score", "")),
    }
    pdf = build_pdf_report(report_data)
    return send_file(
        pdf,
        as_attachment=True,
        download_name="AI_Job_Hunt_Executive_Report.pdf",
        mimetype="application/pdf",
    )


@app.route("/run", methods=["POST"])
@limiter.limit("30 per hour")
def run():
    lang = request.form.get("lang", "en")
    t = get_t(lang)

    cv = request.form.get("cv", "").strip()
    role = request.form.get("role", "").strip()
    company = request.form.get("company", "").strip()
    culture = request.form.get("culture", "").strip()
    reviews = request.form.get("reviews", "").strip()

    job_input_mode = request.form.get("job_input_mode", "url").strip()
    job_url = request.form.get("job_url", "").strip()
    job_text = request.form.get("job_text", "").strip()

    # Basic validation
    if not cv:
        return render_template("index.html", t=t, lang=lang, error="Please paste your CV.", preview=None,
                               job_input_mode=job_input_mode, job_url=job_url, job_text=job_text,
                               role=role, company=company, culture=culture, reviews=reviews)

    if not role:
        return render_template("index.html", t=t, lang=lang, error="Please enter the target job role/title.", preview=None,
                               job_input_mode=job_input_mode, job_url=job_url, job_text=job_text,
                               role=role, company=company, culture=culture, reviews=reviews)

    preview = None
    job = ""
    if job_input_mode == "text":
        if not job_text:
            return render_template("index.html", t=t, lang=lang, error="Please paste the job description / requirements.", preview=None,
                                   job_input_mode=job_input_mode, job_url=job_url, job_text=job_text,
                                   role=role, company=company, culture=culture, reviews=reviews)
        job = job_text
    else:
        if not job_url:
            return render_template("index.html", t=t, lang=lang, error="Please provide a job posting URL.", preview=None,
                                   job_input_mode=job_input_mode, job_url=job_url, job_text=job_text,
                                   role=role, company=company, culture=culture, reviews=reviews)
        try:
            job = fetch_job_from_url(job_url)
        except Exception as e:
            try:
                preview = fetch_job_preview(job_url)
            except Exception:
                preview = None
            return render_template("index.html", t=t, lang=lang, error=str(e), preview=preview,
                                   job_input_mode=job_input_mode, job_url=job_url, job_text=job_text,
                                   role=role, company=company, culture=culture, reviews=reviews)
    # --------- Intelligence pipeline ---------
    hard_gates_raw = hard_gate_extract(cv, job, role, lang)
    hard_gates_data = parse_json_with_repair(hard_gates_raw)
    hard_gate_status = compute_hard_gate_status(hard_gates_data or hard_gates_raw)

    hard_gates_json = json.dumps(hard_gates_data or {}, ensure_ascii=False)

    # Recruiter match first (used for scoring + CV optimization)
    match_raw = recruiter_match(cv, job, role, lang, hard_gates_json)
    match_data = parse_json_with_repair(match_raw)

    match_score = match_data.get("match_score")
    if match_score is None:
        match_score = extract_score_fallback(match_raw, kind="match")
    try:
        match_score = int(match_score)
    except Exception:
        match_score = extract_score_fallback(match_raw, kind="match")

    # Cap match if hard gates are risky/failed
    match_score = apply_hard_gate_caps(match_score, hard_gate_status)

    # Hireability from match + gaps + hard gates
    hire_score, hire_breakdown = compute_hireability_from_match(match_score, match_data, hard_gate_status)

    # Other modules
    deep = requirement_intelligence(cv, job, role, lang)
    ats = ats_audit(cv, job, role, lang, hard_gates_json)
    psyche = recruiter_psychology(cv, job, role, lang)
    optimized = optimize_cv(cv, match_raw, lang)
    ats_cv = ats_submission(cv, job, role, lang, hard_gates_json)
    interview = interview_pack(cv, job, role, lang)
    culture_report = culture_analysis(company, culture, reviews, lang)

    # Layer 2 base explanation
    base_text = build_hireability_sections(match_score, hire_score, match_data, hire_breakdown)

    # Layer 3 optional polish
    use_rewriter = (os.getenv("LLM_REWRITER_MODE", "false").strip().lower() == "true")
    hire_text = base_text
    if use_rewriter:
        structured = {
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
            structured["match_score"],
            structured["hireability_score"],
            structured["critical_gaps_count"],
            structured["moderate_gaps_count"],
            structured["minor_gaps_count"],
            structured["total_penalty"],
            hire_breakdown.get("critical_penalty", 0),
            hire_breakdown.get("moderate_penalty", 0),
            hire_breakdown.get("minor_penalty", 0),
            hire_breakdown.get("evidence_penalty", 0),
            hire_breakdown.get("timeline_penalty", 0),
        ]}
        polished = polish_narrative_with_llm(structured, base_text)
        if polished and validate_rewriter_output(polished, allowed_numbers):
            hire_text = polished

    # Pretty JSON display for recruiter match
    match_display = match_raw
    try:
        match_display = json.dumps(match_data, indent=2, ensure_ascii=False)
    except Exception:
        pass

    # Scores + colors
    hire_color = "green" if hire_score >= 70 else ("yellow" if hire_score >= 40 else "red")
    match_color = "green" if match_score >= 70 else ("yellow" if match_score >= 40 else "red")

    session["hire_score"] = hire_score
    session["match_score"] = match_score

    return render_template(
        "dashboard.html",
        t=t,
        lang=lang,
        hire_score=hire_score,
        match_score=match_score,
        hire_color=hire_color,
        match_color=match_color,
        deep=deep,
        ats=ats,
        psyche=psyche,
        optimized=optimized,
        ats_cv=ats_cv,
        interview=interview,
        culture_report=culture_report,
        hard_gates=str(hard_gates_raw),
        match=match_display,
        hire=hire_text,
    )

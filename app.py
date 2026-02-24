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

def extract_score(text):
    match = re.search(r'(\b\d{2,3}\b)', text)
    return min(int(match.group(1)),100) if match else 60

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
    reviews = request.form.get("reviews")    # Hard gates (eligibility / knockout requirements)
    hard_gate_status = "clear"
    hard_gates_json = None
    try:
        hard_gates_json = hard_gate_extract(cv, job, role, lang)
        hard_gate_status = compute_hard_gate_status(hard_gates_json)
    except Exception:
        # If extraction fails, continue without hard gate signal (do not crash)
        hard_gate_status = "clear"
        hard_gates_json = None


    match = recruiter_match(cv, job, role, lang, hard_gates_json)
    optimized = optimize_cv(cv, match, lang)
    ats = ats_audit(optimized, job, role, lang, hard_gates_json)
    ats_cv = ats_submission(optimized, job, role, lang, hard_gates_json)
    interview = interview_pack(optimized, job, role, lang)
    deep = requirement_intelligence(cv, job, role, lang)
    hire = hireability_score(cv, job, role, lang)
    psyche = recruiter_psychology(cv, job, role, lang)
    culture_report = culture_analysis(company, culture, reviews, lang)

    hire_score = extract_score(hire)
    hire_score = apply_hard_gate_caps(hire_score, hard_gate_status)
    match_score = extract_score(match)
    match_score = apply_hard_gate_caps(match_score, hard_gate_status)
    session["hire_score"] = hire_score
    session["match_score"] = match_score

    return render_template("dashboard.html",
        hard_gate_status=hard_gate_status,

        hard_gates=hard_gates_json,

        t=t,
        hire_score=hire_score,
        match_score=match_score,
        hire_color=score_color(hire_score),
        match_color=score_color(match_score),
        match=match,
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

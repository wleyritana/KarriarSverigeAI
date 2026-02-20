import os, re
from io import BytesIO
from flask import Flask, render_template, request, session, send_file
from dotenv import load_dotenv
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from translations import translations
from agents import *
from report_generator import build_report

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY","dev")

limiter = Limiter(get_remote_address, app=app, storage_uri="memory://")

def extract_score(text):
    match = re.search(r'(\b\d{2,3}\b)', text)
    return min(int(match.group(1)),100) if match else 60

def strip_emojis(text):
    return "".join(ch for ch in (text or "") if ord(ch) < 100000)

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
    job = request.form["job"]
    role = request.form.get("role")
    company = request.form.get("company")
    culture = request.form.get("culture")
    reviews = request.form.get("reviews")

    match = recruiter_match(cv, job, role, lang)
    optimized = optimize_cv(cv, match, lang)
    ats = ats_audit(optimized, lang)
    ats_cv = ats_submission(optimized, lang)
    interview = interview_pack(optimized, job, role, lang)
    deep = requirement_intelligence(cv, job, role, lang)
    hire = hireability_score(cv, job, role, lang)
    psyche = recruiter_psychology(cv, job, role, lang)
    culture_report = culture_analysis(company, culture, reviews, lang)

    session["enhanced_cv_txt"] = strip_emojis(optimized)

    hire_score = extract_score(hire)
    match_score = extract_score(match)

    def score_color(score):
        if score < 70:
            return "red"
        elif score < 85:
            return "amber"
        else:
            return "green"

    return render_template("dashboard.html",
        t=t,
        hire_score=hire_score,
        match_score=match_score,
        hire_color=score_color(hire_score),
        match_color=score_color(match_score),
        optimized=optimized,
        ats=ats,
        ats_cv=ats_cv,
        interview=interview,
        culture_report=culture_report
    )

@app.route("/download")
def download():
    file = build_report(session.get("report", {}))
    return send_file(file, as_attachment=True,
        download_name="AI_Job_Hunt_v5.1_Report.docx",
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document")

@app.route("/download_cv")
def download_cv():
    enhanced = session.get("enhanced_cv_txt")
    return send_file(BytesIO(enhanced.encode("utf-8")),
        as_attachment=True,
        download_name="enhanced_cv.txt",
        mimetype="text/plain")

@app.route("/health")
def health():
    return {"status":"ok"}

from flask import Flask, render_template, request
from app.services.job_fetcher import fetch_job_from_url
from app.services.openai_client import llm_text

def create_app():
    app = Flask(__name__)

    @app.route("/")
    def home():
        return render_template("index.html")

    @app.route("/run", methods=["POST"])
    def run():
        cv = request.form["cv"]
        job_url = request.form["job_url"]
        company_material = request.form.get("company_material")
        employee_reviews = request.form.get("employee_reviews")

        job_ad = fetch_job_from_url(job_url)

        recruiter = llm_text("You are a recruiter.", f"Compare CV and job ad.\nCV:{cv}\nJOB:{job_ad}")
        optimizer = llm_text("Rewrite using X-Y-Z. Do not invent.", cv)
        ats = llm_text("Simulate ATS and list risks.", optimizer)
        interview = llm_text("Generate interview questions.", cv)

        culture = None
        if company_material and employee_reviews:
            culture = llm_text(
                "Analyze company culture vs reviews.",
                f"Branding:{company_material}\nReviews:{employee_reviews}"
            )

        return render_template(
            "result.html",
            recruiter=recruiter,
            optimizer=optimizer,
            ats=ats,
            interview=interview,
            culture=culture
        )

    return app

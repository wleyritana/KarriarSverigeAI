from openai_client import llm

def lang_rule(lang):
    return "Respond in Swedish." if lang == "sv" else "Respond in English."

def hard_gate_extract(cv, job, role, lang):
    system = f"You are an automated hiring system (ATS) focusing on eligibility and knockout gates. {lang_rule(lang)} Output STRICT JSON only."
    user = f'''
Extract ALL hard gates and eligibility constraints from the JOB posting, and check whether the CV explicitly satisfies them.

Return JSON ONLY with this schema:
{{
  "hard_gate_status": "clear|risk|fail",
  "hard_gates": [
    {{
      "type": "citizenship|right_to_work|security_clearance|no_sponsorship|degree|certification|residency|location|other",
      "requirement": "short requirement statement",
      "severity": "hard_gate|strong_preference|unknown",
      "evidence_quote": "verbatim quote from the JOB (max 25 words)",
      "cv_evidence_status": "satisfied|unclear|missing",
      "recommended_action": "what the candidate should do next"
    }}
  ]
}}

Rules:
- Only use evidence_quote from the JOB text.
- Do NOT guess the candidate's citizenship/work authorization/clearance unless explicitly stated in the CV.
- If the JOB mentions sponsorship/citizenship/clearance/degree/certification/location constraints, include them.
- hard_gate_status:
  - "fail" if any hard_gate item has cv_evidence_status="missing"
  - "risk" if no missing but any item has cv_evidence_status="unclear"
  - "clear" if all items are satisfied OR no gates found

ROLE: {role}

CV:
{cv}

JOB:
{job}
'''
    return llm(system, user)

def recruiter_match(cv, job, role, lang, hard_gates_json=None):
    return llm(
        f"You are a recruiter. Be realistic and treat eligibility gates as blockers. {lang_rule(lang)}",
        f'''Provide numeric match score (0-100) and gaps, plus blockers. 
If hard gates exist (citizenship/clearance/no-sponsorship/etc), include them as blockers and cap the score unless the CV explicitly proves eligibility.

Hard-gate analysis (JSON, may be empty or invalid):
{hard_gates_json or ""}

CV:
{cv}

JOB:
{job}

ROLE:
{role}
'''
    )


def optimize_cv(cv, match, lang):
    return llm(
        f"You are a CV strategist. Use X-Y-Z bullets when possible. Do not invent metrics. {lang_rule(lang)}",
        f"""Rewrite CV experience based on: {match}

CV:
{cv}
"""
    )
def ats_audit(cv, job, role, lang, hard_gates_json=None):
    return llm(
        f"You are an ATS system similar to SmartRecruiters/Workday. Audit parsing, screening, and hard gates. {lang_rule(lang)}",
        f'''Return a structured report with these sections:
1) Eligibility & Hard Gates (citizenship/right-to-work/clearance/no sponsorship/degree/certs/location). Use evidence quotes from the JOB.
2) ATS Parsing Risks (format/sections/dates).
3) Screening Risks (must-have keywords, title alignment, years of experience signals).
4) Actionable Fixes (top 10).

Hard-gate analysis (JSON, may be empty or invalid):
{hard_gates_json or ""}

ROLE:
{role}

CV (optimized experience section or ATS version):
{cv}

JOB:
{job}
'''
    )

def ats_submission(cv, job, role, lang, hard_gates_json=None):
    return llm(
        f"You generate an ATS submission CV. One column. Standard headings. No tables/icons. {lang_rule(lang)}",
        f'''Create an ATS submission CV that targets the JOB requirements without inventing facts.
- Use headings: Summary, Skills, Work Experience, Education, Certifications (if present)
- Ensure must-have keywords appear naturally.
- Keep dates consistent.

ROLE: {role}

Hard-gate analysis (for awareness only; do not invent eligibility):
{hard_gates_json or ""}

CV:
{cv}

JOB:
{job}
'''
    )

def interview_pack(cv, job, role, lang):
    return llm(
        f"You are a hiring manager. {lang_rule(lang)}",
        f"Generate technical, HR and strategic questions. CV:{cv} JOB:{job} ROLE:{role}"
    )

def requirement_intelligence(cv, job, role, lang):
    return llm(
        f"You analyze job deeply. {lang_rule(lang)}",
        f"Break job into core skills, hidden signals, seniority expectations and alignment. CV:{cv} JOB:{job} ROLE:{role}"
    )

def hireability_score(cv, job, role, lang):
    return llm(
        f"You calculate hireability score. {lang_rule(lang)}",
        f"Return numeric hireability score (0-100) and explanation. CV:{cv} JOB:{job} ROLE:{role}"
    )

def recruiter_psychology(cv, job, role, lang):
    return llm(
        f"You simulate recruiter psychology. {lang_rule(lang)}",
        f"Simulate recruiter reaction. CV:{cv} JOB:{job} ROLE:{role}"
    )

def culture_analysis(company, culture, reviews, lang):
    return llm(
        f"You analyze company culture alignment. {lang_rule(lang)}",
        f"Compare official culture vs employee reviews and identify risks. Company:{company} Official:{culture} Reviews:{reviews}"
    )

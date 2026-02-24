from openai_client import llm

def lang_rule(lang):
    return "Respond in Swedish." if lang == "sv" else "Respond in English."



def hard_gate_extract(cv, job, role, lang):
    system = f"You are an automated hiring system (ATS) focusing on eligibility and knockout gates. {lang_rule(lang)} Output STRICT JSON only."
    user = f'''
Extract ALL eligibility constraints / hard gates from the JOB posting, then check whether the CV explicitly satisfies them.

Return JSON ONLY with this schema:
{{
  "hard_gates": [
    {{
      "type": "citizenship|right_to_work|security_clearance|no_sponsorship|degree|certification|residency|location|language|other",
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
- Do NOT guess candidate eligibility beyond what is explicitly in the CV.
- Include language requirements (e.g., fluent Swedish/English) when stated as required/mandatory.
- Use severity="hard_gate" only when the job says required/mandatory/must. Use strong_preference for "preferred/plus".
- For cv_evidence_status:
  - satisfied: CV explicitly states it (e.g., language skills, citizenship/work authorization, certifications)
  - unclear: not stated in CV
  - missing: CV contradicts or clearly lacks a required item (e.g., "needs sponsorship" while job says no sponsorship)

ROLE: {role}

CV:
{cv}

JOB:
{job}
'''
    return llm(system, user)

def recruiter_match(cv, job, role, lang, hard_gates_json=None):
    system = f"You are a recruiter and ATS screener. Be realistic and strict. {lang_rule(lang)} Output STRICT JSON only (no markdown)."
    user = f'''
Return JSON only with this schema:
{{
  "match_score": 0-100,
  "blockers": ["..."],
  "critical_gaps": ["missing must-have requirement ..."],
  "moderate_gaps": ["missing nice-to-have or weaker evidence ..."],
  "minor_gaps": ["presentation or minor alignment improvements ..."],
  "evidence_quality": "strong|medium|weak",
  "timeline_risk": "low|medium|high",
  "short_rationale": "2-5 sentences explaining the score"
}}

Rules:
- match_score MUST represent fit for THIS job only, based on JOB requirements vs CV evidence.
- If hard gates exist (citizenship/clearance/no-sponsorship/language/etc), include them as blockers when relevant.
- Do NOT invent facts not present in the CV.
- Keep lists concise (max ~8 items each).

Hard-gate analysis (JSON, may be empty or invalid):
{hard_gates_json or ""}

ROLE: {role}

CV:
{cv}

JOB:
{job}
'''
    return llm(system, user)
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

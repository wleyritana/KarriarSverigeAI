from openai_client import llm

def lang_rule(lang):
    return "Respond in Swedish." if lang == "sv" else "Respond in English."

def recruiter_match(cv, job, role, lang):
    return llm(f"You are a recruiter. {lang_rule(lang)}",
               f"Provide numeric match score (0-100) and gaps. CV:{cv} JOB:{job} ROLE:{role}")

def optimize_cv(cv, match, lang):
    return llm(f"You are a CV strategist. {lang_rule(lang)}",
               f"Rewrite CV experience based on: {match} CV:{cv}")

def ats_audit(cv, lang):
    return llm(f"You are an ATS system. {lang_rule(lang)}",
               f"Provide ATS risks and fixes. CV:{cv}")

def ats_submission(cv, lang):
    return llm(f"You generate ATS CV. {lang_rule(lang)}",
               f"Rewrite CV in ATS format. CV:{cv}")

def interview_pack(cv, job, role, lang):
    return llm(f"You are a hiring manager. {lang_rule(lang)}",
               f"Generate interview questions. CV:{cv} JOB:{job} ROLE:{role}")

def requirement_intelligence(cv, job, role, lang):
    return llm(f"You analyze job deeply. {lang_rule(lang)}",
               f"Break job into core skills and alignment. CV:{cv} JOB:{job} ROLE:{role}")

def hireability_score(cv, job, role, lang):
    return llm(f"You calculate hireability score. {lang_rule(lang)}",
               f"Return numeric hireability score (0-100). CV:{cv} JOB:{job} ROLE:{role}")

def recruiter_psychology(cv, job, role, lang):
    return llm(f"You simulate recruiter psychology. {lang_rule(lang)}",
               f"Simulate recruiter reaction. CV:{cv} JOB:{job} ROLE:{role}")

# KarriarSverigeAI

# KarriarSverigeAI – Enterprise ATS Intelligence Platform

AI-powered job application intelligence system with recruiter simulation, ATS screening logic, deterministic hard-gate enforcement, and hireability scoring.

Production-ready for GitHub and Railway deployment.

---

## Overview

KarriarSverigeAI simulates how real automated hiring systems (SmartRecruiters, Workday-style ATS) screen candidates.

This platform combines:

- Automated Hard Gate detection (citizenship, clearance, etc.)
- ATS ranking simulation
- Recruiter match scoring
- CV optimization
- Interview preparation
- Culture alignment analysis
- Deterministic score enforcement

This version is enterprise-aligned and production-stable.

---

## Core Capabilities

### 1. URL-Based Job Extraction

- Enter job posting URL
- Automatic HTML cleaning
- Graceful fallback if blocked
- No copy/paste required

---

### 2. Hard Gate Intelligence (Enterprise Feature)

Automatically detects from job posting:

- Citizenship requirements
- Right-to-work constraints
- No sponsorship clauses
- Security clearance requirements
- Required degrees
- Required certifications
- Location constraints

Each gate includes:

- Evidence quote from job posting
- CV evidence status (satisfied / unclear / missing)

#### Deterministic Score Caps

Hard gates override scoring:

- fail → score capped at 25
- risk → score capped at 45
- clear → no cap

This mirrors real ATS knockout logic.

---

### 3. Recruiter Simulation

Simulates real recruiter evaluation:

- Match score (0–100)
- Gap analysis
- Blocker detection
- Seniority alignment review

Score respects hard gate enforcement.

---

### 4. ATS Audit (SmartRecruiters-Style Simulation)

Includes:

- Eligibility & compliance analysis
- Parsing risks (formatting, structure, dates)
- Screening risks (keywords, experience alignment)
- Actionable top fixes
- Structured ranking breakdown

---

### 5. ATS Submission CV Generator

Generates ATS-ready version:

- One-column structure
- Standard headings
- No tables/icons
- Keyword-aligned formatting
- Consistent dates
- Certification section (if present)

---

### 6. Hireability Score

- Numeric score (0–100)
- Deterministically capped by hard gates
- Consistent across modules

---

### 7. Interview Preparation Pack

Generates:

- Technical questions
- HR questions
- Strategic questions
- Hiring manager perspective

---

### 8. Recruiter Psychology Module

Simulates:

- Recruiter first impression
- Risk perception
- Promotion readiness
- Narrative clarity

---

### 9. Culture & Employee Review Analysis

If provided:

- Compare official employer branding
- Cross-analyze employee review themes
- Identify alignment risks
- Highlight cultural red flags

---

### 10. PDF Export

Downloadable structured report including:

- Hard Gate results
- Scores
- ATS audit
- CV optimization
- Interview pack

---

## Architecture

- Stateless (no database required)
- Access Gate (password protected)
- Rate limiting on analysis endpoint
- Health endpoint (/health)
- Strict JSON validation for hard gates
- Deterministic Python-based enforcement layer

---

## Project Structure

KarriarSverigeAI-main/

├── app.py  
├── agents.py  
├── openai_client.py  
├── job_fetcher.py  
├── templates/  
├── static/  
├── requirements.txt  
├── Procfile  
├── railway.json  
└── .env.example  

---

## Environment Variables

Set in Railway or locally:

OPENAI_API_KEY=your_openai_key  
SECRET_KEY=random_secure_string  
ACCESS_PASSWORD=your_access_gate_password  

Optional:

OPENAI_MODEL=gpt-4.1-mini  

---

## Local Development

1. Create virtual environment  
   python -m venv venv  
   source venv/bin/activate  

2. Install dependencies  
   pip install -r requirements.txt  

3. Create .env from .env.example  

4. Run  
   python app.py  

---

## Railway Deployment

1. Push repository to GitHub  
2. Create new Railway project  
3. Deploy from GitHub  
4. Set environment variables  
5. Railway auto-detects Procfile  

Production ready.

---

## System Design Philosophy

This system does not attempt to bypass hiring requirements.

It:

- Detects eligibility gates
- Enforces deterministic caps
- Simulates ATS ranking behavior
- Improves ranking within valid constraints
- Provides transparent screening logic

This mirrors real enterprise hiring systems.

---

## Version

Enterprise Aligned Version  
Hard Gate–Aware ATS Intelligence  
Production Stable  

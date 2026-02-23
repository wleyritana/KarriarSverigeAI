# KarriarSverigeAI

AI Job Hunting System --- Version 6 (Produktionsversion)

En AI-driven plattform för jobbsökningsoptimering byggd med Flask,
OpenAI och PostgreSQL (Railway-redo).

Version 6 innehåller: - Full multi-agent-pipeline - Iterativ
poängsättningsloop - ATS-simulering - Intervjuförberedelsemotor -
Webbgränssnitt med autentisering - Analysdashboard -
Produktionsdistribution via Railway

------------------------------------------------------------------------

Översikt

AI Job Hunting System simulerar den verkliga rekryteringsprocessen:

1.  Applicant Tracking System (ATS)
2.  Senior rekryterargranskning
3.  Bedömning av rekryterande chef
4.  HR- och kulturmatchning
5.  Kandidatens strategiska beslutsstöd

Systemet optimerar CV:n både för maskinläsbarhet och mänsklig
trovärdighet.

------------------------------------------------------------------------

Kärnarkitektur (V6)

Multi-agent-flöde

1.  Extractor Agent
    -   Tolkar CV och jobbannons\
    -   Skapar strukturerad Job Map och Candidate Map
2.  Recruiter Agent
    -   Genererar matchningspoäng (0--100)\
    -   Identifierar viktigaste kompetensluckorna\
    -   Upptäcker anställningshinder
3.  Optimizer Agent
    -   Skriver om avsnittet Professional Experience enligt Google
        X-Y-Z\
    -   Integrerar saknade nyckelord\
    -   Undviker påhittade mätvärden
4.  ATS Agent
    -   Simulerar Workday / SuccessFactors\
    -   Flaggar strukturella risker\
    -   Skapar en ATS-optimerad inlämningsversion
5.  Iterationsloop
    -   Kör om matchningsanalys efter optimering\
    -   Visar förbättring (delta)
6.  Interview Agent
    -   Tekniska djupfrågor\
    -   HR- och värderingsfrågor\
    -   Strategiska kandidatfrågor
7.  Analyslager
    -   Genomsnittlig poängförbättring\
    -   Historik över körningar\
    -   Prestandaspårning

------------------------------------------------------------------------

Teknikstack

Backend: - Flask 3 - SQLAlchemy - Flask-Login - OpenAI Responses API -
Gunicorn

Databas: - SQLite (lokal utveckling) - PostgreSQL (Railway produktion)

Distribution: - Railway (Nixpacks build) - Gunicorn WSGI-server

------------------------------------------------------------------------

Installation (Lokal utveckling)

1.  Klona repository

git clone `<din-repo-url>`{=html} cd ai-job-hunting-system

2.  Skapa virtuell miljö

python -m venv .venv source .venv/bin/activate \# Windows:
.venv`\Scripts`{=tex}`\activate`{=tex}

3.  Installera beroenden

pip install -r requirements.txt

4.  Konfigurera miljövariabler

Kopiera miljöfilen:

cp .env.example .env

Redigera `.env`:

OPENAI_API_KEY=din_nyckel SECRET_KEY=slumpmässig_säker_sträng

5.  Starta applikationen

export FLASK_APP=app \# Windows: set FLASK_APP=app flask run

Öppna: http://127.0.0.1:5000

------------------------------------------------------------------------

Produktionsdistribution (Railway)

1.  Pusha repository till GitHub\
2.  Skapa nytt Railway-projekt\
3.  Distribuera från GitHub\
4.  Lägg till PostgreSQL-plugin\
5.  Lägg till miljövariabler:

OPENAI_API_KEY SECRET_KEY OPENAI_MODEL (valfri)

Railway binder automatiskt till \$PORT via Gunicorn.

------------------------------------------------------------------------

Funktioner

-   Säker användarautentisering
-   Permanent historik över körningar
-   Jämförelse av matchningspoäng före/efter
-   Klassificering av ATS-risker
-   X-Y-Z-strukturerad omskrivning av meriter
-   Intervjuförberedelsepaket
-   Analysdashboard
-   Lagring av jobbvarningspreferenser (redo för bakgrundsjobb)

------------------------------------------------------------------------

Säkerhetsöverväganden

För produktionsmiljö bör följande övervägas:

-   Kryptering eller avidentifiering av personuppgifter
-   Retentionspolicy för lagrad data
-   Rate limiting
-   Övervakning och loggning
-   HTTPS-tvingande
-   Bakgrundsarbetare för jobbvarningar

------------------------------------------------------------------------

Färdplan (Nästa utvecklingssteg)

-   Filuppladdning (PDF/DOCX-tolkning)
-   Export av CV till DOCX/PDF
-   Strukturerad JSON-validering
-   Stripe-prenumerationshantering
-   Administrativ analys
-   Enterprise multi-tenant-läge

------------------------------------------------------------------------

Licens

Privat / Intern användning\
(Justera vid kommersiell distribution)

------------------------------------------------------------------------

Författare

AI Job Hunting System --- Version 6\
Multi-Agent Hireability Optimization Engine

## Licens

Intern eller kommersiell användning enligt konfiguration.\
Lägg till separat licensfil vid offentlig publicering.


## Job posting input (URL)
This version expects the job posting as a URL (not pasted text). The app fetches and cleans the page automatically.


## Railway deployment
This repo includes Procfile and railway.json for Railway. Set environment variables OPENAI_API_KEY and SECRET_KEY.

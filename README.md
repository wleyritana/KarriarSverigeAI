# KarriarSverigeAI

## AI Job Hunt v5.4 -- Mobilanpassad Intelligensplattform

AI Job Hunt v5.4 är en fullständig AI-driven karriärintelligensplattform
som analyserar, optimerar och strategiskt positionerar en kandidats CV
mot en specifik jobbannons.

Denna version inkluderar:

-   Full mobilanpassning
-   Alla moduler (1--8) korrekt renderade
-   Företagskultur + medarbetarrecensioner
-   Kollapsbara intelligenssektioner
-   Animerade och färgkodade poängstaplar
-   Svenska som standardspråk (med engelskt stöd)
-   Railway-redo produktionstruktur

------------------------------------------------------------------------

## Funktioner

### Kärnmoduler (1--8)

1.  Rekryterarens matchningsanalys\
2.  CV-optimering\
3.  ATS-analys\
4.  ATS-optimerat CV\
5.  Intervjuförberedelse (Teknisk + HR + Strategisk)\
6.  Företagskultur -- Verklighet vs Bild\
7.  Rekryterarens psykologisimulering\
8.  Anställningsbarhetsanalys

### Förbättrad Intelligens

-   Kravintelligens (djupanalys av jobbkrav)
-   Hireability-score (0--100)
-   Rekryterarens 30-sekunders intryck
-   Strategisk positioneringsanalys

------------------------------------------------------------------------

## Poängsystem

Färgkodade och animerade staplar:

-   Under 70% → Röd (Hög risk)\
-   70--84% → Amber (Behöver förbättras)\
-   85%+ → Grön (Stark matchning)

Staplarna animeras från 0% upp till slutpoängen vid laddning.

------------------------------------------------------------------------

## Mobilanpassning

-   Responsiv layout
-   Touch-vänliga knappar
-   Anpassade textfält
-   Skalbara kort och sektioner
-   Matrix-tema (mörk design)

Fungerar på: - Mobil - Surfplatta - Desktop

------------------------------------------------------------------------

## Språksystem

Standard: Svenska

-   Alla UI-texter växlar mellan svenska och engelska
-   AI-analysen följer valt språk
-   Sessionsbaserad språkhantering
-   Ingen duplicering av templates

------------------------------------------------------------------------

## Teknisk Arkitektur

Backend: - Flask - OpenAI API - Flask-Limiter - python-docx - Gunicorn

Frontend: - Jinja2 templates - Matrix CSS-tema - Kollapsbara sektioner -
JavaScript-animationer

Deployment: - Railway-redo - Procfile inkluderad - runtime.txt
definierad

------------------------------------------------------------------------

## Projektstruktur

ai-job-hunt-v5.4-mobile/ │ ├── app.py ├── agents.py ├── openai_client.py
├── report_generator.py ├── translations.py │ ├── templates/ │ ├──
index.html │ └── dashboard.html │ ├── static/ │ └── styles.css │ ├──
requirements.txt ├── Procfile ├── runtime.txt └── README.md

------------------------------------------------------------------------

## Lokal Installation

1.  Skapa virtuell miljö

python -m venv .venv\
source .venv/bin/activate

Windows:

.venv`\Scripts`{=tex}`\activate  `{=tex}

2.  Installera beroenden

pip install -r requirements.txt

3.  Skapa .env-fil

OPENAI_API_KEY=din_api_nyckel\
OPENAI_MODEL=gpt-4.1-mini\
SECRET_KEY=byt_till_något_säkert

4.  Starta applikationen

flask --app app run

Öppna:

http://127.0.0.1:5000

------------------------------------------------------------------------

## Railway Deployment

1.  Ladda upp projektet till GitHub\
2.  Koppla repository till Railway\
3.  Lägg till miljövariabler:
    -   OPENAI_API_KEY
    -   SECRET_KEY\
4.  Deploya

Hälsokontroll:

/health

------------------------------------------------------------------------

## Positionering

AI Job Hunt v5.4 är en:

-   AI-driven karriärintelligensplattform\
-   Rekryterarsimuleringsmotor\
-   Strategiskt anställningsoptimeringssystem\
-   SaaS-redo karriärverktyg

Lämplig för:

-   Professionella individer\
-   Karriärcoacher\
-   HR-rådgivning\
-   Universitet\
-   Kommersiell SaaS-lansering

------------------------------------------------------------------------

## Licens

Intern eller kommersiell användning enligt konfiguration.\
Lägg till separat licensfil vid offentlig publicering.

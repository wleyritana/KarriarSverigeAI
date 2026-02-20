# KarriarSverigeAI

# AI Job Hunt v5 -- Tvåspråkig Intelligensplattform (Standard: Svenska)

AI Job Hunt v5 är en fullstack AI‑plattform för karriärintelligens som
analyserar och optimerar en kandidats CV mot en jobbannons med hjälp av
rekryterarsimulering, strategisk modellering och psykologiska insikter.

Denna förbättrade version inkluderar fullständigt tvåspråkigt gränssnitt
(Svenska som standard), executive‑dashboard och produktionsklar
konfiguration för driftsättning.

------------------------------------------------------------------------

## 🌍 Språksystem

Standardspråk: **Svenska**

-   Alla UI‑texter växlar dynamiskt mellan svenska och engelska\
-   AI‑analysen följer valt språk\
-   Språk sparas i session\
-   Ingen duplicering av templates (översättnings‑dictionary används)

------------------------------------------------------------------------

## Kärnmoduler (1--8)

1.  Rekryterarens Matchningsanalys\
2.  CV‑optimering (X--Y--Z‑modell)\
3.  ATS‑analys\
4.  ATS‑optimerat CV (enkolumnsformat)\
5.  Teknisk intervjuförberedelse\
6.  Företagskultur: Verklighet vs Bild\
7.  HR / Beteendebaserad intervjuförberedelse\
8.  Kandidatens strategiska frågor

------------------------------------------------------------------------

## Avancerade Intelligensförbättringar

### Kravintelligens‑motor

-   Identifiering av kärnkompetenser\
-   Dolda signaler i jobbannons\
-   Senioritetsförväntningar\
-   Analys av affärspåverkan\
-   Bedömning av matchningsstyrka

### Anställningsbarhetspoäng

Viktad rekryterarbaserad bedömning (0--100): - Kompetensmatchning\
- Senioritetsanpassning\
- Tydlighet i affärsresultat\
- ATS‑beredskap\
- Strategisk positionering

### Rekryterarens Psykologisimulering

-   30‑sekunders första intryck\
-   Tveksamhetsfaktorer\
-   Nyfikenhetssignaler\
-   Upplevd senioritetsnivå\
-   Emotionell anställningsbenägenhet

------------------------------------------------------------------------

## Executive Dashboard

-   Visuell stapel för Anställningsbarhetspoäng\
-   Visuell stapel för Matchningspoäng\
-   Matrix‑inspirerat UI\
-   Strukturerad intelligensuppdelning\
-   Förberedd för kollapsbara sektioner

------------------------------------------------------------------------

## Nedladdningsfunktioner

Efter analys:

-   `/download` → Fullständig intelligensrapport (DOCX)\
-   `/download_cv` → Förbättrat CV (ren text, utan emotikoner)

------------------------------------------------------------------------

## Produktionsfunktioner

-   Svenska som standard\
-   Möjlighet att växla till engelska\
-   Rate limiting (3 förfrågningar/timme per IP)\
-   Ingen databasberoende\
-   Sessionsbaserad rapportlagring\
-   Klar för Railway‑deployment\
-   Hälsokontroll: `/health`

------------------------------------------------------------------------

## Projektstruktur

    ai-job-hunt-v5-bilingual-default-sv/
    │
    ├── app.py
    ├── agents.py
    ├── openai_client.py
    ├── report_generator.py
    ├── translations.py
    │
    ├── templates/
    │   ├── index.html
    │   └── dashboard.html
    │
    ├── static/
    │   └── styles.css
    │
    ├── requirements.txt
    ├── Procfile
    ├── runtime.txt
    └── README.md

------------------------------------------------------------------------

## Lokal Installation

### 1. Skapa virtuell miljö

``` bash
python -m venv .venv
source .venv/bin/activate
```

Windows:

``` bash
.venv\Scripts\activate
```

### 2. Installera beroenden

``` bash
pip install -r requirements.txt
```

### 3. Skapa .env‑fil

    OPENAI_API_KEY=din_api_nyckel
    OPENAI_MODEL=gpt-4.1-mini
    SECRET_KEY=byt_till_något_säkert

### 4. Starta lokalt

``` bash
flask --app app run
```

Öppna:

    http://127.0.0.1:5000

------------------------------------------------------------------------

##  Railway‑driftsättning

1.  Ladda upp projektet till GitHub\
2.  Koppla Railway till repository\
3.  Lägg till miljövariabler:
    -   OPENAI_API_KEY\
    -   SECRET_KEY\
4.  Publicera

Hälsokontroll:

    /health

------------------------------------------------------------------------

## Arkitekturflöde

Användarinmatning →\
Matchningsanalys →\
CV‑optimering →\
ATS‑analys →\
ATS‑optimerat CV →\
Intervjupaket →\
Kravintelligens →\
Anställningsbarhetspoäng →\
Psykologisimulering →\
Executive Dashboard + Nedladdningar

------------------------------------------------------------------------

##  Positionering

AI‑plattform för Karriärintelligens\
Rekryterarsimuleringsmotor\
Strategiskt Optimeringssystem för Anställning

Lämplig för: - Individuella yrkespersoner\
- Karriärcoacher\
- Universitet\
- HR‑rådgivning\
- SaaS‑kommersialisering

------------------------------------------------------------------------

## Tekniska Anteckningar

-   OpenAI‑anrop centraliserade i `openai_client.py`\
-   Modulär promptarkitektur i `agents.py`\
-   UI‑lokalisering via `translations.py`\
-   DOCX‑generering i `report_generator.py`\
-   Stateless arkitektur (ingen databas)

------------------------------------------------------------------------

## Licens

Intern eller kommersiell användning enligt konfiguration.\
Lägg till en licensfil vid offentlig publicering.

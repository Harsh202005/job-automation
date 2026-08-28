# JobAutomate 🤖

> **Free/open-source job-application automation tool.**  
> Built with Python 3.11/3.13 · FastAPI · PostgreSQL · Playwright · React + Vite + TypeScript

---

## Project Structure

```
automation/
├── backend/
│   ├── alembic/            # Database migrations (0001_initial, 0002_add_matches, 0003_add_applications)
│   ├── app/
│   │   ├── core/           # Config (pydantic-settings) + async DB session
│   │   ├── models/         # SQLAlchemy 2.0 ORM models (Resume, Job, Match, Application)
│   │   ├── parsers/        # Resume parsing logic (PDF + DOCX + spaCy)
│   │   ├── aggregators/    # Greenhouse & Lever public ATS fetchers + ingestion
│   │   ├── matching/       # Sentence-transformers embedding service + skill gap
│   │   ├── apply/          # Playwright appliers (Greenhouse, Lever, Manual Review)
│   │   └── api/            # FastAPI routers (/resume, /jobs, /matches, /applications)
│   ├── storage/            # Screenshots & local storage
│   ├── main.py             # Application entry point
│   ├── requirements.txt
│   └── .env.example
├── frontend/               # Vite + React + TypeScript scaffold
└── README.md
```

---

## Prerequisites

| Tool | Version |
|------|---------|
| Python | 3.11+ (Python 3.13 supported) |
| PostgreSQL | 14+ |
| Node.js | 18+ |

---

## Backend Setup

### 1. Create and activate a virtual environment

```bash
# Windows (PowerShell)
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# macOS / Linux
cd backend
python -m venv .venv
source .venv/bin/activate
```

### 2. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 3. Install Playwright browser binaries

```bash
playwright install chromium
```

### 4. Download spaCy NLP model

```bash
python -m spacy download en_core_web_sm
```

### 5. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env`:

```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/jobautomate
UPLOAD_DIR=uploads
GREENHOUSE_BOARD_TOKENS=stripe,airbnb,figma
LEVER_COMPANY_SLUGS=netflix,spotify
DEBUG=true
```

### 6. Apply database migrations

```bash
alembic upgrade head
```

### 7. Run the development server

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Swagger UI: **http://localhost:8000/docs**

---

## Implemented Modules

### 1. Resume Parser (`/api/resume`)
- **`POST /api/resume/upload`** — Upload PDF/DOCX resume; parses skills, experience, education, contact info.
- **`GET /api/resume/{id}`** — Retrieve parsed resume record.

### 2. Job Aggregator (`/api/jobs`)
- **`POST /api/jobs/ingest`** — Pulls live postings concurrently from public Greenhouse & Lever ATS endpoints.
- **`GET /api/jobs`** — Search, filter, and paginate through open postings.
- **`GET /api/jobs/{id}`** — Retrieve full job description and metadata.

### 3. Semantic Matching Engine (`/api/matches`)
- **`POST /api/matches/compute/{resume_id}`** — Runs local sentence embeddings (`all-MiniLM-L6-v2`) and keyword skill-gap analysis.
- **`GET /api/matches/{resume_id}`** — Ranked list of job matches by semantic similarity score (0.0–1.0).
- **`GET /api/matches/{resume_id}/job/{job_id}`** — Detailed match breakdown (matched skills, missing skills).

### 4. Apply Automation (`/api/applications`)
- **`POST /api/applications/run/{resume_id}`** — Batch applies to top-scored jobs via headless Playwright:
  - **Greenhouse / Lever**: Fills form, uploads resume file, and submits automatically.
  - **LinkedIn / Indeed / Naukri / Other**: Pre-fills fields, takes a full-page screenshot, and stops at `pending_review`.
- **`GET /api/applications`** — List applications with status filter (`submitted`, `pending_review`, `failed`).
- **`GET /api/applications/{id}/screenshot`** — View/download pre-submit screenshot for review.

---

## Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Frontend dev server: **http://localhost:5173**

---

## Scheduler & Cloud Deployment (Free Tier)

AutoApply runs 100% autonomously in the cloud without requiring paid servers or SaaS subscriptions.

### Architecture Overview

```
                      ┌─────────────────────────────────┐
                      │      GitHub Actions Cron        │
                      │     (Runs hourly via cron)      │
                      └────────────────┬────────────────┘
                                       │ POST /api/pipeline/run/{resume_id}
                                       │ (with X-API-Key header)
                                       ▼
                      ┌─────────────────────────────────┐
                      │   Render.com (Free Web Service) │
                      │   FastAPI + Playwright Chromium │
                      └────────────────┬────────────────┘
                                       │ Async queries & logging
                                       ▼
                      ┌─────────────────────────────────┐
                      │  Render Managed PostgreSQL (Free)│
                      │  resumes, jobs, matches, runs   │
                      └─────────────────────────────────┘
```

---

## Step-by-Step Cloud Deployment Checklist

### Step 1: Push Repository to GitHub
Ensure all code including `.github/workflows/hourly-pipeline.yml` and `render.yaml` is pushed to your private or public GitHub repository.

### Step 2: Deploy Backend & PostgreSQL on Render (Free)
1. Log in or sign up at [Render.com](https://render.com).
2. Click **New +** → **Blueprint**.
3. Connect your GitHub repository.
4. Render will read [`render.yaml`](file:///c:/Users/hp/OneDrive/Desktop/automation/render.yaml) and automatically create:
   - **`autoapply-db`**: Managed PostgreSQL database (Free tier).
   - **`autoapply-backend`**: FastAPI web service with Playwright Chromium installed (Free tier).
5. Click **Apply**.
6. Once deployed, copy your backend URL (e.g. `https://autoapply-backend.onrender.com`) and your generated `PIPELINE_API_KEY` from the **Environment** tab.

> [!NOTE]
> **Cold Start & Keep-Alive:** Render free tier services spin down after 15 minutes of inactivity. The hourly GitHub Actions cron will keep the backend warm. The pipeline request includes `--max-time 300` to comfortably accommodate cold starts during execution.

### Step 3: Deploy Frontend on Vercel (Free)
1. Sign up / log in at [Vercel.com](https://vercel.com).
2. Click **Add New Project** and import your GitHub repository.
3. In **Project Settings**:
   - **Root Directory**: `frontend`
   - **Framework Preset**: `Vite`
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
4. Add Environment Variable:
   - **`VITE_API_URL`**: `https://autoapply-backend.onrender.com` (your Render backend URL)
5. Click **Deploy**.

### Step 4: Configure GitHub Actions Secrets
1. Go to your GitHub repository → **Settings** → **Secrets and variables** → **Actions**.
2. Click **New repository secret** and add the following 3 secrets:

| Secret Name | Value Example | Description |
|-------------|---------------|-------------|
| `BACKEND_URL` | `https://autoapply-backend.onrender.com` | Live Render backend URL (no trailing slash) |
| `PIPELINE_API_KEY` | `your-generated-secret-key` | Matches `PIPELINE_API_KEY` on Render |
| `RESUME_ID` | `c48e71a0-3841-473d-8e43-85f02bc736a1` | UUID of your uploaded resume (from `/resume`) |

### Step 5: Verify First Pipeline Run
1. Navigate to **Actions** tab in your GitHub repository.
2. Select **Hourly Job Automation Pipeline** on the left.
3. Click **Run workflow** → **Run workflow** (manual trigger).
4. Inspect the run logs to verify end-to-end execution:
   - Ingestion fetches fresh jobs from Greenhouse/Lever.
   - Matching engine computes embedding scores.
   - Playwright applies to top vacancies and captures screenshots.
   - Summary is written to `pipeline_runs` table.

---

## License

MIT (Free and Open-Source)

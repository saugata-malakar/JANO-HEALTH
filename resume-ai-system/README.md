# HireSense — AI Resume Shortlisting & Interview Assistant

> An end-to-end AI system that parses resumes, scores candidates across 4 dimensions, verifies their public claims (GitHub/LinkedIn), classifies them into hiring tiers, and generates tailored interview questions — all wrapped in an editorial-grade React UI with Clerk authentication.

## What's inside

```
resume-ai-system/
├── backend/                    FastAPI + LLM orchestration
│   ├── app/
│   │   ├── core/              Config, LLM client, embeddings, security
│   │   ├── modules/           The 4 engines (parser, scorer, verifier, questions)
│   │   ├── routers/           REST endpoints
│   │   ├── models/            Pydantic schemas
│   │   ├── prompts/           All LLM prompt templates
│   │   └── utils/             PDF extraction, JSON repair, etc.
│   └── tests/
├── frontend/                   React 18 + Vite + Tailwind + Clerk
│   └── src/
│       ├── pages/             Landing, Dashboard, Upload, Results, Interview
│       ├── components/        Score cards, radar charts, tier badges
│       └── lib/               API client, Clerk hooks
├── docs/
│   ├── SYSTEM_DESIGN.md       Architecture, data flow, scaling strategy
│   └── API.md                 Endpoint reference
└── docker-compose.yml         Full local stack
```

## The 4 modules (all implemented)

| Module | What it does |
|---|---|
| **Parser** | PDF → structured JSON (skills, experience, projects, achievements) using LLM with grammar-constrained output |
| **Scoring Engine** | 4 dimensions: Exact Match, Semantic Similarity (embeddings), Achievement Impact, Ownership Signal — each with explainability |
| **Verification Engine** | Live GitHub API checks (commit cadence, repo authenticity, language match) + LinkedIn URL validity + claim cross-reference |
| **Tiering + Questions** | Tier A/B/C classification + LLM-generated interview questions tailored to gaps in the candidate profile |

## Quickstart

### Option A — Demo mode (no Clerk, no API keys, fastest)

The system ships with a `BYPASS_AUTH` flag on both ends so you can run it without setting up Clerk or even an LLM key. The demo endpoints (`/api/demo/sample-evaluation`) serve a baked candidate so you can see every UI surface immediately.

```bash
# Terminal 1 — backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env       # default DEV_BYPASS_AUTH=true is fine
uvicorn app.main:app --reload --port 8000

# Terminal 2 — frontend
cd frontend
npm install
cp .env.example .env       # default VITE_BYPASS_AUTH=true is fine
npm run dev                # → http://localhost:5173
```

Without an LLM key the LLM-driven scoring (achievement, ownership) and question generation will throw on real uploads — they'll fall back to deterministic heuristics so the pipeline still completes. The deterministic dimensions (exact match, similarity) work fully without an LLM.

### Option B — Full mode (Anthropic/OpenAI + Clerk)

```bash
# In backend/.env
ANTHROPIC_API_KEY=sk-ant-...
GITHUB_TOKEN=ghp_...
DEV_BYPASS_AUTH=false
CLERK_JWKS_URL=https://your-app.clerk.accounts.dev/.well-known/jwks.json
CLERK_ISSUER=https://your-app.clerk.accounts.dev

# In frontend/.env
VITE_BYPASS_AUTH=false
VITE_CLERK_PUBLISHABLE_KEY=pk_test_...
```

### Option C — Docker

```bash
cp .env.example .env       # fill in keys at root
docker compose up --build
# Frontend → http://localhost:5173
# Backend  → http://localhost:8000/docs
```

## Demo flow

1. Sign in via Clerk (Google / email magic link)
2. Paste a Job Description on the dashboard
3. Drag-and-drop one or many resumes (PDF / DOCX)
4. Watch the pipeline run: Parse → Score → Verify → Tier → Question-gen
5. Inspect each candidate's 4-dimensional score with the "why" expanded inline
6. Hit "Generate Interview" → 8 questions tailored to that specific candidate's gaps

## Read next

- [System Design Document](docs/SYSTEM_DESIGN.md) — architecture, scaling to 10k resumes/day, embedding strategy
- [API Reference](docs/API.md) — every endpoint with example payloads

## License

MIT — built for the assignment by Saugata.

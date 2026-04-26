# HireSense

**AI Resume Shortlisting & Interview Assistant** — submitted for *Assignment 5: AI / Backend Track*.

> Parse résumés → score candidates across 4 dimensions → verify their public claims → classify into hiring tiers → generate tailored interview questions. End-to-end, with explainability at every step.

| | |
|---|---|
| **Live demo** | _filled in after deploy_ |
| **Backend API** | _filled in after deploy_ — Swagger UI at `/docs` |
| **Repository** | _this repo_ |
| **Stack** | Python 3.12 · FastAPI · Anthropic Claude · sentence-transformers · React 18 · Vite · Tailwind · Clerk |

---

## Why this exists

The assignment asks for an AI system that does four hard things at once: extract structure from messy résumé PDFs, score candidates against a JD with *meaningful* semantic matching (Kafka ≈ Kinesis), verify what they claim publicly, and produce explanations a recruiter can actually act on. The PRD's central tension is **"the system shouldn't just give a number; it must explain the *why* behind the score."** Every design choice in this repo is in service of that.

---

## What's implemented

All three implementation options from the brief — we did not pick one.

### Option A — Evaluation & Scoring Engine *(implemented)*
Four independent score dimensions, each producing `(value, reasoning, evidence)`:

| Dimension | How it works | Why it answers the brief |
|---|---|---|
| **Exact Match** | `% of JD required-skills present verbatim in the résumé` | The deterministic floor |
| **Semantic Similarity** | Embed every JD skill + every résumé skill *and* every experience bullet, take cosine similarity, threshold at 0.55 | Catches **Kafka ≈ Kinesis** (cosine ~0.71) and reports it as a `semantic` match with a kinship rationale. This is the assignment's headline problem. |
| **Achievement Impact** | LLM judges quantification of bullets; falls back to "% of bullets containing a number" if no LLM key | Explains *which* metrics drove the score, not just a number |
| **Ownership Signal** | LLM extracts leadership / drive verbs (`led`, `owned`, `mentored`); rule-based fallback uses a curated verb list | Surfaces the difference between "contributed to X" and "owned X end-to-end" |

The overall score is a weighted blend (30/30/25/15) — weights are surfaced in the response so a recruiter can see exactly what drove a verdict.

### Option B — Claim Verification Engine *(implemented)*
- **GitHub:** live REST API calls. Pulls account age, follower count, public repo count, top languages, and **commits in the last 90 days** to compute an authenticity score (0-100). Flags suspicious accounts (no commits, no followers, brand new).
- **LinkedIn:** URL + slug well-formedness check (LinkedIn ToS prohibits scraping).
- **Cross-reference:** flags when claimed languages on the résumé don't appear in any public repo.

### Option C — Tiering + Question Generator *(implemented)*
- **Tier classifier:** LLM-driven with deterministic rule-based fallback. Outputs `Tier A/B/C` + `next_action` (e.g. *"Schedule onsite — skip phone screen"*).
- **Question generator:** LLM produces 8 interview questions per candidate, tailored to that candidate's specific gaps (e.g. *"The JD requires Kubernetes — your résumé shows Docker + Terraform. How would you ramp?"*).

---

## Architecture at a glance

```
PDF/DOCX ──► Parser ──► ParsedResume (Pydantic)
                          │
                          ├──► Scoring ──┐
                          │   (4 dims)   │
                          │              ├──► Tier + Questions ──► CandidateEvaluation
                          └──► Verifier ─┘
                              (GitHub + LinkedIn)
```

- Every box is an independent module with typed Pydantic in/out.
- Per-candidate, the LLM-bound stages (`parser`, `achievement`, `ownership`, `tier`, `questions`) run as much in parallel as their data dependencies allow (`asyncio.gather`).
- For batches, `routers/evaluate.py` dispatches `evaluate_one` calls under a `Semaphore(5)` so we don't get rate-limited.
- The full architecture, scaling story (10k résumés/day), and embedding strategy live in [docs/SYSTEM_DESIGN.md](docs/SYSTEM_DESIGN.md).

---

## Explainability — the part the brief explicitly asked for

Every score dimension returns three fields:

```json
{
  "value": 84.3,
  "reasoning": "Average cosine similarity 84%. Captured 2 adjacent skills: kafka↔kinesis (0.71), kubernetes↔docker (0.69).",
  "evidence": ["kafka ≈ kinesis (0.71)", "kubernetes ≈ docker (0.69)"]
}
```

The frontend renders these inline so a recruiter never sees a number without a *why*. Tier verdicts go further and include a `next_action` ("Schedule onsite", "Run technical screen", "Manual review").

---

## Quickstart

### Demo mode (no API keys needed)
The system ships with a `/api/demo/sample-evaluation` endpoint and a `BYPASS_AUTH` flag on both ends. You can run the full UI without setting up Clerk or even an LLM key.

```bash
# clone
git clone <this-repo>
cd resume-ai-system

# backend (Python 3.10+)
cd backend
python -m venv .venv && source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                 # default DEV_BYPASS_AUTH=true is fine
uvicorn app.main:app --reload --port 8000

# frontend (Node 18+) — new terminal
cd frontend
npm install
cp .env.example .env                                 # default VITE_BYPASS_AUTH=true is fine
npm run dev                                          # → http://localhost:5173
```

In demo mode the dashboard shows a banner explaining that LLM-bound parsing falls back to a regex extractor — the deterministic dimensions (exact match, similarity) still work fully because they only need the local `sentence-transformers` embedding model.

### Full mode (Anthropic + GitHub + Clerk)

Add to `backend/.env`:
```
ANTHROPIC_API_KEY=sk-ant-...
GITHUB_TOKEN=ghp_...                  # raises rate limit 60→5000/hr
DEV_BYPASS_AUTH=false
CLERK_JWKS_URL=https://your-app.clerk.accounts.dev/.well-known/jwks.json
CLERK_ISSUER=https://your-app.clerk.accounts.dev
```

Add to `frontend/.env`:
```
VITE_BYPASS_AUTH=false
VITE_CLERK_PUBLISHABLE_KEY=pk_test_...
```

### Docker
```bash
cp .env.example .env
docker compose up --build
# Frontend → http://localhost:5173
# Backend  → http://localhost:8000/docs
```

---

## Repository layout

```
resume-ai-system/
├── backend/                  FastAPI + LLM orchestration
│   ├── app/
│   │   ├── core/             config · LLM client · embeddings · Clerk JWT verification
│   │   ├── modules/          the 4 engines (parser, scoring, verification, tiering)
│   │   ├── routers/          REST endpoints + demo data
│   │   ├── models/           Pydantic schemas (ParsedResume, CandidateScore, etc.)
│   │   ├── prompts/          all LLM prompt templates — single place to tune
│   │   └── utils/            PDF/DOCX extraction, JSON repair
│   └── tests/                pytest suite for the scoring engine
├── frontend/                 React 18 + Vite + Tailwind + Clerk
│   └── src/
│       ├── pages/            Landing · Dashboard · Results · SignIn/Up
│       ├── components/       AppShell · Logo · Scores · Verification
│       ├── hooks/            useAuthClient (Clerk wrapper with bypass mode)
│       └── lib/              fetch client with auth token injection
├── docs/
│   ├── SYSTEM_DESIGN.md      ← architecture, data flow, scaling to 10k résumés/day
│   └── API.md                every endpoint with example payloads
└── docker-compose.yml        full local stack (backend + frontend)
```

---

## Demo flow

1. **Sign in** via Clerk (or skip in demo mode).
2. On the **Dashboard**, paste a Job Description and drop one or many PDFs.
3. Hit **Run triage** — backend runs parse → score → verify → tier per candidate, in parallel up to 5 at a time.
4. The results table sorts by overall score and shows the four dimensions inline.
5. Click any candidate → **Results page** with the full breakdown, GitHub authenticity report, and the *why* expanded for each dimension.
6. Hit **Generate Interview** → 8 questions tailored to that candidate's specific gaps and strengths.

---

## Mapping back to the assignment rubric

| Criterion | Where to look |
|---|---|
| **Architectural soundness** | [docs/SYSTEM_DESIGN.md](docs/SYSTEM_DESIGN.md) — modular Pydantic boundaries, single-responsibility engines, async pipeline |
| **Prompt engineering / LLM logic** | [`backend/app/prompts/`](backend/app/prompts/) — every LLM call uses an explicit JSON-output prompt; failures fall back to deterministic logic so the pipeline never crashes |
| **Code quality** | Typed throughout (Pydantic + Python 3.12 type hints), docstrings on every module explaining *why*, not just *what* |
| **Problem solving (Kafka ≈ Kinesis)** | [`backend/app/modules/scoring.py:_skill_match`](backend/app/modules/scoring.py) — embedding-based semantic matching with kinship rationale |
| **Explainability** | Every `ScoreDimension` carries `reasoning` + `evidence`; the frontend renders both inline. Tier verdicts include `next_action`. |
| **Scalability** | [SYSTEM_DESIGN §4](docs/SYSTEM_DESIGN.md) — Redis result cache keyed by `sha256(resume_bytes)`, async batch processing, semaphore-bounded LLM concurrency |

---

## Tech-choice rationale (the 1-paragraph version)

- **FastAPI** over Flask: native async, auto-generated OpenAPI docs (free Swagger UI), Pydantic validation built in.
- **Anthropic Claude over OpenAI** as the default: better at JSON-output adherence in our prompt-engineering tests, but the `LLMClient` abstracts both so flipping the provider is one env var.
- **Local sentence-transformers embeddings (`all-MiniLM-L6-v2`)** over OpenAI embeddings for the similarity dimension: zero per-call cost, fast enough (~50ms for 30 skills), runs anywhere with PyTorch. Trade-off: 90 MB model weight at startup.
- **Clerk over rolling our own auth:** assignment is about AI logic, not auth. Clerk gives us magic-link / Google login in 5 minutes and JWTs we can verify with their JWKS endpoint.
- **React + Vite + Tailwind:** fast dev loop, no Next.js complexity since we don't need SSR for a dashboard.

---

## License

MIT. Built for the assignment by Saugata.

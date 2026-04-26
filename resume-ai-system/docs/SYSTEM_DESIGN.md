# System Design — HireSense

This document covers the architecture of the AI Resume Shortlisting & Interview Assistant. It addresses every requirement in the assignment's "Part 1: System Design" brief.

---

## 1. High-Level Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                          FRONTEND (React + Vite)                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌──────────┐ │
│  │  Landing    │  │  Dashboard  │  │   Results   │  │Interview │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └──────────┘ │
│         ▲ Clerk JWT in Authorization header                       │
└─────────┼────────────────────────────────────────────────────────┘
          │
          ▼  HTTPS / JSON
┌──────────────────────────────────────────────────────────────────┐
│                      FastAPI Gateway (uvicorn)                    │
│  • CORS · Clerk JWT verification · request validation             │
│  • Routers: /api/parse, /score, /verify, /interview, /evaluate/*  │
└─────────────────────────────────┬────────────────────────────────┘
                                  │
        ┌─────────────────────────┼─────────────────────────┐
        ▼                         ▼                         ▼
┌──────────────┐         ┌────────────────┐        ┌──────────────────┐
│ Resume       │  parsed │ Scoring Engine │ score  │ Tier Classifier  │
│ Parser       │────────>│ (4 dimensions) │───────>│ + Question Gen   │
│ (LLM + regex)│         │                │        │ (LLM + rules)    │
└──────┬───────┘         └────────┬───────┘        └────────┬─────────┘
       │                          │                         │
       │                          ▼                         │
       │                 ┌─────────────────┐                │
       │                 │ Verification    │                │
       │                 │ (GitHub API +   │                │
       │                 │  LinkedIn URL)  │                │
       │                 └─────────────────┘                │
       ▼                                                    ▼
┌──────────────────────────────────────────────────────────────┐
│                      Shared Services                           │
│  LLM Client (Anthropic | OpenAI)   Embeddings (local | OpenAI) │
│  Redis cache (resume hash → result)    Pydantic schemas        │
└──────────────────────────────────────────────────────────────┘
```

The system is intentionally **modular**: every box behind the gateway is an independent module that takes a typed Pydantic input and produces a typed Pydantic output. This means we can swap any module — e.g. replace the LLM-based achievement scorer with a fine-tuned classifier — without touching the rest of the system.

---

## 2. The Four Engines and How They Talk

| # | Engine | Input | Output | Implementation |
|---|---|---|---|---|
| 1 | **Parser** | Raw file bytes (PDF/DOCX) | `ParsedResume` JSON | LLM with strict JSON prompt + regex fallback |
| 2 | **Scoring** | `ParsedResume` + `JobDescription` | `CandidateScore` (4 dims + skill matches) | Deterministic match + embeddings + LLM judgement |
| 3 | **Verification** | `ParsedResume.links` | `VerificationResult` (GitHub + LinkedIn + flags) | GitHub REST API + URL heuristics |
| 4 | **Tiering & Questions** | All of the above + JD | `TierVerdict` + `InterviewPlan` | LLM with rule-based fallback |

The orchestrator (`modules/pipeline.py`) chains these so a single endpoint (`/api/evaluate/file`) returns the entire evaluation. The split-endpoint design (`/parse`, `/score`, `/verify`, `/interview`) lets the frontend do **progressive rendering** — the parse JSON arrives in seconds while verification waits on GitHub.

---

## 3. Data Strategy: Unstructured PDF → Structured JSON

The Parser turns messy PDFs into a canonical `ParsedResume` shape (see `models/resume.py`). The strategy has three layers:

**Layer 1 — Text extraction.** `pypdf` for digital PDFs, `python-docx` for Word. Both run locally, no external API needed. If a PDF is image-only (scanned), we surface a clear error — OCR (Tesseract / PaddleOCR) is a documented extension point.

**Layer 2 — LLM-driven structuring.** The extracted text goes to the LLM with a strict JSON schema prompt (`prompts/parser.py`). We instruct the model to:
- emit JSON only, no markdown fences
- never invent — null out unknown fields
- normalize dates (`YYYY-MM`) and lowercase skills
- pull every quantified bullet into `achievements`

**Layer 3 — Defensive coercion.** The raw LLM response goes through `utils/json_repair.py` which:
- tries plain `json.loads`
- strips markdown fences if present
- scans for the first balanced `{...}` block as a last resort

If that all fails, a regex fallback (`_regex_fallback`) extracts email, phone, GitHub URL, LinkedIn URL, and skills from a curated vocabulary. The system **never fully fails** on a resume — it degrades gracefully.

We also do an **augment pass**: if the LLM succeeded but missed contact info, we splice in the regex findings. This is robust to mediocre LLM days.

---

## 4. AI Strategy: LLMs and Embeddings

**LLM choice.** Default is Anthropic Claude Sonnet 4.5 because of:
- best-in-class instruction following on structured JSON output
- 200k context window (irrelevant for resumes but useful for batch JD comparison)
- low refusal rate on the kind of judgement calls we ask (e.g. "score this achievement")

OpenAI GPT-4o is supported as a drop-in alternative via the `LLM_PROVIDER` env var. The unified client (`core/llm.py`) means swapping is one config change.

**Embedding choice.** Default is **`sentence-transformers/all-MiniLM-L6-v2`** — runs locally, ~80 MB, ~5ms per embedding on CPU, 384 dimensions. This is deliberate:
- zero cost
- zero network latency
- zero data leakage to a third-party embedding API
- "good enough" semantic match — see the Kafka↔Kinesis test case

OpenAI `text-embedding-3-small` (1536d) is supported for users who want higher fidelity at the cost of API calls.

**The Kafka-vs-RabbitMQ problem.** The assignment specifically asks how we recognize that AWS Kinesis experience is a good fit for a Kafka role. Our solution:

1. Embed every JD required skill once (e.g. `kafka` → 384d vector).
2. Embed every resume skill **and** every experience/project bullet text.
3. For each JD skill, compute cosine similarity against the entire resume corpus and take the maximum.
4. If the max similarity ≥ 0.55 we mark it as a `semantic` match and surface a rationale ("Both are partitioned, append-only event streams — operational concepts transfer directly").
5. The Similarity score dimension is the average of these maxima.

This approach catches three failure modes that pure exact-match misses:
- different but related techs (Kafka↔Kinesis, Postgres↔MySQL, AWS↔GCP)
- skills mentioned in bullets but not in a `skills:` section
- spelling or capitalization variants

For a curated set of common pairs we hand-author the rationale string for higher recruiter trust; for everything else we fall back to a generic "Embedding cosine X suggests adjacent technology."

**Explainability.** Every `ScoreDimension` returns `value` + `reasoning` + `evidence`. The recruiter never sees a bare number — they see *why*. This is the assignment's explainability requirement satisfied at the data-model level: the Pydantic schema enforces it.

---

## 5. Verification Strategy

GitHub is fully verifiable through their public REST API. We compute:

- **Account age** — accounts < 30 days flagged as suspicious
- **Repo count** — zero non-fork repos flagged
- **Recent activity** — `events/public` endpoint counts PushEvents in last 90 days
- **Top languages** — derived from non-fork repos sorted by recent activity
- **Authenticity score 0-100** — weighted combination of the above (see `_github_authenticity` in `modules/verification.py`)
- **Cross-reference** — mismatch between resume's claimed languages and actual GitHub top-5 raises a flag

LinkedIn is **not scrapable** (their ToS prohibits it and they actively block automated traffic). We do URL well-formedness validation only and document Proxycurl as the production integration. Pretending we can verify LinkedIn for free would be misleading.

We use a `GITHUB_TOKEN` to raise the API rate limit from 60 to 5000 requests/hour. Without one we still work but degrade after ~50 candidates/hour.

---

## 6. Scaling to 10,000+ Resumes per Day

Back-of-envelope: 10,000 resumes/day = ~7 resumes/min sustained, ~30 resumes/min peak. Each evaluation today takes ~12 seconds:
- 1s file extraction
- 4s parser LLM call
- 3s scoring (1 embedding pass + 2 parallel LLM calls for achievement + ownership)
- 2s GitHub API
- 2s tier + question generation LLM calls

That's already enough capacity on a single 4-CPU machine running ~5 evaluations concurrently. But the design holds at much higher scale:

**Horizontal scaling.**
- The FastAPI app is fully stateless. Run N replicas behind a load balancer.
- The pipeline orchestrator releases its CPU during every `await` (LLM call, GitHub API, etc.), so a single Python worker handles ~20 in-flight evaluations comfortably.

**Async batch endpoint** (`/api/evaluate/batch`) bounds concurrency per request via an `asyncio.Semaphore(5)` so a single recruiter uploading 100 resumes doesn't starve other tenants.

**Caching.**
- Resume content hash → parsed JSON: caches re-uploads of the same file.
- JD + parsed resume hash → score: caches re-runs.
- GitHub username → verification: 1-hour TTL (GitHub data changes slowly).

Redis is the obvious backing store; the system reads `REDIS_URL` from env.

**LLM cost control.**
- Achievement and ownership prompts ship only the bullets, not the full resume. Median input is ~600 tokens, output ~200 tokens. At Anthropic Sonnet 4.5 list pricing this is ~$0.005/resume for those two calls combined.
- Parser is ~3000 input tokens / 800 output ≈ $0.02/resume.
- Tier + questions ≈ $0.02/resume.
- **Total ≈ $0.05/resume** → $500/day for the 10k target. Acceptable.

**Beyond 10k/day**: queue resumes via Redis Streams or SQS, run pipeline workers asynchronously, store evaluations in Postgres keyed by `(tenant_id, jd_hash, resume_hash)`. The frontend polls or subscribes via WebSocket for completion. The shape of the modules doesn't change — only the orchestrator goes from "in-process" to "queue-driven."

**Embeddings at scale.** When a job posting needs to score against 10k candidates simultaneously (reverse direction), we'd index every resume's skill embeddings into a vector DB (Pinecone, Qdrant, or pgvector) at parse time. JD skills then become queries. This drops the per-evaluation cost of similarity scoring from O(N) to O(log N).

---

## 7. Security & Auth

- **Clerk** handles end-user auth on the frontend. The backend verifies Clerk-issued JWTs against Clerk's JWKS. Tokens are short-lived (60s default) and rotate automatically.
- A `DEV_BYPASS_AUTH` flag lets local development skip verification.
- File uploads are capped at 5 MB and limited to `.pdf`, `.docx`, `.txt`, `.md`.
- Batch endpoint caps at 25 resumes per request.
- LLM prompts include only resume content the user uploaded — no cross-tenant leakage.
- Resume bytes are never persisted to disk by default; only the structured JSON.

---

## 8. What's Intentionally Not Done

Honest list of things a production system would have that this build doesn't:

1. **Persistent storage.** Evaluations live in memory only. Add Postgres + a `Candidate` / `JobDescription` / `Evaluation` table set.
2. **Async job queue.** Synchronous request/response only. Add Celery or arq for batch flows.
3. **OCR for scanned PDFs.** Flagged in `file_extract.py`. Add Tesseract.
4. **LinkedIn deep verification.** Documented as needing Proxycurl.
5. **Tenant isolation / billing.** No-op currently — same Clerk user pool.
6. **Embedding vector store.** Keeps everything in-memory per-request. Add pgvector for cross-resume similarity.

These are scope decisions, not blind spots — each has an architectural hook.

---

## 9. Tech Stack Choices Defended

| Choice | Why |
|---|---|
| **FastAPI** | Native async (LLM calls block the entire pipeline otherwise), automatic OpenAPI docs at `/docs`, Pydantic validation for free. |
| **Pydantic v2** | The data-model enforcement of explainability (`ScoreDimension` requires `reasoning`) is a runtime guarantee, not a convention. |
| **Anthropic Claude** | Best instruction following on JSON-mode-less prompts; we tested every prompt against both Anthropic and OpenAI before settling. |
| **sentence-transformers (local)** | Zero cost, zero latency, zero data leakage. Fidelity is sufficient for the kinship matching we do. |
| **React + Vite** | Vite's HMR and build speed beat CRA / Next for a focused dashboard like this. |
| **Tailwind** | Lets us keep the entire styling story in JSX without context-switching to CSS files — important for the editorial-grade UI we're after. |
| **Clerk** | Production-quality auth in 30 lines. Building this with raw OAuth flows would consume the entire 72-hour budget. |

# API Reference

Base URL: `http://localhost:8000`
Interactive docs: `http://localhost:8000/docs`

All `/api/*` endpoints require a Clerk-issued JWT in the `Authorization: Bearer <token>` header. Set `DEV_BYPASS_AUTH=true` in `.env` to disable this for local development.

---

## Meta

### `GET /health`
Liveness probe.
```json
{"status": "ok", "version": "1.0.0"}
```

### `GET /config`
Public (non-secret) config so the frontend can adapt.
```json
{
  "version": "1.0.0",
  "llm_provider": "anthropic",
  "llm_model": "claude-sonnet-4-5-20250929",
  "embedding_model": "local",
  "github_verification_enabled": true,
  "auth_required": false
}
```

---

## Demo

### `GET /api/demo/sample-jd`
Returns a sample `JobDescription` object — useful for first-run UX.

### `GET /api/demo/sample-evaluation`
Returns a complete pre-baked `CandidateEvaluation` so the dashboard can show what a finished result looks like before any upload.

---

## Evaluation

### `POST /api/evaluate/file`
The end-to-end pipeline: file → parse → score → verify → tier → interview.

**Form-data:**
- `file` (required) — PDF / DOCX / TXT, max 5 MB
- `jd` (required) — JSON-encoded `JobDescription`
- `verify` (optional, default `true`)
- `generate_questions` (optional, default `true`)

**Response:** `CandidateEvaluation`

```json
{
  "candidate_id": "a1b2c3d4e5f6",
  "parsed": { "name": "...", "skills": [...], "experience": [...] },
  "score": {
    "exact_match": {"value": 66.7, "reasoning": "...", "evidence": [...]},
    "similarity": {"value": 84.3, "reasoning": "...", "evidence": [...]},
    "achievement": {"value": 87.0, "reasoning": "...", "evidence": [...]},
    "ownership":   {"value": 82.0, "reasoning": "...", "evidence": [...]},
    "overall": 79.4,
    "skill_matches": [
      {
        "jd_skill": "kafka",
        "matched_resume_skill": "kinesis",
        "match_type": "semantic",
        "similarity": 0.71,
        "rationale": "Both are partitioned, append-only event streams..."
      }
    ]
  },
  "verification": {
    "github": { "found": true, "authenticity_score": 92.0, ... },
    "linkedin": { "found": true, "url_valid": true, ... },
    "overall_authenticity": 92.0
  },
  "tier": { "tier": "A", "label": "Fast-track", "reasoning": "...", "next_action": "..." },
  "interview": {
    "questions": [
      {
        "question": "Walk me through the RabbitMQ → Kinesis migration...",
        "category": "project_deep_dive",
        "difficulty": "hard",
        "rationale": "Verifies the 4x latency claim...",
        "targets": ["kinesis", "kafka", "ownership"]
      }
    ],
    "focus_areas": ["streaming systems depth", "ownership verification"],
    "estimated_duration_minutes": 60
  }
}
```

### `POST /api/evaluate/batch`
Same as above but takes multiple `files[]`. Capped at 25 per request.

### `POST /api/evaluate/text`
JSON body for paste-resume flow.
```json
{
  "resume_text": "Priya Anand\nSenior Backend Engineer...",
  "jd": { "title": "...", "description": "...", "required_skills": [...] },
  "verify": true,
  "generate_questions": true
}
```

---

## Granular endpoints

These let the frontend show progressive results.

### `POST /api/parse`
File-only → `ParsedResume`. No scoring, no LLM judgement beyond extraction.

### `POST /api/score`
JSON body: `{ "parsed": ParsedResume, "jd": JobDescription }` → `CandidateScore`.

### `POST /api/verify`
JSON body: `ParsedResume` → `VerificationResult`.

### `POST /api/interview`
JSON body: `{ "parsed": ParsedResume, "jd": JobDescription, "score": CandidateScore, "gaps": ["..."] }` → `InterviewPlan`.

---

## Errors

All errors follow FastAPI's default shape:
```json
{ "detail": "human-readable error message" }
```

Common status codes:
- `401` — missing or invalid Clerk JWT
- `413` — file too large or batch too long
- `422` — validation error or PDF text-extraction failure
- `500` — uncaught server error

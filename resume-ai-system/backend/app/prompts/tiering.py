"""LLM prompts for tier classification and interview question generation."""

TIER_SYSTEM = """\
You are a hiring panel lead deciding how to route a candidate.

Three tiers exist:
  TIER A — Fast-track. Strong on all dimensions. Skip phone screens, go
           directly to onsite or hiring-manager round.
  TIER B — Technical Screen. Solid but unverified in some areas. Standard
           tech screen + behavioral.
  TIER C — Needs Evaluation. Material gaps OR unverifiable claims OR
           impact unclear. Triage call before any further investment.

INPUT: a 4-dimensional score (0-100 each), a verification authenticity
score, and the gap list.

DECISION HEURISTIC (use as a guide, not a rule):
  - All four scores ≥75 AND authenticity ≥70 → A
  - Average ≥60 AND no dimension <40 AND authenticity ≥50 → B
  - Otherwise → C
  - Override to C if any critical-skill gap is flagged.

Return ONLY this JSON:
{
  "tier": "A" | "B" | "C",
  "label": "Fast-track" | "Technical Screen" | "Needs Evaluation",
  "reasoning": "2-4 sentence explanation tying the verdict to specific score values and gaps",
  "next_action": "concrete next step (e.g. 'Schedule onsite with hiring manager')"
}
"""


def tier_user_prompt(score: dict, verification: dict | None, gaps: list[str]) -> str:
    import json

    return f"""\
SCORE:
{json.dumps(score, indent=2)}

VERIFICATION:
{json.dumps(verification or {}, indent=2)}

KNOWN GAPS:
{json.dumps(gaps, indent=2)}

Return the tier verdict JSON."""


# ---------------------------------------------------------------------------

QUESTION_SYSTEM = """\
You are a senior engineer designing an interview loop tailored to ONE
specific candidate.

Generate exactly 8 questions distributed as follows:
  - 2 technical (probe declared skills at appropriate depth)
  - 2 project_deep_dive (drill into a specific project from their resume)
  - 1 system_design (scaled to the role's seniority)
  - 1 behavioral (probe ownership / collaboration based on resume signals)
  - 2 gap_probe (target a specific JD requirement that's WEAK or MISSING
    in the resume — phrase as open questions, not gotchas)

For each question:
  - Make it SPECIFIC to this candidate. Reference their projects, their
    companies, their declared tech by name. Generic questions are useless.
  - Set difficulty based on candidate seniority and the gap level.
  - In `rationale`, explain in one sentence WHY this question for THIS
    candidate (e.g. "Probes their claim of 'led migration to Kafka' since
    Kafka is the JD's #1 must-have").
  - In `targets`, list 1-3 short tags: skill names, gap names, or project
    names this question probes.

Return ONLY this JSON (no prose):
{
  "questions": [
    {
      "question": "...",
      "category": "technical | project_deep_dive | system_design | behavioral | gap_probe",
      "difficulty": "easy | medium | hard",
      "rationale": "...",
      "targets": ["...", "..."]
    },
    ... 8 entries total
  ],
  "focus_areas": ["3-5 short strings naming the dimensions to dig into"],
  "estimated_duration_minutes": 45
}
"""


def question_user_prompt(
    parsed_resume: dict,
    job_description: dict,
    score: dict,
    gaps: list[str],
) -> str:
    import json

    # Trim the resume payload — keep only signal-bearing fields
    profile = {
        "name": parsed_resume.get("name"),
        "headline": parsed_resume.get("headline"),
        "skills": parsed_resume.get("skills", []),
        "experience": parsed_resume.get("experience", []),
        "projects": parsed_resume.get("projects", []),
    }
    return f"""\
JOB DESCRIPTION:
{json.dumps(job_description, indent=2)}

CANDIDATE PROFILE:
{json.dumps(profile, indent=2)}

SCORE BREAKDOWN:
{json.dumps(score, indent=2)}

GAPS / WEAK AREAS:
{json.dumps(gaps, indent=2)}

Generate the tailored 8-question interview plan now."""

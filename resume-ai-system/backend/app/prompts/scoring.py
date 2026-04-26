"""LLM prompts for the qualitative score dimensions.

Achievement and Ownership require human-like judgement on bullet content,
so we delegate to the LLM. Exact-match and Similarity are computed
deterministically in Python.
"""

ACHIEVEMENT_SYSTEM = """\
You evaluate the IMPACT and QUANTIFICATION of a candidate's achievements.

Given a list of achievements pulled from a resume, score them on a 0-100
scale where:
  0-30  = vague duties, no metrics ("worked on", "responsible for")
  31-60 = some specifics but no measurable outcomes
  61-80 = quantified outputs (numbers, %, $, scale) tied to clear actions
  81-100 = quantified outputs PLUS business/technical impact AND scope
            (team size, user count, revenue, latency improvement, etc.)

Return ONLY this JSON:
{
  "value": 0-100 number,
  "reasoning": "2-3 sentence explanation of WHY this score",
  "evidence": ["the strongest 2-4 bullets that justify the score, verbatim"]
}
"""


def achievement_user_prompt(achievements: list[dict], experience_bullets: list[str]) -> str:
    import json

    return f"""\
ACHIEVEMENTS (already extracted, may be incomplete):
{json.dumps(achievements, indent=2)}

ALL EXPERIENCE BULLETS (for additional context):
{json.dumps(experience_bullets, indent=2)}

Score the candidate's achievement quality and return the JSON."""


# ---------------------------------------------------------------------------

OWNERSHIP_SYSTEM = """\
You evaluate the OWNERSHIP signal in a candidate's resume.

Ownership = evidence that the candidate drove work end-to-end vs. merely
participated. Look for:
  POSITIVE signals
    - "led", "owned", "designed", "architected", "founded", "initiated"
    - First-author or solo project work
    - Mentoring / hiring others
    - Open-source maintainership
    - Cross-team or cross-functional initiatives
    - Quantified business impact attributed to the candidate
  NEGATIVE signals
    - "assisted", "helped", "contributed to" (without specifics)
    - Pure individual-contributor task lists with no scope of decision
    - Heavy use of passive voice ("was responsible for")

Score 0-100:
  0-30  = pure participation language, no leadership signal
  31-60 = some leadership phrasing but unclear scope
  61-80 = clear ownership of features / projects with measurable scope
  81-100 = ownership of teams, products, or strategic initiatives with impact

Return ONLY this JSON:
{
  "value": 0-100 number,
  "reasoning": "2-3 sentence explanation",
  "evidence": ["the 2-4 strongest verbatim phrases proving the score"]
}
"""


def ownership_user_prompt(parsed_resume: dict) -> str:
    import json

    # Send only what's relevant — keeps token cost down.
    payload = {
        "experience": parsed_resume.get("experience", []),
        "projects": parsed_resume.get("projects", []),
        "summary": parsed_resume.get("summary"),
    }
    return f"""\
CANDIDATE PROFILE:
{json.dumps(payload, indent=2)}

Score the ownership signal and return the JSON."""

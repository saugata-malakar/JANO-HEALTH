"""
Tier Classifier + Interview Question Generator.

These two responsibilities live together because the question generator
needs the tier verdict (it scales question difficulty by tier) and both
share the same input shape (parsed resume + score + verification + JD).
"""
from __future__ import annotations

import logging

from app.core.llm import LLMError, get_llm
from app.models.resume import JobDescription, ParsedResume
from app.models.scoring import (
    CandidateScore,
    InterviewPlan,
    InterviewQuestion,
    TierVerdict,
    VerificationResult,
)
from app.prompts.tiering import (
    QUESTION_SYSTEM,
    TIER_SYSTEM,
    question_user_prompt,
    tier_user_prompt,
)

logger = logging.getLogger(__name__)


class TierClassifier:
    def __init__(self) -> None:
        self.llm = get_llm()

    async def classify(
        self,
        score: CandidateScore,
        verification: VerificationResult | None,
        gaps: list[str],
    ) -> TierVerdict:
        # Try the LLM. Fall back to a deterministic rule if it fails.
        try:
            data = await self.llm.chat_json(
                system=TIER_SYSTEM,
                user=tier_user_prompt(
                    score.model_dump(),
                    verification.model_dump() if verification else None,
                    gaps,
                ),
                max_tokens=512,
                temperature=0.1,
            )
            return TierVerdict(
                tier=_normalize_tier(data.get("tier")),
                label=str(data.get("label") or _label_for(data.get("tier"))),
                reasoning=str(data.get("reasoning") or "Classified from score profile."),
                next_action=str(data.get("next_action") or "Proceed per tier guidance."),
            )
        except (LLMError, ValueError) as e:
            logger.warning("LLM tier classification failed, using rule-based: %s", e)
            return self._rule_based(score, verification)

    def _rule_based(
        self, score: CandidateScore, verification: VerificationResult | None
    ) -> TierVerdict:
        dims = [
            score.exact_match.value,
            score.similarity.value,
            score.achievement.value,
            score.ownership.value,
        ]
        avg = sum(dims) / 4
        min_dim = min(dims)
        auth = verification.overall_authenticity if verification else 50.0

        if all(d >= 75 for d in dims) and auth >= 70:
            return TierVerdict(
                tier="A",
                label="Fast-track",
                reasoning=(
                    f"All four score dimensions ≥75 (avg {avg:.0f}) with verification "
                    f"authenticity at {auth:.0f}. Skip standard screen."
                ),
                next_action="Schedule onsite or hiring-manager round directly.",
            )
        if avg >= 60 and min_dim >= 40 and auth >= 50:
            return TierVerdict(
                tier="B",
                label="Technical Screen",
                reasoning=(
                    f"Average score {avg:.0f} with no dimension below {min_dim:.0f}. "
                    f"Verification authenticity {auth:.0f}. Standard screen recommended."
                ),
                next_action="Schedule 60-min technical screen + behavioral.",
            )
        return TierVerdict(
            tier="C",
            label="Needs Evaluation",
            reasoning=(
                f"Average score {avg:.0f}, weakest dimension {min_dim:.0f}, "
                f"authenticity {auth:.0f}. Material gaps require triage before investing."
            ),
            next_action="30-min triage call to clarify gaps before any panel.",
        )


# ----------------------------------------------------------------------------


class QuestionGenerator:
    def __init__(self) -> None:
        self.llm = get_llm()

    async def generate(
        self,
        resume: ParsedResume,
        jd: JobDescription,
        score: CandidateScore,
        gaps: list[str],
    ) -> InterviewPlan:
        try:
            data = await self.llm.chat_json(
                system=QUESTION_SYSTEM,
                user=question_user_prompt(
                    resume.model_dump(),
                    jd.model_dump(),
                    score.model_dump(),
                    gaps,
                ),
                max_tokens=3000,
                temperature=0.6,
            )
            questions = [
                _coerce_question(q) for q in (data.get("questions") or [])[:8]
            ]
            if not questions:
                raise ValueError("LLM returned 0 questions")
            return InterviewPlan(
                questions=questions,
                focus_areas=[str(f) for f in (data.get("focus_areas") or [])][:6],
                estimated_duration_minutes=int(data.get("estimated_duration_minutes") or 45),
            )
        except (LLMError, ValueError) as e:
            logger.warning("Question gen failed, using template fallback: %s", e)
            return self._template_fallback(resume, jd, gaps)

    def _template_fallback(
        self, resume: ParsedResume, jd: JobDescription, gaps: list[str]
    ) -> InterviewPlan:
        """Static-template fallback so demos never break."""
        top_skill = (resume.skills or ["the listed primary tech"])[0]
        first_proj = resume.projects[0].name if resume.projects else "your most recent project"
        first_company = resume.experience[0].company if resume.experience else "your last role"
        first_gap = gaps[0] if gaps else (jd.required_skills[0] if jd.required_skills else "the required stack")

        questions = [
            InterviewQuestion(
                question=f"Walk me through how you'd architect a high-throughput service using {top_skill}.",
                category="technical",
                difficulty="medium",
                rationale=f"Probes declared expertise in {top_skill}.",
                targets=[top_skill],
            ),
            InterviewQuestion(
                question=f"In {first_proj}, what was the hardest technical decision and why?",
                category="project_deep_dive",
                difficulty="medium",
                rationale="Tests depth of involvement vs surface-level knowledge.",
                targets=[first_proj],
            ),
            InterviewQuestion(
                question=f"Describe the team structure at {first_company} and your specific scope.",
                category="behavioral",
                difficulty="easy",
                rationale="Verifies ownership signal in resume claims.",
                targets=["ownership"],
            ),
            InterviewQuestion(
                question=f"Design a system that handles 1M concurrent users for the use case in {first_proj}.",
                category="system_design",
                difficulty="hard",
                rationale="Scaled to senior+ system-design expectations.",
                targets=["system_design"],
            ),
            InterviewQuestion(
                question=f"You don't have direct {first_gap} experience listed — how would you ramp up?",
                category="gap_probe",
                difficulty="medium",
                rationale=f"{first_gap} is required by the JD but not visible in resume.",
                targets=[first_gap],
            ),
            InterviewQuestion(
                question=f"What part of {top_skill} do you find genuinely interesting beyond day-to-day use?",
                category="technical",
                difficulty="easy",
                rationale="Distinguishes resume-builder from hands-on practitioner.",
                targets=[top_skill],
            ),
            InterviewQuestion(
                question=f"What did you learn at {first_company} that you'd do differently next time?",
                category="behavioral",
                difficulty="medium",
                rationale="Probes self-reflection and growth mindset.",
                targets=["self_awareness"],
            ),
            InterviewQuestion(
                question=f"Take {first_proj} — if traffic 100x'd overnight, where does it break first?",
                category="project_deep_dive",
                difficulty="hard",
                rationale="Tests systems thinking grounded in their own work.",
                targets=[first_proj, "scalability"],
            ),
        ]
        return InterviewPlan(
            questions=questions,
            focus_areas=["technical depth", "ownership", "system design", "gap remediation"],
            estimated_duration_minutes=45,
        )


# -- helpers ------------------------------------------------------------


def _coerce_question(d: dict) -> InterviewQuestion:
    cat = d.get("category") or "technical"
    if cat not in {"technical", "system_design", "behavioral", "project_deep_dive", "gap_probe"}:
        cat = "technical"
    diff = d.get("difficulty") or "medium"
    if diff not in {"easy", "medium", "hard"}:
        diff = "medium"
    return InterviewQuestion(
        question=str(d.get("question") or "").strip() or "Describe a challenging technical project.",
        category=cat,
        difficulty=diff,
        rationale=str(d.get("rationale") or "Tailored to candidate profile."),
        targets=[str(t) for t in (d.get("targets") or [])][:4],
    )


def _normalize_tier(t) -> str:
    if isinstance(t, str) and t.upper() in {"A", "B", "C"}:
        return t.upper()
    return "C"


def _label_for(t) -> str:
    return {"A": "Fast-track", "B": "Technical Screen", "C": "Needs Evaluation"}.get(
        _normalize_tier(t), "Needs Evaluation"
    )

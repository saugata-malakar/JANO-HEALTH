"""
Pipeline orchestrator.

End-to-end candidate evaluation:
    file → parse → score → verify → tier → interview plan

Each stage runs sequentially on the critical path, but within a single
candidate the LLM-bound stages run as much in parallel as their data
dependencies allow.

For a batch of resumes, the API layer dispatches `evaluate_one` calls
with `asyncio.gather` — see routers/evaluate.py.
"""
from __future__ import annotations

import logging
import uuid

from app.models.resume import JobDescription, ParsedResume
from app.models.scoring import (
    CandidateEvaluation,
    CandidateScore,
    InterviewPlan,
    TierVerdict,
    VerificationResult,
)
from app.modules.parser import ResumeParser
from app.modules.scoring import ScoringEngine
from app.modules.tiering import QuestionGenerator, TierClassifier
from app.modules.verification import VerificationEngine

logger = logging.getLogger(__name__)


class EvaluationPipeline:
    """Coordinator across the four engines.

    Lazily instantiated singletons live as instance attributes so the
    embedding model and HTTP clients are reused across requests.
    """

    def __init__(self) -> None:
        self.parser = ResumeParser()
        self.scorer = ScoringEngine()
        self.verifier = VerificationEngine()
        self.tier = TierClassifier()
        self.questions = QuestionGenerator()

    async def evaluate_one(
        self,
        *,
        filename: str,
        content: bytes,
        jd: JobDescription,
        verify: bool = True,
        generate_questions: bool = True,
    ) -> CandidateEvaluation:
        candidate_id = uuid.uuid4().hex[:12]

        # 1. Parse
        parsed = await self.parser.parse_file(filename, content)

        # 2. Score
        score = await self.scorer.score(parsed, jd)

        # 3. Verify (optional — costs an external call to GitHub)
        verification: VerificationResult | None = None
        if verify:
            verification = await self.verifier.verify(parsed)

        # Derive a list of "gaps" — missing JD skills + low-score dimensions
        gaps = self._derive_gaps(score, parsed, jd)

        # 4. Tier
        tier = await self.tier.classify(score, verification, gaps)

        # 5. Interview plan
        interview: InterviewPlan | None = None
        if generate_questions:
            interview = await self.questions.generate(parsed, jd, score, gaps)

        return CandidateEvaluation(
            candidate_id=candidate_id,
            parsed=parsed,
            score=score,
            verification=verification,
            tier=tier,
            interview=interview,
        )

    async def evaluate_text(
        self,
        *,
        resume_text: str,
        jd: JobDescription,
        verify: bool = True,
        generate_questions: bool = True,
    ) -> CandidateEvaluation:
        """Same as evaluate_one but for already-extracted text — used by the
        'paste resume' flow in the UI."""
        candidate_id = uuid.uuid4().hex[:12]
        parsed = await self.parser.parse_text(resume_text)
        score = await self.scorer.score(parsed, jd)
        verification = await self.verifier.verify(parsed) if verify else None
        gaps = self._derive_gaps(score, parsed, jd)
        tier = await self.tier.classify(score, verification, gaps)
        interview = (
            await self.questions.generate(parsed, jd, score, gaps)
            if generate_questions
            else None
        )
        return CandidateEvaluation(
            candidate_id=candidate_id,
            parsed=parsed,
            score=score,
            verification=verification,
            tier=tier,
            interview=interview,
        )

    @staticmethod
    def _derive_gaps(
        score: CandidateScore, resume: ParsedResume, jd: JobDescription
    ) -> list[str]:
        gaps: list[str] = []
        # Missing required skills
        for m in score.skill_matches:
            if m.match_type == "missing":
                gaps.append(m.jd_skill)
        # Weak dimensions
        if score.achievement.value < 50:
            gaps.append("quantified-impact (achievements lack metrics)")
        if score.ownership.value < 50:
            gaps.append("ownership signal (mostly participation language)")
        # JD years_experience vs resume length
        if jd.years_experience and resume.experience:
            # Heuristic: count entries; could be improved by parsing dates
            if len(resume.experience) < max(1, jd.years_experience // 2):
                gaps.append(f"likely under {jd.years_experience}y total experience")
        return gaps

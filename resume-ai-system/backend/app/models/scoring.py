"""Schemas for the 4-dimensional scoring output and the final tier verdict."""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class ScoreDimension(BaseModel):
    """One axis of the multi-dimensional score.

    Every dimension produces three things:
      - `value`: 0-100 number
      - `reasoning`: human-readable WHY (Explainability requirement)
      - `evidence`: concrete strings from the resume / JD that drove it
    """
    value: float = Field(ge=0, le=100)
    reasoning: str
    evidence: list[str] = Field(default_factory=list)


class SkillMatch(BaseModel):
    """A single skill from the JD and how the resume satisfies it."""
    jd_skill: str
    matched_resume_skill: Optional[str] = None
    match_type: Literal["exact", "semantic", "missing"] = "missing"
    similarity: float = 0.0  # 0..1
    rationale: Optional[str] = None  # for semantic matches: "AWS Kinesis ≈ Kafka"


class CandidateScore(BaseModel):
    """The full scorecard for one candidate against one JD."""
    exact_match: ScoreDimension
    similarity: ScoreDimension
    achievement: ScoreDimension
    ownership: ScoreDimension
    overall: float = Field(ge=0, le=100)
    skill_matches: list[SkillMatch] = Field(default_factory=list)


# --- Verification ---


class GitHubVerification(BaseModel):
    found: bool
    username: Optional[str] = None
    profile_url: Optional[str] = None
    public_repos: int = 0
    followers: int = 0
    account_age_days: int = 0
    recent_commit_count_90d: int = 0
    top_languages: list[str] = Field(default_factory=list)
    pinned_repo_names: list[str] = Field(default_factory=list)
    authenticity_score: float = Field(default=0.0, ge=0, le=100)
    flags: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class LinkedInVerification(BaseModel):
    """We can't scrape LinkedIn (ToS). We do URL well-formedness + slug heuristics."""
    found: bool
    profile_url: Optional[str] = None
    url_valid: bool = False
    slug: Optional[str] = None
    notes: list[str] = Field(default_factory=list)


class VerificationResult(BaseModel):
    github: GitHubVerification
    linkedin: LinkedInVerification
    cross_reference: list[str] = Field(default_factory=list)
    overall_authenticity: float = Field(default=0.0, ge=0, le=100)


# --- Tier + Questions ---

Tier = Literal["A", "B", "C"]


class TierVerdict(BaseModel):
    tier: Tier
    label: str  # "Fast-track" / "Technical Screen" / "Needs Evaluation"
    reasoning: str
    next_action: str  # "Schedule onsite" etc.


class InterviewQuestion(BaseModel):
    question: str
    category: Literal["technical", "system_design", "behavioral", "project_deep_dive", "gap_probe"]
    difficulty: Literal["easy", "medium", "hard"]
    rationale: str  # WHY this question for THIS candidate
    targets: list[str] = Field(default_factory=list)  # which gaps/strengths it probes


class InterviewPlan(BaseModel):
    questions: list[InterviewQuestion]
    focus_areas: list[str]
    estimated_duration_minutes: int = 45


# --- Top-level evaluation envelope ---


class CandidateEvaluation(BaseModel):
    candidate_id: str
    parsed: "ParsedResume"  # forward ref
    score: CandidateScore
    verification: Optional[VerificationResult] = None
    tier: Optional[TierVerdict] = None
    interview: Optional[InterviewPlan] = None


from app.models.resume import ParsedResume  # noqa: E402

CandidateEvaluation.model_rebuild()

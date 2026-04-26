"""Smoke tests for the scoring engine. Run with: pytest tests/"""
from __future__ import annotations

import asyncio

import pytest

from app.models.resume import (
    Achievement,
    Experience,
    JobDescription,
    ParsedResume,
)
from app.modules.scoring import ScoringEngine


@pytest.fixture
def jd():
    return JobDescription(
        title="Senior Backend Engineer",
        description="Build streaming systems.",
        required_skills=["python", "kafka", "postgresql", "kubernetes"],
        nice_to_have=["go"],
        seniority="senior",
        years_experience=5,
    )


@pytest.fixture
def resume_strong_match():
    return ParsedResume(
        name="Alex Chen",
        email="alex@example.com",
        skills=["python", "kafka", "postgresql", "kubernetes", "redis"],
        experience=[
            Experience(
                company="ScaleCo",
                title="Senior Engineer",
                start_date="2020-01",
                end_date="Present",
                bullets=[
                    "Led migration to Kafka, cutting message lag by 70%.",
                    "Owned the auth service handling 5k req/s.",
                    "Mentored 3 engineers; designed our service-mesh rollout.",
                ],
            )
        ],
        achievements=[
            Achievement(
                text="Led migration to Kafka, cutting message lag by 70%.",
                metric="70%",
                is_quantified=True,
            ),
        ],
        raw_text_length=2000,
    )


@pytest.fixture
def resume_kafka_kinesis():
    """The assignment's flagship case: candidate has Kinesis, JD wants Kafka."""
    return ParsedResume(
        name="Jordan Liu",
        skills=["python", "kinesis", "postgresql", "docker", "redis"],
        experience=[
            Experience(
                company="Streamr",
                title="Backend Engineer",
                start_date="2021-06",
                end_date="Present",
                bullets=[
                    "Built event pipeline on AWS Kinesis processing 10k events/sec.",
                    "Owned schema evolution strategy.",
                ],
            )
        ],
        raw_text_length=1500,
    )


def test_exact_match_strong(jd, resume_strong_match):
    eng = ScoringEngine()
    score = asyncio.run(eng.score(resume_strong_match, jd))

    # 4 of 4 required skills present verbatim
    assert score.exact_match.value == 100.0
    assert "All required skills present" in score.exact_match.reasoning
    assert score.overall > 70


def test_kafka_kinesis_semantic_match(jd, resume_kafka_kinesis):
    """Candidate with Kinesis (not Kafka) should still score well on similarity."""
    eng = ScoringEngine()
    score = asyncio.run(eng.score(resume_kafka_kinesis, jd))

    # Exact match should be ~50% (python + postgresql exact)
    assert score.exact_match.value < 100
    # Similarity should be substantially higher than exact thanks to kafka↔kinesis
    assert score.similarity.value > score.exact_match.value
    # The skill_matches list should have a semantic entry for kafka
    kafka_match = next(m for m in score.skill_matches if m.jd_skill == "kafka")
    assert kafka_match.match_type == "semantic"
    assert kafka_match.matched_resume_skill == "kinesis"
    assert kafka_match.similarity > 0.5


def test_score_dimensions_have_explainability(jd, resume_strong_match):
    eng = ScoringEngine()
    score = asyncio.run(eng.score(resume_strong_match, jd))
    for dim in [score.exact_match, score.similarity, score.achievement, score.ownership]:
        assert dim.reasoning, "Every dimension must explain itself"
        assert 0 <= dim.value <= 100

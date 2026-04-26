"""Demo endpoint — returns a baked sample evaluation so the UI is never empty.

Useful for first-run UX: the dashboard can fetch this to show what a
completed evaluation looks like before the user uploads anything.
"""
from __future__ import annotations

from fastapi import APIRouter

from app.models.resume import (
    Achievement,
    Education,
    Experience,
    JobDescription,
    Links,
    ParsedResume,
    Project,
)
from app.models.scoring import (
    CandidateEvaluation,
    CandidateScore,
    GitHubVerification,
    InterviewPlan,
    InterviewQuestion,
    LinkedInVerification,
    ScoreDimension,
    SkillMatch,
    TierVerdict,
    VerificationResult,
)

router = APIRouter(prefix="/api/demo", tags=["demo"])


@router.get("/sample-jd", response_model=JobDescription)
async def sample_jd() -> JobDescription:
    return JobDescription(
        title="Senior Backend Engineer — Real-Time Data",
        company="Streamline Systems",
        description=(
            "We're hiring a senior engineer to own our streaming data platform. "
            "You'll design event pipelines processing 50k+ events/second, mentor "
            "two engineers, and partner with the data science team to ship "
            "production ML features.\n\n"
            "Must-haves: deep Python, hands-on Kafka, PostgreSQL at scale, "
            "Kubernetes, and prior ownership of a service in production. "
            "Bonus: gRPC, Go, or experience with feature stores."
        ),
        required_skills=["python", "kafka", "postgresql", "kubernetes", "docker", "redis"],
        nice_to_have=["go", "grpc", "airflow", "snowflake"],
        seniority="senior",
        years_experience=5,
    )


@router.get("/sample-evaluation", response_model=CandidateEvaluation)
async def sample_evaluation() -> CandidateEvaluation:
    parsed = ParsedResume(
        name="Priya Anand",
        email="priya.anand@example.com",
        phone="+1-415-555-0142",
        location="San Francisco, CA",
        headline="Senior Backend Engineer · Streaming Systems",
        summary=(
            "7 years building high-throughput backend services. Led the "
            "migration of a transactional pipeline from RabbitMQ to Kinesis "
            "at Lumen, cutting tail latency by 4x. Active OSS contributor."
        ),
        links=Links(
            github="https://github.com/octocat",
            linkedin="https://linkedin.com/in/priya-anand",
        ),
        skills=[
            "python", "kinesis", "rabbitmq", "postgresql", "redis",
            "docker", "kubernetes", "terraform", "fastapi", "grpc",
        ],
        experience=[
            Experience(
                company="Lumen Data",
                title="Staff Engineer",
                start_date="2022-03",
                end_date="Present",
                bullets=[
                    "Led 4-engineer migration from RabbitMQ to AWS Kinesis, "
                    "reducing P99 latency from 800ms to 180ms (4x).",
                    "Designed schema-registry pattern adopted across 12 services.",
                    "Mentored two junior engineers, both promoted within 18 months.",
                ],
            ),
            Experience(
                company="Hexa Inc",
                title="Senior Backend Engineer",
                start_date="2019-06",
                end_date="2022-02",
                bullets=[
                    "Owned the billing service handling $40M ARR.",
                    "Reduced infrastructure spend 38% via right-sizing K8s pods.",
                    "Built gRPC inter-service layer replacing REST monolith.",
                ],
            ),
        ],
        education=[
            Education(
                institution="UC Berkeley",
                degree="B.S.",
                field_of_study="Computer Science",
                start_year=2014,
                end_year=2018,
            ),
        ],
        projects=[
            Project(
                name="streamx",
                description="Open-source Python toolkit for Kinesis consumer groups.",
                technologies=["python", "kinesis", "asyncio"],
                url="https://github.com/octocat/streamx",
                bullets=[
                    "Adopted by 6 companies. 1.2k GitHub stars.",
                    "Solo-authored; maintained for 2+ years.",
                ],
            ),
        ],
        achievements=[
            Achievement(
                text="Cut P99 latency from 800ms to 180ms after Kinesis migration.",
                metric="4x",
                is_quantified=True,
                source_section="experience",
            ),
            Achievement(
                text="Reduced infrastructure spend by 38% at Hexa.",
                metric="38%",
                is_quantified=True,
                source_section="experience",
            ),
            Achievement(
                text="Owned billing service handling $40M ARR.",
                metric="$40M",
                is_quantified=True,
                source_section="experience",
            ),
        ],
        certifications=["AWS Solutions Architect Professional"],
        raw_text_length=4200,
    )

    score = CandidateScore(
        exact_match=ScoreDimension(
            value=66.7,
            reasoning="4 of 6 required skills match verbatim. Missing: kafka, kubernetes.",
            evidence=["python", "postgresql", "redis", "docker"],
        ),
        similarity=ScoreDimension(
            value=84.3,
            reasoning=(
                "Average cosine similarity 84%. Captured 2 adjacent skills: "
                "kafka↔kinesis (0.71), kubernetes↔terraform (0.62)."
            ),
            evidence=["kafka ≈ kinesis (0.71)", "kubernetes ≈ docker (0.69)"],
        ),
        achievement=ScoreDimension(
            value=87.0,
            reasoning=(
                "Multiple bullets quantify outcomes (4x latency, 38% cost, $40M ARR). "
                "Impact tied to clear actions and scope."
            ),
            evidence=[
                "Cut P99 latency from 800ms to 180ms (4x)",
                "Reduced infrastructure spend 38%",
                "Owned billing service handling $40M ARR",
            ],
        ),
        ownership=ScoreDimension(
            value=82.0,
            reasoning=(
                "Strong leadership language: led, designed, owned, mentored. "
                "Solo-authored OSS project plus team mentorship."
            ),
            evidence=["Led 4-engineer migration", "Solo-authored streamx", "Mentored two juniors"],
        ),
        overall=79.4,
        skill_matches=[
            SkillMatch(jd_skill="python", matched_resume_skill="python", match_type="exact", similarity=1.0),
            SkillMatch(
                jd_skill="kafka",
                matched_resume_skill="kinesis",
                match_type="semantic",
                similarity=0.71,
                rationale="Both are partitioned, append-only event streams — operational concepts transfer directly.",
            ),
            SkillMatch(jd_skill="postgresql", matched_resume_skill="postgresql", match_type="exact", similarity=1.0),
            SkillMatch(
                jd_skill="kubernetes",
                matched_resume_skill="docker",
                match_type="semantic",
                similarity=0.69,
                rationale="Container orchestration adjacency — strong on Docker, k8s skills typically transfer.",
            ),
            SkillMatch(jd_skill="docker", matched_resume_skill="docker", match_type="exact", similarity=1.0),
            SkillMatch(jd_skill="redis", matched_resume_skill="redis", match_type="exact", similarity=1.0),
        ],
    )

    verification = VerificationResult(
        github=GitHubVerification(
            found=True,
            username="octocat",
            profile_url="https://github.com/octocat",
            public_repos=8,
            followers=14_392,
            account_age_days=5_800,
            recent_commit_count_90d=42,
            top_languages=["Python", "Go", "Shell"],
            pinned_repo_names=["streamx", "Hello-World", "Spoon-Knife"],
            authenticity_score=92.0,
            flags=[],
            notes=["Account age 5800 days (mature).", "42 commits in last 90 days (active)."],
        ),
        linkedin=LinkedInVerification(
            found=True,
            profile_url="https://linkedin.com/in/priya-anand",
            url_valid=True,
            slug="priya-anand",
            notes=["URL is well-formed."],
        ),
        cross_reference=[],
        overall_authenticity=92.0,
    )

    tier = TierVerdict(
        tier="A",
        label="Fast-track",
        reasoning=(
            "All four dimensions strong (exact 67, similarity 84, achievement 87, "
            "ownership 82) with verified GitHub authenticity 92. The Kafka gap is "
            "covered by deep Kinesis experience — operationally equivalent."
        ),
        next_action="Schedule onsite with hiring manager. Skip phone screen.",
    )

    interview = InterviewPlan(
        questions=[
            InterviewQuestion(
                question=(
                    "Walk me through the RabbitMQ → Kinesis migration at Lumen. "
                    "What were the consumer-group semantics differences that bit you?"
                ),
                category="project_deep_dive",
                difficulty="hard",
                rationale="Verifies the 4x latency claim and probes Kafka-adjacent depth.",
                targets=["kinesis", "kafka", "ownership"],
            ),
            InterviewQuestion(
                question="How would you design a 50k-events/sec pipeline using Kafka specifically?",
                category="system_design",
                difficulty="hard",
                rationale="Translates Kinesis experience into Kafka-native design — JD's #1 skill.",
                targets=["kafka", "system_design"],
            ),
            InterviewQuestion(
                question="streamx has 1.2k stars — what's the most painful issue you've had to triage?",
                category="project_deep_dive",
                difficulty="medium",
                rationale="Tests OSS maintainership ownership claim.",
                targets=["streamx", "ownership"],
            ),
            InterviewQuestion(
                question="The JD requires Kubernetes — your resume shows Docker + Terraform. How would you ramp?",
                category="gap_probe",
                difficulty="medium",
                rationale="Direct gap: K8s declared as required but only adjacent skills present.",
                targets=["kubernetes"],
            ),
            InterviewQuestion(
                question="Tell me about mentoring the two juniors — what did you change after one of them struggled?",
                category="behavioral",
                difficulty="medium",
                rationale="Probes claim of mentorship leading to promotions.",
                targets=["ownership", "mentorship"],
            ),
            InterviewQuestion(
                question="In the billing service, how did you ensure correctness during the gRPC migration?",
                category="technical",
                difficulty="hard",
                rationale="Tests deep ownership of a $40M-ARR system.",
                targets=["grpc", "billing", "ownership"],
            ),
            InterviewQuestion(
                question="When would you NOT use Kinesis or Kafka? Pick a scenario from your past work.",
                category="technical",
                difficulty="medium",
                rationale="Distinguishes pattern-matching from genuine systems judgement.",
                targets=["kafka", "kinesis"],
            ),
            InterviewQuestion(
                question="What in the Lumen architecture would you redesign today, with hindsight?",
                category="behavioral",
                difficulty="medium",
                rationale="Probes self-reflection grounded in their actual work.",
                targets=["self_awareness", "system_design"],
            ),
        ],
        focus_areas=["streaming systems depth", "Kafka transferability", "ownership verification", "Kubernetes ramp"],
        estimated_duration_minutes=60,
    )

    return CandidateEvaluation(
        candidate_id="demo",
        parsed=parsed,
        score=score,
        verification=verification,
        tier=tier,
        interview=interview,
    )

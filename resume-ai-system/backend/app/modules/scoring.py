"""
The Multi-Dimensional Scoring Engine.

Four independent score dimensions, each producing a value, a human-readable
reasoning string, and concrete evidence quotes. The overall score is a
weighted blend; weights are tunable and surfaced in the response so the
recruiter knows exactly why the number is what it is.

  EXACT MATCH   — deterministic. % of JD required-skills present verbatim.
  SIMILARITY    — embedding-based. Captures Kafka↔RabbitMQ↔Kinesis kinship.
  ACHIEVEMENT   — LLM-judged. Quality and quantification of accomplishments.
  OWNERSHIP     — LLM-judged. Leadership / drive signal in language used.

The Similarity score is the answer to the assignment's "Kafka problem":
even when the candidate has Kinesis instead of Kafka, the cosine similarity
between their skill embedding and the JD's `kafka` embedding is high
(typically 0.65-0.78), so they get partial credit and are surfaced as a
"semantic" match with a rationale.
"""
from __future__ import annotations

import asyncio
import logging

import numpy as np

from app.core.embeddings import cosine_similarity, get_embeddings
from app.core.llm import LLMError, get_llm
from app.models.resume import JobDescription, ParsedResume
from app.models.scoring import (
    CandidateScore,
    ScoreDimension,
    SkillMatch,
)
from app.prompts.scoring import (
    ACHIEVEMENT_SYSTEM,
    OWNERSHIP_SYSTEM,
    achievement_user_prompt,
    ownership_user_prompt,
)

logger = logging.getLogger(__name__)


# Tunable weights — sum to 1.0
WEIGHTS = {
    "exact_match": 0.30,
    "similarity": 0.30,
    "achievement": 0.25,
    "ownership": 0.15,
}

# Cosine similarity threshold for "semantic match" (rough kinship)
SEMANTIC_MATCH_THRESHOLD = 0.55


class ScoringEngine:
    def __init__(self) -> None:
        self.embeddings = get_embeddings()
        self.llm = get_llm()

    async def score(
        self,
        resume: ParsedResume,
        jd: JobDescription,
    ) -> CandidateScore:
        """Run all four dimensions concurrently, then assemble the verdict."""
        # Skill matching produces both the exact_match score AND the similarity
        # score in a single embedding pass — they're computed together.
        skill_task = asyncio.create_task(self._skill_match(resume, jd))

        # LLM dimensions run in parallel
        ach_task = asyncio.create_task(self._achievement_score(resume))
        own_task = asyncio.create_task(self._ownership_score(resume))

        skill_matches, exact_dim, sim_dim = await skill_task
        achievement_dim = await ach_task
        ownership_dim = await own_task

        overall = (
            exact_dim.value * WEIGHTS["exact_match"]
            + sim_dim.value * WEIGHTS["similarity"]
            + achievement_dim.value * WEIGHTS["achievement"]
            + ownership_dim.value * WEIGHTS["ownership"]
        )

        return CandidateScore(
            exact_match=exact_dim,
            similarity=sim_dim,
            achievement=achievement_dim,
            ownership=ownership_dim,
            overall=round(overall, 1),
            skill_matches=skill_matches,
        )

    # --- 1 & 2. Exact + Similarity (single embedding pass) ----------------

    async def _skill_match(
        self, resume: ParsedResume, jd: JobDescription
    ) -> tuple[list[SkillMatch], ScoreDimension, ScoreDimension]:
        """Build skill-by-skill match table and derive both score dimensions."""
        jd_skills = [s.strip().lower() for s in jd.required_skills if s.strip()]
        resume_skills = [s.strip().lower() for s in resume.skills if s.strip()]

        if not jd_skills:
            placeholder = ScoreDimension(
                value=0,
                reasoning="No required skills supplied in the job description.",
                evidence=[],
            )
            return [], placeholder, placeholder

        if not resume_skills:
            zero_dim = lambda why: ScoreDimension(value=0, reasoning=why, evidence=[])  # noqa: E731
            return (
                [SkillMatch(jd_skill=s, match_type="missing") for s in jd_skills],
                zero_dim("Resume contains no extractable skills."),
                zero_dim("No skills available to compare embeddings against."),
            )

        # ----- Exact match (deterministic) -------------------------------
        resume_set = set(resume_skills)
        exact_hits = [s for s in jd_skills if s in resume_set]
        exact_pct = (len(exact_hits) / len(jd_skills)) * 100

        # ----- Embedding similarity --------------------------------------
        # We embed every JD skill and every resume skill, then for each JD
        # skill find its best resume match.
        # We also fold the resume's experience/project bullets into the
        # corpus so a candidate who used Kafka in a bullet (but didn't list
        # it as a "skill") still gets credit. This is the assignment's
        # explicit Kafka↔Kinesis case.
        bullet_corpus: list[str] = []
        for exp in resume.experience:
            bullet_corpus.extend(exp.bullets)
        for proj in resume.projects:
            bullet_corpus.extend(proj.bullets)
            bullet_corpus.extend(proj.technologies)

        # Build the side we compare against: skills + bullets
        right_side = list(resume_skills) + bullet_corpus
        right_labels = list(resume_skills) + ["[bullet] " + b[:80] for b in bullet_corpus]

        jd_embs = await self.embeddings.embed(jd_skills)
        right_embs = await self.embeddings.embed(right_side)

        sim_matrix = cosine_similarity(jd_embs, right_embs)  # (J, R)

        skill_matches: list[SkillMatch] = []
        sim_scores_for_overall: list[float] = []

        for i, jd_skill in enumerate(jd_skills):
            row = sim_matrix[i]
            best_idx = int(np.argmax(row)) if row.size else -1
            best_sim = float(row[best_idx]) if best_idx >= 0 else 0.0
            best_label = right_labels[best_idx] if best_idx >= 0 else None
            best_skill = right_side[best_idx] if best_idx >= 0 else None

            if jd_skill in resume_set:
                skill_matches.append(
                    SkillMatch(
                        jd_skill=jd_skill,
                        matched_resume_skill=jd_skill,
                        match_type="exact",
                        similarity=1.0,
                    )
                )
                sim_scores_for_overall.append(1.0)
            elif best_sim >= SEMANTIC_MATCH_THRESHOLD:
                skill_matches.append(
                    SkillMatch(
                        jd_skill=jd_skill,
                        matched_resume_skill=best_skill,
                        match_type="semantic",
                        similarity=round(best_sim, 3),
                        rationale=_kinship_rationale(jd_skill, best_skill, best_label, best_sim),
                    )
                )
                sim_scores_for_overall.append(best_sim)
            else:
                skill_matches.append(
                    SkillMatch(
                        jd_skill=jd_skill,
                        match_type="missing",
                        similarity=round(best_sim, 3),
                    )
                )
                sim_scores_for_overall.append(best_sim)

        sim_avg = (sum(sim_scores_for_overall) / len(sim_scores_for_overall)) * 100

        # ----- Build the two ScoreDimensions ------------------------------
        missing = [m.jd_skill for m in skill_matches if m.match_type == "missing"]
        semantic = [m for m in skill_matches if m.match_type == "semantic"]

        exact_dim = ScoreDimension(
            value=round(exact_pct, 1),
            reasoning=(
                f"{len(exact_hits)} of {len(jd_skills)} required skills appear verbatim. "
                + (f"Missing: {', '.join(missing[:5])}." if missing else "All required skills present.")
            ),
            evidence=[s for s in exact_hits[:8]],
        )

        sim_evidence = [
            f"{m.jd_skill} ≈ {m.matched_resume_skill} ({m.similarity:.2f})"
            for m in semantic[:6]
        ]
        sim_dim = ScoreDimension(
            value=round(sim_avg, 1),
            reasoning=(
                f"Average cosine similarity across {len(jd_skills)} JD skills is {sim_avg:.0f}%. "
                + (
                    f"Captured {len(semantic)} adjacent skill(s): "
                    + ", ".join(f"{m.jd_skill}↔{m.matched_resume_skill}" for m in semantic[:3])
                    + ("." if semantic else "")
                    if semantic
                    else "No notable semantic adjacencies."
                )
            ),
            evidence=sim_evidence,
        )

        return skill_matches, exact_dim, sim_dim

    # --- 3. Achievement -------------------------------------------------

    async def _achievement_score(self, resume: ParsedResume) -> ScoreDimension:
        achievements = [a.model_dump() for a in resume.achievements]
        bullets: list[str] = []
        for exp in resume.experience:
            bullets.extend(exp.bullets)

        if not achievements and not bullets:
            return ScoreDimension(
                value=0,
                reasoning="No achievements or experience bullets to evaluate.",
                evidence=[],
            )

        try:
            data = await self.llm.chat_json(
                system=ACHIEVEMENT_SYSTEM,
                user=achievement_user_prompt(achievements, bullets[:30]),
                max_tokens=1024,
                temperature=0.2,
            )
            return _coerce_dim(data)
        except LLMError as e:
            logger.warning("Achievement LLM scoring failed, falling back: %s", e)
            return self._achievement_fallback(resume)

    def _achievement_fallback(self, resume: ParsedResume) -> ScoreDimension:
        """Heuristic: % of bullets containing numbers."""
        import re

        all_bullets = []
        for exp in resume.experience:
            all_bullets.extend(exp.bullets)
        for proj in resume.projects:
            all_bullets.extend(proj.bullets)

        if not all_bullets:
            return ScoreDimension(value=0, reasoning="No bullets available.", evidence=[])

        quantified = [b for b in all_bullets if re.search(r"\d", b)]
        ratio = len(quantified) / len(all_bullets)
        score = min(100, ratio * 110)  # ratio of 0.9+ → near 100
        return ScoreDimension(
            value=round(score, 1),
            reasoning=f"{len(quantified)}/{len(all_bullets)} bullets contain quantifiable metrics.",
            evidence=quantified[:4],
        )

    # --- 4. Ownership ---------------------------------------------------

    async def _ownership_score(self, resume: ParsedResume) -> ScoreDimension:
        if not resume.experience and not resume.projects:
            return ScoreDimension(
                value=0,
                reasoning="No experience or project content to evaluate.",
                evidence=[],
            )
        try:
            data = await self.llm.chat_json(
                system=OWNERSHIP_SYSTEM,
                user=ownership_user_prompt(resume.model_dump()),
                max_tokens=1024,
                temperature=0.2,
            )
            return _coerce_dim(data)
        except LLMError as e:
            logger.warning("Ownership LLM scoring failed, falling back: %s", e)
            return self._ownership_fallback(resume)

    def _ownership_fallback(self, resume: ParsedResume) -> ScoreDimension:
        positive_terms = [
            "led", "owned", "designed", "architected", "founded",
            "initiated", "drove", "spearheaded", "mentored",
        ]
        negative_terms = ["assisted", "helped", "supported", "contributed to"]
        all_text = " ".join(b.lower() for exp in resume.experience for b in exp.bullets)
        all_text += " " + " ".join(b.lower() for p in resume.projects for b in p.bullets)

        pos = sum(all_text.count(t) for t in positive_terms)
        neg = sum(all_text.count(t) for t in negative_terms)
        raw = pos * 12 - neg * 6
        score = max(0, min(100, 30 + raw))

        return ScoreDimension(
            value=round(score, 1),
            reasoning=f"Heuristic: {pos} ownership verbs vs {neg} participation verbs across bullets.",
            evidence=[t for t in positive_terms if t in all_text][:4],
        )


# --- helpers ------------------------------------------------------------


def _coerce_dim(data: dict) -> ScoreDimension:
    """Coerce a possibly-loose LLM JSON dict into a ScoreDimension."""
    value = data.get("value")
    try:
        value = float(value)
    except (TypeError, ValueError):
        value = 0.0
    value = max(0.0, min(100.0, value))
    return ScoreDimension(
        value=value,
        reasoning=str(data.get("reasoning") or "No reasoning provided."),
        evidence=[str(e) for e in data.get("evidence") or [] if e],
    )


def _kinship_rationale(jd_skill: str, matched: str | None, label: str | None, sim: float) -> str:
    """Generate a short explanation for why a semantic match is plausible."""
    if matched is None:
        return ""
    # Hand-crafted hints for common pairs make the rationale pop.
    pairs = {
        ("kafka", "kinesis"): "Both are partitioned, append-only event streams — operational concepts transfer directly.",
        ("kafka", "rabbitmq"): "Both are message brokers; consumer-group / queue semantics transfer with caveats.",
        ("postgres", "mysql"): "Same SQL family; tuning, indexing, and migration patterns overlap heavily.",
        ("react", "vue"): "Both component-based reactive frameworks; mental models transfer 1:1.",
        ("aws", "gcp"): "Cloud primitives map closely (S3↔GCS, EC2↔GCE, Lambda↔Cloud Functions).",
        ("pytorch", "tensorflow"): "Same deep-learning conceptual stack; idiomatic differences in autograd handling.",
    }
    key = (jd_skill, matched.replace("[bullet] ", ""))
    if key in pairs:
        return pairs[key]
    if (key[1], key[0]) in pairs:
        return pairs[(key[1], key[0])]
    if label and label.startswith("[bullet]"):
        return f"Mentioned in experience bullet (cosine={sim:.2f})."
    return f"Embedding cosine similarity = {sim:.2f} suggests adjacent technology."

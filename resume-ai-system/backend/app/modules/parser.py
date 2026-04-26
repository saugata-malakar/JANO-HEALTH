"""
Resume Parser — converts unstructured resume text into a ParsedResume.

Pipeline:
    file bytes → text (utils.file_extract) → LLM JSON → ParsedResume

If the LLM fails or produces malformed JSON, we fall back to a regex
heuristic extractor that catches the most common fields. This means
the system NEVER fully fails on a resume — it degrades gracefully.
"""
from __future__ import annotations

import logging
import re

from app.core.llm import LLMError, get_llm
from app.models.resume import (
    Achievement,
    Education,
    Experience,
    Links,
    ParsedResume,
    Project,
)
from app.prompts.parser import PARSER_SYSTEM, parser_user_prompt
from app.utils.file_extract import extract_text

logger = logging.getLogger(__name__)


class ResumeParser:
    """Async parser. One instance per app — safe to share."""

    def __init__(self) -> None:
        self.llm = get_llm()

    async def parse_file(self, filename: str, content: bytes) -> ParsedResume:
        text = extract_text(filename, content)
        return await self.parse_text(text)

    async def parse_text(self, text: str) -> ParsedResume:
        # Truncate to ~12k chars — covers any reasonable resume (~3 pages).
        # Most LLM context windows handle this trivially; we cap to keep
        # cost predictable and prevent prompt-injection from very long files.
        text_for_llm = text[:12_000]

        try:
            data = await self.llm.chat_json(
                system=PARSER_SYSTEM,
                user=parser_user_prompt(text_for_llm),
                max_tokens=4096,
                temperature=0.1,
            )
        except LLMError as e:
            logger.warning("LLM parsing failed, falling back to regex: %s", e)
            return self._regex_fallback(text)

        try:
            parsed = self._coerce(data, raw_len=len(text))
        except Exception as e:
            logger.warning("Coercing LLM output to ParsedResume failed: %s", e)
            return self._regex_fallback(text)

        # If the LLM gave us almost nothing useful, augment with regex
        if not parsed.email or not parsed.skills or not parsed.name:
            fallback = self._regex_fallback(text)
            parsed.name = parsed.name or fallback.name
            parsed.email = parsed.email or fallback.email
            parsed.phone = parsed.phone or fallback.phone
            if not parsed.skills:
                parsed.skills = fallback.skills
            if not parsed.links.github:
                parsed.links.github = fallback.links.github
            if not parsed.links.linkedin:
                parsed.links.linkedin = fallback.links.linkedin

        return parsed

    # ---- internals ----------------------------------------------------

    def _coerce(self, data: dict, raw_len: int) -> ParsedResume:
        """Construct a ParsedResume from a raw LLM dict, defending against
        partial / malformed outputs."""
        return ParsedResume(
            name=_s(data.get("name")),
            email=_s(data.get("email")),
            phone=_s(data.get("phone")),
            location=_s(data.get("location")),
            headline=_s(data.get("headline")),
            summary=_s(data.get("summary")),
            links=Links(**(data.get("links") or {})),
            skills=[s.lower().strip() for s in data.get("skills") or [] if isinstance(s, str)],
            experience=[Experience(**e) for e in data.get("experience") or [] if isinstance(e, dict)],
            education=[Education(**e) for e in data.get("education") or [] if isinstance(e, dict)],
            projects=[Project(**p) for p in data.get("projects") or [] if isinstance(p, dict)],
            achievements=[
                Achievement(**a) for a in data.get("achievements") or [] if isinstance(a, dict)
            ],
            certifications=[c for c in data.get("certifications") or [] if isinstance(c, str)],
            languages=[l for l in data.get("languages") or [] if isinstance(l, str)],
            raw_text_length=raw_len,
        )

    def _regex_fallback(self, text: str) -> ParsedResume:
        """Best-effort regex extractor. Used when the LLM is unavailable
        or produces garbage. Captures only the easy fields."""
        email_match = re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", text)
        phone_match = re.search(r"(\+?\d[\d\s().-]{8,}\d)", text)
        github_match = re.search(r"https?://(?:www\.)?github\.com/[\w-]+", text)
        linkedin_match = re.search(
            r"https?://(?:www\.)?linkedin\.com/in/[\w-]+", text
        )

        # Name heuristic: first non-trivial line that looks like a person's name
        # (2-4 capitalized words, no digits, no @ sign).
        name = None
        for line in text.splitlines()[:8]:
            stripped = line.strip()
            if (
                stripped
                and 4 <= len(stripped) <= 60
                and "@" not in stripped
                and not re.search(r"\d", stripped)
                and re.match(r"^[A-Z][A-Za-z'.-]+(\s+[A-Z][A-Za-z'.-]+){1,3}$", stripped)
            ):
                name = stripped
                break

        # Skill heuristic: a curated list of common tech terms
        skill_vocab = {
            "python", "java", "javascript", "typescript", "go", "rust", "c++",
            "c#", "ruby", "php", "swift", "kotlin", "scala", "r",
            "react", "vue", "angular", "node", "express", "fastapi", "django",
            "flask", "spring", "rails",
            "postgresql", "mysql", "mongodb", "redis", "elasticsearch",
            "kafka", "rabbitmq", "kinesis", "pulsar",
            "aws", "gcp", "azure", "docker", "kubernetes", "terraform",
            "tensorflow", "pytorch", "scikit-learn", "pandas", "numpy",
            "spark", "hadoop", "airflow", "dbt", "snowflake",
        }
        text_lower = text.lower()
        found_skills = sorted(s for s in skill_vocab if re.search(rf"\b{re.escape(s)}\b", text_lower))

        return ParsedResume(
            name=name,
            email=email_match.group(0) if email_match else None,
            phone=phone_match.group(1) if phone_match else None,
            links=Links(
                github=github_match.group(0) if github_match else None,
                linkedin=linkedin_match.group(0) if linkedin_match else None,
            ),
            skills=found_skills,
            raw_text_length=len(text),
        )


def _s(v) -> str | None:
    if v is None:
        return None
    if isinstance(v, str):
        v = v.strip()
        return v or None
    return str(v)

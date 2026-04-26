"""Pydantic schemas for the parsed resume structure.

This is the canonical JSON shape that the Parser emits and every other
module (Scoring, Verification, Question Generator) consumes. Keeping
this single source of truth prevents downstream drift.
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, HttpUrl


class Education(BaseModel):
    institution: str
    degree: Optional[str] = None
    field_of_study: Optional[str] = None
    start_year: Optional[int] = None
    end_year: Optional[int] = None
    gpa: Optional[str] = None


class Experience(BaseModel):
    company: str
    title: str
    start_date: Optional[str] = None  # "2023-01" style
    end_date: Optional[str] = None    # "Present" allowed
    location: Optional[str] = None
    bullets: list[str] = Field(default_factory=list)


class Project(BaseModel):
    name: str
    description: Optional[str] = None
    technologies: list[str] = Field(default_factory=list)
    url: Optional[str] = None
    bullets: list[str] = Field(default_factory=list)


class Achievement(BaseModel):
    """Quantified accomplishment extracted from any section.

    `metric` captures the *number* part ("40% reduction", "$2M saved",
    "3x faster"). `is_quantified` is True iff at least one numeric
    figure backs the claim — used directly by the Achievement score.
    """
    text: str
    metric: Optional[str] = None
    is_quantified: bool = False
    source_section: Optional[str] = None  # "experience" / "projects" / etc.


class Links(BaseModel):
    github: Optional[str] = None
    linkedin: Optional[str] = None
    portfolio: Optional[str] = None
    other: list[str] = Field(default_factory=list)


class ParsedResume(BaseModel):
    """The full structured resume."""
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    headline: Optional[str] = None
    summary: Optional[str] = None
    links: Links = Field(default_factory=Links)
    skills: list[str] = Field(default_factory=list)
    experience: list[Experience] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    projects: list[Project] = Field(default_factory=list)
    achievements: list[Achievement] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    raw_text_length: int = 0


class JobDescription(BaseModel):
    """Job description provided by the recruiter."""
    title: str
    company: Optional[str] = None
    description: str
    required_skills: list[str] = Field(default_factory=list)
    nice_to_have: list[str] = Field(default_factory=list)
    seniority: Optional[str] = None  # "junior" / "mid" / "senior" / "staff"
    years_experience: Optional[int] = None

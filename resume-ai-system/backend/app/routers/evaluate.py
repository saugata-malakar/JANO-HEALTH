"""
Evaluation endpoints — the main API surface.

Endpoints:
  POST /api/evaluate/file        single resume file + JD → full evaluation
  POST /api/evaluate/batch       multiple files + JD → list of evaluations
  POST /api/evaluate/text        pasted text + JD → full evaluation
  POST /api/parse                resume only — useful for previewing parse
  POST /api/score                already-parsed resume + JD → score only
  POST /api/verify               parsed resume → verification only
  POST /api/interview            parsed + score + JD → questions only

The split lets the frontend show progressive results: parse first, then
score, then verification streams in once GitHub responds.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from app.core.security import AuthUser, get_current_user
from app.models.resume import JobDescription, ParsedResume
from app.models.scoring import CandidateEvaluation, CandidateScore, InterviewPlan
from app.modules.pipeline import EvaluationPipeline
from app.modules.scoring import ScoringEngine
from app.modules.tiering import QuestionGenerator
from app.modules.verification import VerificationEngine

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["evaluation"])

# Singleton pipeline — initialized on module import. Heavy work (loading
# the embedding model) is deferred until first use.
_pipeline = EvaluationPipeline()
_scorer = _pipeline.scorer
_verifier = _pipeline.verifier
_questions = _pipeline.questions


# Limits
MAX_FILE_BYTES = 5 * 1024 * 1024  # 5 MB
MAX_BATCH_SIZE = 25
ALLOWED_EXTS = {".pdf", ".docx", ".txt", ".md"}


# --- request/response shapes -------------------------------------------


class TextEvalRequest(BaseModel):
    resume_text: str = Field(min_length=20)
    jd: JobDescription
    verify: bool = True
    generate_questions: bool = True


class ScoreOnlyRequest(BaseModel):
    parsed: ParsedResume
    jd: JobDescription


class InterviewOnlyRequest(BaseModel):
    parsed: ParsedResume
    jd: JobDescription
    score: CandidateScore
    gaps: list[str] = []


# --- endpoints ----------------------------------------------------------


@router.post("/evaluate/file", response_model=CandidateEvaluation)
async def evaluate_file(
    user: Annotated[AuthUser, Depends(get_current_user)],
    file: UploadFile = File(...),
    jd: str = Form(..., description="Job description as JSON-encoded string"),
    verify: bool = Form(default=True),
    generate_questions: bool = Form(default=True),
) -> CandidateEvaluation:
    _validate_upload(file)
    content = await file.read()
    if len(content) > MAX_FILE_BYTES:
        raise HTTPException(413, f"File exceeds {MAX_FILE_BYTES} bytes.")
    try:
        jd_obj = JobDescription.model_validate_json(jd)
    except Exception as e:
        raise HTTPException(422, f"Invalid jd JSON: {e}") from e

    return await _pipeline.evaluate_one(
        filename=file.filename or "resume.pdf",
        content=content,
        jd=jd_obj,
        verify=verify,
        generate_questions=generate_questions,
    )


@router.post("/evaluate/batch", response_model=list[CandidateEvaluation])
async def evaluate_batch(
    user: Annotated[AuthUser, Depends(get_current_user)],
    files: list[UploadFile] = File(...),
    jd: str = Form(...),
    verify: bool = Form(default=True),
    generate_questions: bool = Form(default=False),
) -> list[CandidateEvaluation]:
    if len(files) > MAX_BATCH_SIZE:
        raise HTTPException(413, f"Batch exceeds {MAX_BATCH_SIZE} resumes.")
    try:
        jd_obj = JobDescription.model_validate_json(jd)
    except Exception as e:
        raise HTTPException(422, f"Invalid jd JSON: {e}") from e

    payloads: list[tuple[str, bytes]] = []
    for f in files:
        _validate_upload(f)
        c = await f.read()
        if len(c) > MAX_FILE_BYTES:
            raise HTTPException(413, f"{f.filename} exceeds size limit.")
        payloads.append((f.filename or "resume.pdf", c))

    # Bound concurrency — too many simultaneous LLM calls can rate-limit
    sem = asyncio.Semaphore(5)

    async def run(name: str, content: bytes) -> CandidateEvaluation:
        async with sem:
            try:
                return await _pipeline.evaluate_one(
                    filename=name,
                    content=content,
                    jd=jd_obj,
                    verify=verify,
                    generate_questions=generate_questions,
                )
            except Exception as e:
                logger.exception("Batch eval failed for %s", name)
                # Return a synthetic minimal evaluation so the batch keeps going
                from app.models.resume import ParsedResume
                from app.models.scoring import (
                    CandidateScore,
                    ScoreDimension,
                    TierVerdict,
                )

                empty_dim = ScoreDimension(value=0, reasoning=f"Failed: {e}", evidence=[])
                return CandidateEvaluation(
                    candidate_id="error",
                    parsed=ParsedResume(name=name),
                    score=CandidateScore(
                        exact_match=empty_dim,
                        similarity=empty_dim,
                        achievement=empty_dim,
                        ownership=empty_dim,
                        overall=0,
                    ),
                    tier=TierVerdict(
                        tier="C",
                        label="Needs Evaluation",
                        reasoning=f"Pipeline error: {e}",
                        next_action="Manual review.",
                    ),
                )

    return await asyncio.gather(*(run(n, c) for n, c in payloads))


@router.post("/evaluate/text", response_model=CandidateEvaluation)
async def evaluate_text(
    body: TextEvalRequest,
    user: Annotated[AuthUser, Depends(get_current_user)],
) -> CandidateEvaluation:
    return await _pipeline.evaluate_text(
        resume_text=body.resume_text,
        jd=body.jd,
        verify=body.verify,
        generate_questions=body.generate_questions,
    )


@router.post("/parse", response_model=ParsedResume)
async def parse_only(
    user: Annotated[AuthUser, Depends(get_current_user)],
    file: UploadFile = File(...),
) -> ParsedResume:
    _validate_upload(file)
    content = await file.read()
    if len(content) > MAX_FILE_BYTES:
        raise HTTPException(413, "File too large.")
    return await _pipeline.parser.parse_file(file.filename or "resume.pdf", content)


@router.post("/score", response_model=CandidateScore)
async def score_only(
    body: ScoreOnlyRequest,
    user: Annotated[AuthUser, Depends(get_current_user)],
) -> CandidateScore:
    return await _scorer.score(body.parsed, body.jd)


@router.post("/verify")
async def verify_only(
    body: ParsedResume,
    user: Annotated[AuthUser, Depends(get_current_user)],
):
    return await _verifier.verify(body)


@router.post("/interview", response_model=InterviewPlan)
async def interview_only(
    body: InterviewOnlyRequest,
    user: Annotated[AuthUser, Depends(get_current_user)],
) -> InterviewPlan:
    return await _questions.generate(body.parsed, body.jd, body.score, body.gaps)


# --- helpers ----------------------------------------------------------


def _validate_upload(file: UploadFile) -> None:
    if not file.filename:
        raise HTTPException(422, "File has no filename.")
    name = file.filename.lower()
    if not any(name.endswith(ext) for ext in ALLOWED_EXTS):
        raise HTTPException(422, f"Unsupported file type. Allowed: {sorted(ALLOWED_EXTS)}")

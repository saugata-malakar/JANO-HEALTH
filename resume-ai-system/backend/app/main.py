"""
HireSense FastAPI entrypoint.

Run with: uvicorn app.main:app --reload --port 8000
"""
from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import __version__
from app.core.config import get_settings
from app.routers import demo, evaluate, health
from app.utils.file_extract import ResumeExtractionError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="HireSense API",
        description=(
            "AI Resume Shortlisting & Interview Assistant. Parses resumes, "
            "scores candidates across 4 dimensions, verifies public claims, "
            "classifies into tiers, and generates tailored interview questions."
        ),
        version=__version__,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(demo.router)
    app.include_router(evaluate.router)

    @app.exception_handler(ResumeExtractionError)
    async def extraction_handler(request: Request, exc: ResumeExtractionError):
        logger.warning("Resume extraction failed: %s", exc)
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={"detail": "Validation error", "errors": exc.errors()},
        )

    @app.on_event("startup")
    async def on_startup() -> None:
        logger.info("HireSense %s starting up", __version__)
        logger.info("LLM provider: %s (%s)", settings.llm_provider, settings.llm_model)
        logger.info("Embedding model: %s", settings.embedding_model)
        if settings.dev_bypass_auth:
            logger.warning("⚠ DEV_BYPASS_AUTH=true — auth is disabled. Do not deploy this way.")

    return app


app = create_app()

"""Health and meta endpoints — no auth required."""
from fastapi import APIRouter

from app import __version__
from app.core.config import get_settings

router = APIRouter(tags=["meta"])


@router.get("/health")
async def health() -> dict:
    return {"status": "ok", "version": __version__}


@router.get("/config")
async def public_config() -> dict:
    """Surface non-secret config so the frontend can adjust UI accordingly."""
    s = get_settings()
    return {
        "version": __version__,
        "llm_provider": s.llm_provider,
        "llm_model": s.llm_model,
        "embedding_model": s.embedding_model,
        "github_verification_enabled": bool(s.github_token),
        "auth_required": not s.dev_bypass_auth,
    }

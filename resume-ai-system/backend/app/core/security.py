"""
Clerk JWT verification for FastAPI.

Clerk issues short-lived JWTs signed with RS256. We fetch the JWKS once and
cache the public keys, then verify each incoming token's signature, expiry,
issuer, and audience.

For local development you can set DEV_BYPASS_AUTH=true to skip verification
and use a mock user — never enable this in production.
"""
from __future__ import annotations

import logging
import time
from typing import Any

import httpx
import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import get_settings

logger = logging.getLogger(__name__)
_bearer = HTTPBearer(auto_error=False)


class JWKSCache:
    """In-memory JWKS cache with 1-hour TTL."""

    def __init__(self, ttl: int = 3600) -> None:
        self.ttl = ttl
        self._keys: dict[str, Any] = {}
        self._fetched_at: float = 0

    async def get_keys(self, url: str) -> dict[str, Any]:
        if self._keys and (time.time() - self._fetched_at) < self.ttl:
            return self._keys
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            jwks = resp.json()
        self._keys = {k["kid"]: k for k in jwks.get("keys", [])}
        self._fetched_at = time.time()
        return self._keys


_jwks_cache = JWKSCache()


class AuthUser:
    """Lightweight user representation extracted from the JWT."""

    def __init__(self, sub: str, email: str | None = None, claims: dict | None = None) -> None:
        self.sub = sub
        self.email = email
        self.claims = claims or {}

    def __repr__(self) -> str:  # pragma: no cover
        return f"AuthUser(sub={self.sub!r}, email={self.email!r})"


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> AuthUser:
    settings = get_settings()

    # Dev bypass
    if settings.dev_bypass_auth:
        return AuthUser(sub="dev-user", email="dev@local")

    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not settings.clerk_jwks_url:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Auth not configured: CLERK_JWKS_URL is missing",
        )

    token = credentials.credentials
    try:
        unverified_header = jwt.get_unverified_header(token)
    except jwt.PyJWTError as e:
        raise HTTPException(401, f"Malformed token: {e}") from e

    kid = unverified_header.get("kid")
    if not kid:
        raise HTTPException(401, "Token missing 'kid' header")

    keys = await _jwks_cache.get_keys(settings.clerk_jwks_url)
    if kid not in keys:
        # Refresh once in case keys rotated
        _jwks_cache._fetched_at = 0
        keys = await _jwks_cache.get_keys(settings.clerk_jwks_url)
        if kid not in keys:
            raise HTTPException(401, "Unknown signing key")

    public_key = jwt.algorithms.RSAAlgorithm.from_jwk(keys[kid])

    try:
        payload = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            audience=settings.clerk_audience or None,
            issuer=settings.clerk_issuer or None,
            options={
                "verify_aud": bool(settings.clerk_audience),
                "verify_iss": bool(settings.clerk_issuer),
            },
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expired")
    except jwt.PyJWTError as e:
        raise HTTPException(401, f"Token verification failed: {e}") from e

    return AuthUser(
        sub=payload["sub"],
        email=payload.get("email"),
        claims=payload,
    )

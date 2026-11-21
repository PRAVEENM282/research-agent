from __future__ import annotations

import hashlib
import hmac
from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, Request
from sqlalchemy import select

from src.config.settings import settings
from src.db.engine import AsyncSessionFactory
from src.db.models import User, UserSession


SESSION_COOKIE = "handoff_session"


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def csrf_for(token: str) -> str:
    return hmac.new(
        settings.oidc_session_secret.encode("utf-8"),
        ("csrf:" + token).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


async def require_user(request: Request) -> User:
    raw_token = request.cookies.get(SESSION_COOKIE)
    if not raw_token:
        raise HTTPException(401, detail={"code": "authentication_required", "message": "Sign in to continue."})
    async with AsyncSessionFactory() as session:
        record = (
            await session.execute(
                select(UserSession, User)
                .join(User, User.id == UserSession.user_id)
                .where(
                    UserSession.token_hash == token_hash(raw_token),
                    UserSession.revoked_at.is_(None),
                    UserSession.expires_at > datetime.now(UTC),
                )
            )
        ).one_or_none()
    if record is None:
        raise HTTPException(401, detail={"code": "authentication_required", "message": "Sign in to continue."})
    request.state.session_token = raw_token
    request.state.user = record[1]
    return record[1]


async def require_csrf(request: Request) -> None:
    token = getattr(request.state, "session_token", None) or request.cookies.get(SESSION_COOKIE)
    supplied = request.headers.get("x-csrf-token", "")
    if not token or not hmac.compare_digest(csrf_for(token), supplied):
        raise HTTPException(403, detail={"code": "csrf_failed", "message": "Refresh the page and try again."})
    origin = request.headers.get("origin")
    if not origin:
        raise HTTPException(403, detail={"code": "origin_required", "message": "A same-origin request is required."})
    expected = f"{request.url.scheme}://{request.url.netloc}"
    if not hmac.compare_digest(origin.rstrip("/"), expected.rstrip("/")):
        raise HTTPException(403, detail={"code": "origin_rejected", "message": "A same-origin request is required."})


def current_user_payload(user: User) -> dict[str, str | UUID | None]:
    return {
        "id": user.id,
        "issuer": user.issuer,
        "subject": user.subject,
        "email": user.email,
        "display_name": user.display_name,
    }

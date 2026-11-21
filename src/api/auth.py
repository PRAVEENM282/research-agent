from __future__ import annotations

import secrets
import logging
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy import text

from src.api.dependencies import (
    SESSION_COOKIE,
    csrf_for,
    current_user_payload,
    require_csrf,
    require_user,
    token_hash,
)
from src.config.settings import settings
from src.db.engine import AsyncSessionFactory
from src.db.models import User, UserSession

router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])
oauth = OAuth()
logger = logging.getLogger(__name__)

_SAFE_OIDC_ERROR_CODES = {
    "access_denied",
    "invalid_client",
    "invalid_grant",
    "invalid_request",
    "unauthorized_client",
    "temporarily_unavailable",
    "server_error",
}


def _oidc_client():
    if not all((settings.oidc_issuer_url, settings.oidc_client_id, settings.oidc_client_secret, settings.oidc_redirect_uri)):
        raise HTTPException(503, detail={"code": "oidc_not_configured", "message": "Sign-in is not configured yet."})
    if "handoff" not in oauth._clients:
        issuer = settings.oidc_issuer_url.rstrip("/")
        oauth.register(
            name="handoff",
            client_id=settings.oidc_client_id,
            client_secret=settings.oidc_client_secret,
            server_metadata_url=f"{issuer}/.well-known/openid-configuration",
            client_kwargs={"scope": "openid profile email", "code_challenge_method": "S256"},
        )
    return oauth.create_client("handoff")


@router.get("/config")
async def auth_config() -> dict[str, bool]:
    return {
        "oidc_available": all(
            (settings.oidc_issuer_url, settings.oidc_client_id, settings.oidc_client_secret, settings.oidc_redirect_uri)
        )
    }


@router.get("/login")
async def login(request: Request) -> RedirectResponse:
    client = _oidc_client()
    return await client.authorize_redirect(
        request,
        settings.oidc_redirect_uri,
    )


@router.get("/callback")
async def callback(request: Request) -> RedirectResponse:
    client = _oidc_client()
    try:
        token = await client.authorize_access_token(request)
    except Exception as exc:
        error_code = getattr(exc, "error", None)
        diagnostic = error_code if error_code in _SAFE_OIDC_ERROR_CODES else type(exc).__name__
        logger.warning(
            "OIDC callback failed during code exchange or ID-token validation (%s)", diagnostic
        )
        return RedirectResponse("/login?error=signin_failed", status_code=303)
    claims = token.get("userinfo")
    if claims is None:
        logger.warning("OIDC callback returned no validated ID-token claims")
        return RedirectResponse("/login?error=signin_failed", status_code=303)
    issuer = str(claims.get("iss", "")).rstrip("/")
    subject = str(claims.get("sub", ""))
    email = str(claims.get("email", "")).strip().lower()
    if not issuer or issuer != settings.oidc_issuer_url.rstrip("/") or not subject:
        return RedirectResponse("/login?error=signin_failed", status_code=303)
    email_is_allowed = settings.oidc_allow_any_emails or email in settings.allowed_email_list
    if claims.get("email_verified") is not True or not email or not email_is_allowed:
        return RedirectResponse("/login?error=account_not_allowed", status_code=303)

    raw_session = secrets.token_urlsafe(48)
    expires = datetime.now(UTC) + timedelta(days=14)
    async with AsyncSessionFactory() as db, db.begin():
        row = await db.execute(
            text("""INSERT INTO users(issuer, subject, email, display_name)
            VALUES (:issuer, :subject, :email, :name)
            ON CONFLICT (issuer, subject) DO UPDATE SET email=EXCLUDED.email,
                display_name=EXCLUDED.display_name RETURNING id"""),
            {
                "issuer": issuer,
                "subject": subject,
                "email": email,
                "name": str(claims.get("name", ""))[:200] or None,
            },
        )
        user_id = row.scalar_one()
        bootstrap_email = settings.oidc_bootstrap_email.strip().lower()
        if bootstrap_email and email == bootstrap_email:
            await db.execute(
                text(
                    """INSERT INTO task_owners(task_id, user_id)
                    SELECT t.id, :user_id FROM tasks t
                    LEFT JOIN task_owners o ON o.task_id=t.id
                    WHERE o.task_id IS NULL ON CONFLICT (task_id) DO NOTHING"""
                ),
                {"user_id": user_id},
            )
        db.add(UserSession(id=uuid4(), token_hash=token_hash(raw_session), user_id=user_id, expires_at=expires))
    response = RedirectResponse(url="/workspace", status_code=303)
    response.set_cookie(
        SESSION_COOKIE,
        raw_session,
        max_age=14 * 24 * 60 * 60,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
        path="/",
    )
    request.session.clear()
    return response


@router.get("/me")
async def me(request: Request, user: User = Depends(require_user)) -> dict[str, object]:
    raw_token = request.state.session_token
    return {"user": current_user_payload(user), "csrf_token": csrf_for(raw_token)}


@router.post("/logout", dependencies=[Depends(require_csrf)])
async def logout(request: Request, user: User = Depends(require_user)) -> Response:
    raw_token = request.cookies.get(SESSION_COOKIE)
    if raw_token:
        async with AsyncSessionFactory() as db, db.begin():
            await db.execute(
                UserSession.__table__.update()
                .where(UserSession.token_hash == token_hash(raw_token), UserSession.user_id == user.id)
                .values(revoked_at=datetime.now(UTC))
            )
    result = Response(status_code=204)
    result.delete_cookie(SESSION_COOKIE, path="/", httponly=True, secure=settings.session_cookie_secure, samesite="lax")
    return result

from __future__ import annotations

import asyncio

from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import AnyHttpUrl, BaseModel, Field, SecretStr, field_validator
from sqlalchemy import select

from src.agents.mcp_client import (
    discover_connection_tools_sync,
    encrypt_credential,
    get_owned_connection,
    list_owned_connections,
)
from src.agents.url_policy import UnsafeURL, validate_public_http_url
from src.api.dependencies import require_csrf, require_user
from src.config.settings import settings
from src.db.engine import AsyncSessionFactory
from src.db.models import MCPConnection, User

router = APIRouter(prefix="/api/v1/connections", tags=["tool connections"])


class ConnectionInput(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    url: AnyHttpUrl
    bearer_token: SecretStr | None = None
    enabled_tools: list[str] = Field(default_factory=list, max_length=100)
    read_only_tools: list[str] = Field(default_factory=list, max_length=100)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return value.strip()


class ConnectionSummary(BaseModel):
    id: UUID
    name: str
    url: str
    credential_configured: bool
    enabled_tools: list[str]
    read_only_tools: list[str]


def _summary(connection: MCPConnection) -> ConnectionSummary:
    return ConnectionSummary(
        id=connection.id,
        name=connection.name,
        url=connection.server_url,
        credential_configured=connection.encrypted_bearer_token is not None,
        enabled_tools=list(connection.enabled_tools or []),
        read_only_tools=list(connection.read_only_tools or []),
    )


async def _validate_url(value: str) -> None:
    try:
        if not value.lower().startswith("https://"):
            raise UnsafeURL("MCP servers must use HTTPS.")
        await validate_public_http_url(value)
    except UnsafeURL as exc:
        raise HTTPException(422, detail={"code": "unsafe_connection_url", "message": str(exc)}) from None


@router.get("", response_model=list[ConnectionSummary])
async def list_connections(user: User = Depends(require_user)) -> list[ConnectionSummary]:
    return [_summary(item) for item in list_owned_connections(user.id)]


@router.post("", response_model=ConnectionSummary, status_code=201, dependencies=[Depends(require_csrf)])
async def create_connection(body: ConnectionInput, user: User = Depends(require_user)) -> ConnectionSummary:
    await _validate_url(str(body.url))
    if len(set(body.enabled_tools)) != len(body.enabled_tools) or len(set(body.read_only_tools)) != len(body.read_only_tools):
        raise HTTPException(422)
    connection = MCPConnection(
        id=uuid4(),
        user_id=user.id,
        name=body.name,
        server_url=str(body.url),
        encrypted_bearer_token=None,
        enabled_tools=body.enabled_tools,
        read_only_tools=body.read_only_tools,
    )
    try:
        connection.encrypted_bearer_token = encrypt_credential(
            user.id, body.bearer_token.get_secret_value() if body.bearer_token else None
        )
    except RuntimeError:
        raise HTTPException(503, detail={"code": "encryption_unavailable", "message": "Credential encryption is not configured."}) from None
    async with AsyncSessionFactory() as db, db.begin():
        db.add(connection)
    return _summary(connection)


@router.put("/{connection_id}", response_model=ConnectionSummary, dependencies=[Depends(require_csrf)])
async def update_connection(
    connection_id: UUID, body: ConnectionInput, user: User = Depends(require_user)
) -> ConnectionSummary:
    connection = get_owned_connection(user.id, connection_id)
    if connection is None:
        raise HTTPException(404)
    await _validate_url(str(body.url))
    connection.name = body.name
    connection.server_url = str(body.url)
    connection.enabled_tools = body.enabled_tools
    connection.read_only_tools = body.read_only_tools
    if body.bearer_token is not None:
        value = body.bearer_token.get_secret_value()
        try:
            connection.encrypted_bearer_token = encrypt_credential(user.id, value) if value else None
        except RuntimeError:
            raise HTTPException(503, detail={"code": "encryption_unavailable", "message": "Credential encryption is not configured."}) from None
    async with AsyncSessionFactory() as db, db.begin():
        db.add(connection)
    return _summary(connection)


@router.get("/{connection_id}/tools")
async def connection_tools(connection_id: UUID, user: User = Depends(require_user)) -> list[dict[str, object]]:
    connection = get_owned_connection(user.id, connection_id)
    if connection is None:
        raise HTTPException(404)
    try:
        return await asyncio.to_thread(discover_connection_tools_sync, connection, user.id)
    except Exception as exc:
        raise HTTPException(502, detail={"code": "connection_failed", "message": f"Tool discovery failed ({type(exc).__name__})."}) from None


@router.post("/{connection_id}/test", dependencies=[Depends(require_csrf)])
async def test_connection(connection_id: UUID, user: User = Depends(require_user)) -> dict[str, object]:
    connection = get_owned_connection(user.id, connection_id)
    if connection is None:
        raise HTTPException(404)
    try:
        tools = await asyncio.to_thread(discover_connection_tools_sync, connection, user.id)
    except Exception as exc:
        return {"ok": False, "error": type(exc).__name__}
    return {"ok": True, "tool_count": len(tools)}


@router.delete("/{connection_id}", status_code=204, dependencies=[Depends(require_csrf)])
async def delete_connection(connection_id: UUID, user: User = Depends(require_user)) -> None:
    async with AsyncSessionFactory() as db, db.begin():
        connection = await db.scalar(
            select(MCPConnection).where(MCPConnection.id == connection_id, MCPConnection.user_id == user.id)
        )
        if connection is None:
            raise HTTPException(404)
        await db.delete(connection)

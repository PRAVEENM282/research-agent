from __future__ import annotations

import asyncio
import hashlib
import json
import os
from typing import Any
from uuid import UUID

import httpx2
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from mcp import Client
from mcp.client.streamable_http import streamable_http_client

from src.agents.url_policy import validate_public_http_url
from src.config.settings import settings
from src.db.engine import SyncSessionFactory
from src.db.models import MCPConnection


def _encryption_key() -> bytes:
    if not settings.app_encryption_key:
        raise RuntimeError("MCP credential encryption is not configured.")
    return hashlib.sha256(settings.app_encryption_key.encode("utf-8")).digest()


def encrypt_credential(user_id: UUID, value: str | None) -> bytes | None:
    if not value:
        return None
    return encrypt_user_payload(user_id, value.encode("utf-8"))


def decrypt_credential(user_id: UUID, encrypted: bytes | None) -> str | None:
    if not encrypted:
        return None
    plaintext = decrypt_user_payload(user_id, encrypted)
    return plaintext.decode("utf-8")


def encrypt_user_payload(user_id: UUID, value: bytes) -> bytes:
    nonce = os.urandom(12)
    ciphertext = AESGCM(_encryption_key()).encrypt(nonce, value, user_id.bytes)
    return nonce + ciphertext


def decrypt_user_payload(user_id: UUID, value: bytes) -> bytes:
    return AESGCM(_encryption_key()).decrypt(value[:12], value[12:], user_id.bytes)


def _tool_schema(tool: Any) -> dict[str, Any]:
    schema = getattr(tool, "inputSchema", None)
    if hasattr(schema, "model_dump"):
        schema = schema.model_dump(mode="json")
    elif hasattr(schema, "dict"):
        schema = schema.dict()
    if not isinstance(schema, dict):
        schema = {"type": "object", "properties": {}}
    encoded = json.dumps(schema)
    if len(encoded) > 12_000:
        return {"type": "object", "properties": {}, "description": "Tool schema exceeded the allowed size."}
    return schema


async def _open_mcp(connection: MCPConnection, credential: str | None):
    await validate_public_http_url(connection.server_url)
    headers = {"Authorization": f"Bearer {credential}"} if credential else {}
    client = httpx2.AsyncClient(
        headers=headers,
        timeout=httpx2.Timeout(15.0, read=30.0),
        follow_redirects=False,
        trust_env=False,
    )
    transport = streamable_http_client(connection.server_url, http_client=client)
    return client, transport


async def discover_connection_tools(connection: MCPConnection, user_id: UUID) -> list[dict[str, Any]]:
    credential = decrypt_credential(user_id, connection.encrypted_bearer_token)
    http_client, transport = await _open_mcp(connection, credential)
    try:
        async with Client(transport) as client:
            response = await client.list_tools()
        return [
            {
                "name": str(tool.name)[:200],
                "description": str(tool.description or "")[:1000],
                "input_schema": _tool_schema(tool),
                "configured_read_only": tool.name in set(connection.read_only_tools or []),
                "enabled": tool.name in set(connection.enabled_tools or []),
            }
            for tool in response.tools[:100]
        ]
    finally:
        await http_client.aclose()


async def call_connection_tool(
    connection: MCPConnection, user_id: UUID, tool_name: str, arguments: dict[str, Any]
) -> dict[str, Any]:
    credential = decrypt_credential(user_id, connection.encrypted_bearer_token)
    http_client, transport = await _open_mcp(connection, credential)
    try:
        async with Client(transport) as client:
            result = await client.call_tool(tool_name, arguments)
        blocks = []
        remaining = 12_000
        for item in getattr(result, "content", [])[:40]:
            if remaining <= 0:
                break
            if hasattr(item, "text"):
                value = str(item.text)[: min(3000, remaining)]
                blocks.append({"type": "text", "text": value})
                remaining -= len(value)
            else:
                blocks.append({"type": type(item).__name__})
        return {"is_error": bool(getattr(result, "isError", False)), "content": blocks}
    finally:
        await http_client.aclose()


def discover_connection_tools_sync(connection: MCPConnection, user_id: UUID) -> list[dict[str, Any]]:
    return asyncio.run(discover_connection_tools(connection, user_id))


def call_connection_tool_sync(
    connection: MCPConnection, user_id: UUID, tool_name: str, arguments: dict[str, Any]
) -> dict[str, Any]:
    return asyncio.run(call_connection_tool(connection, user_id, tool_name, arguments))


def get_owned_connection(user_id: UUID, connection_id: UUID) -> MCPConnection | None:
    with SyncSessionFactory() as session:
        return session.query(MCPConnection).filter_by(id=connection_id, user_id=user_id).one_or_none()


def list_owned_connections(user_id: UUID) -> list[MCPConnection]:
    with SyncSessionFactory() as session:
        return list(
            session.query(MCPConnection)
            .filter_by(user_id=user_id)
            .order_by(MCPConnection.created_at.desc())
            .all()
        )

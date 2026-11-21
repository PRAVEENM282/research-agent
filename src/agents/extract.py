from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from urllib.parse import urlparse

import trafilatura

from src.agents.url_policy import fetch_public_page
from src.config.settings import settings


async def fetch_and_extract(url: str) -> dict[str, str | None]:
    final_url, _, raw = await fetch_public_page(
        url,
        timeout=settings.research_timeout_seconds,
        max_bytes=settings.research_max_bytes,
        max_redirects=3,
    )
    html = raw.decode("utf-8", errors="replace")
    text = trafilatura.extract(
        html,
        include_comments=False,
        include_tables=True,
        favor_precision=True,
        deduplicate=True,
    )
    metadata = trafilatura.extract_metadata(html)
    if not text or len(text.strip()) < 80:
        raise RuntimeError("The page did not contain enough extractable text.")
    parsed = urlparse(final_url)
    return {
        "title": ((metadata.title if metadata else None) or parsed.hostname or "Untitled page")[:500],
        "url": final_url,
        "domain": (parsed.hostname or "")[:253],
        "retrieved_at": datetime.now(UTC).isoformat(),
        "excerpt": text.strip()[:12000],
        "status": "EXTRACTED",
    }


def fetch_and_extract_sync(url: str) -> dict[str, str | None]:
    return asyncio.run(fetch_and_extract(url))

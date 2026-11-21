from __future__ import annotations

from urllib.parse import urlparse

import httpx
from pydantic import AnyHttpUrl, BaseModel, Field

from src.config.settings import settings


class SearchHit(BaseModel):
    title: str = Field(max_length=500)
    url: AnyHttpUrl
    snippet: str = Field(default="", max_length=2000)


async def search_web(query: str, limit: int | None = None) -> list[SearchHit]:
    query = " ".join(query.split())[:1000]
    if not query:
        return []
    if not settings.searxng_url:
        raise RuntimeError("Live research is unavailable because SEARXNG_URL is not configured.")
    bound = min(max(1, limit or settings.research_max_results), settings.research_max_results)
    endpoint = settings.searxng_url.rstrip("/") + "/search"
    try:
        async with httpx.AsyncClient(timeout=settings.research_timeout_seconds, follow_redirects=False) as client:
            response = await client.get(endpoint, params={"q": query, "format": "json", "language": "en"})
            response.raise_for_status()
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise RuntimeError(f"Live search failed ({type(exc).__name__}).") from None
    results = data.get("results", []) if isinstance(data, dict) else []
    hits: list[SearchHit] = []
    seen: set[str] = set()
    for item in results:
        if not isinstance(item, dict) or not isinstance(item.get("url"), str):
            continue
        parsed = urlparse(item["url"])
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            continue
        canonical = item["url"].split("#", 1)[0]
        if canonical in seen:
            continue
        seen.add(canonical)
        try:
            hits.append(
                SearchHit(
                    title=str(item.get("title") or parsed.hostname)[:500],
                    url=canonical,
                    snippet=str(item.get("content") or item.get("snippet") or "")[:2000],
                )
            )
        except ValueError:
            continue
        if len(hits) >= bound:
            break
    return hits

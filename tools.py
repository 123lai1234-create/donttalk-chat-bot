"""Function-call tool definitions + executors.

Each tool has:
  - OpenAI function-calling schema (`SCHEMA`)
  - async executor returning JSON-serializable dict
"""
from __future__ import annotations

import json
import logging
from typing import Any, Callable, Awaitable

import httpx

from config import config

log = logging.getLogger("chat-bot.tools")


# ---------------------------------------------------------------------------
# Tool: get_stock
# ---------------------------------------------------------------------------
async def get_stock(ticker: str) -> dict:
    """Fetch latest stock quote from the site API. Ticker like 'AAPL' or 'TSLA'."""
    ticker = (ticker or "").strip().upper()
    if not ticker:
        return {"ok": False, "error": "ticker is required"}

    url = f"{config.SITE_URL}/api/stock/{ticker}"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(url)
            r.raise_for_status()
            data = r.json()
        # strict symbol match
        if isinstance(data, dict) and data.get("symbol", "").upper() != ticker:
            return {"ok": False, "error": f"symbol mismatch: asked {ticker}, got {data.get('symbol')}"}
        return {"ok": True, "ticker": ticker, "data": data}
    except Exception as e:
        log.exception("get_stock failed for %s", ticker)
        return {"ok": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Tool: search_site
# ---------------------------------------------------------------------------
async def search_site(query: str) -> dict:
    """Search inside the site (uses Pagefind if available, falls back to /api/og scan)."""
    q = (query or "").strip()
    if not q:
        return {"ok": False, "error": "query is required"}

    # The Astro site has Pagefind at /pagefind/; this is a placeholder for the
    # RAG search path that will replace this in V1. We surface a stub now so
    # the agent loop is testable end-to-end.
    return {
        "ok": True,
        "query": q,
        "hint": "search_site is a stub in V0; will be replaced by RAG retrieval in V1.",
    }


# ---------------------------------------------------------------------------
# Tool: play_music
# ---------------------------------------------------------------------------
async def play_music(track: str) -> dict:
    """Resolve a music track on the site. Track can be a track id, title, or partial match."""
    t = (track or "").strip()
    if not t:
        return {"ok": False, "error": "track is required"}

    # music.astro uses /music/<id> for tracks; the agent will surface the URL.
    return {
        "ok": True,
        "track_query": t,
        "play_url": f"{config.SITE_URL}/music/",
        "hint": "User should open /music/ to find and play. We can deep-link by id in V1.",
    }


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------
TOOL_REGISTRY: dict[str, Callable[..., Awaitable[dict[str, Any]]]] = {
    "get_stock": get_stock,
    "search_site": search_site,
    "play_music": play_music,
}


# ---------------------------------------------------------------------------
# OpenAI function-calling schemas
# ---------------------------------------------------------------------------
TOOL_SCHEMAS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "get_stock",
            "description": "Get the latest stock quote for a given ticker (e.g. AAPL, TSLA, 2330.TW). Returns price, change, and basic fundamentals if available.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Stock ticker symbol, e.g. AAPL or 2330.TW",
                    },
                },
                "required": ["ticker"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_site",
            "description": "Search the donttalk site for a topic. Use this when the user asks about content on the site (works, music, blog, gene-ai, stock, ngs, etc.).",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search keywords, e.g. 'music production' or 'stem cell'",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "play_music",
            "description": "Find / play a music track on the site. Pass a track id, title, or partial match.",
            "parameters": {
                "type": "object",
                "properties": {
                    "track": {
                        "type": "string",
                        "description": "Track id or title fragment",
                    },
                },
                "required": ["track"],
            },
        },
    },
]


async def execute_tool(name: str, arguments: dict) -> dict:
    fn = TOOL_REGISTRY.get(name)
    if not fn:
        return {"ok": False, "error": f"unknown tool: {name}"}
    try:
        return await fn(**arguments)
    except TypeError as e:
        return {"ok": False, "error": f"bad arguments for {name}: {e}"}
    except Exception as e:
        log.exception("tool %s failed", name)
        return {"ok": False, "error": str(e)}

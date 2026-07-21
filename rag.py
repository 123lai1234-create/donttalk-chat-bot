"""RAG retrieval: query -> top-k chunks from Chroma."""
from __future__ import annotations

import asyncio
import logging
import os
import sys
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import httpx

from config import config

# chromadb is optional — only imported when RAG is actually used (and the
# requirements file may not include it on free-tier deploys). This keeps
# the service importable even if chromadb isn't installed.
_chromadb = None
_Settings = None


def _ensure_chroma():
    global _chromadb, _Settings
    if _chromadb is None:
        try:
            import chromadb as _c
            from chromadb.config import Settings as _S
        except ImportError as e:
            raise RuntimeError(
                "chromadb is not installed; install it via `pip install chromadb` "
                "to enable RAG. (or unset the dependency entirely if you only need fallback)"
            ) from e
        _chromadb = _c
        _Settings = _S
    return _chromadb, _Settings

log = logging.getLogger("rag")

_client = None
_collection = None


def _get_collection():
    global _client, _collection
    if _collection is None:
        if not os.path.isdir(config.CHROMA_DIR):
            return None
        chromadb, Settings = _ensure_chroma()
        _client = chromadb.PersistentClient(path=config.CHROMA_DIR, settings=Settings(anonymized_telemetry=False))
        _collection = _client.get_or_create_collection(
            name=f"{config.SITE_NAME}_pages",
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


async def embed_query(q: str) -> list[float]:
    if not config.OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY not set")
    async with httpx.AsyncClient(timeout=30.0) as c:
        r = await c.post(
            f"{config.OPENAI_BASE_URL}/embeddings",
            headers={"Authorization": f"Bearer {config.OPENAI_API_KEY}"},
            json={"model": config.EMBEDDING_MODEL, "input": q},
        )
        r.raise_for_status()
        data = r.json()
    return data["data"][0]["embedding"]


async def retrieve(query: str, k: int = 5, min_score: float = 0.0) -> list[dict[str, Any]]:
    """Return top-k chunks. Each: {url, title, source, text, score}."""
    col = _get_collection()
    if col is None or col.count() == 0:
        return []
    vec = await embed_query(query)
    res = col.query(query_embeddings=[vec], n_results=k, include=["documents", "metadatas", "distances"])
    out: list[dict] = []
    for i, doc in enumerate(res["documents"][0]):
        meta = res["metadatas"][0][i]
        dist = res["distances"][0][i] if res.get("distances") else None
        score = (1 - dist) if dist is not None else None
        if score is not None and score < min_score:
            continue
        out.append({
            "url": meta.get("url", ""),
            "title": meta.get("title", ""),
            "source": meta.get("source", ""),
            "text": doc,
            "score": score,
        })
    return out


def format_context(chunks: list[dict], max_chars: int = 4000) -> str:
    """Concatenate chunks into a context block, capped at max_chars."""
    if not chunks:
        return ""
    parts: list[str] = []
    used = 0
    for i, c in enumerate(chunks, 1):
        head = f"[{i}] {c['title']} — {c['url']}\n"
        body = c["text"].strip()
        block = head + body + "\n"
        if used + len(block) > max_chars and parts:
            break
        parts.append(block)
        used += len(block)
    return "\n".join(parts)

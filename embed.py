"""Chunk markdown into passages + embed via OpenAI-compatible embeddings endpoint
+ persist to Chroma.

Reads:  data/scraped.jsonl
Writes: data/chroma/  (Chroma persistent dir)
        data/embeddings-meta.json

Usage:
    python -m embed
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Iterable

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import httpx
import tiktoken
import chromadb
from chromadb.config import Settings

from config import config

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("embed")

INPUT_PATH = Path("data/scraped.jsonl")
CHUNK_TOKENS = 500
CHUNK_OVERLAP = 60


def _split_markdown(text: str, max_tokens: int = CHUNK_TOKENS, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split by paragraphs first, then group to fit token budget."""
    enc = tiktoken.get_encoding("cl100k_base")
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: list[str] = []
    buf: list[str] = []
    buf_tokens = 0
    for p in paragraphs:
        pt = len(enc.encode(p))
        if buf_tokens + pt > max_tokens and buf:
            chunks.append("\n\n".join(buf))
            # keep tail for overlap
            tail = []
            tail_tokens = 0
            for prev in reversed(buf):
                pt2 = len(enc.encode(prev))
                if tail_tokens + pt2 > overlap:
                    break
                tail.insert(0, prev)
                tail_tokens += pt2
            buf = tail
            buf_tokens = tail_tokens
        buf.append(p)
        buf_tokens += pt
    if buf:
        chunks.append("\n\n".join(buf))
    return [c for c in chunks if c.strip()]


async def _embed_batch(client: httpx.AsyncClient, texts: list[str]) -> list[list[float]]:
    """Call /v1/embeddings with batch up to 64."""
    out: list[list[float]] = []
    BATCH = 32
    for i in range(0, len(texts), BATCH):
        batch = texts[i : i + BATCH]
        r = await client.post(
            f"{config.OPENAI_BASE_URL}/embeddings",
            headers={"Authorization": f"Bearer {config.OPENAI_API_KEY}"},
            json={"model": config.EMBEDDING_MODEL, "input": batch},
            timeout=60.0,
        )
        if r.status_code >= 400:
            raise RuntimeError(f"embeddings {r.status_code}: {r.text[:300]}")
        data = r.json()
        # ensure same order
        sorted_items = sorted(data["data"], key=lambda x: x["index"])
        out.extend(item["embedding"] for item in sorted_items)
        log.info("embedded %d/%d", i + len(batch), len(texts))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default=str(INPUT_PATH))
    ap.add_argument("--chroma-dir", default=config.CHROMA_DIR)
    ap.add_argument("--collection", default=f"{config.SITE_NAME}_pages")
    ap.add_argument("--limit", type=int, default=0, help="only embed first N pages (debug)")
    args = ap.parse_args()

    if not config.OPENAI_API_KEY:
        log.error("OPENAI_API_KEY is empty; set env first")
        return 2
    if not Path(args.input).exists():
        log.error("missing input: %s (run scraper first)", args.input)
        return 2

    Path(args.chroma_dir).mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=args.chroma_dir, settings=Settings(anonymized_telemetry=False))
    col = client.get_or_create_collection(
        name=args.collection,
        metadata={"hnsw:space": "cosine"},
    )
    log.info("chroma collection: %s (existing count: %d)", args.collection, col.count())

    pages: list[dict] = []
    with open(args.input, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            pages.append(json.loads(line))
    if args.limit:
        pages = pages[: args.limit]
    log.info("loaded %d pages", len(pages))

    docs: list[str] = []
    metas: list[dict] = []
    ids: list[str] = []
    for p_idx, p in enumerate(pages):
        chunks = _split_markdown(p["markdown"])
        for c_idx, chunk in enumerate(chunks):
            cid = f"p{p_idx}-c{c_idx}"
            docs.append(chunk)
            metas.append({
                "url": p["url"],
                "title": p["title"],
                "source": p["source"],
                "chunk_index": c_idx,
            })
            ids.append(cid)
    log.info("total chunks: %d", len(docs))

    if not docs:
        log.warning("no docs to embed")
        return 0

    # dedupe against existing ids
    existing = set(col.get(include=[])["ids"])
    new_idx = [i for i, _id in enumerate(ids) if _id not in existing]
    if not new_idx:
        log.info("nothing new to embed (all %d ids exist)", len(ids))
        return 0
    new_docs = [docs[i] for i in new_idx]
    new_metas = [metas[i] for i in new_idx]
    new_ids = [ids[i] for i in new_idx]
    log.info("to embed: %d (skipping %d already in db)", len(new_docs), len(existing))

    async def run() -> None:
        async with httpx.AsyncClient() as hclient:
            vecs = await _embed_batch(hclient, new_docs)
        col.add(ids=new_ids, documents=new_docs, metadatas=new_metas, embeddings=vecs)
        log.info("chroma collection now has %d docs", col.count())

    asyncio.run(run())

    # write meta
    meta = {
        "collection": args.collection,
        "chroma_dir": args.chroma_dir,
        "embedding_model": config.EMBEDDING_MODEL,
        "total_chunks": len(docs),
        "pages": len(pages),
    }
    Path("data/embeddings-meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    log.info("done. %s", meta)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

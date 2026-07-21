"""Scrape donttalk site pages (online + local fallback) and convert HTML to Markdown chunks.

Output: list[dict] of {url, title, source ('online'|'local'), text, markdown}

Usage:
    python -m scraper --online   # scrape live site
    python -m scraper --local    # read local astro/src/pages/**/*.astro
    python -m scraper --both     # online first, local as fallback for missing
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import re
from pathlib import Path
from typing import Iterable
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from markdownify import markdownify as md

from config import config

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("scraper")

# Pages we know exist (online + local). Local ones are read from astro/src/pages.
LOCAL_PAGES_ROOT = Path(r"D:\project\astro\src\pages")

# Online roots we'll try. Skip external links entirely.
ONLINE_ROOTS = [
    config.SITE_URL,
]


# ---------------------------------------------------------------------------
# Online scrape
# ---------------------------------------------------------------------------
def _normalize_url(href: str, base: str) -> str | None:
    if not href:
        return None
    if href.startswith(("mailto:", "tel:", "javascript:", "#")):
        return None
    abs_url = urljoin(base, href)
    p = urlparse(abs_url)
    if p.netloc and not p.netloc.endswith("donttalk.vercel.app"):
        return None
    # strip fragment
    p = p._replace(fragment="")
    url = p.geturl()
    # only http(s)
    if not url.startswith("http"):
        return None
    return url.rstrip("/")


async def _crawl_online(start: str, max_pages: int = 80) -> list[dict]:
    seen: set[str] = set()
    queue: list[str] = [start.rstrip("/")]
    out: list[dict] = []
    async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
        while queue and len(out) < max_pages:
            url = queue.pop(0)
            if url in seen:
                continue
            seen.add(url)
            try:
                r = await client.get(url)
                if r.status_code != 200 or "text/html" not in r.headers.get("content-type", ""):
                    continue
                html = r.text
            except httpx.HTTPError as e:
                log.warning("fetch %s failed: %s", url, e)
                continue
            soup = BeautifulSoup(html, "lxml")
            # title
            title = (soup.title.string if soup.title and soup.title.string else url).strip()
            # remove nav/header/footer/script/style
            for tag in soup(["nav", "header", "footer", "script", "style", "noscript", "iframe"]):
                tag.decompose()
            text_html = str(soup.body) if soup.body else html
            markdown = md(text_html, heading_style="ATX", strip=["a", "img"])
            markdown = re.sub(r"\n{3,}", "\n\n", markdown).strip()
            if len(markdown) < 50:
                log.info("skip (too short): %s", url)
                continue
            out.append({
                "url": url,
                "title": title,
                "source": "online",
                "markdown": markdown,
            })
            log.info("scraped [%d/%d] %s (%d chars)", len(out), max_pages, url, len(markdown))
            # enqueue more
            for a in soup.find_all("a", href=True):
                nu = _normalize_url(a["href"], url)
                if nu and nu not in seen and nu.startswith(start):
                    queue.append(nu)
    return out


# ---------------------------------------------------------------------------
# Local scrape
# ---------------------------------------------------------------------------
def _read_local_astro(path: Path) -> dict | None:
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8", errors="ignore")
    # crude: extract <body> HTML-ish or just use whole .astro file
    # .astro has frontmatter --- ... --- then template; markdownify on full file works ok
    # we strip frontmatter
    parts = text.split("---", 2)
    body = parts[2] if len(parts) >= 3 else text
    soup = BeautifulSoup(body, "lxml")
    for tag in soup(["script", "style", "noscript", "iframe"]):
        tag.decompose()
    title_tag = soup.find(["h1", "h2", "title"])
    title = title_tag.get_text(strip=True) if title_tag else path.stem
    markdown = md(str(soup), heading_style="ATX", strip=["a", "img"])
    markdown = re.sub(r"\n{3,}", "\n\n", markdown).strip()
    if len(markdown) < 50:
        return None
    # derive URL
    rel = path.relative_to(LOCAL_PAGES_ROOT).with_suffix("").as_posix()
    if rel == "index":
        url = f"{config.SITE_URL}/"
    else:
        url = f"{config.SITE_URL}/{rel}/"
    return {"url": url, "title": title, "source": "local", "markdown": markdown}


def _crawl_local() -> list[dict]:
    out: list[dict] = []
    for p in LOCAL_PAGES_ROOT.rglob("*.astro"):
        item = _read_local_astro(p)
        if item:
            out.append(item)
            log.info("local [%d] %s (%d chars)", len(out), p.name, len(item["markdown"]))
    return out


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["online", "local", "both"], default="both")
    ap.add_argument("--out", default="data/scraped.jsonl")
    ap.add_argument("--max-pages", type=int, default=80)
    args = ap.parse_args()

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)

    results: list[dict] = []
    if args.mode in ("online", "both"):
        for root in ONLINE_ROOTS:
            log.info("crawling online root: %s", root)
            results.extend(await _crawl_online(root, max_pages=args.max_pages))

    if args.mode in ("local", "both"):
        log.info("reading local astro pages from %s", LOCAL_PAGES_ROOT)
        results.extend(_crawl_local())

    # dedupe by url
    seen: set[str] = set()
    deduped: list[dict] = []
    for r in results:
        if r["url"] in seen:
            continue
        seen.add(r["url"])
        deduped.append(r)

    with open(args.out, "w", encoding="utf-8") as f:
        for r in deduped:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    log.info("wrote %d pages to %s", len(deduped), args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

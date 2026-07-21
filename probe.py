"""Probe candidate base URLs to find which one accepts this sk-cp- key.

For each candidate: GET {base}/v1/models with Bearer auth.
- 200 OK = base URL correct + key valid
- 401/403 = base URL wrong OR key invalid for this provider
- 4xx other = base URL reached but rejected
- network error = unreachable

Prints summary. Does NOT log the key, only the prefix.
"""
import asyncio
import io
import sys
import httpx

# Force UTF-8 stdout so error bodies with non-ASCII don't break Windows cp950
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

CANDIDATES = [
    "https://api.openai.com/v1",
    "https://api.openai-proxy.org/v1",
    "https://api.fe8.cn/v1",
    "https://sg.uiuiapi.com/v1",
    "https://api.chatanywhere.com.cn/v1",
    "https://api.openai-sb.com/v1",
    "https://api.gptapi.us/v1",
    "https://api.closeai-proxy.xyz/v1",
    "https://one-api.dev/v1",
    "https://api.deepbricks.ai/v1",
]


async def probe(client: httpx.AsyncClient, key: str, base: str) -> tuple[str, int, str]:
    url = f"{base}/models"
    try:
        r = await client.get(url, headers={"Authorization": f"Bearer {key}"}, timeout=10.0)
        return base, r.status_code, (r.text or "")[:160]
    except httpx.HTTPError as e:
        return base, 0, f"ERR: {type(e).__name__}: {e}"


async def main() -> int:
    key = sys.argv[1] if len(sys.argv) > 1 else ""
    if not key:
        print("usage: probe.py <api-key>")
        return 2
    print(f"probing {len(CANDIDATES)} bases; key prefix: {key[:6]}...{key[-4:]}\n")
    async with httpx.AsyncClient() as client:
        results = await asyncio.gather(*(probe(client, key, b) for b in CANDIDATES))
    for base, status, snippet in results:
        marker = "[OK]" if status == 200 else "[--]"
        print(f"{marker} {status:>3}  {base}\n     {snippet[:140]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

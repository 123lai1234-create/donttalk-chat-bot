"""Quick LLM test."""
import asyncio
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import httpx


async def main():
    base = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
    key = os.environ.get("OPENAI_API_KEY", "")
    if not key:
        print("no key"); return
    print(f"base: {base}")
    print(f"key: {key[:8]}...{key[-4:]} ({len(key)} chars)")
    async with httpx.AsyncClient(timeout=30.0) as c:
        # Non-streaming
        r = await c.post(
            f"{base}/chat/completions",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": "hi, reply just OK"}],
                "stream": False,
                "max_tokens": 10,
            },
        )
        print(f"\n[non-stream] status: {r.status_code}")
        print(f"body: {r.text[:600]}")


asyncio.run(main())

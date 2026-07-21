"""Debug: dump raw LLM SSE stream."""
import asyncio
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import httpx


async def main():
    base = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
    key = os.environ.get("OPENAI_API_KEY", "")
    async with httpx.AsyncClient(timeout=30.0) as c:
        async with c.stream(
            "POST",
            f"{base}/chat/completions",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": "hi"}],
                "stream": True,
                "max_tokens": 50,
            },
        ) as r:
            print(f"status: {r.status_code}")
            async for line in r.aiter_lines():
                if line:
                    print(f"  {line[:200]}")


asyncio.run(main())

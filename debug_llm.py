"""Debug: hit LLM directly, print first few raw SSE events."""
import asyncio
import json
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import httpx

KEY = os.environ["OPENAI_API_KEY"]
BASE = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")


async def main():
    body = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "Reply in 繁體中文."},
            {"role": "user", "content": "用 30 字介紹你自己"},
        ],
        "stream": True,
        "temperature": 0.5,
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        async with client.stream(
            "POST",
            f"{BASE}/chat/completions",
            headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"},
            json=body,
        ) as resp:
            print(f"status: {resp.status_code}")
            print(f"content-type: {resp.headers.get('content-type')}")
            count = 0
            async for line in resp.aiter_lines():
                if not line:
                    continue
                print(f"  LINE: {line[:200]}")
                count += 1
                if count >= 10:
                    print("  ...(truncated)")
                    break


asyncio.run(main())

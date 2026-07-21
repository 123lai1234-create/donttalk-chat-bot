"""Curl-style: dump full SSE stream to stdout."""
import asyncio
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import httpx

CASES = [
    "嗨",
    "介紹一下",
    "蛋白質 AI 怎麼做",
    "幫我查台積電股價",
    "你有做哪些音樂",
]


async def main():
    async with httpx.AsyncClient(timeout=30.0) as c:
        for msg in CASES:
            print(f"\n========== USER: {msg} ==========")
            async with c.stream("POST", "http://127.0.0.1:8765/chat", json={"message": msg, "history": []}) as r:
                if r.status_code != 200:
                    print(f"HTTP {r.status_code}: {await r.aread()}")
                    continue
                async for line in r.aiter_lines():
                    if line:
                        print(line)
            print("-" * 60)


asyncio.run(main())

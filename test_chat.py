"""Test chat end-to-end via SSE."""
import asyncio
import json
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import httpx


async def chat(msg: str):
    print(f"\n=== USER: {msg} ===")
    async with httpx.AsyncClient(timeout=30.0) as c:
        async with c.stream(
            "POST",
            "http://127.0.0.1:8765/chat",
            json={"message": msg, "history": []},
        ) as r:
            print(f"status: {r.status_code}")
            buf = ""
            async for line in r.aiter_lines():
                if line.startswith("event:"):
                    evt = line[6:].strip()
                elif line.startswith("data:"):
                    data = line[5:].strip()
                    try:
                        d = json.loads(data)
                    except json.JSONDecodeError:
                        continue
                    t = d.get("type", "?")
                    if t == "token":
                        print(d.get("content", ""), end="", flush=True)
                    elif t == "tool_call":
                        print(f"\n[tool_call] {d.get('name')} {d.get('arguments')}")
                    elif t == "tool_result":
                        print(f"[tool_result] {d.get('name')}: ok={d.get('result', {}).get('ok')}")
                    elif t == "rag":
                        chunks = d.get("chunks", [])
                        print(f"\n[rag] {len(chunks)} chunks: " + ", ".join(c.get("title", "")[:30] for c in chunks[:3]))
                    elif t == "error":
                        print(f"\n[error] {d.get('message')}")
                    elif t == "done":
                        full = d.get("content", "")
                        if full and not print("\n", end=""):  # only newline if nothing printed
                            pass
                elif line == "":
                    pass
            print()  # final newline


async def main():
    await chat("嗨")
    await chat("介紹一下")
    await chat("蛋白質 AI 怎麼做？")
    await chat("幫我查台積電股價")
    await chat("你有做哪些音樂")


asyncio.run(main())

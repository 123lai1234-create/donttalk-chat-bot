"""FastAPI app: /chat (SSE), /healthz."""
from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import traceback

# Emit a startup marker IMMEDIATELY so we can see in Render logs whether
# the process even reached __main__ vs. crashing during import.
print(f"[startup] python={sys.version.split()[0]} pid={os.getpid()}", file=sys.stderr, flush=True)
print(f"[startup] PORT={os.getenv('PORT', '(unset)')} cwd={os.getcwd()}", file=sys.stderr, flush=True)

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel, Field
    from sse_starlette.sse import EventSourceResponse
    from agent import stream_chat
    from config import config
    print("[startup] all imports ok", file=sys.stderr, flush=True)
except Exception as e:
    print(f"[startup][FATAL] import error: {e}", file=sys.stderr, flush=True)
    traceback.print_exc(file=sys.stderr)
    raise

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
log = logging.getLogger("chat-bot")

app = FastAPI(title=f"{config.SITE_NAME} Chat Bot", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    history: list[dict] = Field(default_factory=list)


@app.get("/healthz")
async def healthz():
    return {
        "ok": True,
        "site": config.SITE_NAME,
        "model": config.OPENAI_MODEL,
        "base_url": config.OPENAI_BASE_URL,
        "has_key": bool(config.OPENAI_API_KEY),
    }


@app.post("/chat")
async def chat(req: ChatRequest):
    if not req.message.strip():
        raise HTTPException(400, "message is empty")

    async def event_gen():
        try:
            async for evt in stream_chat(req.history, req.message):
                yield {"event": evt.get("type", "message"), "data": json.dumps(evt, ensure_ascii=False)}
        except asyncio.CancelledError:
            log.info("client disconnected")
            raise
        except Exception as e:
            log.exception("chat failed")
            yield {"event": "error", "data": json.dumps({"type": "error", "message": str(e)})}

    return EventSourceResponse(event_gen())


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=config.HOST, port=config.PORT, reload=False)

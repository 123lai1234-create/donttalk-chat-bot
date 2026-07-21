"""Create Render Web Service via API + trigger deploy."""
import asyncio
import json
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import httpx

KEY = "rnd_Kj02Io2I0GlOXcahdMK6WZiyYwqp"
TEAM_ID = "tea-d78l7saa214c73aaj5tg"
REPO = "https://github.com/123lai1234-create/donttalk-chat-bot"
HEADERS = {"Authorization": f"Bearer {KEY}", "Accept": "application/json", "Content-Type": "application/json"}


async def main():
    async with httpx.AsyncClient(timeout=60.0) as c:
        # 1. Create web service
        body = {
            "type": "web_service",
            "name": "donttalk-chat-bot",
            "ownerId": TEAM_ID,
            "repo": REPO,
            "branch": "master",
            "autoDeploy": "yes",
            "serviceDetails": {
                "plan": "free",
                "region": "oregon",
                "runtime": "python",
                "healthCheckPath": "/healthz",
                "envSpecificDetails": {
                    "buildCommand": "pip install -r requirements.txt",
                    "startCommand": "uvicorn main:app --host 0.0.0.0 --port $PORT",
                    "pythonVersion": "3.11.9",
                },
            },
            "envVars": [
                {"key": "OPENAI_API_KEY", "value": "PLACEHOLDER"},
                {"key": "OPENAI_BASE_URL", "value": "https://api.fe8.cn/v1"},
                {"key": "OPENAI_MODEL", "value": "gpt-4o-mini"},
                {"key": "EMBEDDING_MODEL", "value": "text-embedding-3-small"},
                {"key": "SITE_URL", "value": "https://donttalk.vercel.app"},
                {"key": "SITE_NAME", "value": "donttalk"},
                {"key": "ALLOWED_ORIGINS", "value": "https://donttalk.vercel.app,http://localhost:4321"},
                {"key": "LOG_LEVEL", "value": "INFO"},
            ],
        }
        print("Creating service...")
        r = await c.post("https://api.render.com/v1/services", headers=HEADERS, json=body)
        print(f"  status: {r.status_code}")
        if r.status_code >= 400:
            print("  body:", r.text)
            return
        data = r.json()
        svc = data.get("service") or data
        sid = svc.get("id")
        url = svc.get("serviceDetails", {}).get("url") or svc.get("url")
        print(f"  service id: {sid}")
        print(f"  url: {url}")
        # 2. Update OPENAI_API_KEY (placeholder -> ask user later if they want to provide a new key)
        # Actually since the current devcto.com key is rejected, we just deploy with placeholder.
        # The agent will fall back to the built-in KB. User can set the real key in Render dashboard later.
        print()
        print(f"DONE. Service: {url}")
        print(f"Service id: {sid}")
        print()
        print("Next: visit the service in Render dashboard, set OPENAI_API_KEY, and watch the first deploy.")


asyncio.run(main())

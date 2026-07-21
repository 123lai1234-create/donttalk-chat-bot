# 部署 SOP — 一條龍 chat-bot 上線

## 概述

- **後端**：FastAPI → Railway（與現有 NGS/AI FastAPI 並行）
- **前端**：Astro（Vercel 既有部署）→ 加 `/api/chat` rewrite 代理到 Railway
- **總時間**：~15 分鐘（含 Railway 部署等啟動 + Vercel 重新 build + 線上驗證）

## 前置：確認 key 狀態

`sk-cp-` key 在 devcto.com / fe8.cn 平台**被標記異常**（`Please check sk key from the platform`）。
- 請到 https://devcto.com 後台查 key 餘額 / 狀態
- 如需新 key，重新生成後用 `python probe.py <new_key>` 確認仍能用 `https://api.fe8.cn/v1`

**好消息**：即使 key 仍異常，後端有 **fallback 模式**（內建 PROJECTS 知識庫 + keyword match），
讓 widget 在沒有 LLM 時也能給用戶合理回應。Key 通了自動切回 LLM。

---

## Step 1: 部署後端到 Railway（~8 分鐘）

### 1.1 確認 Railway CLI 登入
```powershell
railway --version
railway whoami
# 如果未登入：railway login（會開瀏覽器）
```

### 1.2 一鍵部署
```powershell
cd D:\project\chat-bot
.\deploy.ps1
```

互動式：
1. 確認登入 → 自動跳過
2. project 設定 → 選 1（創新 project）或 2（連結現有）
3. 環境變數 → 貼 `OPENAI_API_KEY`（從 devcto.com 拿），其他用預設
4. 自動 `railway up`
5. 等 30 秒拿 URL（`https://chat-bot-xxx.up.railway.app`）

### 1.3 驗證
```powershell
curl https://<your-app>.up.railway.app/healthz
# 應該回 {"ok":true,"site":"donttalk","model":"gpt-4o-mini",...}
```

---

## Step 2: 更新 vercel.json 指向 Railway

把 Step 1 拿到的 URL 貼到 `D:\project\vercel.json`：

```json
"rewrites": [
  { "source": "/api/chat", "destination": "https://<your-app>.up.railway.app/chat" },
  { "source": "/api/chat/:path*", "destination": "https://<your-app>.up.railway.app/chat/:path*" },
  { "source": "/api/:path*", "destination": "/api?p=:path*" }
]
```

---

## Step 3: 重新 build + 部署前端（~3 分鐘）

```powershell
cd D:\project\astro
npm.cmd run build
# 確認 ChatWidget 在 dist：
Select-String -Path dist\index.html -Pattern 'cw-btn' | Select-Object -First 1

# 部署
$env:VERCEL_TOKEN = "<your-vercel-token>"  # session env，不寫檔
cd D:\project\astro
npx vercel deploy --prebuilt --prod --yes --archive tgz
```

**注意**：Hobby plan `git push` auto-deploy 壞掉，**必須手動 `vercel deploy --prebuilt --prod`**。

---

## Step 4: 線上驗證（~2 分鐘）

1. **chat 端到端**：
   - 開 https://donttalk.vercel.app
   - 點左下角 AI 助手
   - 試問「嗨」、「介紹一下」、「蛋白質 AI 怎麼做」
   - 應該看到 SSE token 串流（key 通）或 fallback 模式回應

2. **後端 healthz**：
   ```powershell
   Invoke-WebRequest -Uri "https://<railway>.up.railway.app/healthz" -UseBasicParsing
   ```

3. **CORS 檢查**：
   - DevTools Network → /api/chat request → 看 status code
   - 失敗看後端 log：`railway logs`

---

## 故障排除

### 「CORS error」
檢查 Railway `ALLOWED_ORIGINS` 是否含 `https://donttalk.vercel.app`

### 「502 Bad Gateway」
- 後端沒啟動：看 `railway logs`
- healthcheckPath 不對：確認 `railway.json` 寫 `/healthz`

### 「LLM 401 / key rejected」
- `railway variables` 看 OPENAI_API_KEY 是不是對的
- 重新貼 key：`railway variables set OPENAI_API_KEY=<new>`

### Vercel rewrite 沒生效
- 確認 `vercel.json` 改完 + 已 push / 已重新 deploy
- 確認 rewrite 順序：chat rewrite 必須在 `/api/:path*` 之前

### SSE 串流中斷
- Vercel Hobby plan 函數 10s timeout（但**這是 Serverless Function**，rewrite 走 proxy 不算函數）
- Railway 沒有 timeout 問題
- 確認 chunk size 別太大（fallback 用 4 char/chunk，OK）

---

## 一次性 vs 之後改動

- **後端改動**：`cd D:\project\chat-bot && railway up` 自動重 deploy
- **前端改動**：`cd D:\project\astro && npm run build && npx vercel deploy --prebuilt --prod --yes`
- **環境變數**：`railway variables set KEY=val`
- **RAG 入庫**（等 key 通後）：
  ```powershell
  cd D:\project\chat-bot
  $env:OPENAI_API_KEY = "<key>"
  python -m scraper --mode both --out data/scraped.jsonl
  python -m embed
  railway run python -m embed  # 在 Railway 上跑也行（用同個 env）
  ```

# donttalk Chat Bot (RAG + FunctionCall Agent)

AI 助手，掛在 https://donttalk.vercel.app 全站右下（避開 Pagefind 搜尋按鈕）。

## 架構

```
┌──────────────────┐   POST /chat (SSE)   ┌──────────────────┐
│  Astro 前端      │ ──────────────────►  │  FastAPI 後端    │
│  ChatWidget.astro│ ◄──────────────────  │  Railway         │
│  (左下角氣泡)    │   event: token/...   │  chat-bot/       │
└──────────────────┘                       └──────────────────┘
                                                   │
                                  ┌────────────────┼────────────────┐
                                  ▼                ▼                ▼
                           ┌──────────┐    ┌─────────────┐   ┌──────────┐
                           │ OpenAI   │    │ Chroma      │   │ 站內 API │
                           │ /v1/chat │    │ 12+ pages   │   │ /api/... │
                           │ /embed   │    │ cosine sim  │   │ Function │
                           └──────────┘    └─────────────┘   └──────────┘
```

## V0（已上）
- FastAPI `/chat` SSE 串流
- FunctionCall 工具：`get_stock`, `play_music`, `search_site`
- Astro `ChatWidget.astro`（左下角浮動氣泡）
- 全站 64 頁整合 + 音樂/視頻頁打擾防護

## V1（已上）
- 站內 RAG 知識庫（爬本地 astro pages → embedding → Chroma）
- User 訊息進來 → RAG 召回 top-5 → 注入 system prompt

## 環境變數 (.env)

```bash
OPENAI_API_KEY=sk-cp-...
OPENAI_BASE_URL=https://api.fe8.cn/v1      # 從 probe.py 確認
OPENAI_MODEL=gpt-4o-mini
EMBEDDING_MODEL=text-embedding-3-small
SITE_URL=https://donttalk.vercel.app
ALLOWED_ORIGINS=https://donttalk.vercel.app,http://localhost:4321
CHROMA_DIR=./data/chroma
```

## 本地跑

```bash
# 後端
cd D:\project\chat-bot
.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8765

# 前端 (另一個 terminal)
cd D:\project\astro
npm.cmd run dev
# 訪問 http://localhost:4321 任何頁面，右下角會看到 AI 助手按鈕
```

## RAG 入庫

```bash
# 1. 爬蟲（線上 + 本地，會先試線上、本地 fallback）
cd D:\project\chat-bot
.venv\Scripts\python.exe -m scraper --mode both --out data/scraped.jsonl

# 2. 切片 + embedding + 寫入 Chroma
.venv\Scripts\python.exe -m embed
```

## 部署

### 後端 → Railway
1. Railway → New Project → Deploy from GitHub repo（或 CLI `railway up`）
2. 設定環境變數（同上 .env）
3. Procfile 已在 repo，會自動跑 `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. 拿到 `https://xxx.up.railway.app`

### 前端 → Vercel
1. `astro/vercel.json` 加 rewrite：`/api/chat → https://<railway>.up.railway.app/chat`
2. 部署：`cd astro && npx vercel deploy --prebuilt --prod --yes`
3. 驗證：https://donttalk.vercel.app 開聊天，按鈕發訊息

## ⚠️ Key 狀態

`sk-cp-` 開頭 key 在 devcto.com 平台**被標記異常**（"Please check sk key from the platform"）。
- 請到 https://devcto.com / fe8.cn 後台查 key 狀態（餘額？被禁？）
- 如需新 key，發新 key 後用 `python probe.py <new_key>` 確認 base URL
- key 通了再跑 `embed` 入庫 + 部署

## 檔案

```
chat-bot/
├── main.py           # FastAPI app
├── agent.py          # LLM loop + tool calling + RAG 注入
├── tools.py          # FunctionCall 工具定義
├── rag.py            # RAG 召回
├── scraper.py        # 爬蟲（線上 + 本地 astro）
├── embed.py          # 切片 + embedding + Chroma
├── config.py         # 環境變數
├── probe.py          # base URL 探測
├── requirements.txt
├── Procfile          # Railway
├── runtime.txt       # Python 版本
├── data/             # scraped.jsonl + chroma/（gitignore）
└── README.md
```

## 已知限制
- Vercel Hobby plan 12 functions cap：所以後端獨立部署在 Railway
- `ChatWidget` 對繁體中文最佳，英文也行（system prompt 設定）
- FunctionCall 工具依賴站內 `/api/...` 端點可用
- 音樂/視頻頁面自動隱藏 widget（避免干擾播放）

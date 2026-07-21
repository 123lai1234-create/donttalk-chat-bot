# 互動式 Railway 部署 — 給用戶複製貼上跑的腳本
# 跑完後告訴 Mavis「OK + Railway URL」

# Step 1: 登入（會開瀏覽器，按確認）
cd D:\project\chat-bot
railway login

# Step 2: 創新 project（給 chat-bot 獨立用，不動 NGS API）
#    會問 project name，輸入: chat-bot
railway init --name chat-bot

# Step 3: 設環境變數
railway variables set OPENAI_BASE_URL=https://api.fe8.cn/v1
railway variables set OPENAI_MODEL=gpt-4o-mini
railway variables set EMBEDDING_MODEL=text-embedding-3-small
railway variables set SITE_URL=https://donttalk.vercel.app
railway variables set SITE_NAME=donttalk
railway variables set ALLOWED_ORIGINS=https://donttalk.vercel.app,http://localhost:4321
railway variables set LOG_LEVEL=INFO

# ⚠️ Step 4 貼上你從 devcto.com / fe8.cn 拿的新 key：
# railway variables set OPENAI_API_KEY=sk-cp-你的新key

# Step 5: 部署
railway up --detach

# Step 6: 拿 URL（要等 30-60 秒 deploy 完才會出現）
railway domain
# 輸出會像: https://chat-bot-production-xxxx.up.railway.app

# Step 7: 驗證
curl https://<your-railway-url>/healthz
# 應該回 {"ok":true,...}

# 然後把 URL 貼給 Mavis

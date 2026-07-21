# 一鍵部署 chat-bot 到 Railway
# 用法：cd D:\project\chat-bot && .\deploy.ps1
#
# 流程：
#   1. 確認 railway CLI 登入狀態
#   2. 創 Railway project（互動式）
#   3. 設定環境變數（互動式貼 key）
#   4. 部署
#   5. 印出 Railway URL（給前端 vercel.json 用）

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  chat-bot Railway 部署腳本" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# 1. 確認 railway CLI
$railway = Get-Command railway -ErrorAction SilentlyContinue
if (-not $railway) {
  Write-Host "[X] 找不到 railway CLI，請先裝：npm install -g @railway/cli" -ForegroundColor Red
  exit 1
}
Write-Host "[OK] railway CLI found: $($railway.Source)" -ForegroundColor Green

# 2. 確認登入
Write-Host ""
Write-Host "[?] 確認 Railway 登入狀態..." -ForegroundColor Yellow
& railway whoami 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
  Write-Host "[!] 還沒登入，開始互動式登入..." -ForegroundColor Yellow
  & railway login
  if ($LASTEXITCODE -ne 0) {
    Write-Host "[X] 登入失敗" -ForegroundColor Red
    exit 1
  }
}
Write-Host "[OK] Railway 登入完成" -ForegroundColor Green

# 3. 初始化或連結 project
Write-Host ""
Write-Host "[?] 檢查 Railway project..." -ForegroundColor Yellow
& railway status 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
  Write-Host "[!] 目前目錄還沒連結 Railway project" -ForegroundColor Yellow
  Write-Host "    請選擇：1) 創新 project  2) 連結現有 project" -ForegroundColor Yellow
  $choice = Read-Host "    輸入 1 或 2"
  if ($choice -eq "1") {
    & railway init
  } else {
    & railway link
  }
  if ($LASTEXITCODE -ne 0) {
    Write-Host "[X] project 設定失敗" -ForegroundColor Red
    exit 1
  }
}
Write-Host "[OK] Railway project 已連結" -ForegroundColor Green

# 4. 設定環境變數
Write-Host ""
Write-Host "[?] 設定環境變數（從 .env 讀取或互動式貼上）..." -ForegroundColor Yellow
if (Test-Path ".env") {
  Write-Host "    發現 .env 檔，是否用裡面的值？[Y/n]" -ForegroundColor Yellow
  $useEnv = Read-Host "    "
  if ($useEnv -ne "n") {
    Get-Content .env | Where-Object { $_ -match '^\s*[A-Z_]+=' -and $_ -notmatch '^\s*#' } | ForEach-Object {
      $key = ($_ -split '=', 2)[0].Trim()
      $val = ($_ -split '=', 2)[1].Trim()
      & railway variables set "$key=$val" 2>&1 | Out-Null
      Write-Host "    [set] $key" -ForegroundColor Green
    }
  }
}
Write-Host ""
Write-Host "    至少要設定 OPENAI_API_KEY（去 devcto.com / fe8.cn 拿）" -ForegroundColor Yellow
$key = Read-Host "    貼 OPENAI_API_KEY (Enter 跳過 = 用 .env)"
if ($key) {
  & railway variables set "OPENAI_API_KEY=$key" 2>&1 | Out-Null
  Write-Host "    [set] OPENAI_API_KEY" -ForegroundColor Green
}
# 其餘變數設預設值
& railway variables set "OPENAI_BASE_URL=https://api.fe8.cn/v1" 2>&1 | Out-Null
& railway variables set "OPENAI_MODEL=gpt-4o-mini" 2>&1 | Out-Null
& railway variables set "EMBEDDING_MODEL=text-embedding-3-small" 2>&1 | Out-Null
& railway variables set "SITE_URL=https://donttalk.vercel.app" 2>&1 | Out-Null
& railway variables set "SITE_NAME=donttalk" 2>&1 | Out-Null
& railway variables set "ALLOWED_ORIGINS=https://donttalk.vercel.app,http://localhost:4321" 2>&1 | Out-Null
& railway variables set "LOG_LEVEL=INFO" 2>&1 | Out-Null
Write-Host "    [set] 其他預設值（OPENAI_BASE_URL / MODEL / SITE_URL / ALLOWED_ORIGINS）" -ForegroundColor Green

# 5. 部署
Write-Host ""
Write-Host "[?] 開始部署..." -ForegroundColor Yellow
& railway up --detach
if ($LASTEXITCODE -ne 0) {
  Write-Host "[X] 部署失敗" -ForegroundColor Red
  exit 1
}
Write-Host "[OK] 部署指令已送出" -ForegroundColor Green

# 6. 拿 URL
Write-Host ""
Write-Host "[?] 等 30 秒拿 deploy URL..." -ForegroundColor Yellow
Start-Sleep -Seconds 30
$url = & railway domain 2>&1 | Select-Object -First 1
if ($url) {
  Write-Host ""
  Write-Host "==========================================" -ForegroundColor Green
  Write-Host "  [OK] 部署完成！" -ForegroundColor Green
  Write-Host "  Railway URL: $url" -ForegroundColor Green
  Write-Host "==========================================" -ForegroundColor Green
  Write-Host ""
  Write-Host "下一步：" -ForegroundColor Cyan
  Write-Host "  1. 把 $url 貼給 Mavis" -ForegroundColor Cyan
  Write-Host "  2. 我會更新 D:\project\vercel.json 的 PLACEHOLDER 為 $url" -ForegroundColor Cyan
  Write-Host "  3. 部署前端 Vercel：cd D:\project\astro && npx vercel deploy --prebuilt --prod --yes" -ForegroundColor Cyan
} else {
  Write-Host "[!] 還沒拿到 URL，等 1 分鐘後跑 railway domain 拿" -ForegroundColor Yellow
}

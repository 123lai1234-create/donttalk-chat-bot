"""Client-side fallback when LLM is unavailable.

If the upstream LLM rejects the key / rate-limits / 5xxs, we still want
the chat widget to give a useful answer. This module does:

  1. Keyword + fuzzy match against an inlined PROJECTS knowledge base
  2. Picks the best-matching project + 1-2 sibling projects
  3. Returns a structured response with the same SSE event shape the
     real agent emits (token + tool_result), so the frontend renders
     the same way

The knowledge base is a small subset of the public site content
(music, gene-ai, protein-ai, ngs, stock-app, blog, etc.). It is
deliberately compact — RAG already covers depth when the LLM works.
"""
from __future__ import annotations

import json
import re
from typing import Any

# ---------------------------------------------------------------------------
# Knowledge base
# ---------------------------------------------------------------------------
PROJECTS: list[dict[str, Any]] = [
    {
        "id": "protein-ai",
        "title": "蛋白質 AI 設計系統",
        "url": "/report",
        "icon": "🧬",
        "category": "bio",
        "keywords": [
            "蛋白質", "protein", "esm", "esm-2", "proteinmpnn", "mpnn",
            "rosetta", "序列", "氨基酸", "amino", "語言模型", "language model",
            "reinforce", "rl", "ppi", "binder", "折疊", "fold", "結構",
            "序列設計", "sequence design",
        ],
        "summary": "從序列到結構的 AI 設計 pipeline：ESM-2 嵌入、Bayesian Optimization 找最佳採樣條件、ProteinMPNN 設計序列、REINFORCE 微調。完整報告見 /report。",
    },
    {
        "id": "protein-mpnn",
        "title": "ProteinMPNN 互動工作台",
        "url": "/protein-mpnn",
        "icon": "🧪",
        "category": "bio",
        "keywords": ["proteinmpnn", "mpnn", "互動", "工作台", "3d", "3d 預覽", "突變", "mutation", "rosetta 評分", "設計工具"],
        "summary": "把 ProteinMPNN 塞進瀏覽器：輸入序列、選固定位置、即時看 3D 結構與突變著色。前往 /protein-mpnn 直接玩。",
    },
    {
        "id": "gene-ai",
        "title": "基因 AI 平台",
        "url": "/gene-ai",
        "icon": "🔬",
        "category": "bio",
        "keywords": [
            "基因", "gene", "crispr", "啟動子", "promoter", "dna", "rna",
            "變異", "variant", "knowledge", "知識庫", "rag",
            "opentargets", "ot", "pathway", "pathways", "序列",
        ],
        "summary": "把序列資料、知識文件、變異效應評估整合成一個即時可用的基因資料平台。Live API + RAG 文件搜尋 + OpenTargets / Pathways 知識庫。詳見 /gene-ai。",
    },
    {
        "id": "ngs",
        "title": "NGS 次世代定序",
        "url": "/ngs",
        "icon": "📊",
        "category": "bio",
        "keywords": [
            "ngs", "定序", "sequencing", "rna-seq", "rnaseq", "wgs",
            "scrna", "單細胞", "single cell", "qc", "reads", "coverage",
            "覆蓋度", "fastq", "bam", "vcf", "深度", "depth",
        ],
        "summary": "從實驗設計（深度估算、read 配置）一路到 QC、功能分析的完整 NGS 工作站。內建計算器、圖表集、即時 API。前往 /ngs。",
    },
    {
        "id": "stem-cell",
        "title": "幹細胞研究",
        "url": "/stem-cell",
        "icon": "🧫",
        "category": "bio",
        "keywords": ["幹細胞", "stem cell", "ipsc", "分化", "differentiation", "再生醫學", "regenerative"],
        "summary": "幹細胞 / iPSC 相關研究筆記與工具集。詳見 /stem-cell。",
    },
    {
        "id": "music",
        "title": "音樂作品集",
        "url": "/music",
        "icon": "🎵",
        "category": "creative",
        "keywords": ["音樂", "music", "歌", "song", "mp3", "作詞", "作曲", "編曲", "demo", "playlist"],
        "summary": "原創音樂作品集：作詞、作曲、編曲、demo。支援線上播放、上傳、分類瀏覽。前往 /music。",
    },
    {
        "id": "stock-app",
        "title": "台股均線買賣訊號",
        "url": "/stock",
        "icon": "📈",
        "category": "tools",
        "keywords": ["股票", "stock", "台股", "均線", "ma", "買賣訊號", "signal", "2330", "tsmc", "台積電", "個股", "ticker"],
        "summary": "台股均線買賣訊號小工具。輸入 ticker 看即時均線交叉訊號。Live API 由 Railway FastAPI 提供。前往 /stock。",
    },
    {
        "id": "blog",
        "title": "技術文章",
        "url": "/blog",
        "icon": "📖",
        "category": "writing",
        "keywords": ["blog", "文章", "article", "技術", "tech", "esm2", "蛋白質", "ngs", "trading", "交易"],
        "summary": "ESM-2 / ProteinMPNN / NGS / 量化交易等研究筆記與技術解析。前往 /blog。",
    },
    {
        "id": "thesis",
        "title": "碩士論文 · 遺傳演算法",
        "url": "/thesis",
        "icon": "📝",
        "category": "research",
        "keywords": ["論文", "thesis", "遺傳演算法", "ga", "genetic algorithm", "ppts", "gappts", "etf50", "回測", "backtest", "量化", "trading"],
        "summary": "以 48 檔 ETF50 股票池重建 PPTS × GAPPTS，族群演化視覺化與逐檔回測比較。詳見 /thesis。",
    },
    {
        "id": "interview",
        "title": "面試準備手冊",
        "url": "/interview",
        "icon": "🎯",
        "category": "study",
        "keywords": ["面試", "interview", "模擬", "mock", "數學", "math", "mini project", "衝刺", "sprint", "六週"],
        "summary": "模擬面試問答、數學推導筆記、Mini Project 完整程式碼、六週衝刺計劃。前往 /interview。",
    },
    {
        "id": "works",
        "title": "作品總覽",
        "url": "/works",
        "icon": "💼",
        "category": "portfolio",
        "keywords": ["作品", "works", "portfolio", "全部", "all", "projects", "專案"],
        "summary": "所有專案卡片篩選、即時 API 統計、跨域作品集一覽。前往 /works。",
    },
    {
        "id": "about",
        "title": "關於我",
        "url": "/about",
        "icon": "👤",
        "category": "about",
        "keywords": ["關於", "about", "我", "me", "介紹", "intro", "background", "背景", "經歷", "履歷", "resume", "cv"],
        "summary": "電資工程 × 生醫雙碩士，把 AI / 蛋白質設計 / 基因分析 / NGS 整合成可操作的研究平台。前往 /about 看完整背景。",
    },
    {
        "id": "diving",
        "title": "東北角潛水浪況",
        "url": "/diving",
        "icon": "🤿",
        "category": "tools",
        "keywords": ["潛水", "diving", "東北角", "northeast", "浪況", "windguru", "cwa", "海況", "go", "no-go"],
        "summary": "Windguru + CWA 海況時序圖 + 在地潛點特性的即時潛水決策小工具。前往 /diving。",
    },
    {
        "id": "tools",
        "title": "小工具集",
        "url": "/tools",
        "icon": "🛠️",
        "category": "tools",
        "keywords": ["工具", "tools", "互動", "interactive", "showcase", "demo", "小工具"],
        "summary": "放在瀏覽器即可使用，無需安裝的網頁互動元件 demo 集合。前往 /tools。",
    },
]

# Quick intent to project fallback for common phrasings
GREETINGS = ["hi", "嗨", "你好", "hello", "哈嘍", "您好", "早安", "午安", "晚安"]
ABOUT_SITE = [
    "這是什麼", "這是什麼網站", "什麼網站", "你是誰", "介紹", "site", "about this",
    "what is this", "introduce", "who are you", "介紹自己", "網站",
]


# ---------------------------------------------------------------------------
# Matching
# ---------------------------------------------------------------------------
def _score(text: str, kw: str) -> int:
    t = text.lower()
    k = kw.lower()
    if k in t:
        # length-weighted: longer keywords are more specific
        return len(k) * 2
    # fuzzy: all chars present in order
    ti, ki = 0, 0
    while ti < len(t) and ki < len(k):
        if t[ti] == k[ki]:
            ki += 1
        ti += 1
    return 1 if ki == len(k) else 0


def match(text: str) -> list[dict[str, Any]]:
    """Return top-N matching projects, sorted by score."""
    t = text.strip()
    if not t:
        return []
    scored: list[tuple[int, dict]] = []
    for p in PROJECTS:
        s = sum(_score(t, kw) for kw in p["keywords"])
        if s > 0:
            scored.append((s, p))
    scored.sort(key=lambda x: -x[0])
    return [p for _, p in scored[:3]]


def build_reply(text: str) -> str:
    """Compose a markdown reply for the user. Pure server-side, no LLM."""
    t = text.strip()
    low = t.lower()

    # Greeting
    if any(g in low for g in GREETINGS) and len(t) < 30:
        return (
            "嗨！我是這個站的 AI 助手 👋\n\n"
            "我可以幫你：\n"
            "- 查站內作品（蛋白質 AI / 基因 / NGS / 音樂 / 股票…）\n"
            "- 查股票即時報價（直接給 ticker）\n"
            "- 回答關於本站的任何問題\n\n"
            "問我任何東西試試？\n\n"
            "_註：目前 LLM 連線異常（key 被平台標記），先用站內知識庫 fallback。Key 通了會自動切到 LLM。_"
        )

    # Site intro
    if any(kw in low for kw in ABOUT_SITE) and len(t) < 30:
        return (
            "這是 **JT Lai 的個人作品集**，涵蓋：\n\n"
            "- 🧬 蛋白質 AI 設計（ESM-2 / ProteinMPNN / REINFORCE）\n"
            "- 🔬 基因 AI 平台（RAG + OpenTargets + Pathways）\n"
            "- 📊 NGS 次世代定序工作站\n"
            "- 🎵 原創音樂作品集\n"
            "- 📈 台股均線買賣訊號工具\n"
            "- 📝 碩士論文（遺傳演算法量化）\n\n"
            "完整作品列表：[/works](/works) · 背景：[/about](/about)"
        )

    # Project match
    matches = match(t)
    if matches:
        top = matches[0]
        rest = matches[1:]
        out = [f"**{top['icon']} {top['title']}** — {top['summary']}", "", f"→ [{top['title']}]({top['url']})"]
        for p in rest:
            out.append(f"- {p['icon']} [{p['title']}]({p['url']})：{p['summary']}")
        if rest:
            out.append("")
            out.append("_也許你也有興趣看上面幾個？_")
        return "\n".join(out)

    # Default
    return (
        "抱歉，我沒對到站內具體的主題 😅\n\n"
        "你可以試試：\n"
        "- 「蛋白質 AI 怎麼做」\n"
        "- 「介紹基因平台」\n"
        "- 「查 2330 股價」\n"
        "- 「你有做哪些音樂」\n\n"
        "或直接看：[/works](/works)\n\n"
        "_註：目前 LLM 連線異常（key 被平台標記），先用站內知識庫 fallback。Key 通了會自動切到 LLM。_"
    )


# ---------------------------------------------------------------------------
# SSE event emitter
# ---------------------------------------------------------------------------
async def stream_fallback(text: str):
    """Yield SSE events in the same shape as the real agent."""
    reply = build_reply(text)
    # 1. RAG-like event (we matched from internal KB, not Chroma, but same UX)
    yield {"type": "rag", "chunks": [{"url": "(built-in KB)", "title": "Project knowledge base", "score": 1.0}]}
    # 2. token events (chunk by char to feel streamed)
    chunk = 4
    for i in range(0, len(reply), chunk):
        piece = reply[i : i + chunk]
        yield {"type": "token", "content": piece}
    # 3. done
    yield {"type": "done", "content": reply, "loops": 0, "fallback": True}

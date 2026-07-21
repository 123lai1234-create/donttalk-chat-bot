"""Safely patch index.astro: remove legacy chatbot block. Use UTF-8 bytes only."""
import re
from pathlib import Path

p = Path(r"D:\project\astro\src\pages\index.astro")
text = p.read_text(encoding="utf-8")
print("original size:", len(text), "chars")

# Locate the legacy chatbot block (anchor: "<!-- AI 助手人偶按鈕 -->" through "</Base>")
# We strip everything from the comment line up to (but not including) "</Base>"
anchor = "    <!-- AI 助手人偶按鈕 -->"
end = "</Base>"
i = text.find(anchor)
j = text.rfind(end)
assert i > 0 and j > i, f"anchors not found: i={i}, j={j}"

# Drop the block, keep "</Base>" intact
new = text[:i].rstrip() + "\n" + text[j:].lstrip()

# Now update pageStyles/pageScripts to drop chatbot.css / chatbot.js references
new = new.replace(
    'pageStyles={["/styles/index.css", "/styles/index-live.css", "/styles/index-content.css", "/styles/chatbot.css"]}',
    'pageStyles={["/styles/index.css", "/styles/index-live.css", "/styles/index-content.css"]}',
)
new = new.replace(
    'pageScripts={["https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js", "/scripts/index-ui.js", "/scripts/index-live.js", "/scripts/index-charts.js", "/scripts/chatbot.js"]}',
    'pageScripts={["https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js", "/scripts/index-ui.js", "/scripts/index-live.js", "/scripts/index-charts.js"]}',
)

p.write_text(new, encoding="utf-8")
print("new size:", len(new), "chars")

# Verify: still has the right title (no garbled chars)
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
for i, line in enumerate(new.split("\n")[:15], 1):
    print(f"{i:3d}: {line}")

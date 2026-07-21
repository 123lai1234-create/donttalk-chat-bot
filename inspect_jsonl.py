"""Quick inspector: print summary of scraped.jsonl."""
import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

p = Path(sys.argv[1] if len(sys.argv) > 1 else "data/scraped.jsonl")
if not p.exists():
    print("not found:", p); sys.exit(1)

lines = [l for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
print(f"total pages: {len(lines)}\n")
for i, line in enumerate(lines):
    rec = json.loads(line)
    print(f"[{i+1:2d}] {rec['source']:6s}  {len(rec['markdown']):5d} chars  {rec['url']}")
    print(f"     title: {rec['title'][:60]}")
    print(f"     preview: {rec['markdown'][:80].replace(chr(10),' ')}...")
    print()

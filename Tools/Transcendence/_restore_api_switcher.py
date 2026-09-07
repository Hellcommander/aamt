import json
from pathlib import Path

p = Path(
    r"C:\Users\Arend\.cursor\projects\d-games-Steam-steamapps-common-Transcendence-Extensions"
    r"\agent-transcripts\7e1b39d9-9043-483d-944d-690e64cb4fb4"
    r"\7e1b39d9-9043-483d-944d-690e64cb4fb4.jsonl"
)
out = Path(
    r"D:\games\Steam\steamapps\common\Transcendence\Tools\Transcendence"
    r"\TranscendenceApiSwitcher.ps1"
)

cands = []
for i, line in enumerate(p.open(encoding="utf-8", errors="replace"), 1):
    if "TranscendenceApiSwitcher.ps1" not in line or "contents" not in line:
        continue
    try:
        o = json.loads(line)
    except Exception:
        continue
    for c in o.get("message", {}).get("content", []):
        if c.get("type") != "tool_use":
            continue
        inp = c.get("input") or {}
        path = str(inp.get("path", "")).replace("/", "\\")
        if not path.endswith("TranscendenceApiSwitcher.ps1"):
            continue
        text = inp.get("contents") or inp.get("new_string") or ""
        if len(text) > 500:
            cands.append((i, c.get("name"), len(text), text))

cands.sort(key=lambda x: -x[2])
print("candidates", [(a, b, c) for a, b, c, _ in cands[:5]])
if not cands:
    raise SystemExit("not found")

_, _, _, text = cands[0]
text = (
    text.replace("\u2014", "-")
    .replace("\u2013", "-")
    .replace("\u2192", "->")
    .replace("\u00a0", " ")
)
out.write_text(text, encoding="utf-8-sig")
print("wrote", out.stat().st_size)

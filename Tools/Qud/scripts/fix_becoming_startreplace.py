"""Replace GameText.VariableReplace with StartReplace; fix usings."""
from pathlib import Path
import re

root = Path(r"E:\SteamLibrary\steamapps\workshop\content\333640\3769019231")
files = [
    "Disarm.cs",
    "Dislocate.cs",
    "Redirect.cs",
    "StunningForceCompression.cs",
    "Ignite.cs",
    "Thermoregulation.cs",
    "Haruspicy.cs",
]


def ensure_using(text: str, ns: str) -> str:
    if re.search(rf"(?m)^using\s+{re.escape(ns)}\s*;", text):
        return text
    m = list(re.finditer(r"(?m)^using\s+[^;]+;\s*\n", text))
    if not m:
        return f"using {ns};\n" + text
    last = m[-1]
    return text[: last.end()] + f"using {ns};\n" + text[last.end() :]


def drop_using(text: str, ns: str) -> str:
    return re.sub(rf"(?m)^using\s+{re.escape(ns)}\s*;\s*\n", "", text)


pat = re.compile(r'GameText\.VariableReplace\("(=subject\.[^"]+)",\s*([^)]+)\)')

for name in files:
    p = root / name
    t = p.read_text(encoding="utf-8")
    t = drop_using(t, "XRL.Language")
    t = ensure_using(t, "XRL.World.Text")

    def repl(m: re.Match) -> str:
        return f'"{m.group(1)}".StartReplace().SetSubject({m.group(2)}).ToString()'

    t2, n = pat.subn(repl, t)
    p.write_text(t2, encoding="utf-8")
    print(f"{name}: {n}")

# leftover scan
print("--- leftovers ---")
needles = [
    r"base\.Type\s*=",
    r"\.t\(\)",
    r"\.poss\(",
    r"\.Poss\(",
    r"GameObject\.its\b|\.its\b(?!\s*=)",
    r'AddAction\("',
    r"GameText\.VariableReplace",
    r"using XRL\.Language",
]
for p in root.glob("*.cs"):
    text = p.read_text(encoding="utf-8", errors="ignore")
    for n in needles:
        hits = re.findall(n, text)
        if hits:
            print(f"{p.name}: {n} x{len(hits)}")

"""Fix Becoming (3769019231) CS0618: Type.set, .t(), poss/Poss, .its, AddAction."""
from pathlib import Path
import re

root = Path(r"C:\Users\Arend\AppData\LocalLow\Freehold Games\CavesOfQud\Mods\Becoming v0.5")

TYPE_FILES = [
    "Ignite.cs",
    "Prescience.cs",
    "RewriteOutcome.cs",
    "MirrorRemembers.cs",
    "Haruspicy.cs",
    "Thermoregulation.cs",
]


def ensure_using(text: str, ns: str) -> str:
    if re.search(rf"(?m)^using\s+{re.escape(ns)}\s*;", text):
        return text
    # after last using
    m = list(re.finditer(r"(?m)^using\s+[^;]+;\s*\n", text))
    if not m:
        return f"using {ns};\n" + text
    last = m[-1]
    return text[: last.end()] + f"using {ns};\n" + text[last.end() :]


def strip_type_ctor(text: str) -> str:
    # Remove constructors that only set Type
    text = re.sub(
        r"(?ms)\n\s*public\s+\w+\(\)\s*\{\s*base\.Type\s*=\s*\"Mental\"\s*;\s*\}\s*",
        "\n",
        text,
    )
    # Or just the assignment if ctor has more
    text = re.sub(r"(?m)^\s*base\.Type\s*=\s*\"Mental\"\s*;\s*\n", "", text)
    return text


def the_name(expr: str) -> str:
    return f'GameText.VariableReplace("=subject.the.name=", {expr})'


for name in TYPE_FILES:
    p = root / name
    t = p.read_text(encoding="utf-8")
    n = strip_type_ctor(t)
    if n != t:
        p.write_text(n, encoding="utf-8")
        print(f"Type removed: {name}")

# --- MachineLearning AddAction ---
p = root / "MachineLearning.cs"
t = p.read_text(encoding="utf-8")
t = ensure_using(t, "XRL.World")
old = 'E.AddAction("MachineLearningLog", "view learning log", "ViewMachineLearningLog", null, \'v\', FireOnActor: false, 60);'
new = """E.AddAction(new InventoryAction
                {
                    Name = "MachineLearningLog",
                    Display = "view learning log",
                    Command = "ViewMachineLearningLog",
                    Key = 'v',
                    Default = 60
                });"""
if old in t:
    t = t.replace(old, new)
    p.write_text(t, encoding="utf-8")
    print("MachineLearning AddAction")
else:
    print("MachineLearning AddAction: pattern miss")

# --- LaseBeamVFX poss/Poss ---
p = root / "LaseBeamVFX.cs"
t = p.read_text(encoding="utf-8")
t = ensure_using(t, "XRL.World.Text")
t = t.replace(
    'IComponent<GameObject>.AddPlayerMessage("Your laser beam doesn\'t penetrate " + combatTarget.poss("armor") + ".", \'r\');',
    'IComponent<GameObject>.AddPlayerMessage("Your laser beam doesn\'t penetrate =subject.the.name\'s= armor.".StartReplace().SetSubject(combatTarget).ToString(), \'r\');',
)
t = t.replace(
    'IComponent<GameObject>.AddPlayerMessage(__instance.ParentObject.Poss("laser beam") + " doesn\'t penetrate your armor.", \'g\');',
    'IComponent<GameObject>.AddPlayerMessage("=subject.The.name\'s= laser beam doesn\'t penetrate your armor.".StartReplace().SetSubject(__instance.ParentObject).ToString(), \'g\');',
)
p.write_text(t, encoding="utf-8")
print("LaseBeamVFX")

# --- Haruspicy its + t ---
p = root / "Haruspicy.cs"
t = p.read_text(encoding="utf-8")
t = ensure_using(t, "XRL.Language")
t = ensure_using(t, "XRL.World.Text")
t = t.replace(
    'IComponent<GameObject>.AddPlayerMessage("{{W|You read " + target.t() + ".}} " + DescribeResistances(target));',
    'IComponent<GameObject>.AddPlayerMessage("{{W|You read " + GameText.VariableReplace("=subject.the.name=", target) + ".}} " + DescribeResistances(target));',
)
t = t.replace(
    'if (Popup.ShowYesNo("The reading finds a tear leading to " + target.its + " home dimension. Step through?") != DialogResult.Yes)',
    'if (Popup.ShowYesNo("The reading finds a tear leading to " + GameText.VariableReplace("=subject.its=", target) + " home dimension. Step through?") != DialogResult.Yes)',
)
p.write_text(t, encoding="utf-8")
print("Haruspicy")

# Generic .t() replacements in listed files
T_FILES = {
    "Disarm.cs": [
        (
            'IComponent<GameObject>.AddPlayerMessage("Your attempt to disarm " + attacker.t() + " fails.");',
            'IComponent<GameObject>.AddPlayerMessage("Your attempt to disarm " + GameText.VariableReplace("=subject.the.name=", attacker) + " fails.");',
        ),
    ],
    "Dislocate.cs": [
        (
            'IComponent<GameObject>.AddPlayerMessage("{{C|You wrench " + attacker.t() + "\'s joint out of place!}}");',
            'IComponent<GameObject>.AddPlayerMessage("{{C|You wrench " + GameText.VariableReplace("=subject.the.name\'s=", attacker) + " joint out of place!}}");',
        ),
    ],
    "Redirect.cs": [
        (
            'string direction = PickDirectionS("Redirect " + attacker.t() + "?");',
            'string direction = PickDirectionS("Redirect " + GameText.VariableReplace("=subject.the.name=", attacker) + "?");',
        ),
        (
            'IComponent<GameObject>.AddPlayerMessage("{{C|You redirect " + attacker.t() + " off their feet!}}");',
            'IComponent<GameObject>.AddPlayerMessage("{{C|You redirect " + GameText.VariableReplace("=subject.the.name=", attacker) + " off their feet!}}");',
        ),
        (
            'IComponent<GameObject>.AddPlayerMessage("{{C|You can\'t budge " + attacker.t() + ", but you spoil their footing - their next strike falters!}}");',
            'IComponent<GameObject>.AddPlayerMessage("{{C|You can\'t budge " + GameText.VariableReplace("=subject.the.name=", attacker) + ", but you spoil their footing - their next strike falters!}}");',
        ),
    ],
    "StunningForceCompression.cs": [
        (
            'IComponent<GameObject>.AddPlayerMessage("{{W|The force detonates entirely inside " + target.t() + "!}}");',
            'IComponent<GameObject>.AddPlayerMessage("{{W|The force detonates entirely inside " + GameText.VariableReplace("=subject.the.name=", target) + "!}}");',
        ),
    ],
    "Ignite.cs": [
        (
            '? "{{R|You lay your hand on " + target.t() + " and " + (target.IsPlural ? "they burst" : "it bursts") + " into flame!}}"',
            '? "{{R|You lay your hand on " + GameText.VariableReplace("=subject.the.name=", target) + " and " + (target.IsPlural ? "they burst" : "it bursts") + " into flame!}}"',
        ),
        (
            ': "{{R|You focus your mind and " + target.t() + " burst" + (target.IsPlural ? "" : "s") + " into flame!}}");',
            ': "{{R|You focus your mind and " + GameText.VariableReplace("=subject.the.name=", target) + " burst" + (target.IsPlural ? "" : "s") + " into flame!}}");',
        ),
    ],
    "Thermoregulation.cs": [
        (
            '? "{{R|You lay your hand on " + target.t() + " and " + (target.IsPlural ? "they burst" : "it bursts") + " into flame!}}"',
            '? "{{R|You lay your hand on " + GameText.VariableReplace("=subject.the.name=", target) + " and " + (target.IsPlural ? "they burst" : "it bursts") + " into flame!}}"',
        ),
        (
            ': "{{R|You focus your mind and " + target.t() + " burst" + (target.IsPlural ? "" : "s") + " into flame!}}");',
            ': "{{R|You focus your mind and " + GameText.VariableReplace("=subject.the.name=", target) + " burst" + (target.IsPlural ? "" : "s") + " into flame!}}");',
        ),
        (
            '? "{{c|You lay your hand on " + target.t() + " and " + (target.IsPlural ? "they go" : "it goes") + " cold!}}"',
            '? "{{c|You lay your hand on " + GameText.VariableReplace("=subject.the.name=", target) + " and " + (target.IsPlural ? "they go" : "it goes") + " cold!}}"',
        ),
        (
            ': "{{c|You focus your mind and " + target.t() + " grow" + (target.IsPlural ? "" : "s") + " cold!}}");',
            ': "{{c|You focus your mind and " + GameText.VariableReplace("=subject.the.name=", target) + " grow" + (target.IsPlural ? "" : "s") + " cold!}}");',
        ),
    ],
}

for fname, pairs in T_FILES.items():
    p = root / fname
    t = p.read_text(encoding="utf-8")
    t = ensure_using(t, "XRL.Language")
    changed = 0
    for old, new in pairs:
        if old in t:
            t = t.replace(old, new)
            changed += 1
        else:
            print(f"MISS {fname}: {old[:60]}...")
    p.write_text(t, encoding="utf-8")
    print(f"{fname}: {changed}/{len(pairs)}")

# leftover scan
needles = [r"base\.Type\s*=", r"\.t\(\)", r"\.poss\(", r"\.Poss\(", r"\.its\b", r'AddAction\("']
print("--- leftovers ---")
for p in root.glob("*.cs"):
    text = p.read_text(encoding="utf-8", errors="ignore")
    for n in needles:
        hits = len(re.findall(n, text))
        if hits:
            print(f"{p.name}: {n} x{hits}")

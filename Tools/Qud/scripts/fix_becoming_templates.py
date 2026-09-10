"""Collapse split StartReplace concatenations into single templates."""
from pathlib import Path

root = Path(r"C:\Users\Arend\AppData\LocalLow\Freehold Games\CavesOfQud\Mods\Becoming v0.5")

replacements = {
    "Disarm.cs": [
        (
            'IComponent<GameObject>.AddPlayerMessage("Your attempt to disarm " + "=subject.the.name=".StartReplace().SetSubject(attacker).ToString() + " fails.");',
            'IComponent<GameObject>.AddPlayerMessage("Your attempt to disarm =subject.the.name= fails.".StartReplace().SetSubject(attacker).ToString());',
        ),
    ],
    "Dislocate.cs": [
        (
            'IComponent<GameObject>.AddPlayerMessage("{{C|You wrench " + "=subject.the.name\'s=".StartReplace().SetSubject(attacker).ToString() + " joint out of place!}}");',
            'IComponent<GameObject>.AddPlayerMessage("{{C|You wrench =subject.the.name\'s= joint out of place!}}".StartReplace().SetSubject(attacker).ToString());',
        ),
    ],
    "Redirect.cs": [
        (
            'string direction = PickDirectionS("Redirect " + "=subject.the.name=".StartReplace().SetSubject(attacker).ToString() + "?");',
            'string direction = PickDirectionS("Redirect =subject.the.name=?".StartReplace().SetSubject(attacker).ToString());',
        ),
        (
            'IComponent<GameObject>.AddPlayerMessage("{{C|You redirect " + "=subject.the.name=".StartReplace().SetSubject(attacker).ToString() + " off their feet!}}");',
            'IComponent<GameObject>.AddPlayerMessage("{{C|You redirect =subject.the.name= off their feet!}}".StartReplace().SetSubject(attacker).ToString());',
        ),
        (
            'IComponent<GameObject>.AddPlayerMessage("{{C|You can\'t budge " + "=subject.the.name=".StartReplace().SetSubject(attacker).ToString() + ", but you spoil their footing - their next strike falters!}}");',
            'IComponent<GameObject>.AddPlayerMessage("{{C|You can\'t budge =subject.the.name=, but you spoil their footing - their next strike falters!}}".StartReplace().SetSubject(attacker).ToString());',
        ),
    ],
    "StunningForceCompression.cs": [
        (
            'IComponent<GameObject>.AddPlayerMessage("{{W|The force detonates entirely inside " + "=subject.the.name=".StartReplace().SetSubject(target).ToString() + "!}}");',
            'IComponent<GameObject>.AddPlayerMessage("{{W|The force detonates entirely inside =subject.the.name=!}}".StartReplace().SetSubject(target).ToString());',
        ),
    ],
    "Haruspicy.cs": [
        (
            'IComponent<GameObject>.AddPlayerMessage("{{W|You read " + "=subject.the.name=".StartReplace().SetSubject(target).ToString() + ".}} " + DescribeResistances(target));',
            'IComponent<GameObject>.AddPlayerMessage("{{W|You read =subject.the.name=.}} ".StartReplace().SetSubject(target).ToString() + DescribeResistances(target));',
        ),
        (
            'if (Popup.ShowYesNo("The reading finds a tear leading to " + "=subject.its=".StartReplace().SetSubject(target).ToString() + " home dimension. Step through?") != DialogResult.Yes)',
            'if (Popup.ShowYesNo("The reading finds a tear leading to =subject.its= home dimension. Step through?".StartReplace().SetSubject(target).ToString()) != DialogResult.Yes)',
        ),
    ],
}

# Ignite / Thermoregulation keep ternary for plural verbs; only wrap the name piece is fine,
# but we can do full templates with two branches still using StartReplace on each branch.

ignite_old = '''                    IComponent<GameObject>.AddPlayerMessage(touch
                        ? "{{R|You lay your hand on " + "=subject.the.name=".StartReplace().SetSubject(target).ToString() + " and " + (target.IsPlural ? "they burst" : "it bursts") + " into flame!}}"
                        : "{{R|You focus your mind and " + "=subject.the.name=".StartReplace().SetSubject(target).ToString() + " burst" + (target.IsPlural ? "" : "s") + " into flame!}}");'''

ignite_new = '''                    IComponent<GameObject>.AddPlayerMessage((touch
                        ? "{{R|You lay your hand on =subject.the.name= and " + (target.IsPlural ? "they burst" : "it bursts") + " into flame!}}"
                        : "{{R|You focus your mind and =subject.the.name= burst" + (target.IsPlural ? "" : "s") + " into flame!}}").StartReplace().SetSubject(target).ToString());'''

thermo_pairs = [
    (
        '''                IComponent<GameObject>.AddPlayerMessage(touch
                    ? "{{R|You lay your hand on " + "=subject.the.name=".StartReplace().SetSubject(target).ToString() + " and " + (target.IsPlural ? "they burst" : "it bursts") + " into flame!}}"
                    : "{{R|You focus your mind and " + "=subject.the.name=".StartReplace().SetSubject(target).ToString() + " burst" + (target.IsPlural ? "" : "s") + " into flame!}}");''',
        '''                IComponent<GameObject>.AddPlayerMessage((touch
                    ? "{{R|You lay your hand on =subject.the.name= and " + (target.IsPlural ? "they burst" : "it bursts") + " into flame!}}"
                    : "{{R|You focus your mind and =subject.the.name= burst" + (target.IsPlural ? "" : "s") + " into flame!}}").StartReplace().SetSubject(target).ToString());''',
    ),
    (
        '''                IComponent<GameObject>.AddPlayerMessage(touch
                    ? "{{c|You lay your hand on " + "=subject.the.name=".StartReplace().SetSubject(target).ToString() + " and " + (target.IsPlural ? "they go" : "it goes") + " cold!}}"
                    : "{{c|You focus your mind and " + "=subject.the.name=".StartReplace().SetSubject(target).ToString() + " grow" + (target.IsPlural ? "" : "s") + " cold!}}");''',
        '''                IComponent<GameObject>.AddPlayerMessage((touch
                    ? "{{c|You lay your hand on =subject.the.name= and " + (target.IsPlural ? "they go" : "it goes") + " cold!}}"
                    : "{{c|You focus your mind and =subject.the.name= grow" + (target.IsPlural ? "" : "s") + " cold!}}").StartReplace().SetSubject(target).ToString());''',
    ),
]

for name, pairs in replacements.items():
    p = root / name
    t = p.read_text(encoding="utf-8")
    for old, new in pairs:
        if old not in t:
            print(f"MISS {name}: {old[:70]}...")
        else:
            t = t.replace(old, new)
            print(f"OK {name}")
    p.write_text(t, encoding="utf-8")

p = root / "Ignite.cs"
t = p.read_text(encoding="utf-8")
if ignite_old in t:
    t = t.replace(ignite_old, ignite_new)
    p.write_text(t, encoding="utf-8")
    print("OK Ignite.cs")
else:
    print("MISS Ignite.cs")

p = root / "Thermoregulation.cs"
t = p.read_text(encoding="utf-8")
for i, (old, new) in enumerate(thermo_pairs):
    if old not in t:
        print(f"MISS Thermoregulation[{i}]")
    else:
        t = t.replace(old, new)
        print(f"OK Thermoregulation[{i}]")
p.write_text(t, encoding="utf-8")

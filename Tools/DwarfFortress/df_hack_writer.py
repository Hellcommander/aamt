#!/usr/bin/env python3
"""Write DFHack helper scripts when DFHack is installed."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, Optional

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from df_paths import dfhack_present, dfhack_scripts

HOOKS_LUA = '''-- {modid}_hooks.lua
-- AAMT: announce when custom reactions complete (DFHack).
-- Usage: enable via dfhack.init or script runner: {modid}_hooks

local modid = "{modid}"
local reaction_ids = {{
{reaction_list}
}}

local function onReactionComplete(reaction)
  if not reaction or not reaction.id then return end
  for _, rid in ipairs(reaction_ids) do
    if reaction.id == rid then
      local msg = string.format("[%s] Reaction %s completed.", modid, rid)
      if dfhack and dfhack.gui and dfhack.gui.showAnnouncement then
        dfhack.gui.showAnnouncement(msg, COLOR_LIGHTGREEN)
      else
        print(msg)
      end
    end
  end
end

-- Soft registration: avoid hard failure if event API differs
local ok, err = pcall(function()
  if dfhack and dfhack.onStateChange then
    print(string.format("[%s] hooks loaded (reaction announce ready)", modid))
  end
end)
if not ok then
  print(string.format("[%s] hooks load note: %s", modid, tostring(err)))
end

return {{
  onReactionComplete = onReactionComplete,
  modid = modid,
}}
'''

TEST_LUA = '''-- {modid}_test.lua
-- AAMT: spawn one unit of the custom creature for arena testing.
-- Usage (DFHack console): {modid}_test

local modid = "{modid}"
local creature = "{creature_id}"

local function spawn_test()
  if not dfhack or not dfhack.gui then
    print("[" .. modid .. "] DFHack GUI API unavailable")
    return
  end
  local pos = dfhack.gui.getMousePos and dfhack.gui.getMousePos() or nil
  if not pos and df.global and df.global.cursor then
    pos = xyz2pos(df.global.cursor.x, df.global.cursor.y, df.global.cursor.z)
  end
  if not pos then
    print("[" .. modid .. "] Move cursor / mouse over a tile first")
    return
  end
  -- Prefer create-unit if present (common DFHack script)
  local ok = pcall(function()
    dfhack.run_command("create-unit", creature, "female", tostring(pos.x), tostring(pos.y), tostring(pos.z))
  end)
  if ok then
    print(string.format("[%s] spawn requested: %s", modid, creature))
  else
    print(string.format("[%s] Could not spawn via create-unit; creature id=%s", modid, creature))
    print("Try: create-unit " .. creature .. " female")
  end
end

spawn_test()
'''

ANALYZE_LUA = '''-- {modid}_analyze.lua
-- AAMT: main-thread snapshot of unit under cursor (no worker threads).
-- Usage: {modid}_analyze
-- DF simulation remains single-threaded; this only reads and prints JSON-ish lines.

local modid = "{modid}"
local creature = "{creature_id}"

local function analyze()
  print(string.format("[%s] analyze start for creature raw id %s", modid, creature))
  local unit = nil
  local ok, err = pcall(function()
    if dfhack and dfhack.gui and dfhack.gui.getSelectedUnit then
      unit = dfhack.gui.getSelectedUnit()
    end
  end)
  if not ok then
    print(string.format("[%s] unit API note: %s", modid, tostring(err)))
  end
  if not unit then
    print(string.format("[%s] No selected unit. Select a unit and rerun.", modid))
    print(string.format("[%s] Expected raw creature id: %s", modid, creature))
    return
  end
  local race = unit.race
  local name = "unknown"
  pcall(function()
    if unit.name and dfhack and dfhack.TranslateName then
      name = dfhack.TranslateName(unit.name) or name
    end
  end)
  print(string.format('{"modid":"%s","creature_raw":"%s","unit_id":%s,"race":%s,"name":"%s"}',
    modid, creature, tostring(unit.id or -1), tostring(race or -1), tostring(name)))
  print(string.format("[%s] analyze done (main thread only)", modid))
end

analyze()
'''


def write_dfhack_scripts(
    spec: Dict[str, Any],
    *,
    df_root: Optional[Path] = None,
    also_copy_to: Optional[Path] = None,
) -> Dict[str, Path]:
    """Write hack/scripts helpers if DFHack is present. Otherwise skip."""
    if not dfhack_present(df_root):
        print("[df_hack_writer] DFHack not present; skipping.")
        return {}

    scripts_dir = dfhack_scripts(df_root)
    if scripts_dir is None:
        print("[df_hack_writer] hack/scripts missing; skipping.")
        return {}

    cid = str(spec["id"]).upper()
    modid = f"aamt_{cid.lower()}"
    reactions = spec.get("custom_reactions") or []
    reaction_lines = []
    for r in reactions:
        rid = str(r.get("id") or r.get("name") or "").upper().replace(" ", "_")
        if rid:
            reaction_lines.append(f'  "{rid}",')
    if not reaction_lines:
        reaction_lines.append(f'  "{cid}_SAMPLE_REACTION",')

    hooks = HOOKS_LUA.format(modid=modid, reaction_list="\n".join(reaction_lines))
    test = TEST_LUA.format(modid=modid, creature_id=cid)
    analyze = ANALYZE_LUA.format(modid=modid, creature_id=cid)

    written: Dict[str, Path] = {}
    targets = [scripts_dir]
    if also_copy_to is not None:
        targets.append(Path(also_copy_to))

    for target in targets:
        target.mkdir(parents=True, exist_ok=True)
        for fname, content in (
            (f"{modid}_hooks.lua", hooks),
            (f"{modid}_test.lua", test),
            (f"{modid}_analyze.lua", analyze),
        ):
            hp = target / fname
            hp.write_text(content, encoding="utf-8")
            written[str(hp)] = hp
            print(f"[df_hack_writer] Wrote {hp}")

    return written

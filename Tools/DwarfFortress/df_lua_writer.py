#!/usr/bin/env python3
"""Optional native Lua scripts for DF mods (safe worldgen-friendly stubs)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict


INIT_LUA_TEMPLATE = '''-- AAMT DF Creature Tool — scripts/init.lua
-- Mod id: {mod_id}
-- Creature: {creature_id} ({name})
--
-- This file is intentionally conservative. Premium DF loads scripts/init.lua
-- from mods when present. We avoid worldgen-breaking hooks and only register
-- a no-op / logging path that is safe if the Lua API differs between versions.
--
-- If you expand this, prefer raws.register* patterns documented for your DF
-- version, and test in an arena save first.

local MOD_ID = "{mod_id}"
local CREATURE_ID = "{creature_id}"

local function aamt_log(msg)
  -- dfhack may or may not be present; plain print is fine in script context.
  if type(print) == "function" then
    print(string.format("[AAMT:%s] %s", MOD_ID, tostring(msg)))
  end
end

-- Safe do_once style gate
if rawget(_G, "__AAMT_" .. MOD_ID .. "_INIT") then
  return
end
_G["__AAMT_" .. MOD_ID .. "_INIT"] = true

aamt_log("init.lua loaded for creature " .. CREATURE_ID)

-- Placeholder: no harmful registration.
-- Example (commented) — enable only if your DF build exposes these APIs:
-- if raws and raws.registerInteraction then
--   raws.registerInteraction({{
--     id = MOD_ID .. "_GREETING",
--     -- ...
--   }})
-- end

return true
'''


def write_lua_scripts(
    spec: Dict[str, Any],
    mod_root: Path,
    *,
    force: bool = False,
) -> Path | None:
    """Write scripts/init.lua when include_native_lua is set (or force)."""
    if not force and not spec.get("include_native_lua"):
        return None
    scripts = Path(mod_root) / "scripts"
    scripts.mkdir(parents=True, exist_ok=True)
    cid = str(spec["id"]).upper()
    mod_id = f"aamt_{cid.lower()}"
    name = str(spec.get("name_singular") or cid.lower())
    text = INIT_LUA_TEMPLATE.format(mod_id=mod_id, creature_id=cid, name=name)
    out = scripts / "init.lua"
    out.write_text(text, encoding="utf-8")
    return out

# Prompt pack: Scan

Goal: find the issue, not patch yet.

1. If MODERROR/type conflicts: `mod_errors` + `list_mods` first; `set_project` on the real mod.
2. If runtime/turn bugs: `game_logs` (player/threading) before blaming "external mods".
3. Call `scan_project` so you see every **active-project** file (may be a Workshop mod, not Workspace/src).
4. Call `compile` and quote the diagnostics.
5. `grep` for suspicious APIs (`FireEvent`, `UseEnergy`, `HarmonyPatch`, invented type names).
6. `search` / `lookup_type` to check whether a name is real.
7. If the user mentions turns, energy, runtime behavior, or character generation, `simulate` then `sim_timeline` (use `scenario=chargen` for chargen).
8. Report: file + line/evidence + why it is wrong + what to change. Do not write files unless asked.

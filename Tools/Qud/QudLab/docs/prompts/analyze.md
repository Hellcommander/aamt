# Prompt pack: Analyze (simulate + files)



Goal: explain a runtime/turn bug using live logs, the restricted simulator, and the active mod project.



1. `game_logs` (`kind=threading` or `player`) for in-game repro — CTA no-spend, MODERROR, energy lines, duplicate pool registration.

2. `event_pools` (`scan=true` after mod DLL changes) when suspecting mod MinEvent pool bloat or duplicate FNV1A32 event IDs.

3. `mod_errors` if compile/type conflicts are involved.

4. `simulate` with the right `scenario` (`lag-diagnose` from live logs, `worldgen-getzone` for Starting-game / ResolveCell / GetZone, `crowd-load` / `yd-load` for oversized crowded maps + city water + Yd hydraulic pipes — `--stress` is the ThreadingAPI offload comparison, `npc-cta-no-spend`, `move-input-lag`, `cta-inf-turn`, `player-turn-starvation`, `broodmother-bta-starve`, or `lag-suite` for all) then `sim_timeline`.

5. `set_project` to the real LocalLow/Workshop mod if needed; `scan_project` for full source context.

6. Match timeline kinds (`Energy`, `BeginTakeAction`, `EndTurn`, `Event`, `Refuse`, `Module`, `DataError`, `Worldgen`, `ResolveCell`, `GetZone`, `Hang`, `Builder`) to the code that would produce them.

7. `lookup_type` for event/part APIs you cite.

8. Recommend a concrete code change (file + method). Use `write_file` only in Fix mode.


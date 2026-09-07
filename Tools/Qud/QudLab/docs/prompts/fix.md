# Prompt pack: Fix

Goal: make the **active mod project** compile (and behave) against the live Qud install.

1. For MODERROR / type conflicts: `mod_errors` first, then `list_mods`, `set_project` on the conflicting mod folder.
2. `scan_project` + `compile` before editing. If the bug is runtime, `game_logs` + `simulate` too.
3. `search` / `lookup_type` for every type you touch — never invent XRL names.
4. `write_file` with the **entire** file contents (path relative to active project root).
5. `compile` again. If it still fails, fix remaining diagnostics and repeat.
6. Keep Harmony / IPart / BaseMutation patterns already in the file unless they are the bug.
7. No texture bytes. ThreadingAPI is a separate WIP mod.

# AGENTS.md — Qud Lab

## Ground rules

1. User must own Caves of Qud (Steam/GOG). Never bundle game DLLs or assets into the repo.
1b. Restricted simulator is gitignored / download-only (compiled DLL pack preferred).
   Do not commit sources or `pack/private/`. Public tree uses MIT stubs +
   `SimulatorFactory`. Granted users: `Fetch-PrivatePack.ps1`. Maintainers:
   `Build-PrivatePack.ps1`.
2. Prefer live install metadata: `qudlab setup` then `qudlab serve`, query `http://127.0.0.1:47821/`.
3. Do **not** invent Qud type names — use `/type`, `/search`, `/browse`, `/mutations`, `/genotypes`, `/subtypes`.
4. ThreadingAPI is a **separate WIP mod**, not part of this repo.
5. Simulator is debug-only: no playable arena / save-load. Named scenario `worldgen-getzone` walks bootGame GetZone (hop-capped IndexOf hang; `--stress` skips GetZoneEvent).
6. Unity editor: `E:\tools\Unity_Editor\6000.0.77f1`.
7. ThreadingAPI `ThreadActionLog`: enable **Options → Mod: ThreadingAPI → Multithreaded action logging**, or set `THREADINGAPI_ACTION_LOG=1` → `%LOCALAPPDATA%\QudLab\cache\threading-actions.ndjson`.

## Phase 5 — Local LLM agent (vLLM + optional SGLang frontend)

**Desktop:** double-click `QudLab.bat` (Start serve + Ask / Scan all / Fix / Sim+Ask).

GPU inference runs in **WSL vLLM** (`http://127.0.0.1:8000/v1`). SGLang does **not** merge with vLLM and does **not** take `sglang serve --remote` as an upstream flag. Qud Lab’s `qudlab sglang serve --remote` is a **Windows OpenAI frontend** on `:30000` that forwards to vLLM (real `sglang_router --backend openai` if installed, otherwise the bundled proxy). Cursor / CortexIDE / LM Studio can point at `:30000`; `QUDLAB_LLM_BACKEND=auto` prefers vLLM `:8000` directly.

```powershell
cd "D:\games\Ai assisted toolkit\Tools\Qud\QudLab"
.\QudLab.bat
# or CLI:
.\qudlab-cli.bat serve
# other terminal — GPU backend:
.\qudlab-cli.bat vllm serve --model Qwen/Qwen2.5-Coder-7B-Instruct-AWQ
# optional Windows frontend for Cursor / LM Studio:
.\qudlab-cli.bat sglang serve --remote
.\qudlab-cli.bat ai scan "find bugs in the workspace"
.\qudlab-cli.bat ai fix "make it compile"
.\qudlab-cli.bat ai analyze "why does EndTurn stall"
```

11 GB 2080 Ti (+~2 GB Cursor): **Qwen2.5-Coder-7B-Instruct-AWQ**, `--max-model-len 65536`, `--gpu-memory-utilization 0.72`, `--swap-space 24` (KV spill to RAM). WSL2 vLLM defaults to `VLLM_USE_V2_MODEL_RUNNER=0` (avoids `UVA is not available`) and needs WSL `gcc` for Triton JIT. Ollama remains a fallback (`qwen3:8b` tools / `deepseek-r1:7b`). Env: `QUDLAB_LLM_BACKEND`, `QUDLAB_VLLM_URL`, `QUDLAB_SGLANG_URL`, `OLLAMA_HOST`, `VLLM_MAX_MODEL_LEN`, `VLLM_SWAP_SPACE`, `VLLM_GPU_UTIL`.

## Phase 6 — Real mod IDE + live debug loop

Target **LocalLow + Workshop mods** as the active project (not only `Workspace/src`). Hot-switch without restarting serve. Tail live game logs for diagnose/fix.

```powershell
cd "D:\games\Ai assisted toolkit\Tools\Qud\QudLab"
$cli = ".\artifacts\bin\QudLab.Cli\Release\net8.0\QudLab.Cli.dll"
dotnet $cli serve

# Hot-switch to a real mod (GUI/Unity mod picker does the same via POST)
Invoke-RestMethod -Method POST -Uri http://127.0.0.1:47821/project/set `
  -ContentType application/json -Body '{"query":"Broodmother"}'

# List mods + active project
Invoke-RestMethod http://127.0.0.1:47821/mods
Invoke-RestMethod http://127.0.0.1:47821/project

# Live logs after in-game repro (ThreadingAPI: THREADINGAPI_ACTION_LOG=1)
Invoke-RestMethod "http://127.0.0.1:47821/logs/game?kind=threading&tail=100"
dotnet $cli logs tail --kind player --grep CommandTakeAction
dotnet $cli logs conflicts

# Event pool audit (mod MinEvent bloat + duplicate IDs)
dotnet $cli events scan
dotnet $cli events pools --mod Broodmother --cache Pool
Invoke-RestMethod http://127.0.0.1:47821/events/pools?mod=Broodmother
Invoke-RestMethod -Method POST http://127.0.0.1:47821/events/pools/scan

# Scenario debugger (Unity/GUI scenario dropdown + stress toggle)
Invoke-RestMethod http://127.0.0.1:47821/simulate/scenarios
dotnet $cli simulate --scenario lag-diagnose --turns 8
dotnet $cli simulate --scenario lag-suite --turns 6
dotnet $cli simulate --scenario npc-cta-no-spend --turns 8
dotnet $cli simulate --scenario npc-cta-no-spend --turns 8 --stress
dotnet $cli simulate --scenario move-input-lag --turns 8
dotnet $cli simulate --scenario crowd-load --turns 8
dotnet $cli simulate --scenario crowd-load --turns 8 --stress
dotnet $cli simulate --scenario yd-load --turns 8 --stress
dotnet $cli simulate --scenario cta-inf-turn --turns 8 --stress
```

AI tools added: `list_mods`, `set_project`, `mod_errors`, **`game_logs`**, **`event_pools`**. Analyze flow: `game_logs` → `mod_errors` → `sim_timeline` → `simulate(scenario=…)`. Event bloat: `event_pools` → check `modPooled` + `idConflicts`.

New HTTP endpoints: `GET /mods`, `GET /project`, `POST /project/set`, `GET /project/conflicts`, `POST /project/rescan`, `GET /logs/game`, `GET /simulate/scenarios`, **`GET /events/pools`**, **`POST /events/pools/scan`**.

## Phase 4b — In-Unity object host

Open `UnityProject/` in **6000.0.77f1**. On gate PASS the shell runtime-`LoadFrom`s install Managed (no DLL copies into Assets).

- Host ready → Simulate binds **one entity reference**, runs **≥2 turns** on that same object (`FireEvent` / `UseEnergy`), then `POST /simulation/ingest`
- Later Simulate clicks **continue** on the same `ActiveEntity` (no respawn) for turn debugging
- Host fail / create needs full game boot → falls back to Phase 4a `POST /simulate` (also stamps a stable synthetic `EntityId` across turns)
- Factory create may fail outside a real game session; without a live entity, 4b refuses instead of faking probe-only turns

```powershell
cd "D:\games\Ai assisted toolkit\Tools\Qud\QudLab"
$cli = ".\artifacts\bin\QudLab.Cli\Release\net8.0\QudLab.Cli.dll"
dotnet $cli serve
# then press Simulate in Unity
```

## Phase 4a workflow (CLI synthetic)

```powershell
dotnet $cli simulate --turns 10 --blueprint Human --stress
# Broodmother / ThreadingAPI: player loses turns → world races
dotnet $cli simulate --scenario player-turn-starvation --turns 8
dotnet $cli simulate --scenario player-turn-starvation --turns 8 --stress   # fixed-guard path
# BeforeAI veto from ToBoolean(markup)→false → Brain no-spend inf loop
dotnet $cli simulate --scenario cta-inf-turn --turns 8
dotnet $cli simulate --scenario cta-inf-turn --turns 8 --stress             # fixed (no bool coerce)
# Broodmother player: BTA Check=false zeros energy after hunger tick
dotnet $cli simulate --scenario broodmother-bta-starve --turns 8
dotnet $cli simulate --scenario broodmother-bta-starve --turns 8 --stress   # recover Check=true
# Character generation (EmbarkBuilder modules)
dotnet $cli simulate --scenario chargen --genotype "Mutated Human" --subtype Apostle --mutation Telepathy
dotnet $cli simulate --scenario chargen --genotype "True Kin" --subtype Horticulturist --turns 4
dotnet $cli simulate --scenario chargen --stress   # sweep every genotype×subtype pairing
# New Game stuck on Starting game / GetZone (bug = IndexOf hang; --stress = skip GetZoneEvent)
dotnet $cli simulate --scenario worldgen-getzone
dotnet $cli simulate --scenario worldgen-getzone --zone JoppaWorld.2.23.1.1.10 --stress
# Oversized crowded zone + city water + Yd hydraulic pipes (vanilla zones are 80×25)
# --stress = ThreadingAPI offload of LiquidVolume / IPowerTransmission WantTurnTick
dotnet $cli simulate --scenario crowd-load --turns 8
dotnet $cli simulate --scenario crowd-load --turns 8 --stress
dotnet $cli simulate --scenario yd-load --turns 8 --stress
```

Useful endpoints:

- `POST /simulate` — synthetic cache-validated sim (`scenario=chargen`, `worldgen-getzone`, `crowd-load` / `yd-load` for water+pipe ThreadingAPI A/B)
- `GET /genotypes`, `/subtypes`, `/catalogs?kind=`
- `POST /simulation/ingest` — Unity/object-host timeline → cache
- `GET /simulation/timeline` — structured events
- `GET /simulation/logs`, `/browse`, `POST /compile`, `/diagnostics`
- `POST /ai/run` — local Ollama agent (ask/scan/fix/analyze)

## Assembly references (Copilot)

```powershell
dotnet $cli sync-refs
```

Open `QudLab.code-workspace`. Edit `Workspace/src`.

See `docs/prompts/` and `COPILOT.md`.

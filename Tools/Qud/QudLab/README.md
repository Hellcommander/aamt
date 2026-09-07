# Qud Lab

Unity 6–hosted Caves of Qud mod IDE + restricted simulator + local AI mod-assistant.

**Requires** a Steam or GOG install of Caves of Qud. Default path:

`D:\games\Steam\steamapps\common\Caves of Qud`

Does **not** redistribute game DLLs or assets. Does **not** include ThreadingAPI
(that is a separate WIP mod — not ready for release).

## Unity version

Match the game: **6000.0.77f1**.

Editor install: `E:\tools\Unity_Editor\6000.0.77f1`  
(Hub may still be at `D:\tools\Unity_Hub`.) Open `UnityProject/`.

## Copilot / IDE assembly references (priority)

Without HintPaths to the game's Managed folder, Copilot has no `XRL.*` symbols.

```bat
Setup.bat
```

Then open **`QudLab.code-workspace`** in Cursor and edit `Workspace/src`.
Details: [COPILOT.md](COPILOT.md)

- `qudlab sync-refs` — regenerate HintPaths after game updates (118 IDE essentials; full Managed for Roslyn)
- `qudlab serve` → `/mods`, `/project`, `/logs/game`, `/simulate/scenarios`, `/ai/run`
- `qudlab project set "Broodmother"` — hot-switch active mod (no serve restart)
- `qudlab logs tail --kind threading` — live Player.log + ThreadingAPI NDJSON
- `qudlab simulate --scenario lag-diagnose` — classify freeze/lag from logs + replay repro
- `qudlab simulate --scenario lag-suite` — regression battery (npc-cta-no-spend, move-input-lag, crowd-load, worldgen-getzone, …)
- `qudlab simulate --scenario crowd-load` — oversized zone + NPCs + city water + Yd hydraulic pipes; `--stress` = ThreadingAPI offload; `--yd` denser pipes
- `qudlab compile` — multi-file Workspace/src → `Workspace/bin/` (or `--file` for single)
- `qudlab simulate` — restricted cache-validated turn/thread timeline, `--scenario chargen`, or `--scenario worldgen-getzone` (optional `--remote` + `simhost`)
- Unity Simulate — Phase 4b object host (`LoadFrom` install Managed) with Phase 4a HTTP fallback
- Unity Ask / Scan all / Fix / Sim+Ask — local Ollama agent with Cursor-like tools

## Quick start (desktop GUI)

Double-click **`QudLab.bat`** — opens the control panel (gate / serve / compile / simulate / Ask·Scan·Fix·Sim+Ask).

CLI wrapper: **`qudlab-cli.bat`** (same commands as the DLL).  
Do not create a lowercase `qudlab.bat` next to `QudLab.bat` — on Windows those are the same filename.

```powershell
.\QudLab.bat
.\qudlab-cli.bat serve
.\qudlab-cli.bat ollama scan "find bugs"
```

## Quick start (CLI — works without Unity)

```powershell
cd "D:\games\Ai assisted toolkit\Tools\Qud\QudLab"
.\Setup.bat
# or:
dotnet build QudLab.sln -c Release
$cli = ".\artifacts\bin\QudLab.Cli\Release\net8.0\QudLab.Cli.dll"
dotnet $cli setup
dotnet $cli serve
dotnet $cli compile
dotnet $cli template harmony MyPatch --write
dotnet $cli simulate --turns 10 --blueprint Human
dotnet $cli simulate --scenario chargen --genotype "Mutated Human" --subtype Apostle
```

Env override: `QUDLAB_QUD_PATH`.

## Layout

| Path | Role |
|------|------|
| `src/QudLab.Core` | Path gate, binders, cache models (proprietary core) |
| `src/QudLab.Indexer` | Reflect Managed + parse ObjectBlueprints |
| `src/QudLab.Assistant` | HTTP mod-assistant (`:47821`) for Cursor/Ollama/VS Code/Windsurf |
| `src/QudLab.RoslynCompile` | Compile `.cs` against install Managed DLLs |
| `src/QudLab.Simulator` / `SimHost` | Restricted debug sim (+ optional external process) |
| `src/QudLab.Ai` | Ollama HTTP client (`/api/chat` tools + `/api/generate`) + local agent |
| `src/QudLab.Cli` | Command-line surface |
| `src/QudLab.Gui` | Desktop launcher WinForms (serve + local AI) |
| `QudLab.bat` / `qudlab-cli.bat` | GUI launcher / CLI wrapper |
| `UnityProject/` | Shell UI + Phase 4b Managed host (runtime LoadFrom; no bundled DLLs) |
| `Workspace/src` | Mod sources (Copilot HintPaths) |
| `Workspace/bin` | Roslyn output DLL (never written into game install) |

## Mod assistant (multi-AI)

`qudlab serve` exposes (schema **2.0**):

- `/cache/status` — stamp, stale, XRL counts
- `/search?q=&kind=type|blueprint|mutation|ability|all`
- `/types`, `/type?name=`, `/namespaces`, `/browse?ns=&q=`
- `/blueprints`, `/blueprint?name=`
- `/mutations?q=`, `/abilities?q=`, `/events`
- `/genotypes?q=`, `/subtypes?q=`, `/catalogs?kind=pregen|embark-module|starting-location`
- `/assets?prefix=` — metadata only
- `/refs`, `/mods`, `/project`, `POST /project/set`, `/project/conflicts`, `/logs/game`
- `/project/files`, `/project/file`, `POST /project/write`
- `POST /compile` — Roslyn active mod compile; `GET /diagnostics` — last results
- `POST /simulate` — restricted debug sim; `GET /simulate/scenarios` — lag/turn repro catalog
- `POST /simulation/ingest` — Unity Phase 4b timeline → cache
- `GET /simulation/timeline`, `/simulation/logs`
- `GET /ai/status`, `/ai/models` — Ollama reachability (`http://127.0.0.1:11434`)
- `POST /ai/run` — Cursor-like local agent (`mode`: ask|scan|fix|analyze). Tools: scan every workspace file, grep, compile, simulate, write_file
- `POST /ai/ask`, `/ai/scan`, `/ai/fix`, `/ai/analyze` — same agent, mode implied

Cache auto-rebuilds when missing/stale. Cursor and Ollama share the same localhost cache.
Unity may LoadFrom install Managed for a restricted object-host spike; it never copies those DLLs into the project.

Suggested Ollama models for 11GB 2080 Ti: **`qwen3:8b`** (tools), **`deepseek-r1:7b`** (VRAM-safe reasoning), **`deepseek-r1:14b`** (CPU spillover). See https://github.com/ollama/ollama — env `OLLAMA_HOST`, `QUDLAB_OLLAMA_MODEL`.

## Safety

- No asset/DLL hashes (branch-friendly)
- Fail closed without install / StreamingAssets / Managed
- Simulator refuses non-debug / arena-style use
- Dual license: `LICENSE-MIT.md` + `LICENSE-PROPRIETARY.md`
- Restricted simulator / SimHost / Unity LoadFrom host are **download-only** (gitignored). A clone of AAMT does not include them; unpack with `Fetch-PrivatePack.ps1` after access is granted. MIT `PublicStubs` keep the solution building.

## Agents

See [AGENTS.md](AGENTS.md).

# Copilot / Cursor — Qud assembly references + Phase 4

Without HintPaths + the intelligence cache, Copilot will guess wrong `XRL.*` names.

## One-time / after game update

```bat
Setup.bat
```

## Open in Cursor

Open **`QudLab.code-workspace`**.

Default C# project: `Workspace/QudLab.ModWorkspace.csproj` (HintPaths into your Managed folder).

## Live assistant (Phase 2–6)

```powershell
dotnet .\artifacts\bin\QudLab.Cli\Release\net8.0\QudLab.Cli.dll serve
```

| Endpoint | Purpose |
|----------|---------|
| `/cache/status` | schema 2.0, stale, counts |
| `/search?q=&kind=` | ranked type/blueprint/mutation/ability/genotype/subtype |
| `/browse?ns=&q=` | type browser (namespaces + filtered types) |
| `/type?name=` | full type node |
| `/mutations?q=` | Mutations.xml graph |
| `/genotypes?q=` | Genotypes.xml (chargen) |
| `/subtypes?q=` | Subtypes.xml callings/castes |
| `/abilities?q=` | ActivatedAbilities.xml |
| `/project/files` | active mod paths (hot-switch via `/project/set`) |
| `GET /mods?q=` | LocalLow + Workshop mod list |
| `GET /project` | active root, name, file count |
| `POST /project/set` | `{"path"}` or `{"query":"Broodmother"}` — hot rescan |
| `GET /project/conflicts` | TYPE CONFLICTS from build_log + Player.log |
| `POST /project/rescan` | re-enumerate active project files |
| `GET /logs/game?kind=&tail=` | build / player / threading NDJSON tail |
| `GET /simulate/scenarios` | named debug scenarios + stress support |
| `POST /compile` | Roslyn compile active project → `Workspace/bin/` |
| `/diagnostics` | last compile diagnostics |
| `POST /simulate` | restricted debug sim (turns, `scenario=chargen`, or `scenario=worldgen-getzone`) |
| `POST /simulation/ingest` | Unity Phase 4b timeline → cache |
| `/simulation/timeline` | structured turn/thread timeline + stress |
| `/simulation/logs` | turn log + thread DTOs |
| `/refs` | Managed HintPath list |
| `GET /ai/status` | Ollama up + installed models |
| `POST /ai/run` | local agent (ask/scan/fix/analyze) with tools |

Cache auto-rebuilds on `serve` when missing or stale (Assembly-CSharp mtime / schema).

## Compile / simulate / templates

```powershell
dotnet … QudLab.Cli.dll compile
dotnet … QudLab.Cli.dll simulate --turns 10 --blueprint Human --stress
dotnet … QudLab.Cli.dll simulate --scenario chargen --genotype "Mutated Human" --subtype Apostle
dotnet … QudLab.Cli.dll simulate --scenario chargen --stress
dotnet … QudLab.Cli.dll simulate --scenario worldgen-getzone [--zone JoppaWorld.2.23.1.1.10] [--stress]
dotnet … QudLab.Cli.dll simulate --scenario crowd-load --turns 8 [--yd] [--stress]
dotnet … QudLab.Cli.dll simulate --scenario yd-load --turns 8 --stress
dotnet … QudLab.Cli.dll simhost   # then: simulate --remote
dotnet … QudLab.Cli.dll template part MyPart --write
dotnet … QudLab.Cli.dll template harmony MyPatch --target XRL.World.GameObject --write
```

Unity (`E:\tools\Unity_Editor\6000.0.77f1`):

- Compile → `POST /compile` (no Roslyn in-process)
- Simulate → Phase **4b** Managed `LoadFrom` + reflection ticks when host ready; else Phase **4a** `POST /simulate`
- **Ask / Scan all / Fix / Sim+Ask** → `POST /ai/run` (vLLM / SGLang / Ollama tools: `list_mods`, `set_project`, `game_logs`, `event_pools`, scan, compile, simulate)
- **Mod picker** (◀ mod / mod ▶) + **Conflicts** + **Scenario** + **stress** in Unity shell
- Never copies game DLLs into `UnityProject/`; ThreadingAPI is not bundled

## Local LLM (vLLM backend, optional SGLang frontend)

GPU inference is **vLLM in WSL** (`http://127.0.0.1:8000/v1`). `qudlab sglang serve --remote` is a Windows OpenAI frontend on `:30000` that forwards to vLLM — they do not merge into one runtime. Upstream SGLang has no `--remote` flag; Qud Lab uses `sglang_router --backend openai` when installed, else `scripts/openai-proxy.py`.

```powershell
dotnet … QudLab.Cli.dll vllm serve --model Qwen/Qwen2.5-3B-Instruct
dotnet … QudLab.Cli.dll sglang serve --remote
dotnet … QudLab.Cli.dll ai models
dotnet … QudLab.Cli.dll ai ask "How does IPart WantEvent work? look up the type"
dotnet … QudLab.Cli.dll ai scan "find bugs across all workspace files"
```

Ollama remains a fallback (`ollama serve` then `qudlab ollama ask …`). The agent calls tools (`list_mods`, `set_project`, `game_logs`, `event_pools`, `mod_errors`, `scan_project`, `grep`, `lookup_type`, `compile`, `simulate`, `write_file`) instead of guessing. 2080 Ti (11GB): vLLM `Qwen/Qwen2.5-3B-Instruct`, or Ollama `qwen3:8b` / `deepseek-r1:7b`. Prompt packs: `docs/prompts/agent.md`, `scan.md`, `fix.md`, `analyze.md`.

## Not included

**ThreadingAPI** is a separate WIP mod. No real CoQ object instantiation in SimHost.

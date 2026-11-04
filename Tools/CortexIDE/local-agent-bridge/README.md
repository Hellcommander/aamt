# Local Agent Bridge for CortexIDE (2.1)

Turns CortexIDE into a working AI coding toolset on **local models** (vLLM / SGLang router, Ollama, any OpenAI-compatible server), with file, search and shell tools, `SKILL.md` skills, `.canvas.tsx` canvases, and imported chats (including Cursor exports and agent transcripts).

2.1 renames the extension from `arend.cursor-agent-bridge` to `arend.local-agent-bridge`. Command, view and setting ids moved from `cursorAgentBridge.*` to `localAgentBridge.*`, and the MCP server from `cursor-bridge` to `local-agent-bridge`. On first sync it removes the old `.voidrules` section, `cursor-agent.md` / `00-cursor-agent.md` and the old `mcp.json` entry. `Install-Vsix.ps1` uninstalls the old extension.

## Agent panel

Activity bar → **Local Agent** → **Agent** (or the `$(hubot) Agent` status-bar item, or **Local Agent Bridge: Open Agent**).

CortexIDE's built-in chat ignores extension chat contributions, so the agent runs in its own panel, where tool calls are actually executed:

- **Tools** (Cursor-compatible names): `Read`, `LS`, `Glob`, `Grep` (CortexIDE's bundled ripgrep), `Shell` (PowerShell; quoted `.exe` paths get `&` automatically), `StrReplace`, `Write`, `Delete`, `ReadLints`, `WebFetch`, `list_skills`, `read_skill`, `attempt_completion`. Common aliases (`read_file`, `edit_file`, `run_terminal_cmd`, `find_file`, …) map onto these.
- **Agent loop, not a chatbot**: the model narrates each step, gathers → edits → verifies. A reply that only announces work ("I will fix…"), asks permission, or tutors is pushed back. `attempt_completion` is rejected until a requested edit was made and a requested check (build/test) was run.
- **Text tool calls**: models that print calls as text (`<tool_call>…`, fenced JSON, or bare `{"name":…,"arguments":…}` like Ollama's qwen2.5-coder) are parsed. A backend that rejects native `tools` switches to text mode automatically.
- **Context management without asking the model to summarise**: the context window comes from the backend (`max_model_len` on vLLM; `min(model limit, ollamaNumCtx)` on Ollama). When near the limit, old tool output is compacted first. Then the middle of the run is replaced by a **progress digest** built from the tool calls themselves: files read/changed, searches, commands with exit codes and error lines, and errors hit.
- **Progress index**: after each turn the digest is written to `<workspace>/.cortexide/agent/progress.md` and fed back into the next turn. **Progress** opens it.
- **Skills**: the skill catalog is in the system prompt; when the task names a skill, its body is attached. The agent can also `read_skill`.
- **Project rules**: `AGENTS.md`, `.cursorrules`, `CLAUDE.md`, and `alwaysApply` rules in `.cursor/rules` are included.
- **Import chat**: from a Cursor agent transcript (`~/.cursor/projects/*/agent-transcripts`) or an exported `.md` / `.jsonl` / `.json`. The last 24 turns go into context and all earlier user requests go into the progress index. The input is pre-filled with "continue the unfinished work".
- **Stop** aborts the model call and kills a running shell command.

### Backends

**Model** picks the backend and model. `auto` tries vLLM (`:30000` Qud Lab router, then `:8000`), then Ollama (`:11434`). For vLLM the bearer key comes from `%LOCALAPPDATA%\QudLab\vllm-proxy-key.txt` unless `localAgentBridge.agent.apiKey` is set. Ollama uses its native `/api/chat` so `num_ctx` is honoured; its `/v1` endpoint is stuck at the server default context.

### Safety

- Writes, deletes and shell commands are limited to the open workspace folders plus `localAgentBridge.agent.writableRoots` (e.g. a game's `Mods` folder). Reads may go anywhere unless `readAnywhere` is off.
- Obviously destructive commands (format, wiping a drive root, shutdown, diskpart, …) are always blocked. Set `localAgentBridge.agent.shell` to `confirm` to approve each command, or `off`.
- Deletes go to the recycle bin.

## Skills, canvases, MCP

On startup (or **Sync Skills & Canvases**) `SKILL.md` files from the Cursor, Claude and Agents skill folders are copied into `.cortexide/skills` (64 max), with `.cortexide/agents/local-agent.md`, `.cortexide/rules/00-local-agent.md` and a managed `.voidrules` section for CortexIDE's built-in Agent mode.

The `local-agent-bridge` MCP server (`list_skills`, `read_skill`, `match_skills`, `list_canvases`, `read_canvas`, `import_cursor_chat`, `list_imported_chats`) is registered in `%USERPROFILE%\.cortexide\mcp.json`. It speaks newline-delimited JSON like every MCP client and still answers `Content-Length` framed clients.

`*.canvas.tsx` files (Cursor's canvas format) open in a live preview (custom editor) against a local runtime for the `cursor/canvas` import; **Open Canvas Source** shows the TSX. The bundled `docs-canvas` skill adds `DocsShell`, `TableOfContents`, `DocSection`, `CodeBlock`, `References`.

## Settings

| Setting | Default | |
|---|---|---|
| `localAgentBridge.agent.provider` | `auto` | `auto` / `vllm` / `ollama` / `openai` |
| `localAgentBridge.agent.baseUrl` | | override URL (ends in `/v1`) |
| `localAgentBridge.agent.model` | | empty = first preferred model served |
| `localAgentBridge.agent.apiKey` | | bearer key (empty = Qud Lab key file for vLLM) |
| `localAgentBridge.agent.contextTokens` | `0` | 0 = ask the backend |
| `localAgentBridge.agent.ollamaNumCtx` | `16384` | |
| `localAgentBridge.agent.maxOutputTokens` | `2048` | |
| `localAgentBridge.agent.maxRounds` | `30` | model↔tool rounds per request |
| `localAgentBridge.agent.shell` | `auto` | `auto` / `confirm` / `off` |
| `localAgentBridge.agent.writableRoots` | `[]` | extra folders the agent may change |
| `localAgentBridge.agent.readAnywhere` | `true` | |
| `localAgentBridge.syncOnStartup` | `true` | |
| `localAgentBridge.includeBuiltInSkills` | `true` | include `~/.cursor/skills-cursor` |
| `localAgentBridge.includePluginSkills` | `false` | |
| `localAgentBridge.extraSkillRoots` | `[]` | |
| `localAgentBridge.maxSkills` | `64` | |
| `localAgentBridge.writeWorkspaceFiles` | `true` | |

## Development

Source lives in `Tools\CortexIDE\local-agent-bridge` of the AAMT repo. Don't edit the installed copy under `%USERPROFILE%\.cortexide\extensions`: the next install replaces it.

Needs Node.js (for the tests, `npx` and the MCP server) and CortexIDE at `D:\tools\CortexIDE`.

| Step | Command (from this folder) |
|---|---|
| Test | `node test/run.js` (or `node test/run.js mcp` for one file) |
| Package | `.\Build-Vsix.ps1` → `local-agent-bridge-<version>.vsix` |
| Install | close CortexIDE, then `.\Install-Vsix.ps1` (or `.\Install-Vsix.ps1 -Build`) |
| Live agent run | `node test/run.js --e2e qwen2.5-coder:7b` (needs Ollama or vLLM running) |

- `Build-Vsix.ps1` downloads React 18.3.1 (`media\react*.production.min.js`, MIT, Meta) from unpkg if missing and checks the SHA-256. Those two files are third-party, so they are gitignored (see `THIRD_PARTY.md` at the repo root). It runs the tests, then `npx @vscode/vsce package --no-dependencies`. `-SkipTests` skips the tests.
- `Install-Vsix.ps1` refuses to run while CortexIDE is open. It backs up installed copies to `%USERPROFILE%\.cortexide\extension-backups`, uninstalls the pre-rename `arend.cursor-agent-bridge`, drops its `cursor-bridge` entry from `mcp.json`, and runs `cortexide.cmd --install-extension <vsix> --force`. `-ExtensionsDir <folder>` installs somewhere else instead, which lets you try an install while CortexIDE is open.
- Tests run under plain node. `test/vscode-stub.js` stands in for the `vscode` API, so `extension.test.js` activates the real extension. It checks that every contributed command, view and setting is wired up, and that the startup sync writes `mcp.json`. `mcp-server.test.js` runs the MCP stdio handshake in both framings. Set `CORTEXIDE_APP` if CortexIDE's `resources\app` is not at the default path; the bundled-ripgrep test needs it.
- Bump `version` in `package.json` (and `serverInfo.version` in `mcp-server.js`) for each install you want to tell apart.

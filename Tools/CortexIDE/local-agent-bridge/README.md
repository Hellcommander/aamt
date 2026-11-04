# Local Agent Bridge for CortexIDE (2.2.1)

Turns CortexIDE into a working AI coding toolset on **local models** (vLLM / SGLang router, Ollama, any OpenAI-compatible server) **or on Claude** through the Anthropic Messages API, with file, search and shell tools, `SKILL.md` skills, `.canvas.tsx` canvases, and imported chats (including Cursor exports and agent transcripts).

2.2 adds the **Claude** backend (see Backends below): the same agent loop, tools, skills and progress index, driven by Claude models over the Anthropic API.

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

**Model** picks the backend and model. `auto` tries vLLM (`:30000` Qud Lab router, then `:8000`), then Ollama (`:11434`), then Claude if credentials are set. For vLLM the bearer key comes from `%LOCALAPPDATA%\QudLab\vllm-proxy-key.txt` unless `localAgentBridge.agent.apiKey` is set. Ollama uses its native `/api/chat` so `num_ctx` is honoured; its `/v1` endpoint is stuck at the server default context.

#### Claude (Anthropic API)

**Model → Claude (Anthropic API)** runs the agent on Claude (`claude-opus-5-5` by default; the picker lists every model your key can see, from `GET /v1/models`). Credentials, first match wins:

1. **Agent: Set Claude API Key** — stored in CortexIDE Secret Storage, never in settings.json. Keys come from <https://console.anthropic.com/settings/keys>.
2. `ANTHROPIC_API_KEY` in CortexIDE's environment.
3. `ANTHROPIC_AUTH_TOKEN` (an OAuth bearer token).
4. A profile from the Anthropic CLI: `ant auth login`. The bridge calls `ant auth print-credentials --access-token` and sends the token as a bearer with the `oauth-2025-04-20` beta header.

A **user-scoped** key (`sk-ant-usr-…`) is not tied to a workspace, so the API also needs `anthropic-workspace-id`: set `localAgentBridge.agent.claudeWorkspaceId` (or `ANTHROPIC_WORKSPACE_ID`) to the `wrkspc_…` id from console.anthropic.com → Settings → Workspaces. Workspace-scoped keys (`sk-ant-api03-…`) need nothing extra. Pasted keys may keep stray quotes or angle brackets; they are stripped.

How the Claude backend differs from the local ones (`lib/anthropic.js`, raw HTTPS — the extension ships without node_modules):

- **Streaming** (SSE), so long turns never hit an HTTP timeout; the panel shows "Writing… N chars" while Claude works. 429 / 529 / 5xx and dropped connections are retried.
- **Prompt caching**: a cache breakpoint on the system prompt plus top-level automatic caching of the growing conversation. The end-of-turn status line reports input tokens, how many came from cache, and output tokens.
- **Adaptive thinking** on Claude 4.6+ and 5.x models, with `localAgentBridge.agent.claudeEffort` (`default` / `low` / `medium` / `high` / `xhigh` / `max`). `xhigh` suits hard coding tasks; `low` is the cheap setting. No `temperature` is sent (the current API rejects it).
- **Thinking blocks are replayed** while the transcript is append-only. Newer Claude models bind a thinking block to the exact history before it, so once the loop compacts (rewrites) the transcript the blocks are dropped from then on; if the API still rejects one, the round is resent without them.
- **Context**: the planning window is `min(model window, 200k)` unless `localAgentBridge.agent.contextTokens` is set — the whole conversation is resent every round, so compaction keeps cost in check. `claudeMaxOutputTokens` (default 16000) replaces `maxOutputTokens`; thinking tokens count against it.
- A `refusal` stop reason surfaces as an error in the panel instead of an empty reply.

### Safety

- The file tools (`Write`, `StrReplace`, `Delete`) only change files inside the open workspace folders plus `localAgentBridge.agent.writableRoots` (e.g. a game's `Mods` folder). Reads may go anywhere unless `readAnywhere` is off.
- `Shell` is **not sandboxed**. Its working directory must be inside those folders, but the command itself runs with your user's full rights and can touch any path it names. Use `confirm` (or `off`) if that is too much trust for the model you run.
- Obviously destructive commands (format, wiping a drive root, shutdown, diskpart, …) are always blocked. Set `localAgentBridge.agent.shell` to `confirm` to approve each command, or `off`.
- Deletes go to the recycle bin.

## Skills, canvases, MCP

On startup (or **Sync Skills & Canvases**) `SKILL.md` files from the Cursor, Claude and Agents skill folders are copied into `.cortexide/skills` (64 max), with `.cortexide/agents/local-agent.md`, `.cortexide/rules/00-local-agent.md` and a managed `.voidrules` section for CortexIDE's built-in Agent mode.

The `local-agent-bridge` MCP server (`list_skills`, `read_skill`, `match_skills`, `list_canvases`, `read_canvas`, `import_cursor_chat`, `list_imported_chats`) is registered in `%USERPROFILE%\.cortexide\mcp.json`. It speaks newline-delimited JSON like every MCP client and still answers `Content-Length` framed clients.

`*.canvas.tsx` files (Cursor's canvas format) open in a live preview (custom editor) against a local runtime for the `cursor/canvas` import; **Open Canvas Source** shows the TSX. The bundled `docs-canvas` skill adds `DocsShell`, `TableOfContents`, `DocSection`, `CodeBlock`, `References`.

## Settings

| Setting | Default | |
|---|---|---|
| `localAgentBridge.agent.provider` | `auto` | `auto` / `vllm` / `ollama` / `anthropic` / `openai` |
| `localAgentBridge.agent.baseUrl` | | override URL (ends in `/v1`) |
| `localAgentBridge.agent.model` | | empty = first preferred model served |
| `localAgentBridge.agent.apiKey` | | bearer key (empty = Qud Lab key file for vLLM) |
| `localAgentBridge.agent.contextTokens` | `0` | 0 = ask the backend |
| `localAgentBridge.agent.ollamaNumCtx` | `16384` | |
| `localAgentBridge.agent.maxOutputTokens` | `2048` | local backends |
| `localAgentBridge.agent.claudeMaxOutputTokens` | `16000` | Claude, thinking included |
| `localAgentBridge.agent.claudeEffort` | `default` | `default` / `low` / `medium` / `high` / `xhigh` / `max` |
| `localAgentBridge.agent.claudeWorkspaceId` | | `wrkspc_…`, only for user-scoped keys |
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
| Live agent run | `node test/run.js --e2e qwen2.5-coder:7b` (needs Ollama or vLLM running); `AGENT_PROVIDER=anthropic node test/e2e.js claude-sonnet-5-5` for Claude (needs `ANTHROPIC_API_KEY`) |

- `Build-Vsix.ps1` downloads React 18.3.1 (`media\react*.production.min.js`, MIT, Meta) from unpkg if missing and checks the SHA-256. Those two files are third-party, so they are gitignored (see `THIRD_PARTY.md` at the repo root). It runs the tests, then `npx @vscode/vsce package --no-dependencies`. `-SkipTests` skips the tests.
- `Install-Vsix.ps1` refuses to run while CortexIDE is open. It backs up installed copies to `%USERPROFILE%\.cortexide\extension-backups`, uninstalls the pre-rename `arend.cursor-agent-bridge`, drops its `cursor-bridge` entry from `mcp.json`, and runs `cortexide.cmd --install-extension <vsix> --force`. `-ExtensionsDir <folder>` installs somewhere else instead, which lets you try an install while CortexIDE is open.
- Tests run under plain node. `test/vscode-stub.js` stands in for the `vscode` API, so `extension.test.js` activates the real extension. It checks that every contributed command, view and setting is wired up, and that the startup sync writes `mcp.json`. `mcp-server.test.js` runs the MCP stdio handshake in both framings. `llm.test.js` drives the Claude backend against a mock Messages API (message conversion, SSE parsing, caching and thinking fields, retries, credential precedence). Set `CORTEXIDE_APP` if CortexIDE's `resources\app` is not at the default path; the bundled-ripgrep test needs it.
- Bump `version` in `package.json` (and `serverInfo.version` in `mcp-server.js`) for each install you want to tell apart.

# Local Agent Bridge for CortexIDE (2.6.0)

Turns CortexIDE into a working AI coding toolset on **local models** (vLLM / SGLang router, Ollama, any OpenAI-compatible server) **or on Claude** through the Anthropic Messages API, with file, search and shell tools, `SKILL.md` skills, `.canvas.tsx` canvases, and imported chats (including Cursor exports and agent transcripts).

2.6 redesigns the Agent panel and adds **browser sign-in**. The top bar shows the backend and model in use with a status dot (click it to switch); **⋯** opens one menu for model, effort, API key, permissions, undo, find-in-chat, import, skills and settings; an empty chat shows a set-up card and example prompts; a problem shows as a banner with the buttons that fix it; chips under the input show shell mode, permission mode and effort. **Sign in with Claude** (panel, menu, or the command *Agent: Sign In with Claude (browser)*) runs the official `claude auth login` in a terminal: your browser opens, the credentials stay in Claude Code's own store, and the extension only polls `claude auth status`. Once signed in, the panel switches to the Claude Code engine with `claudeCodeAuth: login`. The page itself is `media/agent-panel.html`.

2.5 adds the **Claude Code engine** (see Backends below): the Agent panel can hand the whole turn to the installed Claude Code CLI, so it behaves like the Claude app — same tools, system prompt, context handling, skills, `CLAUDE.md`, MCP servers and subagents.

2.4 makes small local models drive the agent much more reliably: streamed local replies (no idle timeouts, live progress, reasoning kept apart), a far more forgiving text tool-call parser, indentation-tolerant edits, dropped cut-off writes, a stall detector, project check commands and a workspace map in the prompt, and a one-time "run the check" nudge.

2.3 makes the agent work more like a full coding agent: a `TodoWrite` plan shown in the panel, `MultiEdit`, a read-only `Task` sub-agent, parallel look-ups, numbered `Read` output, a read-before-edit guard, editor errors reported after each edit, git status in context, and a per-turn changed-files card with diff and **Undo**.

2.2 adds the **Claude** backend (see Backends below): the same agent loop, tools, skills and progress index, driven by Claude models over the Anthropic API.

2.1 renames the extension from `arend.cursor-agent-bridge` to `arend.local-agent-bridge`. Command, view and setting ids moved from `cursorAgentBridge.*` to `localAgentBridge.*`, and the MCP server from `cursor-bridge` to `local-agent-bridge`. On first sync it removes the old `.voidrules` section, `cursor-agent.md` / `00-cursor-agent.md` and the old `mcp.json` entry. `Install-Vsix.ps1` uninstalls the old extension.

## Agent panel

Activity bar → **Local Agent** → **Agent** (or the `$(hubot) Agent` status-bar item, or **Local Agent Bridge: Open Agent**).

CortexIDE's built-in chat ignores extension chat contributions, so the agent runs in its own panel, where tool calls are actually executed:

- **Tools** (Cursor-compatible names): `Read` (numbered lines), `LS`, `Glob` (newest first), `Grep` (CortexIDE's bundled ripgrep; `output_mode` content / files_with_matches / count, `context`, `case_sensitive`), `Shell` (PowerShell; quoted `.exe` paths get `&` automatically; optional per-call `timeout`), `StrReplace`, `MultiEdit` (several replacements in one file, all-or-nothing), `Write`, `Delete`, `ReadLints`, `WebFetch`, `TodoWrite`, `Task`, `list_skills`, `read_skill`, `attempt_completion`. Common aliases (`read_file`, `edit_file`, `run_terminal_cmd`, `find_file`, `multi_edit`, `todo_write`, …) map onto these.
- **Agent loop, not a chatbot**: the model narrates each step, plans → gathers → edits → verifies. A reply that only announces work ("I will fix…"), asks permission, or tutors is pushed back. `attempt_completion` is rejected until a requested edit was made, a requested check (build/test) was run, and the todo list has no open items.
- **Plan**: for multi-step work the agent keeps a `TodoWrite` list, shown live above the input box.
- **Parallel look-ups**: consecutive read-only calls in one reply (`Read`, `Grep`, `Glob`, `LS`, `WebFetch`, `Task`, …) run side by side.
- **Task sub-agent**: `Task` runs a read-only research agent (Read / LS / Glob / Grep / WebFetch, up to 16 rounds) in its own context and returns only its report, so broad searches don't fill the main context. Turn off with `localAgentBridge.agent.subagents`.
- **Safer edits** (`requireReadBeforeEdit`): `Write` over an existing file needs a prior `Read`; `StrReplace` / `MultiEdit` on an unread file only accept an exact unique match (e.g. copied from `Grep` output); and a file that changed on disk since the agent read it must be read again. Line-number prefixes copied from `Read` output into `old_string` are tolerated, and when `old_string` only differs in indentation or trailing spaces from exactly one place, that place is edited and `new_string` re-indented to match (the result says so). Repeated failed edits on one file get firmer advice (short `old_string`, then a full rewrite). Each edit result shows the edited lines plus any errors the language server now reports for that file (`diagnosticsAfterEdit`).
- **Changed files + Undo**: after each turn (also a stopped one) a card lists the files the agent's file tools changed, with +/− line counts. Click a file for a before ↔ now diff; **Undo** (or **Agent: Undo Last Turn's Edits**) restores them, deletes files it created and brings back files it deleted, and warns first if a file was changed again since. Snapshots live in memory for the last 10 turns until CortexIDE restarts. Changes made through `Shell` are not captured.
- **Project context**: branch and `git status`, the project's check commands (npm/pnpm/yarn scripts, `dotnet build/test`, `pytest`, `cargo`, `go`, `make`, a `run-tests.ps1`-style script) and a two-level workspace map go into the system prompt. If the agent changed code and never ran a check, its first `attempt_completion` is sent back once with the command to run.
- **Stall detector**: on an edit task, after 6 rounds of only looking, the agent is told to state the root cause and make the change (repeated every 4 rounds until it edits). When the user reports a failure, the rules say to reproduce it first.
- **Text tool calls**: models that print calls as text are parsed: `<tool_call>{json}</tool_call>`, Qwen3-Coder `<function=…><parameter=…>`, Llama `<function=…>{json}` and `<|python_tag|>`, Mistral `[TOOL_CALLS]`, fenced JSON, bare JSON (Ollama qwen2.5-coder), and flat `{"tool": …, "path": …}`. JSON is repaired when a model puts raw newlines/tabs or `\'` / `\d` escapes in code strings, leaves trailing commas, or is cut off. `<think>` reasoning is removed first, so calls a model only considered are never run. A backend that rejects native `tools` switches to text mode automatically.
- **Local streaming**: Ollama (NDJSON) and OpenAI-compatible servers (SSE) are streamed, so a CPU-offloaded model never idles the socket into a timeout (limit 15 min of silence), the panel shows "Writing…" / "Thinking…" progress, and reasoning (`thinking`, `reasoning_content`) stays out of the answer and the history. A server that ignores `stream` still works.
- **Output limit**: a reply cut at `maxOutputTokens` is reported; a cut-off `Write` / `StrReplace` is dropped instead of saving a partial file, and the model is told to write big files in parts. A thinking model that spent the whole budget thinking is told to think less. Raise `maxOutputTokens` (4096–8192) for qwen3 / deepseek-r1.
- **Context management without asking the model to summarise**: the context window comes from the backend (`max_model_len` on vLLM; `min(model limit, ollamaNumCtx)` on Ollama). When near the limit, old tool output is compacted first. Then the middle of the run is replaced by a **progress digest** built from the tool calls themselves: files read/changed, searches, commands with exit codes and error lines, and errors hit.
- **Progress index**: after each turn the digest is written to `<workspace>/.cortexide/agent/progress.md` and fed back into the next turn. **Progress** opens it.
- **Skills**: the skill catalog is in the system prompt; when the task names a skill, its body is attached. The agent can also `read_skill`.
- **Project rules**: `AGENTS.md`, `.cursorrules`, `CLAUDE.md`, and `alwaysApply` rules in `.cursor/rules` are included.
- **Import chat**: from a Cursor agent transcript (`~/.cursor/projects/*/agent-transcripts`) or an exported `.md` / `.jsonl` / `.json`. The last 24 turns go into context and all earlier user requests go into the progress index. The input is pre-filled with "continue the unfinished work".
- **Stop** aborts the model call and kills a running shell command.

### Backends

**Model** picks the backend and model. `auto` tries vLLM (`:30000` Qud Lab router, then `:8000`), then Ollama (`:11434`), then Claude if credentials are set. For vLLM the bearer key comes from `%LOCALAPPDATA%\QudLab\vllm-proxy-key.txt` unless `localAgentBridge.agent.apiKey` is set. Ollama uses its native `/api/chat` so `num_ctx` is honoured; its `/v1` endpoint is stuck at the server default context.

#### Claude Code engine

**Model → Claude Code (same engine as the Claude app)** sets `localAgentBridge.agent.provider` to `claude-code`. The bridge then does not run its own loop: it starts the installed CLI headless for each turn (`claude -p --output-format stream-json --input-format stream-json`, `lib/claude-code.js`) in the first workspace folder and renders its event stream — narration, tool calls with results, the `TodoWrite` plan, token and cost totals. The conversation continues through Claude Code's own session (`--resume`), so its compaction and memory apply; **New** starts a fresh session.

- **Needs** the Claude Code CLI (`claude` on PATH, `%USERPROFILE%\.local\bin\claude.exe`, or `claudeCodePath`).
- **Auth** (`claudeCodeAuth`): `auto` passes the bridge's Anthropic key when one is set (plus `claudeWorkspaceId` as a request header) and otherwise leaves Claude Code to its own login; `apiKey` and `login` force one or the other. For `login`, run `claude` in a terminal once and use `/login`.
- **Permissions** (`claudeCodePermissionMode`, default `acceptEdits`): the panel cannot show Claude Code's approval prompts, so a call that would prompt is denied and reported. Shell follows `localAgentBridge.agent.shell`: `auto` pre-approves the command tools, `off` removes them, `confirm` leaves them to the mode (denied in headless use).
- **Undo** still works: each file is snapshotted when Claude Code announces an edit, which feeds the changed-files card. Files changed by shell commands are not tracked.
- The active file and selection are added to the prompt. `claudeEffort` and extra workspace folders / `writableRoots` (as `--add-dir`) are passed on. The bridge's own tools, skill catalog and progress index are not used in this mode; Claude Code's are.

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

- The file tools (`Write`, `StrReplace`, `MultiEdit`, `Delete`) only change files inside the open workspace folders plus `localAgentBridge.agent.writableRoots` (e.g. a game's `Mods` folder). Reads may go anywhere unless `readAnywhere` is off.
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
| `localAgentBridge.agent.provider` | `auto` | `auto` / `vllm` / `ollama` / `anthropic` / `claude-code` / `openai` |
| `localAgentBridge.agent.baseUrl` | | override URL (ends in `/v1`) |
| `localAgentBridge.agent.model` | | empty = first preferred model served |
| `localAgentBridge.agent.apiKey` | | bearer key (empty = Qud Lab key file for vLLM) |
| `localAgentBridge.agent.contextTokens` | `0` | 0 = ask the backend |
| `localAgentBridge.agent.ollamaNumCtx` | `16384` | |
| `localAgentBridge.agent.maxOutputTokens` | `2048` | local backends |
| `localAgentBridge.agent.claudeMaxOutputTokens` | `16000` | Claude, thinking included |
| `localAgentBridge.agent.claudeEffort` | `default` | `default` / `low` / `medium` / `high` / `xhigh` / `max` |
| `localAgentBridge.agent.claudeWorkspaceId` | | `wrkspc_…`, only for user-scoped keys |
| `localAgentBridge.agent.claudeCodePath` | | Claude Code CLI; empty = PATH, then `~/.local/bin` |
| `localAgentBridge.agent.claudeCodePermissionMode` | `acceptEdits` | `acceptEdits` / `auto` / `plan` / `manual` |
| `localAgentBridge.agent.claudeCodeAuth` | `auto` | `auto` / `apiKey` / `login` |
| `localAgentBridge.agent.maxRounds` | `30` | model↔tool rounds per request |
| `localAgentBridge.agent.shell` | `auto` | `auto` / `confirm` / `off` |
| `localAgentBridge.agent.writableRoots` | `[]` | extra folders the agent may change |
| `localAgentBridge.agent.readAnywhere` | `true` | |
| `localAgentBridge.agent.requireReadBeforeEdit` | `true` | refuse edits not based on a current `Read` |
| `localAgentBridge.agent.diagnosticsAfterEdit` | `true` | add the file's editor errors to edit results |
| `localAgentBridge.agent.subagents` | `true` | offer the `Task` sub-agent |
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

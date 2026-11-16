# Local Agent Bridge for CortexIDE (2.17.1)

Turns CortexIDE into a working AI coding toolset on **local models** (vLLM / SGLang router, Ollama, any OpenAI-compatible server) **or on Claude** through the Anthropic Messages API, with file, search and shell tools, `SKILL.md` skills, `.canvas.tsx` canvases, and imported chats (including Cursor exports and agent transcripts).

2.17.1 restyles the **Agent panel**: no speaker labels; your messages sit in a soft bubble and the agent writes plain prose; tool calls are compact lines with a status dot on a thin rail; the composer is one rounded box with the text field, chips and a round send / stop button, with the + / @ picker floating above it; the top bar and chat tabs are slimmer. See *Credits* for where the look comes from.

2.17 adds a **New Tab page** and **canvases that work like the agent's own artifacts**:
- **New Tab** (editor area): opening or focusing the Local Agent replaces VS Code's Welcome page with it (`localAgentBridge.newTab`: `replaceWelcome` / `always` / `off`; command *Open New Tab*, or the home button on the Agent view). It has a composer that starts a chat (mode picker, model), the open tabs, this workspace's Changes / Browser / Terminal / Files / Canvas / Side Chat, its canvases, your `localAgentBridge.agent.panels` and the recent chats.
- **Canvas card in the chat**: when a turn creates or changes a `.canvas.tsx`, the chat shows a card (click to open, **Source** for the file), and the canvas opens beside the editor (`localAgentBridge.agent.canvasAutoOpen`: `always` / `created` / `off`). An open canvas re-renders on every save.
- **Canvas toolbar**: *Ask the agent to change this canvas…* (sent to the chat on screen, or a new one when it is busy), **Refresh data** (the agent reruns the canvas's data sources and updates it in place), **Source**, **Reveal**. Buttons inside a canvas that start a chat (`useCanvasAction` `newComposerChat`) now reach the agent instead of copying a path.
- **The agent makes canvases**: the system prompt names this workspace's canvas folder (`~/.cursor/projects/<slug>/canvases`, the only place Cursor looks) and says when a canvas beats a markdown table; it follows the `canvas` skill.
- **Canvases across workspaces**: *Link Canvas to This Workspace* (palette, Explorer menu, New Tab) hard-links canvases of another workspace (with their `.canvas.data.json` state) into this one, e.g. after a game moved from `F:\SteamLibrary` to `D:\games\Steam`. One file, shown in both; it is copied when the drives differ. (An editor that saves by replacing the file breaks the link; VS Code saves in place.)
- The runtime exports `canvasPaletteGrokDark` / `canvasPaletteGrokLight` from the current SDK. The `docs-canvas` skill now uses only the public SDK, so its canvases also compile in Cursor.

2.16 makes **local models** much harder to derail, from failures seen in real Ollama chats:
- **Background shells**: `Shell { run_in_background: true }` starts a dev server, watcher or long build and returns at once with an id. `ShellOutput` reads its new output (`wait`, `until` a regex such as `listening`, `filter` lines), and `ShellKill` stops it with its child processes. Background shells outlive the turn, are listed per chat (at most 6 running), and are killed when CortexIDE closes. A foreground command killed at its timeout now suggests `run_in_background`.
- **Retries on local backends**: a vLLM / SGLang / Ollama 429, 5xx, "model is loading" or dropped connection is retried up to 3 times with backoff, as Claude already was. There is no retry once text has streamed.
- **Binary files are protected**: `Write` / `StrReplace` / `MultiEdit` refuse `.dll`, `.exe`, archives, images, audio and any file with NUL bytes, and point to `Copy-Item` instead. A model once wrote text over a plugin DLL.
- **Syntax check after edits**: an edit that leaves a `.json` file invalid, or an XML / project file with unbalanced tags, says so in the edit result with the line.
- **Ollama thinking models** (qwen3, deepseek-r1) that spend the whole output budget thinking get thinking switched off (`think: false`) for the rest of the turn. Models stay loaded between rounds (`keep_alive` 30m).
- **Wrong model warning**: starting a chat on an Ollama model that cannot call tools (llava, bakllava, …) shows a status line naming the installed models that can, coding models first.
- **The "run the check" nudge** only fires for files inside the workspace the check belongs to: a mod under the Steam folder is no longer told to run the toolkit's `dotnet build`.
- A failed wrap-up request at the round limit no longer throws away the turn.
- **Repetition loops**: when Ollama aborts a reply with "token repeat limit reached", the step is retried (twice at most) with a repetition penalty and more temperature instead of ending the turn. An edit whose `new_string` equals `old_string` now tells the model to write the changed text.

2.15.2: `Install-Vsix.cmd` and the startup sync accept a `~/.cortexide/mcp.json` that starts with a UTF-8 byte order mark (as Windows PowerShell 5.1 writes it). Before, the installer stopped with "Unexpected token" and the sync silently dropped every other MCP server in that file.

2.15.1: the MCP server gains **`list_running_chats`** and **`steer_chat`**, so another agent or tool can see which chats are working in any open window and send one a message (`mode` steer / queue / now; the chat may be named by id, id prefix or part of its title, or left out when only one runs). Messages steered into a running turn are no longer counted as turns of their own, and `/compress` folds them into the turn they joined.

2.15 adds **named agents** (build, plan, ask, explore, plus your own Markdown agents; Plan and Ask really lose the edit tools), **permission rules** (allow / ask / deny, last match wins, with *Allow once / Allow always / Deny* prompts), **custom slash commands** from Markdown files, **`AGENTS.md` instructions** (global, per folder, and found while the agent reads), saved full output for tool results that had to be cut, and a **＋ Start a chat here** row and button on every sidebar folder. The design follows [opencode](https://github.com/anomalyco/opencode) (MIT); no opencode code is copied (see *Agents, permissions and commands*).

2.14.1: REA is taken from a **built source clone** (`Tools\Shared\third_party\Reverse-Engineer-anything` with `dist\` and `node_modules\`) before the prebuilt npm package; `Tools\Fetch-ThirdParty.ps1 -AgentBridge -BuildRea` builds it, links the global `rea` command and puts 7-Zip on the user PATH.

2.14 adds **drag and drop** into the Agent input (from the OS; hold Shift when dragging from the Explorer or a tab), pasted screenshots, a Cursor-style ＋/@ attach menu and modes (Agent, Plan, Debug, Multitask, Ask). The empty chat is now a **panel launcher** (Open Tabs, Changes, Browser, Terminal, Files, Canvas, Side Chat, this workspace's canvases, and your own entries from `localAgentBridge.agent.panels`). Startup sync no longer fails when a workspace folder is read-only (e.g. under `C:\Program Files`): that folder is skipped, and `~/.cortexide/mcp.json` is always updated to the installed version.

2.13 adds **conversation steering**: while a chat works, the input box stays open. Enter steers the running turn (taken in at its next step), Alt+Enter queues the message as the next turn, Ctrl+Shift+Enter stops the turn and sends it. `/compress` sent while a chat works runs as soon as the turn ends (see *Chats and history*).

2.12 turns the history drawer into a **Cursor-style sidebar tree**: Pinned (from every workspace), then one collapsible branch per workspace folder from the master index, runs on several models as a sub-branch, "More" after 5 chats, and "No agents yet" for open folders without chats. A chat of another folder can be opened in that folder's window, continued here as a copy, read as Markdown, or pinned (see *Chats and history*).

2.11 adds a **right-click menu on file names in the chat**: open (at the line, when one is given), open to the side, show diff, reveal in the Explorer view or the OS file manager, copy the path or relative path. Ctrl+click opens the file (see *Agent panel*).

2.10 adds **`/compress [focus]`** (alias `/compact`, as in Claude Code): the chat's history is replaced by a summary its own model writes, brief on older turns and detailed on the recent ones (see *Chats and history*).

2.9 lets the agent **see images and read binary files**: images linked in a message (paths, `file:///`, http(s), markdown) and the ones `ReadImage` / `AnalyzeFile` open are sent to vision models on Claude, Ollama and OpenAI-compatible servers; `AnalyzeFile` turns DLLs/EXEs, archives, PDFs and game formats into structured text. It also adds **MCP servers inside the agent loop** (`McpTools` / `McpCall`), with REA (Reverse Engineer Anything) picked up automatically. See *Images and binary files* and *MCP servers in the agent*.

2.8 adds **output limits per chat**: one chat can be raised to Extended, Maximum or Custom output tokens, tool rounds and Claude effort for complex work, while chats beside it keep the defaults (see *Chats and history*).

2.7 adds **chats with history**: every chat is saved in a history cache laid out like Claude Code's `~/.claude/projects`, keeps its own backend and model, and runs on its own, so several chats (on different models) can work at the same time. Open chats show as tabs with a status dot; **☰** (Ctrl+H) opens the history; **Run Prompt on Several Models** sends one prompt to a chat per model. See *Chats and history* below. The single chat saved by 2.6 is moved into the history on first open. 2.7.1 adds a three-level index (master → folder → chat), a folder with its own sub-index and `progress.md` per chat, and file claims so chats running together cannot overwrite each other's files. 2.7.2 makes the per-chat sub-indexes the source of truth, so two CortexIDE windows on one workspace no longer overwrite each other's chat list (see *Several windows* below).

2.6 redesigns the Agent panel and adds **browser sign-in**. The top bar shows the backend and model in use with a status dot (click it to switch); **⋯** opens one menu for model, effort, API key, permissions, undo, find-in-chat, import, skills and settings; an empty chat shows a set-up card and example prompts; a problem shows as a banner with the buttons that fix it; chips under the input show shell mode, permission mode and effort. **Sign in with Claude** (panel, menu, or the command *Agent: Sign In with Claude (browser)*) runs the official `claude auth login` in a terminal: your browser opens, the credentials stay in Claude Code's own store, and the extension only polls `claude auth status`. Once signed in, the panel switches to the Claude Code engine with `claudeCodeAuth: login`. The page itself is `media/agent-panel.html`.

2.5 adds the **Claude Code engine** (see Backends below): the Agent panel can hand the whole turn to the installed Claude Code CLI, so it behaves like the Claude app — same tools, system prompt, context handling, skills, `CLAUDE.md`, MCP servers and subagents.

2.4 makes small local models drive the agent much more reliably: streamed local replies (no idle timeouts, live progress, reasoning kept apart), a far more forgiving text tool-call parser, indentation-tolerant edits, dropped cut-off writes, a stall detector, project check commands and a workspace map in the prompt, and a one-time "run the check" nudge.

2.3 makes the agent work more like a full coding agent: a `TodoWrite` plan shown in the panel, `MultiEdit`, a read-only `Task` sub-agent, parallel look-ups, numbered `Read` output, a read-before-edit guard, editor errors reported after each edit, git status in context, and a per-turn changed-files card with diff and **Undo**.

2.2 adds the **Claude** backend (see Backends below): the same agent loop, tools, skills and progress index, driven by Claude models over the Anthropic API.

2.1 renames the extension from `arend.cursor-agent-bridge` to `arend.local-agent-bridge`. Command, view and setting ids moved from `cursorAgentBridge.*` to `localAgentBridge.*`, and the MCP server from `cursor-bridge` to `local-agent-bridge`. On first sync it removes the old `.voidrules` section, `cursor-agent.md` / `00-cursor-agent.md` and the old `mcp.json` entry. `Install-Vsix.ps1` uninstalls the old extension.

## Agent panel

Activity bar → **Local Agent** → **Agent** (or the `$(hubot) Agent` status-bar item, or **Local Agent Bridge: Open Agent**).

CortexIDE's built-in chat ignores extension chat contributions, so the agent runs in its own panel, where tool calls are actually executed:

- **Tools** (Cursor-compatible names): `Read` (numbered lines), `LS`, `Glob` (newest first), `Grep` (CortexIDE's bundled ripgrep; `output_mode` content / files_with_matches / count, `context`, `case_sensitive`), `Shell` (PowerShell; quoted `.exe` paths get `&` automatically; optional per-call `timeout`; `run_in_background`), `ShellOutput` / `ShellKill`, `StrReplace`, `MultiEdit` (several replacements in one file, all-or-nothing), `Write`, `Delete`, `ReadLints`, `WebFetch`, `TodoWrite`, `Task`, `ReadImage`, `AnalyzeFile`, `McpTools` / `McpCall` (when an MCP server is configured), `list_skills`, `read_skill`, `attempt_completion`. Common aliases (`read_file`, `edit_file`, `run_terminal_cmd`, `find_file`, `multi_edit`, `todo_write`, …) map onto these.
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
- **Progress index**: after each turn the digest is written to the chat's own `progress.md` (in its session folder, see *Chats and history*) and fed back into that chat's next turn. Chats never share one. **Progress** (or **Agent: Open Progress Index (this chat)**) opens it.
- **Skills**: the skill catalog is in the system prompt; when the task names a skill, its body is attached. The agent can also `read_skill`.
- **Project rules**: `AGENTS.md`, `.cursorrules`, `CLAUDE.md`, and `alwaysApply` rules in `.cursor/rules` are included.
- **Import chat**: from a Cursor agent transcript (`~/.cursor/projects/*/agent-transcripts`) or an exported `.md` / `.jsonl` / `.json`. The last 24 turns go into context and all earlier user requests go into the progress index. The input is pre-filled with "continue the unfinished work".
- **Stop** aborts the model call and kills a running shell command, in the chat on screen only.
- **Open files from the chat**: right-click a file name anywhere in the conversation (a changed-files row, a tool row such as `Read src/x.js`, a `code` span, a path in an answer, a `path:line:` line in `Grep` output, or a selected path) for **Open** (at that line when one is given: `x.js:12:3`, `x.js(12,3)`, `x.js#L12`), **Open to the side**, **Show diff** (changed files), **Reveal in Explorer view**, **Reveal in File Explorer**, **Copy path** and **Copy relative path**. Ctrl+click (Cmd+click) opens the file directly. Windows paths with spaces, `file:///` links, `~/` and relative paths work; a relative path is looked up under each workspace folder, then by searching the workspace (a pick when several files match). Images, PDFs and binaries open with the editor's own viewer; a folder is revealed in the Explorer. Where no file is under the pointer, the usual menu shows. The path matching lives in `lib/file-ref.js`, which the extension also inlines into the panel page so both sides agree.

### Chats and history

- **History cache**: `%USERPROFILE%\.cortexide\agent\projects\<workspace-slug>\` (change with `historyDir`). The slug is Claude Code's (`D:\games\x` → `D--games-x`). The indexes have three levels:
  - **Master index** `%USERPROFILE%\.cortexide\agent\index.json`: every workspace folder that has chats, with its chat, running and claim counts.
  - **Main index of a folder** `projects\<slug>\index.json`: one entry per chat (title, backend, model, status, unread, pinned, open) and the live file claims of running chats.
  - **Per chat** `projects\<slug>\sessions\<id>\`: `session.json` (log, model history, todos, progress digest), its own `index.json` sub-index (header, files it changed, its finished turns) and its own `progress.md`.

  **Several windows on one workspace**: each chat's sub-index header is the source of truth; the main index is a merged cache of them. Every write of the main index takes `index.json.lock`, re-reads the file, merges, and writes: chats this window changed keep its version, chats other windows added or changed are taken in, and a deleted chat leaves a tombstone (`removed`, kept 30 days) so no window brings it back. A rename, pin or tab close made in one window survives the other window saving its running copy of that chat. Claims are checked and taken under the same lock. A chat running in one window cannot be started or deleted from another. Each window watches the main index and redraws its tabs and history when another window changes it. On load, a chat folder the main index does not list is added back from its sub-index. A lock left by a crashed process is broken at once; a lock held longer than 3 s is ignored rather than hanging the editor.

  **Agent: Open Session Indexes** opens any of them. Chats saved by 2.7.0 as flat `sessions\<id>.json` move into their own folder when first read. A damaged master or main index is rebuilt from the chats' sub-indexes (`session.json` for chats without one); a chat left running when CortexIDE closed loads as *stopped*. Past `historyLimit` the oldest chats that are not pinned, open or running are deleted.
- **Tabs**: open chats sit in a strip above the conversation. The dot shows running / done / error / stopped, and a bold title means the chat finished while you were looking at another one. **＋** starts a new chat on the last model picked; **×** closes the tab (the chat stays in the history).
- **History drawer** (**☰**, Ctrl+H, or **Agent: Chat History**), laid out like Cursor's agent sidebar:
  - **Pinned:** pinned chats of every workspace folder, newest first; chats of other folders show the folder name.
  - **Workspaces:** one collapsible branch per folder in the master index. This window's folders come first and start open; the others are sorted by their newest chat and start folded. Each shows 5 chats, then **More**. An open folder without chats shows **No agents yet**; a folder that no longer exists is struck through.
  - Chats from one **Run prompt on several models** run are a sub-branch, one row per model.
  - Each row shows its status dot and a short age (`5m`, `3h`, `2d`, `3w`, `2mo`). Fold and More states survive reloads. Arrow keys walk the tree.
  - This folder's chats can be pinned, renamed or deleted. Another folder's chat opens a pick: open that folder in a new window or this one, **continue it here** (a copy; the original stays), **read it** as Markdown, or pin it (written through that folder's locked index). Other folders' indexes are otherwise only read.
  - Search covers titles, models and folder names everywhere, plus the conversation text of this folder's chats.
- **One model per chat**: the model picker changes the chat on screen. A chip under the input shows that chat's model, and another shows how many chats are running.
- **Output limits per chat** (menu → *Output limits for this chat…*, the ↥ chip, or **Agent: Set Chat Limits**): raise one chat for complex work while the others stay cheap.
  - **Standard**: the `maxOutputTokens` / `claudeMaxOutputTokens`, `maxRounds` and `claudeEffort` settings.
  - **Extended**: local models 8192 / Claude 32000 output tokens per reply, 80 tool rounds per turn, Claude effort at least *high*.
  - **Maximum**: local 16384 / Claude 64000 output tokens, 150 rounds, Claude effort at least *xhigh*.
  - **Custom**: your own output tokens, rounds and effort for that chat (0 = the setting); Custom may also lower them.

  Presets only raise a setting, never lower it. The output is capped to the Claude model's own `max_tokens` and, on local models, to half the context window (the prompt needs the rest); the turn's status line says when a cap applied. The Claude Code engine gets the output cap as `CLAUDE_CODE_MAX_OUTPUT_TOKENS` and the effort as `--effort`; rounds do not apply there. The choice is stored in the chat's index entry and sub-index, so it survives reloads and other windows. A change to a running chat applies from its next turn. `defaultSessionLimits` sets what new chats start with.
- **Side by side**: each chat has its own run, Stop and Undo, so you can start or switch chats while others work. Events from background chats go into their own logs, not the one on screen. `maxParallel` (default 4, 0 = no limit) caps how many run at once.
- **Run Prompt on Several Models** (menu, or the command): pick models, and the prompt starts in a new chat on each. Each chat keeps its own progress and sub-index. Workspace files are shared, so **file claims** keep chats running together from overwriting each other (next item).
- **File claims**: while a chat runs, each file it changes is claimed in the folder's main index. If another running chat tries `StrReplace`, `MultiEdit`, `Write` or `Delete` on that file, the edit is refused and its model is told which chat holds the file and to work on other files. A chat whose only edits were refused may finish and report instead of being pushed to "make the change". Claims are released when the turn ends; claims of a chat that stopped running or of an editor process that exited are ignored. A second CortexIDE window on the same workspace sees the claims through the file on disk. Limits: edits made through `Shell` are not claimed, and Claude Code chats (which edit through their own tools) only get a warning after the fact.
- **`/compress [focus]`** (or `/compact`, the menu item *Compress chat history*, or **Agent: Compress Chat History**): typed as the whole message, it summarises the chat instead of running a turn. Its own model gets a graded transcript built from the chat log:
  - the last `compressRecentTurns` turns (default 3) in full: prompts, tool calls with their results, answers, changed files, errors;
  - the six turns before those shortened, with tool results cut to a line;
  - older turns as an outline: prompt, tool names, changed files, the start of the answer;
  - a summary from an earlier `/compress`, carried forward in place of the turns it covered.

  If that is still too long for about 60% of the context window, the oldest turns lose detail first and then are left out; the latest turn is always kept. The summary has fixed sections: goal, earlier work (brief), recent work (detailed), files, current state and open items. Text after the command (`/compress keep the build-script details`) is passed on as a focus. The chat's history then becomes that summary. The progress index keeps its list of changed files and commands, and drops its per-turn notes, searches and errors, which the summary covers. The summary is shown in the chat and stays in the history ahead of the newest 12 turns. Claude Code chats are summarised by the CLI in plan mode with no tools, then start a fresh Claude Code session whose first prompt carries the summary. Stop cancels it and leaves the history as it was; so does a failure or an empty summary. Sent while the chat works, `/compress` waits above the input box ("after this turn") and runs when the turn ends; **Stop & send** (Ctrl+Shift+Enter) stops the turn and compresses at once, with the stopped turn in the summary. Messages sent while it compresses run afterwards, on the compressed history.
- **Steering** (`steerDefault`): while a chat works, typing shows **Steer** (Enter), **Queue** (Alt+Enter) and **Stop & send** (Ctrl+Shift+Enter). A steered message is merged into the running turn at its next model call and shows as "steered while working"; a pending one holds back the turn's completion so it is not lost. Waiting messages are listed above the input box, each with *steer now*, *stop & send* and ✎ (back into the box). After **Stop** or a failed turn they go back into the input box instead of running. **Agent: Steer Running Chat…** reaches chats running in other windows through each chat's `inbox\` folder. Limits: queued messages are lost if the window reloads, and a steering message is seen only after the current model reply or tool call finishes.
- **Import** opens the imported chat as a new chat instead of replacing the one on screen. Its picker also lists Claude Code sessions for this workspace (`~/.claude/projects/<slug>/*.jsonl`, all projects if none match); one picked there resumes on the Claude Code engine.

### Images and binary files

- **Images in a message**: image paths, `file:///` links, http(s) image URLs and markdown image links in your prompt are loaded and attached to it (up to `maxImages`; missing files are skipped).
- **`ReadImage`** attaches an image for the model to look at. For a model that cannot see images it returns size and format and says so; `Read` on an image hands over to it instead of refusing a binary.
- **Formats**: PNG, JPEG, GIF and WebP go as they are; BMP, TGA and DDS (BC1-BC3, uncompressed) are decoded and sent as PNG; anything too large is scaled to `imageMaxEdge` (System.Drawing through PowerShell) and kept under 5 MB.
- **Which models see images**: `vision: auto` decides per chat: Claude always; Ollama models from `/api/show` capabilities (or a vision projector); other servers from the model name (GPT-4o/4.1/5, Gemini, Qwen-VL / Qwen2.5-VL / Qwen3-VL, LLaVA, Llama 3.2 Vision / Llama 4, Gemma 3, Pixtral, MiniCPM-V, InternVL, …). `on` / `off` force it. The Claude Code engine opens linked images itself and is left alone.
- **Context**: images count in the token estimate; only the newest `maxImages` stay in the conversation (older ones become a note to call `ReadImage` again), and compaction drops old images before it trims text.
- **`AnalyzeFile`** (`path`, optional `entry`, `filter`, `pages`) identifies a file by its bytes (about 55 formats) and returns structured text instead of raw bytes:
  - **PE files**: imports, exports, sections; for .NET assemblies the assembly name, references, resources, and types with methods and fields, plus Unity / Harmony / BepInEx / MelonLoader detection. `filter` narrows to matching names.
  - **Archives**: ZIP (incl. Zip64), TAR and gzip are read in JS. With 7-Zip installed, 7z, RAR, xz, bzip2, zstd, CAB, ISO and MSI are listed through `7z.exe`. `entry` reads one file inside: text is shown, images go to the model, binaries are analysed in turn. DOCX text is extracted.
  - **PDF**: page count, document info and text. With pdf.js installed (see below) compressed, font-encoded and encrypted PDFs are read properly and `pages` (`"3"`, `"2-5"`, `"1,4,7-"`) picks pages; otherwise a built-in best-effort reader is used.
  - **Game formats**: MPQ, BSA / BA2, Bethesda plugins, Unity bundles are identified with the tool to use; anything else gets a hex dump and its readable strings.

### MCP servers in the agent

The agent's own loop (not only the Claude Code engine) can use MCP servers over stdio. A big server's tool list does not fit a local model's context (REA's 139 tool schemas are about 2 MB), so the model gets two small tools instead:

- **`McpTools`**: list servers, search their tools, or show one tool's arguments.
- **`McpCall`**: run a tool. Text and images come back; images only go to models that can see them.

Servers come from `mcpServers` (same shape as `~/.cursor/mcp.json` / `~/.claude.json`), optionally from those two files (`mcpImport`), and **REA** (Reverse Engineer Anything, MIT) is added as `rea` when it is installed under `thirdPartyDir` or the workspace's `Tools\Shared\third_party` (`mcpAutoRea`; needs Node 22.19+, or set `mcpNodePath`). A server starts on first use, answers `roots/list` with the workspace folders, restarts once after a crash, and is stopped with the extension. `mcpMode` runs calls freely (`auto`), asks first (`confirm`) or refuses them (`off`); Stop and `mcpTimeoutSec` end a call that hangs. HTTP / SSE servers are skipped with a note. Chats on the Claude Code engine use Claude Code's own MCP configuration instead.

**Optional libraries**: `Tools\Fetch-ThirdParty.ps1 -AgentBridge` installs `rea-agents` and `pdfjs-dist` into `Tools\Shared\third_party\node\node_modules` (gitignored; see `THIRD_PARTY.md`). They are loaded at run time and never bundled into the VSIX; `thirdPartyDir` points elsewhere if you keep them outside the workspace. 7-Zip is used as an installed program (`%ProgramFiles%\7-Zip\7z.exe` or PATH). Add `-BuildRea` to build the REA clone from source instead (`npm ci`, `npm run build`, the prebuilt Windows addon copied from the same-version package because it only builds on Linux/MinGW, `npm link` for a global `rea`); the bridge then uses the clone. For Ghidra-backed native analysis set the user variables `GHIDRA_INSTALL_DIR`, `JAVA_HOME` (JDK 21+) and optionally `REA_ANALYSIS_PROVIDER=ghidra`, restart CortexIDE, and check with `rea doctor --provider ghidra`.

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

### Agents, permissions and commands

Inspired by [opencode](https://github.com/anomalyco/opencode) (MIT, Copyright (c) 2025 opencode): the ideas and file layouts follow its documentation, the code is written for this extension, and the bridge is not affiliated with or endorsed by opencode. Its folders (`.opencode/…`, `~/.config/opencode/…`) are read as well, so existing opencode agents and commands work here.

- **Agents** (`lib/agents.js`): built-in **build** (all tools), **plan** and **ask** (no edit tools; ask also has no `Shell`) and **explore** (read-only sub-agent). The composer modes pick them (Plan → plan, Ask → ask, the others → build). Your own agents are Markdown files with a YAML header (`description`, `mode: primary|subagent|all`, `tools`, `permissions`, `steps`, `hidden`, `disabled`) and the system-prompt addition as body, in `~/.cortexide/agents`, `~/.claude/agents`, `~/.config/opencode/agents` and the project's `.cortexide/agents`, `.claude/agents`, `.opencode/agents`; a project file replaces a global one of the same name. `@name` at the start of a message runs the turn as that agent, and `Task` can run a named sub-agent (sub-agents stay read-only).
- **Permission rules** (`lib/permissions.js`, setting `localAgentBridge.agent.permissions`): an ordered list of `allow` / `ask` / `deny` rules on a tool and a pattern; the last matching rule wins. A shell command chained with `&&`, `;` or `|` is checked part by part. `ask` shows **Allow once / Allow always / Deny**; *Allow always* is saved for the workspace and never overrides a `deny`. Reading `.env` files asks by default. ⋯ → permissions → **Edit permission rules…** / **Forget "Allow always" answers**.
- **Slash commands** (`lib/commands.js`): Markdown files in `.cortexide/commands`, `.claude/commands` or `.opencode/commands` (project or home) become `/name`. The body is the prompt, with `$ARGUMENTS`, `$1`, `$2`… and `` !`command` `` replaced by that command's output; the header may set `description`, `argument-hint` and `agent`.
- **Instructions** (`lib/instructions.js`, setting `localAgentBridge.agent.instructions`): the global `~/.cortexide/AGENTS.md` and `~/.config/opencode/AGENTS.md`, then each workspace folder's `AGENTS.md` / `CLAUDE.md` / `.cursorrules` up to the repository root, then extra files or globs from the setting (URLs are skipped). An `AGENTS.md` in a sub-folder is added the first time the agent reads a file below it.
- **Saved output** (`lib/tool-output.js`): a tool result too long for the context is cut, and the full text is saved under `%TEMP%\cortexide-tool-output`; the result names the file so the agent can `Grep` it or `Read` it with offset/limit.
- With the **Claude Code engine**, agents and permission rules do not restrict anything: Claude Code runs its own tool loop and permission system.

## Skills, canvases, MCP

On startup (or **Sync Skills & Canvases**) `SKILL.md` files from the Cursor, Claude and Agents skill folders are copied into `.cortexide/skills` (64 max), with `.cortexide/agents/local-agent.md`, `.cortexide/rules/00-local-agent.md` and a managed `.voidrules` section for CortexIDE's built-in Agent mode.

The `local-agent-bridge` MCP server (`list_skills`, `read_skill`, `match_skills`, `list_canvases`, `read_canvas`, `import_cursor_chat`, `list_imported_chats`, `list_running_chats`, `steer_chat`) is registered in `%USERPROFILE%\.cortexide\mcp.json`. It speaks newline-delimited JSON like every MCP client and still answers `Content-Length` framed clients.

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
| `localAgentBridge.agent.historyDir` | | chat history cache; empty = `%USERPROFILE%\.cortexide\agent` |
| `localAgentBridge.agent.historyLimit` | `200` | chats kept per workspace |
| `localAgentBridge.agent.maxParallel` | `4` | chats that may run at once (0 = no limit) |
| `localAgentBridge.agent.defaultSessionLimits` | `standard` | output limits new chats start with: `standard`, `extended`, `max` |
| `localAgentBridge.agent.compressRecentTurns` | `3` | latest turns `/compress` passes in full and summarises in detail |
| `localAgentBridge.agent.vision` | `auto` | send images to the model: `auto` (by model name) / `on` / `off` |
| `localAgentBridge.agent.imageMaxEdge` | `1568` | images are scaled to this long edge (px) |
| `localAgentBridge.agent.maxImages` | `6` | newest images kept per chat (and attached per message) |
| `localAgentBridge.agent.mcpServers` | `{}` | stdio MCP servers for `McpTools` / `McpCall` |
| `localAgentBridge.agent.mcpImport` | `[]` | also use `cursor` (`~/.cursor/mcp.json`) and / or `claude` (`~/.claude.json`) servers |
| `localAgentBridge.agent.mcpAutoRea` | `true` | add REA as `rea` when it is installed |
| `localAgentBridge.agent.mcpNodePath` | | node used for REA (empty = PATH) |
| `localAgentBridge.agent.mcpMode` | `auto` | `auto` / `confirm` / `off` for `McpCall` |
| `localAgentBridge.agent.mcpTimeoutSec` | `300` | per MCP call |
| `localAgentBridge.agent.steerDefault` | `steer` | what Enter does while a chat works: `steer` / `queue` |
| `localAgentBridge.agent.permissions` | `[]` | allow / ask / deny rules, last match wins |
| `localAgentBridge.agent.instructions` | `[]` | extra instruction files or globs |
| `localAgentBridge.agent.panels` | `[]` | your own entries in the empty-chat panel launcher |
| `localAgentBridge.agent.thirdPartyDir` | | REA / pdf.js folder; empty = workspace `Tools\Shared\third_party` |
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
- Tests run under plain node. `test/vscode-stub.js` stands in for the `vscode` API, so `extension.test.js` activates the real extension. It checks that every contributed command, view and setting is wired up, and that the startup sync writes `mcp.json`. `mcp-server.test.js` runs the MCP stdio handshake in both framings. `llm.test.js` drives the Claude backend against a mock Messages API (message conversion, SSE parsing, caching and thinking fields, retries, credential precedence). `sessions.test.js` covers the history cache; `agent-view.test.js` drives the panel with a scripted fake model: 2.6 migration, two chats running on different models, `maxParallel`, per-chat event routing, unread flags, per-chat Stop, file claims between two running chats (refusal, release, per-chat progress and sub-index, master index), and `/compress` (summary call, history replaced, the next turn sent only the summary). `file-ref.test.js` covers finding paths in chat text (spaces, line suffixes, URLs and e-mail excluded) and resolving them; `agent-view.test.js` also runs every right-click action through the real handler. `compress.test.js` covers the graded transcript: recent turns in full, older ones outlined, shrinking from the oldest end, earlier summaries carried forward, failed `/compress` entries skipped. `images.test.js` covers detection and conversion, `ReadImage` with and without vision, prompt image links, the three backends' image message formats, and the loop handing images to the model. `file-analyze.test.js` checks CAB / ISO / MSI detection, pdf.js on a generated PDF with compressed streams (title, text, page selection, the not-installed note) and 7-Zip on a generated `.7z` (listing, a text entry, an image entry attached); the pdf.js and 7-Zip parts skip themselves when those are missing. `mcp-client.test.js` runs a fake MCP server (paging, search, images, `roots/list`, confirm / off, Stop and timeouts, crash restart) and, when installed, starts REA for real. The harness reports a test that awaits a promise that can never settle as a failure rather than letting node exit 0. Set `CORTEXIDE_APP` if CortexIDE's `resources\app` is not at the default path; the bundled-ripgrep test needs it.
- Bump `version` in `package.json` for each install you want to tell apart (the MCP server reports the same version).

## Credits

The look and workflow of this extension take inspiration from other coding environments: the Agent panel, the New Tab page and the canvas host from Cursor and Claude Code, and agents, permissions and commands from [opencode](https://github.com/anomalyco/opencode). Only ideas are borrowed. No code from any of them is copied: everything here is written for this extension from their public documentation and observed behaviour. The `cursor/canvas` runtime is an independent implementation written against the published SDK type definitions, so the same canvas file opens in both places. The extension is not affiliated with or endorsed by the makers of any of these tools.

Third-party code that does ship with the VSIX: React 18.3.1 (MIT, Meta), see `THIRD_PARTY.md` at the repository root.

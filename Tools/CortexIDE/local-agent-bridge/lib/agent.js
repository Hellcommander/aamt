"use strict";

// Agent loop (local models or Claude): plan → gather → act → verify → attempt_completion.
// Read-only calls in one reply run in parallel; Task runs a read-only sub-agent in its own context.

const llm = require("./llm");
const { TOOL_DEFS, MUTATING, READ_ONLY, MCP_TOOLS, canonName, execToolRich, clip, renderTodos } = require("./agent-tools");
const { parseTextCalls, narration, stripThinking, isTutor, looksLikeWork, announcesAction, wantsEdit, wantsVerify } = require("./agent-parse");
const { Progress, compact, estimateTokens, limitImages, short } = require("./agent-context");
const { matchSkills } = require("./scan");
const { steerMessage: steerText } = require("./steer");
const agentsLib = require("./agents");

const MAX_NUDGES = 5;
/** Matches the tool result of an edit refused because another running chat holds the file (agent-view heldMessage). */
const HELD_RE = /^error: .* is being changed by another chat/;
const SUBAGENT_ROUNDS = 16;
/** Look-only rounds on an edit task before the model is told to stop investigating and act. */
const STALL_ROUNDS = 6;
/** Extra rounds a steering message buys (up to twice the chat's round limit). */
const STEER_ROUNDS = 10;
/** Calls that may run side by side in one round. */
const PARALLEL = new Set([...READ_ONLY, "Task"]);

function openTodos(todos) {
  return (todos || []).filter((t) => t.status !== "completed");
}

/** Why a text-only reply is not an acceptable end of turn, or "" if it is. */
function unfinishedReason({ said, prompt, toolsUsed, mutated, verified, todos, subagent, readOnly }) {
  if (subagent || readOnly) {
    // Sub-agents and read-only agents (Plan, Ask) answer in text; there is nothing to edit or verify.
    if (!said) return "Reply with your findings now (paths, line numbers, what you could not determine).";
    // A Plan / Ask question may need no lookup; a sub-agent's report must come from the code.
    if (toolsUsed === 0 && (subagent || looksLikeWork(prompt))) return "Look at the code first: call Glob, Grep or Read before answering.";
    return "";
  }
  if (!said || isTutor(said)) {
    return toolsUsed
      ? "Do not ask me anything or explain how to do it. Continue the task with your tools, then call attempt_completion."
      : "Start now: call a tool (LS, Glob, Grep or Read) to look at the relevant files. Do not ask questions or give instructions.";
  }
  if (toolsUsed === 0 && looksLikeWork(prompt)) {
    return "Start now: call a tool (LS, Glob, Grep or Read) to look at the relevant files. Do not describe the plan.";
  }
  if (announcesAction(said) && !/\b(done|fixed|completed|finished|passes|passed|verified)\b/i.test(said)) {
    return "You described the next step but did not do it. Make that tool call now instead of describing it.";
  }
  if (wantsEdit(prompt) && !mutated) {
    return "You have not changed any file yet, so the task is not done. Make the change with StrReplace, MultiEdit or Write now (Read the file first; copy old_string exactly).";
  }
  if (mutated && wantsVerify(prompt) && !verified) {
    return "You changed files but have not verified them. Run the check the user asked for with Shell (or ReadLints), fix any failure, then call attempt_completion.";
  }
  const open = openTodos(todos);
  if (open.length) {
    return "Your todo list still has open items:\n" + renderTodos(open) + "\nFinish them, or update the list with TodoWrite if they no longer apply, then call attempt_completion.";
  }
  return "";
}

const RULES = `You are CortexIDE Agent, an autonomous coding agent working inside the user's IDE. You act through tools. You are not a tutor or a chatbot.

How you work:
1. When the user asks you to do something, do it yourself with tools. Never ask for permission, never ask the user to run steps you can run, never reply with a tutorial.
2. Before each tool call write one short sentence saying what you are about to do and why.
3. Plan multi-step work: for a task with 3 or more steps, first call TodoWrite with the steps. Keep exactly one item in_progress, and mark each item completed as soon as it is done.
4. When the user says something fails (a test, build, command or error), reproduce it first: run that command with Shell and read the actual error before searching. Then locate before you act: Glob / Grep (output_mode files_with_matches for a first wide search), then Read. Never say a file or folder does not exist until LS or Read has failed on it. Put independent lookups in one reply as several tool calls: they run in parallel. For a broad question about unfamiliar code, send a Task sub-agent and work from its report.
5. See the exact current lines before you change them (Read, or Grep output). Edit with StrReplace, or MultiEdit for several changes to one file: copy old_string exactly, without the line-number prefix, and keep it short (the few lines that change plus one distinctive line). Use Write only for new files or full rewrites of files you have Read. Follow the code's existing style. Never claim a change you did not make with a tool.
6. Verify: an edit result shows the changed lines and any compiler errors in that file; fix errors you caused. Then build, test or lint with Shell when the project has a way to, and fix what fails.
7. Shell is PowerShell on Windows. Quote paths with spaces; run a quoted exe as: & "C:\\path\\tool.exe" args. Start servers, watchers and other commands that never exit with run_in_background: true, wait for their ready line with ShellOutput (until), and stop them with ShellKill when they are no longer needed.
8. If a skill matches the task, call read_skill and follow it.
   Canvas: when the result is a standalone artifact the user will look at (a dashboard, report, audit, analysis, comparison, timeline, data-heavy findings), make a canvas instead of a long markdown table: read_skill canvas, then Write one <name>.canvas.tsx (kebab-case) into the canvas folder named under Environment, that default-exports a React component and imports only from "cursor/canvas", with the data embedded. It opens beside the chat by itself and re-renders whenever you edit it. To change a canvas, edit that file.
9. Keep going until the task is complete, then call attempt_completion with what changed and how you verified it. If the user only asked a question, answer it directly after gathering the facts.`;

const SUBAGENT_RULES = `You are a read-only research sub-agent working for CortexIDE Agent. Answer the question below by looking at the code with Glob, Grep, LS, Read and WebFetch. Put independent lookups in one reply: they run in parallel. You cannot change files or run commands.

When you know the answer, reply without a tool call: a concise report with the facts found, file paths with line numbers, short code excerpts where they matter, and what you could not determine. Do not suggest that the user do anything.`;

const TEXT_TOOL_FORMAT = `
Tool calling: this backend has no native tool calls. To call a tool reply with exactly:
<tool_call>{"name": "<tool>", "arguments": {...}}</tool_call>
One call per block; several blocks in one reply are allowed. You may write one short sentence before them. Tools:
`;

function toolDefsFor(subagent, mcp, agent) {
  let defs = subagent ? TOOL_DEFS.filter((t) => READ_ONLY.has(t.function.name)) : TOOL_DEFS;
  if (!mcp || !mcp.size) defs = defs.filter((t) => !MCP_TOOLS.has(t.function.name));
  if (agent) {
    // A named agent narrows the set (its tools list, or tools it switches off); it never widens it.
    const keep = new Set(agentsLib.toolNames(agent, defs.map((t) => t.function.name)));
    defs = defs.filter((t) => keep.has(t.function.name) || t.function.name === "attempt_completion");
  }
  return defs;
}

function toolSignatureList(defs = TOOL_DEFS) {
  return defs.map((t) => {
    const p = t.function.parameters.properties || {};
    const req = new Set(t.function.parameters.required || []);
    const args = Object.keys(p).map((k) => k + (req.has(k) ? "" : "?")).join(", ");
    return "- " + t.function.name + "(" + args + "): " + t.function.description;
  }).join("\n");
}

function systemPrompt({ env, skills, task, prior, textMode, subagent, mcp, agent, agents }) {
  const parts = [subagent ? SUBAGENT_RULES : RULES];
  if (agent && agent.prompt) parts.push((agent.builtin ? "" : "Agent “" + agent.name + "” instructions (they take precedence over the general rules above where they differ):\n") + agent.prompt.trim());
  const envLines = ["", "Environment:", "- OS: Windows, shell: PowerShell", "- Date: " + new Date().toISOString().slice(0, 10)];
  if (env.roots && env.roots.length) envLines.push("- Workspace folders: " + env.roots.join("; ") + " (relative paths resolve against the first)");
  else envLines.push("- No folder is open; use absolute paths.");
  if (env.activeFile) envLines.push("- Active file: " + env.activeFile + (env.activeLine ? " (cursor at line " + env.activeLine + ")" : ""));
  if (env.openFiles && env.openFiles.length) envLines.push("- Open editors: " + env.openFiles.slice(0, 8).join("; "));
  if (env.git) envLines.push("- Git: " + clip(env.git, 1200).replace(/\n/g, "\n  "));
  if (env.checks && env.checks.length) envLines.push("- Check a change with: " + env.checks.join(" | "));
  if (env.canvasDir && !subagent) envLines.push("- Canvas folder (write new canvases directly here; Cursor and CortexIDE both find them): " + env.canvasDir);
  parts.push(envLines.join("\n"));
  if (env.tree) parts.push("Workspace layout (top two levels):\n" + clip(env.tree, 2500));
  if (!subagent && env.selection) parts.push("Selected text in the active file:\n```\n" + clip(env.selection, 4000) + "\n```");
  if (env.rules) parts.push("Project rules:\n" + clip(env.rules, subagent ? 2000 : 6000));
  if (!subagent && agents && agents.length) {
    const cat = agentsLib.subagentCatalog(agents);
    if (cat.length > 1) parts.push("Sub-agents for the Task tool (pass agent: <name>; default explore):\n" + cat.join("\n"));
  }

  if (!subagent && skills && skills.length) {
    const hits = matchSkills(skills, task, 3);
    parts.push(
      "Skills (read_skill <name> before following one):\n" +
        skills.slice(0, 40).map((s) => "- " + s.name + ": " + short(s.description || "", 110)).join("\n")
    );
    const top = hits[0];
    if (top && new RegExp("\\b" + top.name.replace(/[-_]/g, "[-_ ]?") + "\\b", "i").test(task)) {
      parts.push("Skill '" + top.name + "' matches this task. Its instructions:\n" + clip(top.instructions, 6000));
    }
  }
  if (mcp && mcp.size) {
    parts.push(
      "MCP servers (find tools with McpTools, run them with McpCall" + (subagent ? "; you can only list them" : "") + "):\n" + mcp.summary().join("\n")
    );
  }
  if (!subagent && prior) parts.push("Earlier in this session (programmatic index of past work):\n" + clip(prior, 5000));
  if (textMode) parts.push(TEXT_TOOL_FORMAT + toolSignatureList(toolDefsFor(subagent, mcp, agent)));
  return parts.join("\n\n");
}

function sanitize(messages) {
  return messages.map((m) => {
    const out = { role: m.role, content: m.content == null ? "" : m.content };
    if (m.tool_calls) out.tool_calls = m.tool_calls;
    if (m.tool_call_id) out.tool_call_id = m.tool_call_id;
    if (m.name) out.name = m.name;
    if (m.blocks) out.blocks = m.blocks; // raw Claude content, replayed verbatim (thinking + tool_use)
    if (Array.isArray(m.images) && m.images.length) out.images = m.images; // the backend adapters turn these into image parts
    if (m.role === "assistant" && m.tool_calls && !m.content) out.content = null;
    return out;
  });
}

function toolLabel(c) {
  const a = c.args || {};
  if (c.name === "TodoWrite") return Array.isArray(a.todos) ? a.todos.length + " items" : "";
  if (c.name === "Task") return a.description || short(a.prompt || a.task || "", 60);
  if (c.name === "MultiEdit") return (a.path || "") + (Array.isArray(a.edits) ? " (" + a.edits.length + " edits)" : "");
  return String(a.path || a.file_path || a.target_file || a.pattern || a.query || a.command || a.url || a.name || "");
}

/**
 * @param {object} o
 * @param {object} o.backend from llm.discover()
 * @param {string} o.model
 * @param {number} o.contextTokens
 * @param {string} [o.effort] Claude reasoning effort (low|medium|high|xhigh|max); "" = model default
 * @param {string} o.prompt
 * @param {{mime:string,data:string,path:string,width:number,height:number}[]} [o.images] images attached to the prompt (vision models only)
 * @param {number} [o.maxImages] newest images kept in the conversation (default 6)
 * @param {{role:string,content:string}[]} [o.history] prior turns (user/assistant text only)
 * @param {object} [o.prior] Progress JSON from earlier turns
 * @param {import("./agent-tools").ToolContext} o.tools
 * @param {object} o.env { roots, activeFile, activeLine, openFiles, selection, rules, git }
 * @param {any[]} [o.skills]
 * @param {boolean} [o.subagent] read-only research run started by the Task tool
 * @param {boolean} [o.allowTask] offer the Task tool (default true)
 * @param {(ev:object)=>void} [o.onEvent]
 * @param {{take:()=>{text:string,from?:string,images?:object[]}[], has:()=>boolean}} [o.steer]
 *   messages the user sends while the turn runs; taken in at the start of each round
 * @param {AbortSignal} [o.signal]
 */
async function runAgent(o) {
  const emit = (ev) => o.onEvent && o.onEvent(ev);
  const subagent = !!o.subagent;
  const agent = o.agent || null;
  const maxRounds = Math.max(1, agent && agent.steps ? Math.min(agent.steps, o.maxRounds || agent.steps) : o.maxRounds || 30);
  const maxTokens = o.maxOutputTokens || 2048;
  const budget = Math.max(2048, (o.contextTokens || 16384) - maxTokens - 256);
  const progress = new Progress({ ...(subagent ? {} : o.prior || {}), task: o.prompt });
  const priorText = !subagent && o.prior ? new Progress(o.prior).toText() : "";
  let textMode = !!o.textMode;
  const mcp = o.tools && o.tools.mcp && o.tools.mcp.size ? o.tools.mcp : null;
  let defs = toolDefsFor(subagent, mcp, agent);
  if (!subagent && o.allowTask === false) defs = defs.filter((t) => t.function.name !== "Task");
  const allowed = new Set(defs.map((t) => t.function.name));
  /** No edit tool: Plan / Ask style agents answer in text and are not pushed to change files. */
  const readOnly = !subagent && !["StrReplace", "MultiEdit", "Write"].some((n) => allowed.has(n));
  // Claude binds its thinking blocks to an unedited history: once compaction has rewritten the
  // transcript they are no longer replayed (the API would reject them on newer accounts).
  let historyEdited = false;
  const usage = { input: 0, cached: 0, output: 0 };
  let streamed = 0;
  let shown = 0;

  const buildSystem = () =>
    systemPrompt({ env: o.env || {}, skills: o.skills || [], task: o.prompt, prior: priorText, textMode, subagent, mcp, agent, agents: o.agents });

  const messages = [{ role: "system", content: buildSystem() }];
  for (const h of subagent ? [] : o.history || []) {
    if ((h.role === "user" || h.role === "assistant") && h.content) {
      // A /compress summary replaces the whole earlier history, so it gets a far larger share.
      messages.push({ role: h.role, content: clip(String(h.content), h.summary ? 24000 : 3000) });
    }
  }
  const promptImages = !subagent && Array.isArray(o.images) ? o.images.filter((i) => i && i.data) : [];
  messages.push(promptImages.length ? { role: "user", content: o.prompt, images: promptImages } : { role: "user", content: o.prompt });
  const firstUser = messages.length - 1;
  const maxImages = Math.max(1, o.maxImages || 6);
  /** tool call id → images its result carries */
  const imagesOf = new Map();

  const seen = new Map();
  /** lower-case path → consecutive failed edits, for escalating hints */
  const editFails = new Map();
  let toolsUsed = 0;
  let mutated = false;
  let mutatedCode = false; // a non-prose file changed
  // The project checks come from the first workspace folder: they say nothing about files elsewhere
  // (a mod folder under Steam is not checked by the toolkit's dotnet build).
  const checkRoot = o.env && o.env.roots && o.env.roots[0] ? String(o.env.roots[0]).toLowerCase().replace(/[\\/]+$/, "").replace(/\//g, "\\") + "\\" : "";
  let mutatedChecked = false; // a code file under checkRoot changed
  // Ollama thinking models (qwen3, deepseek-r1) can spend the whole output budget thinking; then
  // the rest of the turn runs with thinking off.
  let noThink = false;
  // A small model stuck repeating itself (Ollama aborts with "token repeat limit reached") gets the
  // round again with a repetition penalty and more temperature instead of losing the turn.
  let antiRepeat = 0;
  // Auto-switch (o.switchOnStruggle): a model that is clearly not up to the task ends the turn early
  // with a reason, so the caller can hand the work to a stronger model.
  let thinkOverflows = 0;
  let struggle = "";
  const struggling = (why) => {
    if (o.switchOnStruggle && !subagent && !struggle) struggle = why;
    return !!struggle;
  };
  const struggleResult = () => {
    emit({ type: "status", text: "This model is struggling: " + struggle });
    return { text: "", struggling: struggle, toolsUsed, mutated, progress: progress.toJSON(), todos: todos(), steered };
  };
  let idleRounds = 0; // tool rounds since the start without a successful edit
  let verifyNudged = false;
  let verified = false;
  let heldOff = false; // an edit was refused because a chat running beside this one holds the file
  let nudges = 0;
  let final = "";
  const todos = () => (subagent ? [] : (o.tools && o.tools.todos) || []);
  // Steering: the task grows with each message the user sends while this turn runs.
  let task = o.prompt;
  let roundLimit = maxRounds;
  const steered = [];
  const steerPending = () => !subagent && !!(o.steer && o.steer.has());
  /** Take waiting steering messages into the conversation; true when there were any. */
  const takeSteer = (round) => {
    if (subagent || !o.steer) return false;
    const items = (o.steer.take() || []).filter((i) => i && String(i.text || "").trim());
    if (!items.length) return false;
    const text = steerText(items);
    const imgs = items.flatMap((i) => i.images || []);
    const last = messages[messages.length - 1];
    // Merged into a trailing user message: some chat templates reject two user turns in a row.
    if (last && last.role === "user") {
      last.content = String(last.content || "") + "\n\n" + text;
      if (imgs.length) last.images = [...(last.images || []), ...imgs];
    } else messages.push(imgs.length ? { role: "user", content: text, images: imgs } : { role: "user", content: text });
    task += "\n\n" + items.map((i) => i.text).join("\n\n");
    steered.push(...items.map((i) => ({ text: i.text, from: i.from || "" })));
    nudges = 0;
    idleRounds = 0;
    verifyNudged = false;
    // New instructions get rounds of their own (at most double the chat's limit).
    roundLimit = Math.max(roundLimit, Math.min(round + STEER_ROUNDS, maxRounds * 2));
    for (const i of items) emit({ type: "steered", text: i.text, from: i.from || "" });
    emit({ type: "status", text: "Steered: took in " + (items.length > 1 ? items.length + " new messages" : "your new message") + " at round " + round });
    return true;
  };

  /** Run one non-completion tool call; returns the result text. Safe to run concurrently for PARALLEL calls. */
  const runOne = async (c, sig) => {
    const label = toolLabel(c);
    emit({ type: "tool", name: c.name, label, status: "start" });
    const n = seen.get(sig) || 1;
    let result;
    if (!allowed.has(c.name) && c.name !== "attempt_completion") {
      result = "error: " + c.name + " is not available here. Available: " + [...allowed].join(", ");
    } else if (n >= 3 && !MUTATING.has(c.name) && c.name !== "TodoWrite") {
      result = "skipped: you already ran this exact call " + (n - 1) + " times with the same result. Use what you have, try something different, or finish.";
    } else if (c.name === "Task") {
      result = await runTask(c.args);
    } else {
      try {
        const rich = await execToolRich(o.tools, c.name, c.args);
        result = rich.text;
        if (rich.images.length) imagesOf.set(c.id, rich.images);
      } catch (e) {
        result = "error: " + (e.message || e);
      }
    }
    if (c.name === "StrReplace" || c.name === "MultiEdit") result = editHint(c, result);
    result = clip(result, 24000);
    toolsUsed++;
    if (MUTATING.has(c.name) && HELD_RE.test(result)) heldOff = true;
    if (c.name !== "Shell" && MUTATING.has(c.name) && !/^error/.test(result)) {
      mutated = true;
      verified = false;
      const edited = String((c.args && (c.args.path || c.args.file_path || c.args.target_file)) || "");
      if (!/\.(md|markdown|txt|rst)$/i.test(edited)) {
        mutatedCode = true;
        const abs = edited && o.tools && typeof o.tools.resolve === "function" ? o.tools.resolve(edited) : edited;
        if (!checkRoot || String(abs).toLowerCase().replace(/\//g, "\\").startsWith(checkRoot)) mutatedChecked = true;
      }
    } else if (mutated && c.name === "ReadLints" && !/^error/.test(result)) verified = true;
    // A failed, blocked or declined command proves nothing; only a clean exit verifies.
    else if (mutated && c.name === "Shell" && /^exit 0 \(/.test(result)) verified = true;
    progress.record(c.name, c.args, result);
    emit({ type: "tool", name: c.name, label, status: "done", ok: !/^(error|skipped)/.test(result), result: result.slice(0, 4000) });
    if (c.name === "TodoWrite" && !/^error/.test(result)) emit({ type: "todos", todos: todos() });
    return result;
  };

  /** Repeated failed edits on one file get firmer advice than the tool's own error. */
  const editHint = (c, result) => {
    const p = String((c.args && (c.args.path || c.args.file_path || c.args.target_file)) || "").toLowerCase();
    if (!p) return result;
    if (!/^error: (old_string|edit \d+ of)/.test(result)) {
      if (!/^error/.test(result)) editFails.delete(p);
      return result;
    }
    const n = (editFails.get(p) || 0) + 1;
    editFails.set(p, n);
    if (n === 2) return result + "\n\nSecond failed edit on this file. Read the exact lines again (Read with offset/limit around the target), then use a SHORT old_string: 1-3 distinctive lines copied character for character, without line numbers.";
    if (n >= 3) return result + "\n\nEdits to this file keep failing. Read the whole file again. If it is small, rewrite it completely with Write (full contents); otherwise make one small StrReplace per change.";
    return result;
  };

  const runTask = async (args) => {
    const question = String((args && (args.prompt || args.task)) || "").trim();
    if (!question) return "error: Task needs a prompt";
    const want = String(args.agent || args.subagent_type || "").trim();
    let subDef = null;
    if (want && want.toLowerCase() !== "explore") {
      subDef = agentsLib.find(o.agents, want);
      if (!subDef || !agentsLib.isSub(subDef)) {
        const names = agentsLib.subagentCatalog(o.agents || []).map((l) => l.slice(2).split(":")[0]);
        return "error: no sub-agent named " + want + ". Available: " + (names.join(", ") || "explore");
      }
    }
    if (o.tools && typeof o.tools.permit === "function") {
      const refused = await o.tools.permit("Task", { ...args, agent: subDef ? subDef.name : "explore" });
      if (refused) return refused;
    }
    // A named sub-agent's own rules apply to its calls only (opencode: a sub-agent uses its own permissions).
    let subTools = o.tools;
    if (subDef && subDef.rules && subDef.rules.length && o.tools) {
      subTools = Object.create(o.tools);
      subTools.rules = [...o.tools.rules, ...subDef.rules];
    }
    const tag = "Task" + (subDef ? " @" + subDef.name : "") + (args.description ? " (" + short(args.description, 40) + ")" : "");
    try {
      const sub = await runAgent({
        ...o,
        tools: subTools,
        agent: subDef,
        prompt: question,
        subagent: true,
        history: [],
        prior: null,
        maxRounds: Math.min(maxRounds, subDef && subDef.steps ? subDef.steps : SUBAGENT_ROUNDS),
        onEvent: (ev) => {
          if (ev.type === "tool" && ev.status === "start") emit({ type: "status", transient: true, text: tag + " → " + ev.name + " " + ev.label });
          else if (ev.type === "usage") {
            usage.input += ev.input;
            usage.cached += ev.cached;
            usage.output += ev.output;
          }
        },
      });
      return "Sub-agent report (" + sub.toolsUsed + " tool calls):\n" + sub.text;
    } catch (e) {
      if (o.signal && o.signal.aborted) throw e;
      return "error: sub-agent failed: " + (e.message || e);
    }
  };

  for (let round = 1; round <= roundLimit; round++) {
    if (o.signal && o.signal.aborted) throw new Error("stopped");
    takeSteer(round);
    if (o.switchOnStruggle && !subagent) {
      const edits = !readOnly && wantsEdit(task) && !mutated && !heldOff;
      if (nudges >= 3 && !mutated && !readOnly && struggling("it kept answering or announcing instead of doing the work (" + nudges + " reminders)")) return struggleResult();
      if (Math.max(0, ...editFails.values()) >= 3 && struggling("its edits kept failing on the same file")) return struggleResult();
      if (edits && idleRounds >= STALL_ROUNDS + 4 && struggling("it kept looking around for " + idleRounds + " rounds without making the change")) return struggleResult();
    }
    const level = compact(messages, budget, progress, { firstUser });
    if (level) {
      historyEdited = true;
      if (!subagent) emit({ type: "status", text: "Context compacted (level " + level + ") to fit " + budget + " tokens" });
    }
    if (!subagent) emit({ type: "status", text: "Round " + round + " · ~" + estimateTokens(messages) + "/" + budget + " tokens", transient: true });

    let reply;
    streamed = 0;
    shown = 0;
    let thought = 0;
    let thoughtShown = 0;
    try {
      reply = await llm.chat({
        backend: o.backend,
        model: o.model,
        messages: sanitize(messages),
        tools: textMode ? null : defs,
        maxTokens,
        temperature: Math.max(o.temperature == null ? 0.2 : o.temperature, antiRepeat ? 0.4 + 0.2 * antiRepeat : 0),
        repeatPenalty: antiRepeat ? 1.1 + 0.1 * antiRepeat : undefined,
        numCtx: o.backend.provider === "ollama" ? o.contextTokens : undefined,
        effort: o.effort || "",
        replayThinking: !historyEdited,
        think: noThink ? false : undefined,
        onRetry: (r) => emit({ type: "status", text: "Backend unavailable (" + short(r.error, 100) + ") — retry " + r.attempt + " of " + r.of }),
        onText: (t) => {
          streamed += t.length;
          if (!subagent && streamed - shown >= 300) {
            shown = streamed;
            emit({ type: "status", text: "Writing… " + streamed + " chars", transient: true });
          }
        },
        onReasoning: (t) => {
          thought += t.length;
          if (!subagent && thought - thoughtShown >= 500) {
            thoughtShown = thought;
            emit({ type: "status", text: "Thinking… " + thought + " chars", transient: true });
          }
        },
        signal: o.signal,
      });
    } catch (e) {
      if (e instanceof llm.ThinkingMismatch && !historyEdited) {
        historyEdited = true;
        emit({ type: "status", text: "Claude rejected the replayed thinking blocks — resending without them" });
        round--;
        continue;
      }
      if (/repeat limit|repetition|repeating/i.test(String(e.message || "")) && antiRepeat >= 2 && struggling("it kept repeating itself")) return struggleResult();
      if (/repeat limit|repetition|repeating/i.test(String(e.message || "")) && antiRepeat < 2 && !(o.signal && o.signal.aborted)) {
        antiRepeat++;
        emit({ type: "status", text: "The model got stuck repeating itself (" + short(String(e.message), 80) + ") — retrying this step with a repetition penalty" });
        round--;
        continue;
      }
      if (e instanceof llm.ToolsUnsupported && !textMode && struggling("it cannot call tools (" + short(e.message, 80) + ")")) return struggleResult();
      if (e instanceof llm.ToolsUnsupported && !textMode) {
        textMode = true;
        messages[0].content = buildSystem();
        emit({ type: "status", text: "Backend rejected native tools (" + short(e.message, 120) + ") — switching to text tool calls" });
        round--;
        continue;
      }
      if (/maximum context length|context length|too many tokens|prompt is too long/i.test(e.message || "") && round < roundLimit) {
        emit({ type: "status", text: "Backend says the prompt is too long — compacting harder" });
        historyEdited = true;
        compact(messages, Math.floor(budget * 0.6), progress, { firstUser, keepRecent: 4 });
        continue;
      }
      throw e;
    }

    if (reply.usage) {
      usage.input += Number(reply.usage.prompt_tokens) || 0;
      usage.cached += Number(reply.usage.cache_read) || 0;
      usage.output += Number(reply.usage.completion_tokens) || 0;
    }
    const isClaude = o.backend.provider === "anthropic";
    if (reply.truncated) {
      const where = o.limitLabel && o.limitLabel !== "Standard" ? "this chat's " + o.limitLabel + " limits" : "localAgentBridge.agent." + (isClaude ? "claudeMaxOutputTokens" : "maxOutputTokens");
      emit({ type: "status", text: "Reply was cut at the output token limit (" + maxTokens + " tokens, " + where + "). For complex work raise this chat's limits: Agent: Set Chat Limits, or the ⋯ menu." });
    }
    // What goes back into the history: the answer without reasoning (it only costs context).
    const kept = stripThinking(reply.content || "").trim();

    let calls = (reply.tool_calls || [])
      .filter((tc) => tc && tc.function && tc.function.name)
      .map((tc) => {
        let args = tc.function.arguments;
        if (typeof args === "string") {
          try {
            args = JSON.parse(args || "{}");
          } catch {
            args = {};
          }
        }
        return { id: tc.id || llm.newId(), name: canonName(tc.function.name), args: args || {} };
      });
    const fromText = !calls.length;
    if (fromText) calls = parseTextCalls(reply.content).map((c) => ({ ...c, id: llm.newId() }));
    const said = narration(reply.content);
    const CUT_ADVICE = "Your reply was cut off at the output limit (" + maxTokens + " tokens). Keep replies short: one sentence, then the tool call. Write a long file in parts: Write the first part, then add the rest with StrReplace (anchor on the last lines) — never one huge Write.";

    // (Claude replays its raw blocks, so a cut tool_use there is left to the API's own handling.)
    if (!isClaude && reply.truncated && calls.length && MUTATING.has(calls[calls.length - 1].name) && calls[calls.length - 1].name !== "Shell") {
      // The last call's arguments were cut mid-way; running it would save a partial file.
      const cut = calls.pop();
      emit({ type: "status", text: "Dropped a " + cut.name + " call that was cut off at the output limit" });
      if (!calls.length) {
        messages.push({ role: "assistant", content: kept.slice(0, 2000) + "\n…[cut off]" });
        messages.push({ role: "user", content: "Your " + cut.name + " call was not run: " + CUT_ADVICE });
        nudges++;
        continue;
      }
    }

    if (!calls.length) {
      // No tool call: a real final answer, or the model stalling / announcing instead of acting.
      if (steerPending()) {
        // The user wrote while this answer was being produced: keep it, and go on with their message.
        if (said && !subagent) emit({ type: "thought", text: said });
        messages.push({ role: "assistant", content: (isClaude ? reply.content : kept) || "(empty)", blocks: reply.blocks });
        if (round >= roundLimit) roundLimit = round + 1;
        continue;
      }
      let reason = nudges < MAX_NUDGES ? unfinishedReason({ said, prompt: task, toolsUsed, mutated: mutated || heldOff, verified: verified || (heldOff && !mutated), todos: todos(), subagent, readOnly }) : "";
      const thinkOverflow = reply.truncated && !said && (reply.reasoning || /<think/i.test(reply.content || ""));
      if (thinkOverflow) thinkOverflows++;
      if (thinkOverflows >= 2 && struggling("it spent its whole output budget thinking, twice")) return struggleResult();
      if (thinkOverflow && o.backend.provider === "ollama" && !noThink) {
        noThink = true;
        emit({ type: "status", text: "The model used the whole output budget (" + maxTokens + " tokens) thinking — thinking is off for the rest of this turn" });
      }
      if (nudges < MAX_NUDGES && reply.truncated && !said) reason = thinkOverflow
        ? "You used the whole output budget thinking and produced no answer. Think briefly, then make the next tool call directly."
        : CUT_ADVICE;
      if (reason) {
        nudges++;
        if (said && !subagent) emit({ type: "thought", text: said });
        messages.push({ role: "assistant", content: (isClaude ? reply.content : kept) || "(empty)", blocks: reply.blocks });
        messages.push({ role: "user", content: reason });
        if (!subagent) emit({ type: "status", text: "Not done yet — " + reason.split(/[.:]/)[0].toLowerCase() });
        continue;
      }
      final = said || kept || "";
      break;
    }

    if (said && !subagent) emit({ type: "thought", text: said });
    if (fromText) messages.push({ role: "assistant", content: kept || reply.content });
    else messages.push({ role: "assistant", content: (isClaude ? reply.content : kept) || null, blocks: reply.blocks, tool_calls: calls.map((c) => ({ id: c.id, type: "function", function: { name: c.name, arguments: JSON.stringify(c.args) } })) });

    const results = new Map();
    let completion = null;
    for (let i = 0; i < calls.length; ) {
      if (o.signal && o.signal.aborted) throw new Error("stopped");
      const c = calls[i];
      if (completion) {
        // Completion is final: anything the model queued after attempt_completion in the same
        // reply is not run (it would change files after the summary was accepted). Native tool
        // calls still need a result each, so they get a "skipped" one.
        results.set(c.id, "skipped: attempt_completion was already accepted, so this call was not run.");
        emit({ type: "status", text: "Ignored " + c.name + " queued after attempt_completion" });
        i++;
        continue;
      }
      if (c.name === "attempt_completion") {
        let why = "";
        const open = openTodos(todos());
        if (subagent) {
          // A sub-agent's report is its completion summary; there is nothing to verify.
          completion = String(c.args.summary || c.args.result || said || "");
          results.set(c.id, "completed");
          i++;
          continue;
        }
        // A chat whose edits were all refused by another running chat's claim may finish and report:
        // pushing it to "make the change" would only burn rounds on more refusals.
        if (steerPending()) {
          // Not counted as a nudge: the user asked for more, the model did nothing wrong.
          results.set(c.id, "error: not completed — the user sent a new message while you were working (it follows). Handle it, then call attempt_completion again.");
          emit({ type: "status", text: "Completion held — a new message from you is waiting" });
          i++;
          continue;
        }
        if (readOnly) why = "";
        else if (nudges < MAX_NUDGES && wantsEdit(task) && !mutated && !heldOff) why = "no file has been changed yet. Make the change first.";
        else if (nudges < MAX_NUDGES && mutated && wantsVerify(task) && !verified) why = "the change is not verified. Run the requested check with Shell first.";
        else if (nudges < MAX_NUDGES && open.length) why = "your todo list still has open items (" + open.map((t) => t.content).join("; ") + "). Finish them or update the list with TodoWrite.";
        else if (!verifyNudged && mutatedCode && mutatedChecked && !verified && o.env && o.env.checks && o.env.checks.length) {
          // Once per turn: the project has a known check and the change was never checked.
          verifyNudged = true;
          why = "you changed code but have not checked it. Run " + o.env.checks[0] + " with Shell (or ReadLints) and fix any failure. If no check applies to this change, call attempt_completion again.";
        }
        if (why) {
          nudges++;
          results.set(c.id, "error: cannot complete yet — " + why);
          emit({ type: "status", text: "Completion rejected — " + short(why, 160) });
        } else {
          completion = String(c.args.summary || c.args.result || said || "Done.");
          results.set(c.id, "completed");
        }
        i++;
        continue;
      }
      // A run of consecutive look-only calls (and Task sub-agents) goes out in parallel.
      let j = i + 1;
      if (PARALLEL.has(c.name)) while (j < calls.length && PARALLEL.has(calls[j].name)) j++;
      const batch = calls.slice(i, j).map((b) => {
        const sig = b.name + JSON.stringify(b.args);
        seen.set(sig, (seen.get(sig) || 0) + 1);
        return { b, sig };
      });
      if (batch.length > 1 && !subagent) emit({ type: "status", text: "Running " + batch.length + " lookups in parallel", transient: true });
      const out = await Promise.all(batch.map(({ b, sig }) => runOne(b, sig)));
      batch.forEach(({ b }, k) => results.set(b.id, out[k]));
      i = j;
    }

    // Stall detector: small models can circle (re-reading, re-searching) instead of making the edit.
    if (!subagent && !completion && calls.length) {
      idleRounds++;
      if (!readOnly && wantsEdit(task) && !mutated && !heldOff && idleRounds >= STALL_ROUNDS && (idleRounds - STALL_ROUNDS) % 4 === 0) {
        const last = calls[calls.length - 1];
        results.set(
          last.id,
          results.get(last.id) +
            "\n\n[Agent note] " + idleRounds + " rounds of looking and nothing changed yet. Stop investigating: write the root cause in one sentence (quote the failing line or error), then make the change now with StrReplace, MultiEdit or Write. If something truly blocks you, say exactly what."
        );
        emit({ type: "status", text: "Stalled for " + idleRounds + " rounds — told the model to act" });
      }
    }

    if (fromText) {
      const textResults = calls.map((c) => "[" + c.name + " result]\n" + results.get(c.id));
      const imgs = calls.flatMap((c) => imagesOf.get(c.id) || []);
      const msg = { role: "user", content: textResults.join("\n\n") + "\n\nContinue. Use another <tool_call>" + (subagent ? " or reply with your report." : " or finish with attempt_completion.") };
      if (imgs.length) msg.images = imgs;
      messages.push(msg);
    } else {
      for (const c of calls) {
        const msg = { role: "tool", tool_call_id: c.id, name: c.name, content: results.get(c.id) };
        if (imagesOf.has(c.id)) msg.images = imagesOf.get(c.id);
        messages.push(msg);
      }
    }
    for (const c of calls) imagesOf.delete(c.id);
    if (limitImages(messages, maxImages) && !subagent) {
      historyEdited = true;
      emit({ type: "status", text: "Dropped older images to keep the newest " + maxImages, transient: true });
    }
    if (completion) {
      final = completion;
      break;
    }
    if (round === roundLimit && steerPending()) roundLimit++; // a message arrived on the last round: answer it
    else if (round === roundLimit && !readOnly && wantsEdit(task) && !mutated && !heldOff && struggling("it used all " + roundLimit + " rounds without changing anything")) return struggleResult();
    else if (round === roundLimit) {
      emit({ type: "status", text: "Reached " + roundLimit + " rounds — asking for a wrap-up" });
      messages.push({ role: "user", content: subagent ? "Stop using tools. Report what you found so far." : "Stop using tools. Summarise what you did, what is verified, and what is left." });
      // The work is already on disk: a failed wrap-up must not turn the whole turn into an error.
      let wrap = null;
      try {
        wrap = await llm.chat({
          backend: o.backend,
          model: o.model,
          messages: sanitize(messages),
          tools: null,
          maxTokens,
          numCtx: o.backend.provider === "ollama" ? o.contextTokens : undefined,
          effort: o.effort || "",
          replayThinking: !historyEdited,
          signal: o.signal,
        });
      } catch (e) {
        if (o.signal && o.signal.aborted) throw e;
        emit({ type: "status", text: "Wrap-up request failed (" + short(String(e.message || e), 120) + ") — showing the last progress instead" });
      }
      final = (wrap && narration(wrap.content)) || said || "(stopped after " + roundLimit + " rounds" + (mutated ? "; files were changed — see the changed-files card" : "") + ")";
    }
  }

  if (subagent) {
    emit({ type: "usage", ...usage });
    return { text: final || "(the sub-agent found nothing)", toolsUsed };
  }
  if (!final) final = mutated ? "Done." : "(no answer)";
  progress.notes.push("Turn: " + short(o.prompt, 200) + " → " + short(final, 300));
  if (o.backend && o.backend.provider === "anthropic" && usage.input + usage.output > 0) {
    emit({
      type: "status",
      text: "Claude usage this turn: " + usage.input.toLocaleString() + " input tokens (" + usage.cached.toLocaleString() + " from cache) · " + usage.output.toLocaleString() + " output",
    });
  }
  emit({ type: "assistant", text: final });
  return { text: final, progress: progress.toJSON(), toolsUsed, mutated, todos: todos(), steered };
}

module.exports = { runAgent, systemPrompt, unfinishedReason, RULES, SUBAGENT_RULES };

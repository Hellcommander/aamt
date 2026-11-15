"use strict";

// Agent loop (local models or Claude): plan → gather → act → verify → attempt_completion.
// Read-only calls in one reply run in parallel; Task runs a read-only sub-agent in its own context.

const llm = require("./llm");
const { TOOL_DEFS, MUTATING, READ_ONLY, canonName, execTool, clip, renderTodos } = require("./agent-tools");
const { parseTextCalls, narration, stripThinking, isTutor, looksLikeWork, announcesAction, wantsEdit, wantsVerify } = require("./agent-parse");
const { Progress, compact, estimateTokens, short } = require("./agent-context");
const { matchSkills } = require("./scan");

const MAX_NUDGES = 5;
const SUBAGENT_ROUNDS = 16;
/** Look-only rounds on an edit task before the model is told to stop investigating and act. */
const STALL_ROUNDS = 6;
/** Calls that may run side by side in one round. */
const PARALLEL = new Set([...READ_ONLY, "Task"]);

function openTodos(todos) {
  return (todos || []).filter((t) => t.status !== "completed");
}

/** Why a text-only reply is not an acceptable end of turn, or "" if it is. */
function unfinishedReason({ said, prompt, toolsUsed, mutated, verified, todos, subagent }) {
  if (subagent) {
    if (!said) return "Reply with your findings now (paths, line numbers, what you could not determine).";
    if (toolsUsed === 0) return "Look at the code first: call Glob, Grep or Read before answering.";
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
7. Shell is PowerShell on Windows. Quote paths with spaces; run a quoted exe as: & "C:\\path\\tool.exe" args. Do not start servers or watchers that never exit.
8. If a skill matches the task, call read_skill and follow it.
9. Keep going until the task is complete, then call attempt_completion with what changed and how you verified it. If the user only asked a question, answer it directly after gathering the facts.`;

const SUBAGENT_RULES = `You are a read-only research sub-agent working for CortexIDE Agent. Answer the question below by looking at the code with Glob, Grep, LS, Read and WebFetch. Put independent lookups in one reply: they run in parallel. You cannot change files or run commands.

When you know the answer, reply without a tool call: a concise report with the facts found, file paths with line numbers, short code excerpts where they matter, and what you could not determine. Do not suggest that the user do anything.`;

const TEXT_TOOL_FORMAT = `
Tool calling: this backend has no native tool calls. To call a tool reply with exactly:
<tool_call>{"name": "<tool>", "arguments": {...}}</tool_call>
One call per block; several blocks in one reply are allowed. You may write one short sentence before them. Tools:
`;

function toolDefsFor(subagent) {
  return subagent ? TOOL_DEFS.filter((t) => READ_ONLY.has(t.function.name)) : TOOL_DEFS;
}

function toolSignatureList(defs = TOOL_DEFS) {
  return defs.map((t) => {
    const p = t.function.parameters.properties || {};
    const req = new Set(t.function.parameters.required || []);
    const args = Object.keys(p).map((k) => k + (req.has(k) ? "" : "?")).join(", ");
    return "- " + t.function.name + "(" + args + "): " + t.function.description;
  }).join("\n");
}

function systemPrompt({ env, skills, task, prior, textMode, subagent }) {
  const parts = [subagent ? SUBAGENT_RULES : RULES];
  const envLines = ["", "Environment:", "- OS: Windows, shell: PowerShell", "- Date: " + new Date().toISOString().slice(0, 10)];
  if (env.roots && env.roots.length) envLines.push("- Workspace folders: " + env.roots.join("; ") + " (relative paths resolve against the first)");
  else envLines.push("- No folder is open; use absolute paths.");
  if (env.activeFile) envLines.push("- Active file: " + env.activeFile + (env.activeLine ? " (cursor at line " + env.activeLine + ")" : ""));
  if (env.openFiles && env.openFiles.length) envLines.push("- Open editors: " + env.openFiles.slice(0, 8).join("; "));
  if (env.git) envLines.push("- Git: " + clip(env.git, 1200).replace(/\n/g, "\n  "));
  if (env.checks && env.checks.length) envLines.push("- Check a change with: " + env.checks.join(" | "));
  parts.push(envLines.join("\n"));
  if (env.tree) parts.push("Workspace layout (top two levels):\n" + clip(env.tree, 2500));
  if (!subagent && env.selection) parts.push("Selected text in the active file:\n```\n" + clip(env.selection, 4000) + "\n```");
  if (env.rules) parts.push("Project rules:\n" + clip(env.rules, subagent ? 1500 : 3000));

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
  if (!subagent && prior) parts.push("Earlier in this session (programmatic index of past work):\n" + clip(prior, 5000));
  if (textMode) parts.push(TEXT_TOOL_FORMAT + toolSignatureList(toolDefsFor(subagent)));
  return parts.join("\n\n");
}

function sanitize(messages) {
  return messages.map((m) => {
    const out = { role: m.role, content: m.content == null ? "" : m.content };
    if (m.tool_calls) out.tool_calls = m.tool_calls;
    if (m.tool_call_id) out.tool_call_id = m.tool_call_id;
    if (m.name) out.name = m.name;
    if (m.blocks) out.blocks = m.blocks; // raw Claude content, replayed verbatim (thinking + tool_use)
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
 * @param {{role:string,content:string}[]} [o.history] prior turns (user/assistant text only)
 * @param {object} [o.prior] Progress JSON from earlier turns
 * @param {import("./agent-tools").ToolContext} o.tools
 * @param {object} o.env { roots, activeFile, activeLine, openFiles, selection, rules, git }
 * @param {any[]} [o.skills]
 * @param {boolean} [o.subagent] read-only research run started by the Task tool
 * @param {boolean} [o.allowTask] offer the Task tool (default true)
 * @param {(ev:object)=>void} [o.onEvent]
 * @param {AbortSignal} [o.signal]
 */
async function runAgent(o) {
  const emit = (ev) => o.onEvent && o.onEvent(ev);
  const subagent = !!o.subagent;
  const maxRounds = Math.max(1, o.maxRounds || 30);
  const maxTokens = o.maxOutputTokens || 2048;
  const budget = Math.max(2048, (o.contextTokens || 16384) - maxTokens - 256);
  const progress = new Progress({ ...(subagent ? {} : o.prior || {}), task: o.prompt });
  const priorText = !subagent && o.prior ? new Progress(o.prior).toText() : "";
  let textMode = !!o.textMode;
  let defs = toolDefsFor(subagent);
  if (!subagent && o.allowTask === false) defs = defs.filter((t) => t.function.name !== "Task");
  const allowed = new Set(defs.map((t) => t.function.name));
  // Claude binds its thinking blocks to an unedited history: once compaction has rewritten the
  // transcript they are no longer replayed (the API would reject them on newer accounts).
  let historyEdited = false;
  const usage = { input: 0, cached: 0, output: 0 };
  let streamed = 0;
  let shown = 0;

  const buildSystem = () =>
    systemPrompt({ env: o.env || {}, skills: o.skills || [], task: o.prompt, prior: priorText, textMode, subagent });

  const messages = [{ role: "system", content: buildSystem() }];
  for (const h of subagent ? [] : o.history || []) {
    if ((h.role === "user" || h.role === "assistant") && h.content) {
      messages.push({ role: h.role, content: clip(String(h.content), 3000) });
    }
  }
  messages.push({ role: "user", content: o.prompt });
  const firstUser = messages.length - 1;

  const seen = new Map();
  /** lower-case path → consecutive failed edits, for escalating hints */
  const editFails = new Map();
  let toolsUsed = 0;
  let mutated = false;
  let mutatedCode = false; // a non-prose file changed
  let idleRounds = 0; // tool rounds since the start without a successful edit
  let verifyNudged = false;
  let verified = false;
  let nudges = 0;
  let final = "";
  const todos = () => (subagent ? [] : (o.tools && o.tools.todos) || []);

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
        result = await execTool(o.tools, c.name, c.args);
      } catch (e) {
        result = "error: " + (e.message || e);
      }
    }
    if (c.name === "StrReplace" || c.name === "MultiEdit") result = editHint(c, result);
    result = clip(result, 24000);
    toolsUsed++;
    if (c.name !== "Shell" && MUTATING.has(c.name) && !/^error/.test(result)) {
      mutated = true;
      verified = false;
      if (!/\.(md|markdown|txt|rst)$/i.test(String((c.args && (c.args.path || c.args.file_path || c.args.target_file)) || ""))) mutatedCode = true;
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
    const tag = "Task" + (args.description ? " (" + short(args.description, 40) + ")" : "");
    try {
      const sub = await runAgent({
        ...o,
        prompt: question,
        subagent: true,
        history: [],
        prior: null,
        maxRounds: Math.min(maxRounds, SUBAGENT_ROUNDS),
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

  for (let round = 1; round <= maxRounds; round++) {
    if (o.signal && o.signal.aborted) throw new Error("stopped");
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
        temperature: o.temperature == null ? 0.2 : o.temperature,
        numCtx: o.backend.provider === "ollama" ? o.contextTokens : undefined,
        effort: o.effort || "",
        replayThinking: !historyEdited,
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
      if (e instanceof llm.ToolsUnsupported && !textMode) {
        textMode = true;
        messages[0].content = buildSystem();
        emit({ type: "status", text: "Backend rejected native tools (" + short(e.message, 120) + ") — switching to text tool calls" });
        round--;
        continue;
      }
      if (/maximum context length|context length|too many tokens|prompt is too long/i.test(e.message || "") && round < maxRounds) {
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
    if (reply.truncated) emit({ type: "status", text: "Reply was cut at the output token limit (" + maxTokens + " tokens, localAgentBridge.agent." + (isClaude ? "claudeMaxOutputTokens" : "maxOutputTokens") + ")" });
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
      let reason = nudges < MAX_NUDGES ? unfinishedReason({ said, prompt: o.prompt, toolsUsed, mutated, verified, todos: todos(), subagent }) : "";
      if (nudges < MAX_NUDGES && reply.truncated && !said) reason = reply.reasoning || /<think/i.test(reply.content || "")
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
        if (nudges < MAX_NUDGES && wantsEdit(o.prompt) && !mutated) why = "no file has been changed yet. Make the change first.";
        else if (nudges < MAX_NUDGES && mutated && wantsVerify(o.prompt) && !verified) why = "the change is not verified. Run the requested check with Shell first.";
        else if (nudges < MAX_NUDGES && open.length) why = "your todo list still has open items (" + open.map((t) => t.content).join("; ") + "). Finish them or update the list with TodoWrite.";
        else if (!verifyNudged && mutatedCode && !verified && o.env && o.env.checks && o.env.checks.length) {
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
      if (wantsEdit(o.prompt) && !mutated && idleRounds >= STALL_ROUNDS && (idleRounds - STALL_ROUNDS) % 4 === 0) {
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
      messages.push({ role: "user", content: textResults.join("\n\n") + "\n\nContinue. Use another <tool_call>" + (subagent ? " or reply with your report." : " or finish with attempt_completion.") });
    } else {
      for (const c of calls) messages.push({ role: "tool", tool_call_id: c.id, name: c.name, content: results.get(c.id) });
    }
    if (completion) {
      final = completion;
      break;
    }
    if (round === maxRounds) {
      emit({ type: "status", text: "Reached " + maxRounds + " rounds — asking for a wrap-up" });
      messages.push({ role: "user", content: subagent ? "Stop using tools. Report what you found so far." : "Stop using tools. Summarise what you did, what is verified, and what is left." });
      const wrap = await llm.chat({
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
      final = narration(wrap.content) || "(stopped after " + maxRounds + " rounds)";
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
  return { text: final, progress: progress.toJSON(), toolsUsed, mutated, todos: todos() };
}

module.exports = { runAgent, systemPrompt, unfinishedReason, RULES, SUBAGENT_RULES };

"use strict";

// Agent loop for local models: gather → act → verify → attempt_completion.

const llm = require("./llm");
const { TOOL_DEFS, MUTATING, canonName, execTool, clip } = require("./agent-tools");
const { parseTextCalls, narration, isTutor, looksLikeWork, announcesAction, wantsEdit, wantsVerify } = require("./agent-parse");

const MAX_NUDGES = 5;

/** Why a text-only reply is not an acceptable end of turn, or "" if it is. */
function unfinishedReason({ said, prompt, toolsUsed, mutated, verified }) {
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
    return "You have not changed any file yet, so the task is not done. Make the change with StrReplace or Write now (copy old_string exactly from Read output).";
  }
  if (mutated && wantsVerify(prompt) && !verified) {
    return "You changed files but have not verified them. Run the check the user asked for with Shell (or ReadLints), fix any failure, then call attempt_completion.";
  }
  return "";
}
const { Progress, compact, estimateTokens, short } = require("./agent-context");
const { matchSkills } = require("./scan");

const RULES = `You are CortexIDE Agent, an autonomous coding agent working inside the user's IDE. You act through tools. You are not a tutor or a chatbot.

Rules:
1. When the user asks you to do something, do it yourself with tools. Never ask for permission, never ask the user to run steps you can run, never reply with a tutorial.
2. Before each tool call write one short sentence saying what you are about to do and why.
3. Locate before you act: LS / Glob / Grep, then Read. Never say a file or folder does not exist until LS or Read has failed on it.
4. Edit with StrReplace (copy old_string exactly from Read output, including indentation) or Write for new files. Never claim a change you did not make with a tool.
5. Verify: after editing, Read the changed region, run ReadLints, or build/test with Shell. Fix what fails.
6. Shell is PowerShell on Windows. Quote paths with spaces; run a quoted exe as: & "C:\\path\\tool.exe" args.
7. If a skill matches the task, call read_skill and follow it.
8. Keep going until the task is complete, then call attempt_completion with what changed and how you verified it. If the user only asked a question, answer it directly after gathering the facts.`;

const TEXT_TOOL_FORMAT = `
Tool calling: this backend has no native tool calls. To call a tool reply with exactly:
<tool_call>{"name": "<tool>", "arguments": {...}}</tool_call>
One call per block; you may write one short sentence before it. Tools:
`;

function toolSignatureList() {
  return TOOL_DEFS.map((t) => {
    const p = t.function.parameters.properties || {};
    const req = new Set(t.function.parameters.required || []);
    const args = Object.keys(p).map((k) => k + (req.has(k) ? "" : "?")).join(", ");
    return "- " + t.function.name + "(" + args + "): " + t.function.description;
  }).join("\n");
}

function systemPrompt({ env, skills, task, prior, textMode }) {
  const parts = [RULES];
  const envLines = ["", "Environment:", "- OS: Windows, shell: PowerShell", "- Date: " + new Date().toISOString().slice(0, 10)];
  if (env.roots && env.roots.length) envLines.push("- Workspace folders: " + env.roots.join("; ") + " (relative paths resolve against the first)");
  else envLines.push("- No folder is open; use absolute paths.");
  if (env.activeFile) envLines.push("- Active file: " + env.activeFile + (env.activeLine ? " (cursor at line " + env.activeLine + ")" : ""));
  if (env.openFiles && env.openFiles.length) envLines.push("- Open editors: " + env.openFiles.slice(0, 8).join("; "));
  parts.push(envLines.join("\n"));
  if (env.selection) parts.push("Selected text in the active file:\n```\n" + clip(env.selection, 4000) + "\n```");
  if (env.rules) parts.push("Project rules:\n" + clip(env.rules, 3000));

  if (skills && skills.length) {
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
  if (prior) parts.push("Earlier in this session (programmatic index of past work):\n" + clip(prior, 5000));
  if (textMode) parts.push(TEXT_TOOL_FORMAT + toolSignatureList());
  return parts.join("\n\n");
}

function sanitize(messages) {
  return messages.map((m) => {
    const out = { role: m.role, content: m.content == null ? "" : m.content };
    if (m.tool_calls) out.tool_calls = m.tool_calls;
    if (m.tool_call_id) out.tool_call_id = m.tool_call_id;
    if (m.name) out.name = m.name;
    if (m.role === "assistant" && m.tool_calls && !m.content) out.content = null;
    return out;
  });
}

/**
 * @param {object} o
 * @param {object} o.backend from llm.discover()
 * @param {string} o.model
 * @param {number} o.contextTokens
 * @param {string} o.prompt
 * @param {{role:string,content:string}[]} [o.history] prior turns (user/assistant text only)
 * @param {object} [o.prior] Progress JSON from earlier turns
 * @param {import("./agent-tools").ToolContext} o.tools
 * @param {object} o.env { roots, activeFile, activeLine, openFiles, selection, rules }
 * @param {any[]} [o.skills]
 * @param {(ev:object)=>void} [o.onEvent]
 * @param {AbortSignal} [o.signal]
 */
async function runAgent(o) {
  const emit = (ev) => o.onEvent && o.onEvent(ev);
  const maxRounds = Math.max(1, o.maxRounds || 30);
  const maxTokens = o.maxOutputTokens || 2048;
  const budget = Math.max(2048, (o.contextTokens || 16384) - maxTokens - 256);
  const progress = new Progress({ ...(o.prior || {}), task: o.prompt });
  const priorText = o.prior ? new Progress(o.prior).toText() : "";
  let textMode = !!o.textMode;

  const buildSystem = () =>
    systemPrompt({ env: o.env || {}, skills: o.skills || [], task: o.prompt, prior: priorText, textMode });

  const messages = [{ role: "system", content: buildSystem() }];
  for (const h of o.history || []) {
    if ((h.role === "user" || h.role === "assistant") && h.content) {
      messages.push({ role: h.role, content: clip(String(h.content), 3000) });
    }
  }
  messages.push({ role: "user", content: o.prompt });
  const firstUser = messages.length - 1;

  const seen = new Map();
  let toolsUsed = 0;
  let mutated = false;
  let verified = false;
  let nudges = 0;
  let final = "";

  for (let round = 1; round <= maxRounds; round++) {
    if (o.signal && o.signal.aborted) throw new Error("stopped");
    const level = compact(messages, budget, progress, { firstUser });
    if (level) emit({ type: "status", text: "Context compacted (level " + level + ") to fit " + budget + " tokens" });
    emit({ type: "status", text: "Round " + round + " · ~" + estimateTokens(messages) + "/" + budget + " tokens", transient: true });

    let reply;
    try {
      reply = await llm.chat({
        backend: o.backend,
        model: o.model,
        messages: sanitize(messages),
        tools: textMode ? null : TOOL_DEFS,
        maxTokens,
        temperature: o.temperature == null ? 0.2 : o.temperature,
        numCtx: o.backend.provider === "ollama" ? o.contextTokens : undefined,
        signal: o.signal,
      });
    } catch (e) {
      if (e instanceof llm.ToolsUnsupported && !textMode) {
        textMode = true;
        messages[0].content = buildSystem();
        emit({ type: "status", text: "Backend rejected native tools (" + short(e.message, 120) + ") — switching to text tool calls" });
        round--;
        continue;
      }
      if (/maximum context length|context length|too many tokens|prompt is too long/i.test(e.message || "") && round < maxRounds) {
        emit({ type: "status", text: "Backend says the prompt is too long — compacting harder" });
        compact(messages, Math.floor(budget * 0.6), progress, { firstUser, keepRecent: 4 });
        continue;
      }
      throw e;
    }

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

    if (!calls.length) {
      // No tool call: a real final answer, or the model stalling / announcing instead of acting.
      const reason = nudges < MAX_NUDGES ? unfinishedReason({ said, prompt: o.prompt, toolsUsed, mutated, verified }) : "";
      if (reason) {
        nudges++;
        if (said) emit({ type: "thought", text: said });
        messages.push({ role: "assistant", content: reply.content || "(empty)" });
        messages.push({ role: "user", content: reason });
        emit({ type: "status", text: "Not done yet — " + reason.split(".")[0].toLowerCase() });
        continue;
      }
      final = said || reply.content || "";
      break;
    }

    if (said) emit({ type: "thought", text: said });
    if (fromText) messages.push({ role: "assistant", content: reply.content });
    else messages.push({ role: "assistant", content: reply.content || null, tool_calls: calls.map((c) => ({ id: c.id, type: "function", function: { name: c.name, arguments: JSON.stringify(c.args) } })) });

    const textResults = [];
    let completion = null;
    for (const c of calls) {
      if (o.signal && o.signal.aborted) throw new Error("stopped");
      let result;
      if (c.name === "attempt_completion") {
        let why = "";
        if (nudges < MAX_NUDGES && wantsEdit(o.prompt) && !mutated) why = "no file has been changed yet. Make the change first.";
        else if (nudges < MAX_NUDGES && mutated && wantsVerify(o.prompt) && !verified) why = "the change is not verified. Run the requested check with Shell first.";
        if (why) {
          nudges++;
          result = "error: cannot complete yet — " + why;
          emit({ type: "status", text: "Completion rejected — " + why });
        } else {
          completion = String(c.args.summary || c.args.result || said || "Done.");
          result = "completed";
        }
      } else {
        const sig = c.name + JSON.stringify(c.args);
        const n = (seen.get(sig) || 0) + 1;
        seen.set(sig, n);
        const label = c.args.path || c.args.pattern || c.args.command || c.args.url || c.args.name || "";
        emit({ type: "tool", name: c.name, label: String(label), status: "start" });
        if (n >= 3 && !MUTATING.has(c.name)) {
          result = "skipped: you already ran this exact call " + (n - 1) + " times with the same result. Use what you have, try something different, or finish.";
        } else {
          try {
            result = await execTool(o.tools, c.name, c.args);
          } catch (e) {
            result = "error: " + (e.message || e);
          }
        }
        result = clip(result, 24000);
        toolsUsed++;
        if (c.name !== "Shell" && MUTATING.has(c.name) && !/^error/.test(result)) {
          mutated = true;
          verified = false;
        } else if (mutated && (c.name === "Shell" || c.name === "ReadLints")) verified = true;
        progress.record(c.name, c.args, result);
        emit({ type: "tool", name: c.name, label: String(label), status: "done", ok: !/^(error|skipped)/.test(result), result: result.slice(0, 4000) });
      }
      if (fromText) textResults.push("[" + c.name + " result]\n" + result);
      else messages.push({ role: "tool", tool_call_id: c.id, name: c.name, content: result });
    }
    if (fromText && textResults.length) {
      messages.push({ role: "user", content: textResults.join("\n\n") + "\n\nContinue. Use another <tool_call> or finish with attempt_completion." });
    }
    if (completion) {
      final = completion;
      break;
    }
    if (round === maxRounds) {
      emit({ type: "status", text: "Reached " + maxRounds + " rounds — asking for a wrap-up" });
      messages.push({ role: "user", content: "Stop using tools. Summarise what you did, what is verified, and what is left." });
      const wrap = await llm.chat({
        backend: o.backend,
        model: o.model,
        messages: sanitize(messages),
        tools: null,
        maxTokens,
        numCtx: o.backend.provider === "ollama" ? o.contextTokens : undefined,
        signal: o.signal,
      });
      final = narration(wrap.content) || "(stopped after " + maxRounds + " rounds)";
    }
  }

  if (!final) final = mutated ? "Done." : "(no answer)";
  progress.notes.push("Turn: " + short(o.prompt, 200) + " → " + short(final, 300));
  emit({ type: "assistant", text: final });
  return { text: final, progress: progress.toJSON(), toolsUsed, mutated };
}

module.exports = { runAgent, systemPrompt, RULES };

"use strict";

// Custom slash commands: a Markdown file whose body is a prompt template, run as /name args.
// Design follows opencode's commands (https://github.com/anomalyco/opencode, MIT, Copyright (c) 2025
// opencode): $ARGUMENTS for the whole argument text, $1..$n for quoted-aware positional arguments (the
// highest one takes the rest), arguments appended after a blank line when the template has no
// placeholder, !`command` blocks replaced by the command's output, nested files named "dir/name",
// optional front matter (description, agent), project files replacing global ones.
// Claude Code's `.claude/commands/*.md` use the same $ARGUMENTS form and load the same way.
// Written from the documented behaviour; no opencode source is copied.

const fs = require("fs");
const path = require("path");
const os = require("os");
const fm = require("./frontmatter");

/** Built into the panel; a file cannot take these names. */
const RESERVED = new Set(["compress", "compact", "commands", "help", "agents"]);

function dirsFor(roots, home) {
  const h = home || os.homedir();
  const global = [path.join(h, ".config", "opencode", "commands"), path.join(h, ".config", "opencode", "command"), path.join(h, ".claude", "commands"), path.join(h, ".cortexide", "commands")];
  const project = [];
  for (const r of roots || []) {
    if (!r) continue;
    project.push(path.join(r, ".opencode", "commands"), path.join(r, ".opencode", "command"), path.join(r, ".claude", "commands"), path.join(r, ".cortexide", "commands"));
  }
  return [...global, ...project]; // later wins
}

function walk(dir, base, depth, out) {
  let ents = [];
  try {
    ents = fs.readdirSync(dir, { withFileTypes: true });
  } catch {
    return;
  }
  for (const e of ents) {
    const p = path.join(dir, e.name);
    if (e.isDirectory() && depth < 3) walk(p, base, depth + 1, out);
    else if (e.isFile() && /\.md$/i.test(e.name)) out.push(p);
  }
}

/** Every command (name → definition), global first so project files replace them. */
function loadCommands(roots, { home } = {}) {
  const map = new Map();
  for (const dir of dirsFor(roots, home)) {
    const files = [];
    walk(dir, dir, 0, files);
    for (const file of files) {
      const name = path.relative(dir, file).replace(/\\/g, "/").replace(/\.md$/i, "").toLowerCase();
      if (!name || RESERVED.has(name)) continue;
      let text;
      try {
        text = fs.readFileSync(file, "utf8");
      } catch {
        continue;
      }
      const { data, body } = fm.parse(text);
      if (!body.trim()) continue;
      map.set(name, {
        name,
        file,
        template: body,
        description: String(data.description || "").trim() || firstLine(body),
        hint: String(data["argument-hint"] || data.argumentHint || "").trim(),
        agent: String(data.agent || "").trim(),
      });
    }
  }
  return [...map.values()].sort((a, b) => a.name.localeCompare(b.name));
}

function firstLine(s) {
  const l = String(s).split(/\r?\n/).find((x) => x.trim()) || "";
  return l.trim().slice(0, 100);
}

/** "/name rest" → { command, args } when name is a known command; else null. */
function match(text, commands) {
  const m = /^\/([\w./:-]+)(?:\s+([\s\S]*))?$/.exec(String(text || "").trim());
  if (!m) return null;
  const want = m[1].toLowerCase().replace(/:/g, "/"); // Claude Code writes nested commands as dir:name
  const c = (commands || []).find((x) => x.name === want);
  return c ? { command: c, args: (m[2] || "").trim() } : null;
}

/** Split arguments on spaces; single or double quotes group words and are removed. */
function splitArgs(s) {
  const out = [];
  const re = /"([^"]*)"|'([^']*)'|(\S+)/g;
  let m;
  while ((m = re.exec(String(s || "")))) out.push(m[1] != null ? m[1] : m[2] != null ? m[2] : m[3]);
  return out;
}

/** Fill $ARGUMENTS and $1..$n; without any placeholder the arguments are appended after a blank line. */
function fill(template, args) {
  const t = String(template);
  const raw = String(args || "");
  const nums = [...t.matchAll(/\$(\d+)/g)].map((m) => Number(m[1])).filter((n) => n > 0);
  const hasAll = /\$ARGUMENTS\b/.test(t);
  if (!hasAll && !nums.length) return raw ? t + "\n\n" + raw : t;
  const words = splitArgs(raw);
  const top = nums.length ? Math.max(...nums) : 0;
  let out = t.replace(/\$ARGUMENTS\b/g, raw);
  out = out.replace(/\$(\d+)/g, (_, d) => {
    const n = Number(d);
    if (n < 1) return "$" + d;
    if (n === top) return words.slice(n - 1).join(" ");
    return words[n - 1] == null ? "" : words[n - 1];
  });
  return out;
}

/**
 * Expand a command: fill the arguments, then replace each !`cmd` with that command's output.
 * @param {(cmd:string) => Promise<string>} [run] runs one shell block; without it the blocks are left as written
 */
async function expand(command, args, run) {
  let text = fill(command.template, args);
  const blocks = [...text.matchAll(/!`([^`\n]+)`/g)];
  if (blocks.length && run) {
    const outs = [];
    for (const b of blocks) {
      let out;
      try {
        out = await run(b[1]);
      } catch (e) {
        out = "(failed: " + ((e && e.message) || e) + ")";
      }
      outs.push(String(out == null ? "" : out).trimEnd());
    }
    let k = 0;
    text = text.replace(/!`([^`\n]+)`/g, () => outs[k++]);
  }
  return { prompt: text.trim(), agent: command.agent || "" };
}

/** Lines for /commands. */
function listing(commands) {
  if (!commands.length) return "No custom commands. Add Markdown files to .cortexide/commands/ (or .opencode/commands/, .claude/commands/) in the workspace or your home folder: the file name is the command, the body is the prompt ($ARGUMENTS, $1, !`git diff`).";
  return commands.map((c) => "/" + c.name + (c.hint ? " " + c.hint : "") + " — " + c.description + (c.agent ? " (agent: " + c.agent + ")" : "")).join("\n");
}

module.exports = { RESERVED, loadCommands, match, splitArgs, fill, expand, listing, dirsFor };

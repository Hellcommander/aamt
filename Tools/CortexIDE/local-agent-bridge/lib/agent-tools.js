"use strict";

// Agent toolset with Cursor-compatible tool names (Read, Grep, Glob, LS, Shell, StrReplace, Write, ...).
// Runs inside the extension host; `vscode` is optional so the module also loads under plain node.

const fs = require("fs");
const path = require("path");
const { spawn } = require("child_process");

let vscode = null;
try {
  vscode = require("vscode");
} catch {
  /* plain node (tests / MCP) */
}

const MAX_READ_LINES = 400;
const MAX_OUT = 16000;
const SKIP_DIRS = new Set(["node_modules", ".git", "bin", "obj", ".venv", "venv", "__pycache__", "dist", "out"]);
const BLOCKED_SHELL = [
  /\bformat(\.com)?\s+[a-z]:/i,
  /\b(shutdown|restart-computer|stop-computer)\b/i,
  /\bremove-item\b[^|;]*\s[a-z]:\\?\s*(-|$)/i,
  /\brm(dir)?\s+(-rf?|\/s)\s+[a-z]:\\?\s*$/i,
  /\bdel\s+\/s\b[^|;]*[a-z]:\\windows/i,
  /\bdiskpart\b|\bbcdedit\b|\breg\s+delete\s+hk(lm|ey_local_machine)/i,
];

function tool(name, description, properties, required) {
  return {
    type: "function",
    function: {
      name,
      description,
      parameters: { type: "object", properties: properties || {}, required: required || [] },
    },
  };
}

const TODO_STATUS = ["pending", "in_progress", "completed"];

const TOOL_DEFS = [
  tool("Read", "Read a text file. Lines come back numbered as '  N\\tline' (the number and tab are not part of the file). Returns up to 400 lines; pass offset (1-based line) and limit for more.", {
    path: { type: "string", description: "Absolute path, or relative to the first workspace folder" },
    offset: { type: "number" },
    limit: { type: "number" },
  }, ["path"]),
  tool("LS", "List a directory (folders end with /).", { path: { type: "string" } }, ["path"]),
  tool("Glob", "Find files by glob pattern, e.g. **/*.cs or **/Mutations/*.xml. Newest files first.", {
    pattern: { type: "string" },
    path: { type: "string", description: "Folder to search (default: workspace)" },
  }, ["pattern"]),
  tool("Grep", "Search file contents with ripgrep. Default output is path:line:text. Case-insensitive unless case_sensitive is set.", {
    pattern: { type: "string", description: "Regex (or literal text)" },
    path: { type: "string", description: "File or folder (default: workspace)" },
    glob: { type: "string", description: "Only files matching this glob, e.g. *.cs" },
    output_mode: { type: "string", enum: ["content", "files_with_matches", "count"], description: "content (default), files_with_matches (just paths — best for a first wide search), or count" },
    context: { type: "number", description: "Lines of context around each match (content mode, max 10)" },
    case_sensitive: { type: "boolean" },
    head_limit: { type: "number", description: "Max output lines (default 200)" },
  }, ["pattern"]),
  tool("Shell", "Run a PowerShell command (build, test, git, dotnet, scripts). Returns exit code and output. Do not start servers or watchers that never exit.", {
    command: { type: "string" },
    cwd: { type: "string", description: "Working folder (default: workspace)" },
    timeout: { type: "number", description: "Seconds before the command is killed (default from settings, max 600)" },
  }, ["command"]),
  tool("StrReplace", "Replace an exact, unique snippet in a file. Copy old_string verbatim from Read (or Grep) output, without the line-number prefix. The result shows the edited lines and any new compiler errors.", {
    path: { type: "string" },
    old_string: { type: "string" },
    new_string: { type: "string" },
    replace_all: { type: "boolean" },
  }, ["path", "old_string", "new_string"]),
  tool("MultiEdit", "Several StrReplace edits to one file, applied in order and all-or-nothing. Prefer this over repeated StrReplace calls on the same file.", {
    path: { type: "string" },
    edits: {
      type: "array",
      items: {
        type: "object",
        properties: { old_string: { type: "string" }, new_string: { type: "string" }, replace_all: { type: "boolean" } },
        required: ["old_string", "new_string"],
      },
    },
  }, ["path", "edits"]),
  tool("Write", "Create a file, or overwrite one completely (Read it first). Prefer StrReplace for changes to existing files.", {
    path: { type: "string" },
    contents: { type: "string" },
  }, ["path", "contents"]),
  tool("Delete", "Delete a file.", { path: { type: "string" } }, ["path"]),
  tool("ReadLints", "Editor diagnostics (compiler/linter errors) for a file, or all open problems if no path.", {
    path: { type: "string" },
  }, []),
  tool("WebFetch", "Fetch a URL and return its text.", { url: { type: "string" } }, ["url"]),
  tool("list_skills", "List the skills (SKILL.md workflows) available to follow.", {}, []),
  tool("read_skill", "Read a skill's full instructions by name before following it.", {
    name: { type: "string" },
  }, ["name"]),
  tool("TodoWrite", "Create or update your task list for multi-step work (3+ steps). Send the whole list every time. Keep exactly one item in_progress while working and mark items completed as soon as they are done.", {
    todos: {
      type: "array",
      items: {
        type: "object",
        properties: { content: { type: "string" }, status: { type: "string", enum: TODO_STATUS } },
        required: ["content", "status"],
      },
    },
  }, ["todos"]),
  tool("Task", "Send a read-only research sub-agent (Read, LS, Glob, Grep, WebFetch) to answer one question about the codebase in its own context, and get back its report. Use it for broad searches that would otherwise fill your context. Several Task calls in one reply run in parallel.", {
    description: { type: "string", description: "3-6 word label" },
    prompt: { type: "string", description: "The full question, with everything the sub-agent needs to know" },
  }, ["prompt"]),
  tool("attempt_completion", "Finish the task. Call only after the work is done and verified.", {
    summary: { type: "string", description: "What changed and how it was verified" },
  }, ["summary"]),
];

const ALIASES = {
  read: "Read", read_file: "Read", readfile: "Read", open_file: "Read", view_file: "Read", cat: "Read",
  ls: "LS", list_dir: "LS", list_directory: "LS", list_files: "LS", listdir: "LS",
  glob: "Glob", glob_files: "Glob", glob_file_search: "Glob", file_search: "Glob", find_file: "Glob", find_files: "Glob",
  grep: "Grep", search: "Grep", grep_search: "Grep", codebase_search: "Grep", search_files: "Grep",
  shell: "Shell", run_terminal: "Shell", run_terminal_cmd: "Shell", run_command: "Shell", terminal: "Shell", bash: "Shell", powershell: "Shell",
  strreplace: "StrReplace", str_replace: "StrReplace", replace_in_file: "StrReplace", search_replace: "StrReplace", edit_file: "StrReplace", edit: "StrReplace",
  write: "Write", write_file: "Write", create_file: "Write",
  delete: "Delete", delete_file: "Delete", remove_file: "Delete",
  readlints: "ReadLints", read_lints: "ReadLints", get_diagnostics: "ReadLints", diagnostics: "ReadLints",
  webfetch: "WebFetch", web_fetch: "WebFetch", fetch: "WebFetch",
  multiedit: "MultiEdit", multi_edit: "MultiEdit", multi_replace: "MultiEdit",
  todowrite: "TodoWrite", todo_write: "TodoWrite", todos: "TodoWrite", update_todos: "TodoWrite", plan: "TodoWrite",
  task: "Task", subagent: "Task", agent: "Task", research: "Task",
  list_skills: "list_skills", read_skill: "read_skill", match_skills: "list_skills",
  attempt_completion: "attempt_completion", complete: "attempt_completion", finish: "attempt_completion", done: "attempt_completion",
};

const NAMES = new Set(TOOL_DEFS.map((t) => t.function.name));
const MUTATING = new Set(["Shell", "StrReplace", "MultiEdit", "Write", "Delete"]);
/** Tools that only look: safe to run side by side in one round, and all a sub-agent gets. */
const READ_ONLY = new Set(["Read", "LS", "Glob", "Grep", "WebFetch", "ReadLints", "list_skills", "read_skill"]);

function canonName(name) {
  const raw = String(name || "").trim();
  if (NAMES.has(raw)) return raw;
  return ALIASES[raw.toLowerCase()] || raw;
}

function normArgs(name, args) {
  const a = { ...(args || {}) };
  if (a.target_file && !a.path) a.path = a.target_file;
  if (a.file_path && !a.path) a.path = a.file_path;
  if (a.filename && !a.path) a.path = a.filename;
  if (a.directory && !a.path) a.path = a.directory;
  if (a.target_directory && !a.path) a.path = a.target_directory;
  if (a.cmd && !a.command) a.command = a.cmd;
  if (a.working_directory && !a.cwd) a.cwd = a.working_directory;
  if (a.query && !a.pattern) a.pattern = a.query;
  if (a.glob_pattern && !a.pattern) a.pattern = a.glob_pattern;
  if (name === "Glob" && a.name && !a.pattern) a.pattern = String(a.name); // bare name → contains-match in globFiles
  if (a.content != null && a.contents == null) a.contents = a.content;
  if (a.old_str != null && a.old_string == null) a.old_string = a.old_str;
  if (a.new_str != null && a.new_string == null) a.new_string = a.new_str;
  if (a["-C"] != null && a.context == null) a.context = a["-C"];
  if (a["-i"] != null && a.case_sensitive == null) a.case_sensitive = !a["-i"];
  if (a.timeout_sec != null && a.timeout == null) a.timeout = a.timeout_sec;
  if (a.task && !a.prompt) a.prompt = a.task;
  if (a.question && !a.prompt) a.prompt = a.question;
  // Small models often send arrays as JSON text.
  for (const k of ["edits", "todos"]) {
    if (typeof a[k] === "string") {
      try {
        a[k] = JSON.parse(a[k]);
      } catch {
        /* reported by the tool */
      }
    }
  }
  return a;
}

/** "   12\tcode" → "code" when every non-empty line carries a Read line-number prefix. */
function stripLineNumbers(s) {
  const lines = String(s).split("\n");
  const body = lines.filter((l) => l.trim());
  if (!body.length || !body.every((l) => /^\s*\d+\t/.test(l))) return s;
  return lines.map((l) => l.replace(/^\s*\d+\t/, "")).join("\n");
}

function numbered(lines, first) {
  const w = String(first + lines.length - 1).length;
  return lines.map((l, i) => String(first + i).padStart(Math.max(w, 4)) + "\t" + l).join("\n");
}

function clip(text, max = MAX_OUT) {
  const t = String(text == null ? "" : text);
  if (t.length <= max) return t;
  const head = Math.floor(max * 0.7);
  return t.slice(0, head) + "\n…[" + (t.length - max) + " chars omitted]…\n" + t.slice(-(max - head));
}

function isUnder(abs, root) {
  const a = path.resolve(abs).toLowerCase();
  const r = path.resolve(root).toLowerCase();
  return a === r || a.startsWith(r.endsWith(path.sep) ? r : r + path.sep);
}

class ToolContext {
  /**
   * @param {object} o
   * @param {string[]} o.roots workspace folders
   * @param {string[]} [o.writableRoots] extra folders the agent may modify
   * @param {boolean} [o.readAnywhere]
   * @param {"auto"|"confirm"|"off"} [o.shellMode]
   * @param {number} [o.shellTimeoutSec]
   * @param {string} [o.rgPath]
   * @param {() => any[]} [o.skills]
   * @param {(command: string, cwd: string) => Promise<boolean>} [o.confirmShell]
   * @param {boolean} [o.requireRead] refuse edits to existing files the agent has not Read (default true)
   * @param {boolean} [o.diagnosticsAfterEdit] append new editor errors to edit results (default true)
   * @param {AbortSignal} [o.signal]
   */
  constructor(o) {
    this.roots = (o.roots || []).filter(Boolean);
    this.writable = [...this.roots, ...(o.writableRoots || [])].filter(Boolean);
    this.readAnywhere = o.readAnywhere !== false;
    this.shellMode = o.shellMode || "auto";
    this.shellTimeoutSec = o.shellTimeoutSec || 120;
    this.rgPath = o.rgPath || "rg";
    this.skills = o.skills || (() => []);
    this.confirmShell = o.confirmShell || (async () => true);
    this.requireRead = o.requireRead !== false;
    this.diagnosticsAfterEdit = o.diagnosticsAfterEdit !== false;
    this.signal = o.signal;
    /** lower-case abs path → mtime when the agent last read (or wrote) it */
    this.reads = new Map();
    /** abs path → { before: string|null } — file contents before the agent first touched it */
    this.checkpoint = new Map();
    /** @type {{content:string,status:string}[]} */
    this.todos = [];
  }

  markRead(abs) {
    try {
      this.reads.set(abs.toLowerCase(), fs.statSync(abs).mtimeMs);
    } catch {
      /* gone */
    }
  }

  /** Error text when an edit to an existing file is not based on what is on disk now, else "". */
  /** True when the read-before-edit rule applies and the agent has not read this existing file. */
  unread(abs) {
    return this.requireRead && fs.existsSync(abs) && !this.reads.has(abs.toLowerCase());
  }

  /**
   * Error text when an edit to an existing file is not based on what is on disk now, else "".
   * With exactOk, an unread file passes: StrReplace's exact unique match proves the model knows that
   * region (e.g. from Grep output), so only loose matches and whole-file writes need a Read.
   */
  staleCheck(abs, { exactOk = false } = {}) {
    if (!this.requireRead || !fs.existsSync(abs)) return "";
    const seen = this.reads.get(abs.toLowerCase());
    if (seen == null) return exactOk ? "" : "error: Read " + abs + " before changing it, so the edit is based on its current contents.";
    if (openDirty(abs)) return ""; // unsaved editor buffer: mtime says nothing, and edits go through the buffer
    let now = seen;
    try {
      now = fs.statSync(abs).mtimeMs;
    } catch {
      /* raced */
    }
    return now !== seen ? "error: " + abs + " changed on disk since you last read it. Read it again, then redo the edit." : "";
  }

  /** Keep the pre-agent contents so the turn can be reviewed and undone. */
  remember(abs) {
    if (this.checkpoint.has(abs)) return;
    let before = null;
    try {
      if (fs.existsSync(abs)) before = currentText(abs);
    } catch {
      before = null;
    }
    this.checkpoint.set(abs, { before });
  }

  resolve(p) {
    let raw = String(p || "").trim().replace(/^["'`]|["'`]$/g, "");
    if (!raw) return "";
    raw = raw.replace(/^file:\/\/\/?/i, "");
    if (/^~[\\/]/.test(raw)) raw = path.join(process.env.USERPROFILE || require("os").homedir(), raw.slice(2));
    if (!path.isAbsolute(raw)) raw = path.join(this.roots[0] || process.cwd(), raw);
    return path.normalize(raw);
  }

  canRead(abs) {
    return this.readAnywhere || this.writable.some((r) => isUnder(abs, r));
  }

  canWrite(abs) {
    return this.writable.some((r) => isUnder(abs, r));
  }

  writeDenied(abs) {
    return (
      "error: " + abs + " is outside the folders this agent may change (" + (this.writable.join("; ") || "no workspace open") +
      "). Ask the user to open that folder or add it to localAgentBridge.agent.writableRoots."
    );
  }
}

function openDoc(abs) {
  if (!vscode || !vscode.workspace || !vscode.workspace.textDocuments) return null;
  return vscode.workspace.textDocuments.find((d) => d.uri && d.uri.fsPath && d.uri.fsPath.toLowerCase() === abs.toLowerCase()) || null;
}

function openDirty(abs) {
  const d = openDoc(abs);
  return !!(d && d.isDirty);
}

function readFile(ctx, a) {
  const abs = ctx.resolve(a.path);
  if (!abs) return "error: missing path";
  if (!ctx.canRead(abs)) return "error: reading outside the workspace is disabled: " + abs;
  if (!fs.existsSync(abs)) return "error: not found: " + abs + nearMiss(abs);
  if (fs.statSync(abs).isDirectory()) return listDir(ctx, { path: abs });
  const data = openDirty(abs) ? currentText(abs) : fs.readFileSync(abs, "utf8");
  if (/\u0000/.test(data.slice(0, 8000))) return "error: " + abs + " looks like a binary file (" + fs.statSync(abs).size + " bytes)";
  ctx.markRead(abs);
  const lines = data.split(/\r?\n/);
  const start = Math.max(1, Number(a.offset) || 1);
  const limit = Math.max(1, Number(a.limit) || MAX_READ_LINES);
  const slice = lines.slice(start - 1, start - 1 + limit).map((l) => (l.length > 2000 ? l.slice(0, 2000) + "…[line cut]" : l));
  const end = start - 1 + slice.length;
  const more = end < lines.length ? "\n…[" + (lines.length - end) + " more lines — Read with offset " + (end + 1) + "]" : "";
  if (!slice.length) return abs + " (" + lines.length + " lines; offset " + start + " is past the end)";
  return abs + " (lines " + start + "-" + end + " of " + lines.length + ")\n" + clip(numbered(slice, start), 40000) + more;
}

function nearMiss(abs) {
  const dir = path.dirname(abs);
  if (!fs.existsSync(dir)) return " (parent folder does not exist either)";
  const want = path.basename(abs).toLowerCase();
  const stem = want.replace(/\.[^.]+$/, "");
  let names = [];
  try {
    names = fs.readdirSync(dir);
  } catch {
    return "";
  }
  const close = names.filter((n) => n.toLowerCase().includes(stem.slice(0, Math.max(3, stem.length - 2)))).slice(0, 8);
  return close.length ? "\nSimilar names in " + dir + ":\n" + close.join("\n") : "\n" + dir + " contains " + names.length + " entries; use LS.";
}

function listDir(ctx, a) {
  const abs = ctx.resolve(a.path || ctx.roots[0] || ".");
  if (!ctx.canRead(abs)) return "error: reading outside the workspace is disabled: " + abs;
  if (!fs.existsSync(abs)) return "error: not found: " + abs + nearMiss(abs);
  if (!fs.statSync(abs).isDirectory()) return "error: not a directory: " + abs;
  const rows = [];
  for (const ent of fs.readdirSync(abs, { withFileTypes: true })) {
    rows.push(ent.isDirectory() ? ent.name + "/" : ent.name);
  }
  rows.sort((x, y) => (x.endsWith("/") === y.endsWith("/") ? x.localeCompare(y) : x.endsWith("/") ? -1 : 1));
  return abs + " (" + rows.length + " entries)\n" + clip(rows.slice(0, 400).join("\n"));
}

function runProcess(exe, args, { cwd, timeoutSec = 60, signal, input } = {}) {
  return new Promise((resolve) => {
    let child;
    try {
      child = spawn(exe, args, { cwd, windowsHide: true });
    } catch (e) {
      resolve({ code: -1, out: "error: " + e.message });
      return;
    }
    const chunks = [];
    let size = 0;
    const take = (c) => {
      if (size < 4 * 1024 * 1024) chunks.push(c);
      size += c.length;
    };
    child.stdout.on("data", take);
    child.stderr.on("data", take);
    const kill = () => {
      try {
        if (process.platform === "win32") spawn("taskkill", ["/pid", String(child.pid), "/T", "/F"], { windowsHide: true });
        else child.kill("SIGKILL");
      } catch {
        /* already gone */
      }
    };
    const timer = setTimeout(() => {
      kill();
      chunks.push(Buffer.from("\n[timed out after " + timeoutSec + "s]"));
    }, timeoutSec * 1000);
    const onAbort = () => kill();
    if (signal) signal.addEventListener("abort", onAbort, { once: true });
    child.on("error", (e) => chunks.push(Buffer.from("error: " + e.message)));
    child.on("close", (code) => {
      clearTimeout(timer);
      if (signal) signal.removeEventListener("abort", onAbort);
      resolve({ code: code == null ? -1 : code, out: Buffer.concat(chunks).toString("utf8") });
    });
    if (input != null) child.stdin.end(input);
    else child.stdin.end();
  });
}

async function grep(ctx, a) {
  const pat = String(a.pattern || "");
  if (!pat) return "error: missing pattern";
  const target = ctx.resolve(a.path || ctx.roots[0] || ".");
  if (!ctx.canRead(target)) return "error: reading outside the workspace is disabled: " + target;
  if (!fs.existsSync(target)) return "error: not found: " + target;
  const mode = ["files_with_matches", "count"].includes(a.output_mode) ? a.output_mode : "content";
  const headLimit = Math.min(1000, Math.max(1, Number(a.head_limit) || 200));
  const args = ["--no-heading", "--color", "never", "--max-columns", "240", "--max-filesize", "2M"];
  if (!a.case_sensitive) args.push("-i");
  if (mode === "files_with_matches") args.push("-l");
  else if (mode === "count") args.push("-c");
  else {
    args.push("-n", "-m", "20");
    const ctxLines = Math.min(10, Math.max(0, Number(a.context) || 0));
    if (ctxLines) args.push("-C", String(ctxLines));
  }
  if (a.glob) args.push("-g", String(a.glob));
  let regexOk = true;
  try {
    new RegExp(pat);
  } catch {
    regexOk = false;
  }
  if (!regexOk) args.push("-F");
  args.push("--", pat, target);
  const r = await runProcess(ctx.rgPath, args, { cwd: ctx.roots[0], timeoutSec: 30, signal: ctx.signal });
  if (/ENOENT|not recognized|error: spawn/i.test(r.out) && r.code !== 0 && r.code !== 1) return grepJs(target, pat, a.glob, mode, !!a.case_sensitive);
  const out = r.out.trim();
  if (!out) return "(no matches for " + pat + " in " + target + ")";
  const lines = out.split(/\r?\n/);
  return clip((lines.length > headLimit ? lines.slice(0, headLimit).join("\n") + "\n…[" + (lines.length - headLimit) + " more lines — narrow path/glob, or use output_mode files_with_matches]" : out));
}

function walk(root, onFile, limit = 20000) {
  let n = 0;
  const stack = [root];
  while (stack.length && n < limit) {
    const dir = stack.pop();
    let ents;
    try {
      ents = fs.readdirSync(dir, { withFileTypes: true });
    } catch {
      continue;
    }
    for (const e of ents) {
      const p = path.join(dir, e.name);
      if (e.isDirectory()) {
        if (!SKIP_DIRS.has(e.name) && !e.name.startsWith(".")) stack.push(p);
      } else if (onFile(p) === false || ++n >= limit) {
        return;
      }
    }
  }
}

function globToRegex(glob) {
  let g = String(glob).replace(/\\/g, "/");
  let re = "";
  for (let i = 0; i < g.length; i++) {
    const c = g[i];
    if (c === "*") {
      if (g[i + 1] === "*") {
        re += ".*";
        i++;
        if (g[i + 1] === "/") i++;
      } else re += "[^/]*";
    } else if (c === "?") re += "[^/]";
    else if (c === "{") re += "(";
    else if (c === "}") re += ")";
    else if (c === "," ) re += "|";
    else re += c.replace(/[.+^$()|[\]\\]/g, "\\$&");
  }
  return new RegExp("(^|/)" + re + "$", "i");
}

function grepJs(target, pat, glob, mode = "content", caseSensitive = false) {
  let re;
  const flags = caseSensitive ? "" : "i";
  try {
    re = new RegExp(pat, flags);
  } catch {
    re = new RegExp(pat.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), flags);
  }
  const gre = glob ? globToRegex(glob) : null;
  const hits = [];
  const scan = (file) => {
    if (gre && !gre.test(file.replace(/\\/g, "/"))) return;
    let text;
    try {
      if (fs.statSync(file).size > 2 * 1024 * 1024) return;
      text = fs.readFileSync(file, "utf8");
    } catch {
      return;
    }
    let n = 0;
    text.split(/\r?\n/).forEach((line, i) => {
      if (!re.test(line)) return;
      n++;
      if (mode === "content" && hits.length < 200) hits.push(file + ":" + (i + 1) + ":" + line.slice(0, 240));
    });
    if (n && mode === "files_with_matches") hits.push(file);
    else if (n && mode === "count") hits.push(file + ":" + n);
    if (hits.length >= 200) return false;
  };
  if (fs.statSync(target).isFile()) scan(target);
  else walk(target, scan);
  return hits.length ? hits.join("\n") : "(no matches for " + pat + ")";
}

async function globFiles(ctx, a) {
  let pattern = String(a.pattern || "").trim();
  if (!pattern) return "error: missing pattern";
  let base = a.path ? ctx.resolve(a.path) : ctx.roots[0];
  if (path.isAbsolute(pattern) && !a.path) {
    const star = pattern.search(/[*?{]/);
    const cut = star < 0 ? pattern.length : pattern.lastIndexOf(path.sep, star);
    base = pattern.slice(0, cut);
    pattern = pattern.slice(cut + 1) || "**/*";
  }
  if (!base) return "error: no workspace folder open; pass path";
  if (!ctx.canRead(base)) return "error: reading outside the workspace is disabled: " + base;
  if (!fs.existsSync(base)) return "error: not found: " + base;
  if (!/[*?{]/.test(pattern)) pattern = "**/*" + pattern + "*";
  const r = await runProcess(ctx.rgPath, ["--files", "--color", "never", "--sortr", "modified", "-g", pattern, base], {
    cwd: base,
    timeoutSec: 30,
    signal: ctx.signal,
  });
  let files;
  if (r.code === 0 || r.code === 1) files = r.out.split(/\r?\n/).filter(Boolean);
  else {
    const re = globToRegex(pattern);
    files = [];
    walk(base, (f) => {
      if (re.test(path.relative(base, f).replace(/\\/g, "/"))) files.push(f);
      if (files.length >= 500) return false;
    });
  }
  if (!files.length) return "(no files match " + pattern + " under " + base + ")";
  const shown = files.slice(0, 150).map((f) => (path.isAbsolute(f) ? f : path.join(base, f)));
  return shown.join("\n") + (files.length > 150 ? "\n…[" + (files.length - 150) + " more — narrow the pattern]" : "");
}

async function shell(ctx, a) {
  let cmd = String(a.command || "").trim();
  if (!cmd) return "error: missing command";
  if (ctx.shellMode === "off") return "error: Shell is disabled (localAgentBridge.agent.shell = off)";
  if (BLOCKED_SHELL.some((re) => re.test(cmd))) return "error: blocked destructive command";
  const cwd = ctx.resolve(a.cwd || ctx.roots[0] || process.cwd());
  if (!fs.existsSync(cwd)) return "error: cwd not found: " + cwd;
  if (!ctx.canWrite(cwd)) return ctx.writeDenied(cwd);
  if (ctx.shellMode === "confirm" && !(await ctx.confirmShell(cmd, cwd))) return "error: the user declined to run this command";
  // A command that starts with a quoted exe path is a parse error in PowerShell without the call operator.
  if (/^["'][^"']+\.(exe|bat|cmd|ps1)["']/i.test(cmd)) cmd = "& " + cmd;
  let exe = "bash";
  let args = ["-lc", cmd];
  if (process.platform === "win32") {
    const script =
      "$ProgressPreference='SilentlyContinue'; [Console]::OutputEncoding=[Text.Encoding]::UTF8; $global:LASTEXITCODE=0\n" +
      cmd +
      "\nif ($LASTEXITCODE) { exit $LASTEXITCODE } elseif (-not $?) { exit 1 }\n";
    exe = "powershell.exe";
    args = ["-NoLogo", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-EncodedCommand", Buffer.from(script, "utf16le").toString("base64")];
  }
  const timeoutSec = Math.min(600, Math.max(1, Number(a.timeout) || ctx.shellTimeoutSec));
  const r = await runProcess(exe, args, { cwd, timeoutSec, signal: ctx.signal });
  return "exit " + r.code + " (cwd " + cwd + ")\n" + (clip(r.out.trim()) || "(no output)");
}

async function saveText(abs, contents) {
  if (vscode) {
    const doc = vscode.workspace.textDocuments.find((d) => d.uri.fsPath.toLowerCase() === abs.toLowerCase());
    if (doc && doc.isDirty) {
      const edit = new vscode.WorkspaceEdit();
      edit.replace(doc.uri, new vscode.Range(doc.positionAt(0), doc.positionAt(doc.getText().length)), contents);
      // Both report failure by returning false rather than throwing; the caller turns a throw into
      // an "error:" tool result, so the agent never claims an edit that did not land.
      if (!(await vscode.workspace.applyEdit(edit))) throw new Error("the editor refused the edit to " + abs);
      if (!(await doc.save())) throw new Error("the edit was applied but saving " + abs + " failed");
      return;
    }
  }
  fs.mkdirSync(path.dirname(abs), { recursive: true });
  fs.writeFileSync(abs, contents, "utf8");
}

function currentText(abs) {
  if (vscode) {
    const doc = vscode.workspace.textDocuments.find((d) => d.uri.fsPath.toLowerCase() === abs.toLowerCase());
    if (doc) return doc.getText();
  }
  return fs.readFileSync(abs, "utf8");
}

/**
 * Apply one exact replacement to `cur`. Returns { next, count, at } or { error }.
 * Tolerates LF old_string on a CRLF file and Read line-number prefixes copied into the strings.
 */
function applyReplace(cur, oldS, newS, replaceAll, abs, allowLoose = true) {
  if (!oldS) return { error: "old_string is empty" };
  if (oldS === newS) return { error: "old_string and new_string are identical; nothing to change" };
  const crlf = cur.includes("\r\n");
  const variants = [[oldS, newS]];
  const stripped = stripLineNumbers(oldS);
  if (stripped !== oldS) variants.push([stripped, stripLineNumbers(newS)]);
  for (const [o, n] of variants.slice()) if (crlf) variants.push([o.replace(/\r?\n/g, "\r\n"), n.replace(/\r?\n/g, "\r\n")]);
  const hit = variants.find(([o]) => cur.includes(o));
  if (!hit) {
    if (!allowLoose) return { error: "old_string not found exactly in " + abs + ", and you have not Read this file yet. Read it, then copy old_string exactly." };
    const loose = looseMatch(cur, stripped, stripLineNumbers(newS));
    if (loose === "ambiguous") return { error: "old_string matches several places in " + abs + " once whitespace is ignored; include more surrounding lines" };
    if (loose) return { ...loose, count: 1, loose: true };
    const first = stripped.split(/\r?\n/).find((l) => l.trim().length > 3) || stripped;
    const lines = cur.split(/\r?\n/);
    const near = lines.findIndex((l) => l.includes(first.trim()));
    const hint = near >= 0
      ? "\nClosest match near line " + (near + 1) + ":\n" + numbered(lines.slice(Math.max(0, near - 2), near + 6), Math.max(1, near - 1))
      : "";
    return { error: "old_string not found in " + abs + ". Read the file again and copy the text exactly (whitespace matters, line-number prefixes are not part of the file)." + hint };
  }
  const [find, repl] = hit;
  const count = cur.split(find).length - 1;
  if (count > 1 && !replaceAll) return { error: "old_string matches " + count + " places in " + abs + "; include more surrounding lines or set replace_all" };
  const at = cur.indexOf(find);
  const next = replaceAll ? cur.split(find).join(repl) : cur.slice(0, at) + repl + cur.slice(at + find.length);
  return { next, count: replaceAll ? count : 1, at, repl };
}

/**
 * Indentation-tolerant fallback for old_string: compare whole lines with leading/trailing
 * whitespace ignored. Only a single matching window is accepted. new_string is re-indented by the
 * difference between the file's indentation and the model's at the first line.
 * Returns { next, at, repl }, "ambiguous", or null.
 */
function looseMatch(cur, oldS, newS) {
  const want = oldS.replace(/\r/g, "").split("\n");
  while (want.length && !want[0].trim()) want.shift();
  while (want.length && !want[want.length - 1].trim()) want.pop();
  if (!want.length || want.join("").trim().length < 8) return null; // too little to anchor on safely
  const eol = cur.includes("\r\n") ? "\r\n" : "\n";
  const lines = cur.split(/\r?\n/);
  // Only indentation and trailing whitespace are forgiven; spacing inside a line must match.
  const norm = (l) => l.trim();
  const target = want.map(norm);
  const hits = [];
  for (let i = 0; i + target.length <= lines.length; i++) {
    let ok = true;
    for (let k = 0; k < target.length && ok; k++) ok = norm(lines[i + k]) === target[k];
    if (ok) hits.push(i);
    if (hits.length > 1) return "ambiguous";
  }
  if (!hits.length) return null;
  const i = hits[0];
  const indentOf = (l) => (l.match(/^[ \t]*/) || [""])[0];
  const fileIndent = indentOf(lines[i]);
  const modelIndent = indentOf(want[0]);
  const newLines = newS.replace(/\r/g, "").split("\n");
  while (newLines.length && !newLines[0].trim()) newLines.shift();
  while (newLines.length && !newLines[newLines.length - 1].trim()) newLines.pop();
  const reindented = newLines.map((l) => {
    if (!l.trim()) return "";
    if (l.startsWith(modelIndent)) return fileIndent + l.slice(modelIndent.length);
    return fileIndent + l.trimStart();
  });
  const before = lines.slice(0, i);
  const after = lines.slice(i + target.length);
  const at = before.length ? before.join(eol).length + eol.length : 0;
  const repl = reindented.join(eol);
  return { next: [...before, ...(reindented.length ? reindented : []), ...after].join(eol), at, repl };
}

/** Numbered lines around an edit so the model sees the result without another Read. */
function snippet(text, at, len) {
  const lines = text.split(/\r?\n/);
  const first = text.slice(0, at).split(/\r?\n/).length; // 1-based
  const span = Math.max(1, text.slice(at, at + len).split(/\r?\n/).length);
  const from = Math.max(1, first - 2);
  const to = Math.min(lines.length, first + span + 1);
  if (to - from > 30) return numbered(lines.slice(from - 1, from + 11), from) + "\n…\n" + numbered(lines.slice(to - 8, to), to - 7);
  return numbered(lines.slice(from - 1, to), from);
}

/** Wait briefly for the language server, then report errors in `abs`. "" when there are none. */
async function editorProblems(ctx, abs) {
  if (!ctx.diagnosticsAfterEdit || !vscode || !vscode.languages || !vscode.languages.onDidChangeDiagnostics) return "";
  const uri = vscode.Uri.file(abs);
  try {
    await vscode.workspace.openTextDocument(uri);
  } catch {
    return "";
  }
  await new Promise((resolve) => {
    let sub = null;
    let settle = null;
    const done = () => {
      clearTimeout(cap);
      clearTimeout(settle);
      if (sub) sub.dispose();
      resolve();
    };
    const cap = setTimeout(done, 2500);
    sub = vscode.languages.onDidChangeDiagnostics((e) => {
      if (e.uris.some((u) => u.fsPath.toLowerCase() === abs.toLowerCase())) {
        clearTimeout(settle);
        settle = setTimeout(done, 400);
      }
    });
  });
  const errs = vscode.languages.getDiagnostics(uri).filter((d) => d.severity === 0);
  if (!errs.length) return "";
  return "\nEditor errors in this file now (fix them if your edit caused them):\n" +
    errs.slice(0, 15).map((d) => "  line " + (d.range.start.line + 1) + ": " + d.message.split("\n")[0]).join("\n");
}

async function commit(ctx, abs, next) {
  ctx.remember(abs);
  await saveText(abs, next);
  ctx.markRead(abs);
}

async function strReplace(ctx, a) {
  const abs = ctx.resolve(a.path);
  if (!abs) return "error: missing path";
  if (!ctx.canWrite(abs)) return ctx.writeDenied(abs);
  if (!fs.existsSync(abs)) return "error: not found: " + abs + " (use Write to create it)";
  const unread = ctx.unread(abs);
  const stale = ctx.staleCheck(abs, { exactOk: true });
  if (stale) return stale;
  const r = applyReplace(currentText(abs), String(a.old_string == null ? "" : a.old_string), String(a.new_string == null ? "" : a.new_string), !!a.replace_all, abs, !unread);
  if (r.error) return "error: " + r.error;
  await commit(ctx, abs, r.next);
  const line = r.next.slice(0, r.at).split(/\r?\n/).length;
  return "edited " + abs + " (" + r.count + " replacement" + (r.count > 1 ? "s" : "") + ", at line " + line + (r.loose ? ", matched ignoring whitespace and re-indented — check the lines below" : "") + ")\n" +
    snippet(r.next, r.at, r.repl.length) + (await editorProblems(ctx, abs));
}

async function multiEdit(ctx, a) {
  const abs = ctx.resolve(a.path);
  if (!abs) return "error: missing path";
  if (!ctx.canWrite(abs)) return ctx.writeDenied(abs);
  if (!fs.existsSync(abs)) return "error: not found: " + abs + " (use Write to create it)";
  const edits = Array.isArray(a.edits) ? a.edits : [];
  if (!edits.length) return "error: edits must be a non-empty array of {old_string, new_string}";
  const unread = ctx.unread(abs);
  const stale = ctx.staleCheck(abs, { exactOk: true });
  if (stale) return stale;
  let cur = currentText(abs);
  let firstAt = Infinity;
  let lastEnd = 0;
  for (let i = 0; i < edits.length; i++) {
    const e = normArgs("StrReplace", edits[i]);
    const r = applyReplace(cur, String(e.old_string == null ? "" : e.old_string), String(e.new_string == null ? "" : e.new_string), !!e.replace_all, abs, !unread);
    if (r.error) return "error: edit " + (i + 1) + " of " + edits.length + ": " + r.error + "\nNo edits were applied.";
    // Keep the touched span roughly in place as later edits shift text around it.
    if (r.at < firstAt) firstAt = r.at;
    lastEnd = Math.max(lastEnd, r.at + r.repl.length);
    cur = r.next;
  }
  await commit(ctx, abs, cur);
  const line = cur.slice(0, firstAt).split(/\r?\n/).length;
  return "edited " + abs + " (" + edits.length + " edits, from line " + line + ")\n" +
    snippet(cur, firstAt, Math.max(0, lastEnd - firstAt)) + (await editorProblems(ctx, abs));
}

async function writeFile(ctx, a) {
  const abs = ctx.resolve(a.path);
  if (!abs) return "error: missing path";
  if (!ctx.canWrite(abs)) return ctx.writeDenied(abs);
  const contents = String(a.contents == null ? "" : a.contents);
  const existed = fs.existsSync(abs);
  if (existed && fs.statSync(abs).isDirectory()) return "error: " + abs + " is a folder";
  const stale = ctx.staleCheck(abs);
  if (stale) return stale.replace("before changing it", "before overwriting it (or use StrReplace for a partial change)");
  await commit(ctx, abs, contents);
  return (existed ? "overwrote " : "created ") + abs + " (" + contents.split(/\r?\n/).length + " lines)" + (await editorProblems(ctx, abs));
}

async function deleteFile(ctx, a) {
  const abs = ctx.resolve(a.path);
  if (!abs) return "error: missing path";
  if (!ctx.canWrite(abs)) return ctx.writeDenied(abs);
  if (!fs.existsSync(abs)) return "error: not found: " + abs;
  if (fs.statSync(abs).isDirectory()) return "error: Delete only removes files; use Shell for folders";
  ctx.remember(abs);
  if (vscode) await vscode.workspace.fs.delete(vscode.Uri.file(abs), { useTrash: true });
  else fs.unlinkSync(abs);
  ctx.reads.delete(abs.toLowerCase());
  return "deleted " + abs + (vscode ? " (moved to recycle bin)" : "");
}

function todoWrite(ctx, a) {
  const raw = Array.isArray(a.todos) ? a.todos : null;
  if (!raw) return "error: todos must be an array of {content, status}";
  const norm = (s) => {
    const t = String(s || "pending").toLowerCase().replace(/[\s-]+/g, "_");
    if (/^(done|complete|completed|finished)$/.test(t)) return "completed";
    if (/^(in_progress|active|doing|started|working)$/.test(t)) return "in_progress";
    return "pending";
  };
  ctx.todos = raw
    .map((t) => (typeof t === "string" ? { content: t, status: "pending" } : { content: String(t.content || t.task || t.title || "").trim(), status: norm(t.status) }))
    .filter((t) => t.content)
    .slice(0, 30);
  const active = ctx.todos.filter((t) => t.status === "in_progress").length;
  const open = ctx.todos.filter((t) => t.status !== "completed").length;
  return "Todo list updated (" + (ctx.todos.length - open) + "/" + ctx.todos.length + " done):\n" + renderTodos(ctx.todos) +
    (open && !active ? "\nNo item is in_progress: mark the one you work on next." : "");
}

function renderTodos(todos) {
  const mark = { completed: "[x]", in_progress: "[>]", pending: "[ ]" };
  return (todos || []).map((t) => mark[t.status] + " " + t.content).join("\n");
}

function readLints(ctx, a) {
  if (!vscode) return "(diagnostics need the editor)";
  const sev = ["error", "warning", "info", "hint"];
  let pairs;
  if (a.path) {
    const uri = vscode.Uri.file(ctx.resolve(a.path));
    pairs = [[uri, vscode.languages.getDiagnostics(uri)]];
  } else {
    pairs = vscode.languages.getDiagnostics();
  }
  const rows = [];
  for (const [uri, diags] of pairs) {
    for (const d of diags) {
      if (d.severity > 1) continue;
      rows.push(sev[d.severity] + " " + uri.fsPath + ":" + (d.range.start.line + 1) + " " + d.message);
    }
  }
  return rows.length ? clip(rows.slice(0, 80).join("\n")) : "(no errors or warnings" + (a.path ? " in " + a.path : "") + ")";
}

function webFetch(a, depth = 0) {
  const u = String(a.url || "").trim();
  if (!/^https?:\/\//i.test(u)) return Promise.resolve("error: url must start with http(s)://");
  const lib = u.startsWith("https") ? require("https") : require("http");
  return new Promise((resolve) => {
    const req = lib.get(u, { timeout: 20000, headers: { "User-Agent": "CortexIDE-Agent/2.0" } }, (res) => {
      if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location && depth < 4) {
        res.resume();
        resolve(webFetch({ url: new URL(res.headers.location, u).toString() }, depth + 1));
        return;
      }
      // Keep at most ~1 MB: the result is clipped to 12k chars anyway, so a huge or endless
      // response must not be buffered whole.
      const MAX_BYTES = 1024 * 1024;
      const chunks = [];
      let size = 0;
      let cut = false;
      const finish = () => {
        let text = Buffer.concat(chunks).toString("utf8");
        if (/html/i.test(res.headers["content-type"] || "")) {
          text = text
            .replace(/<(script|style|noscript)[\s\S]*?<\/\1>/gi, "")
            .replace(/<[^>]+>/g, " ")
            .replace(/&nbsp;/g, " ")
            .replace(/&amp;/g, "&")
            .replace(/&lt;/g, "<")
            .replace(/&gt;/g, ">")
            .replace(/[ \t]+/g, " ")
            .replace(/\n\s*\n+/g, "\n");
        }
        resolve("HTTP " + res.statusCode + " " + u + (cut ? " (first 1 MB only)" : "") + "\n" + clip(text.trim(), 12000));
      };
      res.on("data", (c) => {
        if (cut) return;
        const room = MAX_BYTES - size;
        if (c.length >= room) {
          chunks.push(c.subarray(0, room));
          size = MAX_BYTES;
          cut = true;
          finish();
          res.destroy();
          return;
        }
        chunks.push(c);
        size += c.length;
      });
      res.on("end", () => {
        if (!cut) finish();
      });
      res.on("error", (e) => {
        if (!cut) resolve("error: " + e.message);
      });
    });
    req.on("error", (e) => resolve("error: " + e.message));
    req.on("timeout", () => req.destroy(new Error("timeout")));
  });
}

async function execTool(ctx, name, rawArgs) {
  const canon = canonName(name);
  const a = normArgs(canon, rawArgs);
  switch (canon) {
    case "Read":
      return readFile(ctx, a);
    case "LS":
      return listDir(ctx, a);
    case "Glob":
      return globFiles(ctx, a);
    case "Grep":
      return grep(ctx, a);
    case "Shell":
      return shell(ctx, a);
    case "StrReplace":
      return strReplace(ctx, a);
    case "MultiEdit":
      return multiEdit(ctx, a);
    case "TodoWrite":
      return todoWrite(ctx, a);
    case "Task":
      return "error: Task only runs inside the agent loop";
    case "Write":
      return writeFile(ctx, a);
    case "Delete":
      return deleteFile(ctx, a);
    case "ReadLints":
      return readLints(ctx, a);
    case "WebFetch":
      return webFetch(a);
    case "list_skills": {
      const skills = ctx.skills();
      if (!skills.length) return "(no skills found)";
      return skills.map((s) => "- " + s.name + ": " + (s.description || "").slice(0, 160)).join("\n");
    }
    case "read_skill": {
      const want = String(a.name || "").toLowerCase().replace(/^\//, "");
      const s = ctx.skills().find((x) => x.name.toLowerCase() === want);
      if (!s) return "error: no skill named " + a.name + ". Call list_skills.";
      return "# " + s.name + "\nSource: " + s.file + "\nSupporting files: " + s.dir + "\n\n" + clip(s.instructions, 20000);
    }
    case "attempt_completion":
      return "completed";
    default:
      return "error: unknown tool " + name + ". Available: " + [...NAMES].join(", ");
  }
}

function defaultRgPath(appRoot) {
  const candidates = [];
  if (appRoot) {
    for (const pkg of ["ripgrep-win32-x64", "ripgrep-win32-arm64", "ripgrep"]) {
      candidates.push(path.join(appRoot, "node_modules", "@vscode", pkg, "bin", "rg.exe"));
      candidates.push(path.join(appRoot, "node_modules.asar.unpacked", "@vscode", pkg, "bin", "rg.exe"));
      candidates.push(path.join(appRoot, "node_modules", "@vscode", pkg, "bin", "rg"));
    }
  }
  return candidates.find((c) => fs.existsSync(c)) || "rg";
}

module.exports = {
  TOOL_DEFS,
  NAMES,
  MUTATING,
  READ_ONLY,
  renderTodos,
  stripLineNumbers,
  canonName,
  normArgs,
  execTool,
  ToolContext,
  defaultRgPath,
  clip,
};

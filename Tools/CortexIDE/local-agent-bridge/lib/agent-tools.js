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

const TOOL_DEFS = [
  tool("Read", "Read a text file. Returns up to 400 lines; pass offset (1-based line) and limit for more.", {
    path: { type: "string", description: "Absolute path, or relative to the first workspace folder" },
    offset: { type: "number" },
    limit: { type: "number" },
  }, ["path"]),
  tool("LS", "List a directory (folders end with /).", { path: { type: "string" } }, ["path"]),
  tool("Glob", "Find files by glob pattern, e.g. **/*.cs or **/Mutations/*.xml.", {
    pattern: { type: "string" },
    path: { type: "string", description: "Folder to search (default: workspace)" },
  }, ["pattern"]),
  tool("Grep", "Search file contents with ripgrep. Returns path:line: text.", {
    pattern: { type: "string", description: "Regex (or literal text)" },
    path: { type: "string", description: "File or folder (default: workspace)" },
    glob: { type: "string", description: "Only files matching this glob, e.g. *.cs" },
  }, ["pattern"]),
  tool("Shell", "Run a PowerShell command (build, test, git, dotnet, scripts). Returns exit code and output.", {
    command: { type: "string" },
    cwd: { type: "string", description: "Working folder (default: workspace)" },
  }, ["command"]),
  tool("StrReplace", "Replace an exact, unique snippet in a file. Copy old_string verbatim from Read output.", {
    path: { type: "string" },
    old_string: { type: "string" },
    new_string: { type: "string" },
    replace_all: { type: "boolean" },
  }, ["path", "old_string", "new_string"]),
  tool("Write", "Create a file or overwrite it completely.", {
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
  list_skills: "list_skills", read_skill: "read_skill", match_skills: "list_skills",
  attempt_completion: "attempt_completion", complete: "attempt_completion", finish: "attempt_completion", done: "attempt_completion",
};

const NAMES = new Set(TOOL_DEFS.map((t) => t.function.name));
const MUTATING = new Set(["Shell", "StrReplace", "Write", "Delete"]);

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
  return a;
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
    this.signal = o.signal;
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

function readFile(ctx, a) {
  const abs = ctx.resolve(a.path);
  if (!abs) return "error: missing path";
  if (!ctx.canRead(abs)) return "error: reading outside the workspace is disabled: " + abs;
  if (!fs.existsSync(abs)) return "error: not found: " + abs + nearMiss(abs);
  if (fs.statSync(abs).isDirectory()) return listDir(ctx, { path: abs });
  const data = fs.readFileSync(abs, "utf8");
  const lines = data.split(/\r?\n/);
  const start = Math.max(1, Number(a.offset) || 1);
  const limit = Math.max(1, Number(a.limit) || MAX_READ_LINES);
  const slice = lines.slice(start - 1, start - 1 + limit);
  const end = start - 1 + slice.length;
  const more = end < lines.length ? "\n…[" + (lines.length - end) + " more lines — Read with offset " + (end + 1) + "]" : "";
  return abs + " (lines " + start + "-" + end + " of " + lines.length + ")\n" + clip(slice.join("\n"), 40000) + more;
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
  const args = ["-n", "-i", "--no-heading", "--color", "never", "--max-columns", "240", "--max-filesize", "2M", "-m", "20"];
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
  if (/ENOENT|not recognized|error: spawn/i.test(r.out) && r.code !== 0 && r.code !== 1) return grepJs(target, pat, a.glob);
  const out = r.out.trim();
  if (!out) return "(no matches for " + pat + " in " + target + ")";
  const lines = out.split(/\r?\n/);
  return clip((lines.length > 200 ? lines.slice(0, 200).join("\n") + "\n…[" + (lines.length - 200) + " more matches — narrow path/glob]" : out));
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

function grepJs(target, pat, glob) {
  let re;
  try {
    re = new RegExp(pat, "i");
  } catch {
    re = new RegExp(pat.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "i");
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
    text.split(/\r?\n/).forEach((line, i) => {
      if (hits.length < 200 && re.test(line)) hits.push(file + ":" + (i + 1) + ":" + line.slice(0, 240));
    });
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
  const r = await runProcess(ctx.rgPath, ["--files", "--color", "never", "-g", pattern, base], {
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
  const r = await runProcess(exe, args, { cwd, timeoutSec: ctx.shellTimeoutSec, signal: ctx.signal });
  return "exit " + r.code + " (cwd " + cwd + ")\n" + (clip(r.out.trim()) || "(no output)");
}

async function saveText(abs, contents) {
  if (vscode) {
    const doc = vscode.workspace.textDocuments.find((d) => d.uri.fsPath.toLowerCase() === abs.toLowerCase());
    if (doc && doc.isDirty) {
      const edit = new vscode.WorkspaceEdit();
      edit.replace(doc.uri, new vscode.Range(doc.positionAt(0), doc.positionAt(doc.getText().length)), contents);
      await vscode.workspace.applyEdit(edit);
      await doc.save();
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

async function strReplace(ctx, a) {
  const abs = ctx.resolve(a.path);
  if (!abs) return "error: missing path";
  if (!ctx.canWrite(abs)) return ctx.writeDenied(abs);
  if (!fs.existsSync(abs)) return "error: not found: " + abs + " (use Write to create it)";
  const oldS = String(a.old_string == null ? "" : a.old_string);
  const newS = String(a.new_string == null ? "" : a.new_string);
  if (!oldS) return "error: old_string is empty";
  let cur = currentText(abs);
  const eol = cur.includes("\r\n") ? "\r\n" : "\n";
  let find = oldS;
  let repl = newS;
  if (!cur.includes(find) && eol === "\r\n") {
    find = oldS.replace(/\r?\n/g, "\r\n");
    repl = newS.replace(/\r?\n/g, "\r\n");
  }
  if (!cur.includes(find)) {
    const first = oldS.split(/\r?\n/).find((l) => l.trim().length > 3) || oldS;
    const lines = cur.split(/\r?\n/);
    const near = lines.findIndex((l) => l.includes(first.trim()));
    const hint = near >= 0
      ? "\nClosest match near line " + (near + 1) + ":\n" + lines.slice(Math.max(0, near - 2), near + 6).join("\n")
      : "";
    return "error: old_string not found in " + abs + ". Read the file again and copy the text exactly (whitespace matters)." + hint;
  }
  const count = cur.split(find).length - 1;
  if (count > 1 && !a.replace_all) return "error: old_string matches " + count + " places in " + abs + "; include more surrounding lines or set replace_all";
  const next = a.replace_all ? cur.split(find).join(repl) : cur.replace(find, () => repl);
  await saveText(abs, next);
  const at = next.indexOf(repl);
  const line = at >= 0 ? next.slice(0, at).split(/\r?\n/).length : 0;
  return "edited " + abs + " (" + (a.replace_all ? count : 1) + " replacement" + (count > 1 && a.replace_all ? "s" : "") + (line ? ", at line " + line : "") + ")";
}

async function writeFile(ctx, a) {
  const abs = ctx.resolve(a.path);
  if (!abs) return "error: missing path";
  if (!ctx.canWrite(abs)) return ctx.writeDenied(abs);
  const contents = String(a.contents == null ? "" : a.contents);
  const existed = fs.existsSync(abs);
  await saveText(abs, contents);
  return (existed ? "overwrote " : "created ") + abs + " (" + contents.split(/\r?\n/).length + " lines)";
}

async function deleteFile(ctx, a) {
  const abs = ctx.resolve(a.path);
  if (!abs) return "error: missing path";
  if (!ctx.canWrite(abs)) return ctx.writeDenied(abs);
  if (!fs.existsSync(abs)) return "error: not found: " + abs;
  if (fs.statSync(abs).isDirectory()) return "error: Delete only removes files; use Shell for folders";
  if (vscode) await vscode.workspace.fs.delete(vscode.Uri.file(abs), { useTrash: true });
  else fs.unlinkSync(abs);
  return "deleted " + abs + (vscode ? " (moved to recycle bin)" : "");
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
      const chunks = [];
      res.on("data", (c) => chunks.push(c));
      res.on("end", () => {
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
        resolve("HTTP " + res.statusCode + " " + u + "\n" + clip(text.trim(), 12000));
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
  canonName,
  normArgs,
  execTool,
  ToolContext,
  defaultRgPath,
  clip,
};

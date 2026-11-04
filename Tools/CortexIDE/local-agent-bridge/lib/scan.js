"use strict";

const fs = require("fs");
const os = require("os");
const path = require("path");

const RESERVED = new Set(["clear", "new", "settings", "model", "help"]);
const SKIP_DIRS = new Set([
  "node_modules", ".git", ".git-rewrite", "bin", "obj", "dist",
  "out", ".next", "vendor", "__pycache__",
]);

function home() {
  return process.env.USERPROFILE || os.homedir();
}

function exists(p) {
  try {
    fs.accessSync(p);
    return true;
  } catch {
    return false;
  }
}

function parseFrontmatter(text) {
  const fm = {};
  let body = text;
  const m = /^---\s*\r?\n([\s\S]*?)\r?\n---\s*\r?\n?/.exec(text);
  if (m) {
    body = text.slice(m[0].length);
    for (const raw of m[1].split("\n")) {
      const kv = /^([A-Za-z_][\w-]*)\s*:\s*(.*)$/.exec(raw.trim());
      if (!kv) continue;
      let v = kv[2].trim().replace(/^["']|["']$/g, "");
      if (/^[>|][-+]?$/.test(v)) v = "";
      fm[kv[1].toLowerCase()] = v;
    }
    if (!fm.description) {
      const descBlock = /(?:^|\n)description:\s*[>|][-+]?\s*\r?\n([\s\S]*?)(?=\n[A-Za-z_][\w-]*\s*:|\n---|$)/.exec(m[1]);
      if (descBlock) {
        fm.description = descBlock[1].split("\n").map((l) => l.trim()).filter(Boolean).join(" ");
      }
    }
  }
  return { fm, body: body.trim() };
}

function sanitizeName(name, fallback) {
  let n = String(name || fallback || "skill")
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9_-]+/g, "-")
    .replace(/^-+|-+$/g, "");
  if (!n) n = fallback || "skill";
  if (RESERVED.has(n)) n = `skill-${n}`;
  return n.slice(0, 64);
}

function defaultSkillRoots(includeBuiltIn, extraRoots) {
  const h = home();
  const roots = [
    { dir: path.join(h, ".cursor", "skills"), source: "user", priority: 20 },
    { dir: path.join(h, ".agents", "skills"), source: "agents", priority: 30 },
    { dir: path.join(h, ".claude", "skills"), source: "claude", priority: 40 },
  ];
  if (includeBuiltIn) {
    roots.push({ dir: path.join(h, ".cursor", "skills-cursor"), source: "cursor-builtin", priority: 50 });
  }
  for (const d of extraRoots || []) {
    if (d) roots.push({ dir: d, source: "extra", priority: 10 });
  }
  return roots.filter((r) => exists(r.dir));
}

function workspaceSkillRoots(workspaceFolders) {
  const out = [];
  for (const folder of workspaceFolders || []) {
    out.push({ dir: path.join(folder, ".cursor", "skills"), source: "workspace", priority: 0 });
    out.push({ dir: path.join(folder, ".agents", "skills"), source: "workspace-agents", priority: 1 });
    out.push({ dir: path.join(folder, ".claude", "skills"), source: "workspace-claude", priority: 2 });
  }
  return out.filter((r) => exists(r.dir));
}

function walkSkillFiles(root, maxDepth, files) {
  if (maxDepth < 0 || !exists(root)) return;
  let entries;
  try {
    entries = fs.readdirSync(root, { withFileTypes: true });
  } catch {
    return;
  }
  for (const ent of entries) {
    if (ent.name.startsWith(".") && ent.name !== ".cursor") continue;
    const full = path.join(root, ent.name);
    if (ent.isDirectory()) {
      if (SKIP_DIRS.has(ent.name)) continue;
      walkSkillFiles(full, maxDepth - 1, files);
    } else if (ent.isFile() && ent.name === "SKILL.md") {
      files.push(full);
    }
  }
}

function scanPluginSkills() {
  const cache = path.join(home(), ".cursor", "plugins", "cache");
  if (!exists(cache)) return [];
  const files = [];
  walkSkillFiles(cache, 8, files);
  return files.map((file) => loadSkill(file, "plugin", 80)).filter(Boolean);
}

function loadSkill(file, source, priority) {
  let text;
  try {
    text = fs.readFileSync(file, "utf8");
  } catch {
    return null;
  }
  const { fm, body } = parseFrontmatter(text);
  const dirName = path.basename(path.dirname(file));
  const name = sanitizeName(fm.name, dirName);
  const description = String(fm.description || "").replace(/\s+/g, " ").slice(0, 1024);
  if (!body) return null;
  return {
    name,
    description,
    instructions: body,
    source,
    priority,
    file,
    dir: path.dirname(file),
    bytes: Buffer.byteLength(text, "utf8"),
  };
}

function scanSkills(options) {
  const {
    workspaceFolders = [],
    includeBuiltIn = true,
    includePlugin = false,
    extraSkillRoots = [],
  } = options || {};

  const files = [];
  const seenFiles = new Set();
  const addRoot = (root) => {
    const found = [];
    walkSkillFiles(root.dir, 3, found);
    for (const file of found) {
      const key = file.toLowerCase();
      if (seenFiles.has(key)) continue;
      seenFiles.add(key);
      const skill = loadSkill(file, root.source, root.priority);
      if (skill) files.push(skill);
    }
  };

  for (const root of workspaceSkillRoots(workspaceFolders)) addRoot(root);
  for (const root of defaultSkillRoots(includeBuiltIn, extraSkillRoots)) addRoot(root);
  if (includePlugin) files.push(...scanPluginSkills());

  files.sort((a, b) => a.priority - b.priority || a.name.localeCompare(b.name));
  const kept = [];
  const seenNames = new Set();
  for (const skill of files) {
    if (seenNames.has(skill.name)) continue;
    seenNames.add(skill.name);
    kept.push(skill);
  }
  return kept;
}

function cursorProjectSlug(folder) {
  return folder
    .replace(/^[A-Za-z]:/, (m) => m[0].toLowerCase())
    .replace(/[\\/]+/g, "-")
    .replace(/[^A-Za-z0-9._-]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

function scanCanvases(workspaceFolders) {
  const projectsRoot = path.join(home(), ".cursor", "projects");
  const canvases = [];
  const seen = new Set();

  const addDir = (dir, project) => {
    if (!exists(dir)) return;
    let names;
    try {
      names = fs.readdirSync(dir);
    } catch {
      return;
    }
    for (const name of names) {
      if (!name.endsWith(".canvas.tsx")) continue;
      const file = path.join(dir, name);
      const key = file.toLowerCase();
      if (seen.has(key)) continue;
      seen.add(key);
      canvases.push({
        name: name.replace(/\.canvas\.tsx$/i, ""),
        file,
        project,
        dir,
      });
    }
  };

  for (const folder of workspaceFolders || []) {
    addDir(path.join(folder, "canvases"), path.basename(folder));
    addDir(path.join(projectsRoot, cursorProjectSlug(folder), "canvases"), cursorProjectSlug(folder));
  }

  if (exists(projectsRoot)) {
    let projects = [];
    try {
      projects = fs.readdirSync(projectsRoot, { withFileTypes: true });
    } catch {
      projects = [];
    }
    for (const ent of projects) {
      if (!ent.isDirectory()) continue;
      addDir(path.join(projectsRoot, ent.name, "canvases"), ent.name);
    }
  }

  canvases.sort((a, b) => a.name.localeCompare(b.name));
  return canvases;
}

function matchSkills(skills, query, limit) {
  const q = String(query || "").toLowerCase();
  if (!q.trim()) return skills.slice(0, limit || 8);
  const terms = q.split(/[^a-z0-9]+/).filter((t) => t.length > 2);
  const scored = skills.map((s) => {
    const blob = `${s.name} ${s.description} ${s.instructions.slice(0, 800)}`.toLowerCase();
    let score = 0;
    if (blob.includes(q)) score += 10;
    for (const t of terms) {
      if (s.name.includes(t)) score += 5;
      if (s.description.toLowerCase().includes(t)) score += 3;
      if (blob.includes(t)) score += 1;
    }
    return { s, score };
  });
  return scored
    .filter((x) => x.score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, limit || 8)
    .map((x) => x.s);
}

module.exports = {
  home,
  exists,
  parseFrontmatter,
  sanitizeName,
  scanSkills,
  scanCanvases,
  matchSkills,
  cursorProjectSlug,
  RESERVED,
};

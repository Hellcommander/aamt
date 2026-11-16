"use strict";
// Canvases across workspaces. Cursor only finds a canvas in ~/.cursor/projects/<workspace-slug>/canvases,
// and the slug comes from the folder path, so a project that moved (F:\SteamLibrary → D:\games\Steam) or
// a second workspace on the same work loses them. Linking puts a hard link of the canvas (and its
// .canvas.data.json state) into another workspace's canvas folder: one file, shown in both. When a hard
// link is not possible (another drive), it is copied.

const fs = require("fs");
const path = require("path");
const { home, scanCanvases, cursorProjectSlug } = require("./scan");

/** The folder Cursor (and the agent) use for this workspace's canvases. */
function projectCanvasDir(folder) {
  return path.join(home(), ".cursor", "projects", cursorProjectSlug(folder), "canvases");
}

function sameFile(a, b) {
  try {
    const x = fs.statSync(a);
    const y = fs.statSync(b);
    return x.ino === y.ino && x.dev === y.dev && x.ino !== 0;
  } catch {
    return false;
  }
}

function linkOne(src, dst, { overwrite = false } = {}) {
  if (fs.existsSync(dst)) {
    if (sameFile(src, dst)) return "already linked";
    if (!overwrite) return "exists";
    fs.unlinkSync(dst);
  }
  try {
    fs.linkSync(src, dst);
    return "linked";
  } catch {
    fs.copyFileSync(src, dst);
    return "copied";
  }
}

/**
 * Link a canvas into the canvas folder of `folder` (a workspace folder path).
 * @returns {{target:string, how:string}} how: linked | copied | already linked | exists
 */
function linkCanvas(file, folder, opts = {}) {
  const dir = projectCanvasDir(folder);
  fs.mkdirSync(dir, { recursive: true });
  const target = path.join(dir, path.basename(file));
  const how = linkOne(file, target, opts);
  const data = file.replace(/\.canvas\.tsx$/i, ".canvas.data.json");
  if (how !== "exists" && fs.existsSync(data)) {
    try {
      linkOne(data, target.replace(/\.canvas\.tsx$/i, ".canvas.data.json"), opts);
    } catch {
      /* state is optional */
    }
  }
  return { target, how };
}

/** Canvases of other workspaces (not already in one of `roots`), grouped by their Cursor project. */
function otherCanvases(roots) {
  const mine = new Set((roots || []).map((r) => projectCanvasDir(r).toLowerCase()));
  for (const r of roots || []) mine.add(path.join(r, "canvases").toLowerCase());
  const here = new Set();
  for (const c of scanCanvases(roots)) if (mine.has(path.dirname(c.file).toLowerCase())) here.add(c.name.toLowerCase());
  return scanCanvases(roots).filter((c) => !mine.has(path.dirname(c.file).toLowerCase()) && !here.has(c.name.toLowerCase()));
}

module.exports = { projectCanvasDir, linkCanvas, otherCanvases, sameFile };

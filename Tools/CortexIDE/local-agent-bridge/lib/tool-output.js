"use strict";

// Full output of a tool result that had to be cut, kept in a file the agent can Grep or Read.
// Idea from opencode (https://github.com/anomalyco/opencode, MIT, Copyright (c) 2025 opencode), which
// writes truncated tool output to disk and points the model at it. Written independently.

const fs = require("fs");
const path = require("path");
const os = require("os");

const KEEP_DAYS = 3;
let pruned = false;

function dir() {
  return path.join(os.tmpdir(), "cortexide-tool-output");
}

function prune(d) {
  if (pruned) return;
  pruned = true;
  const old = Date.now() - KEEP_DAYS * 86400000;
  try {
    for (const n of fs.readdirSync(d)) {
      const p = path.join(d, n);
      try {
        if (fs.statSync(p).mtimeMs < old) fs.rmSync(p, { force: true });
      } catch {
        /* in use */
      }
    }
  } catch {
    /* no folder yet */
  }
}

/** Save text; returns the file path, or "" when it could not be written. */
function save(text, label = "output") {
  const d = dir();
  try {
    fs.mkdirSync(d, { recursive: true });
    prune(d);
    const name = new Date().toISOString().replace(/[-:]/g, "").replace(/\..*/, "") + "-" + String(label).replace(/[^\w.-]+/g, "_").slice(0, 40) + "-" + Math.random().toString(36).slice(2, 7) + ".txt";
    const p = path.join(d, name);
    fs.writeFileSync(p, String(text));
    return p;
  } catch {
    return "";
  }
}

/**
 * `clip(text, max)`, and when something was cut, the whole text saved with a note on where it is.
 * @param {(t:string,max:number)=>string} clip
 */
function clipSaved(text, max, clip, label) {
  const t = String(text == null ? "" : text);
  if (t.length <= max) return t;
  const p = save(t, label);
  const note = p ? "\n[Full output (" + t.length + " chars, " + t.split("\n").length + " lines) saved to " + p + ". Grep it, or Read it with offset/limit, for the omitted part.]" : "";
  return clip(t, max) + note;
}

/** True for files written here (readable even when reading outside the workspace is off). */
function isOutputFile(abs) {
  const d = dir().toLowerCase();
  return path.resolve(abs).toLowerCase().startsWith(d + path.sep);
}

module.exports = { dir, save, clipSaved, isOutputFile };

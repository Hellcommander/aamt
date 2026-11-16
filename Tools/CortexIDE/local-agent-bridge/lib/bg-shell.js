"use strict";
// Background shells: servers, watchers and long builds the agent starts with
// Shell { run_in_background: true } and then reads (ShellOutput) or stops (ShellKill).
// They outlive the turn that started them (like Claude Code's background Bash), are listed per
// chat, and are all killed when the extension deactivates.

const { spawn } = require("child_process");
const { StringDecoder } = require("string_decoder");

/** Output kept per shell; older text is dropped from the front. */
const KEEP_CHARS = 512 * 1024;
/** Running shells per chat. */
const MAX_RUNNING = 6;

/** id → shell */
const shells = new Map();
let nextId = 1;

function killTree(child) {
  if (!child || child.exitCode != null) return;
  try {
    if (process.platform === "win32") spawn("taskkill", ["/pid", String(child.pid), "/T", "/F"], { windowsHide: true });
    else child.kill("SIGKILL");
  } catch {
    /* already gone */
  }
}

/**
 * Start a command in the background.
 * @returns {{id:string, pid:number}|{error:string}}
 */
function start(exe, args, { cwd, command, owner = "" }) {
  const running = [...shells.values()].filter((s) => s.owner === owner && s.exitCode == null);
  if (running.length >= MAX_RUNNING) {
    return { error: "error: " + running.length + " background shells are already running in this chat (" + running.map((s) => s.id).join(", ") + "). Stop one with ShellKill first." };
  }
  let child;
  try {
    child = spawn(exe, args, { cwd, windowsHide: true });
  } catch (e) {
    return { error: "error: " + e.message };
  }
  const s = {
    id: "bg" + nextId++,
    owner,
    command,
    cwd,
    child,
    pid: child.pid,
    started: Date.now(),
    text: "",
    dropped: 0, // chars cut from the front of `text`
    read: 0, // absolute offset (dropped + index) the agent has read up to
    exitCode: null,
    ended: 0,
    waiters: new Set(),
  };
  const decOut = new StringDecoder("utf8");
  const decErr = new StringDecoder("utf8");
  const add = (t) => {
    if (!t) return;
    s.text += t;
    if (s.text.length > KEEP_CHARS) {
      const cut = s.text.length - KEEP_CHARS;
      s.text = s.text.slice(cut);
      s.dropped += cut;
    }
    for (const w of s.waiters) w();
  };
  child.stdout.on("data", (b) => add(decOut.write(b)));
  child.stderr.on("data", (b) => add(decErr.write(b)));
  child.on("error", (e) => add("\nerror: " + e.message + "\n"));
  child.on("close", (code) => {
    add(decOut.end() + decErr.end());
    s.exitCode = code == null ? -1 : code;
    s.ended = Date.now();
    for (const w of s.waiters) w();
  });
  child.stdin.end();
  shells.set(s.id, s);
  return { id: s.id, pid: s.pid };
}

function get(id) {
  return shells.get(String(id || "").trim()) || null;
}

function status(s) {
  const secs = Math.round(((s.ended || Date.now()) - s.started) / 1000);
  return s.exitCode == null ? "running for " + secs + "s" : "exited with code " + s.exitCode + " after " + secs + "s";
}

/**
 * Resolve once new output arrives, the shell exits, `ms` pass or `signal` aborts. With `until`,
 * keeps waiting until unread output matches it (or the shell exits / time runs out).
 */
function waitFor(s, ms, { until, signal } = {}) {
  return new Promise((resolve) => {
    const unread = () => s.text.slice(Math.max(0, s.read - s.dropped));
    const ready = () => s.exitCode != null || (until ? until.test(unread()) : unread().length > 0);
    if (ms <= 0 || ready()) return resolve();
    let timer = null;
    const done = () => {
      clearTimeout(timer);
      s.waiters.delete(check);
      if (signal) signal.removeEventListener("abort", done);
      resolve();
    };
    // Output comes in bursts; a short settle keeps one read from returning half a line.
    let settle = null;
    const check = () => {
      if (!ready()) return;
      clearTimeout(settle);
      settle = setTimeout(done, 150);
    };
    s.waiters.add(check);
    timer = setTimeout(done, ms);
    if (signal) signal.addEventListener("abort", done, { once: true });
  });
}

/** Unread output since the last call (and marks it read). */
function takeNew(s, filter) {
  const from = Math.max(0, s.read - s.dropped);
  const lost = s.read < s.dropped ? s.dropped - s.read : 0;
  let out = s.text.slice(from);
  s.read = s.dropped + s.text.length;
  if (filter) out = out.split(/\r?\n/).filter((l) => filter.test(l)).join("\n");
  return (lost ? "…[" + lost + " older chars were dropped]\n" : "") + out;
}

function kill(s) {
  killTree(s.child);
}

function list(owner) {
  return [...shells.values()].filter((s) => owner == null || s.owner === owner);
}

/** Forget exited shells of a chat (or all) — running ones stay. */
function prune(owner) {
  for (const s of shells.values()) if (s.exitCode != null && (owner == null || s.owner === owner)) shells.delete(s.id);
}

function killAll(owner) {
  for (const s of shells.values()) if (owner == null || s.owner === owner) killTree(s.child);
}

module.exports = { start, get, status, waitFor, takeNew, kill, list, prune, killAll, MAX_RUNNING, _shells: shells };

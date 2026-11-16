"use strict";

// Conversation steering: messages sent to a chat while it is working.
//   steer  injected into the running turn at its next step (between tool rounds); the task goes on
//   queue  run as the chat's next turn once this one finishes
//   now    stop the running turn and send this as the next turn
// Another window, the MCP server and the steer CLI cannot reach the running window's memory, so
// they drop messages into the chat's inbox folder (sessions/<id>/inbox/*.json, beside its sub-index);
// the window running the chat moves them into its queue.

const fs = require("fs");
const path = require("path");
const { SessionStore, readMaster, defaultRoot, pidAlive } = require("./sessions");

const MODES = ["steer", "queue", "now"];
const MAX_TEXT = 20000;
/** Panel commands (/compress, /compact) cannot be folded into a running turn: they wait for it. */
const COMMAND = /^\/(compress|compact)(\s|$)/i;
const isCommand = (text) => COMMAND.test(String(text || "").trim());
/** The mode a message really gets: a command sent as "steer" waits for the turn instead. */
const modeFor = (text, mode) => {
  const m = MODES.includes(mode) ? mode : "steer";
  return m === "steer" && isCommand(text) ? "queue" : m;
};

class SteerQueue {
  constructor() {
    this.items = [];
    this.subs = new Set();
    this.seq = 0;
  }

  /** Add a message. extra may carry { from, images }. Returns the item, or null for empty text. */
  push(text, mode = "steer", extra = {}) {
    text = String(text || "").trim().slice(0, MAX_TEXT);
    if (!text) return null;
    const it = { id: ++this.seq + "-" + Date.now().toString(36), text, mode: modeFor(text, mode), at: Date.now(), ...extra, command: isCommand(text) };
    this.items.push(it);
    for (const f of this.subs) {
      try {
        f(it);
      } catch {
        /* a listener's problem is not the sender's */
      }
    }
    return it;
  }

  /** Remove and return the steering messages for the running turn, oldest first. */
  takeSteer() {
    const out = this.items.filter((i) => i.mode === "steer");
    if (out.length) this.items = this.items.filter((i) => i.mode !== "steer");
    return out;
  }

  hasSteer() {
    return this.items.some((i) => i.mode === "steer");
  }

  remove(id) {
    const i = this.items.findIndex((x) => x.id === id);
    return i < 0 ? null : this.items.splice(i, 1)[0];
  }

  setMode(id, mode) {
    const it = this.items.find((x) => x.id === id);
    if (it && MODES.includes(mode)) it.mode = modeFor(it.text, mode);
    return it || null;
  }

  /** Remove and return everything. */
  drain() {
    const out = this.items;
    this.items = [];
    return out;
  }

  get size() {
    return this.items.length;
  }

  /** What the panel shows (no image data). */
  list() {
    return this.items.map(({ id, text, mode, at, from, command }) => ({ id, text, mode, at, from: from || "", command: !!command }));
  }

  onPush(fn) {
    this.subs.add(fn);
    return () => this.subs.delete(fn);
  }
}

/** The user message that carries steering into a running turn. */
function steerMessage(items) {
  const texts = items.map((i) => String(i.text || "").trim()).filter(Boolean);
  if (!texts.length) return "";
  const from = items.find((i) => i.from) ? " (sent from " + items.find((i) => i.from).from + ")" : "";
  return (
    "[New message from the user while you were working" + from + ". It steers the current task: follow it from now on. " +
    "Keep the earlier request unless this message changes or cancels it. If you already finished something it changes, redo that part.]\n\n" +
    texts.join("\n\n")
  );
}

/** How a running turn's user message reads in the chat history once steering was taken in. */
function withSteering(text, items) {
  const texts = (items || []).map((i) => String(i.text || "").trim()).filter(Boolean);
  return texts.length ? text + "\n\n" + texts.map((t) => "[Added while working] " + t).join("\n\n") : text;
}

function inboxDir(chatDir) {
  return path.join(chatDir, "inbox");
}

/** Drop a message for a chat that runs elsewhere (another window, or for an outside tool). */
function postInbox(chatDir, { text, mode = "steer", from = "" } = {}) {
  text = String(text || "").trim().slice(0, MAX_TEXT);
  if (!text) throw new Error("empty message");
  const dir = inboxDir(chatDir);
  fs.mkdirSync(dir, { recursive: true });
  const name = Date.now().toString().padStart(14, "0") + "-" + process.pid + "-" + Math.random().toString(36).slice(2, 8) + ".json";
  const file = path.join(dir, name);
  const tmp = file + ".tmp";
  fs.writeFileSync(tmp, JSON.stringify({ text, mode: MODES.includes(mode) ? mode : "steer", from: String(from || ""), at: Date.now() }), "utf8");
  fs.renameSync(tmp, file); // the reader only picks up *.json, so it never sees half a message
  return file;
}

/** Take (read and delete) the messages waiting in a chat's inbox, oldest first. */
function takeInbox(chatDir) {
  const dir = inboxDir(chatDir);
  let names;
  try {
    names = fs.readdirSync(dir).filter((n) => n.endsWith(".json")).sort();
  } catch {
    return [];
  }
  const out = [];
  for (const n of names) {
    const f = path.join(dir, n);
    let m = null;
    try {
      m = JSON.parse(fs.readFileSync(f, "utf8"));
    } catch {
      m = null;
    }
    try {
      fs.unlinkSync(f);
    } catch {
      continue; // another reader took it
    }
    if (m && m.text) out.push({ text: String(m.text), mode: MODES.includes(m.mode) ? m.mode : "steer", from: String(m.from || ""), at: m.at || 0 });
  }
  return out;
}

/** Chats that are running right now in any open window, across every workspace in the master index. */
function listRunning({ root, workspace } = {}) {
  root = root || defaultRoot();
  const out = [];
  for (const w of readMaster(root).workspaces || []) {
    if (workspace && String(w.workspace || "").toLowerCase() !== String(workspace).toLowerCase()) continue;
    let main = null;
    try {
      main = JSON.parse(fs.readFileSync(path.join(w.dir || path.join(root, "projects", w.slug), "index.json"), "utf8"));
    } catch {
      continue;
    }
    for (const e of (main && main.sessions) || []) {
      if (e.status !== "running" || !e.pid || !pidAlive(e.pid)) continue;
      out.push({ id: e.id, title: e.title || "", model: e.model || "", provider: e.provider || "", workspace: main.workspace || w.workspace || "", pid: e.pid, updated: e.updated || 0 });
    }
  }
  return out.sort((a, b) => b.updated - a.updated);
}

/**
 * Send a message to a chat from outside its window. `id` may be a chat id, a unique id prefix or
 * a title fragment of a running chat. Returns { id, title, file }.
 */
function sendExternal({ root, id, text, mode = "steer", from = "outside" } = {}) {
  root = root || defaultRoot();
  const running = listRunning({ root });
  const q = String(id || "").trim().toLowerCase();
  let hit = running.filter((c) => c.id.toLowerCase() === q);
  if (!hit.length && q) hit = running.filter((c) => c.id.toLowerCase().startsWith(q));
  if (!hit.length && q) hit = running.filter((c) => c.title.toLowerCase().includes(q));
  if (!q && running.length === 1) hit = running;
  if (!hit.length) throw new Error(q ? "No running chat matches “" + id + "”." + (running.length ? " Running: " + running.map((c) => c.id + " (" + c.title + ")").join(", ") : " No chat is running.") : "Name the chat: " + (running.length ? running.length + " are running." : "no chat is running."));
  if (hit.length > 1) throw new Error("“" + id + "” matches " + hit.length + " running chats: " + hit.map((c) => c.id + " (" + c.title + ")").join(", "));
  const c = hit[0];
  const store = new SessionStore({ root, workspace: c.workspace });
  const file = postInbox(store.chatDir(c.id), { text, mode, from });
  return { id: c.id, title: c.title, workspace: c.workspace, file };
}

module.exports = { MODES, isCommand, modeFor, SteerQueue, steerMessage, withSteering, postInbox, takeInbox, inboxDir, listRunning, sendExternal };

"use strict";

// Canvases across workspaces: a canvas of another Cursor project (e.g. a game that moved from F: to D:)
// is hard-linked into this workspace's ~/.cursor/projects/<slug>/canvases, with its state sidecar.

const fs = require("fs");
const os = require("os");
const path = require("path");
const assert = require("assert");
const { test, after, EXT } = require("./harness");

const home = fs.mkdtempSync(path.join(os.tmpdir(), "canvas-home-"));
process.env.USERPROFILE = home;
after(() => fs.rmSync(home, { recursive: true, force: true }));
const link = require(path.join(EXT, "lib", "canvas-link"));

const oldDir = path.join(home, ".cursor", "projects", "f-SteamLibrary-steamapps-common-Starfield", "canvases");
fs.mkdirSync(oldDir, { recursive: true });
const a = path.join(oldDir, "shadow-vortex.canvas.tsx");
fs.writeFileSync(a, 'export default function A() { return null; }\n');
fs.writeFileSync(path.join(oldDir, "shadow-vortex.canvas.data.json"), '{"tab":2}');
fs.writeFileSync(path.join(oldDir, "hydra.canvas.tsx"), "export default () => null;\n");
const ws = path.join(home, "Starfield");
fs.mkdirSync(ws);

test("projectCanvasDir uses Cursor's workspace slug", () => {
  assert.strictEqual(path.basename(path.dirname(link.projectCanvasDir("D:\\games\\Steam\\steamapps\\common\\Starfield"))), "d-games-Steam-steamapps-common-Starfield");
});

test("other workspaces' canvases are offered; linking makes one file shown in both", () => {
  assert.deepStrictEqual(link.otherCanvases([ws]).map((c) => c.name).sort(), ["hydra", "shadow-vortex"]);
  const r = link.linkCanvas(a, ws);
  assert.strictEqual(r.how, "linked");
  assert.strictEqual(path.dirname(r.target), link.projectCanvasDir(ws));
  assert.ok(link.sameFile(a, r.target), "a hard link, not a copy");
  assert.strictEqual(fs.readFileSync(r.target.replace(".canvas.tsx", ".canvas.data.json"), "utf8"), '{"tab":2}', "state comes along");
  fs.appendFileSync(a, "// edited in the old workspace\n");
  assert.match(fs.readFileSync(r.target, "utf8"), /edited in the old workspace/, "edits show in both");
  assert.deepStrictEqual(link.otherCanvases([ws]).map((c) => c.name), ["hydra"], "a linked canvas is no longer offered");
  assert.strictEqual(link.linkCanvas(a, ws).how, "already linked");
});

test("a different canvas with the same name is not overwritten", () => {
  const other = path.join(home, ".cursor", "projects", "e-x", "canvases");
  fs.mkdirSync(other, { recursive: true });
  const b = path.join(other, "hydra.canvas.tsx");
  fs.writeFileSync(b, "export default () => 'b';\n");
  fs.writeFileSync(path.join(link.projectCanvasDir(ws), "hydra.canvas.tsx"), "export default () => 'mine';\n");
  assert.strictEqual(link.linkCanvas(b, ws).how, "exists");
  assert.match(fs.readFileSync(path.join(link.projectCanvasDir(ws), "hydra.canvas.tsx"), "utf8"), /mine/);
});

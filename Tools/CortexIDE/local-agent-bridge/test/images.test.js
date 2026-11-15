"use strict";

// Image support end to end: file detection / conversion, ReadImage with and without vision,
// images linked in a prompt, the per-backend message formats, and the agent loop actually
// handing tool-result and prompt images to the model (llm.chat is replaced by a script).

const fs = require("fs");
const os = require("os");
const path = require("path");
const assert = require("assert");
const { test, after, EXT } = require("./harness");
const fa = require(path.join(EXT, "lib", "file-analyze"));
const llm = require(path.join(EXT, "lib", "llm"));
const anthropic = require(path.join(EXT, "lib", "anthropic"));
const { runAgent } = require(path.join(EXT, "lib", "agent"));
const { ToolContext, execToolRich, promptImages } = require(path.join(EXT, "lib", "agent-tools"));
const { estimateTokens, compact, limitImages, Progress } = require(path.join(EXT, "lib", "agent-context"));

const realChat = llm.chat;
after(() => {
  llm.chat = realChat;
});

const ws = fs.mkdtempSync(path.join(os.tmpdir(), "agent-img-"));
after(() => fs.rmSync(ws, { recursive: true, force: true }));

function png(w, h) {
  const rgba = new Uint8Array(w * h * 4);
  for (let i = 0; i < w * h; i++) rgba.set([255, (i * 7) & 255, 0, 255], i * 4);
  return fa.encodePng(w, h, rgba);
}

/** 24-bit bottom-up BMP, which the APIs reject: it has to be converted to PNG. */
function bmp(w, h) {
  const row = Math.ceil((w * 3) / 4) * 4;
  const b = Buffer.alloc(54 + row * h);
  b.write("BM", 0);
  b.writeUInt32LE(b.length, 2);
  b.writeUInt32LE(54, 10);
  b.writeUInt32LE(40, 14);
  b.writeInt32LE(w, 18);
  b.writeInt32LE(h, 22);
  b.writeUInt16LE(1, 26);
  b.writeUInt16LE(24, 28);
  b.writeUInt32LE(row * h, 34);
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) b.set([0, 0, 255], 54 + y * row + x * 3);
  return b;
}

fs.writeFileSync(path.join(ws, "shot.png"), png(40, 20));
fs.writeFileSync(path.join(ws, "icon.bmp"), bmp(8, 4));
fs.writeFileSync(path.join(ws, "notes.txt"), "plain text\n");

const ctx = (o = {}) => new ToolContext({ roots: [ws], rgPath: "missing-rg", ...o });

test("detect + imageInfo: PNG and BMP by their bytes", () => {
  const p = fs.readFileSync(path.join(ws, "shot.png"));
  const d = fa.detect(p, "shot.png");
  assert.strictEqual(d.kind, "image");
  assert.strictEqual(d.mime, "image/png");
  const info = fa.imageInfo(p, d.format);
  assert.deepStrictEqual([info.width, info.height], [40, 20]);
  assert.strictEqual(fa.detect(fs.readFileSync(path.join(ws, "icon.bmp")), "x").kind, "image");
  assert.notStrictEqual(fa.detect(Buffer.from("hello"), "a.txt").kind, "image");
});

test("prepareImage: PNG goes as-is; BMP is converted to PNG", async () => {
  const a = await fa.prepareImage(path.join(ws, "shot.png"));
  assert.strictEqual(a.mime, "image/png");
  assert.deepStrictEqual([a.width, a.height], [40, 20]);
  assert.ok(Buffer.from(a.data, "base64").slice(1, 4).toString() === "PNG");
  const b = await fa.prepareImage(path.join(ws, "icon.bmp"));
  assert.strictEqual(b.mime, "image/png");
  assert.deepStrictEqual([b.width, b.height], [8, 4]);
});

test("findImageRefs: absolute, relative, markdown and URL references", () => {
  const refs = fa.findImageRefs('see C:\\Users\\Me\\Shots\\Cursor 1.png and ![x](media/icon.png) or https://example.com/a.jpg?x=1, also "notes.txt"');
  assert.ok(refs.includes("C:\\Users\\Me\\Shots\\Cursor 1.png"), JSON.stringify(refs));
  assert.ok(refs.includes("media/icon.png"), JSON.stringify(refs));
  assert.ok(refs.some((r) => r.startsWith("https://example.com/a.jpg")), JSON.stringify(refs));
  assert.ok(!refs.some((r) => /notes\.txt/.test(r)));
});

test("ReadImage attaches the image for a vision model", async () => {
  const r = await execToolRich(ctx({ vision: true }), "ReadImage", { path: "shot.png" });
  assert.strictEqual(r.images.length, 1, r.text);
  assert.strictEqual(r.images[0].mime, "image/png");
  assert.ok(/attached/.test(r.text), r.text);
});

test("ReadImage without vision returns metadata and says the model cannot see it", async () => {
  const r = await execToolRich(ctx({ vision: false, model: "qwen2.5-coder" }), "ReadImage", { path: "shot.png" });
  assert.strictEqual(r.images.length, 0);
  assert.ok(/cannot see images/.test(r.text), r.text);
  assert.ok(!/attached/.test(r.text), "must not claim an attachment: " + r.text);
});

test("Read on an image hands over to ReadImage instead of refusing a binary", async () => {
  const r = await execToolRich(ctx({ vision: true }), "Read", { path: "shot.png" });
  assert.strictEqual(r.images.length, 1, r.text);
});

test("promptImages: linked files that exist are attached, missing ones skipped", async () => {
  const pi = await promptImages(ctx({ vision: true }), "Compare " + path.join(ws, "shot.png") + " with icon.bmp and gone.png");
  assert.strictEqual(pi.images.length, 2, JSON.stringify(pi.notes));
  assert.strictEqual(pi.notes.length, 2);
  const none = await promptImages(ctx({ vision: false }), "look at shot.png");
  assert.strictEqual(none.images.length, 0);
  assert.ok(/cannot see images/.test(none.notes[0]));
});

const IMG = { mime: "image/png", data: "QUJD", path: "a.png", width: 4, height: 2 };
const loopMsgs = () => [
  { role: "system", content: "sys" },
  { role: "user", content: "task", images: [IMG] },
  { role: "assistant", content: null, tool_calls: [{ id: "t1", type: "function", function: { name: "ReadImage", arguments: "{}" } }] },
  { role: "tool", tool_call_id: "t1", name: "ReadImage", content: "a.png attached", images: [IMG] },
];

test("OpenAI format: image_url parts; tool images follow the round in a user message", () => {
  const out = llm.toOpenAIMessages(loopMsgs());
  assert.ok(Array.isArray(out[1].content) && out[1].content.some((p) => p.type === "image_url" && p.image_url.url === "data:image/png;base64,QUJD"));
  assert.strictEqual(out[3].role, "tool");
  assert.strictEqual(typeof out[3].content, "string");
  assert.strictEqual(out[4].role, "user");
  assert.ok(out[4].content.some((p) => p.type === "image_url"));
  assert.ok(out.every((m) => !("images" in m)));
});

test("Ollama format: base64 in images[]; tool images in a following user message", () => {
  const out = llm.toOllamaMessages(loopMsgs());
  assert.deepStrictEqual(out[1].images, ["QUJD"]);
  assert.strictEqual(out[3].role, "tool");
  assert.ok(!out[3].images);
  assert.strictEqual(out[4].role, "user");
  assert.deepStrictEqual(out[4].images, ["QUJD"]);
});

test("Claude format: image blocks in the user turn and inside the tool_result", () => {
  const { messages } = anthropic.toMessages(loopMsgs());
  const first = messages[0].content;
  assert.ok(first.some((b) => b.type === "image" && b.source.type === "base64" && b.source.media_type === "image/png" && b.source.data === "QUJD"));
  const tr = messages[2].content.find((b) => b.type === "tool_result");
  assert.ok(Array.isArray(tr.content), "tool_result with an image carries a block list");
  assert.ok(tr.content.some((b) => b.type === "image"));
  assert.ok(tr.content.some((b) => b.type === "text" && /attached/.test(b.text)));
});

test("agent loop: prompt images and ReadImage results reach the model", async () => {
  let i = 0;
  const seen = [];
  llm.chat = async (req) => {
    seen.push(req.messages);
    i++;
    if (i === 1) return { content: "Looking at it.", tool_calls: [{ id: "r1", type: "function", function: { name: "ReadImage", arguments: JSON.stringify({ path: "icon.bmp" }) } }] };
    return { content: "", tool_calls: [{ id: "r2", type: "function", function: { name: "attempt_completion", arguments: JSON.stringify({ summary: "It is blue." }) } }] };
  };
  const tools = ctx({ vision: true });
  const r = await runAgent({ backend: { provider: "vllm" }, model: "qwen2.5-vl", contextTokens: 32000, prompt: "what colour is shot.png", images: [IMG], tools, env: { roots: [ws] } });
  assert.strictEqual(r.text, "It is blue.");
  const firstUser = seen[0].find((m) => m.role === "user");
  assert.deepStrictEqual(firstUser.images, [IMG]);
  const toolMsg = seen[1].find((m) => m.role === "tool" && m.tool_call_id === "r1");
  assert.ok(toolMsg && toolMsg.images && toolMsg.images.length === 1, "ReadImage result carries its image");
  assert.strictEqual(toolMsg.images[0].mime, "image/png");
});

test("text-mode tool calls: the result message carries the images", async () => {
  let i = 0;
  let second = null;
  llm.chat = async (req) => {
    i++;
    if (i === 1) return { content: 'Checking.\n<tool_call>{"name": "ReadImage", "arguments": {"path": "shot.png"}}</tool_call>' };
    second = req.messages;
    return { content: "", tool_calls: [{ id: "z", type: "function", function: { name: "attempt_completion", arguments: '{"summary":"seen"}' } }] };
  };
  await runAgent({ backend: { provider: "vllm" }, model: "llava", contextTokens: 32000, prompt: "describe shot.png", tools: ctx({ vision: true }), env: { roots: [ws] } });
  const last = second[second.length - 1];
  assert.strictEqual(last.role, "user");
  assert.ok(last.images && last.images.length === 1, JSON.stringify(Object.keys(last)));
});

test("token estimate counts images; limitImages keeps the newest", () => {
  const big = { ...IMG, width: 1000, height: 750 };
  assert.ok(estimateTokens([{ role: "user", content: "x", images: [big] }]) > 900);
  const msgs = [1, 2, 3, 4].map((k) => ({ role: "tool", content: "r" + k, images: [{ ...IMG, path: "p" + k + ".png" }] }));
  assert.strictEqual(limitImages(msgs, 2), 2);
  assert.ok(!msgs[0].images && !msgs[1].images && msgs[2].images && msgs[3].images);
  assert.ok(/image removed to save context: p1\.png/.test(msgs[0].content));
});

test("compaction drops old images before trimming text, and keeps the task's images", () => {
  const big = { ...IMG, width: 1500, height: 1500 };
  const msgs = [{ role: "system", content: "sys" }, { role: "user", content: "task", images: [IMG] }];
  for (let k = 0; k < 12; k++) msgs.push({ role: "user", content: "step " + k, images: [{ ...big, path: "s" + k + ".png" }] });
  const level = compact(msgs, 8000, new Progress({}), { firstUser: 1, keepRecent: 4 });
  assert.ok(level >= 1);
  assert.deepStrictEqual(msgs[1].images, [IMG]);
  assert.ok(estimateTokens(msgs) <= 8000 || level >= 3, "estimate " + estimateTokens(msgs));
});

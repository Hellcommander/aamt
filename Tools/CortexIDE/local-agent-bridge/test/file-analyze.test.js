"use strict";

// AnalyzeFile's optional helpers: pdf.js (from Tools\Shared\third_party) and 7-Zip (installed
// program), plus the magic bytes that route files to them. The live parts skip themselves when
// pdf.js or 7-Zip is not on this machine.

const fs = require("fs");
const os = require("os");
const path = require("path");
const zlib = require("zlib");
const assert = require("assert");
const { spawnSync } = require("child_process");
const { test, after, EXT } = require("./harness");
const fa = require(path.join(EXT, "lib", "file-analyze"));
const { ToolContext, execToolRich } = require(path.join(EXT, "lib", "agent-tools"));

const ws = fs.mkdtempSync(path.join(os.tmpdir(), "agent-fa-"));
after(() => fs.rmSync(ws, { recursive: true, force: true }));

const THIRD_PARTY = path.resolve(EXT, "..", "..", "Shared", "third_party");
const HAVE_PDFJS = !!fa.findPdfjs([THIRD_PARTY]);
const SEVEN = fa.find7z();

const ctx = (o = {}) => new ToolContext({ roots: [ws], rgPath: "missing-rg", thirdParty: [THIRD_PARTY], ...o });

/** A small PDF whose page text sits in Flate-compressed content streams, with a correct xref. */
function makePdf(pageTexts) {
  const objs = [];
  const n = pageTexts.length;
  objs[1] = "<< /Type /Catalog /Pages 2 0 R >>";
  objs[2] = "<< /Type /Pages /Kids [" + pageTexts.map((_, i) => 4 + i * 2 + " 0 R").join(" ") + "] /Count " + n + " >>";
  objs[3] = "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>";
  const streams = {};
  pageTexts.forEach((t, i) => {
    const page = 4 + i * 2;
    objs[page] = "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 3 0 R >> >> /Contents " + (page + 1) + " 0 R >>";
    streams[page + 1] = zlib.deflateSync(Buffer.from("BT /F1 12 Tf 72 720 Td (" + t + ") Tj ET", "latin1"));
  });
  const total = 3 + n * 2;
  const parts = [Buffer.from("%PDF-1.5\n%\xe2\xe3\xcf\xd3\n", "latin1")];
  let at = parts[0].length;
  const offsets = [];
  for (let i = 1; i <= total; i++) {
    offsets[i] = at;
    let chunk;
    if (streams[i]) {
      chunk = Buffer.concat([
        Buffer.from(i + " 0 obj\n<< /Length " + streams[i].length + " /Filter /FlateDecode >>\nstream\n", "latin1"),
        streams[i],
        Buffer.from("\nendstream\nendobj\n", "latin1"),
      ]);
    } else chunk = Buffer.from(i + " 0 obj\n" + objs[i] + "\nendobj\n", "latin1");
    parts.push(chunk);
    at += chunk.length;
  }
  let xref = "xref\n0 " + (total + 1) + "\n0000000000 65535 f \n";
  for (let i = 1; i <= total; i++) xref += String(offsets[i]).padStart(10, "0") + " 00000 n \n";
  xref += "trailer\n<< /Size " + (total + 1) + " /Root 1 0 R /Info << /Title (Agent test PDF) >> >>\nstartxref\n" + at + "\n%%EOF\n";
  parts.push(Buffer.from(xref, "latin1"));
  return Buffer.concat(parts);
}

test("detect: CAB, ISO, MSI and other OLE files", () => {
  assert.strictEqual(fa.detect(Buffer.from("MSCF\0\0\0\0padding"), "x.cab").format, "cab");
  const iso = Buffer.alloc(0x8010);
  iso.write("CD001", 0x8001, "latin1");
  assert.strictEqual(fa.detect(iso, "disc.iso").format, "iso");
  const ole = Buffer.from("d0cf11e0a1b11ae1" + "00".repeat(32), "hex");
  assert.strictEqual(fa.detect(ole, "setup.msi").format, "msi");
  assert.strictEqual(fa.detect(ole, "old.doc").format, "ole");
  for (const f of ["7z", "rar", "xz", "bzip2", "zstd", "cab", "iso", "msi"]) assert.ok(fa.SEVEN_ZIP_FORMATS.has(f), f);
});

test("parsePages: single pages, ranges, open ranges, clamped to the page count", () => {
  assert.deepStrictEqual(fa.parsePages("", 3), [1, 2, 3]);
  assert.deepStrictEqual(fa.parsePages("2", 5), [2]);
  assert.deepStrictEqual(fa.parsePages("4-", 5), [4, 5]);
  assert.deepStrictEqual(fa.parsePages("1,3-4, 9", 5), [1, 3, 4]);
  assert.deepStrictEqual(fa.parsePages("junk", 5), []);
});

test("pdf.js: text from compressed streams, title, and a page selection", async () => {
  const f = path.join(ws, "doc.pdf");
  fs.writeFileSync(f, makePdf(["Hello from page one", "Second page words", "Third page here"]));
  const r = await fa.pdfjsText(f, { dirs: [THIRD_PARTY] });
  assert.ok(r, "pdf.js not found");
  assert.strictEqual(r.pages, 3);
  const all = r.lines.join("\n");
  assert.ok(/Title: Agent test PDF/.test(all), all);
  assert.ok(/Hello from page one/.test(all) && /Third page here/.test(all), all);
  const two = (await fa.pdfjsText(f, { dirs: [THIRD_PARTY], pages: "2" })).lines.join("\n");
  assert.ok(/Second page words/.test(two) && !/Hello from page one/.test(two), two);
}, { skip: !HAVE_PDFJS && "pdf.js not in Tools\\Shared\\third_party" });

test("AnalyzeFile on a PDF uses pdf.js from the context's third-party folders", async () => {
  fs.writeFileSync(path.join(ws, "tool.pdf"), makePdf(["Compressed text the agent must see"]));
  const r = await execToolRich(ctx(), "AnalyzeFile", { path: "tool.pdf" });
  assert.ok(/pdf\.js/.test(r.text) && /Compressed text the agent must see/.test(r.text), r.text);
  const none = await execToolRich(ctx({ thirdParty: [path.join(ws, "nothing-here")] }), "AnalyzeFile", { path: "tool.pdf", pages: "1" });
  assert.ok(/pdf\.js is not installed/.test(none.text), none.text);
}, { skip: !HAVE_PDFJS && "pdf.js not in Tools\\Shared\\third_party" });

test("7-Zip: AnalyzeFile lists a .7z, reads a text entry and attaches an image entry", async () => {
  const src = path.join(ws, "src");
  fs.mkdirSync(path.join(src, "sub"), { recursive: true });
  fs.writeFileSync(path.join(src, "readme.txt"), "line one\nline two\n");
  const rgba = new Uint8Array(8 * 8 * 4).fill(200);
  fs.writeFileSync(path.join(src, "sub", "icon.png"), fa.encodePng(8, 8, rgba));
  const arc = path.join(ws, "pack.7z");
  const made = spawnSync(SEVEN, ["a", "-bd", arc, "readme.txt", "sub"], { cwd: src, windowsHide: true });
  assert.strictEqual(made.status, 0, String(made.stderr));

  const list = await execToolRich(ctx(), "AnalyzeFile", { path: "pack.7z" });
  assert.ok(/read with 7-Zip/.test(list.text) && /readme\.txt/.test(list.text) && /sub\/icon\.png/.test(list.text), list.text);

  const txt = await execToolRich(ctx(), "AnalyzeFile", { path: "pack.7z", entry: "readme.txt" });
  assert.ok(/line two/.test(txt.text), txt.text);

  const img = await execToolRich(ctx({ vision: true }), "AnalyzeFile", { path: "pack.7z", entry: "icon.png" });
  assert.strictEqual(img.images.length, 1, img.text);
  assert.strictEqual(img.images[0].mime, "image/png");

  const miss = await execToolRich(ctx(), "AnalyzeFile", { path: "pack.7z", entry: "nope.bin" });
  assert.ok(/No entry matching/.test(miss.text), miss.text);
}, { skip: !SEVEN && "7-Zip not installed" });

test("without 7-Zip a .7z gets the Shell command instead of an error", () => {
  const f = path.join(ws, "fake.7z");
  fs.writeFileSync(f, Buffer.from("377abcaf271c000400000000", "hex"));
  const r = fa.analyzeFile(f);
  assert.strictEqual(r.format, "7z");
  assert.ok(/7z\.exe/.test(r.text), r.text);
});

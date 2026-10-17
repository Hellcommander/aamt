"use strict";

const fs = require("fs");
const path = require("path");

let tsCache = null;

function loadTypescript(appRoot) {
  if (tsCache) return tsCache;
  const candidates = [
    appRoot && path.join(appRoot, "extensions", "node_modules", "typescript"),
    appRoot && path.join(appRoot, "node_modules", "typescript"),
    "typescript",
  ].filter(Boolean);
  for (const c of candidates) {
    try {
      tsCache = require(c);
      return tsCache;
    } catch {
      /* next */
    }
  }
  return null;
}

function transpileCanvas(source, fileName, appRoot) {
  const ts = loadTypescript(appRoot);
  if (!ts) {
    return {
      js: "",
      diagnostics: ["TypeScript not found under CortexIDE appRoot — cannot transpile .canvas.tsx"],
    };
  }

  const result = ts.transpileModule(source, {
    compilerOptions: {
      jsx: ts.JsxEmit.React,
      module: ts.ModuleKind.CommonJS,
      target: ts.ScriptTarget.ES2020,
      esModuleInterop: true,
      skipLibCheck: true,
      isolatedModules: true,
    },
    fileName: fileName || "canvas.tsx",
    reportDiagnostics: true,
  });

  const diagnostics = (result.diagnostics || []).map((d) => {
    const msg = ts.flattenDiagnosticMessageText(d.messageText, "\n");
    const line = d.start != null && source
      ? source.slice(0, d.start).split(/\r?\n/).length
      : 0;
    return line ? `L${line}: ${msg}` : msg;
  });

  return { js: result.outputText || "", diagnostics };
}

function sidecarPath(canvasFile) {
  return String(canvasFile || "").replace(/\.canvas\.tsx$/i, ".canvas.data.json");
}

function readSidecar(canvasFile) {
  const file = sidecarPath(canvasFile);
  try {
    if (!fs.existsSync(file)) return {};
    return JSON.parse(fs.readFileSync(file, "utf8")) || {};
  } catch {
    return {};
  }
}

function writeSidecar(canvasFile, data) {
  const file = sidecarPath(canvasFile);
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, JSON.stringify(data, null, 2), "utf8");
}

module.exports = { transpileCanvas, loadTypescript, sidecarPath, readSidecar, writeSidecar };

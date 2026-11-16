"use strict";

// Markdown front matter ("---" YAML block, then the body) for agent and command files.
// A small YAML subset, enough for the files opencode, Claude Code and Cursor write: scalars,
// quoted keys ("git *": allow), inline lists [a, b], block lists, lists of maps, nested maps
// and | / > blocks. No anchors, tags or multi-document streams.

const FM = /^\uFEFF?---[ \t]*\r?\n([\s\S]*?)\r?\n---[ \t]*(?:\r?\n|$)/;

function stripComment(s) {
  // " # comment" outside quotes
  let q = "";
  for (let i = 0; i < s.length; i++) {
    const ch = s[i];
    if (q) {
      if (ch === q) q = "";
    } else if (ch === '"' || ch === "'") q = ch;
    else if (ch === "#" && (i === 0 || /\s/.test(s[i - 1]))) return s.slice(0, i).trimEnd();
  }
  return s;
}

function splitTop(s, sep) {
  const out = [];
  let q = "";
  let depth = 0;
  let cur = "";
  for (const ch of s) {
    if (q) {
      if (ch === q) q = "";
    } else if (ch === '"' || ch === "'") q = ch;
    else if (ch === "[" || ch === "{") depth++;
    else if (ch === "]" || ch === "}") depth--;
    else if (ch === sep && depth === 0) {
      out.push(cur);
      cur = "";
      continue;
    }
    cur += ch;
  }
  if (cur.trim()) out.push(cur);
  return out.map((x) => x.trim()).filter((x) => x !== "");
}

function scalar(raw) {
  const s = stripComment(String(raw).trim());
  if (s === "") return "";
  if ((s[0] === '"' && s.endsWith('"')) || (s[0] === "'" && s.endsWith("'"))) {
    const inner = s.slice(1, -1);
    return s[0] === '"' ? inner.replace(/\\(["\\nt])/g, (_, c) => ({ n: "\n", t: "\t" }[c] || c)) : inner.replace(/''/g, "'");
  }
  if (s[0] === "[" && s.endsWith("]")) return splitTop(s.slice(1, -1), ",").map(scalar);
  if (s[0] === "{" && s.endsWith("}")) {
    const o = {};
    for (const part of splitTop(s.slice(1, -1), ",")) {
      const kv = splitKey(part);
      if (kv) o[kv.key] = scalar(kv.rest);
    }
    return o;
  }
  if (/^(true|yes|on)$/i.test(s)) return true;
  if (/^(false|no|off)$/i.test(s)) return false;
  if (/^(null|~)$/i.test(s)) return null;
  if (/^-?\d+(\.\d+)?$/.test(s)) return Number(s);
  return s;
}

/** "key: rest" → {key, rest}; the key may be quoted. null when the text is not a key. */
function splitKey(t) {
  const m = /^("(?:[^"\\]|\\.)*"|'(?:[^']|'')*'|[^\s"'#\-[{][^:]*?|-[^\s:][^:]*?)\s*:(?:\s+([\s\S]*)|$)/.exec(t);
  if (!m) return null;
  let key = m[1];
  if (key[0] === '"' || key[0] === "'") key = scalar(key);
  return { key: String(key), rest: m[2] == null ? "" : m[2] };
}

const isItem = (t) => t === "-" || t.startsWith("- ");

function parseYaml(text) {
  const lines = [];
  for (const raw of String(text || "").split(/\r?\n/)) {
    const t = raw.trim();
    if (!t || t.startsWith("#")) {
      lines.push({ indent: -1, t: "", raw }); // kept for | blocks
      continue;
    }
    lines.push({ indent: raw.match(/^[ \t]*/)[0].replace(/\t/g, "  ").length, t, raw });
  }
  let i = 0;
  const skipBlank = () => {
    while (i < lines.length && lines[i].indent < 0) i++;
  };

  function block(minIndent) {
    skipBlank();
    if (i >= lines.length || lines[i].indent < minIndent) return null;
    return isItem(lines[i].t) ? list(lines[i].indent) : map(lines[i].indent);
  }

  function literal(parentIndent, folded) {
    const out = [];
    let ind = -1;
    while (i < lines.length && (lines[i].indent < 0 || lines[i].indent > parentIndent)) {
      const l = lines[i++];
      if (l.indent < 0) {
        out.push("");
        continue;
      }
      if (ind < 0) ind = l.indent;
      out.push(l.raw.replace(/\t/g, "  ").slice(ind));
    }
    while (out.length && out[out.length - 1] === "") out.pop();
    return folded ? out.join(" ").replace(/\s+/g, " ").trim() : out.join("\n");
  }

  function value(rest, indent) {
    const r = stripComment(rest.trim());
    if (r === "|" || r === "|-" || r === ">" || r === ">-") return literal(indent, r[0] === ">");
    if (r !== "") return scalar(r);
    skipBlank();
    if (i < lines.length && lines[i].indent > indent) return block(indent + 1);
    if (i < lines.length && lines[i].indent === indent && isItem(lines[i].t)) return list(indent); // "key:\n- a"
    return "";
  }

  function map(indent) {
    const out = {};
    for (;;) {
      skipBlank();
      if (i >= lines.length || lines[i].indent !== indent || isItem(lines[i].t)) break;
      const kv = splitKey(lines[i].t);
      i++;
      if (!kv) continue;
      out[kv.key] = value(kv.rest, indent);
    }
    return out;
  }

  function list(indent) {
    const out = [];
    for (;;) {
      skipBlank();
      if (i >= lines.length || lines[i].indent !== indent || !isItem(lines[i].t)) break;
      const body = lines[i].t.replace(/^-\s*/, "");
      if (!body) {
        i++;
        out.push(block(indent + 1));
        continue;
      }
      const kv = /^["'[{]/.test(body) ? null : splitKey(body);
      if (kv) {
        // "- key: v" starts a map whose further keys line up with "key".
        const itemIndent = indent + (lines[i].t.length - body.length);
        lines[i] = { indent: itemIndent, t: body, raw: " ".repeat(itemIndent) + body };
        out.push(map(itemIndent));
      } else {
        i++;
        out.push(scalar(body));
      }
    }
    return out;
  }

  const v = block(0);
  return v && typeof v === "object" && !Array.isArray(v) ? v : {};
}

/** { data, body } — data is {} when the file has no front matter. */
function parse(text) {
  const s = String(text || "");
  const m = FM.exec(s);
  if (!m) return { data: {}, body: s.replace(/^\uFEFF/, "").trim() };
  let data = {};
  try {
    data = parseYaml(m[1]);
  } catch {
    data = {};
  }
  return { data, body: s.slice(m[0].length).trim() };
}

/** "Read, Grep" | ["Read","Grep"] | {read:true, write:false} → { allow:Set|null, deny:Set } (lower-case names). */
function toolList(v) {
  const allow = new Set();
  const deny = new Set();
  if (v == null || v === "") return { allow: null, deny };
  if (typeof v === "string") v = v.split(/[,\s]+/);
  if (Array.isArray(v)) {
    for (const x of v) if (String(x || "").trim()) allow.add(String(x).trim().toLowerCase());
    return { allow: allow.size ? allow : null, deny };
  }
  if (typeof v === "object") {
    for (const [k, on] of Object.entries(v)) (on === false ? deny : allow).add(k.toLowerCase());
    return { allow: null, deny }; // a map only switches tools off (opencode's tools: {write: false})
  }
  return { allow: null, deny };
}

module.exports = { parse, parseYaml, scalar, toolList };

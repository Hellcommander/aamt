// File references in chat text: "D:\a b\c.js:12", "lib/x.js(3,4)", "file:///D:/x.png", "~/notes.md#L5".
// Shared by the extension (require) and the Agent panel (agent-view.js inlines this file into the page),
// so both agree on what counts as a path. No require() here: it must also run inside the webview.
var FileRef = (function () {
  "use strict";

  var SUFFIX = "(?::(\\d+)(?::(\\d+))?|\\((\\d+)(?:,\\s*(\\d+))?\\)|#L(\\d+)(?:C(\\d+))?)?";
  var EXT = "\\.(?=[A-Za-z0-9_]*[A-Za-z])[A-Za-z0-9_]{1,10}(?![A-Za-z0-9_])";
  var BAD = "\\\\/:*?\"<>|\\r\\n";
  var ALTS = [
    // file:///D:/a%20b/c.js
    "file:\\/\\/\\/?[^\\s\"'<>`]+?(?=[)\\],;.!?]*(?:\\s|$|[\"'`<>]))",
    // Windows absolute, folder names may hold spaces; the last part must have an extension ...
    "(?:[A-Za-z]:|\\\\\\\\[^" + BAD + "\\s]+)[\\\\/](?:[^" + BAD + "]+[\\\\/])*[^" + BAD + "\\s][^" + BAD + "]*?" + EXT,
    // ... or no spaces at all
    "(?:[A-Za-z]:|\\\\\\\\[^" + BAD + "\\s]+)[\\\\/][^\\s\"'<>|*?`]*[^\\s\"'<>|*?`.,;:)\\]]",
    // relative or POSIX: needs an extension, or a separator between two names
    "(?:~|\\.{1,2})?[\\\\/]?(?:[\\w.@+$-]+[\\\\/])*[\\w@+$-][\\w.@+$-]*" + EXT,
    "(?:~|\\.{1,2})?[\\\\/]?(?:[\\w.@+$-]+[\\\\/])+[\\w@+$-][\\w.@+$-]*",
  ];
  // never start inside a word, a URL ("https://x/y.js") or another path
  var RX = "(?<![\\w:/\\\\.@$~-])(" + ALTS.join("|") + ")" + SUFFIX;

  function num(s) {
    var n = parseInt(s, 10);
    return n > 0 ? n : 0;
  }
  function clean(p) {
    if (/^file:/i.test(p)) {
      p = p.replace(/^file:\/\/\/?/i, "");
      try {
        p = decodeURIComponent(p);
      } catch (e) {}
      if (!/^[A-Za-z]:/.test(p)) p = "/" + p;
    }
    return p.replace(/[)\],;.!?'"`]+$/, "");
  }

  /** Every file-like reference in a line of text: [{path, line, col, start, end}]. */
  function all(text) {
    text = String(text || "");
    var out = [];
    var re = new RegExp(RX, "g");
    var m;
    while ((m = re.exec(text))) {
      var raw = m[1];
      var start = m.index;
      // part of a URL ("https://x/y.js") or an e-mail address: not a file
      var before = text.slice(Math.max(0, start - 3), start);
      if (/:\/\/?$|@$/.test(before) || /^\/\//.test(raw)) continue;
      var p = clean(raw);
      if (!p || /^\.+$/.test(p) || /^[\\/]+$/.test(p)) continue;
      if (/^[^\\/\s]+@[^\\/\s]+$/.test(p) || /^(?:e\.g|i\.e|etc|vs)$/i.test(p)) continue; // e-mail, abbreviations
      out.push({
        path: p,
        line: num(m[2] || m[4] || m[6]),
        col: num(m[3] || m[5] || m[7]),
        start: start,
        end: start + m[0].length,
      });
    }
    return out;
  }

  /** The reference at character `offset` of `text` (else the first one), or null. */
  function find(text, offset) {
    var refs = all(text);
    if (!refs.length) return null;
    if (offset == null) return refs[0];
    for (var i = 0; i < refs.length; i++) if (offset >= refs[i].start && offset <= refs[i].end) return refs[i];
    return null;
  }

  /** `text` is one reference and nothing else (a label, a `code` span, a selection). */
  function whole(text) {
    var t = String(text || "").trim().replace(/^["'`<(\[]+|[>"'`)\]]+$/g, "");
    var r = find(t, 0);
    return r && r.start === 0 && r.end >= t.replace(/[)\],;.!?'"`]+$/, "").length ? r : null;
  }

  function isAbs(p) {
    return /^(?:[A-Za-z]:[\\/]|\\\\|\/)/.test(p);
  }
  function join(a, b) {
    return a.replace(/[\\/]+$/, "") + (a.indexOf("\\") >= 0 ? "\\" : "/") + b.replace(/^\.[\\/]/, "").replace(/^[\\/]+/, "");
  }

  /**
   * Absolute path of `p`: as is when absolute, ~ is the home folder, else the first workspace root that has it.
   * @param {string} p
   * @param {string[]} roots workspace folders
   * @param {{exists:(p:string)=>boolean, home?:string, join?:(a:string,b:string)=>string}} o
   * @returns {string|null}
   */
  function resolve(p, roots, o) {
    p = String(p || "").trim();
    if (!p) return null;
    var j = (o && o.join) || join;
    var exists = (o && o.exists) || function () { return false; };
    if (/^~[\\/]/.test(p) && o && o.home) p = j(o.home, p.slice(2));
    if (isAbs(p)) return exists(p) ? p : null;
    for (var i = 0; i < (roots || []).length; i++) {
      var c = j(roots[i], p);
      if (exists(c)) return c;
    }
    return null;
  }

  return { all: all, find: find, whole: whole, resolve: resolve, isAbs: isAbs };
})();
if (typeof module === "object" && module.exports) module.exports = FileRef;

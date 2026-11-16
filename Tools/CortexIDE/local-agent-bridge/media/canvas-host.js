(function () {
  const vscode = acquireVsCodeApi();
  const root = document.getElementById("root");
  const errorEl = document.getElementById("error");
  let persistTimer = null;
  let persistBuf = {};

  function showError(text) {
    if (!text) {
      errorEl.hidden = true;
      errorEl.textContent = "";
      return;
    }
    errorEl.hidden = false;
    errorEl.textContent = text;
  }

  function persist(state) {
    persistBuf = Object.assign({}, persistBuf, state);
    clearTimeout(persistTimer);
    persistTimer = setTimeout(() => {
      vscode.postMessage({ type: "persist", state: persistBuf });
    }, 200);
  }

  window.__CANVAS_HOST__ = {
    persist,
    dispatch(action) {
      vscode.postMessage({ type: "action", action });
    },
  };

  // Toolbar: name, last render time, ask / refresh / source / reveal.
  const bar = document.getElementById("bar");
  if (bar) {
    bar.addEventListener("click", (e) => {
      const b = e.target.closest("button[data-act]");
      if (b) vscode.postMessage({ type: "toolbar", action: b.dataset.act });
    });
    document.getElementById("bar-ask").addEventListener("submit", (e) => {
      e.preventDefault();
      const q = document.getElementById("bar-q");
      const text = q.value.trim();
      if (!text) return;
      vscode.postMessage({ type: "toolbar", action: "ask", text });
      q.value = "";
    });
  }
  function stamp(file) {
    const n = document.getElementById("bar-name");
    if (n && file) n.textContent = String(file).split(/[\\/]/).pop().replace(/\.canvas\.tsx$/i, "");
    const t = document.getElementById("bar-time");
    if (t) t.textContent = "updated " + new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  }

  window.addEventListener("message", (event) => {
    const msg = event.data;
    if (!msg || msg.type !== "source") return;
    stamp(msg.file);
    showError((msg.diagnostics && msg.diagnostics.length) ? msg.diagnostics.join("\n") : "");
    try {
      if (!window.CanvasRuntime) throw new Error("cursor/canvas runtime did not load");
      if (!msg.js) throw new Error("No transpiled JavaScript");
      window.CanvasRuntime.__setHost({
        file: msg.file,
        persisted: msg.persisted || {},
        kind: msg.kind || "dark",
        persist,
        dispatch: window.__CANVAS_HOST__.dispatch,
      });
      const factory = new Function(
        "exports",
        "module",
        "require",
        "React",
        msg.js + "\n;return module.exports && (module.exports.default || module.exports);"
      );
      const module = { exports: {} };
      function req(name) {
        if (name === "cursor/canvas" || name === "cursor/canvas.js") return window.CanvasRuntime;
        if (name === "react" || name === "react/jsx-runtime") return window.React;
        throw new Error("Canvas may only import from cursor/canvas, got " + name);
      }
      const Component = factory(module.exports, module, req, window.React);
      if (!Component) throw new Error("Canvas has no default export");
      const el = window.React.createElement(window.CanvasRuntime.ThemeProvider, null,
        window.React.createElement(Component)
      );
      if (!window.__canvasRoot) {
        window.__canvasRoot = window.ReactDOM.createRoot(root);
      }
      window.__canvasRoot.render(el);
    } catch (err) {
      showError(String(err && err.stack ? err.stack : err));
      if (window.__canvasRoot) {
        try { window.__canvasRoot.unmount(); } catch (_) {}
        window.__canvasRoot = null;
        root.innerHTML = "";
      }
    }
  });

  vscode.postMessage({ type: "ready" });
})();

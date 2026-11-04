(function (global) {
  const React = global.React;
  if (!React) throw new Error("React UMD must load before canvas-runtime.js");
  const h = React.createElement;
  const { useState, useEffect, useMemo, useRef, useContext, createContext } = React;

  const ThemeCtx = createContext(null);
  const CardCtx = createContext({ open: true, collapsible: false, size: "base", stickyHeader: false });
  const TextNest = createContext(false);

  let host = {
    file: "",
    persisted: {},
    kind: "dark",
    persist: function () {},
    dispatch: function () {},
  };

  function cssVar(name, fallback) {
    try {
      const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
      return v || fallback;
    } catch {
      return fallback;
    }
  }

  const colorPalette = {
    gray: "#8b8b8b",
    purple: "#b48ead",
    green: "#a3be8c",
    yellow: "#ebcb8b",
    pink: "#d08770",
    blue: "#81a1c1",
    orange: "#d08770",
    red: "#bf616a",
    teal: "#88c0d0",
  };
  const usageColorSequence = ["gray", "purple", "green", "yellow", "pink", "blue", "orange"];
  const categoryPaletteDark = colorPalette;
  const categoryPaletteLight = colorPalette;

  function buildTheme(kind) {
    const dark = kind !== "light";
    const tokens = {
      kind: dark ? "dark" : "light",
      text: {
        primary: cssVar("--vscode-editor-foreground", dark ? "#e6e6e6" : "#1e1e1e"),
        secondary: cssVar("--vscode-descriptionForeground", dark ? "#9d9d9d" : "#5a5a5a"),
        tertiary: dark ? "#7a7a7a" : "#6a6a6a",
        quaternary: dark ? "#5a5a5a" : "#8a8a8a",
        link: cssVar("--vscode-textLink-foreground", "#82aaff"),
        onAccent: cssVar("--vscode-button-foreground", "#ffffff"),
      },
      bg: {
        editor: cssVar("--vscode-editor-background", dark ? "#181818" : "#ffffff"),
        chrome: cssVar("--vscode-sideBar-background", dark ? "#141414" : "#f3f3f3"),
        elevated: cssVar("--vscode-editorWidget-background", dark ? "#1e1e1e" : "#f8f8f8"),
      },
      fill: {
        primary: cssVar("--vscode-button-background", dark ? "#2a2a2a" : "#e8e8e8"),
        secondary: dark ? "#242424" : "#ececec",
        tertiary: dark ? "#1f1f1f" : "#f4f4f4",
        quaternary: dark ? "#1a1a1a" : "#fafafa",
      },
      stroke: {
        primary: cssVar("--vscode-panel-border", dark ? "#3a3a3a" : "#d0d0d0"),
        secondary: dark ? "#2e2e2e" : "#e0e0e0",
        tertiary: dark ? "#262626" : "#ececec",
      },
      accent: {
        primary: cssVar("--vscode-focusBorder", "#82aaff"),
        control: cssVar("--vscode-button-background", "#3d5a80"),
      },
      diff: {
        added: cssVar("--vscode-diffEditor-insertedTextBackground", "#3d6b4f"),
        removed: cssVar("--vscode-diffEditor-removedTextBackground", "#7a3a3a"),
      },
      category: colorPalette,
    };
    tokens.tokens = tokens;
    tokens.palette = colorPalette;
    return tokens;
  }

  const canvasTokens = buildTheme("dark");
  const canvasTokensLight = buildTheme("light");
  const canvasPaletteDark = colorPalette;
  const canvasPaletteLight = colorPalette;

  const canvasTypography = {
    h1: { fontSize: "24px", lineHeight: "30px", fontWeight: 590 },
    h2: { fontSize: "18px", lineHeight: "24px", fontWeight: 590 },
    h3: { fontSize: "16px", lineHeight: "22px", fontWeight: 590 },
    body: { fontSize: "14px", lineHeight: "20px", fontWeight: 400 },
    small: { fontSize: "12px", lineHeight: "16px", fontWeight: 400 },
  };
  const canvasSpacing = { "0.5": 2, "1": 4, "1.5": 6, "2": 8, "2.5": 10, "3": 12, "3.5": 14, "4": 16, "4.5": 18, "5": 20, "6": 24, "7": 28, "8": 32, "9": 36, "10": 40 };
  const canvasRadius = { none: 0, xs: 2, sm: 4, md: 6, lg: 8, xl: 12, full: 9999 };

  function mergeStyle(base, override) {
    return Object.assign({}, base || {}, override || {});
  }

  function useHostTheme() {
    return useContext(ThemeCtx) || buildTheme(host.kind);
  }

  function ThemeProvider({ children }) {
    const theme = useMemo(() => buildTheme(host.kind), [host.kind]);
    return h(ThemeCtx.Provider, { value: theme }, children);
  }

  function useCanvasState(key, defaultValue) {
    const initial = Object.prototype.hasOwnProperty.call(host.persisted || {}, key)
      ? host.persisted[key]
      : defaultValue;
    const [value, setValue] = useState(initial);
    const set = (action) => {
      setValue((prev) => {
        const next = typeof action === "function" ? action(prev) : action;
        host.persisted = Object.assign({}, host.persisted, { [key]: next });
        host.persist({ [key]: next });
        return next;
      });
    };
    return [value, set];
  }

  function useCanvasAction() {
    return function dispatch(action) {
      host.dispatch(action);
    };
  }

  function toneColor(theme, tone) {
    if (tone === "success") return "#a3be8c";
    if (tone === "danger") return "#bf616a";
    if (tone === "warning") return "#ebcb8b";
    if (tone === "info") return theme.accent.primary;
    return theme.text.primary;
  }

  function Stack({ children, gap, style }) {
    return h("div", { style: mergeStyle({ display: "flex", flexDirection: "column", gap: gap != null ? gap : 12 }, style) }, children);
  }
  function Row({ children, gap, align, justify, wrap, style }) {
    const alignMap = { start: "flex-start", center: "center", end: "flex-end", stretch: "stretch" };
    const justMap = { start: "flex-start", center: "center", end: "flex-end", "space-between": "space-between" };
    return h("div", {
      style: mergeStyle({
        display: "flex",
        flexDirection: "row",
        gap: gap != null ? gap : 8,
        alignItems: alignMap[align || "center"],
        justifyContent: justMap[justify || "start"],
        flexWrap: wrap ? "wrap" : "nowrap",
      }, style),
    }, children);
  }
  function Grid({ children, columns, gap, align, style }) {
    const cols = typeof columns === "number" ? "repeat(" + columns + ", minmax(0, 1fr))" : columns;
    return h("div", {
      style: mergeStyle({
        display: "grid",
        gridTemplateColumns: cols,
        gap: gap != null ? gap : 12,
        alignItems: align || "stretch",
      }, style),
    }, children);
  }
  function Divider({ style }) {
    const theme = useHostTheme();
    return h("div", { style: mergeStyle({ height: 1, background: theme.stroke.tertiary, width: "100%" }, style) });
  }
  function Spacer() {
    return h("div", { style: { flex: 1, minWidth: 0 } });
  }

  function parseInline(children) {
    if (typeof children !== "string") return children;
    const parts = [];
    const re = /`([^`]+)`|\[([^\]]+)\]\(([^)]+)\)/g;
    let last = 0;
    let m;
    let i = 0;
    while ((m = re.exec(children))) {
      if (m.index > last) parts.push(children.slice(last, m.index));
      if (m[1] != null) parts.push(h(Code, { key: "c" + i++ }, m[1]));
      else parts.push(h(Link, { key: "l" + i++, href: m[3] }, m[2]));
      last = m.index + m[0].length;
    }
    if (!parts.length) return children;
    if (last < children.length) parts.push(children.slice(last));
    return parts;
  }

  function Text({ children, tone, size, as, weight, italic, truncate, style }) {
    const theme = useHostTheme();
    const nested = useContext(TextNest);
    const tag = as || (nested ? "span" : "p");
    const color = tone === "secondary" ? theme.text.secondary
      : tone === "tertiary" ? theme.text.tertiary
      : tone === "quaternary" ? theme.text.quaternary
      : theme.text.primary;
    const weightMap = { normal: 400, medium: 500, semibold: 590, bold: 700 };
    const trunc = truncate === true || truncate === "end"
      ? { overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }
      : truncate === "start"
        ? { overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", direction: "rtl", textAlign: "left" }
        : {};
    return h(TextNest.Provider, { value: true },
      h(tag, {
        style: mergeStyle(Object.assign({
          margin: tag === "p" ? "0" : undefined,
          color,
          fontSize: size === "small" ? "12px" : "14px",
          lineHeight: size === "small" ? "16px" : "20px",
          fontWeight: weightMap[weight || "normal"],
          fontStyle: italic ? "italic" : undefined,
        }, trunc), style),
      }, parseInline(children))
    );
  }

  function H1({ children, style }) {
    const theme = useHostTheme();
    return h("h1", { style: mergeStyle(Object.assign({ margin: 0, color: theme.text.primary }, canvasTypography.h1), style) }, children);
  }
  function H2({ children, style }) {
    const theme = useHostTheme();
    return h("h2", { style: mergeStyle(Object.assign({ margin: 0, color: theme.text.primary }, canvasTypography.h2), style) }, children);
  }
  function H3({ children, style }) {
    const theme = useHostTheme();
    return h("h3", { style: mergeStyle(Object.assign({ margin: 0, color: theme.text.primary }, canvasTypography.h3), style) }, children);
  }
  function Code({ children, style }) {
    const theme = useHostTheme();
    return h("code", {
      style: mergeStyle({
        fontFamily: "var(--canvas-mono)",
        fontSize: "0.92em",
        background: theme.fill.secondary,
        padding: "1px 5px",
        borderRadius: 4,
      }, style),
    }, children);
  }
  function Link({ children, href, style }) {
    const theme = useHostTheme();
    const dispatch = useCanvasAction();
    return h("a", {
      href: href || "#",
      style: mergeStyle({ color: theme.text.link, textDecoration: "none" }, style),
      onClick: (e) => {
        e.preventDefault();
        if (!href) return;
        if (/^[a-zA-Z]:[\\/]/.test(href) || href.startsWith("/") || href.startsWith(".")) {
          dispatch({ type: "openFile", path: href });
        } else {
          window.open(href, "_blank");
        }
      },
    }, children);
  }

  function CanvasChevron({ expanded }) {
    return h("span", {
      style: { display: "inline-block", transform: expanded ? "rotate(90deg)" : "none", width: 12, transition: "transform 80ms" },
    }, "▸");
  }

  function Card({ children, variant, size, stickyHeader, collapsible, defaultOpen, open: openProp, onOpenChange, style }) {
    const theme = useHostTheme();
    const [open, setOpen] = useState(openProp != null ? openProp : defaultOpen !== false);
    const isOpen = openProp != null ? openProp : open;
    const ctx = { open: collapsible ? isOpen : true, collapsible: !!collapsible, size: size || "base", stickyHeader: !!stickyHeader };
    const border = variant === "borderless" ? "none" : "1px solid " + theme.stroke.secondary;
    const radius = variant === "borderless" ? 0 : 8;
    return h(CardCtx.Provider, { value: Object.assign({}, ctx, {
      toggle: () => {
        const next = !isOpen;
        if (openProp == null) setOpen(next);
        if (onOpenChange) onOpenChange(next);
      },
    }) },
      h("div", {
        style: mergeStyle({
          background: variant === "borderless" ? "transparent" : theme.bg.elevated,
          border,
          borderRadius: radius,
          overflow: "hidden",
        }, style),
      }, children)
    );
  }

  function CardHeader({ children, trailing, style }) {
    const theme = useHostTheme();
    const card = useContext(CardCtx);
    const height = card.size === "lg" ? 32 : 28;
    const inner = h("div", {
      style: mergeStyle({
        display: "flex",
        alignItems: "center",
        gap: 8,
        height,
        padding: "0 12px",
        fontSize: 12,
        color: theme.text.secondary,
        borderBottom: card.open ? "1px solid " + theme.stroke.tertiary : "none",
        position: card.stickyHeader ? "sticky" : "static",
        top: 0,
        background: theme.bg.elevated,
      }, style),
    },
      card.collapsible ? h(CanvasChevron, { expanded: card.open }) : null,
      h("span", { style: { flex: 1, minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" } }, children),
      trailing ? h("span", { style: { flexShrink: 0 } }, trailing) : null
    );
    if (!card.collapsible) return inner;
    return h("button", {
      type: "button",
      onClick: card.toggle,
      style: { display: "block", width: "100%", background: "transparent", border: "none", padding: 0, color: "inherit", cursor: "pointer", textAlign: "left" },
    }, inner);
  }

  function CardBody({ children, style }) {
    const theme = useHostTheme();
    const card = useContext(CardCtx);
    if (card.collapsible && !card.open) return null;
    return h("div", { style: mergeStyle({ padding: 12, color: theme.text.primary }, style) }, children);
  }

  function Button({ children, variant, disabled, type, style, onClick }) {
    const theme = useHostTheme();
    const v = variant || "secondary";
    const bg = v === "primary" ? theme.accent.control : v === "ghost" ? "transparent" : theme.fill.primary;
    const color = v === "primary" ? theme.text.onAccent : theme.text.primary;
    const border = v === "ghost" ? "1px solid transparent" : "1px solid " + theme.stroke.secondary;
    return h("button", {
      type: type || "button",
      disabled,
      onClick,
      style: mergeStyle({
        height: 24,
        padding: "0 10px",
        borderRadius: 6,
        border,
        background: bg,
        color,
        fontSize: 12,
        cursor: disabled ? "not-allowed" : "pointer",
        opacity: disabled ? 0.5 : 1,
      }, style),
    }, children);
  }

  function Pill({ children, active, size, leadingContent, keyboardHint, disabled, title, style, onClick }) {
    const theme = useHostTheme();
    const sm = size === "sm";
    return h("button", {
      type: "button",
      title,
      disabled,
      onClick,
      style: mergeStyle({
        height: sm ? 18 : 24,
        padding: sm ? "0 6px" : "0 10px",
        borderRadius: 9999,
        border: sm ? "none" : "1px solid " + theme.stroke.secondary,
        background: active ? theme.fill.primary : "transparent",
        color: theme.text.primary,
        fontSize: sm ? 11 : 12,
        cursor: onClick && !disabled ? "pointer" : "default",
        display: "inline-flex",
        alignItems: "center",
        gap: 6,
      }, style),
    }, leadingContent, children, keyboardHint ? h("span", { style: { color: theme.text.tertiary, fontSize: 10 } }, keyboardHint) : null);
  }

  function Stat({ value, label, tone, style }) {
    const theme = useHostTheme();
    return h("div", { style: mergeStyle({ display: "flex", flexDirection: "column", gap: 2 }, style) },
      h("div", { style: { fontSize: 22, lineHeight: "28px", fontWeight: 590, color: toneColor(theme, tone) } }, value),
      h("div", { style: { fontSize: 12, color: theme.text.tertiary } }, label)
    );
  }

  function Callout({ children, tone, title, icon, style }) {
    const theme = useHostTheme();
    const t = tone || "info";
    const glyph = icon != null ? icon : (t === "warning" ? "!" : t === "danger" ? "×" : t === "success" ? "✓" : "i");
    return h("div", {
      style: mergeStyle({
        display: "flex",
        gap: 10,
        padding: 12,
        border: "1px solid " + theme.stroke.secondary,
        borderRadius: 8,
        background: theme.fill.tertiary,
      }, style),
    },
      h("div", { style: { color: toneColor(theme, t === "neutral" ? null : t), fontWeight: 700, width: 16 } }, glyph),
      h("div", { style: { flex: 1, minWidth: 0 } },
        title ? h("div", { style: { fontWeight: 590, marginBottom: 4 } }, title) : null,
        children
      )
    );
  }

  function Table({ headers, rows, columnAlign, rowTone, framed, striped, stickyHeader, style, emptyMessage }) {
    const theme = useHostTheme();
    const align = (i) => (columnAlign && columnAlign[i]) || "left";
    const body = (rows && rows.length)
      ? rows.map((row, ri) => h("tr", {
        key: ri,
        style: { background: striped && ri % 2 === 1 ? theme.fill.quaternary : "transparent" },
      }, (headers || []).map((_, ci) => h("td", {
        key: ci,
        style: { padding: "8px 10px", textAlign: align(ci), borderTop: "1px solid " + theme.stroke.tertiary, verticalAlign: "top" },
      },
        ci === 0 && rowTone && rowTone[ri]
          ? h("span", { style: { display: "inline-flex", alignItems: "center", gap: 6 } },
              h("span", { style: { width: 6, height: 6, borderRadius: 99, background: toneColor(theme, rowTone[ri]) } }),
              row[ci]
            )
          : row[ci]
      ))))
      : h("tr", null, h("td", { colSpan: (headers || []).length, style: { padding: 12, color: theme.text.tertiary } }, emptyMessage || ""));
    const table = h("table", { style: { width: "100%", borderCollapse: "collapse", fontSize: 13 } },
      h("thead", null, h("tr", null, (headers || []).map((hd, i) => h("th", {
        key: i,
        style: {
          textAlign: align(i),
          padding: "8px 10px",
          fontWeight: 590,
          fontSize: 12,
          color: theme.text.secondary,
          position: stickyHeader ? "sticky" : "static",
          top: 0,
          background: theme.bg.elevated,
        },
      }, hd)))),
      h("tbody", null, body)
    );
    if (framed === false) return h("div", { style }, table);
    return h("div", { style: mergeStyle({ border: "1px solid " + theme.stroke.secondary, borderRadius: 8, overflow: "auto" }, style) }, table);
  }

  function BarChart({ categories, series, height, horizontal, showValues, style }) {
    const theme = useHostTheme();
    const cats = categories || [];
    const s0 = (series && series[0] && series[0].data) || [];
    const max = Math.max(1, ...s0);
    const hgt = height || (horizontal ? Math.max(120, cats.length * 28) : 180);
    if (horizontal) {
      return h("div", { style: mergeStyle({ display: "flex", flexDirection: "column", gap: 6, height: hgt }, style) },
        cats.map((c, i) => {
          const v = Number(s0[i] || 0);
          return h("div", { key: i, style: { display: "flex", alignItems: "center", gap: 8 } },
            h("div", { style: { width: 120, fontSize: 12, color: theme.text.secondary, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" } }, c),
            h("div", { style: { flex: 1, height: 10, background: theme.fill.secondary, borderRadius: 4 } },
              h("div", { style: { width: (v / max * 100) + "%", height: "100%", background: theme.accent.primary, borderRadius: 4 } })
            ),
            showValues ? h("div", { style: { width: 36, fontSize: 12, color: theme.text.tertiary, textAlign: "right" } }, v) : null
          );
        })
      );
    }
    const w = Math.max(16, Math.floor(100 / Math.max(1, cats.length)));
    return h("div", { style: mergeStyle({ display: "flex", alignItems: "flex-end", gap: 6, height: hgt }, style) },
      cats.map((c, i) => {
        const v = Number(s0[i] || 0);
        return h("div", { key: i, style: { flex: 1, display: "flex", flexDirection: "column", alignItems: "center", gap: 4, height: "100%", justifyContent: "flex-end" } },
          showValues ? h("div", { style: { fontSize: 11, color: theme.text.tertiary } }, v) : null,
          h("div", { style: { width: "70%", height: (v / max * 100) + "%", background: theme.accent.primary, borderRadius: 3, minHeight: 2 } }),
          h("div", { style: { fontSize: 10, color: theme.text.tertiary, textAlign: "center" } }, c)
        );
      })
    );
  }

  function LineChart({ categories, series, height, style }) {
    const theme = useHostTheme();
    const cats = categories || [];
    const data = (series && series[0] && series[0].data) || [];
    const max = Math.max(1, ...data.map(Number));
    const hgt = height || 180;
    const pts = data.map((v, i) => {
      const x = cats.length <= 1 ? 0 : (i / (cats.length - 1)) * 100;
      const y = 100 - (Number(v) / max * 100);
      return x + "," + y;
    }).join(" ");
    return h("div", { style: mergeStyle({ height: hgt }, style) },
      h("svg", { viewBox: "0 0 100 100", preserveAspectRatio: "none", width: "100%", height: "100%" },
        h("polyline", { fill: "none", stroke: theme.accent.primary, strokeWidth: 1.5, points: pts, vectorEffect: "non-scaling-stroke" })
      )
    );
  }

  function PieChart({ data, series, style }) {
    const theme = useHostTheme();
    const items = data || (series || []).map((s) => ({ label: s.name || s.label, value: Array.isArray(s.data) ? s.data[0] : s.value }));
    const total = items.reduce((a, x) => a + Number(x.value || 0), 0) || 1;
    let acc = 0;
    return h("div", { style: mergeStyle({ display: "flex", gap: 16, alignItems: "center" }, style) },
      h("svg", { width: 96, height: 96, viewBox: "0 0 32 32" },
        items.map((it, i) => {
          const v = Number(it.value || 0) / total;
          const dash = v * 100;
          const el = h("circle", {
            key: i,
            r: 10,
            cx: 16,
            cy: 16,
            fill: "transparent",
            stroke: usageColorSequence[i % usageColorSequence.length] ? colorPalette[usageColorSequence[i % usageColorSequence.length]] : theme.accent.primary,
            strokeWidth: 6,
            strokeDasharray: dash + " " + (100 - dash),
            strokeDashoffset: 25 - acc,
          });
          acc += dash;
          return el;
        })
      ),
      h(Stack, { gap: 4 }, items.map((it, i) => h(Text, { key: i, size: "small", tone: "secondary" }, (it.label || "") + " · " + it.value)))
    );
  }

  function CollapsibleSection({ title, count, leading, trailing, defaultOpen, children, style }) {
    const [open, setOpen] = useState(defaultOpen !== false);
    const theme = useHostTheme();
    return h("div", { style },
      h("button", {
        type: "button",
        onClick: () => setOpen(!open),
        style: { display: "flex", width: "100%", alignItems: "center", gap: 8, background: "transparent", border: "none", color: theme.text.primary, padding: "6px 0", cursor: "pointer" },
      },
        h(CanvasChevron, { expanded: open }),
        leading,
        h("span", { style: { fontWeight: 590 } }, title),
        count != null ? h("span", { style: { color: theme.text.tertiary, fontSize: 12 } }, count) : null,
        h(Spacer, null),
        trailing
      ),
      open ? h("div", { style: { paddingLeft: 20 } }, children) : null
    );
  }

  function computeDAGLayout(input) {
    const nodes = (input && input.nodes) || [];
    const edges = (input && input.edges) || [];
    const incoming = {};
    nodes.forEach((n) => { incoming[n.id] = 0; });
    edges.forEach((e) => { incoming[e.to] = (incoming[e.to] || 0) + 1; });
    const ranks = [];
    const placed = new Set();
    let remaining = nodes.slice();
    while (remaining.length) {
      const layer = remaining.filter((n) => !incoming[n.id] || incoming[n.id] <= 0);
      const use = layer.length ? layer : remaining.slice(0, 1);
      ranks.push(use.map((n) => n.id));
      use.forEach((n) => placed.add(n.id));
      remaining = remaining.filter((n) => !placed.has(n.id));
      edges.forEach((e) => { if (placed.has(e.from)) incoming[e.to] = Math.max(0, (incoming[e.to] || 1) - 1); });
    }
    const laid = [];
    ranks.forEach((ids, r) => {
      ids.forEach((id, i) => {
        laid.push({ id, x: 24 + r * 180, y: 24 + i * 64, width: 140, height: 40 });
      });
    });
    return { nodes: laid, edges: edges.map((e) => ({ from: e.from, to: e.to })), ranks };
  }

  function DiffStats({ additions, deletions, style }) {
    const a = Number(additions || 0);
    const d = Number(deletions || 0);
    if (!a && !d) return null;
    return h("span", { style: mergeStyle({ fontFamily: "var(--canvas-mono)", fontSize: 12 }, style) },
      a ? h("span", { style: { color: "#a3be8c" } }, "+" + a + " ") : null,
      d ? h("span", { style: { color: "#bf616a" } }, "-" + d) : null
    );
  }

  function DiffView({ lines, showLineNumbers, showAccentStrip, style }) {
    const theme = useHostTheme();
    const nums = showLineNumbers !== false;
    return h("div", { style: mergeStyle({ fontFamily: "var(--canvas-mono)", fontSize: 12, overflow: "auto" }, style) },
      (lines || []).map((ln, i) => {
        const bg = ln.type === "added" ? "rgba(61,107,79,0.35)" : ln.type === "removed" ? "rgba(122,58,58,0.35)" : "transparent";
        const strip = ln.type === "added" ? "#a3be8c" : ln.type === "removed" ? "#bf616a" : "transparent";
        return h("div", { key: i, style: { display: "flex", background: bg } },
          showAccentStrip !== false ? h("div", { style: { width: 3, background: strip } }) : null,
          nums ? h("div", { style: { width: 40, padding: "1px 8px", color: theme.text.quaternary, textAlign: "right" } }, ln.lineNumber || "") : null,
          h("div", { style: { padding: "1px 8px", whiteSpace: "pre" } }, ln.content)
        );
      })
    );
  }

  function fieldStyle(theme) {
    return {
      height: 28,
      padding: "0 8px",
      borderRadius: 6,
      border: "1px solid " + theme.stroke.secondary,
      background: theme.bg.editor,
      color: theme.text.primary,
      fontSize: 13,
    };
  }

  function TextInput({ value, onChange, placeholder, disabled, type, style }) {
    const theme = useHostTheme();
    return h("input", {
      type: type || "text",
      value: value || "",
      placeholder,
      disabled,
      onChange: (e) => onChange && onChange(e.target.value),
      style: mergeStyle(fieldStyle(theme), style),
    });
  }
  function TextArea({ value, onChange, placeholder, disabled, rows, style }) {
    const theme = useHostTheme();
    return h("textarea", {
      value: value || "",
      placeholder,
      disabled,
      rows: rows || 3,
      onChange: (e) => onChange && onChange(e.target.value),
      style: mergeStyle(Object.assign(fieldStyle(theme), { height: "auto", padding: 8, resize: "vertical" }), style),
    });
  }
  function Checkbox({ checked, onChange, disabled, label, style }) {
    const theme = useHostTheme();
    return h("label", { style: mergeStyle({ display: "inline-flex", alignItems: "center", gap: 6, fontSize: 13 }, style) },
      h("input", { type: "checkbox", checked: !!checked, disabled, onChange: (e) => onChange && onChange(e.target.checked) }),
      label
    );
  }
  function Toggle({ checked, onChange, disabled, size, style }) {
    const theme = useHostTheme();
    const w = size === "md" ? 36 : 28;
    const hgt = size === "md" ? 20 : 16;
    return h("button", {
      type: "button",
      disabled,
      onClick: () => onChange && onChange(!checked),
      style: mergeStyle({
        width: w, height: hgt, borderRadius: 99, border: "none",
        background: checked ? theme.accent.primary : theme.fill.primary,
        position: "relative", cursor: "pointer",
      }, style),
    }, h("span", { style: { position: "absolute", top: 2, left: checked ? w - hgt + 2 : 2, width: hgt - 4, height: hgt - 4, borderRadius: 99, background: theme.text.onAccent } }));
  }
  function Select({ value, onChange, options, placeholder, disabled, style }) {
    const theme = useHostTheme();
    return h("select", {
      value: value || "",
      disabled,
      onChange: (e) => onChange && onChange(e.target.value),
      style: mergeStyle(fieldStyle(theme), style),
    },
      placeholder ? h("option", { value: "" }, placeholder) : null,
      (options || []).map((o) => h("option", { key: o.value, value: o.value, disabled: o.disabled }, o.label))
    );
  }
  function IconButton({ children, onClick, disabled, title, variant, size, style }) {
    const theme = useHostTheme();
    const px = size === "sm" ? 16 : 20;
    return h("button", {
      type: "button",
      title,
      disabled,
      onClick,
      style: mergeStyle({
        width: px, height: px, borderRadius: variant === "circle" ? 99 : 4,
        border: "none", background: variant === "circle" ? theme.fill.primary : "transparent",
        color: theme.text.secondary, cursor: "pointer",
      }, style),
    }, children);
  }

  function Swatch({ color, style }) {
    const fill = colorPalette[color] || color || colorPalette.gray;
    return h("span", { style: mergeStyle({ display: "inline-block", width: 24, height: 24, borderRadius: 6, background: fill }, style) });
  }

  function UsageBar({ segments, total, topLeftLabel, topRightLabel, style }) {
    const theme = useHostTheme();
    const segs = segments || [];
    const sum = segs.reduce((a, s) => a + Math.max(0, Number(s.value) || 0), 0);
    const t = Number(total) || sum || 1;
    const rest = Math.max(0, t - sum);
    return h("div", { style },
      (topLeftLabel || topRightLabel) ? h(Row, { justify: "space-between" },
        h(Text, { size: "small", tone: "secondary" }, topLeftLabel),
        h(Text, { size: "small", tone: "secondary" }, topRightLabel)
      ) : null,
      h("div", { style: { display: "flex", height: 8, borderRadius: 99, overflow: "hidden", background: theme.fill.secondary, marginTop: 4 } },
        segs.map((s, i) => h("div", {
          key: s.id || i,
          style: { width: (Math.max(0, Number(s.value) || 0) / t * 100) + "%", background: colorPalette[s.color || usageColorSequence[i % usageColorSequence.length]] },
        })),
        rest > 0 ? h("div", { style: { flex: 1 } }) : null
      )
    );
  }

  function TodoList({ todos, dimmedTodoIds, onTodoClick, style }) {
    if (!todos || !todos.length) return null;
    const theme = useHostTheme();
    const dim = dimmedTodoIds || new Set();
    const mark = { pending: "○", in_progress: "◐", completed: "●", cancelled: "✕" };
    return h("div", { style }, todos.map((t) => h("button", {
      key: t.id,
      type: "button",
      onClick: () => onTodoClick && onTodoClick(t),
      style: { display: "flex", gap: 8, width: "100%", background: "transparent", border: "none", color: theme.text.primary, padding: "6px 0", opacity: dim.has(t.id) ? 0.5 : 1, textAlign: "left", cursor: onTodoClick ? "pointer" : "default" },
    }, h("span", { style: { color: theme.text.tertiary } }, mark[t.status] || "○"), h("span", null, t.content))));
  }

  function TodoListCard({ todos, dimmedTodoIds, defaultExpanded, onTodoClick, style }) {
    if (!todos || !todos.length) return null;
    const done = todos.filter((t) => t.status === "completed").length;
    return h(Card, { collapsible: true, defaultOpen: defaultExpanded !== false, style },
      h(CardHeader, { trailing: h(Text, { size: "small", tone: "tertiary" }, done + " of " + todos.length + " Done") }, "Tasks"),
      h(CardBody, null, h(TodoList, { todos, dimmedTodoIds, onTodoClick }))
    );
  }

  function DocsShell({ title, subtitle, overview, toc, children, references }) {
    const theme = useHostTheme();
    const items = toc || [];
    return h("div", { style: { display: "grid", gridTemplateColumns: items.length ? "200px minmax(0, 1fr)" : "1fr", gap: 24, alignItems: "start" } },
      items.length ? h("nav", { style: { position: "sticky", top: 12 } },
        h(Text, { size: "small", tone: "tertiary", weight: "semibold" }, "On this page"),
        h("div", { style: { display: "flex", flexDirection: "column", gap: 6, marginTop: 8 } },
          items.map((it) => h("a", {
            key: it.id,
            href: "#" + it.id,
            style: { color: theme.text.secondary, textDecoration: "none", fontSize: 12, paddingLeft: (it.level || 1) > 1 ? 10 : 0 },
            onClick: (e) => {
              e.preventDefault();
              const el = document.getElementById(it.id);
              if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
            },
          }, it.label))
        )
      ) : null,
      h(Stack, { gap: 20 },
        title ? h(H1, null, title) : null,
        subtitle ? h(Text, { tone: "secondary" }, subtitle) : null,
        overview ? h(Card, null, h(CardHeader, null, "Overview"), h(CardBody, null, overview)) : null,
        children,
        references ? h(References, { items: references }) : null
      )
    );
  }

  function TableOfContents({ items, style }) {
    const theme = useHostTheme();
    return h("nav", { style }, (items || []).map((it) => h("a", {
      key: it.id,
      href: "#" + it.id,
      style: { display: "block", color: theme.text.secondary, textDecoration: "none", fontSize: 12, padding: "4px 0" },
      onClick: (e) => {
        e.preventDefault();
        const el = document.getElementById(it.id);
        if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
      },
    }, it.label)));
  }

  function DocSection({ id, title, children }) {
    return h(Stack, { gap: 8 },
      h("div", { id }, h(H2, null, title)),
      children
    );
  }

  function CodeBlock({ language, title, children, style }) {
    const theme = useHostTheme();
    return h("div", { style: mergeStyle({ border: "1px solid " + theme.stroke.secondary, borderRadius: 8, overflow: "hidden" }, style) },
      title || language ? h("div", { style: { padding: "6px 10px", fontSize: 12, color: theme.text.tertiary, borderBottom: "1px solid " + theme.stroke.tertiary } }, title || language) : null,
      h("pre", { style: { margin: 0, padding: 12, fontFamily: "var(--canvas-mono)", fontSize: 12, overflow: "auto" } }, children)
    );
  }

  function References({ items, style }) {
    const list = items || [];
    if (!list.length) return null;
    return h(Stack, { gap: 8, style },
      h(H2, null, "References"),
      list.map((it, i) => h(Row, { key: i, gap: 8, align: "center" },
        h(Link, { href: it.href }, it.label),
        it.note ? h(Text, { size: "small", tone: "tertiary" }, it.note) : null
      ))
    );
  }

  function __setHost(next) {
    host = Object.assign({}, host, next || {});
  }

  global.CanvasRuntime = {
    useState, useEffect, useMemo, useRef,
    mergeStyle, Stack, Row, Grid, Divider, Spacer, Table,
    Text, H1, H2, H3, Code, Link,
    Card, CardHeader, CardBody, CanvasChevron, Button, Pill, Stat, Callout,
    BarChart, LineChart, PieChart, CollapsibleSection, computeDAGLayout,
    DiffView, DiffStats,
    Checkbox, IconButton, Select, TextArea, TextInput, Toggle,
    useHostTheme, useCanvasState, useCanvasAction,
    Swatch, TodoList, TodoListCard, UsageBar,
    colorPalette, categoryPaletteDark, categoryPaletteLight, usageColorSequence,
    canvasTokens, canvasTokensLight, canvasPaletteDark, canvasPaletteLight,
    canvasTypography, canvasSpacing, canvasRadius,
    DocsShell, TableOfContents, DocSection, CodeBlock, References,
    ThemeProvider, __setHost,
  };
})(window);

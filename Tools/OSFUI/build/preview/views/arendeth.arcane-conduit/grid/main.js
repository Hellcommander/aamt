"use strict";

const SIZE = 5;
const CX = 2;
const CY = 2;
const ROOT = { x: 1, y: 0 };
const SCALE = 52;
const NS = "http://www.w3.org/2000/svg";
const TYPES = { empty: 0, form: 1, element: 2, modifier: 3, trigger: 4 };
const TABS = [
  { id: "form", label: "Spell", type: TYPES.form },
  { id: "modifier", label: "Mod", type: TYPES.modifier },
  { id: "trigger", label: "Trigger", type: TYPES.trigger },
  { id: "element", label: "Element", type: TYPES.element },
];
// Echoes' opening silhouette: down the center, then a right branch.
const STARTER = [
  [1, 1],
  [2, 2],
  [2, 1],
  [3, 2],
];

let hydrating = false;
let catalog = { form: [], modifier: [], trigger: [], element: [] };
let tab = "form";
let pick = { type: TYPES.form, index: 0 };
let cells = Array.from({ length: SIZE * SIZE }, () => ({ type: 0, index: -1 }));

function idx(x, y) { return y * SIZE + x; }

function cube(col, row) {
  const q = col - (row - (row & 1)) / 2;
  const r = row;
  return { q, r, s: -q - r };
}

function cubeDist(a, b) {
  return (Math.abs(a.q - b.q) + Math.abs(a.r - b.r) + Math.abs(a.s - b.s)) / 2;
}

function onBoard(x, y) {
  return x >= 0 && y >= 0 && x < SIZE && y < SIZE &&
    cubeDist(cube(x, y), cube(CX, CY)) <= 2;
}

function isRoot(x, y) { return x === ROOT.x && y === ROOT.y; }

function pixel(x, y) {
  const c = cube(x, y);
  const o = cube(CX, CY);
  const q = c.q - o.q;
  const r = c.r - o.r;
  return {
    x: SCALE * (1.5 * q),
    y: SCALE * (Math.sqrt(3) * (q / 2 + r)),
  };
}

function neighbors(x, y) {
  return (y & 1) === 0
    ? [[x + 1, y], [x, y - 1], [x - 1, y - 1], [x - 1, y], [x - 1, y + 1], [x, y + 1]]
    : [[x + 1, y], [x + 1, y - 1], [x, y - 1], [x - 1, y], [x, y + 1], [x + 1, y + 1]];
}

function vertices() {
  const out = [];
  for (let y = 0; y < SIZE; y++) {
    for (let x = 0; x < SIZE; x++) {
      if (onBoard(x, y)) out.push([x, y]);
    }
  }
  return out;
}

function triangles() {
  const faces = [];
  for (const [x, y] of vertices()) {
    const e = [x + 1, y];
    const se = (y & 1) === 0 ? [x, y + 1] : [x + 1, y + 1];
    const ne = (y & 1) === 0 ? [x, y - 1] : [x + 1, y - 1];
    if (onBoard(e[0], e[1]) && onBoard(se[0], se[1])) faces.push([[x, y], e, se]);
    if (onBoard(e[0], e[1]) && onBoard(ne[0], ne[1])) faces.push([[x, y], e, ne]);
  }
  return faces;
}

function layout() {
  const pts = vertices().map(([x, y]) => pixel(x, y));
  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;
  for (const p of pts) {
    if (p.x < minX) minX = p.x;
    if (p.y < minY) minY = p.y;
    if (p.x > maxX) maxX = p.x;
    if (p.y > maxY) maxY = p.y;
  }
  const padX = 90;
  const padY = 110;
  return {
    minX, minY, maxX, maxY,
    ox: padX - minX,
    oy: padY - minY,
    w: maxX - minX + padX * 2,
    h: maxY - minY + padY + 70,
  };
}

function svg(name, attrs) {
  const el = document.createElementNS(NS, name);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v !== undefined && v !== null) el.setAttribute(k, String(v));
  }
  return el;
}

function nameOf(type, index) {
  const key = Object.keys(TYPES).find((k) => TYPES[k] === type);
  const list = catalog[key] || [];
  return list[index] || "";
}

function connected() {
  const live = new Set();
  const parent = new Map();
  const rootI = idx(ROOT.x, ROOT.y);
  if (cells[rootI].type !== TYPES.form) return { live, parent };
  const q = [[ROOT.x, ROOT.y]];
  live.add(rootI);
  while (q.length) {
    const [x, y] = q.shift();
    const at = idx(x, y);
    if (cells[at].type === TYPES.trigger && at !== rootI) continue;
    for (const [nx, ny] of neighbors(x, y)) {
      if (!onBoard(nx, ny)) continue;
      const ni = idx(nx, ny);
      if (live.has(ni) || cells[ni].type === TYPES.empty) continue;
      live.add(ni);
      parent.set(ni, at);
      if (cells[ni].type !== TYPES.trigger) q.push([nx, ny]);
    }
  }
  return { live, parent };
}

function socketCount(live) {
  let n = 0;
  for (const i of live) {
    const x = i % SIZE;
    const y = (i / SIZE) | 0;
    if (isRoot(x, y)) continue;
    n += 1;
  }
  return n;
}

function setCell(x, y, type, index) {
  cells[idx(x, y)] = { type, index };
  if (!hydrating) osfui.action("setCell", x, y, type, index);
}

function place(x, y) {
  if (isRoot(x, y)) {
    if (tab !== "form") {
      document.getElementById("hint").textContent = "The north hex is the spell. Pick Spell, then click it or press E to swap.";
      return;
    }
    setCell(x, y, TYPES.form, pick.index);
    render();
    return;
  }
  if (tab === "form") {
    document.getElementById("hint").textContent = "Mods and triggers go on the sockets. The spell stays on the north edge.";
    return;
  }
  const at = idx(x, y);
  if (cells[at].type === pick.type && cells[at].index === pick.index) {
    setCell(x, y, 0, -1);
  } else {
    setCell(x, y, pick.type, pick.index);
  }
  render();
}

function cycleSpell(dir) {
  const list = catalog.form || [];
  if (!list.length) return;
  const cur = cells[idx(ROOT.x, ROOT.y)].index;
  const next = (cur + dir + list.length) % list.length;
  pick = { type: TYPES.form, index: next };
  tab = "form";
  setCell(ROOT.x, ROOT.y, TYPES.form, next);
  render();
}

function summary(live) {
  const root = cells[idx(ROOT.x, ROOT.y)];
  if (root.type !== TYPES.form) return "Dock a spell on the north edge.";
  const parts = [nameOf(TYPES.form, root.index) || "Spell"];
  for (const i of live) {
    const x = i % SIZE;
    const y = (i / SIZE) | 0;
    if (isRoot(x, y)) continue;
    const n = nameOf(cells[i].type, cells[i].index);
    if (n) parts.push(n);
  }
  return parts.join(" + ");
}

function renderTabs() {
  const tabs = document.getElementById("tabs");
  tabs.textContent = "";
  for (const t of TABS) {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "osf-segment" + (tab === t.id ? " is-on" : "");
    b.textContent = t.label;
    b.addEventListener("click", () => {
      tab = t.id;
      pick = { type: t.type, index: 0 };
      render();
    });
    tabs.appendChild(b);
  }
}

function renderPalette() {
  const box = document.getElementById("palette");
  box.textContent = "";
  const list = catalog[tab] || [];
  list.forEach((label, i) => {
    const b = document.createElement("button");
    b.type = "button";
    b.textContent = label;
    if (pick.type === TABS.find((t) => t.id === tab).type && pick.index === i) b.classList.add("is-on");
    b.addEventListener("click", () => {
      pick = { type: TABS.find((t) => t.id === tab).type, index: i };
      if (tab === "form") {
        setCell(ROOT.x, ROOT.y, TYPES.form, i);
      }
      render();
    });
    box.appendChild(b);
  });
}

function defs() {
  const d = svg("defs");
  const glow = svg("filter", { id: "glow", x: "-50%", y: "-50%", width: "200%", height: "200%" });
  glow.appendChild(svg("feGaussianBlur", { stdDeviation: "3.5", result: "b" }));
  const merge = svg("feMerge");
  merge.appendChild(svg("feMergeNode", { in: "b" }));
  merge.appendChild(svg("feMergeNode", { in: "SourceGraphic" }));
  glow.appendChild(merge);
  d.appendChild(glow);

  const pat = svg("pattern", {
    id: "topo",
    width: "48",
    height: "48",
    patternUnits: "userSpaceOnUse",
  });
  pat.appendChild(svg("rect", { width: "48", height: "48", fill: "#120c1c" }));
  for (const r of [8, 14, 20, 28]) {
    pat.appendChild(svg("circle", {
      cx: "24",
      cy: "24",
      r: String(r),
      fill: "none",
      stroke: "rgba(168, 130, 220, 0.11)",
      "stroke-width": "1",
    }));
  }
  d.appendChild(pat);
  return d;
}

function chevron(x1, y1, x2, y2) {
  const mx = (x1 + x2) / 2;
  const my = (y1 + y2) / 2;
  const dx = x2 - x1;
  const dy = y2 - y1;
  const len = Math.hypot(dx, dy) || 1;
  const ux = dx / len;
  const uy = dy / len;
  const px = -uy;
  const py = ux;
  const s = 7;
  const g = svg("polygon", {
    points: [
      mx + ux * s, my + uy * s,
      mx - ux * s + px * s, my - uy * s + py * s,
      mx - ux * s - px * s, my - uy * s - py * s,
    ].join(" "),
    fill: "#ff8a30",
    filter: "url(#glow)",
  });
  return g;
}

function renderBoard() {
  const mesh = document.getElementById("mesh");
  const docks = document.getElementById("docks");
  mesh.textContent = "";
  docks.textContent = "";
  const L = layout();
  mesh.setAttribute("viewBox", `0 0 ${L.w} ${L.h}`);
  mesh.appendChild(defs());

  const world = svg("g", { transform: `translate(${L.ox} ${L.oy})` });
  const { live, parent } = connected();

  for (const face of triangles()) {
    const pts = face.map(([x, y]) => {
      const p = pixel(x, y);
      return `${p.x},${p.y}`;
    }).join(" ");
    world.appendChild(svg("polygon", {
      points: pts,
      fill: "url(#topo)",
      stroke: "rgba(90, 70, 120, 0.45)",
      "stroke-width": "1",
    }));
  }

  const rim = vertices().map(([x, y]) => ({ ...pixel(x, y), x, y }));
  const hull = convexHull(rim);
  if (hull.length) {
    world.appendChild(svg("polygon", {
      points: hull.map((p) => `${p.x},${p.y}`).join(" "),
      fill: "none",
      stroke: "rgba(70, 52, 96, 0.9)",
      "stroke-width": "3",
    }));
  }

  const ghostEdges = [
    [[ROOT.x, ROOT.y], [1, 1]],
    [[1, 1], [2, 2]],
    [[1, 1], [2, 1]],
    [[2, 1], [3, 2]],
  ];
  for (const [fromCell, toCell] of ghostEdges) {
    const destFilled = cells[idx(toCell[0], toCell[1])].type !== TYPES.empty;
    const srcFilled = isRoot(fromCell[0], fromCell[1]) ||
      cells[idx(fromCell[0], fromCell[1])].type !== TYPES.empty;
    if (destFilled && srcFilled) continue;
    const a = pixel(fromCell[0], fromCell[1]);
    const b = pixel(toCell[0], toCell[1]);
    world.appendChild(svg("line", {
      x1: a.x,
      y1: a.y,
      x2: b.x,
      y2: b.y,
      stroke: "rgba(255, 138, 48, 0.28)",
      "stroke-width": "3",
      "stroke-linecap": "round",
    }));
  }

  for (const [child, par] of parent) {
    const c = pixelFromIdx(child);
    const p = pixelFromIdx(par);
    world.appendChild(svg("line", {
      x1: p.x,
      y1: p.y,
      x2: c.x,
      y2: c.y,
      stroke: "#ff8a30",
      "stroke-width": "4",
      "stroke-linecap": "round",
      filter: "url(#glow)",
    }));
    world.appendChild(chevron(p.x, p.y, c.x, c.y));
  }

  for (const [x, y] of vertices()) {
    if (isRoot(x, y)) continue;
    const p = pixel(x, y);
    const cell = cells[idx(x, y)];
    const i = idx(x, y);
    const suggested = STARTER.some(([sx, sy]) => sx === x && sy === y);
    const isLive = live.has(i);
    const r = cell.type ? 11 : (suggested ? 8 : 4.5);
    const node = svg("circle", {
      class: "node-hit",
      cx: p.x,
      cy: p.y,
      r: String(r + 10),
      fill: "transparent",
    });
    node.addEventListener("click", () => place(x, y));
    world.appendChild(node);

    let fill = "rgba(80, 70, 96, 0.35)";
    let stroke = "rgba(120, 100, 140, 0.35)";
    if (suggested && !cell.type) {
      fill = "#1a1010";
      stroke = "rgba(255, 138, 48, 0.55)";
    }
    if (cell.type === TYPES.modifier) { fill = "#dfa63d"; stroke = "#ffd27a"; }
    if (cell.type === TYPES.trigger) { fill = "#cf5b3f"; stroke = "#ffb08a"; }
    if (cell.type === TYPES.element) { fill = "#7aa0b8"; stroke = "#c9e4f2"; }
    if (cell.type && isLive) {
      fill = "#ff8a30";
      stroke = "#ffd2a0";
    } else if (cell.type && !isLive) {
      fill = "#4a4054";
      stroke = "#2a2430";
    }

    const dot = svg("circle", {
      cx: p.x,
      cy: p.y,
      r: String(r),
      fill,
      stroke,
      "stroke-width": cell.type || suggested ? "2.5" : "1",
    });
    if (isLive && cell.type) dot.setAttribute("filter", "url(#glow)");
    world.appendChild(dot);

    if (cell.type) {
      const label = svg("text", {
        x: p.x,
        y: p.y + r + 12,
        fill: isLive ? "#f2efe9" : "#828a93",
        "font-size": "9",
        "font-family": "Bahnschrift, Segoe UI, sans-serif",
        "text-anchor": "middle",
        "pointer-events": "none",
      });
      label.textContent = nameOf(cell.type, cell.index);
      world.appendChild(label);
    }
  }

  mesh.appendChild(world);

  const forms = catalog.form || [];
  const rootCell = cells[idx(ROOT.x, ROOT.y)];
  const activeIndex = rootCell.type === TYPES.form ? rootCell.index : 0;
  const nextIndex = forms.length ? (activeIndex + 1) % forms.length : 0;
  const sockets = socketCount(live);
  const rootPx = pixel(ROOT.x, ROOT.y);
  paintDock(docks, L, rootPx.x, rootPx.y, forms[activeIndex] || "Spell", true, sockets, () => {
    tab = "form";
    pick = { type: TYPES.form, index: activeIndex };
    render();
  });
  if (forms.length > 1) {
    paintDock(docks, L, rootPx.x + SCALE * 2.4, rootPx.y + SCALE * 0.35, forms[nextIndex], false, 0, () => {
      pick = { type: TYPES.form, index: nextIndex };
      tab = "form";
      setCell(ROOT.x, ROOT.y, TYPES.form, nextIndex);
      render();
    });
  }

  document.getElementById("summary").textContent = summary(live);
}

function pixelFromIdx(i) {
  return pixel(i % SIZE, (i / SIZE) | 0);
}

function convexHull(points) {
  const pts = points.slice().sort((a, b) => a.x === b.x ? a.y - b.y : a.x - b.x);
  if (pts.length < 3) return pts;
  const cross = (o, a, b) => (a.x - o.x) * (b.y - o.y) - (a.y - o.y) * (b.x - o.x);
  const lower = [];
  for (const p of pts) {
    while (lower.length >= 2 && cross(lower[lower.length - 2], lower[lower.length - 1], p) <= 0) lower.pop();
    lower.push(p);
  }
  const upper = [];
  for (let i = pts.length - 1; i >= 0; i--) {
    const p = pts[i];
    while (upper.length >= 2 && cross(upper[upper.length - 2], upper[upper.length - 1], p) <= 0) upper.pop();
    upper.push(p);
  }
  lower.pop();
  upper.pop();
  return lower.concat(upper);
}

function paintDock(host, L, px, py, label, on, sockets, onClick) {
  const dock = document.createElement("button");
  dock.type = "button";
  dock.className = "dock" + (on ? " is-on" : "");
  dock.style.left = `${((px + L.ox) / L.w) * 100}%`;
  dock.style.top = `${((py + L.oy) / L.h) * 100}%`;
  if (on) {
    const prompt = document.createElement("div");
    prompt.className = "dock-prompt";
    const kbd = document.createElement("kbd");
    kbd.textContent = "E";
    const swap = document.createElement("span");
    swap.textContent = "Swap";
    prompt.append(kbd, swap);
    dock.appendChild(prompt);
  }
  const hex = document.createElement("div");
  hex.className = "dock-hex";
  hex.textContent = label || "";
  dock.appendChild(hex);
  const row = document.createElement("div");
  row.className = "dock-sockets";
  const n = on ? 4 : 5;
  for (let i = 0; i < n; i++) {
    const pip = document.createElement("span");
    if (on && i < Math.min(4, sockets)) pip.className = "is-lit";
    row.appendChild(pip);
  }
  dock.appendChild(row);
  dock.addEventListener("click", onClick);
  host.appendChild(dock);
}

function render() {
  renderTabs();
  renderPalette();
  renderBoard();
}

document.getElementById("clear").addEventListener("click", () => {
  const keep = cells[idx(ROOT.x, ROOT.y)];
  for (let y = 0; y < SIZE; y++) {
    for (let x = 0; x < SIZE; x++) {
      if (isRoot(x, y)) continue;
      if (!onBoard(x, y)) continue;
      setCell(x, y, 0, -1);
    }
  }
  if (keep.type !== TYPES.form) setCell(ROOT.x, ROOT.y, TYPES.form, 0);
  osfui.action("clearRings");
  render();
});

document.addEventListener("keydown", (ev) => {
  if (ev.key === "e" || ev.key === "E") {
    ev.preventDefault();
    cycleSpell(1);
  }
});

async function loadCatalog() {
  try {
    const res = await fetch("catalog.json");
    if (res.ok) catalog = await res.json();
  } catch (_) { /* preview without catalog still paints the board */ }
  if (!(catalog.form && catalog.form.length)) {
    catalog = {
      form: ["Gravlance", "Emberlance", "Rimeshard"],
      modifier: ["Amplify", "Orbiting", "Lossy"],
      trigger: ["OnImpact", "Echoing", "OnSpawn"],
      element: ["Fire", "Frost", "Shock"],
    };
  }
}

osfui.applyAccent(document.documentElement, "#7B5CFF");

function hydrateCells(values) {
  if (!Array.isArray(values) || values.length < SIZE * SIZE) return;
  hydrating = true;
  for (let i = 0; i < SIZE * SIZE; i++) {
    const parts = String(values[i] || "0,-1").split(",");
    const type = Number(parts[0]) || 0;
    const index = parts.length > 1 ? Number(parts[1]) : -1;
    cells[i] = { type, index: Number.isFinite(index) ? index : -1 };
  }
  const root = cells[idx(ROOT.x, ROOT.y)];
  if (root.type === TYPES.form && root.index >= 0) {
    pick = { type: TYPES.form, index: root.index };
    tab = "form";
  }
  hydrating = false;
  render();
}

osfui.data.on("gridCells", hydrateCells);

loadCatalog().then(() => {
  if (!osfui.available()) {
    setCell(ROOT.x, ROOT.y, TYPES.form, 0);
    pick = { type: TYPES.form, index: 0 };
    render();
    return;
  }
  render();
  osfui.ready.then(() => {
    osfui.action("refresh");
    osfui.viewReady();
  });
});

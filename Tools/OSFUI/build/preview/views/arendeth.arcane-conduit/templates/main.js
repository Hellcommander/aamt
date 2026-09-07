"use strict";

const SAMPLE = [
  { id: "chaos_spray", source: "mod", name: "Chaos Spray", author: "ArcaneConduit", description: "Cone of tiny physics chaos balls.", caps: "0 cap · 8 essence · 0.00 instab · 0 trig cap · 8 dur · 8 arcane", fusion: false, fusionLine: "", autoLoadLine: "auto: city · settlement · Kinetics" },
  { id: "razorstorm", source: "mod", name: "Razorstorm", author: "ArcaneConduit", description: "Saw disc starter.", caps: "0 cap · 12 essence · 0.00 instab · 0 trig cap · 12 dur · 12 arcane", fusion: false, fusionLine: "" },
  { id: "angelic_pair", source: "mod", name: "Angelic Pair", author: "ArcaneConduit", description: "Seraph hunt-wheel on Grid A, cherub controller on Grid B.", caps: "0 cap · 40 essence · fuse pair", fusion: true, fusionLine: "Seraphim fused into Cherubim" },
  { id: "ember_amplify", source: "mod", name: "Ember Amplify", author: "ArcaneConduit", description: "Fire with an amplify socket.", caps: "2 cap · 16 essence · 0.00 instab · 0 trig cap · 16 dur · 16 arcane", fusion: false, fusionLine: "" },
  { id: "suggest_affinity", source: "suggested", name: "Fire affinity", author: "suggestion", description: "Most of your sockets are Fire. This hangs that school's cheapest form on the live bank.", caps: "0 cap · 8 essence · 0.00 instab · 0 trig cap · 8 dur · 8 arcane", fusion: false, fusionLine: "" },
];

let tab = "mod";
let templates = SAMPLE.slice();
let banks = ["Empty", "Empty", "Empty", "Empty", "Empty", "Empty", "Empty", "Empty"];
let activeBank = 0;
let storedBank = 1;
let selected = null;
let pendingDelete = false;
let renaming = false;
let status = "";
let warnings = "";
let importFolder = "";
let exportFolder = "";
let sharePath = "";
let hotkeys = [
  { label: "F2", id: "chaos_spray", source: "mod", name: "Chaos Spray" },
  { label: "F3", id: "razorstorm", source: "mod", name: "Razorstorm" },
  { label: "F4", id: "seraphim", source: "mod", name: "Seraphim" },
  { label: "F6", id: "ember_amplify", source: "mod", name: "Ember Amplify" },
];
let favorites = Array.from({ length: 8 }, (_, i) => ({
  live: i,
  stored: -1,
  liveName: i === 0 ? "Chaos Spray" : "Empty",
  storedName: "last live",
}));

function parseHotkey(row) {
  const parts = String(row || "").split(";;");
  return {
    label: parts[0] || "unbound",
    id: parts[1] || "",
    source: parts[2] || "mod",
    name: parts[3] || "",
  };
}

function renderHotkeys() {
  const box = document.getElementById("hotkeys");
  box.textContent = "";
  hotkeys.forEach((slot, i) => {
    const b = document.createElement("button");
    b.type = "button";
    if (slot.id) b.classList.add("is-bound");
    if (selected && slot.id === selected.id && slot.source === selected.source) b.classList.add("is-on");
    b.appendChild(document.createTextNode(slot.label || "unbound"));
    const sub = document.createElement("small");
    if (slot.id) {
      sub.textContent = slot.name || slot.id;
    } else if (selected && selected.source !== "suggested") {
      sub.textContent = "Bind " + (selected.name || selected.id);
    } else if (selected) {
      sub.textContent = "Keep first";
    } else {
      sub.textContent = "Empty";
    }
    b.appendChild(sub);
    b.title = slot.id
      ? "Click to replace with the selected template, or clear if it is already bound."
      : "Bind the selected template to this key.";
    b.addEventListener("click", () => {
      if (!selected || selected.source === "suggested") return;
      if (slot.id === selected.id && slot.source === selected.source) {
        osfui.action("clearHotkey", i);
        return;
      }
      osfui.action("bindHotkey", i, selected.id, selected.source);
    });
    box.appendChild(b);
  });
}

function parseFavorite(row) {
  const parts = String(row || "").split(";;");
  const live = Number(parts[0]);
  const stored = Number(parts[1]);
  return {
    live: Number.isFinite(live) ? live : -1,
    stored: Number.isFinite(stored) ? stored : -1,
    liveName: parts[2] || "",
    storedName: parts[3] || "last live",
  };
}

function favoriteIsDefault(slot, i) {
  return slot.live === i && slot.stored < 0;
}

function renderFavorites() {
  const box = document.getElementById("favorites");
  if (!box) return;
  box.textContent = "";
  favorites.forEach((slot, i) => {
    const b = document.createElement("button");
    b.type = "button";
    const mapped = !favoriteIsDefault(slot, i);
    if (mapped) b.classList.add("is-bound");
    if (slot.live === activeBank && (slot.stored < 0 || slot.stored === storedBank)) {
      b.classList.add("is-on");
    }
    b.appendChild(document.createTextNode(String(i + 1)));
    const sub = document.createElement("small");
    const aName = slot.liveName || ("Bank " + (slot.live + 1));
    const bName = slot.stored < 0 ? "last live" : (slot.storedName || ("Bank " + (slot.stored + 1)));
    sub.textContent = aName + " + " + bName;
    b.appendChild(sub);
    b.title = mapped
      ? "Click to reset this slot to bank " + (i + 1) + " + last live."
      : "Bind the current live bank (A) and delivery bank (B) to key " + (i + 1) + ".";
    b.addEventListener("click", () => {
      if (mapped && slot.live === activeBank && (slot.stored < 0 || slot.stored === storedBank)) {
        osfui.action("clearFavorite", i);
        return;
      }
      osfui.action("bindFavorite", i);
    });
    box.appendChild(b);
  });
}

function parseRow(row) {
  const parts = String(row || "").split(";;");
  return {
    id: parts[0] || "",
    source: parts[1] || "",
    name: parts[2] || parts[0] || "",
    author: parts[3] || "",
    description: parts[4] || "",
    caps: parts[5] || "",
    fusion: parts[6] === "1",
    fusionLine: parts[7] || "",
    autoLoadLine: parts[8] || "",
  };
}

function listForTab() {
  return templates.filter((t) => t.source === tab);
}

function selectById(id, source) {
  selected = templates.find((t) => t.id === id && t.source === source) || null;
  pendingDelete = false;
  renaming = false;
  render();
}

function renderTabs() {
  const tabs = document.getElementById("tabs");
  tabs.textContent = "";
  for (const t of [
    { id: "mod", label: "Mod" },
    { id: "personal", label: "Personal" },
    { id: "suggested", label: "Suggested" },
  ]) {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "osf-segment" + (tab === t.id ? " is-on" : "");
    b.textContent = t.label;
    b.addEventListener("click", () => {
      tab = t.id;
      const rows = listForTab();
      selected = rows[0] || null;
      pendingDelete = false;
      renaming = false;
      render();
    });
    tabs.appendChild(b);
  }
}

function renderList() {
  const box = document.getElementById("list");
  const empty = document.getElementById("empty");
  box.textContent = "";
  const rows = listForTab();
  empty.textContent = tab === "suggested"
    ? "No suggestions yet. Socket forms on the live banks, then Refresh."
    : "No templates in this list yet.";
  empty.classList.toggle("hidden", rows.length > 0);
  rows.forEach((t) => {
    const b = document.createElement("button");
    b.type = "button";
    if (selected && selected.id === t.id && selected.source === t.source) b.classList.add("is-on");
    b.appendChild(document.createTextNode(t.name || t.id));
    if (t.fusion) {
      const badge = document.createElement("span");
      badge.className = "fuse-badge";
      badge.textContent = "Fuse";
      b.appendChild(badge);
    }
    const sub = document.createElement("small");
    sub.textContent = t.author || t.id;
    b.appendChild(sub);
    b.addEventListener("click", () => selectById(t.id, t.source));
    box.appendChild(b);
  });
}

function renderDetail() {
  const name = document.getElementById("sel-name");
  const meta = document.getElementById("sel-meta");
  const desc = document.getElementById("sel-desc");
  const fusion = document.getElementById("sel-fusion");
  const autoload = document.getElementById("sel-autoload");
  const actions = document.getElementById("sel-actions");
  const warn = document.getElementById("warn");
  const renameForm = document.getElementById("rename-form");
  actions.textContent = "";
  renameForm.classList.toggle("hidden", !(selected && selected.source === "personal" && renaming));

  if (!selected) {
    name.textContent = "Nothing selected";
    meta.textContent = "";
    desc.textContent = tab === "personal"
      ? "Save the live grids to create a personal template."
      : tab === "suggested"
        ? "Suggestions are built from the live banks: school affinity, favorite triggers, leftover capacity, and instability. They are not files until you Keep one."
        : "Mod templates appear when the plugin copies them next to MadScience.dll.";
    if (fusion) {
      fusion.textContent = "";
      fusion.classList.add("hidden");
    }
    if (autoload) {
      autoload.textContent = "";
      autoload.classList.add("hidden");
    }
  } else {
    name.textContent = selected.name || selected.id;
    meta.textContent = [selected.source, selected.author, selected.id, selected.fusion ? "fuse pair" : "", selected.caps].filter(Boolean).join(" · ");
    desc.textContent = selected.description || "No description.";
    if (fusion) {
      fusion.textContent = selected.fusion && selected.fusionLine ? selected.fusionLine : "";
      fusion.classList.toggle("hidden", !(selected.fusion && selected.fusionLine));
    }
    if (autoload) {
      autoload.textContent = selected.autoLoadLine || "";
      autoload.classList.toggle("hidden", !selected.autoLoadLine);
    }

    const apply = document.createElement("button");
    apply.type = "button";
    apply.className = "osf-btn";
    apply.textContent = "Apply";
    apply.addEventListener("click", () => osfui.action("apply", selected.id, selected.source));
    actions.appendChild(apply);

    if (selected.source === "suggested") {
      const keep = document.createElement("button");
      keep.type = "button";
      keep.className = "osf-btn osf-btn--ghost";
      keep.textContent = "Keep as personal";
      keep.addEventListener("click", () => osfui.action("keepSuggested", selected.id));
      actions.appendChild(keep);
    }

    if (selected.source === "personal") {
      const rename = document.createElement("button");
      rename.type = "button";
      rename.className = "osf-btn osf-btn--ghost";
      rename.textContent = renaming ? "Cancel rename" : "Rename";
      rename.addEventListener("click", () => {
        renaming = !renaming;
        pendingDelete = false;
        render();
        if (renaming) {
          const input = document.getElementById("rename-name");
          input.value = selected.name || selected.id;
          input.focus();
        }
      });
      actions.appendChild(rename);

      const del = document.createElement("button");
      del.type = "button";
      del.className = "osf-btn osf-btn--ghost";
      del.textContent = pendingDelete ? "Confirm delete" : "Delete";
      del.addEventListener("click", () => {
        if (!pendingDelete) {
          pendingDelete = true;
          render();
          return;
        }
        osfui.action("delete", selected.name || selected.id);
        pendingDelete = false;
      });
      actions.appendChild(del);
    }

    const share = document.createElement("button");
    share.type = "button";
    share.className = "osf-btn osf-btn--ghost";
    share.textContent = "Export JSON";
    share.addEventListener("click", () => osfui.action("export", selected.id));
    if (selected.source === "personal") actions.appendChild(share);
  }

  if (warnings) {
    warn.className = "osf-note osf-note--warn";
    warn.textContent = warnings;
  } else if (status && status !== "ok") {
    warn.className = "osf-note osf-note--danger";
    warn.textContent = status;
  } else {
    warn.className = "osf-note hidden";
    warn.textContent = "";
  }
}

function renderBanks() {
  const ol = document.getElementById("banks");
  ol.textContent = "";
  banks.forEach((line, i) => {
    const li = document.createElement("li");
    if (i === activeBank) li.classList.add("is-on");
    else if (i === storedBank) li.classList.add("is-stored");

    const label = document.createElement("span");
    label.className = "bank-line";
    label.textContent = line || "(empty)";
    label.title = "Make this Grid A (live / element)";
    label.addEventListener("click", () => osfui.action("setBank", i));
    li.appendChild(label);

    const asB = document.createElement("button");
    asB.type = "button";
    asB.className = "as-b";
    asB.textContent = "B";
    asB.title = "Make this Grid B (stored / delivery)";
    asB.disabled = i === activeBank;
    asB.addEventListener("click", (ev) => {
      ev.stopPropagation();
      osfui.action("setStored", i);
    });
    li.appendChild(asB);

    ol.appendChild(li);
  });
}

function renderShareHint() {
  const hint = document.getElementById("share-hint");
  if (!hint) return;
  if (sharePath) {
    hint.textContent = "Last copy: " + sharePath;
  } else if (importFolder) {
    hint.textContent = "Drop JSON in " + importFolder + " then Import dropped. Export writes to " + (exportFolder || "the Export folder") + ".";
  }
}

function render() {
  renderTabs();
  renderList();
  renderDetail();
  renderHotkeys();
  renderFavorites();
  renderBanks();
  renderShareHint();
}

function ingestTemplates(values) {
  if (!Array.isArray(values)) return;
  const parsed = values.map(parseRow).filter((t) => t.id);
  if (parsed.length || osfui.available()) templates = parsed;
  if (selected) {
    selected = templates.find((t) => t.id === selected.id && t.source === selected.source) || selected;
  } else {
    selected = listForTab()[0] || null;
  }
  render();
}

document.getElementById("rename-form").addEventListener("submit", (ev) => {
  ev.preventDefault();
  if (!selected || selected.source !== "personal") return;
  const next = document.getElementById("rename-name").value.trim();
  if (!next) return;
  osfui.action("rename", selected.name || selected.id, next);
  renaming = false;
});

document.getElementById("save-form").addEventListener("submit", (ev) => {
  ev.preventDefault();
  const name = document.getElementById("save-name").value.trim();
  const description = document.getElementById("save-desc").value.trim();
  if (!name) {
    document.getElementById("save-name").focus();
    return;
  }
  osfui.action("save", name, description, document.getElementById("save-fusion").checked ? "fusion" : "");
});

document.getElementById("reload").addEventListener("click", () => osfui.action("reload"));
document.getElementById("import").addEventListener("click", () => osfui.action("importDropped"));
document.getElementById("open-import").addEventListener("click", () => osfui.action("openFolder", 2));
document.getElementById("open-export").addEventListener("click", () => osfui.action("openFolder", 1));

osfui.applyAccent(document.documentElement, "#7B5CFF");
osfui.data.on("templates", ingestTemplates);
osfui.data.on("banks", (value) => {
  if (Array.isArray(value) && value.length) banks = value.map((v) => String(v));
  render();
});
osfui.data.on("activeBank", (value) => {
  const n = Number(value);
  if (Number.isFinite(n)) activeBank = n;
  render();
});
osfui.data.on("storedBank", (value) => {
  const n = Number(value);
  if (Number.isFinite(n)) storedBank = n;
  render();
});
osfui.data.on("status", (value) => {
  status = value == null ? "" : String(value);
  render();
});
osfui.data.on("warnings", (value) => {
  warnings = value == null ? "" : String(value);
  render();
});
osfui.data.on("hotkeys", (values) => {
  if (!Array.isArray(values)) return;
  const parsed = values.map(parseHotkey);
  if (parsed.length) hotkeys = parsed;
  render();
});
osfui.data.on("favorites", (values) => {
  if (!Array.isArray(values)) return;
  const parsed = values.map(parseFavorite);
  if (parsed.length) favorites = parsed;
  render();
});
osfui.data.on("importFolder", (value) => {
  importFolder = value == null ? "" : String(value);
  render();
});
osfui.data.on("exportFolder", (value) => {
  exportFolder = value == null ? "" : String(value);
  render();
});
osfui.data.on("sharePath", (value) => {
  sharePath = value == null ? "" : String(value);
  render();
});

if (!osfui.available()) {
  document.body.classList.add("is-standalone");
  selected = templates[0];
  banks = ["Chaos Spray", "Empty", "Empty", "Empty", "Empty", "Empty", "Empty", "Empty"];
  render();
} else {
  render();
  osfui.ready.then(() => {
    osfui.action("refresh");
    osfui.viewReady();
  });
}

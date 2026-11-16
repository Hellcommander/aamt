---
name: docs-canvas
description: >-
  Render a documentation-style canvas that organizes architecture
  notes, API references, walkthroughs, and how-tos into a navigable layout
  with sections, tables of contents, and cross-references. Use when the
  user asks for a docs canvas, documentation overview, architecture
  walkthrough, API reference page, or wants to render structured
  documentation as an interactive canvas.
---

# Docs Canvas

Build a canvas that presents documentation — architecture notes, API references, design docs, runbooks, or codebase walkthroughs — as an interactive, navigable surface rather than as a flat markdown file.

## Host

Cursor's canvas runtime is not a VSIX CortexIDE can import. In CortexIDE, Local Agent Bridge transpiles `.canvas.tsx` and renders it with a local `cursor/canvas` runtime (custom editor `localAgentBridge.canvasPreview`).

- Write one `.canvas.tsx` file. Default-export the page component.
- Import **only** `cursor/canvas`. No relative imports, no npm packages, no `fetch`.
- Embed data inline. Omit empty sections. No placeholder copy.
- Prefer built-in primitives over raw HTML. Flat design: no gradients, no box-shadows, no emoji chrome. Colors from `useHostTheme()` tokens.

Read `~/.cursor/skills-cursor/canvas/SKILL.md` for generation policy, slop rules, and the Pre-delivery self-check. Exact SDK exports live in `~/.cursor/skills-cursor/canvas/sdk/index.d.ts`.

## Stay on the public SDK

Use only exports listed in `~/.cursor/skills-cursor/canvas/sdk/index.d.ts`, so the canvas opens in Cursor and in CortexIDE alike. The CortexIDE runtime still renders the old extras (`DocsShell`, `TableOfContents`, `DocSection`, `CodeBlock`, `References`) for canvases written earlier, but Cursor's SDK has none of them, and a canvas that imports them fails to compile there.

For docs layout, define small helpers inside the canvas file:

- **Section:** a `<section id>` wrapping `H2` + `Stack`, so `#id` jump links work.
- **Table of contents:** a `Row` of `<a href="#id">` links coloured with `useHostTheme().accent.primary`.
- **Code:** a `Card` with `CardHeader` (title) and `CardBody` holding a `<pre>` (monospace, `theme.text.primary`).
- **References:** `Link` + `Text tone="secondary"` rows.

## Gather the source material

Accept any of: a directory of markdown files, a single doc URL, an inline outline, or a question to answer from the codebase. Collect headings, code blocks, diagrams, and any cross-references between documents. Cite real paths with `Link` so CortexIDE can `openFile`.

## Plan the canvas layout

Decide the top-level structure before writing components:

1. **Overview** — purpose, scope, audience (one card or a short lead paragraph).
2. **Table of contents** — jump list of the section ids.
3. **Body sections** — one section per logical unit. Mix prose, `Table`, `Callout`, code cards, charts, DAG layout.
4. **References** — related docs, source files, RFCs.

Do not wrap every section in the same `Card`. Mix open sections with cards.

## Render with canvas primitives

Prefer `cursor/canvas` components:

- `H1` / `H2` / `H3` / `Text` / `Code` / `Link` for prose
- `Table` for API parameter lists and option matrices
- `Callout` for Important / Warning / Note (tones `info` / `warning` / `danger` / `success`)
- `BarChart` / `LineChart` / `PieChart` when the doc has real numbers
- `computeDAGLayout` for architecture graphs
- `DiffView` + `DiffStats` for before/after patches

## Tone

Write reader-facing prose. Lead with the answer, then explain. Keep examples small. Never invent type names — quote what you grepped or read.

## File location

Write the canvas only to `~/.cursor/projects/<workspace-slug>/canvases/<name>.canvas.tsx` (the CortexIDE agent's prompt names this folder). Cursor and CortexIDE both read it there; a second copy elsewhere drifts. To show it in another workspace, use Local Agent Bridge: Link Canvas to This Workspace. Link the absolute path in chat.

## Self-check

Same as the canvas skill: hierarchy, composition variety, no slop. Confirm jump-link ids match the section ids. Confirm every chart/table has a specific title and source.

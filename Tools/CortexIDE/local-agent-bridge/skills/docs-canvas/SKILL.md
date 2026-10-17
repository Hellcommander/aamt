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

## CortexIDE extras

These are exported from the same `cursor/canvas` import on CortexIDE. They are **not** in Cursor's published SDK. If the canvas must also open in Cursor, compose the same layout with `Stack` / `Row` / `Card` / `H1`–`H3` / `Link` instead.

```ts
import {
  DocsShell,
  TableOfContents,
  DocSection,
  CodeBlock,
  References,
} from "cursor/canvas";
```

| Export | Role |
| --- | --- |
| `DocsShell` | Page chrome: sticky TOC column, title, subtitle, overview card, body, optional references. |
| `TableOfContents` | Standalone jump list if you are not using `DocsShell`. |
| `DocSection` | `id` + `H2` heading so TOC anchors work. |
| `CodeBlock` | Fenced snippet with optional `language` / `title`. |
| `References` | File and URL list (`{ label, href, note? }`). |

`DocsShell` props:

- `title?: string`
- `subtitle?: string`
- `overview?: ReactNode`
- `toc?: { id: string; label: string; level?: number }[]`
- `children?: ReactNode`
- `references?: { label: string; href: string; note?: string }[]`

`DocSection` props: `id: string`, `title: string`, `children`.

`CodeBlock` props: `language?: string`, `title?: string`, `children` (plain source text).

## Gather the source material

Accept any of: a directory of markdown files, a single doc URL, an inline outline, or a question to answer from the codebase. Collect headings, code blocks, diagrams, and any cross-references between documents. Cite real paths with `Link` so CortexIDE can `openFile`.

## Plan the canvas layout

Decide the top-level structure before writing components:

1. **Overview** — purpose, scope, audience (one card or `DocsShell` `overview`).
2. **Table of contents** — sticky jump list (`DocsShell` `toc` or `TableOfContents`).
3. **Body sections** — one `DocSection` per logical unit. Mix prose, `Table`, `Callout`, `CodeBlock`, charts, DAG layout.
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

Write the canvas to `~/.cursor/projects/<workspace-slug>/canvases/<name>.canvas.tsx` and, for CortexIDE, also to the workspace `canvases/` folder. Link the absolute path in chat.

## Self-check

Same as the canvas skill: hierarchy, composition variety, no slop. Confirm TOC ids match `DocSection` ids. Confirm every chart/table has a specific title and source.

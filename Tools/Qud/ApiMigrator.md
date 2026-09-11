# Caves of Qud — Mod tooling

Install location: `D:\games\Ai assisted toolkit\Tools\Qud`

This folder holds the obsolete-API migrator and related scanners for local `Mods`
(`%USERPROFILE%\AppData\LocalLow\Freehold Games\CavesOfQud\Mods`) and optionally
Steam Workshop content. It no longer needs to live next to the game's LocalLow folder;
set `COQ_TOOLS_ROOT` / `COQ_MODS_ROOT` only if autodetection is wrong.

A thin redirect remains at `CavesOfQud\_tools` so old `Launch-Gui.bat` / PS1 paths still work (that `Launch-Gui.bat` opens ApiMigrator directly). In this folder, use `Launch-ApiMigrator.bat`; `Launch-Gui.bat` is the toolkit GUI menu.

## Chargen XML validator (`Validate-ChargenXml.ps1`)

Scans **PopulationTables**, **Genotypes**, and **Subtypes** XML for New-Game / chargen
breakers: duplicate population groups, self-referential / cyclic `<table>` refs, missing
`Gear` → population tables, genotype `Subtypes` → class IDs, unknown blueprints, `Load=Replace`
on base populations, missing `Encoding="utf-8"`, unused class `DisplayName` (should be
`ChargenTitle`), and related hygiene.

Dry-run by default. Indexes Base + StreamingAssets DLC (read-only) plus every scanned mod.

```powershell
cd "D:\games\Ai assisted toolkit\Tools\Qud"

# Local Mods
.\Validate-ChargenXml.ps1 -Report .\reports\chargen.md

# Local + Workshop
.\Validate-ChargenXml.ps1 -IncludeWorkshop -Report .\reports\chargen.md

# One mod, apply safe fixes (Encoding, self-ref table removal, dup group rename,
# class DisplayName→ChargenTitle). Writes .bak unless -NoBackup.
.\Validate-ChargenXml.ps1 -Mod "Proliferate*" -Apply -Report .\reports\chargen_fix.md
```

Exit code `1` if any **Error**-severity findings remain. Does not launch the game.

---

## CP437 → UTF-16 converter (`Convert-Cp437.ps1`)

After the game switched internal strings to UTF-16, legacy CP437 code points in `.cs` / `.xml`
(e.g. `\x03` for ♥, `\x1A` for →, Latin-1 lookalikes that meant box-drawing) must be converted
to real Unicode. This tool applies the same map as `ConsoleLib.Console.CP437.FromCP437`
(plus `\u000d` → ♪). For named symbols by hand, prefer `XRL.Language.TextConstants` /
`TextConstants.xml`.

Dry-run by default. Always sets `Encoding="utf-8"` on scanned XML roots when encoding
ensure is on (default) — even if no CP437 glyphs were converted — so the game stops
defaulting to CP437 / "Found CP437 Characters". Use `-NoXmlEncoding` to skip.

```powershell
cd "D:\games\Ai assisted toolkit\Tools\Qud"

# Local Mods dry-run
.\Convert-Cp437.ps1 -Report .\reports\cp437.md

# Local + Workshop, one mod, apply
.\Convert-Cp437.ps1 -IncludeWorkshop -Mod "Gigantism" -Apply -NoBackup -Report .\reports\cp437_apply.md

# Also convert ambiguous \t \a \b \v \f string escapes (○ • ◘ ♂ ♀)
.\Convert-Cp437.ps1 -ConvertAmbiguous -Apply
```

CLI equivalent:

```powershell
dotnet run --project ".\src\ApiMigrator.Cli" -c Release -- convert-cp437 --include-workshop --apply
```

Named escapes `\t`/`\a`/`\b`/`\v`/`\f` are **flagged for review** unless `-ConvertAmbiguous`
(they often mean real tabs / bells). Explicit `\x09` / `\u0009` forms are always converted.

---

# Obsolete API Migrator

Finds and fixes obsolete Caves of Qud modding APIs across your `Mods` folder (and, optionally,
your Steam Workshop content), backed by a JSON dump of every `[Obsolete]` member the game's
`Assembly-CSharp.dll` currently reports.

There are three ways to use it:

| Tool | Where | Use it for |
|---|---|---|
| **GUI** (`ApiMigratorGui`) | `src\ApiMigratorGui` | Everyday use — pick folders, dry-run/apply, browse the obsolete-API map, refresh the dump from the game |
| **CLI** (`ApiMigrator.Cli`) | `src\ApiMigrator.Cli` | Scripting / no-UI refresh-dump and migrate, cross-checked against the GUI's engine |
| **PowerShell script** (`Update-ObsoleteApis.ps1`) | this folder | Original zero-build CLI; same rules/dump JSON, no `dotnet` project needed |

CLI and PowerShell each load `ApiMigrator.Core.dll` as an **isolated instance** (shadow copy / in-memory bytes) so a second migrator, GUI rebuild, or `dotnet run` does not fail just because another process already has the shared `bin\Release` DLL open. Set `COQ_APIMIGRATOR_NO_ISOLATE=1` to force in-place CLI load when debugging.

All three read the exact same two data files, so they never disagree with each other:

- **Dump (source of truth for what's obsolete):** `data\obsolete_api_dump.json`
- **Curated auto-fix rules:** `data\curated_rewrite_rules.json`

### Per-game-version profiles (`data/by-version/`)

Steam betas (e.g. `lang-experimental` vs `public`) ship different obsolete surfaces. ApiMigrator
keeps a **profile per Managed `FileVersion`** that includes the dump, curated rules, and rule
charts:

```
data\by-version\
  index.json
  2.0.211.51\
    obsolete_api_dump.json
    curated_rewrite_rules.json
    charts\
    meta.json
  2.0.212.29\
    …
```

On migrate / refresh-dump / resolve-cs0618 / GUI launch / `Update-ObsoleteApis.ps1`, the tool
reads `Assembly-CSharp.dll` FileVersion (+ Steam `BetaKey` when available) and **switches** the
active dump+rules (+ charts when present) to that profile when it exists (after snapshotting the
previous active pair). `refresh-dump --save` and `sync-version --save-profile` write/update the
live version folder.

To use a **different** profile than the installed game (e.g. share the tool and migrate against
public while Steam is on `lang-experimental`), pin it. Migrate / GUI / PS1 honor the pin until
you clear it. Do not include `data\by-version\active-override.json` when sharing — recipients
should pick their own profile.

```powershell
# bat (double-click lists profiles; then pass public / lang / live)
.\Switch-Api.bat public
.\Switch-Api.bat lang
.\Switch-Api.bat live

dotnet run --project "D:\games\Ai assisted toolkit\Tools\Qud\src\ApiMigrator.Cli" -c Release -- switch-api --list
dotnet run --project "D:\games\Ai assisted toolkit\Tools\Qud\src\ApiMigrator.Cli" -c Release -- switch-api public
dotnet run --project "D:\games\Ai assisted toolkit\Tools\Qud\src\ApiMigrator.Cli" -c Release -- switch-api live
dotnet run --project "D:\games\Ai assisted toolkit\Tools\Qud\src\ApiMigrator.Cli" -c Release -- sync-version
dotnet run --project "D:\games\Ai assisted toolkit\Tools\Qud\src\ApiMigrator.Cli" -c Release -- sync-version --save-profile
```

GUI: the bar under the title (`API dump profile` + **Switch**) is the same pin.

### Rule charts (`data/charts/`) — edit these to keep autofixes up to date

Friendly **XML** (primary) / **JSON** packs that compile into `curated_rewrite_rules.json`.
See [`data/charts/README.md`](data/charts/README.md) for the schema and field cheat sheet.

```powershell
dotnet run --project "D:\games\Ai assisted toolkit\Tools\Qud\src\ApiMigrator.Cli" -c Release -- export-charts --force   # JSON → XML packs
dotnet run --project "D:\games\Ai assisted toolkit\Tools\Qud\src\ApiMigrator.Cli" -c Release -- compile-rules           # charts → JSON
dotnet run --project "D:\games\Ai assisted toolkit\Tools\Qud\src\ApiMigrator.Cli" -c Release -- compile-rules --check   # exit 2 if stale

# needsManual → curated autofix (promotion sheets):
dotnet run --project "D:\games\Ai assisted toolkit\Tools\Qud\src\ApiMigrator.Cli" -c Release -- export-promotions
dotnet run --project "D:\games\Ai assisted toolkit\Tools\Qud\src\ApiMigrator.Cli" -c Release -- apply-promotions
```

GUI: Obsolete Map → **Export / Compile rule charts**, **Export / Apply promotions**.
The dump was originally captured from the *"Dump obsolete API replacements via ApiDump"* agent
run (see `_meta.source` inside the JSON for the full provenance) and has since been kept as the
default, hand-curated map. You can refresh it straight from the live game DLLs at any time (see
**DLL Research** below) — refreshing *merges* into this file rather than replacing it, so your
curated entries are never lost.

## Launching the GUI

The easiest way in:

```
Launch-ApiMigrator.bat
```

The bar under the title pins which **API dump profile** migrate uses (`public` vs `lang-experimental`
vs follow Steam). Same pin as `Switch-Api.bat` / `switch-api`.

Double-click it, or run it from a terminal. It just does `dotnet run -c Release -r win-x64`
inside `src\ApiMigratorGui`. First launch will restore/build the project (a few seconds);
subsequent launches are fast.

Equivalent manual command:

```powershell
cd "D:\games\Ai assisted toolkit\Tools\Qud\src\ApiMigratorGui"
dotnet run -c Release -r win-x64
```

Requires the .NET 8 SDK (or newer) — already present on this machine (`dotnet --list-sdks`).
All ApiMigrator app hosts (CLI, GUI, tests) are built for **x64** only (`PlatformTarget=x64`,
`RuntimeIdentifier=win-x64`) — not AnyCPU.

### GUI tabs

- **Migrate** — dual-path scan roots, pre-filled and editable:
  - **Local Mods** (default: `…\CavesOfQud\Mods`)
  - **Include Workshop** checkbox (same as PS1 `-IncludeWorkshop` / CLI `--include-workshop`) with an
    editable Workshop path (discovered via Steam registry + `libraryfolders.vdf`; newest live CoQ install)
  - Optional additional folders via **+ Browse...**
  One **Run Migration** covers every enabled root. Toggle **Apply** (off = dry run) and **.bak backups**.
  **Apply safe autofixes (Local + Workshop)** confirms, then applies curated safe autofixes only
  (equivalent to PS1 `-IncludeWorkshop -Apply -NoBackup`) and writes `reports\all-mods-gui-apply.md`.
  Results show per-file auto-fix counts and remaining manual-review hits; **Save Report As...** writes
  the same Markdown report the CLI produces. Folder pickers never auto-compile or scan.
- **Obsolete Map** — searchable table of every entry in the dump: type, member, whether it's
  auto-fixable, the game's obsolete message, and any curation notes.
- **DLL Research** — point at the game's `Managed` folder (pre-filled with the default Steam
  install path) and **1. Scan Managed**. This reflects `Assembly-CSharp.dll` (read-only — nothing under
  `Managed` is ever written to) and shows a diff against the current dump: what's new, what
  changed, what's no longer reported. Then **2. Update ApiMigrator (save dump)** writes
  `obsolete_api_dump.json` (previous dump backed up under `data\backups\`) — that file is
  what Migrate / CS0618 Resolve / Obsolete Map read. Optionally also writes a markdown research
  report under `reports\`. New dump entries stay `needsManual` until promoted into
  `curated_rewrite_rules.json` autofixes.
- **CS0618 Resolve** — compile a mod against Managed (or paste a warning log) and run curated
  auto-fixes without launching the game.
- **Ollama leftovers** — after Migrate, send leftover DidX / GameText hits to Ollama
  for C# rewrites (not advice). Default is local (`http://localhost:11434`). Optional
  **Use Ollama Cloud** talks to `https://ollama.com` with `OLLAMA_API_KEY` (or a GUI key;
  create one at ollama.com/settings/keys). Free-tier leftover default is `gpt-oss:20b` (fast
  code/JSON). Also: `gpt-oss:120b` (frontier quality), `gemma4:31b` (vision+audio+text, 256K),
  `nemotron-3-nano:30b` / `nemotron-3-super` / `nemotron-3-ultra` (agentic, 1M context).
  Direct cloud uses those names; local `*-cloud` tags (`ollama signin` + `ollama pull gpt-oss:20b-cloud`) still work
  with Cloud unchecked. Probe lists models and resolves `llama3.1` vs `llama3.1:latest`.
  Suggest retries without `format=json` when the model rejects JSON mode, and falls back
  to `/api/generate` if `/api/chat` is missing. Filter the grid, preview original vs
  suggested, Apply selected or high+medium unique-line writes. Hedged skip=true with a C# replacement is kept; advisory prose is rejected.
  CLI: `ollama-probe [--cloud] [--api-key]` / `ollama-suggest [--cloud] [--timeout] [--no-json-format] [--apply]`.
  Window size, last paths, Workshop checkbox, and Ollama host/model persist in `data/gui-settings.json`.
- **CP437 → UTF16** — convert legacy CP437 code points in `.cs` / `.xml` to UTF-16 glyphs; optional
  Workshop roots; always stamps `Encoding="utf-8"` on scanned XML roots (unless encoding ensure is off).

**Migrate XML hygiene** (same pass as C# curated rules): stamps root `Encoding="utf-8"` on every
`.xml`; rewrites mistaken `inventoryobject` / `removeinventoryobject` `Name=` → `Blueprint=`;
strips obsolete/invalid part attrs (`Wire.Material`, `Projectile.RequiresPhaseMatch`,
`Examiner.AlternateDisplayName`, `MeleeWeapon.RenderString`/`SecondaryStat`→`Stat`,
`Corpse.BodyDrop`/`InventoryDrop`, `Brain.IgnoreCombat`, `Physics.Occluding`,
`acegiak_Seed.Chance`); rewrites `MeleeWeapon ElementalDamage`/`Element` into an
`ElementalDamage` part; rewrites `MutationOnEquip ClassName=` → `Mutation=` (and drops
`Variant=`); renames object-blueprint mutation Names to ResolveType/Compat forms (`FlamingHands`→
`FlamingRay`, `FreezingHands`→`FreezingRay`, `Sleep Gas Generation`→`SleepGasGeneration`,
`Nerve Poppy`→`Analgesia`, `Double-muscled`→`HeightenedStrength`, …); Compat.xml blueprint
`Name`/`Inherits` renames (`Doru`→`Tam`, `JoppaZealot`→`VillageZeroConvert`, …); converts
`mutation Value="*delete"` → `removemutation`; converts unknown `<role Name>` → `tag Role`
(or drops when Role already present); fixes `Comwmerce` typo; trims whitespace in
part/mutation `Name=`; renames a 2nd `AnimatedMaterialGeneric` to
`AnimatedMaterialGenericAlternate`; merges duplicate named part/tag children (later attrs win;
`CyberneticsHasImplants` joins `Implants=`); Mutations.xml strips unused `Load=`/`Code=`, converts
`Description=` → `<description><p>…</p></description>`, fixes `ExludeFromPool`→`ExcludeFromPool`;
Naming.xml rewrites deprecated `*Var*` → `=var=`, camelCases `templatevar Name`, strips unused
`templatevar Load=`; strips unused
`DisableForcedConnections` from Worlds.xml `<cell>` tags (zone-only attribute); and appends missing
closing tags when a truncated file fails well-formedness with an open-element stack (clears
`Unexpected end of file` / “elements are not closed” MODERRORs — e.g. ChooseYourFighter expansions).
Comment-only / irreparable XML is left alone. Unnamed skill/part WARNs are often a *side effect* of
failed part ResolveType (see below). Worlds.xml zone `Load` create conflicts and unexpected
cell-level `<builder>` are **report-only** (see Recent Player.log patterns below).

**Migrate C# blueprint-type namespaces:** IPart / mutation / object-builder classes must live in
`XRL.World.Parts`, `XRL.World.Parts.Mutation`, or `XRL.World.ObjectBuilders` so
`ObjectBlueprintLoader` can `ResolveType` them. Custom namespaces (e.g. `COQMAN.HiddenHamlet`)
cause `Could not find XRL.World.Parts.X, element ignored` MODERRORs. ApiMigrator rewrites
IPart-only (etc.) namespace blocks, **splits trailing IPart classes after helpers** into
`XRL.World.Parts`, and adds `using` on sibling files that reference the moved types.

**Local + Workshop in one click (GUI):** launch `Launch-ApiMigrator.bat`, leave **Include Workshop**
checked (default when the Steam path exists). Use **Apply safe autofixes (Local + Workshop)** for a
confirmed bulk apply with no backups, or **Run Migration** with an optional mod-name filter /
dry-run. Uncheck **Include Workshop** for local Mods only.

### Truncated `SomeFile.cs'.` MODWARNs (nullable refs)

CoQ’s in-game Roslyn compiler rejects C# nullable-reference annotations (`#nullable enable`,
`string?`, `Object?`, …). The real diagnostic is usually **CS8632**, but Player.log often shows
only a mangled line like:

```text
MODWARN [Some Mod] - <...>/steamapps/workshop/content/333640/…/Core/Utils/Output.cs'.
```

(Unity/`#` rich-text stripping eats the `#nullable` message, leaving a mystery path.)

**Migrate** (GUI / CLI / `Update-ObsoleteApis.ps1`) auto-strips those on every `.cs` pass:

- Removes `#nullable enable|disable|restore` directives
- Rewrites reference-type `Type?` annotations to `Type` (fields, params, returns, `T?` where safe)
- **Keeps** `?.`, `??`, ternary `? :`, and value-type nullables (`int?`, `bool?`, `DialogResult?`, …)
- **Keeps** same-file and **same-mod** `enum?` (mod-wide enum scan), plus unknown `Type? name = null`
  defaults unless `Type` is a known reference (`string`, `object`, `GameObject`, …). This avoids
  CS1750 when a cross-file enum like `TaskPriority? priority = null` was stripped to a non-nullable
  enum default (ThreadingAPI / ModJobOptions).

### IPart namespace → `XRL.World.Parts`

ObjectBlueprintLoader resolves `<part Name="X"/>` as `XRL.World.Parts.X`. Migrate renames custom
namespaces on IPart-only files accordingly, adds `using XRL.World.Parts` to siblings that reference
the moved types, and **also** adds `using OldNamespace` on the moved file so helpers/types that
remain in the old namespace still compile (ThreadingAPI `EnhancedAIMemoryPart` / `AIPersonality`).

**Partial classes:** only the file that declares `: IPart` / `: BaseMutation` is classified and
moved. Sibling `partial class Name` files (no base list) used to stay behind → CS0103 /
`GetPart<T>` CS0311 (Broodmother `Arendeth_BroodmotherCommands_*`). After a move, Migrate
rewrites any namespace block whose top-level types are all among the moved set to the same
target namespace, and strips same-mod `OldNs.TypeName` FQNs to the short name. Cross-mod FQNs
(e.g. Village Placement Helper `ThreadingAPI.EnhancedAIMemoryPart`) still need a hand fix or
`using XRL.World.Parts`.

### Manifest / config JSON load killers (`ManifestFixer`)

CoQ deserializes `manifest.json` / `config.json` with typed fields. Common Workshop MODERRORs that
**Migrate** auto-fixes (dry-run reports; `-Apply` / `--apply` writes):

| Failure | Example | Fix |
|---|---|---|
| `dependencies` as a JSON **array** | `["Base"]` | Then normalized like the object form (Pickpocket) |
| Single required dep as `Dependencies` **object** / caret range | `{"moremoddinggoodies":"^1.4.0"}` | `"Dependency": "moremoddinggoodies"` — this is the `[JsonProperty]` setter on `ModManifest` that actually fills the required map. A `Dependencies` dictionary that never deserialized is why a dependent compiled (CS0234 / missing `tyrir.lib`) instead of **Missing Dependency** when the library mod failed |
| Multiple required deps | `{ "a": "^1", "b": "1.2.0" }` | Keep `Dependencies` object; rewrite ranges to `"*"` |
| Missing required library (C# `using tyrir.lib`) | no `Dependency` | Add `"Dependency": "moremoddinggoodies"` + `LoadAfter` (ModMap id, never a workshop folder number) |
| Steam workshop folder id or old folder title as a required key | `"3403942187": "*"` or `"More Modding Goodies!"` | **Remap** to the live ModMap id (`moremoddinggoodies`) using `workshop.json` / folder / title aliases. Unresolved published-file ids are still stripped |
| Missing compile-order pin | no `LoadAfter` | Add `LoadAfter` for every required manifest id, **except** ids already in `LoadBefore`. A required `Dependency` is a load-after edge (weight 10M); putting the same id in both created a cycle so XML stub mods (e.g. `WMExtendedMutations_Stubs`) loaded *after* the host and dependents treated them as not Active |
| WM Extended Mutations (beta **or** stable) | `"Dependency": "WMexMutationsStable"` or both keys as AND | One OR key `WMexMutationsBeta\|WMexMutationsStable` (vanilla two-key `Dependencies` is AND and fails if only one edition is installed). `LoadAfter` / `LoadBefore` list both ids separately. LoadBefore of either is still not also required. ThreadingAPI splits `\|` at resolve time |
| Obsolete numeric `loadOrder` / `LoadOrder` | `1` or huge int | **Remove** the field (MODWARN / Int32 overflow MODERROR) |
| Invalid `version` string | `"1.0 Beta"` | Semver-like `1.0.0` (strip words; unparseable → `1.0.0`, noted in report) |
| Empty / null / `{}` manifest | blank file | Minimal `{ "version": "1.0.0" }` (never invents `id` / `title`) |

`id` / `title` are never rewritten when already set. A missing `id` is filled with the canonical ModMap id (sanitized folder name) so later folder renames do not break dependents. Workshop folder numbers and old titles in `Dependencies` / `LoadAfter` are remapped to that id when the library is installed locally.

Live Steam roots are discovered by `SteamInstall` (prefers `D:\games\Steam` when that library has both the game and `workshop\content\333640`). Truncated compiler/Player.log paths (`<...>/steamapps/workshop/content/333640/<id>/File.cs`) resolve against that workshop folder — not a leftover `E:\SteamLibrary` copy.

### Recent Player.log patterns (Worlds.xml + Compat)

XmlDataHelper MODWARNs that **Migrate** now surfaces (report-only unless noted):

| Warn | Handling |
|---|---|
| `Found existing zone with range … load mode create doesn't indicate replace or merge` | **Report-only** (`WorldsXml.ZoneLoadCreate`): under `<cell Load="Merge\|Replace">`, flag `<zone` without `Load=`. Set `Load="Merge"` (soft overlay) or `Load="Replace"` (map floors) by hand — e.g. Bethesda Susa landmark overlays. Never auto-picks Merge vs Replace. |
| `Unexpected 'builder' element` (cell children) | **Report-only** (`WorldsXml.CellBuilder`): cells allow `zone`/`properties` only; move builders to zones (or `postbuilder`); Music → `<music>` on zones. Never auto-deletes builders. |
| Unused attribute `DisableForcedConnections` on `<cell>` | **Autofix** (`WorldsXmlFixer`): strip from cell opening tags (valid on `<zone>` only). |

### Populations.xml (`PopulationXmlFixer` / `PopulationXmlAdviceScanner`)

Confirmed against `XRL.PopulationManager` (Managed). XmlDataHelper is case-sensitive; `Load == "Merge"` etc. are case-sensitive.

| Warn | Handling |
|---|---|
| Required attribute `Name` missing on `<group>` | **Report-only** (`PopulationXml.GroupNameMissing`): add a unique `Name` (vanilla StartingGear uses `Name="Items"`). Never invents names. |
| Unused `name=` / `load=` / `style=` (wrong case) | **Autofix** (`PopulationXmlFixer` + curated rules): `Name=`, `Load=` with Merge\|Replace\|Remove title-case, `Style=` on population/group. |

### Factions.xml (`FactionsXmlFixer` / `FactionsXmlAdviceScanner`)

Confirmed against `XRL.World.Factions` (Managed). Factions merge by `Name`; root never reads `Load`.

| Warn | Handling |
|---|---|
| Unused attribute `Load` on `<factions>` / `<faction Load="Merge">` | **Autofix** (`FactionsXmlFixer`): strip `Load="Merge"`. Keep `Load="Replace"` on `<faction>` (only value the loader checks when Name exists). |
| Unexpected `interest` element | **Report-only** (`FactionsXml.BareInterest`): wrap under `<interests>`. Never auto-wraps. |
| Unused attribute `skill` on `<waterritual>` | **Autofix**: rename to `Skill=` (case-sensitive). |
| Unused attribute `EEmblemTileColor` | **Autofix**: rename to `EmblemTileColor`. |

### Mutations.xml (`MutationsXmlFixer`)

Confirmed against `XRL.MutationFactory` / `MutationEntry` / `IPartEntry` (Managed). Same-Name redeclare merges; **no `Load=`**.

| Warn | Handling |
|---|---|
| Unused attribute `Load` on `<mutations>` / `<category>` / `<mutation>` | **Autofix**: strip `Load=` |
| Unused attribute `Code` on `<mutation>` | **Autofix**: strip (legacy char code removed) |
| Unused attribute `Description` on `<mutation>` | **Autofix**: convert to child `<description><p>…</p></description>` |
| Unused attribute `ExludeFromPool` (typo) | **Autofix**: rename to `ExcludeFromPool` |

### Naming.xml (`NamingXmlFixer`)

Confirmed against `XRL.Names.NameStyles` / XmlDataHelper deprecation messages. Vanilla uses `=var=` placeholders and camelCase `templatevar` Names.

| Warn | Handling |
|---|---|
| Deprecated Variables Format `*Var*` → `=var=` | **Autofix**: rewrite in `<template Name>`; first letter lowercased (`*CreatureType*`→`=creatureType=`) |
| `templatevar Name` should begin with lower case | **Autofix**: PascalCase → camelCase |
| Unused attribute `Load` on `<templatevar>` | **Autofix**: strip |

### Genotypes.xml (`GenotypesXmlFixer`)

Confirmed against `XRL.GenotypeFactory.LoadGenotypeNode` (Managed). Same-Name redeclare merges; **no `Load=`**.

| Warn | Handling |
|---|---|
| Unused attribute `Load` on `<genotype>` | **Autofix**: strip |

### Subtypes.xml (`SubtypesXmlFixer`)

Confirmed against `XRL.SubtypeFactory` (Managed). Root `XMLNodes` only accepts `class` (LanguageXml documents root `subtype` for i18n, but the loader does not). Same-ID/Name redeclare merges; **no `Load=`**.

| Warn | Handling |
|---|---|
| Unused attribute `Load` on class/category/subtype/skills/… | **Autofix**: strip |
| Unused attribute `Code` on `<subtype>` | **Autofix**: strip (legacy char code) |
| Unused attribute `DisplayName` on `<class>` | **Autofix**: rename to `ChargenTitle=` (strip if ChargenTitle already set) |
| Unused attribute `Class` / `Tile` on `<class>` | **Autofix**: strip (those attrs belong on subtype/genotype) |
| Unused attribute `Foreground` / `ForegroundColor` on `<subtype>` | **Autofix**: promote to `DetailColor=` when missing, else strip |
| Unexpected `subtype` / `stat` / `skills` at root | **Autofix**: wrap orphans under `<class ID="Callings">`, or expand a preceding empty/self-closing `<class>` |

Still covered by curated rules (verify enabled):

- `Dual_Wield_*` → `Multiweapon_*` (Compat skill renames)
- ObjectBlueprint `*Wares` builders → `GenericInventoryRestocker`
- `Calendar.get*` → `Get*`
- `AddReplacer` → `SetArgument` (literal/expr/ternary; bare IDs stay advice)
- `AddActionFixer` skips `Override` (no InventoryAction field)
- `ColorUtility.CapitalizeExceptFormatting` / bare `HistoricEvent.*EventProperty` / `History.GetNewEntity` stay `enabled: false`

PreferXML liquids: keep `BaseLiquid` classes in namespace `XRL.Liquids` matching Liquids.xml `<class>`.
Every liquid with `<class>` needs a `<render>` element (may be empty) or `BaseLiquid.Initialize` NREs —
**Autofix** (`LiquidXmlFixer`) inserts `<render />` when missing. Merge-only overlays without `<class>`
inherit vanilla render and are **not** flagged. Class liquids still missing `<render>` after the fixer
report `PreferXML.LiquidMissingRender.Merge`.
Render colors on default render: `colorText`/`colorTile`/`colorDetail` → `baseColorText`/`baseColorTile`/`baseColorDetail`
(attrs + direct children; never `RenderSecondTo*` parts).
`BrighterWithVolume`/`LightLevel` move onto `<part Name="Glows" Class="Glows">` when safe, else report.
Named render parts get `Class="…"` matching `Name=` (Name-only → `BaseLiquidRenderPart` Extraneous for
`colorText`/`BrighterWithVolume`/etc.); leftovers report `PreferXML.LiquidRender.MissingPartClass`.

Bodies anatomy compat (curated):

- `Type="Flipper"` → `Type="Fin"`
- `Laterality="Middle"` → `Laterality="Mid"` (scoped to `Laterality=` attrs)

### CS0019 method-group `Count` (and tuple `??` notes)

Mods sometimes write `.Count > N` when `Count` is the **LINQ extension method group**
(`IEnumerable.Count()`), which compiles as CS0019 (`Operator '>' cannot be applied to operands
of type 'method group' and 'int'`). Example class of bug: More Modding Goodies `MoreOutput.cs`.

**Migrate** (GUI / CLI / `Update-ObsoleteApis.ps1`) runs `CountMethodGroupFixer` on every `.cs` pass
after the nullable stripper:

| Action | Pattern | Result |
|---|---|---|
| **Auto-fix** | `.Where(...).Count > N` (and other LINQ tails: `Select`, `SelectMany`, `OfType`, …) | → `.Count()` |
| **Auto-fix** | `IEnumerable<T> xs; … xs.Count > N` (also `IQueryable` / `IOrdered*`) | → `xs.Count()` |
| **Left alone** | `list.Count`, `dict.Count`, `ToList().Count`, `ICollection`/`IList`/`IReadOnlyList` property uses, ambiguous `var`/`foo.Count` | no rewrite (avoids breaking real properties) |
| **Left alone** | Same identifier declared as `IEnumerable<T>` *and* `List<T>` / `var x = new List<…>` in the file | no typed-name rewrite (Broodmother `defects` CS1955); LINQ-chain `.Where().Count` still fixed |
| **Flag only** | leftover LINQ-chain `.Count` compares Fix couldn’t rewrite; `?? Enumerable.Empty<(...)>` | report as `CS0019.CountMethodGroup` / `CS0019.TupleEmptyCoalesce` (named vs unnamed tuple `??` mismatches — align types by hand) |

Not a curated regex rule — balanced parentheses / typed locals need the dedicated helper (see
`_countMethodGroup` note in `curated_rewrite_rules.json`).

### PreferXML / PreferHarmonyPatch (override extension points)

When a mod **extends game/vanilla behavior or data** via `override` of game virtuals/entries,
prefer this order (see Mods rule `coq-prefer-xml-then-harmony` and the detailed research note
`docs/coq-internal-patching.md`):

1. **Game XML overlay / merge** (not Harmony, not a separate xpath API) when the data fits a
   supported root. Real mechanisms:
   - `DataManager.GetXMLFilesWithRoot` / `YieldXMLStreamsWithRoot` — mod files overlay by root;
     set `Encoding="utf-8"` (and optional `LoadPriority`) on the root.
   - **ObjectBlueprints** — `ObjectBlueprintLoader`: `Load="Merge"` / `MergeIfExists` on
     `<object>`; `removepart` / `removetag` / …; `<mixin Load="Fill">`.
   - **Populations** — `PopulationManager`: `Load="Merge|Replace|Remove"` (default Merge);
     runtime `AddToPopulation` only when XML isn’t enough.
   - **Conversations** — `ConversationXMLBlueprint.Merge`: node `Load="Merge|Replace|Add|Remove"`.
   - **Mutations / Skills / Liquids / InventoryActions** — redeclare the same `Name` so
     `HandleXMLNode` / `XRL.Blueprints.Factory` + `BlueprintReader` merge fields
     (`DisplayName`, `Type`, liquid elements, etc.). Shared enum: `XRL.XmlLoadType`
     (`Merge` / `Replace` / `Remove`) via `BaseXmlReader.GetLoadType`.
2. **Safer Harmony Prefix/Postfix** when code behavior is required (events, lifecycle hooks).
   Prefer Prefix/Postfix over Transpiler; typed `HarmonyPatch`; early-out on `__instance`.
3. **C# `override` only when there is no other option** (required abstract/interface, or no
   XML/Harmony path).

Do **not** assume Harmony when XML can express the change. Do **not** migrate CS0672 by writing a
*new* override signature (e.g. `Register(GameObject)` → `Register(GameObject, IEventRegistrar)`)
when XML or Harmony can replace the override entirely.

**Carve-out:** direct fixes inside the mod’s own methods (obsolete API call sites like
`TextBuilder` / `EmitMessage` / `InventoryAction`, feature logic, bugfixes) are normal in-place
edits. Prefer XML/Harmony only for the *extension mechanism*, not for ordinary mod code repair.

**Migrate** flags curated overrides as report-only hits (never auto-deleted), with **actionable
Advice** in the Markdown report / GUI detail pane. Guidance always says **Do not add `[Obsolete]`**
(CS0672 is not fixed by stamping Obsolete).

| Hit member prefix | Examples | Guidance |
|---|---|---|
| `PreferXML.*` | `DisplayName`, `Type`, `IsLiquid`, `GetDisplayName`, `LiquidProperties`, `LiquidBlood`, `LiquidWarmStatic` | Move to the game’s XML overlay for that domain (see doc); remove setter/override when feasible; Advice includes Mutations.xml / Liquids.xml / BaseGlitchPart snippets |
| `PreferHarmonyPatch.*` | `Register`/`HandleEvent`/`WantEvent` on a **concrete vanilla type** (`Stomach`, `Brain`, …); `Drank`/`Render`/`Apply`/tick hooks | Prefer safer Prefix/Postfix over rewrite-to-new-override. **Not flagged** on the mod’s own `IPart`/`Effect`/`BaseMutation`/`*Part`/`*Effect` event pipeline (`WantEvent`/`HandleEvent`/`Register`/`FireEvent`). |

Implemented by `OverridePreferenceScanner` + `ManualAdvice` (C#) / `Find-OverridePreferenceHits` +
`Get-ManualAdvice` (PowerShell). Stub template: `OverridePreferenceScanner.HarmonyStubTemplate`
(docs/agents only — not written into mod files). Full API/attribute reference:
`docs/coq-internal-patching.md`.

### Confidence-gated programmatic auto-fixes (dry-run lists; `-Apply` writes)

Beyond curated regex, Migrate also runs (on `.cs` only):

| Fixer | Auto-fix when | Otherwise |
|---|---|---|
| **ShowOptionListFixer** | `Popup.ShowOptionList` / `Async` args parse and map to `PickOption` / `PickOptionAsync` (positional order from Managed + named remaps like `onResult`→`OnResult`) | Advice-only with suggested named-arg call shape |
| **RegisterOverrideFixer** | Last-resort: simple `override void Register(GameObject X)` body is only `X.RegisterPartEvent(this, …)` / `UnregisterPartEvent` + optional `base.Register(X)` → bump to `Register(GameObject, IEventRegistrar)` + `Registrar.Register(…)` | Complex bodies left in place. PreferHarmonyPatch only when replacing a vanilla type; the mod’s own `IPart`/`Effect` Register is the part pipeline |
| **ReverseTranslateBitFixer** | Clear ID cues (`string x =`, `+=`, `== "?"`, BitCost…) → `FetchBitByCode(c)?.BitID.ToString() ?? "?"`; clear color cues (`ColorString`, `{{`, DisplayColor…) → `.DisplayColor`; `ReverseCharTranslateBit` → `.BitID` char | Ambiguous sites stay advice (obsolete msg says `.ID`; live field is `BitID`) |
| **AddActionFixer** | Obsolete string `AddAction(…)` on **game inventory events** (`IInventoryActionsEvent`, `GetInventoryActionsEvent`, `EventParameterGetInventoryActions`, …) maps to `AddAction(new InventoryAction { … })`. Strips CS8209 `_ = E.AddAction(...)` void discards. Untyped receivers only rewrite when the file mentions those inventory types. | Static literal Name/Display/Command/Key: **InventoryActionsXmlFixer** writes `AddXMLAction` + `InventoryActions.xml`; unknown named args skipped. **Mod-defined** `AddAction` (vendor-action events, etc.) is left alone. |
| **InventoryActionsXmlFixer** | Literal **inventory** actions → `AddXMLAction("Name")` + merged `InventoryActions.xml` | Custom/vendor `AddAction`, dynamic Display/Command expressions stay as-is / InventoryAction objects |
| **StatisticCtorFixer** | 5-arg `new Statistic("Name", min, max, value, owner)` (or name+displayName form) → `new Statistic(blueprint)` + `Statistics.xml` | Non-literal Name, other arities stay manual |
| **LiquidCsToXmlFixer** | `[IsLiquid]` / ctor literals (including `Temperature`, `Weight`, `Glows`, and complete `FreezeObject*` triples) / GetName/GetColor/GetColors/GetValuePerDram / simple `BeforeRender` glow, `Vaporized => false`, and Blood-like render on `BaseLiquid` → merged `Liquids.xml` (`Name` = ctor slug), strip those C# sites. Merge-missing into an existing liquid; never overwrite values | Non-literal or incomplete assignment groups stay PreferXML.LiquidProperties advice |
| **LiquidDrankToPartFixer** | Own `BaseLiquid.Drank` → `MessageOnDrink` (static Compound+return true) or `XRL.Liquids.Parts.*OnDrink` + Liquids.xml `<part>`; runs before liquid metadata extraction so referenced literals such as `Temperature` can be bound into the part | Vanilla liquid class names left for PreferHarmony; last-resort **DrankOverrideFixer** only on those leftovers |
| **CachedDoubleSemicolonExpansionFixer** | `List<string> x = …CachedDoubleSemicolonExpansion()` → `IReadOnlyList<string>` (CS0266) | Other `List<string>` assigns left alone |
| **ThingsFixer** | `Extensions.Things` / `.Things(` with literal `what` → `XRL.Language.Strings._T("…", "=number.things:…=").SetArgument("number", …)` (FQN; floating receivers wrapped in `(long)Math.Round`) | Non-literal nouns stay advice-only |
| **GameTextCallSiteFixer** | `GameObject.t/an/does/Does/poss`, `.them/.itis`, `LiquidVolume.GetLiquidName`, `Grammar.MakeTitleCase`, literal or local-backed `DidX`/`XDidY`/`XDidYToZ` (including named Actor/Verb and long positional overloads), `GetVerb`, and article/pronoun concatenations → `StartReplace` / `EmitMessage` | Non-literal grammatical words and unsupported message overloads stay advice-only |
| **ModernCompilerFixer** | Repairs current compiler-shape changes (`Render` bool→void, `TakeDamage(ref amount, text)`, zero-argument `WantTurnTick`, generic `HasGoal`, liquid/bit/zone helper renames) and conservative malformed-output/unused-literal cases | Only syntactically and semantically mechanical shapes are changed |
| **GetDisplayNameArgFixer** | CS1739 `GetDisplayName(WithAnnotations: …)` → `Annotations:` (BaseMutation) | Positional `GetDisplayName(false)` left alone (`Direct`) |
| **DrankOverrideFixer** | Last-resort: leftover vanilla-liquid `Drank(..., StringBuilder Message, …)` → `TextBuilder Message` (+ `using XRL.World.Text`) | Own `BaseLiquid.Drank` is **LiquidDrankToPartFixer** (not a signature bump). PreferHarmony for vanilla liquid patches |
| **CapitalizeFixer** | Simple `recv.Capitalize()` / `Capitalize(bool)` → `Translator.InitUpper(recv)` | Chained receivers (`Grammar.Cardinal(n).Capitalize()`) stay advice-only; curated regex covers `Extensions.Capitalize(` |
| **VariableReplacerFixer** | `[VariableObjectReplacer(…)]` → `[VariableReplacer(…, Capitalization = true)]`; `[VariableReplacer]`/`[VariableObjectReplacer]` `DelegateContext` → `VariableContext`; body `Context.Target`/`Pronouns` → add `GameObject Object` | Conversation `DelegateContext` (no VariableReplacer attr) left alone; `Context.Explicit` stays manual |
| **FinalRenderOverrideFixer** | `override bool FinalRender(RenderEvent E, bool Alt)` when `Alt` is unreferenced → drop bool param | PreferHarmonyPatch.FinalRender; if Alt is used, fold logic by hand |
| **HarmonyDynamicPatchFixer** | `[HarmonyPatch(typeof(RemovedType)…)]` / string type name for types in `data/removed_game_apis.json` (Sifrah minigames, etc.) → `[HarmonyPatch]` + `Prepare()`/`TargetMethod()` via `AccessTools.TypeByName` so PatchAll skips when missing | Multi-method classes, `MethodType.Getter`, or no method name stay report-only |
| **HarmonyPatchParameterFixer** | Verified Harmony target-parameter renames are applied to Prefix/Postfix signatures and their bodies; currently `Disarming.Disarm` `Object`→`Subject` | Explicit signature catalog only; unknown targets are never guessed |
| **RemovedGameApiFixer** | `if (Options.Sifrah*)` / `AnySifrah` braced blocks stripped; leftover `Options.Sifrah*` → `false` (then unwrap `false ? a : b`) | Leftover `new PsychicCombatSifrah` / subclassing stays report-only (`RemovedType.*`) |
| **Curated regex** | `.pPhysics`→`.Physics`, `.pRender`→`.Render`, `Brain.pPhysics`→`.ParentObject.Physics`, `GameObject.create(`→`Create(` (not `ScreenBuffer.create`), `LiquidXxx.ID`→`LiquidID.Xxx` (Salt/Blood/Water/WarmStatic/…), `AddReplacer(lit, valueExpr)`→`SetArgument` (delegate/method-group forms → `[VariableReplacer]`, not SetArgument) | — |

Also report-only: **LiquidXmlAdviceScanner** (C# files only) flags liquid temperature/physics/Slippery*/Cleansing/… assignments, `LiquidBlood.*`, and `LiquidWarmStatic.ApplyRandomEffectTo`/`GlitchObject`/`GlitchZone`/`ID` as PreferXML (BaseGlitchPart / GlitchOn* / Liquids.xml). Object-blueprint `Physics Weight=` and population `Weight=` are **not** liquid fields. **TextBuilderHalfMigrationScanner** flags TextBuilder + SB-only `AppendSigned`/`AppendArmor`/… (CS1929), obsolete `AddsRep.AppendDescription` arity, and `InventoryAction.DefaultDisplayOrder` → `Priority`/`Default`. Light CS0118 namespace-vs-type when a `using` imports a namespace ending in `Telepathy`/etc.

Workshop `-Apply` writes go through `WorkshopWrite` (clear ReadOnly, direct write / FileStream,
then same-folder sibling `.tmp` + Replace). **No `%TEMP%` fallback** — cross-volume temp copies
fail or confuse Steam file watches.

Dry-run reports **Auto-fixes that WOULD be applied**; `-Apply` / `--apply` writes them. Advice-only
hits remain in the report with Code + Advice blocks.

## CLI usage

### `ApiMigrator.Cli` (dotnet)

```powershell
cd "D:\games\Ai assisted toolkit\Tools\Qud\src\ApiMigrator.Cli"

# Dry run over the whole Mods folder (default)
dotnet run -- migrate

# Scope to one mod, write changes, custom report path
dotnet run -- migrate --mod "Qud Fishing" --apply --report "..\..\reports\qud_fishing.md"

# Include the Steam Workshop folder too
dotnet run -- migrate --include-workshop

# Refresh the dump from the live game DLLs (dry run - just shows the diff)
dotnet run -- refresh-dump

# ...and actually commit the merge (backs up the old dump automatically)
dotnet run -- refresh-dump --save

# CP437 → UTF-16 (dry-run; add --apply to write)
dotnet run -- convert-cp437 --include-workshop --report "..\..\reports\cp437.md"

# Local Ollama leftover suggestions (requires ollama serve)
dotnet run -- ollama-probe
dotnet run -- ollama-suggest --mod "Improved Mutations" --max 12 --report "..\..\reports\ollama-suggest.md"

# Optional: Ollama Cloud (https://ollama.com) — set OLLAMA_API_KEY or pass --api-key
dotnet run -- ollama-probe --cloud
dotnet run -- ollama-suggest --cloud --model gpt-oss:20b --mod "Improved Mutations"
```

Run `dotnet run -- ` with no arguments for the full flag list.

### `Update-ObsoleteApis.ps1` (no build required)

```powershell
cd "D:\games\Ai assisted toolkit\Tools\Qud"

# Dry run, whole Mods folder
.\Update-ObsoleteApis.ps1

# Apply fixes to one mod folder
.\Update-ObsoleteApis.ps1 -Mod "Qud Fishing" -Apply -Report ".\reports\qud_fishing.md"

# Scan custom paths, including Workshop
.\Update-ObsoleteApis.ps1 -Path @("C:\...\Mods", "D:\games\Steam\steamapps\workshop\content\333640")
```

Parameters: `-Path` (string[], default = this `Mods` folder), `-Mod` (substring filter),
`-Apply` (default off = dry run), `-Report` (markdown output path), `-DumpPath` / `-RulesPath`
(override the JSON data files), `-Exclude` (extra folder-name excludes beyond the built-in
`_tools`, `bin`, `obj`, `.git`, `.vs`, `_decompile*`, `scratch`).

Every apply keeps a `.bak` copy of each changed file next to the original (unless you pass
`--no-backup` to the CLI). **Managed DLLs and StreamingAssets (Base/DLC) are never written.**
Mod scan roots (your own / Workshop source) are the only write targets.

## How it decides what to fix vs. flag

1. **Curated rules** (`data\curated_rewrite_rules.json`) — hand-verified regex find/replace pairs
   where the old and new API are a straight drop-in swap (e.g. `Grammar.Cardinal(` →
   `Translator.Cardinal(`). These are applied automatically under `-Apply`/`--apply`.
   - Optional **`ensureUsings`**: when a rule fires on a `.cs` file, missing `using Namespace;`
     directives are inserted (e.g. `Event.NewStringBuilder` → `TextBuilder.Get` also adds
     `using XRL.World.Text;`).
   - **`postEnsureUsings`**: after all rewrites, if a pattern still matches (e.g. `\bTextBuilder\b`),
     ensure the listed usings — heals leftovers from earlier migrator runs that rewrote call sites
     without the import.
   - Hygiene rules also fix the mistaken FQN `XRL.World.TextBuilder` and
     `StringBuilder x = TextBuilder.Get(...)` typed locals.
   - **`GivesRep.AppendReputationDescription`**: **AppendReputationDescriptionFixer**
     (programmatic — not curated regex) rewrites
     `StringBuilder SB = new(); … .AppendReputationDescription(SB)` to
     `using TextBuilder SB = TextBuilder.Get(); …`. The old multi-line curated regex
     ReDoS-hung PowerShell on empty `new()`/`new StringBuilder()` sites; it is disabled.
   - After curated regex rules, **NullableAnnotationCleaner** strips CoQ-rejected NRTs, then
     **CountMethodGroupFixer** rewrites high-confidence CS0019 `.Count` method-groups
     (LINQ tails / `IEnumerable`-typed names → `.Count()`) and flags
     `?? Enumerable.Empty<(...)>` tuple mismatches for manual review.
   - Then programmatic fixers: **ShowOptionListFixer**, **RegisterOverrideFixer**,
     **ReverseTranslateBitFixer**, **AddActionFixer**, **InventoryActionsXmlFixer**,
     **StatisticCtorFixer**, **LiquidCsToXmlFixer**, **LiquidDrankToPartFixer**, **AppendReputationDescriptionFixer**,
     **ThingsFixer**, **GameTextCallSiteFixer**, **TextBuilderCsFixer**
     (`Event.FinalizeString(tb)` → `tb.ToString()`, `AppendSigned` → `AppendModifier`,
     AddsRep 7-arg Value/Faction swap), **GetDisplayNameArgFixer**, **BaseMutationSetterFixer**,
     **DrankOverrideFixer**,
     **HarmonyDynamicPatchFixer** (removed minigame `typeof` → Prepare/TargetMethod),
     **HarmonyPatchParameterFixer** (verified Prefix/Postfix parameter-name drift),
     **RemovedGameApiFixer** (`Options.Sifrah*` branches) (confidence-gated; see table above).
   - Curated/dump regexes use a **2s MatchTimeout** in Core and `Update-ObsoleteApis.ps1`
     (optional `requiresSubstring` gate on curated rules). Progress logs every 25 files.
   -      **OverridePreferenceScanner** / **LiquidXmlAdviceScanner** / **WorldsXmlAdviceScanner** /
     **FactionsXmlAdviceScanner** + **ManualAdvice** flag curated
     `override` extension points, liquid PreferXML, Worlds.xml Load/builder hygiene, and Factions.xml
     Load/interest/skill/emblem hygiene with actionable Advice — XML → Harmony →
     override only when no other option; **never** “add `[Obsolete]`”. Carve-out for in-place mod
     code fixes. Never auto-deletes complex overrides. **WorldsXmlFixer** strips unused
     cell `DisableForcedConnections`. **FactionsXmlFixer** strips unused `Load=Merge`,
     rewrites `waterritual skill=`→`Skill=` and `EEmblemTileColor`→`EmblemTileColor`
     (bare `<interest>` stays report-only via **FactionsXmlAdviceScanner**).
2. **Dump scan** (`data\obsolete_api_dump.json`) — everything else the game flags `[Obsolete]` is
   matched via each entry's `searchPattern` regex and reported as a "needs manual review" hit with
   the game's own obsolete message, but is **never auto-rewritten** (semantics may have changed,
   e.g. `AddReplacer` — value forms → `SetArgument`, delegate forms → `[VariableReplacer]` —
   or a plain rename that still needs verification). Also note recent dump advice: HistoricEvent
   `ExpandString` → `Expand()`, `GameObject.Poss`/`poss` → `=GameObject.Poss#GameObject=` /
   `=GameObject.poss#GameObject=`, `Calendar.getDay`/`getMonth`/`getYear`/`getTime` → PascalCase `Get*`
   (curated autofix). `Calendar.GetDay` is not auto-rewritten to `=time.day=` (too broad); messaging/Popup/journal may hand-migrate via StartReplace.
   BaseLiquid `Vaporized` →
   `(LiquidVolume, GameObject)`, Grammar `weird*` → `TextConstants.WeirdSets`.)
   - Instance methods use `\.Member\(` (real call sites), not `Type.Member\(` (almost never in
     mods). Refresh-dump heals older dumps that still have the Type-qualified form.
   - **False-positive hardenings:** refresh also re-applies curated pattern tightenings for known
     collisions (modern `Register(Object, IEventRegistrar)`, `AppendRules(string)`,
     `GameObject.RegisterPartEvent`, string `AddAction` vs `InventoryAction`, GameText
     `=subject.The=` tokens, etc.). The scanner additionally skips hits inside `//` / `/* */`
     comments and GameText `=...=` tokens (`HitFilter`). Some members are text-scan-disabled
     (`(?!)`) when they collide too broadly (e.g. `IStingerProperties.GetDescription`) — use
     CS0618 compile for those.

Only promote something from "flagged" to "curated" once you've manually verified the replacement
is a safe, semantically-equivalent swap.

### Example: `ReplaceBuilder.AddObject` -> `SetArgument`

`XRL.World.Text.ReplaceBuilder.AddObject(GameObject, string Alias = null, bool Silent = false)` is
obsolete in favor of `SetArgument`, but `AddObject` textually collides with the very common,
*unrelated* `Cell.AddObject`/`Inventory.AddObject`/`Zone.AddObject` object-placement APIs. The dump
and curated rules split this into two entries so the auto-fixer only ever touches the safe subset:

- **Auto-fixed (`ReplaceBuilder.AddObject(Object,Alias,...)` entry):** calls with an explicit
  string-literal `Alias`, e.g. `.AddObject(Vendor, "vendor")` -> `.SetArgument("vendor", Vendor)`.
  Note the argument order swaps (`AddObject(Object, Alias)` vs. `SetArgument(Alias, Object)`).
- **Flagged for manual review (`ReplaceBuilder.AddObject(Object)` entry):** the common unaliased
  single-arg form, e.g. `.AddObject(Vendor)`. Per the decompiled `ReplaceBuilder` source, this
  overload forwards to `AddArgument(Alias, Object, Silent)` -> `TryArgumentAction`, and a null
  `Alias` makes `TryArgumentAction` reject the argument outright — so real call sites are relying
  on chain *position* against the `SetSubject`(1st)/`SetObject`(2nd) convention, or need a distinct
  chosen alias for a 3rd+ argument via `SetArgument`. That choice needs a human, not a text swap.

Both entries' patterns require one of `StartReplace(`, `_T(`, the literal token `ReplaceBuilder`,
`.Start(`, or `EmitMessage` earlier in the *same statement* (the lookbehind stops at any `;`) as a
confidence signal, so a call like `cell.AddObject(gameObject)` (real `Cell.AddObject`) is never
mistaken for the text API even if an unrelated `ReplaceBuilder`-style chain happens to appear
earlier in the same file.

## DLL research details

- Reflects the DLLs you name (default just `Assembly-CSharp.dll`) inside the Managed folder you
  point at (default `E:\SteamLibrary\steamapps\common\Caves of Qud\CoQ_Data\Managed`) using
  `Assembly.LoadFrom` plus an `AssemblyResolve` handler scoped to that folder — this mirrors the
  approach already proven to work by the original ApiDump tool against this exact game build.
- It is **strictly read-only**: it only loads assemblies into the migrator's own process to read
  their metadata/attributes. Nothing in the `Managed` folder is ever modified.
- A full scan (~8,000 types) takes a few seconds and typically surfaces 600+ `[Obsolete]` members
  across the whole assembly — far more than the curated dump's default ~34, since most of those
  aren't relevant to typical mod code (UI internals, editor-only types, etc.). Saving a refresh
  only *adds* newly-discovered members (flagged `needsManual: true` until you review them) and
  updates the message text on existing single-overload entries — it never deletes or overwrites
  your hand-curated `searchPattern`/`autoFixable`/notes fields.
- Known cosmetic quirk: a few original dump entries used descriptive combined names for grouped
  overloads (e.g. `AddReplacer(Key,Value)`), which won't key-match the precise per-overload names
  reflection reports; a refresh will show these as both "removed" (the old combined label) and
  "added" (the individual overloads) — harmless, just tidy up by hand if it bothers you.

## Project layout

```
  README.md / ApiMigrator.md       - this file / migrator details
  Launch-Gui.bat                    - menu of all Qud GUIs
  Launch-ApiMigrator.bat            - Obsolete-API Migrator GUI
  Switch-Api.bat                    - pin dump+rules to public / lang / live (or --list)
  Update-ObsoleteApis.ps1           - zero-build PowerShell API migrator
  Validate-ChargenXml.ps1           - population / genotype / subtype scanner+fixer
  Convert-Cp437.ps1                 - CP437 → UTF-16 converter for .cs / .xml
  data\
    obsolete_api_dump.json          - active obsolete-API map (synced from by-version)
    curated_rewrite_rules.json      - compiled auto-fix rules (from charts/)
    charts\                         - human-editable XML/JSON rule charts + manifest
    by-version\{FileVersion}\       - dump + rules + charts profiles per Managed build
    by-version\active-override.json - optional pin (switch-api); omit when sharing
    backups\                        - automatic timestamped dump backups from refreshes
  reports\                          - migration reports land here by default
  src\
    Directory.Build.props           - shared x64 PlatformTarget for all projects
    ApiMigrator.Core\               - shared engine (dump/rules loading, rule application,
                                       using insertion, file scanning, migration run,
                                       DLL reflection + diff, CP437 converter, chargen)
    ApiMigrator.Core.Tests\         - smoke runner (`dotnet run -c Release -r win-x64`) exercising
                                       TextBuilder/using hygiene + CP437 against the live rules JSON
    ApiMigrator.Cli\                - `migrate` / `refresh-dump` / `resolve-cs0618` /
                                       `convert-cp437` / `sync-version` / `switch-api` /
                                       `export-charts` / `compile-rules` (win-x64)
    ApiMigratorGui\                 - WPF desktop app on top of Core (win-x64)
  QudLab\                           - mod IDE (separate from ApiMigrator)
```

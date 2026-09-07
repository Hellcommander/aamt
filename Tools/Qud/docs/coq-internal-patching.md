# Caves of Qud — internal XML / data patching (not Harmony)

Research note for ApiMigrator + Cursor rules. Sourced from read-only reflection/decompiles of
`Assembly-CSharp.dll` (Managed) and vanilla StreamingAssets XML. Do **not** treat this as a
replacement for Harmony when code behavior is required.

**Provenance:** `_reports/patching-research/` (ilspycmd + reflection scratch). Re-check after game
updates via DLL Research / `ilspycmd -t <Type>`.

---

## Summary

Mods overlay game data by dropping XML under the mod folder. The game indexes every XML file by
**root element name**, sorts by mod load order + optional `LoadPriority`, then each subsystem
re-reads all streams for its root and applies **per-entry** merge / replace / remove semantics.

There is **no separate "xpath patch" API**. Patching is:

1. File discovery via `DataManager` (root-indexed overlay)
2. Entry-level `Load=` attributes (and blueprint removals / mixins)
3. Occasional runtime helpers (`PopulationManager.AddToPopulation`, factory `Require`/`Get`)

Harmony remains the extension path for behavior; XML is the extension path for data/entries.

---

## Core pipeline

### `XRL.DataManager` — mod XML overlay

| Member | Role |
|---|---|
| `GetXMLFilesWithRoot(string Root)` | Sorted `List<DataFile>` for a root element (e.g. `"Objects"`, `"Populations"`, `"mutations"` — case as indexed) |
| `YieldXMLStreamsWithRoot(string Root, bool IncludeBase = true, bool IncludeMods = true)` | Yields `XmlDataHelper` per file (disposed on next move) |
| `GetXMLStream(DataFile)` / `GetXMLStream(string, ModInfo)` | Open one file as `XmlDataHelper` |
| Cache index | Root tag name -> files; `DataFile.Priority` from root `LoadPriority` (lang-tagged files default priority `-1000`) |

Sort order (`DataFile.CompareTo`): base before mods -> mod order -> higher `LoadPriority` first -> path.

Root attributes every mod XML should set:

```xml
<mutations Encoding="utf-8" LoadPriority="0">
```

- `Encoding="utf-8"` — required to skip CP437 conversion (`BaseXmlReader`; missing -> warn + cp437).
- `LoadPriority` — optional int; higher applies earlier within the same mod tier (vanilla Mutations uses `1000`).

### `XRL.XmlDataHelper` / `XRL.BaseXmlReader`

- `XmlDataHelper` — enhanced reader used by almost all loaders; `HandleNodes(...)`, mod-aware errors.
- `XmlDataHelper.Parse(string path, Dictionary<string, Action<XmlDataHelper>> handlers, bool includeMods = false)` — convenience: base file then optional `ModManager.ForEachFile`.
- `BaseXmlReader.GetLoadType(XmlLoadType Default = XmlLoadType.Default)` — parses attribute `Load`:

```csharp
public enum XmlLoadType : ushort
{
    Default = 0,
    Merge   = 1,
    Replace = 2,
    Remove  = 4
}
```

Many loaders still compare the raw `Load` **string** instead of calling `GetLoadType`, but the
vocabulary is the same: `Merge` / `Replace` / `Remove` (+ domain-specific extras below).

### `XRL.Blueprints.Factory` — liquids, inventory actions, etc.

Newer blueprint XML (e.g. `Liquids.xml`, `InventoryActions.xml`) goes through:

- `Factory.YieldReaders()` -> `DataManager.GetXMLFilesWithRoot(Root)` + `BlueprintReader`
- `Factory.Load()` -> `BlueprintReader.ReadBlueprint(this)` for each file
- Lifecycle hooked to `ModManager` mod-sensitive reset (`OnDeclare` / `OnLoad` / `OnFinish`)
- `BlueprintReader.RequireBlueprint<T>(Name)` / `RemoveBlueprint<T>(Name)` — get-or-create / delete named entries while parsing

Re-reading the same `Name` updates fields via generated `Handle*Node` loaders (`ParseAttribute`
keeps prior values when an attribute is omitted) — i.e. **implicit merge by Name**.

---

## Mechanism by data domain

### 1. Object blueprints — `XRL.World.Loaders.ObjectBlueprintLoader`

**Root:** `objects` / `Objects` (indexed from file root).
**Load:** `GameObjectFactory.LoadBlueprints()` -> `ObjectBlueprintLoader.LoadAllBlueprints()` ->
`DataManager.YieldXMLStreamsWithRoot("Objects")`.

Per `<object Name="..." Inherits="..." Load="...">`:

| `Load` | Behavior |
|---|---|
| *(absent / other)* | Assign / replace dictionary entry `Objects[Name] = data` |
| `Merge` | Merge children into existing blueprint; **error + discard** if Name unknown |
| `MergeIfExists` | Merge only if Name exists; silent no-op otherwise |

`ObjectBlueprintXMLData.Merge` overlays `Inherits` (if set) and merges child collections
(parts, tags, stats, ...).

**Removals (baked):** auto-generated sibling elements `remove` + node name:

- `removepart`, `removetag`, `removestat`, `removeproperty`, `removeintproperty`,
  `removeskill`, `removestag`, `removebuilder`, `removemutation`, ...
- Match key usually `Name=` (inventory objects use `Blueprint=`).

**Mixins:** `<mixin Name="OtherBlueprint" Priority="..." Include="..." Exclude="..." Load="Fill" />`

- Default mixin applies **after** `Inherits`.
- `Load="Fill"` applies **before** `Inherits` (fill gaps from another blueprint).

**Tag sentinel:** tag value `*noinherit` strips that tag during inherit bake.

**Runtime:** after bake, `GameObjectFactory` exposes the final `GameObjectBlueprint` dictionary.
`[WantLoadBlueprint]` types can get a static `LoadBlueprint(GameObjectBlueprint)` callback —
preload hook, not XML merge.

### 2. Populations — `XRL.PopulationManager`

**Root:** `Populations`. Default table `Load` is **`Merge`** if omitted.

| `Load` on `<population>` | Behavior |
|---|---|
| `Merge` | `existing.MergeFrom(incoming, existing)` |
| `Replace` | Replace whole table |
| `Remove` | Delete table |
| *(other / empty after coalesce)* | `Add` (fails if duplicate name) |

Child `<group>`, `<object>`, `<table>` also take `Load` (`Merge` / `Replace` / `Remove`) and
participate in `PopulationList.MergeFrom` (match by name+type or named group).

**Runtime API (beyond XML):**

```csharp
PopulationManager.AddToPopulation(string table, string sibling, params PopulationItem[] items)
```

Inserts items into the group that contains sibling object/table `sibling`. Prefer XML merge when
possible; this is for late/dynamic edits after load.

### 3. Conversations — `ConversationLoader` / `ConversationXMLBlueprint`

**Root:** `Conversations`. Files merged by conversation `ID`.

Default (Load unset / `0`): if ID already exists -> `ConversationXMLBlueprint.Merge`.

Per-node `Load` attribute (stored as `byte`, **not** `XmlLoadType`):

| XML value | Byte | Effect when merging into matching child |
|---|---|---|
| *(default / merge)* | `0` | Deep-merge attributes/children |
| `Replace` | `1` | Replace matching child entirely |
| `Add` | `2` | Always append child (even if ID matches) |
| `Remove` | `3` | Delete matching child |

Matching uses ID/Name/Type qualifiers (`Qualifier` attribute). Vanilla heavily uses
`Load="Merge|Replace|Remove"` on `<choice>`, `<text>`, `<node>`.

### 4. Mutations — `XRL.MutationFactory` + `MutationEntry`

**Root:** `mutations`. Streams via `YieldXMLStreamsWithRoot` (same overlay model).

**No `Load=` on mutation / category / mutations-root nodes.** Re-declaring `<mutation Name="SameName">` finds the existing
`MutationEntry` and calls `HandleXMLNode`, which **overwrites provided attributes** (DisplayName,
Type, Cost, Class, ...) and leaves omitted ones. Categories behave the same by `Name`.
ApiMigrator `MutationsXmlFixer` strips unused `Load=` / `Code=`, converts `Description=` attrs to
`<description><p>…</p></description>`, and fixes `ExludeFromPool` → `ExcludeFromPool`.

Prefer:

```xml
<mutations Encoding="utf-8">
  <category Name="Physical">
    <mutation Name="Adrenal Control" DisplayName="..." Type="..." />
  </category>
</mutations>
```

over C# `override` of `DisplayName` / `Type` / `GetDisplayName`.

Obsolete: leading `-` on category Name for removal — discontinued; use `Hidden="true"`.

### 5. Skills — `XRL.World.Skills.SkillFactory` + `SkillEntry` / `PowerEntry`

**Root:** `skills`. Same overlay + `HandleXMLNode` field merge by skill/power `Name`.

Extra description hooks on `IBaseSkillEntry.HandleXMLNode`:

- `AddDescription="..."`
- `AddDescriptionIfMod="ModSpec: text"`
- `ReplaceDescriptionIfMod="ModSpec: text"`

(`ModManager.ModLoadedBySpec`)

### 6. Liquids / inventory actions — `XRL.Blueprints.*`

XML roots are derived from the factory type name (`LiquidBlueprint` -> `Liquids`,
`InventoryActionBlueprint` -> `InventoryActions`). Files are discovered via
`DataManager.GetXMLFilesWithRoot` and read with `BlueprintReader`.

Declare/update by `Name`; use generated child elements (`<displayName>`, `<type>`, `<parts>`,
`<colors>`, `<flameTemperature>`, `<vaporTemperature>`, `<freezeTemperature>`,
`<combustibility>`, `<fluidity>`, `<evaporativity>`, `<staining>`, `<thermalConductivity>`,
`<circulatoryLossTerm>`, `<circulatoryLossNoun>`, `<valuePerDram>`, …)
rather than overriding `IsLiquid` / liquid description virtuals or assigning those fields in a
`BaseLiquid` constructor. Keep the liquid class in namespace **`XRL.Liquids`** so Liquids.xml
`<class>` / Class= resolves via `ResolveType` (custom namespaces fail the same way as misplaced
IParts → TypeLoadException). Every liquid with a class needs a **`<render>`** element (may be empty) so
`LiquidRenderBlueprint.Read` defaults `Part.Class` to `BaseLiquidRenderPart` — without it,
`BaseLiquid.Initialize` NREs on `Blueprint.Render.Part.Create`. ApiMigrator `LiquidXmlFixer`
inserts empty `<render />` under -Apply when `<class>` is present; merge-only overlays stay
report-only. Render colors use
`<baseColor>` / `<baseColorText>` / `<baseColorTile>` / `<baseColorDetail>` (not part-level
`colorText`/`colorTile`/`colorDetail` on the default render part — those belong on
`RenderSecondTo*` subclasses; `BrighterWithVolume`/`LightLevel` belong on `Glows`).
Named render parts need **both** `Name=` and `Class=` (same type name): `ModuleBlueprint`
resolves `Name`→type after Namespace state is popped, so Name-only parts fall through to
`BaseLiquidRenderPart` and log Extraneous for those fields. `LiquidXmlFixer` adds `Class=`
automatically. Vanilla Algae/Blood/Convalescence/Glows liquids are covered by the local
`LiquidRenderPartClassFix` overlay (and an optional StreamingAssets patch).
ApiMigrator `LiquidCsToXmlFixer` extracts literal ctor assignments, `[IsLiquid]`,
GetName/GetColor/GetColors/GetValuePerDram, and simple Blood-like render into Liquids.xml
under -Apply (`Name` = ctor slug). Own `BaseLiquid.Drank` is `LiquidDrankToPartFixer`
(MessageOnDrink or `XRL.Liquids.Parts.*OnDrink`). Do **not** bump
`Drank(..., StringBuilder, …)` → `TextBuilder` to keep an override — that last-resort
bump is only for leftover vanilla liquid patches.

### 7. Commands and other `XmlDataHelper` consumers

Example: `CommandBindingManager` uses `DataManager.YieldXMLStreamsWithRoot("commands")` +
`HandleNodes`. Same overlay pattern for any root registered in the XML cache.

---

## Runtime registration (non-Harmony)

Useful game APIs (still not Harmony):

| API | Use |
|---|---|
| `PopulationManager.AddToPopulation` | Patch population groups after XML load |
| `BlueprintFactory<T>.Get` / `TryGet` / `Resolve` | Read liquid/inventory/etc. blueprints |
| `MutationFactory.TryGetMutationEntry` / `GetMutationEntryByName` | Read mutation entries |
| `GameObjectFactory.Factory.Blueprints` / helpers | Read object blueprints |
| `ModManager.ForEachFile` / `ForEachFileIn` | Enumerate mod files by name |
| `XmlDataHelper.Parse` | Custom XML with optional mod include |
| `ModManager` mod-sensitive reset events | Re-run loaders when mods hot-reload |

`ModInfo.ApplyHarmonyPatches` / `UnapplyHarmonyPatches` exist but are **Harmony**, not XML.

There is no general "register XML patch at runtime" beyond writing files that `DataManager`
indexes or calling domain helpers like `AddToPopulation`.

---

## When to use which

| Goal | Prefer |
|---|---|
| Change DisplayName / Type / liquid data / skills / inventory actions / blueprint parts-tags | **XML overlay** (`Load="Merge"` / same `Name` redeclare / `removepart` / mixin) |
| Edit population tables | **XML** `Load="Merge|Replace|Remove"` on `<population>` / children; else `AddToPopulation` |
| Edit conversations | **XML** `Load="Merge|Replace|Add|Remove"` on nodes |
| Change event/lifecycle/UI behavior not expressible as data | **Harmony** Prefix/Postfix (typed `HarmonyPatch`, early-out on `__instance`) |
| Required abstract/interface or no XML/Harmony path | **C# `override`** only then |

**Do not** "fix" CS0672 by bumping an override signature when XML or Harmony can replace the
extension point. In-place obsolete-API fixes inside a mod's own methods are fine (carve-out).

---

## Quick examples

**Merge into an existing object:**

```xml
<?xml version="1.0" encoding="utf-8"?>
<objects Encoding="utf-8">
  <object Name="Snapjaw Scavenger" Load="Merge">
    <tag Name="MyModFlag" Value="1" />
    <removepart Name="SomeVanillaPart" />
  </object>
</objects>
```

**Merge population (default Load=Merge):**

```xml
<?xml version="1.0" encoding="utf-8"?>
<populations Encoding="utf-8">
  <population Name="Junk">
    <object Blueprint="MyWidget" Weight="5" />
  </population>
</populations>
```

**Mutation display rename:**

```xml
<?xml version="1.0" encoding="utf-8"?>
<mutations Encoding="utf-8">
  <category Name="Physical">
    <mutation Name="Adrenal Control" DisplayName="{{G|My Label}}" />
  </category>
</mutations>
```

---

## Agent / ApiMigrator pointers

- Cursor rule: `Mods/.cursor/rules/coq-prefer-xml-then-harmony.mdc`
- PreferXML hits: `OverridePreferenceScanner` (`PreferXML.*`)
- Decompile scratch: `_reports/patching-research/decompiled/`
- Refresh obsolete dump: GUI **DLL Research** or `ApiMigrator.Cli refresh-dump` (separate from this note)

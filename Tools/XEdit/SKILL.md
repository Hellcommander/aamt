---
name: xedit-assist
description: Use TES5Edit/xEdit via the XEdit.Clr host for Starfield and other Bethesda plugin work. Prefer Tools/XEdit and TES5Edit dev-4.1.6 definitions over the old 4.1.5f SF1Edit next to Starfield.exe.
---

# xEdit assist

When inspecting or patching `.esm`/`.esp` plugins, call the CLR/CLI instead of guessing record layouts.

## Location

`d:\games\Ai assisted toolkit\Tools\XEdit`

```
xedit-assist.bat locate
xedit-assist.bat defs --signature ALCH
xedit-assist.bat header <plugin>
xedit-assist.bat records <plugin> --signature WEAP --query laser
xedit-assist.bat dump --plugin MyMod.esm --edid Foo
```

Build: `dotnet build XEdit.Clr.sln -c Release`

## Fork

Use **https://github.com/TES5Edit/TES5Edit** branch **`dev-4.1.6`**.

Do not treat GitHub release **4.1.5f** as current Starfield support. That build is missing `.esp` editing, small/medium masters, and later DLC records.

Definitions file: `vendor/TES5Edit/Core/wbDefinitionsSF1.pas`

TES4 flags (Starfield): Master, Optimized, Localized, **Small**, **Update**, **Medium**, **Blueprint**.

## Rules

- Prefer creating **`.esm`** for Starfield.
- Always have `Starfield.esm` as a master. Do not attach blueprint masters unless the file is itself a blueprint.
- Fast path (`header`/`records`/`defs`) for research. Launch xEdit only for decoded dumps and writes.
- If `locate` warns the exe is older than 4.1.5q, say so and still use `defs` from `dev-4.1.6` source.

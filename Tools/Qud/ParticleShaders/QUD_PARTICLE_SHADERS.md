# Qud particle shaders

`Tools\Qud\ParticleShaders` turns a small JSON spec into **map shaders for the
[Qud Shader Library](https://steamcommunity.com/sharedfiles/filedetails/?id=3822020203)**: procedural
particle effects (sparks, embers, spores, motes, shards, rings) drawn as a full-screen pass over the map,
built into a per-platform bundle with Unity, and played by name from a mod's `ShaderEffects.xml` presets
or its C# wrapper (`BroodmotherShaderFX.Play("BM_SporeBurst", cell)`, `VortexShaderFX`, and so on).

```
spec.particles.json
   │  qud_particle_shader.py generate        (python; no Unity)
   ├─► <out>\shaders\<Name>.shader           ShaderKit contract: vUv, _Amt, _T, _Click, _Focus, _CellMap ...
   ├─► <out>\ShaderEffects.fragment.xml      <bundle Name="..."/> + one <preset> per effect
   ├─► <out>\usage.cs.txt                    how the mod plays them
   ├─► <out>\previews\<Name>.gif             numpy twin of the shader maths, over a map shot
   │  --lint: fxc (Windows SDK) compiles every fragment program offline
   │
   │  Build-QudShaderBundle.ps1              (Unity 6000.0.77f1 batch mode, ~1-3 min first run)
   ├─► <out>\Bundles\windows\<bundle>_windows
   │
   │  qud_particle_shader.py install          (copies the bundle, merges the presets)
   └─► <mod>\Bundles\windows\<bundle>_windows + <mod>\ShaderEffects.xml
```

`<out>` is `Tools\Output\QudShaderForge\<bundle>` (gitignored) unless `-OutDir` says otherwise.

## Quick start

```powershell
cd Tools\Qud\ParticleShaders

# generate + lint + previews for the Broodmother sample
.\New-QudParticleShader.ps1 -Spec specs\broodmother.particles.json

# then compile the bundle with Unity and drop it into the mod (restart the game afterwards)
.\New-QudParticleShader.ps1 -Spec specs\broodmother.particles.json -Build -Install

# let Ollama draft a spec from a description, then edit it and generate
.\New-QudParticleShader.ps1 -Spec my.particles.json -Describe "orange embers rising from a campfire, a few bright sparks" -Mod MyMod -Prefix MY_
```

Each step on its own:

```powershell
python -I qud_particle_shader.py generate specs\mountwright.particles.json --lint --preview --mapshot "<save folder>\QudShaderLibrary\mapshot.png"
python -I qud_particle_shader.py lint "..\..\Output\QudShaderForge\mw_fx\shaders\*.shader"
.\Build-QudShaderBundle.ps1 -ShaderDir ..\..\Output\QudShaderForge\mw_fx\shaders -Bundle mw_fx
python -I qud_particle_shader.py install ..\..\Output\QudShaderForge\mw_fx --mod-path "%USERPROFILE%\AppData\LocalLow\Freehold Games\CavesOfQud\Mods\Arendeth_Mountwright"
python -I qud_particle_shader.py schema
```

In game: wish `shader`, pick the new name from the menu (presets appear by their `Name`, raw shaders by the
last part of their path), or just trigger the mod moment that plays the preset.

## Requirements

| Step | Needs | Where it looks |
|---|---|---|
| generate | Python 3.8+ | PATH |
| lint | `fxc.exe` (Windows 10/11 SDK) | `C:\Program Files (x86)\Windows Kits\10\bin\*\x64\fxc.exe`, or `FXC` |
| preview | numpy, Pillow | the toolkit's Python |
| build | Unity matching the game (6000.0.77f1), Windows build support; macOS/Linux support for those bundles | `Shared\UnityVersionResolver` (Unity Hub folders, `E:\tools\Unity_Editor\<version>`) |
| all | the Qud Shader Library mod folder (its `ShaderKit\`) | `QUD_SHADER_LIBRARY`, `settings.json` `shaderLibraryPath`, the Steam workshop item next to `gameRoot`, `Mods\QudShaderLibrary` |
| draft | Ollama | `OLLAMA_HOST` or `http://localhost:11434` |

Add `"shaderLibraryPath": "D:\\games\\Steam\\steamapps\\workshop\\content\\333640\\3822020203"` to
`Tools\Qud\settings.json` if autodetection misses it.

## The spec

```json
{
  "mod": "Arendeth_Broodmother",          // mod id (messages, usage snippet)
  "modFolder": "Broodmother Mutation",    // folder under Mods\ when it differs from the id (install step)
  "bundle": "bm_fx",                      // lower case; Bundles\windows\bm_fx_windows, <bundle Name="bm_fx"/>
  "shaderPath": "Hidden/Broodmother",     // shader path prefix; the effect name is appended and is what plays
  "presetPrefix": "BM_",                  // preset names default to prefix + effect name
  "wrapper": "BroodmotherShaderFX.Play",  // call shown in usage.cs.txt (default QudShaders.Play)
  "effects": [ { ... }, { ... } ]
}
```

Every effect field has a default (`schema` prints them). Units: positions and sizes are **screen heights**
(a map cell is 0.04 high), speeds are screen heights per second, angles are degrees with 0 = right and
90 = up.

| Field | Values | Meaning |
|---|---|---|
| `name` | identifier | plays under this name; one shader per effect |
| `anchor` | `focus` `click` `player` | where the effect sits: the ShaderFX anchor (`.At` / `.Following`), the last (re)fire point, or the player's cell |
| `emitter.shape`, `emitter.radius` | `point` `ring` `disc` `cells` `screen` | where particles are born around the anchor; `cells` snaps births to map cells within `radius`; `screen` is everywhere |
| `mode` | `burst` `continuous` | burst: everything is born at a (re)fire (`_Click.z`), dies after `life`, re-fires with `Refire`; continuous: a steady stream, each slot re-rolls a new particle every cycle |
| `count` | 1..160 | particles in flight; every pixel visits every one, keep bursts under ~100 |
| `life` | `[min, max]` s | per-particle lifetime |
| `stagger` | s | burst: births spread over this long |
| `direction` | `radial` `inward` degrees | heading; radial/inward are relative to the anchor |
| `spread` | 0..360 | cone around the heading |
| `speed` | `[min, max]` | initial speed |
| `gravity`, `drag`, `swirl`, `wobble` | numbers | + gravity is down; drag per second; swirl in radians/s around the anchor; wobble is noise displacement |
| `cellSnap` | bool | positions snap to map cells: a tile-ish look |
| `shape` | `dot` `spark` `ring` `streak` `glyph` | the kernel: soft glow, a Gaussian stretched along the velocity, a thin ring, a trail behind the particle, a crisp square |
| `size`, `endSize`, `stretch` | | radius `[min, max]`, size multiplier at death, spark/streak length in sizes |
| `colors` | `["#birth", "#death"]` | gradient over life |
| `glow`, `blend` | `add` `alpha` `screen` | brightness; additive light, opaque dust/debris, or screen |
| `fadeIn`, `fadeOut`, `flicker` | 0..1 | fractions of life; flicker depth |
| `distort` | screen heights | refraction of the map under particles |
| `preset` | `name seconds amount fadeIn fadeOut refire layer` | the `<preset>` written for this effect |

Every generated shader also exposes `_Count`, `_Scale`, `_Speed`, `_Gravity`, `_Seed`, `_Tint`, `_Tint2`,
so one shader can serve several presets:

```xml
<preset Name="BM_SporeBurstBlue" Shader="SporeBurst" Seconds="3" Amount="1.2">
  <color Name="_Tint" Value="#60c0ff" />
  <float Name="_Count" Value="30" />
</preset>
```

```csharp
QudShaders.Play(new ShaderFX("SporeBurst").At(cell).For(2f).Set("_Tint", Color.cyan).Set("_Scale", 1.5f));
```

## The samples

`specs\` holds one spec per mod that already uses the library; the preset names follow each mod's prefix so
they drop straight into its wrapper and `ShaderEffects.xml`:

| Spec | Bundle | Presets |
|---|---|---|
| `broodmother.particles.json` | `bm_fx` | `BM_SporeBurst` (rising green spores), `BM_ChitinShards` (falling shell streaks), `BM_WebDrift` (cell-snapped grey glyphs drifting sideways) |
| `space_time_vortex.particles.json` | `istv_fx` | `ISTV_AccretionDust` (sparks spiralling into the anchor, with refraction), `ISTV_RuptureEmbers` (outward embers), `ISTV_CollapseShards` (streaks collapsing inward) |
| `telekinesis_throw.particles.json` | `tkt_fx` | `TKT_PsiMotes` (orbiting violet motes), `TKT_ShrapnelSparks` (gravity sparks) |
| `mountwright.particles.json` | `mw_fx` | `MW_DustKick` (opaque dust puff), `MW_HoofSparks` |
| `truecolor_status.particles.json` | `tcs_fx` | `TCS_BloodMotes` (red motes rising around the player) |

Wiring a preset into a mod is one line at the moment it belongs to, for example in Broodmother's
`Arendeth_Broodmother_Gestation.cs` next to `BM_Birth`:

```csharp
BroodmotherShaderFX.Play("BM_SporeBurst", targetCell);
```

The wrappers already no-op when the option is off or no shaders loaded, and an unknown preset name only logs.

## How the shaders work

There is no particle system: the fragment shader loops over `_Count` slots and derives each particle from its
index and the library's clock (`hash` from `QudFX.cginc`), so a particle's position at any time is a closed
form (birth point + heading × speed × drag integral + ½ gravity t², then swirl, wobble, cell snap). The kernel
is evaluated for the pixel, the contributions are accumulated (colour, coverage, a displacement vector for
`distort`), and the map is read once at the displaced position. `_Amt` (strength × fades) scales the result,
so the library's envelope, `Strength()` and `Amount` all apply.

Costs scale with count × pixels; the samples run 24 to 96 particles. `[loop]` with an early break keeps unused
slots cheap.

## Troubleshooting

- **Nothing plays** - wish `shader`: the status line says whether the bundle loaded. `ShaderEffects.xml` is
  read once per launch; restart after installing. Bundle names must be lower case.
- **"wouldn't load; it may have been built with a different Unity version"** - the game moved to a new Unity;
  `Build-QudShaderBundle.ps1` resolves the editor from the game binary, install that version in Unity Hub and
  rebuild.
- **Mac/Linux players see nothing** - only `windowsstandalonesupport` is installed; add the macOS/Linux build
  support modules to the editor and rebuild, the script picks them up.
- **Lint passes but Unity fails** - lint uses a stub `UnityCG.cginc`; the Unity log
  (`Tools\Logs\QudShaderBundle_*.log`) has the real message, printed as `QUDFX shader error in ...`.
- **Preview looks different from the game** - the preview is a numpy re-implementation at 480×225 on a
  synthetic map; give it a real map with `--mapshot` (wish `shader mapshot` writes one to the save folder).

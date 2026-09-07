# Magi-Tech asset generation libraries — Transcendence Tools/Starbound

These libraries used to ship inside the OpenStarbound mod. Offline generation
belongs in the toolchain so the mod only contains game assets + thin shims.

Sprite backends for Magi-Tech item sheets: **SD** (`produce_unity_still_animations.py`)
and **Pixelorama** (`produce_pixelorama_sheets.py` / `-Backend pixelorama`).
3D turntable bake is `libs/mesh_to_sprite.py` plus this `mesh_to_sprite/` tree.

## Layout

| Path | Origin in the mod |
|---|---|
| `libs/` | Python ports of unimplemented C++ assemblers / hitbox gen / Lua tools |
| `cpp_generators/GeneratorAgent/` | `cpp_backend/agents/GeneratorAgent` |
| `cpp_generators/mesh_to_sprite/` | `cpp_backend/core/animation/MeshToSpritePipeline.*` |
| `lua_tools/` | `scripts/tools/*.lua` + `OllamaLuaHelper.lua` |
| `python_pipeline/` | already here (rectpack AtlasPacker) |

## Python libraries (`libs/`)

- **spritesheet_assembler.py** — `SpritesheetAssembler` (HORIZONTAL / GRID / CUSTOM rectpack)
- **hitbox_generator.py** — implements `MechHitboxGenerator` (C++ was a stub)
- **asset_packer.py** — assetPacker / generateManifest / jsonToBinary / chunkJson
- **mesh_to_sprite.py** — wrap stills or Blender into Starbound sheets

```powershell
python .\generate_mech_hitboxes.py --mod-path "F:\Games\OpenStarbound\mods\Magi-Tech Arcane Alchemy and Sorcery"
python .\libs\asset_packer.py manifest "F:\Games\OpenStarbound\mods\Magi-Tech Arcane Alchemy and Sorcery"
```

`Pack-UnityStillsToStarbound.ps1` now packs idle sheets, expands action cycles,
and writes mech/minion `.hitbox.json` files.

## C++ in the mod

`cpp_backend/CMakeLists.txt` globs `cpp_generators` when this folder exists so
in-game type shims (`core/modules/*_asset_generator`) still compile.

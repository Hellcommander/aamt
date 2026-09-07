# Magi-Tech Lua generation helpers (offline copies)

Canonical Python ports: `Tools/Starbound/libs/asset_packer.py`

| Lua | Python |
|---|---|
| assetPacker.lua | `python libs/asset_packer.py pack <dir> <out>` |
| generateManifest.lua | `python libs/asset_packer.py manifest <mod>` |
| jsonToBinary.lua | `python libs/asset_packer.py json-bin <in.json> <out>` |
| chunkJson.lua | `python libs/asset_packer.py chunk <in.json> <dir>` |
| OllamaLuaHelper.lua | Tools/Starbound/OllamaCppBridge.ps1 |

The mod keeps `scripts/tools/*.lua` so in-game `require("/scripts/tools/...")` still works.

# arzedit (toolset)

CLI ARZ/ARC builder from [QuasiMod/arzedit](https://gitlab.com/QuasiMod/arzedit) v0.2b5.

| Path | Role |
|------|------|
| `arzedit/arzedit-master/` | Upstream source |
| `arzedit/toolset/arzedit.csproj` | SDK-style net48 build (no VS 4.5.2 targeting pack) |
| `bin/arzedit.exe` | Built binary used by GD tools |

## Rebuild binary

```bat
Build-Arzedit.bat
```

## Build mod databases

```bat
Run-GdBuildArz.bat
REM or:
python build_mod_arz.py
python build_mod_arz.py --target survival
python build_mod_arz.py --target campaign
python build_mod_arz.py --target staging
python build_mod_arz.py --mod NydiamarIntegrated
```

Direct:

```bat
bin\arzedit.exe build "D:\games\Steam\steamapps\common\Grim Dawn\survivalmode4" -g "D:\games\Steam\steamapps\common\Grim Dawn" -A -R
```

`-A` skip assets, `-R` skip packing resource folders (DB-only).

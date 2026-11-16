@echo off
setlocal
cd /d "%~dp0"
set "PY=D:\Python\Python314\python.exe"
if not exist "%PY%" set "PY=python"
set "PYTHONIOENCODING=utf-8"
rem Where every asset job stands. Starts nothing.
echo ===== system models  (glb=0 or fbx=0: run elin_assets_system_meshes.bat)
"%PY%" elin_trellis_unity.py status
echo ===== portraits  (any listed: run elin_assets_portraits.bat)
"%PY%" elin_generate_portraits.py --list
echo ===== audio  (missing clips: run elin_assets_spell_audio.bat)
"%PY%" elin_deploy_real_audio.py --summary
echo ===== creature paperdolls  (tiles not at deploy: run creature_paperdolls_fast_all.bat, about an hour)
"%PY%" elin_creature_paperdolls.py status
pause

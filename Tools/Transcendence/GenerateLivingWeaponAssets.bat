@echo off
REM Living weapons — same pipeline as CrossMod ships (PBR → mesh → ortho)
cd /d "%~dp0"
set OUT=%1
if "%OUT%"=="" set OUT=C:\Output\LivingWeaponAssets
python generate_living_weapon_assets.py --out-dir "%OUT%" --deploy-resources %2 %3 %4 %5
exit /b %ERRORLEVEL%

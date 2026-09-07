@echo off
REM Magi-Tech draft → reference → final pipeline
REM Example:
REM   Generate-MagiTechSpellPipeline.bat vortexTwister "arcane dust twister spell"

set MOD=F:\Games\OpenStarbound\mods\Magi-Tech Arcane Alchemy and Sorcery
set ASSET=%~1
set THEME=%~2

if "%ASSET%"=="" set ASSET=vortexTwister
if "%THEME%"=="" set THEME=arcane dust twister spell, swirling funnel, magitech

pwsh -NoProfile -ExecutionPolicy Bypass -File "%~dp0Generate-MagiTechSpellPipeline.ps1" ^
  -ModPath "%MOD%" ^
  -AssetId "%ASSET%" ^
  -Theme "%THEME%" ^
  -Kind spell ^
  -IconsOnly ^
  -AutoStartSd

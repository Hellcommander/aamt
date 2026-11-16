@echo off
setlocal
cd /d "%~dp0"
rem Every asset job, one after another: the quick ones first, creature bodies and motion last (days of GPU time).
rem Each job keeps what is already made, so this can be stopped and started again.
set ELIN_ASSETS_NOPAUSE=1
call elin_assets_portraits.bat
call elin_assets_system_art.bat
call elin_assets_spell_effects.bat
call elin_assets_spell_art.bat
call elin_assets_spell_audio.bat
call elin_assets_system_meshes.bat
call creature_paperdolls_fast_all.bat
set ELIN_ASSETS_NOPAUSE=
call creature_paperdolls_everything.bat

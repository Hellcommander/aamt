@echo off
REM Generate weapon-fire and magic-cast animation assets for mech forms
pwsh -NoProfile -ExecutionPolicy Bypass -File "%~dp0GenerateMechWeaponMagicAnimations.ps1" %*

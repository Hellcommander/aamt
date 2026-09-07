@echo off
REM Generate assets for Moving Floating Dungeon Generator system
pwsh -NoProfile -ExecutionPolicy Bypass -File "%~dp0GenerateFloatingDungeonAssets.ps1" %*

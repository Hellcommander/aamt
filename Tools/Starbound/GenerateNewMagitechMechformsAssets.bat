@echo off
REM Generate assets for all new Magitech Mechforms
REM This script generates assets for: Aether Warden, Flux Strider, Iron Bloom, Null Harrier, Shardwright, Helix Bastion

pwsh -NoProfile -ExecutionPolicy Bypass -File "%~dp0GenerateNewMagitechMechformsAssets.ps1" %*

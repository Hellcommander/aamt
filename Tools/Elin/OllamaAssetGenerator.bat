@echo off
REM Batch wrapper for OllamaAssetGenerator.ps1
REM Reads settings from OllamaAssetGenerator.config.json
REM Can be run with no arguments - just double-click!

setlocal enabledelayedexpansion

set SCRIPT_DIR=%~dp0
set SCRIPT_NAME=OllamaAssetGenerator.ps1
set CONFIG_FILE=%SCRIPT_DIR%OllamaAssetGenerator.config.json

REM Check if PowerShell script exists
if not exist "%SCRIPT_DIR%%SCRIPT_NAME%" (
    echo ========================================
    echo ERROR: Script not found!
    echo ========================================
    echo.
    echo %SCRIPT_NAME% not found in:
    echo %SCRIPT_DIR%
    echo.
    pause
    exit /b 1
)

REM Default values (used if config file doesn't exist)
set DEFAULT_MOD_PATH=E:\SteamLibrary\steamapps\common\Elin\Package\Mod\CustomRaceClassCreator
set DEFAULT_ASSET_TYPES=all
set DEFAULT_SYSTEMS=all
set DEFAULT_QUALITY=high
set DEFAULT_GEN_SPRITESHEETS=True
set DEFAULT_USE_OLLAMA=True

REM Read config file if it exists, otherwise use defaults
if exist "%CONFIG_FILE%" (
    REM Use PowerShell to read JSON config
    for /f "tokens=*" %%a in ('powershell.exe -NoProfile -Command "$c = Get-Content '%CONFIG_FILE%' -Raw | ConvertFrom-Json; if ($c.modPath) { $c.modPath } else { '%DEFAULT_MOD_PATH%' }"') do set MOD_PATH=%%a
    for /f "tokens=*" %%a in ('powershell.exe -NoProfile -Command "$c = Get-Content '%CONFIG_FILE%' -Raw | ConvertFrom-Json; if ($c.assetTypes) { $c.assetTypes } else { '%DEFAULT_ASSET_TYPES%' }"') do set ASSET_TYPES=%%a
    for /f "tokens=*" %%a in ('powershell.exe -NoProfile -Command "$c = Get-Content '%CONFIG_FILE%' -Raw | ConvertFrom-Json; if ($c.systems) { $c.systems } else { '%DEFAULT_SYSTEMS%' }"') do set SYSTEMS=%%a
    for /f "tokens=*" %%a in ('powershell.exe -NoProfile -Command "$c = Get-Content '%CONFIG_FILE%' -Raw | ConvertFrom-Json; if ($c.quality) { $c.quality } else { '%DEFAULT_QUALITY%' }"') do set QUALITY=%%a
    for /f "tokens=*" %%a in ('powershell.exe -NoProfile -Command "$c = Get-Content '%CONFIG_FILE%' -Raw | ConvertFrom-Json; if ($c.generateSpritesheets) { $c.generateSpritesheets } else { '%DEFAULT_GEN_SPRITESHEETS%' }"') do set GEN_SPRITESHEETS=%%a
    for /f "tokens=*" %%a in ('powershell.exe -NoProfile -Command "$c = Get-Content '%CONFIG_FILE%' -Raw | ConvertFrom-Json; if ($c.useOllama) { $c.useOllama } else { '%DEFAULT_USE_OLLAMA%' }"') do set USE_OLLAMA=%%a
) else (
    REM Use defaults if config file doesn't exist
    set MOD_PATH=%DEFAULT_MOD_PATH%
    set ASSET_TYPES=%DEFAULT_ASSET_TYPES%
    set SYSTEMS=%DEFAULT_SYSTEMS%
    set QUALITY=%DEFAULT_QUALITY%
    set GEN_SPRITESHEETS=%DEFAULT_GEN_SPRITESHEETS%
    set USE_OLLAMA=%DEFAULT_USE_OLLAMA%
    echo ========================================
    echo INFO: Using default settings
    echo ========================================
    echo Config file not found, using defaults.
    echo Create OllamaAssetGenerator.config.json to customize.
    echo.
)

REM Allow command line override
if not "%~1"=="" set MOD_PATH=%~1
if not "%~2"=="" set ASSET_TYPES=%~2
if not "%~3"=="" set SYSTEMS=%~3
if not "%~4"=="" set QUALITY=%~4

REM Ensure values are set
if "%MOD_PATH%"=="" set MOD_PATH=%DEFAULT_MOD_PATH%
if "%ASSET_TYPES%"=="" set ASSET_TYPES=%DEFAULT_ASSET_TYPES%
if "%SYSTEMS%"=="" set SYSTEMS=%DEFAULT_SYSTEMS%
if "%QUALITY%"=="" set QUALITY=%DEFAULT_QUALITY%
if "%GEN_SPRITESHEETS%"=="" set GEN_SPRITESHEETS=%DEFAULT_GEN_SPRITESHEETS%
if "%USE_OLLAMA%"=="" set USE_OLLAMA=%DEFAULT_USE_OLLAMA%

echo ========================================
echo Ollama Asset Generator
echo ========================================
if exist "%CONFIG_FILE%" (
    echo Config: OllamaAssetGenerator.config.json
) else (
    echo Config: Using defaults
)
echo Mod Path: %MOD_PATH%
echo Asset Types: %ASSET_TYPES%
echo Systems: %SYSTEMS%
echo Quality: %QUALITY%
echo Spritesheets: %GEN_SPRITESHEETS%
echo Ollama: %USE_OLLAMA%
echo ========================================
echo.

REM Set flags based on config
set GEN_SPRITESHEETS_FLAG=
set USE_OLLAMA_FLAG=
if /i "%GEN_SPRITESHEETS%"=="True" set GEN_SPRITESHEETS_FLAG=-GenerateSpritesheets
if /i "%USE_OLLAMA%"=="True" set USE_OLLAMA_FLAG=-UseOllama

REM Change to script directory and run PowerShell script
cd /d "%SCRIPT_DIR%"
powershell.exe -ExecutionPolicy Bypass -NoProfile -File "%SCRIPT_NAME%" -ModPath "%MOD_PATH%" -AssetTypes "%ASSET_TYPES%" -Systems "%SYSTEMS%" -Quality "%QUALITY%" %GEN_SPRITESHEETS_FLAG% %USE_OLLAMA_FLAG%
set EXIT_CODE=%ERRORLEVEL%

echo.
echo ========================================
if !EXIT_CODE! EQU 0 (
    echo [SUCCESS] Generation completed successfully!
) else (
    echo [ERROR] Generation completed with errors
    echo Exit code: !EXIT_CODE!
    echo.
    echo Please check the output above for error details.
)
echo ========================================
echo.
echo Press any key to close this window...
pause >nul

endlocal
exit /b %EXIT_CODE%

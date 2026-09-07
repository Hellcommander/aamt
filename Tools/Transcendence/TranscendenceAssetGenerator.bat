@echo off
REM Transcendence Asset Generator - Batch Launcher
REM Drag and drop asset config JSON files here, or run with parameters

if "%~1"=="" (
    echo Transcendence Asset Generator
    echo.
    echo Usage:
    echo   TranscendenceAssetGenerator.bat [AssetType] [AssetName] [Description]
    echo.
    echo Examples:
    echo   TranscendenceAssetGenerator.bat Ship MyShip "A fast scout ship"
    echo   TranscendenceAssetGenerator.bat Weapon QuantumChamber "Quantum weapon chamber"
    echo.
    echo Or drag a JSON config file onto this batch file.
    echo.
    pause
    exit /b
)

setlocal

REM Check if argument is a JSON file
echo %~1 | findstr /i "\.json$" >nul
if %errorlevel%==0 (
    REM JSON config file provided
    pwsh.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0TranscendenceAssetGenerator.ps1" -ConfigFile "%~1"
) else (
    REM Command line parameters
    set ASSET_TYPE=%~1
    set ASSET_NAME=%~2
    set ASSET_DESC=%~3
    
    if "%ASSET_TYPE%"=="" (
        echo ERROR: AssetType required
        pause
        exit /b 1
    )
    
    if "%ASSET_NAME%"=="" (
        echo ERROR: AssetName required
        pause
        exit /b 1
    )
    
    pwsh.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0TranscendenceAssetGenerator.ps1" -AssetType "%ASSET_TYPE%" -AssetName "%ASSET_NAME%" -Description "%ASSET_DESC%"
)

endlocal


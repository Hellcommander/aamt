@echo off
REM Mod Fixer Launcher
REM Quick launcher for the Ollama-assisted mod fixer

setlocal

REM Check for Python
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python not found. Please install Python 3.8+
    pause
    exit /b 1
)

REM Check for required packages
python -c "import yaml, requests" >nul 2>&1
if errorlevel 1 (
    echo Installing required packages...
    pip install pyyaml requests
    if errorlevel 1 (
        echo Error: Failed to install required packages
        pause
        exit /b 1
    )
)

REM Check for Ollama
curl -s http://localhost:11434/api/tags >nul 2>&1
if errorlevel 1 (
    echo Warning: Ollama not detected at http://localhost:11434
    echo Please ensure Ollama is running.
    echo.
)

REM Get script directory
set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

REM Check if mod path provided
if "%~1"=="" (
    echo Mod Fixer - Ollama-Assisted Mod Fixing
    echo.
    echo Usage: %~nx0 ^<mod_path^> [options]
    echo.
    echo Examples:
    echo   %~nx0 "C:\Games\ToME\mods\my_mod" --profile tome --issue "missing sprite"
    echo   %~nx0 "C:\Games\ToME\mods\my_mod" --profile tome --issue "syntax error" --template fix_syntax_error
    echo   %~nx0 "C:\Games\ToME\mods\my_mod" --profile tome --issue "balance issue" --apply
    echo.
    echo Options:
    echo   --profile ^<name^>        Profile name (tome, unity, minecraft_fabric)
    echo   --issue ^<description^>    Issue description
    echo   --template ^<name^>        Prompt template name
    echo   --apply                    Apply fix (default: dry-run)
    echo   --output-report ^<file^>   Save fix report to file
    echo   --ollama-url ^<url^>       Ollama URL (default: http://localhost:11434)
    echo.
    pause
    exit /b 0
)

REM Run mod fixer
python mod_fixer.py %*

if errorlevel 1 (
    echo.
    echo Error: Mod fixer failed. Check the output above.
    pause
    exit /b 1
)

endlocal


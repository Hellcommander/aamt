@echo off
REM ToME Mod Checker Launcher
REM AI-Assisted Modding Tools (AAMT) - ToME Toolset
REM Launches the GUI with drag and drop support

echo ToME Mod Checker and Fixing Assistant
echo AI-Assisted Modding Tools (AAMT)
echo ======================================
echo.

set SCRIPT_DIR=%~dp0

REM Check tools using AAMT unified detection
powershell -ExecutionPolicy Bypass -File "%SCRIPT_DIR%InitializeToMETools.ps1" -RequiredTools @("Python") -OptionalTools @("Ollama") >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Checking tools...
    powershell -ExecutionPolicy Bypass -File "%SCRIPT_DIR%InitializeToMETools.ps1" -RequiredTools @("Python") -OptionalTools @("Ollama")
    echo.
    echo NOTE: Ollama is optional but recommended for AI-assisted fixing
    echo.
)

REM Get Python path from tool detection
for /f "delims=" %%i in ('powershell -Command "(Import-Module '%SCRIPT_DIR%..\Shared\ToolDetection.psm1' -ErrorAction SilentlyContinue; Get-PythonPath)"') do set PYTHON_PATH=%%i

if defined PYTHON_PATH (
    set "PYTHON_CMD=%PYTHON_PATH%"
) else (
    REM Fallback to PATH detection
    python --version >nul 2>&1
    if errorlevel 1 (
        echo ERROR: Python not found!
        echo Please install Python 3.7+ and add it to PATH
        pause
        exit /b 1
    )
    set "PYTHON_CMD=python"
)

REM Check for tkinterdnd2
%PYTHON_CMD% -c "import tkinterdnd2" >nul 2>&1
if errorlevel 1 (
    echo WARNING: tkinterdnd2 not installed
    echo Drag and drop will be disabled
    echo Install with: pip install tkinterdnd2
    echo.
)

REM Check for Ollama using unified detection
powershell -Command "(Import-Module '%SCRIPT_DIR%..\Shared\ToolDetection.psm1' -ErrorAction SilentlyContinue; if (Test-OllamaAvailable) { Write-Host 'INFO: Ollama detected - AI fixing features enabled' } else { Write-Host 'INFO: Ollama not detected - AI fixing features will be disabled'; Write-Host 'To enable: Start Ollama (ollama serve) and pull codellama:34b' }" 2>nul
echo.

REM Launch GUI
echo Launching ToME Mod Checker GUI...
echo.
%PYTHON_CMD% "%SCRIPT_DIR%tome_mod_checker_gui.py"

if errorlevel 1 (
    echo.
    echo ERROR: Failed to launch GUI
    pause
    exit /b 1
)

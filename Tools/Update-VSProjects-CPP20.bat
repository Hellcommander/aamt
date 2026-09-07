@echo off
REM ============================================================================
REM Update-VSProjects-CPP20.bat - Drag-and-drop wrapper
REM ============================================================================
REM Updates Visual Studio project files to use C++20 standard
REM 
REM Usage: Drag and drop API folder(s) or .vcxproj file(s) onto this .bat file
REM ============================================================================

setlocal

REM Get the directory where this batch file is located
set "SCRIPT_DIR=%~dp0"
set "PS_SCRIPT=%SCRIPT_DIR%Update-VSProjects-CPP20.ps1"

REM Check if PowerShell script exists
if not exist "%PS_SCRIPT%" (
    echo ERROR: PowerShell script not found: %PS_SCRIPT%
    echo.
    pause
    exit /b 1
)

REM Launch PowerShell script, passing all arguments (%* passes all dropped files)
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%PS_SCRIPT%" %*

REM Store exit code
set "EXIT_CODE=%ERRORLEVEL%"

REM Always pause so user can see results
echo.
if %EXIT_CODE% EQU 0 (
    echo Script completed successfully.
) else (
    echo Script exited with error code: %EXIT_CODE%
)
echo.
echo Press any key to close this window...
pause >nul

if %EXIT_CODE% NEQ 0 (
    exit /b %EXIT_CODE%
)

endlocal

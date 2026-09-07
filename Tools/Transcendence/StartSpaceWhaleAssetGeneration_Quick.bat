@echo off
REM ============================================================
REM Start Space Whale Asset Generation - Quick Launch
REM ============================================================
REM Quick launcher without prompts - uses default settings
REM ============================================================

setlocal

set "SCRIPT_DIR=%~dp0"

REM Launch the main batch file with default settings
call "%SCRIPT_DIR%StartSpaceWhaleAssetGeneration.bat"

endlocal


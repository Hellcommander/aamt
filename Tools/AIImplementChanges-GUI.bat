@echo off
REM ============================================================
REM AIImplementChanges-GUI - Launcher with STA mode
REM Supports drag and drop: drag files/folders onto this batch file
REM ============================================================

setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"

REM Check if files/folders were dropped (drag and drop)
set "DROPPED_PATH="
set "LOG_FILE="
set "DROPPED_COUNT=0"

REM Count dropped items and identify folder vs log file
if not "%~1"=="" (
    set "ITEM1=%~1"
    if exist "!ITEM1!" (
        set /a DROPPED_COUNT+=1
        if exist "!ITEM1!\" (
            REM It's a folder
            set "DROPPED_PATH=!ITEM1!"
        ) else (
            REM It's a file - check if it's a log file
            for %%F in ("!ITEM1!") do (
                set "EXT=%%~xF"
                if /i "!EXT!"==".txt" set "LOG_FILE=!ITEM1!"
                if /i "!EXT!"==".log" set "LOG_FILE=!ITEM1!"
                REM If not a log file, use parent directory
                if not defined LOG_FILE (
                    for %%D in ("!ITEM1!") do set "DROPPED_PATH=%%~dpD"
                    set "DROPPED_PATH=!DROPPED_PATH:~0,-1!"
                )
            )
        )
    )
)

REM Check for second dropped item (log file or folder)
if not "%~2"=="" (
    set "ITEM2=%~2"
    if exist "!ITEM2!" (
        set /a DROPPED_COUNT+=1
        if exist "!ITEM2!\" (
            REM It's a folder - use it if we don't have one yet
            if not defined DROPPED_PATH set "DROPPED_PATH=!ITEM2!"
        ) else (
            REM It's a file - check if it's a log file
            for %%F in ("!ITEM2!") do (
                set "EXT=%%~xF"
                if /i "!EXT!"==".txt" set "LOG_FILE=!ITEM2!"
                if /i "!EXT!"==".log" set "LOG_FILE=!ITEM2!"
                REM If not a log file and we don't have a path yet, use parent directory
                if not defined LOG_FILE if not defined DROPPED_PATH (
                    for %%D in ("!ITEM2!") do set "DROPPED_PATH=%%~dpD"
                    set "DROPPED_PATH=!DROPPED_PATH:~0,-1!"
                )
            )
        )
    )
)

echo.
echo ========================================
echo  AI Code Change Implementation - GUI
echo ========================================
echo.

if not "!DROPPED_PATH!"=="" (
    echo Drag and drop detected: !DROPPED_PATH!
    if not "!LOG_FILE!"=="" (
        echo Log file detected: !LOG_FILE!
        echo.
        echo Launching GUI with dropped path and log file...
        echo Will implement changes from log file one by one.
        echo.
        REM Launch in STA mode with -Path and -LogFile parameters
        powershell -STA -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%AIImplementChanges-GUI.ps1" -Path "!DROPPED_PATH!" -LogFile "!LOG_FILE!"
    ) else (
        echo.
        echo Launching GUI with dropped path...
        echo.
        REM Launch in STA mode with -Path parameter
        powershell -STA -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%AIImplementChanges-GUI.ps1" -Path "!DROPPED_PATH!"
    )
) else (
    echo Launching GUI window in STA mode...
    echo.
    echo Tip: You can drag and drop files or folders onto this batch file!
    echo Tip: Drop both a folder AND a .txt/.log file to implement changes from log!
    echo.
    REM Launch in STA mode (required for Windows Forms)
    powershell -STA -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%AIImplementChanges-GUI.ps1" %*
)

if %ERRORLEVEL% neq 0 (
    echo.
    echo Error occurred. Press any key to exit...
    pause >nul
)

endlocal


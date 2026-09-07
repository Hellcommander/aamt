#!/usr/bin/env python3
"""Create the batch file with proper formatting"""

lines = [
    '@echo off',
    'setlocal enabledelayedexpansion',
    'set SCRIPT_DIR=%~dp0',
    'set PS_SCRIPT=%SCRIPT_DIR%CustomRaceClassCreatorAssetGenerator.ps1',
    '',
    'if not exist "%PS_SCRIPT%" (',
    '    echo ERROR: PowerShell script not found',
    '    pause',
    '    exit /b 1',
    ')',
    '',
    'if "%~1"=="" (',
    '    echo Usage: %~nx0 "MOD_PATH"',
    '    echo Or drag the mod folder onto this batch file.',
    '    pause',
    '    exit /b 0',
    ')',
    '',
    'set "MOD_PATH=%~1"',
    '',
    'if not exist "!MOD_PATH!" (',
    '    echo ERROR: Mod path does not exist: !MOD_PATH!',
    '    pause',
    '    exit /b 1',
    ')',
    '',
    'echo.',
    'echo Mod Path: !MOD_PATH!',
    'echo.',
    '',
    'pwsh -NoProfile -ExecutionPolicy Bypass -File "%PS_SCRIPT%" -ModPath "!MOD_PATH!"',
    '',
    'set EXIT_CODE=%ERRORLEVEL%',
    'if %EXIT_CODE% NEQ 0 (',
    '    echo.',
    '    echo Script exited with error code: %EXIT_CODE%',
    '    pause',
    ') else (',
    '    echo.',
    '    echo Generation completed successfully!',
    '    timeout /t 3 >nul',
    ')',
    '',
    'endlocal',
    'exit /b %EXIT_CODE%'
]

with open('CustomRaceClassCreatorAssetGenerator.bat', 'w', encoding='ascii', newline='') as f:
    f.write('\r\n'.join(lines))

print("Batch file created successfully!")

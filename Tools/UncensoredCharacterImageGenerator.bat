@echo off
REM UncensoredCharacterImageGenerator.bat
REM Batch wrapper for UncensoredCharacterImageGenerator.ps1
REM Generates character images handling ANY content that might be blocked

setlocal enabledelayedexpansion

REM Default values
set "DESCRIPTION="
set "CHARACTER_NAME=Character"
set "GAME_TYPE=Generic"
set "MUTATIONS="
set "TRAITS="
set "WIDTH=1024"
set "HEIGHT=1024"
set "OUTPUT_PATH="
set "STABLE_DIFFUSION_URL=http://localhost:8000"
set "SKIP_ENHANCEMENT="
set "VERBOSE="

REM Parse arguments
:parse_args
if "%~1"=="" goto :run
if /i "%~1"=="--description" (
    set "DESCRIPTION=%~2"
    shift
    shift
    goto :parse_args
)
if /i "%~1"=="--name" (
    set "CHARACTER_NAME=%~2"
    shift
    shift
    goto :parse_args
)
if /i "%~1"=="--game" (
    set "GAME_TYPE=%~2"
    shift
    shift
    goto :parse_args
)
if /i "%~1"=="--mutations" (
    set "MUTATIONS=%~2"
    shift
    shift
    goto :parse_args
)
if /i "%~1"=="--traits" (
    set "TRAITS=%~2"
    shift
    shift
    goto :parse_args
)
if /i "%~1"=="--width" (
    set "WIDTH=%~2"
    shift
    shift
    goto :parse_args
)
if /i "%~1"=="--height" (
    set "HEIGHT=%~2"
    shift
    shift
    goto :parse_args
)
if /i "%~1"=="--output" (
    set "OUTPUT_PATH=%~2"
    shift
    shift
    goto :parse_args
)
if /i "%~1"=="--sd-url" (
    set "STABLE_DIFFUSION_URL=%~2"
    shift
    shift
    goto :parse_args
)
if /i "%~1"=="--skip-enhancement" (
    set "SKIP_ENHANCEMENT=-SkipEnhancement"
    shift
    goto :parse_args
)
if /i "%~1"=="--verbose" (
    set "VERBOSE=-Verbose"
    shift
    goto :parse_args
)
shift
goto :parse_args

:run
if "%DESCRIPTION%"=="" (
    echo Error: --description is required
    echo.
    echo Usage:
    echo   UncensoredCharacterImageGenerator.bat --description "Character description" [options]
    echo.
    echo Options:
    echo   --description "text"     Character description (required)
    echo   --name "name"            Character name (default: Character)
    echo   --game "type"            Game type: RimWorld, CDDA, Qud, Generic (default: Generic)
    echo   --mutations "m1,m2"     Comma-separated mutations
    echo   --traits "t1,t2"         Comma-separated traits (medical, disabilities, etc.)
    echo   --width 1024            Image width (default: 1024)
    echo   --height 1024           Image height (default: 1024)
    echo   --output "path"         Output file path (default: auto-generated)
    echo   --sd-url "url"          Stable Diffusion API URL (default: http://localhost:8000)
    echo   --skip-enhancement      Skip Ollama enhancement
    echo   --verbose               Verbose output
    echo.
    echo Examples:
    echo   UncensoredCharacterImageGenerator.bat --description "Elder Irudad" --name "Elder Irudad" --game "Qud" --mutations "Multiple Arms,Chimera,Stinger"
    echo   UncensoredCharacterImageGenerator.bat --description "Adult character" --traits "Incontinent,Wheelchair User" --game "RimWorld"
    exit /b 1
)

REM Build PowerShell command
set "PS_CMD=powershell -ExecutionPolicy Bypass -File"
set "SCRIPT_PATH=%~dp0UncensoredCharacterImageGenerator.ps1"

REM Verify script exists
if not exist "%SCRIPT_PATH%" (
    echo Error: PowerShell script not found: %SCRIPT_PATH%
    exit /b 1
)

set "CMD=%PS_CMD% "%SCRIPT_PATH%" -Description "%DESCRIPTION%" -CharacterName "%CHARACTER_NAME%" -GameType "%GAME_TYPE%" -Width %WIDTH% -Height %HEIGHT%"

if not "%MUTATIONS%"=="" (
    REM Convert comma-separated to array - pass as single string, PowerShell will split it
    set "CMD=!CMD! -Mutations "%MUTATIONS%""
)

if not "%TRAITS%"=="" (
    REM Convert comma-separated to array - pass as single string, PowerShell will split it
    set "CMD=!CMD! -Traits "%TRAITS%""
)

if not "%OUTPUT_PATH%"=="" (
    set "CMD=!CMD! -OutputPath "%OUTPUT_PATH%""
)

if not "%STABLE_DIFFUSION_URL%"=="http://localhost:8000" (
    set "CMD=!CMD! -StableDiffusionUrl "%STABLE_DIFFUSION_URL%""
)

if defined SKIP_ENHANCEMENT (
    set "CMD=!CMD! %SKIP_ENHANCEMENT%"
)

if defined VERBOSE (
    set "CMD=!CMD! %VERBOSE%"
)

REM Run PowerShell script
echo Executing: !CMD!
echo.
!CMD!
set "EXIT_CODE=%ERRORLEVEL%"
if not "%EXIT_CODE%"=="0" (
    echo.
    echo Error: Script exited with code %EXIT_CODE%
    pause
    exit /b %EXIT_CODE%
)

endlocal

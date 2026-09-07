@echo off
REM Test-ElderIrudad.bat
REM Test script for generating the "Elder Irudad" mutant elder character image
REM This tests the uncensored image generator with a complex body horror description
REM 
REM Usage:
REM   Test-ElderIrudad.bat [options]
REM
REM Options:
REM   --ai-enhancement    Enable AI image enhancement
REM   --regenerate        Regenerate with AI improvements
REM   --width <pixels>     Image width (default: 1024)
REM   --height <pixels>    Image height (default: 1024)
REM   --help              Show this help message

setlocal EnableDelayedExpansion

REM Set script directory
cd /d "%~dp0"

REM Default values
set "ENABLE_AI="
set "REGENERATE="
set "WIDTH=1024"
set "HEIGHT=1024"

REM Parse command line arguments
:parse_args
if "%~1"=="" goto :start
if /i "%~1"=="--ai-enhancement" (
    set "ENABLE_AI=-AIEnhancement"
    shift
    goto :parse_args
)
if /i "%~1"=="--regenerate" (
    set "REGENERATE=-RegenerateImproved"
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
if /i "%~1"=="--help" (
    echo.
    echo Test-ElderIrudad.bat - Test script for Elder Irudad image generation
    echo.
    echo Usage:
    echo   Test-ElderIrudad.bat [options]
    echo.
    echo Options:
    echo   --ai-enhancement    Enable AI image enhancement
    echo   --regenerate        Regenerate with AI improvements
    echo   --width ^<pixels^>     Image width (default: 1024)
    echo   --height ^<pixels^>    Image height (default: 1024)
    echo   --help              Show this help message
    echo.
    pause
    exit /b 0
)
shift
goto :parse_args

:start
echo ========================================
echo Testing Elder Irudad Image Generation
echo ========================================
echo.

REM Display configuration
echo Configuration:
echo   Character: Elder Irudad
echo   Game Type: Caves of Qud
echo   Mutations: Multiple Arms, Chimera, Stinger
echo   Traits: Body Horror, Multiple Faces
echo   Resolution: %WIDTH%x%HEIGHT%
if defined ENABLE_AI (
    echo   AI Enhancement: Enabled
    if defined REGENERATE (
        echo   Regenerate Improved: Enabled
    )
) else (
    echo   AI Enhancement: Disabled
)
echo.

REM Build the description (using a variable to handle long text)
set "DESC=A warm smile spreads over an old face freckled by time and a million crumbs of salt. He shrinks under a hunched back and drums the ground beneath him with a short and barb-crowned tail. A second pair of arms rise over the slump of his shoulders, where hands meet and fingers lace to form another face, this one vacant and prehistoric, no mouth and eyes desert-white."

echo Starting image generation...
echo.

REM Run the PowerShell script
REM NOTE: Use -Command so PowerShell can parse @(...) arrays correctly.
powershell -NoProfile -ExecutionPolicy Bypass -Command "& { $env:DESC = '%DESC%'; & '.\\UncensoredCharacterImageGenerator.ps1' -Description $env:DESC -CharacterName 'Elder Irudad' -GameType 'Qud' -Mutations @('Multiple Arms','Chimera','Stinger') -Traits @('Body Horror','Multiple Faces') -Width %WIDTH% -Height %HEIGHT% %ENABLE_AI% %REGENERATE% -Verbose }"

REM Check exit code
set "EXIT_CODE=%ERRORLEVEL%"
echo.
if %EXIT_CODE% EQU 0 (
    echo ========================================
    echo Test completed successfully!
    echo ========================================
    echo.
    echo Generated files should be in the output directory.
    echo Look for files named: Elder_Irudad*.png
    if defined ENABLE_AI (
        echo.
        echo AI analysis file: Elder_Irudad*_ai_analysis.txt
        if defined REGENERATE (
            echo Improved version: Elder_Irudad*_improved.png
        )
    )
) else (
    echo ========================================
    echo Test failed with error code: %EXIT_CODE%
    echo ========================================
    echo.
    echo Troubleshooting:
    echo   1. Ensure Stable Diffusion API is running: http://localhost:8000
    echo   2. Ensure Ollama is running: http://localhost:11434
    if defined ENABLE_AI (
        echo   3. Check that vision models are installed: ollama pull llava:latest
    )
    echo   4. Verify the script path is correct
)

echo.
pause
endlocal

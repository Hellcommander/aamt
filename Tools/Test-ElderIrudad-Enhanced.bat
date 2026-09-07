@echo off
REM Test-ElderIrudad-Enhanced.bat
REM Enhanced test script for generating the "Elder Irudad" mutant elder character image
REM This tests the uncensored image generator with AI enhancement enabled

setlocal EnableDelayedExpansion

REM Set script directory
cd /d "%~dp0"

echo ========================================
echo Testing Elder Irudad Image Generation
echo With AI Enhancement
echo ========================================
echo.

REM Check if Stable Diffusion API is running
echo Checking Stable Diffusion API...
powershell -Command "try { $response = Invoke-RestMethod -Uri 'http://localhost:8000/docs' -Method Get -TimeoutSec 3 -ErrorAction Stop; Write-Host '  [OK] Stable Diffusion API is running' -ForegroundColor Green } catch { Write-Host '  [WARNING] Stable Diffusion API may not be running' -ForegroundColor Yellow }"
echo.

REM Check if Ollama is running
echo Checking Ollama...
powershell -Command "try { $response = Invoke-RestMethod -Uri 'http://localhost:11434/api/tags' -Method Get -TimeoutSec 3 -ErrorAction Stop; Write-Host '  [OK] Ollama is running' -ForegroundColor Green } catch { Write-Host '  [WARNING] Ollama may not be running' -ForegroundColor Yellow }"
echo.

REM Build the description
set "DESC=A warm smile spreads over an old face freckled by time and a million crumbs of salt. He shrinks under a hunched back and drums the ground beneath him with a short and barb-crowned tail. A second pair of arms rise over the slump of his shoulders, where hands meet and fingers lace to form another face, this one vacant and prehistoric, no mouth and eyes desert-white."

REM Export as environment variable for PowerShell
set "DESC=%DESC%"

echo Starting image generation...
echo Description: Elder Irudad - Mutant Elder with body horror features
echo Game Type: Caves of Qud
echo Mutations: Multiple Arms, Chimera, Stinger
echo Traits: Body Horror, Multiple Faces
echo Resolution: 1024x1024
echo AI Enhancement: Enabled
echo.

REM Run the PowerShell script with AI enhancement
REM NOTE: Use -Command so PowerShell can parse @(...) arrays correctly.
powershell -NoProfile -ExecutionPolicy Bypass -Command "& { $env:DESC = '%DESC%'; & '.\\UncensoredCharacterImageGenerator.ps1' -Description $env:DESC -CharacterName 'Elder Irudad' -GameType 'Qud' -Mutations @('Multiple Arms','Chimera','Stinger') -Traits @('Body Horror','Multiple Faces') -Width 1024 -Height 1024 -AIEnhancement -RegenerateImproved -Verbose }"

REM Check exit code
set "EXIT_CODE=%ERRORLEVEL%"
if %EXIT_CODE% EQU 0 (
    echo.
    echo ========================================
    echo Test completed successfully!
    echo ========================================
    echo.
    echo Generated files should be in the output directory.
    echo Look for files named: Elder_Irudad*.png
    echo.
) else (
    echo.
    echo ========================================
    echo Test failed with error code: %EXIT_CODE%
    echo ========================================
    echo.
    echo Troubleshooting:
    echo   1. Ensure Stable Diffusion API is running: http://localhost:8000
    echo   2. Ensure Ollama is running: http://localhost:11434
    echo   3. Check that vision models are installed: ollama pull llava:latest
    echo   4. Verify the script path is correct
    echo.
)

echo.
pause
endlocal

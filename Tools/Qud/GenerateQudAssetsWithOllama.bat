@echo off
REM Batch script to generate Qud mod assets using Ollama for AI-powered design
REM Usage: GenerateQudAssetsWithOllama.bat "Mod Name" [candidates] [--no-ollama]

setlocal

set MOD_NAME=%~1
set CANDIDATES=%~2
set NO_OLLAMA=%~3

if "%MOD_NAME%"=="" (
    echo Usage: GenerateQudAssetsWithOllama.bat "Mod Name" [candidates] [--no-ollama]
    echo.
    echo Examples:
    echo   GenerateQudAssetsWithOllama.bat "Broodmother Mutation"
    echo   GenerateQudAssetsWithOllama.bat "Broodmother Mutation" 5
    echo   GenerateQudAssetsWithOllama.bat "Broodmother Mutation" 3 --no-ollama
    exit /b 1
)

if "%CANDIDATES%"=="" set CANDIDATES=3
if "%CANDIDATES%"=="--no-ollama" (
    set CANDIDATES=3
    set NO_OLLAMA=--no-ollama
)

cd /d "%~dp0"

echo ============================================================
echo Qud Asset Generator with Ollama AI
echo ============================================================
echo Mod: %MOD_NAME%
echo Candidates per asset: %CANDIDATES%
if "%NO_OLLAMA%"=="--no-ollama" (
    echo Ollama: DISABLED (procedural generation only)
) else (
    echo Ollama: ENABLED (AI-powered design generation)
)
echo.

python generate_mod_assets.py "%MOD_NAME%" --candidates %CANDIDATES% %NO_OLLAMA%

if errorlevel 1 (
    echo.
    echo ERROR: Asset generation failed
    exit /b 1
)

echo.
echo ============================================================
echo Asset generation complete!
echo ============================================================

endlocal

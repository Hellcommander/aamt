@echo off
REM ============================================================================
REM Broodmother Mutation asset tools — pick a mode
REM ============================================================================

setlocal enabledelayedexpansion
set "SCRIPT_DIR=%~dp0"
set "MOD_PATH=%USERPROFILE%\AppData\LocalLow\Freehold Games\CavesOfQud\Mods\Broodmother Mutation"

:menu
cls
echo ========================================
echo Broodmother Mutation — Asset Tools
echo ========================================
echo Mod: %MOD_PATH%
echo.
echo   1^) Start SD3.5 server          (port 1338)
echo   2^) POLICE quality loop         (RECOMMENDED — gate+critic+SD retry)
echo   3^) Draft only                  (fast SD, no review — broken drafts kept)
echo   4^) Ollama prompt pack only     (stops SD, wizardlm)
echo   5^) Fresh prompts + police      (Ollama pack then police loop)
echo   6^) FULL multi-model refine     (slow sequential vision agents)
echo   7^) Open DesignDrafts folder
echo   8^) Open Textures folder
echo   9^) Tail SD error log
echo   S^) Stop SD3.5 server           (free VRAM)
echo   0^) Exit
echo.
choice /C 123456789S0 /N /M "Select"
set "C=%ERRORLEVEL%"

if "%C%"=="1" goto :sd
if "%C%"=="2" goto :police
if "%C%"=="3" goto :draft
if "%C%"=="4" goto :ollama
if "%C%"=="5" goto :fresh
if "%C%"=="6" goto :multi
if "%C%"=="7" goto :drafts
if "%C%"=="8" goto :tex
if "%C%"=="9" goto :log
if "%C%"=="10" goto :stopsd
if "%C%"=="11" goto :eof
goto :menu

:sd
call "%SCRIPT_DIR%Start-BroodmotherSDServer.bat"
goto :menu

:police
call "%SCRIPT_DIR%GenerateBroodmotherAssets-Police.bat" "%MOD_PATH%"
goto :menu

:draft
powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%GenerateBroodmotherAssets.ps1" -ModPath "%MOD_PATH%" -LoadExisting -Verbose -QualityMode draft -OllamaModel "wizardlm-uncensored:latest" -PythonExe "E:\tools\miniconda3\python.exe"
echo.
pause
goto :menu

:ollama
call "%SCRIPT_DIR%GenerateBroodmotherAssets-OllamaPrompts.bat" "%MOD_PATH%"
goto :menu

:fresh
call "%SCRIPT_DIR%GenerateBroodmotherAssets-OllamaPrompts.bat" "%MOD_PATH%" nopause
call "%SCRIPT_DIR%GenerateBroodmotherAssets-Police.bat" "%MOD_PATH%"
goto :menu

:multi
call "%SCRIPT_DIR%GenerateBroodmotherAssets-MultiAgent.bat" "%MOD_PATH%"
goto :menu

:drafts
explorer "%MOD_PATH%\DesignDrafts"
goto :menu

:tex
explorer "%MOD_PATH%\Textures"
goto :menu

:log
echo.
echo === Last 40 lines: E:\tools\sd3.5\sd3.5\sd_server.err.log ===
if exist "E:\tools\sd3.5\sd3.5\sd_server.err.log" (
    powershell -NoProfile -Command "Get-Content 'E:\tools\sd3.5\sd3.5\sd_server.err.log' -Tail 40"
) else (
    echo Log not found.
)
echo.
pause
goto :menu

:stopsd
call "%SCRIPT_DIR%Stop-BroodmotherSDServer.bat"
goto :menu

:eof
endlocal
exit /b 0

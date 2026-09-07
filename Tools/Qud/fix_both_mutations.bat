@echo off
setlocal enabledelayedexpansion

set SCRIPT_DIR=%~dp0
set PYTHON_CMD=python
set MODS_PATH=C:\Users\Arend\AppData\LocalLow\Freehold Games\CavesOfQud\Mods
set SAVE_PATH=C:\Users\Arend\AppData\LocalLow\Freehold Games\CavesOfQud

echo ================================================================================
echo COMPREHENSIVE MUTATION MOD FIXER
echo ================================================================================
echo.
echo This will fix ALL issues in both mutation mods using AI simulation
echo Model: wizardlm-uncensored (best for code + visual understanding)
echo.
echo Mods to fix:
echo   1. Improved and Rebalanced Space Time Vortex
echo   2. Broodmother Mutation
echo.
echo ================================================================================
echo.

REM Fix Space-Time Vortex mod
echo.
echo [1/2] Fixing: Improved and Rebalanced Space Time Vortex
echo --------------------------------------------------------------------------------
echo Running comprehensive analysis with mutation simulation...
echo.
"%PYTHON_CMD%" "%SCRIPT_DIR%qud_mod_fixer.py" "Improved and Rebalanced Space Time Vortex" ^
    --model wizardlm-uncensored ^
    --issue "comprehensive fix and simulation: analyze entire mutation lifecycle, ensure mutation Name matches base game exactly for replacement, verify all activated abilities have proper cooldowns and energy costs, ensure vortexes spawn correctly with proper cell validation and null checks, verify all visual effects and assets display properly, check all scheduled callbacks handle stale cell references correctly by re-getting cells from coordinates, ensure proper cleanup in Unmutate method, verify no null reference exceptions, test mutation simulation from Mutate through runtime to Unmutate" ^
    --error-logs "%SAVE_PATH%\Player.log" "%SAVE_PATH%\game_log.txt" "%SAVE_PATH%\errors found.txt" "%SAVE_PATH%\harmony.log.txt" ^
    --save-path "%SAVE_PATH%"

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: Space-Time Vortex fix failed with code: %ERRORLEVEL%
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo [1/2] Space-Time Vortex fix completed successfully!
echo.
echo ================================================================================
echo.

REM Fix Broodmother Mutation mod
echo.
echo [2/2] Fixing: Broodmother Mutation
echo --------------------------------------------------------------------------------
echo Running comprehensive analysis with mutation simulation...
echo.
"%PYTHON_CMD%" "%SCRIPT_DIR%qud_mod_fixer.py" "Broodmother Mutation" ^
    --model wizardlm-uncensored ^
    --issue "comprehensive fix and simulation: analyze entire mutation lifecycle, ensure all activated abilities have proper cooldowns and energy costs, verify broodlings spawn correctly when messages appear with proper error handling and null checks, ensure broodling sack is takeable and works correctly in inventory, verify all creature spawning handles errors gracefully with user feedback, check all visual assets display correctly, ensure proper cleanup in Unmutate method removes all abilities and resources, verify no null reference exceptions, test mutation simulation from Mutate through gestation and spawning to Unmutate" ^
    --error-logs "%SAVE_PATH%\Player.log" "%SAVE_PATH%\game_log.txt" "%SAVE_PATH%\errors found.txt" "%SAVE_PATH%\harmony.log.txt" ^
    --save-path "%SAVE_PATH%"

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: Broodmother Mutation fix failed with code: %ERRORLEVEL%
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo [2/2] Broodmother Mutation fix completed successfully!
echo.
echo ================================================================================
echo.
echo ALL MODS FIXED SUCCESSFULLY!
echo.
echo Both mutation mods have been comprehensively analyzed and fixed using AI simulation.
echo The wizardlm-uncensored model was used to ensure proper code fixes and visual asset handling.
echo.
echo ================================================================================
echo.
pause


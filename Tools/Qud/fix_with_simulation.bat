@echo off
REM Example: Fix Space Time Vortex using mutation architecture simulation
REM The AI will analyze source code mutations and simulate runtime behavior

set SCRIPT_DIR=%~dp0
set PYTHON_CMD=python

echo ============================================================
echo Qud Mod Fixer with Mutation Simulation
echo ============================================================
echo.
echo This will:
echo  1. Analyze your mutation's architecture
echo  2. Retrieve similar mutations from game source
echo  3. Simulate mutation lifecycle (Mutate/Runtime/Unmutate)
echo  4. Generate fixes matching game patterns
echo.

REM Example 1: Natural language with simulation
echo [Example 1] Natural language fix with simulation
"%PYTHON_CMD%" "%SCRIPT_DIR%qud_mod_fixer.py" "Improved and Rebalanced Space Time Vortex" ^
    --issue "ability has no cooldown can spam infinitely" ^
    --model codellama:34b

echo.
echo ============================================================
echo.
pause


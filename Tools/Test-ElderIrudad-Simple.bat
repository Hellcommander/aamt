@echo off
REM Test-ElderIrudad-Simple.bat
REM Simple test script for generating the "Elder Irudad" character image
REM Basic version without AI enhancement

setlocal

cd /d "%~dp0"

echo Testing Elder Irudad Image Generation...
echo.

set "DESC=A warm smile spreads over an old face freckled by time and a million crumbs of salt. He shrinks under a hunched back and drums the ground beneath him with a short and barb-crowned tail. A second pair of arms rise over the slump of his shoulders, where hands meet and fingers lace to form another face, this one vacant and prehistoric, no mouth and eyes desert-white."

REM NOTE: Use -Command so PowerShell can parse @(...) arrays correctly.
powershell -NoProfile -ExecutionPolicy Bypass -Command "& { $env:DESC = '%DESC%'; & '.\\UncensoredCharacterImageGenerator.ps1' -Description $env:DESC -CharacterName 'Elder Irudad' -GameType 'Qud' -Mutations @('Multiple Arms','Chimera','Stinger') -Traits @('Body Horror','Multiple Faces') -Width 1024 -Height 1024 -Verbose }"

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Error: Generation failed with code %ERRORLEVEL%
)

pause
endlocal

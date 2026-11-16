@echo off
REM Compile game_and_dlc_source packs to Tools\Transcendence\Output\CompiledTdb for TESTING ONLY.
REM
REM It never writes into the game folder: Transcendence.tdb and Collection\*.tdb must stay exactly as Steam ships them.
REM A recompiled core/DLC TDB gets a different digest, so the game no longer treats it as the registered DLC (DLC
REM adventures vanish) and edits to core content break Stars of the Pilgrim and Corporate Command. Change official
REM content only through a separate extension in Extensions\.

set "TX=D:\games\Steam\steamapps\common\Transcendence"
set "SRC=%TX%\game_and_dlc_source"
set "OUT=%~dp0Output\CompiledTdb"
set "TC=%TX%\TransCompiler.exe"
if not exist "%OUT%" mkdir "%OUT%"
cd /d "%OUT%" || exit /b 1

echo === Transcendence.tdb (core) ===
"%TC%" /input:"%SRC%\Transcendence_Source\Transcendence.xml" /output:"%OUT%\Transcendence.tdb" /digest
if errorlevel 1 exit /b 1

echo === CorporateHierarchyVol1UNIDs.tdb ===
"%TC%" /input:"%SRC%\CorporateHierarchyVol1UNIDs_Source\CorporateHierarchyVol1UNIDs.xml" /output:"%OUT%\CorporateHierarchyVol1UNIDs.tdb" /digest
if errorlevel 1 exit /b 1

echo === CorporateHierarchyVol01.tdb ===
"%TC%" /input:"%SRC%\CorporateHierarchyVol01_Source\CorporateHierarchyVol01.xml" /output:"%OUT%\CorporateHierarchyVol01.tdb" /digest
if errorlevel 1 exit /b 1

echo === CorporateCommand.tdb ===
"%TC%" /input:"%SRC%\CorporateCommand_Source\CorporateCommand.xml" /entities:"%OUT%\CorporateHierarchyVol01.tdb" /output:"%OUT%\CorporateCommand.tdb" /digest
if errorlevel 1 exit /b 1

echo === StarsOfThePilgrimHD.tdb ===
"%TC%" /input:"%SRC%\StarsOfThePilgrimHD_Source\StarsOfThePilgrimHD.xml" /output:"%OUT%\StarsOfThePilgrimHD.tdb" /digest
if errorlevel 1 exit /b 1

echo === StarsOfThePilgrimSoundtrack.tdb ===
"%TC%" /input:"%SRC%\StarsOfThePilgrimSoundtrack_Source\StarsOfThePilgrimSoundtrack.xml" /output:"%OUT%\StarsOfThePilgrimSoundtrack.tdb" /digest
if errorlevel 1 exit /b 1

echo All packs compiled OK to %OUT% (game folder untouched).
exit /b 0

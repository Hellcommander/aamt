@echo off
REM Compile game_and_dlc_source packs into Collection (+ core Transcendence.tdb)
REM Run from anywhere; uses absolute paths. Requires TransCompiler.exe + Transcendence.tdb in game root.

set "TX=D:\games\Steam\steamapps\common\Transcendence"
set "SRC=%TX%\game_and_dlc_source"
set "COL=%TX%\Collection"
set "TC=%TX%\TransCompiler.exe"
cd /d "%TX%" || exit /b 1

echo === Transcendence.tdb (core) ===
"%TC%" /input:"%SRC%\Transcendence_Source\Transcendence.xml" /output:"%TX%\Transcendence.tdb" /digest
if errorlevel 1 exit /b 1

echo === CorporateHierarchyVol1UNIDs.tdb ===
"%TC%" /input:"%SRC%\CorporateHierarchyVol1UNIDs_Source\CorporateHierarchyVol1UNIDs.xml" /output:"%COL%\CorporateHierarchyVol1UNIDs.tdb" /digest
if errorlevel 1 exit /b 1

echo === CorporateHierarchyVol01.tdb ===
"%TC%" /input:"%SRC%\CorporateHierarchyVol01_Source\CorporateHierarchyVol01.xml" /output:"%COL%\CorporateHierarchyVol01.tdb" /digest
if errorlevel 1 exit /b 1

echo === CorporateCommand.tdb ===
"%TC%" /input:"%SRC%\CorporateCommand_Source\CorporateCommand.xml" /entities:"%COL%\CorporateHierarchyVol01.tdb" /output:"%COL%\CorporateCommand.tdb" /digest
if errorlevel 1 exit /b 1

echo === StarsOfThePilgrimHD.tdb ===
"%TC%" /input:"%SRC%\StarsOfThePilgrimHD_Source\StarsOfThePilgrimHD.xml" /output:"%COL%\StarsOfThePilgrimHD.tdb" /digest
if errorlevel 1 exit /b 1

echo === StarsOfThePilgrimSoundtrack.tdb ===
"%TC%" /input:"%SRC%\StarsOfThePilgrimSoundtrack_Source\StarsOfThePilgrimSoundtrack.xml" /output:"%COL%\StarsOfThePilgrimSoundtrack.tdb" /digest
if errorlevel 1 exit /b 1

echo All packs compiled OK.
exit /b 0

$paths = @(
    "D:\games\Steam\steamapps\common\Transcendence\game and dlc source\Transcendence_Source",
    "D:\games\Steam\steamapps\common\Transcendence\game and dlc source\CorporateCommand_Source",
    "D:\games\Steam\steamapps\common\Transcendence\game and dlc source\CorporateHierarchyVol01_Source",
    "D:\games\Steam\steamapps\common\Transcendence\game and dlc source\CorporateHierarchyVol1UNIDs_Source",
    "D:\games\Steam\steamapps\common\Transcendence\game and dlc source\StarsOfThePilgrimHD_Source",
    "D:\games\Steam\steamapps\common\Transcendence\game and dlc source\StarsOfThePilgrimSoundtrack_Source"
)

.\BuildReferenceArchive.ps1 -SourcePaths $paths -IncludeSource -OutputPath "reference_archive_multi" -DetectUpdates


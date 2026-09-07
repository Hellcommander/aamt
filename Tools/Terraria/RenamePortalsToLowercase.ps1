# Rename Portal Spritesheets to Lowercase
# This script renames all PascalCase portal spritesheets to lowercase

$tilesDir = "d:\User_Directories\Documents\My Games\Terraria\tModLoader\ModSources\CrossModStabilizer\Assets\Tiles"

$renames = @{
    "OrchidJungleBiomePortal_spritesheet.png" = "orchidjunglebiomeportal_spritesheet.png"
    "OrchidDesertBiomePortal_spritesheet.png" = "orchiddesertbiomeportal_spritesheet.png"
    "OrchidOceanBiomePortal_spritesheet.png" = "orchidoceanbiomeportal_spritesheet.png"
    "OrchidSnowBiomePortal_spritesheet.png" = "orchidsnowbiomeportal_spritesheet.png"

# Load shared asset generation settings
$settingsPath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "..\\AssetGenerationSettings.ps1"
if (Test-Path $settingsPath) {
    . $settingsPath
}
    "BurntDesertBiomePortal_spritesheet.png" = "burntdesertbiomeportal_spritesheet.png"
    "WulfrumScrapyardBiomePortal_spritesheet.png" = "wulfrumscrapyardbiomeportal_spritesheet.png"
    "SpiritBiomePortal_spritesheet.png" = "spiritbiomeportal_spritesheet.png"
    "SpiritModPortal_spritesheet.png" = "spiritmodportal_spritesheet.png"
    "SavannaBiomePortal_spritesheet.png" = "savannabiomeportal_spritesheet.png"
    "RedemptionPortal_spritesheet.png" = "redemptionportal_spritesheet.png"
    "AequusPortal_spritesheet.png" = "aequusportal_spritesheet.png"
    "EndPreludePortal_spritesheet.png" = "endpreludeportal_spritesheet.png"
    "StarsAndFirePortal_spritesheet.png" = "starsandfireportal_spritesheet.png"
    "PokeModPortal_spritesheet.png" = "pokemodportal_spritesheet.png"
    "RandomResourcePortal_spritesheet.png" = "randomresourceportal_spritesheet.png"
}

Write-Host "Renaming portal spritesheets to lowercase..." -ForegroundColor Cyan

foreach ($oldName in $renames.Keys) {
    $oldPath = Join-Path $tilesDir $oldName
    $newPath = Join-Path $tilesDir $renames[$oldName]
    
    if (Test-Path $oldPath) {
        if (-not (Test-Path $newPath)) {
            Rename-Item -Path $oldPath -NewName $renames[$oldName]
            Write-Host "[OK] Renamed: $oldName -> $($renames[$oldName])" -ForegroundColor Green
        } else {
            Write-Host "[SKIP] Already exists: $($renames[$oldName])" -ForegroundColor Yellow
        }
    } else {
        Write-Host "[MISSING] Not found: $oldName" -ForegroundColor Red
    }
}

Write-Host "`nRenaming complete!" -ForegroundColor Cyan

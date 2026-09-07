#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Merge generated asset integration scripts into central agent files.
    
.DESCRIPTION
    Intelligently merges generated asset manager scripts into:
    - Lua: scripts/BusPlugins/MainPlugin/core/enhancedAssetManager.lua
    - C++: cpp_backend/core/modules/AssetManager.hpp and .cpp
    
    Groups assets by type/system to maintain organization while reducing file count.
    
.PARAMETER AssetName
    Name of the asset system (e.g., "MagicOrb", "Spellstone")
    
.PARAMETER AssetType
    Type of asset system (e.g., "Weapon", "Item", "Projectile")
    
.PARAMETER ModPath
    Path to the mod directory
    
.PARAMETER Assets
    Array of asset definitions with id, path, type, etc.
    
.PARAMETER MergeMode
    How to merge: "Append" (add to end), "Group" (group by type), "Replace" (replace section)
#>

param(
    [Parameter(Mandatory=$true)
# Validate ModPath is not empty
if ([string]::IsNullOrWhiteSpace($ModPath)) {
    Write-Host "Error: ModPath cannot be empty" -ForegroundColor Red
    Write-Host "  Please provide a valid mod path or use the default" -ForegroundColor Gray
    exit 1
}
]
    [string]$AssetName,
    
    [Parameter(Mandatory=$true)]
    [string]$AssetType,
    
    [Parameter(Mandatory=$false)]
    [string]$ModPath = "F:\Games\OpenStarbound\mods\Magi-Tech Arcane Alchemy and Sorcery",
    
    [Parameter(Mandatory=$false)]
    [array]$Assets = @(),
    
    [Parameter(Mandatory=$false)]
    [ValidateSet("Append", "Group", "Replace")]
    [string]$MergeMode = "Group"
)

$ErrorActionPreference = "Continue"

# Load shared asset generation settings
$settingsPath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "..\\AssetGenerationSettings.ps1"
if (Test-Path $settingsPath) {
    . $settingsPath
}
$PSScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

# Normalize asset name
$normalizedName = $AssetName -replace '([a-z])([A-Z])', '$1$2' -split ' ' | ForEach-Object { 
    if ($_.Length -gt 0) {
        $_.Substring(0,1).ToUpper() + $_.Substring(1).ToLower()
    }
} | Where-Object { $_ }
$normalizedName = ($normalizedName -join '') -replace '[^a-zA-Z0-9]', ''

# Paths
# Validate $ModPath before Join-Path
$luaMainFile = Join-Path $ModPath "scripts\BusPlugins\MainPlugin\core\enhancedAssetManager.lua"
 if ([string]::IsNullOrWhiteSpace($luaMainFile)) {
    Write-Host "  [FAIL] luaMainFile is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($luaMainFile)) {
    Write-Host "  [FAIL] luaMainFile is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
# Validate $ModPath before Join-Path
$cppHeaderFile = Join-Path $ModPath "cpp_backend\core\modules\AssetManager.hpp"
 if ([string]::IsNullOrWhiteSpace($cppHeaderFile)) {
    Write-Host "  [FAIL] cppHeaderFile is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($cppHeaderFile)) {
    Write-Host "  [FAIL] cppHeaderFile is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
# Validate $ModPath before Join-Path
$cppSourceFile = Join-Path $ModPath "cpp_backend\core\modules\AssetManager.cpp"
 if ([string]::IsNullOrWhiteSpace($cppSourceFile)) {
    Write-Host "  [FAIL] cppSourceFile is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($cppSourceFile)) {
    Write-Host "  [FAIL] cppSourceFile is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}

# Check if main files exist
if (-not (Test-Path $luaMainFile)) {
    Write-Host "[ERROR] Main Lua file not found: $luaMainFile" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $cppHeaderFile)) {
    Write-Host "[ERROR] Main C++ header not found: $cppHeaderFile" -ForegroundColor Red
    exit 1
}

Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Merging Asset Integration Scripts" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "Asset System: $AssetName ($AssetType)" -ForegroundColor Yellow
Write-Host "Assets to merge: $($Assets.Count)" -ForegroundColor Yellow
Write-Host "Merge Mode: $MergeMode" -ForegroundColor Yellow
Write-Host ""

# ============================================================================
# Merge into Lua Enhanced Asset Manager
# ============================================================================

Write-Host "Merging into Lua Enhanced Asset Manager..." -ForegroundColor Cyan

$luaContent = Get-Content $luaMainFile -Raw

# Find insertion point - look for "Asset Definitions" section or before return statement
$returnMarker = "return EnhancedAssetManager"
$moduleExportMarker = "-- Module Export"

# Check if section already exists
$sectionName = "-- $normalizedName Asset System"
$sectionExists = $luaContent -match [regex]::Escape($sectionName)

if ($sectionExists) {
    Write-Host "  [INFO] Section already exists, updating..." -ForegroundColor Yellow
    
    # Replace existing section (match from section name to next section or return)
    $sectionPattern = "(?s)($([regex]::Escape($sectionName))[^\r\n]*[\r\n]+.*?)(?=-- [A-Z]|$returnMarker)"
    $newSection = GenerateLuaAssetSection -AssetName $normalizedName -AssetType $AssetType -Assets $Assets
    
    if ($luaContent -match $sectionPattern) {
        $luaContent = $luaContent -replace $sectionPattern, $newSection
    }
} else {
    Write-Host "  [INFO] Adding new section..." -ForegroundColor Green
    
    # Find insertion point before "Module Export" section
    if ($luaContent -match "($moduleExportMarker)") {
        $newSection = "`n" + (GenerateLuaAssetSection -AssetName $normalizedName -AssetType $AssetType -Assets $Assets) + "`n"
        $luaContent = $luaContent -replace "($moduleExportMarker)", "$newSection`$1"
    } elseif ($luaContent -match "($returnMarker)") {
        # Fallback: insert before return statement
        $newSection = "`n" + (GenerateLuaAssetSection -AssetName $normalizedName -AssetType $AssetType -Assets $Assets) + "`n"
        $luaContent = $luaContent -replace "($returnMarker)", "$newSection`$1"
    } else {
        # Append at end
        $newSection = GenerateLuaAssetSection -AssetName $normalizedName -AssetType $AssetType -Assets $Assets
        $luaContent = $luaContent + "`n" + $newSection + "`n"
    }
}

# Write merged Lua file
[System.IO.File]::WriteAllText($luaMainFile, $luaContent, [System.Text.UTF8Encoding]::new($false))
Write-Host "  [OK] Merged into: $luaMainFile" -ForegroundColor Green

# ============================================================================
# Merge into C++ Asset Manager
# ============================================================================

Write-Host "Merging into C++ Asset Manager..." -ForegroundColor Cyan

$cppHeaderContent = Get-Content $cppHeaderFile -Raw
$cppSourceContent = if (Test-Path $cppSourceFile) { Get-Content $cppSourceFile -Raw } else { "" }

# Add asset registration method to header if not exists
$methodName = "register${normalizedName}Assets"
if ($cppHeaderContent -notmatch [regex]::Escape($methodName)) {
    # Find insertion point before private section (add to public section)
    # Look for a good spot in public section, like after other registration methods
    $publicRegistrationMarker = "bool importFromLua\(const std::string& luaFile\);"
    if ($cppHeaderContent -match "($publicRegistrationMarker)") {
        $newMethod = @"

    // ${normalizedName} Asset System Registration
    void $methodName();
"@
        $cppHeaderContent = $cppHeaderContent -replace "($publicRegistrationMarker)", "`$1$newMethod"
    } else {
        # Fallback: add before private section
        $privateMarker = "private:"
        if ($cppHeaderContent -match "($privateMarker)") {
            $newMethod = @"

    // ${normalizedName} Asset System Registration
    void $methodName();
"@
            $cppHeaderContent = $cppHeaderContent -replace "($privateMarker)", "$newMethod`n`$1"
        }
    }
}

# Add implementation to source
if ($cppSourceContent -notmatch [regex]::Escape($methodName)) {
    # Find insertion point - look for end of namespace or similar registration methods
    $implMarker = "} // namespace MagiTech"
    $existingImplMarker = "void AssetManager::register.*Assets\(\)"
    
    if ($cppSourceContent -match $existingImplMarker) {
        # Insert after existing registration methods
        $newImpl = GenerateCppAssetRegistration -AssetName $normalizedName -AssetType $AssetType -Assets $Assets
        $cppSourceContent = $cppSourceContent -replace "($implMarker)", "$newImpl`n`$1"
    } elseif ($cppSourceContent -match "($implMarker)") {
        $newImpl = GenerateCppAssetRegistration -AssetName $normalizedName -AssetType $AssetType -Assets $Assets
        $cppSourceContent = $cppSourceContent -replace "($implMarker)", "$newImpl`n`$1"
    } else {
        # Append at end
        $newImpl = GenerateCppAssetRegistration -AssetName $normalizedName -AssetType $AssetType -Assets $Assets
        $cppSourceContent = $cppSourceContent + "`n" + $newImpl + "`n"
    }
}

# Write merged C++ files
[System.IO.File]::WriteAllText($cppHeaderFile, $cppHeaderContent, [System.Text.UTF8Encoding]::new($false))
Write-Host "  [OK] Merged into: $cppHeaderFile" -ForegroundColor Green

if ($cppSourceFile) {
    [System.IO.File]::WriteAllText($cppSourceFile, $cppSourceContent, [System.Text.UTF8Encoding]::new($false))
    Write-Host "  [OK] Merged into: $cppSourceFile" -ForegroundColor Green
}

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Merge Complete" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# ============================================================================
# Helper Functions
# ============================================================================

function GenerateLuaAssetSection {
    param(
        [string]$AssetName,
        [string]$AssetType,
        [array]$Assets
    )
    
    $section = @"
-- ============================================================================
-- $AssetName Asset System ($AssetType)
-- Auto-generated asset definitions
-- ============================================================================

local ${AssetName}Assets = {
$(if ($Assets.Count -gt 0) {
    $assetLines = $Assets | ForEach-Object {
        "    [`"$($_.Id)`"] = {"
        "        id = `"$($_.Id)`","
        "        path = `"$($_.Path)`","
        "        type = `"$($_.Type)`","
        if ($_.License) { "        license = `"$($_.License)`"," }
        if ($_.Description) { "        description = `"$($_.Description)`"," }
        "        system = `"$AssetName`","
        "        category = `"$AssetType`""
        "    },"
    } | ForEach-Object { $_ }
    $assetLines -join "`n"
} else {
    "    -- No assets defined"
})
}

-- Register ${AssetName} assets
function EnhancedAssetManager.register${AssetName}Assets()
    if not state.initialized then
        log.warning("EnhancedAssetManager: Cannot register ${AssetName} assets - not initialized")
        return false
    end
    
    local registered = 0
    local failed = 0
    
    for assetId, assetData in pairs(${AssetName}Assets) do
        local success = EnhancedAssetManager.registerAsset(
            assetId,
            assetData.path,
            assetData.type,
            "MagiTech",
            assetData.license or "CC-BY-NC-SA",
            {
                description = assetData.description or "Auto-generated $AssetName asset",
                category = assetData.category,
                system = assetData.system
            }
        )
        
        if success then
            registered = registered + 1
        else
            failed = failed + 1
            log.warning("EnhancedAssetManager: Failed to register ${AssetName} asset: " .. assetId)
        end
    end
    
    log.info("EnhancedAssetManager: Registered $registered ${AssetName} assets (failed: $failed)")
    return registered > 0
end

-- Auto-register ${AssetName} assets on initialization if enabled
if config.autoRegisterAssets then
    EnhancedAssetManager.register${AssetName}Assets()
end

"@
    
    return $section
}

function GenerateCppAssetRegistration {
    param(
        [string]$AssetName,
        [string]$AssetType,
        [array]$Assets
    )
    
    $methodNameVar = "register${AssetName}Assets"
    
    # Map asset types to C++ AssetType enum
    $typeMap = @{
        "Texture" = "Texture"
        "Sound" = "Sound"
        "Animation" = "Animation"
        "SpellIcon" = "SpellIcon"
        "SpellEffect" = "SpellEffect"
        "UI" = "UI"
        "Model" = "Model"
        "Shader" = "Shader"
        "Config" = "Config"
        "Lua" = "Lua"
        "Font" = "Font"
        "Video" = "Video"
        "Archive" = "Archive"
        "Document" = "Document"
    }
    
    $impl = @"
// ${AssetName} Asset System Registration ($AssetType)
void AssetManager::$methodNameVar()
{
    std::unique_lock<std::shared_mutex> lock(assetsMutex);
    
$(if ($Assets.Count -gt 0) {
    $assetLines = $Assets | ForEach-Object {
        $cppType = if ($typeMap.ContainsKey($_.Type)) { $typeMap[$_.Type] } else { "Unknown" }
        "    registerAsset(`"$($_.Id)`", `"$($_.Path)`", AssetType::$cppType, `"MagiTech`");"
    }
    $assetLines -join "`n"
} else {
    "    // No assets to register"
})
    
    logInfo("AssetManager: Registered $($Assets.Count) ${AssetName} assets");
}

"@
    
    return $impl
}

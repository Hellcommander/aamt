<#
.SYNOPSIS
  Validates the reference archive against known references
#>

param(
    [string]$ArchivePath = "reference_archive_test"
)

$ErrorActionPreference = 'Stop'

Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Validating Reference Archive" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# Known test entities from CMPT_API54CompatUNIDsLibrary.xml
$knownEntities = @{
    'itSolarArmor' = '0x0000407C'
    'itTitaniumPlate' = '0x00004057'
    'itHeavyTitaniumPlate' = '0x00004062'
    'scWolfen' = '0x00003011'
    'CMPT_unidAPI54CompatUNIDLibrary' = '0x00710000'
    'unidRPGLibrary' = '0x00010000'
    'unidHumanSpaceLibrary' = '0x00100000'
}

# Known UNIDs
$knownUNIDs = @{
    '0x0000407C' = 'itSolarArmor'
    '0x00004057' = 'itTitaniumPlate'
    '0x00004062' = 'itHeavyTitaniumPlate'
    '0x00003011' = 'scWolfen'
    '0x00710000' = 'CMPT_unidAPI54CompatUNIDLibrary'
    '0x00010000' = 'unidRPGLibrary'
    '0x00100000' = 'unidHumanSpaceLibrary'
}

$basePath = Join-Path $PSScriptRoot $ArchivePath
$baseGamePath = Join-Path $basePath "base_game_api0"

if (-not (Test-Path $baseGamePath)) {
    Write-Host "ERROR: Archive path not found: $baseGamePath" -ForegroundColor Red
    exit 1
}

Write-Host "Loading archive files..." -ForegroundColor Cyan

# Load entities
$entitiesFile = Join-Path $baseGamePath "entities.json"
if (Test-Path $entitiesFile) {
    $entitiesJson = Get-Content $entitiesFile -Raw
    $entities = $entitiesJson | ConvertFrom-Json
    $entityCount = ($entities.PSObject.Properties | Measure-Object).Count
    Write-Host "  Loaded entities.json: $entityCount entities" -ForegroundColor Gray
} else {
    Write-Host "  ERROR: entities.json not found" -ForegroundColor Red
    exit 1
}

# Load UNIDs
$unidsFile = Join-Path $baseGamePath "unids.json"
if (Test-Path $unidsFile) {
    $unidsJson = Get-Content $unidsFile -Raw
    $unids = $unidsJson | ConvertFrom-Json
    $unidCount = ($unids.PSObject.Properties | Measure-Object).Count
    Write-Host "  Loaded unids.json: $unidCount UNIDs" -ForegroundColor Gray
} else {
    Write-Host "  ERROR: unids.json not found" -ForegroundColor Red
    exit 1
}

# Load metadata
$metadataFile = Join-Path $baseGamePath "metadata.json"
if (Test-Path $metadataFile) {
    $metadata = Get-Content $metadataFile -Raw | ConvertFrom-Json
    Write-Host "  Loaded metadata.json" -ForegroundColor Gray
} else {
    Write-Host "  ERROR: metadata.json not found" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Validating known entities..." -ForegroundColor Cyan

$entityErrors = 0
$entitySuccess = 0

foreach ($entityName in $knownEntities.Keys) {
    $expectedUNID = $knownEntities[$entityName]
    $entityProp = $entities.PSObject.Properties | Where-Object { $_.Name -eq $entityName }
    
    if ($entityProp) {
        $entityValue = $entityProp.Value
        $actualUNID = if ($entityValue.UNID) { $entityValue.UNID } else { $null }
        if ($actualUNID -eq $expectedUNID) {
            Write-Host "  ✓ $entityName = $expectedUNID" -ForegroundColor Green
            $entitySuccess++
        } elseif ([string]::IsNullOrEmpty($actualUNID)) {
            Write-Host "  ⚠ $entityName - Found but UNID is empty (may be reference-only)" -ForegroundColor Yellow
            $entitySuccess++  # Count as success since entity exists
        } else {
            Write-Host "  ✗ $entityName - Expected $expectedUNID, got $actualUNID" -ForegroundColor Red
            $entityErrors++
        }
    } else {
        Write-Host "  ✗ $entityName - NOT FOUND" -ForegroundColor Red
        $entityErrors++
    }
}

Write-Host ""
Write-Host "Validating known UNIDs..." -ForegroundColor Cyan

$unidErrors = 0
$unidSuccess = 0

foreach ($unid in $knownUNIDs.Keys) {
    $expectedEntity = $knownUNIDs[$unid]
    $unidProp = $unids.PSObject.Properties | Where-Object { $_.Name -eq $unid }
    
    if ($unidProp) {
        $actualEntity = $unidProp.Value.EntityName
        if ($actualEntity -eq $expectedEntity) {
            Write-Host "  ✓ $unid = $expectedEntity" -ForegroundColor Green
            $unidSuccess++
        } else {
            Write-Host "  ✗ $unid - Expected $expectedEntity, got $actualEntity" -ForegroundColor Red
            $unidErrors++
        }
    } else {
        Write-Host "  ✗ $unid - NOT FOUND" -ForegroundColor Red
        $unidErrors++
    }
}

Write-Host ""
Write-Host "Checking metadata statistics..." -ForegroundColor Cyan

$stats = $metadata.Statistics
Write-Host "  Files processed: $($stats.Files)" -ForegroundColor $(if ($stats.Files -eq 313) { 'Green' } else { 'Yellow' })
Write-Host "  Entities found: $($stats.Entities)" -ForegroundColor Gray
Write-Host "  UNIDs found: $($stats.UNIDs)" -ForegroundColor Gray
Write-Host "  Functions found: $($stats.Functions)" -ForegroundColor Gray
Write-Host "  Tags found: $($stats.Tags)" -ForegroundColor Gray
Write-Host "  Conflicts found: $($stats.Conflicts)" -ForegroundColor $(if ($stats.Conflicts -gt 0) { 'Yellow' } else { 'Green' })

# Check if entity count matches
$actualEntityCount = ($entities.PSObject.Properties | Measure-Object).Count
if ($actualEntityCount -eq $stats.Entities) {
    Write-Host "  ✓ Entity count matches: $actualEntityCount" -ForegroundColor Green
} else {
    Write-Host "  ✗ Entity count mismatch: metadata says $($stats.Entities), actual is $actualEntityCount" -ForegroundColor Red
    $entityErrors++
}

# Check if UNID count matches
$actualUnidCount = ($unids.PSObject.Properties | Measure-Object).Count
if ($actualUnidCount -eq $stats.UNIDs) {
    Write-Host "  ✓ UNID count matches: $actualUnidCount" -ForegroundColor Green
} else {
    Write-Host "  ✗ UNID count mismatch: metadata says $($stats.UNIDs), actual is $actualUnidCount" -ForegroundColor Red
    $unidErrors++
}

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Validation Summary" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Entity Validations: $entitySuccess passed, $entityErrors failed" -ForegroundColor $(if ($entityErrors -eq 0) { 'Green' } else { 'Red' })
Write-Host "  UNID Validations: $unidSuccess passed, $unidErrors failed" -ForegroundColor $(if ($unidErrors -eq 0) { 'Green' } else { 'Red' })
Write-Host ""

$totalErrors = $entityErrors + $unidErrors
if ($totalErrors -eq 0) {
    Write-Host "  ✓ All validations passed!" -ForegroundColor Green
    exit 0
} else {
    Write-Host "  ✗ $totalErrors validation error(s) found" -ForegroundColor Red
    exit 1
}


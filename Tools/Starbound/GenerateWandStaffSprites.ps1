#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Generate sprites for all Runic Wands and Staves.
    
.DESCRIPTION
    Generates sprites for all wand and staff types defined in the mod's configuration files.
    Includes inventory icons and animation parts.
    
.PARAMETER ModPath
    Path to the mod directory
    
.PARAMETER OllamaModel
    Ollama model to use
    
.PARAMETER UseCppBackend
    Use C++ backend for generation
#>

param(
    [Parameter(Mandatory=$false)]
    [string]$ModPath = "F:\Games\OpenStarbound\mods\Magi-Tech Arcane Alchemy and Sorcery",
    
    [Parameter(Mandatory=$false)]
    [string]$OllamaModel = "codellama:7b-instruct",
    
    [Parameter(Mandatory=$false)]
    [bool]$UseCppBackend = $true)

$ErrorActionPreference = "Stop"
# Validate ModPath is not empty
if ([string]::IsNullOrWhiteSpace($ModPath)) {
    Write-Host "Error: ModPath cannot be empty" -ForegroundColor Red
    Write-Host "  Please provide a valid mod path or use the default" -ForegroundColor Gray
    exit 1
}


# Load shared asset generation settings
$settingsPath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "..\\AssetGenerationSettings.ps1"
if (Test-Path $settingsPath) {
    . $settingsPath
}
$PSScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$assetGenerator = Join-Path $PSScriptRoot "StarboundOllamaAssetGenerator.ps1"

Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Runic Wand & Staff Sprite Generator" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

$allWands = @()
$allStaves = @()
$generated = 0
$failed = 0

# ============================================================
# 1. LOAD WAND TEMPLATES
# ============================================================
Write-Host "Loading wand templates..." -ForegroundColor Yellow

# Validate $ModPath before Join-Path
$wandTemplatesFile = Join-Path $ModPath "cpp_backend\config\wandTemplates.json"
 if ([string]::IsNullOrWhiteSpace($wandTemplatesFile)) {
    Write-Host "  [FAIL] wandTemplatesFile is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($wandTemplatesFile)) {
    Write-Host "  [FAIL] wandTemplatesFile is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (Test-Path $wandTemplatesFile) {
    $wandData = Get-Content $wandTemplatesFile -Raw | ConvertFrom-Json
    
    foreach ($wand in $wandData.wandTemplates) {
        if (-not $wand.isStaff) {
            $allWands += @{
                Id = $wand.id
                Name = $wand.name
                Description = $wand.description
                Tier = $wand.tier
                Tags = $wand.tags -join ", "
            }
        }
    }
}

Write-Host "  Found $($allWands.Count) wand templates" -ForegroundColor Green

# ============================================================
# 2. LOAD STAFF TEMPLATES
# ============================================================
Write-Host "Loading staff templates..." -ForegroundColor Yellow

# Validate $ModPath before Join-Path
$staffTemplatesFile = Join-Path $ModPath "cpp_backend\config\staffTemplates.json"
 if ([string]::IsNullOrWhiteSpace($staffTemplatesFile)) {
    Write-Host "  [FAIL] staffTemplatesFile is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($staffTemplatesFile)) {
    Write-Host "  [FAIL] staffTemplatesFile is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (Test-Path $staffTemplatesFile) {
    $staffData = Get-Content $staffTemplatesFile -Raw | ConvertFrom-Json
    
    foreach ($staff in $staffData.staffTemplates) {
        $allStaves += @{
            Id = $staff.id
            Name = $staff.name
            Description = $staff.description
            Tier = $staff.tier
            Element = $staff.staffElement
            Tags = $staff.tags -join ", "
        }
    }
}

Write-Host "  Found $($allStaves.Count) staff templates" -ForegroundColor Green

# ============================================================
# 3. LOAD MAGITECH WAND TYPES
# ============================================================
Write-Host "Loading magitech wand types..." -ForegroundColor Yellow

# Validate $ModPath before Join-Path
$magitechWandTypesFile = Join-Path $ModPath "cpp_backend\config\magitechWandTypes.json"
 if ([string]::IsNullOrWhiteSpace($magitechWandTypesFile)) {
    Write-Host "  [FAIL] magitechWandTypesFile is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($magitechWandTypesFile)) {
    Write-Host "  [FAIL] magitechWandTypesFile is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (Test-Path $magitechWandTypesFile) {
    $magitechData = Get-Content $magitechWandTypesFile -Raw | ConvertFrom-Json
    
    foreach ($wandType in $magitechData.magitechWandTypes) {
        if ($wandType.isStaff) {
            $allStaves += @{
                Id = $wandType.id
                Name = $wandType.name
                Description = $wandType.description
                Tier = 2
                Element = if ($wandType.staffElement) { $wandType.staffElement } else { "" }
                Tags = "magitech, staff"
            }
        } else {
            $allWands += @{
                Id = $wandType.id
                Name = $wandType.name
                Description = $wandType.description
                Tier = 2
                Tags = "magitech, wand"
            }
        }
    }
}

Write-Host "  Found $($allWands.Count) total wands, $($allStaves.Count) total staves" -ForegroundColor Green
Write-Host ""

# ============================================================
# 4. GENERATE WAND SPRITES
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Wand Sprites" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

foreach ($wand in $allWands) {
    Write-Host "Generating: $($wand.Name) ($($wand.Id))" -ForegroundColor Cyan
    
    # Create enhanced prompt
    $prompt = "A Starbound wand sprite for '$($wand.Description)'. "
    $prompt += "Tier: $($wand.Tier). "
    $prompt += "Tags: $($wand.Tags). "
    $prompt += "Visual style: Magical wand, runic patterns, glowing effects, pixel art aesthetic matching Starbound."
    
    # Add tier-based visual cues
    switch ($wand.Tier) {
        1 { $prompt += " Simple design, basic magical glow." }
        2 { $prompt += " Refined design, enhanced runic patterns, stronger glow." }
        3 { $prompt += " Masterwork design, intricate runes, powerful energy aura." }
    }
    
    try {
        $params = @{
            AssetType = "ItemSprite"
            AssetName = $wand.Id
            Prompt = $prompt
            OllamaModel = $OllamaModel
            OutputDir = (Join-Path $ModPath "assets")
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($wand.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($wand.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 5. GENERATE STAFF SPRITES
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Staff Sprites" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

foreach ($staff in $allStaves) {
    Write-Host "Generating: $($staff.Name) ($($staff.Id))" -ForegroundColor Cyan
    
    # Create enhanced prompt
    $prompt = "A Starbound staff sprite for '$($staff.Description)'. "
    $prompt += "Tier: $($staff.Tier). "
    if ($staff.Element) {
        $prompt += "Element: $($staff.Element). "
    }
    $prompt += "Tags: $($staff.Tags). "
    $prompt += "Visual style: Two-handed magical staff, longer than wand, ornate design, runic patterns, glowing effects, pixel art aesthetic matching Starbound."
    
    # Add tier-based visual cues
    switch ($staff.Tier) {
        1 { $prompt += " Simple staff design, basic magical glow." }
        2 { $prompt += " Refined staff design, enhanced runic patterns, stronger glow, ornate details." }
        3 { $prompt += " Masterwork staff design, intricate runes, powerful energy aura, legendary appearance." }
    }
    
    # Add element-based visual cues
    if ($staff.Element) {
        switch ($staff.Element.ToLower()) {
            "fire" { $prompt += " Fire elemental theme, red/orange colors, flickering flames." }
            "ice" { $prompt += " Ice elemental theme, blue/white colors, frost patterns." }
            "lightning" { $prompt += " Lightning elemental theme, yellow/white colors, electrical arcs." }
            "elemental" { $prompt += " Multi-elemental theme, rainbow colors, swirling energy." }
            "arcane" { $prompt += " Arcane theme, purple colors, swirling magical energy." }
            "temporal" { $prompt += " Temporal theme, clockwork patterns, time distortion effects." }
        }
    }
    
    try {
        $params = @{
            AssetType = "ItemSprite"
            AssetName = $staff.Id
            Prompt = $prompt
            OllamaModel = $OllamaModel
            OutputDir = (Join-Path $ModPath "assets")
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($staff.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($staff.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# SUMMARY
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Generation Complete" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "Generated: $generated sprites" -ForegroundColor Green
Write-Host "Failed: $failed sprites" -ForegroundColor $(if ($failed -gt 0) { "Red" } else { "Green" })
Write-Host ""
Write-Host "Wands: $($allWands.Count) templates" -ForegroundColor Gray
Write-Host "Staves: $($allStaves.Count) templates" -ForegroundColor Gray
Write-Host ""
Write-Host "Sprites saved to: $(Join-Path $ModPath 'assets\items\sprites')" -ForegroundColor Gray
Write-Host ""
Write-Host "Next step: Create item definitions for wands and staves" -ForegroundColor Yellow
Write-Host ""

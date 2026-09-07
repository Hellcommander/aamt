#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Update existing mech form JSON configs with weapon/magic animations and enhanced fields.
    
.DESCRIPTION
    Adds weapon-fire and magic-cast animation references, plus enhanced form data fields
    (tags, elementAffinity, levelCap, statFormulas, environment modifiers, etc.) to existing
    mech form JSON files.
    
.PARAMETER ModPath
    Path to the mod directory
#>

param(
    [Parameter(Mandatory=$false)]
    [string]$ModPath = "F:\Games\OpenStarbound\mods\Magi-Tech Arcane Alchemy and Sorcery"
)

$ErrorActionPreference = "Stop"
# Validate ModPath is not empty
if ([string]::IsNullOrWhiteSpace($ModPath)) {
    Write-Host "Error: ModPath cannot be empty" -ForegroundColor Red
    Write-Host "  Please provide a valid mod path or use the default" -ForegroundColor Gray
    exit 1
}


Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Mech Form Config Updater" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# Validate $ModPath before Join-Path
$formsDir = Join-Path $ModPath "Data\Config\Mechs"
 if ([string]::IsNullOrWhiteSpace($formsDir)) {
    Write-Host "  [FAIL] formsDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($formsDir)) {
    Write-Host "  [FAIL] formsDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $formsDir)) {
    Write-Host "ERROR: Forms directory not found: $formsDir" -ForegroundColor Red
    exit 1
}

$updated = 0
$skipped = 0
$failed = 0

# Get all form JSON files
$formFiles = Get-ChildItem -Path $formsDir -Filter "*Form.json" -ErrorAction SilentlyContinue

foreach ($file in $formFiles) {
    try {
        $formData = Get-Content $file.FullName -Raw | ConvertFrom-Json
        $formId = $formData.id
        $needsUpdate = $false
        
        Write-Host "Processing: $($file.Name) ($formId)" -ForegroundColor Cyan
        
        # Add weapon animations if missing
        if (-not $formData.weaponAimAnimation) {
            $formData | Add-Member -NotePropertyName "weaponAimAnimation" -NotePropertyValue @{
                frames = 6
                frameSize = @(96, 96)
                image = "/sprites/forms/${formId}_weaponAim.png"
            } -Force
            $needsUpdate = $true
        }
        
        if (-not $formData.weaponFireAnimation) {
            $formData | Add-Member -NotePropertyName "weaponFireAnimation" -NotePropertyValue @{
                frames = 4
                frameSize = @(96, 96)
                image = "/sprites/forms/${formId}_weaponFire.png"
            } -Force
            $needsUpdate = $true
        }
        
        if (-not $formData.weaponReloadAnimation) {
            $formData | Add-Member -NotePropertyName "weaponReloadAnimation" -NotePropertyValue @{
                frames = 8
                frameSize = @(96, 96)
                image = "/sprites/forms/${formId}_weaponReload.png"
            } -Force
            $needsUpdate = $true
        }
        
        if (-not $formData.weaponHolsterAnimation) {
            $formData | Add-Member -NotePropertyName "weaponHolsterAnimation" -NotePropertyValue @{
                frames = 6
                frameSize = @(96, 96)
                image = "/sprites/forms/${formId}_weaponHolster.png"
            } -Force
            $needsUpdate = $true
        }
        
        # Add magic animations if missing
        if (-not $formData.orbEmergenceAnimation) {
            $formData | Add-Member -NotePropertyName "orbEmergenceAnimation" -NotePropertyValue @{
                frames = 6
                frameSize = @(96, 96)
                image = "/sprites/forms/${formId}_orbEmerge.png"
            } -Force
            $needsUpdate = $true
        }
        
        if (-not $formData.magicChannelAnimation) {
            $formData | Add-Member -NotePropertyName "magicChannelAnimation" -NotePropertyValue @{
                frames = 8
                frameSize = @(96, 96)
                image = "/sprites/forms/${formId}_magicChannel.png"
            } -Force
            $needsUpdate = $true
        }
        
        if (-not $formData.magicCastAnimation) {
            $formData | Add-Member -NotePropertyName "magicCastAnimation" -NotePropertyValue @{
                frames = 6
                frameSize = @(96, 96)
                image = "/sprites/forms/${formId}_magicCast.png"
            } -Force
            $needsUpdate = $true
        }
        
        if (-not $formData.orbDissipateAnimation) {
            $formData | Add-Member -NotePropertyName "orbDissipateAnimation" -NotePropertyValue @{
                frames = 4
                frameSize = @(96, 96)
                image = "/sprites/forms/${formId}_orbDissipate.png"
            } -Force
            $needsUpdate = $true
        }
        
        # Add enhanced fields if missing
        if (-not $formData.tags) {
            # Infer tags from form data
            $tags = @()
            if ($formData.abilities -and $formData.abilities.charge) { $tags += "combat" }
            if ($formData.abilities -and $formData.abilities.shockwave) { $tags += "charge" }
            if ($formData.locomotion -and $formData.locomotion.type -eq "bipedal") { $tags += "movement" }
            if ($tags.Count -eq 0) { $tags = @("default") }
            $formData | Add-Member -NotePropertyName "tags" -NotePropertyValue $tags -Force
            $needsUpdate = $true
        }
        
        if (-not $formData.elementAffinity) {
            # Try to infer from form name or use default
            $element = "neutral"
            if ($formId -match "fire|phoenix") { $element = "fire" }
            elseif ($formId -match "ice|frost") { $element = "ice" }
            elseif ($formId -match "electric|storm|lightning") { $element = "electric" }
            elseif ($formId -match "earth|stone|rhino") { $element = "earth" }
            elseif ($formId -match "poison|toxic|acid") { $element = "poison" }
            $formData | Add-Member -NotePropertyName "elementAffinity" -NotePropertyValue $element -Force
            $needsUpdate = $true
        }
        
        if (-not $formData.levelCap) {
            $formData | Add-Member -NotePropertyName "levelCap" -NotePropertyValue 5 -Force
            $needsUpdate = $true
        }
        
        if (-not $formData.xpPerKill) {
            $formData | Add-Member -NotePropertyName "xpPerKill" -NotePropertyValue 10 -Force
            $needsUpdate = $true
        }
        
        if (-not $formData.upgradeSlots) {
            $formData | Add-Member -NotePropertyName "upgradeSlots" -NotePropertyValue 1 -Force
            $needsUpdate = $true
        }
        
        if (-not $formData.statFormulas) {
            $formData | Add-Member -NotePropertyName "statFormulas" -NotePropertyValue @{
                armorMult = "1 + level*0.2"
                speedMult = "1.1 + level*0.03"
            } -Force
            $needsUpdate = $true
        }
        
        if (-not $formData.factions) {
            $formData | Add-Member -NotePropertyName "factions" -NotePropertyValue @{
                allow = @("player", "ally")
                deny = @("hostile")
            } -Force
            $needsUpdate = $true
        }
        
        if (-not $formData.environment) {
            $formData | Add-Member -NotePropertyName "environment" -NotePropertyValue @{
                underwater = @{
                    speedMult = 0.7
                }
                lava = @{
                    armorMult = 1.2
                }
            } -Force
            $needsUpdate = $true
        }
        
        if (-not $formData.collisionBox) {
            $formData | Add-Member -NotePropertyName "collisionBox" -NotePropertyValue @(
                @(-1, -1),
                @(1, -1),
                @(1, 1.5),
                @(-1, 1.5)
            ) -Force
            $needsUpdate = $true
        }
        
        # Update file if changes were made
        if ($needsUpdate) {
            # Convert back to JSON with proper formatting
            $jsonContent = $formData | ConvertTo-Json -Depth 10
            
            # Create backup
            $backupPath = "$($file.FullName).backup"
            Copy-Item -Path $file.FullName -Destination $backupPath -Force
            
            # Write updated JSON
            Set-Content -Path $file.FullName -Value $jsonContent -Encoding UTF8
            $updated++
            Write-Host "  [OK] Updated form config: $formId" -ForegroundColor Green
        } else {
            $skipped++
            Write-Host "  [SKIP] Form already has all fields: $formId" -ForegroundColor Gray
        }
    } catch {
        $failed++
        Write-Host "  [FAIL] Error processing $($file.Name): $_" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Update Complete" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "Updated: $updated forms" -ForegroundColor Green
Write-Host "Skipped: $skipped forms (already complete)" -ForegroundColor Gray
Write-Host "Failed: $failed forms" -ForegroundColor $(if ($failed -gt 0) { "Red" } else { "Green" })
Write-Host ""
Write-Host "Backups created with .backup extension" -ForegroundColor Yellow
Write-Host ""

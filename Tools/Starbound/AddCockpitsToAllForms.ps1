# AddCockpitsToAllForms.ps1
# Adds cockpit specifications to all mech form JSON files

$ErrorActionPreference = "Stop"
$modPath = "F:\Games\OpenStarbound\mods\Magi-Tech Arcane Alchemy and Sorcery"
$mechsDir = "$modPath\Data\Config\Mechs"

# Load cockpit system config
$cockpitConfig = Get-Content "$mechsDir\CockpitSystem.json" | ConvertFrom-Json

# Get all form JSON files
$formFiles = Get-ChildItem "$mechsDir\*Form.json" | Where-Object { $_.Name -ne "CockpitSystem.json" }

Write-Host "=== Adding Cockpit Specifications to All Mech Forms ===" -ForegroundColor Cyan
Write-Host "Found $($formFiles.Count) form files" -ForegroundColor Yellow

foreach ($formFile in $formFiles) {
    Write-Host "`nProcessing: $($formFile.Name)" -ForegroundColor Green
    
    $formJson = Get-Content $formFile.FullName | ConvertFrom-Json
    $formId = $formJson.id
    
    # Check if cockpit already exists
    if ($formJson.cockpit) {
        Write-Host "  Cockpit already exists, skipping..." -ForegroundColor Gray
        continue
    }
    
    # Get form-specific cockpit config or use default
    $cockpitSpec = $cockpitConfig.formSpecificCockpits.$formId
    if (-not $cockpitSpec) {
        $cockpitSpec = $cockpitConfig.cockpitSpecs.default
    }
    
    # Build cockpit object
    $cockpit = @{
        enabled = $true
        position = $cockpitSpec.cockpitPosition
        size = $cockpitSpec.cockpitSize
        shape = $cockpitSpec.shape
        alphaChannel = $true
        transparencyLevel = if ($cockpitSpec.transparencyLevel) { $cockpitSpec.transparencyLevel } else { 0.3 }
        frameStyle = $cockpitSpec.frameStyle
        frameThickness = if ($cockpitSpec.frameThickness) { $cockpitSpec.frameThickness } else { 2 }
        frameColor = if ($cockpitSpec.frameColor) { $cockpitSpec.frameColor } else { @(100, 100, 120, 255) }
        glassTint = if ($cockpitSpec.glassTint) { $cockpitSpec.glassTint } else { @(200, 200, 220, 180) }
        playerVisible = $true
        playerScale = 0.8
        playerOffset = @(0, -0.2)
    }
    
    # Add cockpit before onEnter
    $formJson | Add-Member -MemberType NoteProperty -Name "cockpit" -Value $cockpit -Force
    
    # Convert back to JSON with proper formatting
    $jsonContent = $formJson | ConvertTo-Json -Depth 10
    
    # Write back to file
    Set-Content -Path $formFile.FullName -Value $jsonContent
    
    Write-Host "  Added cockpit: $($cockpitSpec.shape) at $($cockpitSpec.cockpitPosition)" -ForegroundColor White
}

Write-Host "`n=== Cockpit Addition Complete ===" -ForegroundColor Cyan
Write-Host "All forms now have cockpit specifications with alpha channel transparency" -ForegroundColor Green

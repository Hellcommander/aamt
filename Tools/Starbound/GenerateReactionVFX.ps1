# GenerateReactionVFX.ps1
# Generates particle VFX for all reaction types

param(
    [bool]$UseCppBackend = $true,
    [switch]$SkipExisting
)

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
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$modPath = "F:\Games\OpenStarbound\mods\Magi-Tech Arcane Alchemy and Sorcery"

# Load reaction definitions
$reactionConfig = Get-Content "$modPath\config\enhancedAlchemicalGrenadeLauncher.json" | ConvertFrom-Json
$reactions = $reactionConfig.reactions.PSObject.Properties | ForEach-Object { $_.Name }

Write-Host "=== Generating Reaction VFX Particles ===" -ForegroundColor Cyan
Write-Host "Found $($reactions.Count) reactions" -ForegroundColor Yellow

# Ensure directory exists
$particleDir = "$modPath\particles\reactions"
if (-not (Test-Path $particleDir)) {
    New-Item -ItemType Directory -Path $particleDir -Force | Out-Null
}

foreach ($reactionId in $reactions) {
    $particlePath = "$particleDir\$reactionId.particle"
    
    if ($SkipExisting -and (Test-Path $particlePath)) {
        Write-Host "  Skipping existing: $reactionId" -ForegroundColor Gray
        continue
    }
    
    $reaction = $reactionConfig.reactions.$reactionId
    
    # Determine particle style from reaction category
    $particleStyle = "explosion"
    if ($reaction.category) {
        switch ($reaction.category) {
            "combustion" { $particleStyle = "fire" }
            "phase_change" { $particleStyle = "ice" }
            "corrosive" { $particleStyle = "acid" }
            "magical" { $particleStyle = "magic" }
            "explosive" { $particleStyle = "explosion" }
            default { $particleStyle = "generic" }
        }
    }
    
    $params = @{
        AssetType = "Particle"
        Name = "reaction_$reactionId"
        UseCppBackend = $UseCppBackend
        Parameters = @{
            ReactionType = $reactionId
            Category = $reaction.category
            ParticleStyle = $particleStyle
            Intensity = "high"
            Duration = $reaction.duration
            Radius = 5.0
        }
    }
    
    Write-Host "  Generating VFX: $reactionId ($particleStyle)" -ForegroundColor White
    & "$scriptPath\StarboundOllamaAssetGenerator.ps1" @params
}

Write-Host "`n=== Reaction VFX Generation Complete ===" -ForegroundColor Cyan

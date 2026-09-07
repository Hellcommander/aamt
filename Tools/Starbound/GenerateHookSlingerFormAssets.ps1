# GenerateHookSlingerFormAssets.ps1
# Generates assets for the Hook Slinger mech form
# Includes: hook projectiles, rope VFX, swing sounds, UI crosshair hints

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

Write-Host "=== Generating Hook Slinger Form Assets ===" -ForegroundColor Cyan

# 1. Generate Hook Projectile Sprites
Write-Host "[1/6] Generating hook projectile sprites..." -ForegroundColor Green
$hookSprites = @(
    @{Name="hook1"; Color=@(100,200,255); Type="primary"},
    @{Name="hook2"; Color=@(200,100,255); Type="secondary"}
)

foreach ($hook in $hookSprites) {
    $spritePath = "$modPath\projectiles\$($hook.Name).png"
    if ($SkipExisting -and (Test-Path $spritePath)) {
        Write-Host "  Skipping existing: $($hook.Name)" -ForegroundColor Gray
        continue
    }
    
    $params = @{
        AssetType = "Sprite"
        AssetName = "hook_projectile_$($hook.Name)"
        Width = 16
        Height = 16
        UseCppBackend = $UseCppBackend
        Parameters = @{
            Style = "grappling_hook"
            Color = $hook.Color
            Type = $hook.Type
        }
    }
    
    Write-Host "  Generating: $($hook.Name)" -ForegroundColor White
    & "$scriptPath\StarboundOllamaAssetGenerator.ps1" @params
}

# 2. Generate Rope/Cable VFX
Write-Host "[2/6] Generating rope VFX particles..." -ForegroundColor Green
$ropeVFX = @("ropeActive", "ropeSnap", "ropeAttach")

foreach ($vfx in $ropeVFX) {
    $particlePath = "$modPath\particles\$vfx.particle"
    if ($SkipExisting -and (Test-Path $particlePath)) {
        Write-Host "  Skipping existing: $vfx" -ForegroundColor Gray
        continue
    }
    
    $params = @{
        AssetType = "Particle"
        AssetName = "hookSlinger_$vfx"
        UseCppBackend = $UseCppBackend
        Parameters = @{
            FormID = "hookSlinger"
            Type = $vfx
            Color = @(150, 200, 255)
        }
    }
    
    Write-Host "  Generating: $vfx" -ForegroundColor White
    & "$scriptPath\StarboundOllamaAssetGenerator.ps1" @params
}

# 3. Generate Hook Sounds
Write-Host "[3/6] Generating hook sound effects..." -ForegroundColor Green
$hookSounds = @(
    @{Name="hookShoot1"; Type="shoot"; Pitch=1.0},
    @{Name="hookShoot2"; Type="shoot"; Pitch=1.1},
    @{Name="hookRetract"; Type="retract"; Pitch=0.9},
    @{Name="hookAttach"; Type="attach"; Pitch=1.0},
    @{Name="ropeSnap"; Type="snap"; Pitch=1.2}
)

foreach ($sound in $hookSounds) {
    $soundPath = "$modPath\sfx\$($sound.Name).wav"
    if ($SkipExisting -and (Test-Path $soundPath)) {
        Write-Host "  Skipping existing: $($sound.Name)" -ForegroundColor Gray
        continue
    }
    
    $params = @{
        AssetType = "Sound"
        AssetName = "hookSlinger_$($sound.Name)"
        UseCppBackend = $UseCppBackend
        Parameters = @{
            FormID = "hookSlinger"
            Type = $sound.Type
            Pitch = $sound.Pitch
            Duration = 0.5
        }
    }
    
    Write-Host "  Generating: $($sound.Name)" -ForegroundColor White
    & "$scriptPath\StarboundOllamaAssetGenerator.ps1" @params
}

# 4. Generate Swing Animation Frames
Write-Host "[4/6] Generating swing animation frames..." -ForegroundColor Green
$swingAnimPath = "$modPath\sprites\forms\hookSlinger_swing.png"

if (-not ($SkipExisting -and (Test-Path $swingAnimPath))) {
    $params = @{
        AssetType = "Animation"
        AssetName = "hookSlinger_swing"
        UseCppBackend = $UseCppBackend
        Parameters = @{
            FormID = "hookSlinger"
            AnimationType = "swing"
            FrameCount = 10
            FrameSize = @(96, 96)
            Description = "Swinging from hook animation"
        }
    }
    
    & "$scriptPath\StarboundOllamaAssetGenerator.ps1" @params
}

# 5. Generate Grapple Fire/Pull Animations
Write-Host "[5/6] Generating grapple animations..." -ForegroundColor Green
$grappleAnims = @(
    @{Name="grapple_fire"; Frames=6},
    @{Name="grapple_pull"; Frames=8}
)

foreach ($anim in $grappleAnims) {
    $animPath = "$modPath\sprites\forms\hookSlinger_$($anim.Name).png"
    if ($SkipExisting -and (Test-Path $animPath)) {
        Write-Host "  Skipping existing: $($anim.Name)" -ForegroundColor Gray
        continue
    }
    
    $params = @{
        AssetType = "Animation"
        AssetName = "hookSlinger_$($anim.Name)"
        UseCppBackend = $UseCppBackend
        Parameters = @{
            FormID = "hookSlinger"
            AnimationType = $anim.Name
            FrameCount = $anim.Frames
            FrameSize = @(96, 96)
        }
    }
    
    Write-Host "  Generating: $($anim.Name)" -ForegroundColor White
    & "$scriptPath\StarboundOllamaAssetGenerator.ps1" @params
}

# 6. Generate UI Crosshair for Valid Hook Targets
Write-Host "[6/6] Generating UI crosshair sprites..." -ForegroundColor Green
$crosshairSprites = @("hookValid", "hookInvalid", "hookMaxRange")

foreach ($crosshair in $crosshairSprites) {
    $crosshairPath = "$modPath\interface\hookSlinger\$crosshair.png"
    if ($SkipExisting -and (Test-Path $crosshairPath)) {
        Write-Host "  Skipping existing: $crosshair" -ForegroundColor Gray
        continue
    }
    
    $color = switch ($crosshair) {
        "hookValid" { @(0, 255, 0) }
        "hookInvalid" { @(255, 0, 0) }
        "hookMaxRange" { @(255, 255, 0) }
    }
    
    $params = @{
        AssetType = "Sprite"
        AssetName = "hookSlinger_crosshair_$crosshair"
        Width = 32
        Height = 32
        UseCppBackend = $UseCppBackend
        Parameters = @{
            Style = "crosshair"
            Color = $color
            Type = $crosshair
        }
    }
    
    Write-Host "  Generating: $crosshair" -ForegroundColor White
    & "$scriptPath\StarboundOllamaAssetGenerator.ps1" @params
}

Write-Host "`n=== Hook Slinger Form Asset Generation Complete ===" -ForegroundColor Cyan
Write-Host "Generated: hook projectiles, rope VFX, sounds, animations, UI crosshairs" -ForegroundColor Green

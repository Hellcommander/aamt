# GenerateMechFormAnimations.ps1
# Generates animation spritesheets for mech forms
# Each form gets 136 frames across 18 animation cycles

param(
    [bool]$UseCppBackend = $true,
    [switch]$SkipExisting,
    [string]$FormID = ""  # Empty = all forms
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

# Animation cycle definitions (136 total frames)
$animationCycles = @(
    @{Name="idle"; Frames=8; Description="Standing idle"},
    @{Name="walk"; Frames=12; Description="Walking animation"},
    @{Name="run"; Frames=12; Description="Running animation"},
    @{Name="jump"; Frames=8; Description="Jump animation"},
    @{Name="swim"; Frames=8; Description="Swimming animation"},
    @{Name="dash"; Frames=6; Description="Dash movement"},
    @{Name="dodge"; Frames=6; Description="Dodge/evade"},
    @{Name="wallSlide"; Frames=6; Description="Wall sliding"},
    @{Name="wallJumpLaunch"; Frames=8; Description="Wall jump launch"},
    @{Name="wallJumpRecover"; Frames=4; Description="Wall jump recovery"},
    @{Name="charge"; Frames=10; Description="Charging energy"},
    @{Name="orbEmerge"; Frames=6; Description="Orb emergence"},
    @{Name="channel"; Frames=8; Description="Channeling magic"},
    @{Name="cast"; Frames=6; Description="Casting spell"},
    @{Name="orbDissipate"; Frames=4; Description="Orb dissipation"},
    @{Name="weaponAim"; Frames=6; Description="Aiming weapon"},
    @{Name="weaponFire"; Frames=4; Description="Firing weapon"},
    @{Name="weaponReload"; Frames=8; Description="Reloading weapon"},
    @{Name="weaponHolster"; Frames=6; Description="Holstering weapon"}
)

$formIDs = @("biped", "hookSlinger", "centipede", "rhino", "jet", "bladeCyclone", "stealth", "magma", "gorilla", "walker")
if ($FormID -ne "") {
    $formIDs = @($FormID)
}

Write-Host "=== Generating Mech Form Animations ===" -ForegroundColor Cyan
Write-Host "Forms: $($formIDs.Count) | Cycles per form: $($animationCycles.Count)" -ForegroundColor Yellow
Write-Host "NOTE: All animations must include visible cockpit with alpha channel for player visibility" -ForegroundColor Yellow

foreach ($formId in $formIDs) {
    Write-Host "`nProcessing $formId animations..." -ForegroundColor Green
    
    foreach ($anim in $animationCycles) {
        $spritePath = "$modPath\sprites\forms\$($formId)_$($anim.Name).png"
        
        if ($SkipExisting -and (Test-Path $spritePath)) {
            Write-Host "  Skipping existing: $($anim.Name) ($($anim.Frames) frames)" -ForegroundColor Gray
            continue
        }
        
        Write-Host "  Generating: $($anim.Name) ($($anim.Frames) frames)" -ForegroundColor White
        
        # Load form config to get cockpit specs
        $formConfigPath = "$modPath\Data\Config\Mechs\${formId}Form.json"
        $cockpitSpec = $null
        if (Test-Path $formConfigPath) {
            $formConfig = Get-Content $formConfigPath | ConvertFrom-Json
            if ($formConfig.cockpit) {
                $cockpitSpec = $formConfig.cockpit
            }
        }
        
        $params = @{
            AssetType = "Animation"
            AssetName = "$($formId)_$($anim.Name)"
            UseCppBackend = $UseCppBackend
            Parameters = @{
                FormID = $formId
                AnimationType = $anim.Name
                FrameCount = $anim.Frames
                FrameSize = @(96, 96)
                Description = $anim.Description
                IncludeCockpit = $true
                CockpitSpec = $cockpitSpec
                AlphaChannel = $true
                PlayerVisible = $true
            }
        }
        
        & "$scriptPath\StarboundOllamaAssetGenerator.ps1" @params
    }
}

Write-Host "`n=== Mech Form Animation Generation Complete ===" -ForegroundColor Cyan

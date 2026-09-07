# GenerateAllMechFormAssets.ps1
# Master script to generate assets for all 10 MagiTech mech forms
# Generates: icons, animations, VFX particles, sound effects for all forms

param(
    [bool]$UseCppBackend = $true,
    [switch]$SkipExisting,
    [string[]]$FormsToGenerate = @()  # Empty = all forms
)

$ErrorActionPreference = "Stop"
# Validate ModPath is not empty
if ([string]::IsNullOrWhiteSpace($ModPath)) {
    Write-Host "Error: ModPath cannot be empty" -ForegroundColor Red
    Write-Host "  Please provide a valid mod path or use the default" -ForegroundColor Gray
    exit 1
}


# Load shared asset generation settings from Tools root
$settingsPath = Join-Path (Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)) "AssetGenerationSettings.ps1"
if (Test-Path $settingsPath) {
    . $settingsPath
}
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$modPath = "F:\Games\OpenStarbound\mods\Magi-Tech Arcane Alchemy and Sorcery"

# Define all 10 mech forms with their properties
$mechForms = @(
    @{ID="biped"; Name="Biped"; Role="All-Purpose"; Color=@(150,150,150); Slot=0},
    @{ID="hookSlinger"; Name="Hook Slinger"; Role="Traversal"; Color=@(100,200,255); Slot=1},
    @{ID="centipede"; Name="Centipede"; Role="Terrain Control"; Color=@(100,255,100); Slot=2},
    @{ID="rhino"; Name="Rhino"; Role="Impact Combat"; Color=@(180,180,180); Slot=3},
    @{ID="jet"; Name="Jet"; Role="Aerial Assault"; Color=@(200,220,255); Slot=4},
    @{ID="bladeCyclone"; Name="Blade Cyclone"; Role="Area DPS"; Color=@(220,220,255); Slot=5},
    @{ID="stealth"; Name="Stealth"; Role="Infiltration"; Color=@(80,80,120); Slot=6},
    @{ID="magma"; Name="Magma"; Role="Environmental"; Color=@(255,100,50); Slot=7},
    @{ID="gorilla"; Name="Gorilla"; Role="Heavy Melee"; Color=@(120,80,60); Slot=8},
    @{ID="walker"; Name="Walker"; Role="Turret/Defense"; Color=@(150,150,180); Slot=9}
)

# Filter forms if specific ones requested
if ($FormsToGenerate.Count -gt 0) {
    $mechForms = $mechForms | Where-Object { $FormsToGenerate -contains $_.ID }
}

Write-Host "=== Generating MagiTech Mech Form Assets ===" -ForegroundColor Cyan
Write-Host "Forms to generate: $($mechForms.Count)" -ForegroundColor Yellow

foreach ($form in $mechForms) {
    Write-Host "`n[Slot $($form.Slot)] Processing $($form.Name) Form..." -ForegroundColor Green
    
    # Load form config for cockpit specs
    $formConfigPath = "$modPath\Data\Config\Mechs\$($form.Name -replace ' ','')Form.json"
    $cockpitSpec = $null
    if (Test-Path $formConfigPath) {
        $formConfig = Get-Content $formConfigPath | ConvertFrom-Json
        if ($formConfig.cockpit) {
            $cockpitSpec = $formConfig.cockpit
        }
    }
    
    # 1. Generate Form Icon (48x48 for wheel, 64x64 for UI)
    Write-Host "  [1/4] Generating form icons..." -ForegroundColor White
    $iconPath48 = "$modPath\interface\icons\forms\$($form.ID).png"
    $iconPath64 = "$modPath\interface\icons\forms\$($form.ID)_large.png"
    
    if (-not ($SkipExisting -and (Test-Path $iconPath48))) {
        $params = @{
            AssetType = "Icon"
            AssetName = "form_$($form.ID)"
            Size = 48
            Shape = "Circle"
            UseCppBackend = $UseCppBackend
            Parameters = @{
                Color = $form.Color
                Glow = $true
                GlowIntensity = 0.7
                Label = $form.Name
                Role = $form.Role
                IncludeCockpit = $true
                CockpitSpec = $cockpitSpec
            }
        }
        & "$scriptPath\StarboundOllamaAssetGenerator.ps1" @params
    }
    
    if (-not ($SkipExisting -and (Test-Path $iconPath64))) {
        $params = @{
            AssetType = "Icon"
            AssetName = "form_$($form.ID)_large"
            Size = 64
            Shape = "Circle"
            UseCppBackend = $UseCppBackend
            Parameters = @{
                Color = $form.Color
                Glow = $true
                GlowIntensity = 0.7
                Label = $form.Name
            }
        }
        & "$scriptPath\StarboundOllamaAssetGenerator.ps1" @params
    }
    
    # 2. Generate VFX Particles (enter, exit)
    Write-Host "  [2/4] Generating VFX particles..." -ForegroundColor White
    $particleEnterPath = "$modPath\particles\$($form.ID)Enter.particle"
    $particleExitPath = "$modPath\particles\$($form.ID)Exit.particle"
    
    if (-not ($SkipExisting -and (Test-Path $particleEnterPath))) {
        $params = @{
            AssetType = "Particle"
            AssetName = "$($form.ID)_enter"
            UseCppBackend = $UseCppBackend
            Parameters = @{
                FormID = $form.ID
                Type = "enter"
                Color = $form.Color
                Intensity = "high"
            }
        }
        & "$scriptPath\StarboundOllamaAssetGenerator.ps1" @params
    }
    
    if (-not ($SkipExisting -and (Test-Path $particleExitPath))) {
        $params = @{
            AssetType = "Particle"
            AssetName = "$($form.ID)_exit"
            UseCppBackend = $UseCppBackend
            Parameters = @{
                FormID = $form.ID
                Type = "exit"
                Color = $form.Color
                Intensity = "medium"
            }
        }
        & "$scriptPath\StarboundOllamaAssetGenerator.ps1" @params
    }
    
    # 3. Generate Sound Effects (activate, deactivate)
    Write-Host "  [3/4] Generating sound effects..." -ForegroundColor White
    $sfxActivatePath = "$modPath\sfx\$($form.ID)_activate.wav"
    $sfxDeactivatePath = "$modPath\sfx\$($form.ID)_deactivate.wav"
    
    if (-not ($SkipExisting -and (Test-Path $sfxActivatePath))) {
        $params = @{
            AssetType = "Sound"
            AssetName = "$($form.ID)_activate"
            UseCppBackend = $UseCppBackend
            Parameters = @{
                FormID = $form.ID
                Type = "activate"
                Duration = 1.0
            }
        }
        & "$scriptPath\StarboundOllamaAssetGenerator.ps1" @params
    }
    
    if (-not ($SkipExisting -and (Test-Path $sfxDeactivatePath))) {
        $params = @{
            AssetType = "Sound"
            AssetName = "$($form.ID)_deactivate"
            UseCppBackend = $UseCppBackend
            Parameters = @{
                FormID = $form.ID
                Type = "deactivate"
                Duration = 0.8
            }
        }
        & "$scriptPath\StarboundOllamaAssetGenerator.ps1" @params
    }
    
    # 4. Call individual form asset generator if exists
    Write-Host "  [4/4] Calling form-specific asset generator..." -ForegroundColor White
    $formScriptPath = "$scriptPath\Generate$($form.Name -replace ' ','')FormAssets.ps1"
    if (Test-Path $formScriptPath) {
        & $formScriptPath -UseCppBackend $UseCppBackend -SkipExisting:$SkipExisting
    } else {
        Write-Host "    No specific script found for $($form.Name), skipping..." -ForegroundColor Gray
    }
}

Write-Host "`n=== All Mech Form Assets Generation Complete ===" -ForegroundColor Cyan
Write-Host "Generated assets for $($mechForms.Count) forms" -ForegroundColor Green

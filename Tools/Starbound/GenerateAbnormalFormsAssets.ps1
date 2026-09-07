# GenerateAbnormalFormsAssets.ps1
# Generates assets for all abnormal segmented mech forms

param(
    [bool]$UseCppBackend = $true,
    [string]$ModPath = "F:\Games\OpenStarbound\mods\Magi-Tech Arcane Alchemy and Sorcery"
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

# Use Ollama-based asset generator for AI-assisted high-quality asset generation
# Validate $scriptPath before Join-Path
$ollamaGenerator = Join-Path $scriptPath "StarboundOllamaAssetGenerator.ps1"
if ([string]::IsNullOrWhiteSpace($ollamaGenerator)) {
    Write-Host "  [FAIL] ollamaGenerator is null (${scriptPath}: '${scriptPath}')" -ForegroundColor Red
    exit 1
}
if (-not (Test-Path $ollamaGenerator)) {
    Write-Error "StarboundOllamaAssetGenerator.ps1 not found at $ollamaGenerator"
    exit 1
}
Write-Host "Using AI-assisted asset generation with Ollama for high-quality assets" -ForegroundColor Green

$forms = @(
    @{
        Id="coilSerpent"
        Name="Coil Serpent Mech"
        Theme="serpentine_ambush"
        Type="serpentine"
        Segments=@("head", "neck", "neck", "neck", "neck", "core", "tail")
    },
    @{
        Id="crystalSpire"
        Name="Crystal Spire Mech"
        Theme="crystal_support"
        Type="stationary"
        Segments=@("base", "nodeA", "nodeB", "nodeC", "antenna")
    },
    @{
        Id="riftWyrm"
        Name="Rift Wyrm Mech"
        Theme="void_teleport"
        Type="serpentine"
        Segments=@("head", "warp1", "warp2", "warp3", "core")
    },
    @{
        Id="echoWalker"
        Name="Echo Walker Mech"
        Theme="ecm_sensor"
        Type="bipedal"
        Segments=@("footL", "legL", "torso", "legR", "footR", "sensorArray")
    },
    @{
        Id="bloomHarvester"
        Name="Bloom Harvester Mech"
        Theme="organic_harvester"
        Type="rooted"
        Segments=@("rootBase", "stalk1", "stalk2", "stalk3", "stalk4", "stalk5", "bloom")
    },
    @{
        Id="fractureColossus"
        Name="Fracture Colossus Mech"
        Theme="siege_boss"
        Type="quadrupedal"
        Segments=@("foot1", "foot2", "foot3", "foot4", "torso", "armL", "armR", "core")
    },
    @{
        Id="phaseSwarm"
        Name="Phase Swarm Mech"
        Theme="swarm_controller"
        Type="hover"
        Segments=@("core", "bay1", "bay2", "bay3", "bay4", "bay5", "bay6")
    }
)

Write-Host "Generating assets for $($forms.Count) abnormal segmented mech forms..." -ForegroundColor Cyan

foreach ($form in $forms) {
    Write-Host "`n=== $($form.Name) ($($form.Type)) ===" -ForegroundColor Yellow
    
    # Validate $ModPath before Join-Path
    $formPath = Join-Path $ModPath "Data\Config\Mechs\$($form.Id)Form.json"
    if ([string]::IsNullOrWhiteSpace($formPath)) {
        Write-Host "  [FAIL] formPath is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
        continue
    }
    if (-not (Test-Path $formPath)) {
        Write-Warning "Form config not found: $formPath"
        continue
    }
    
    try {
        # Generate icon using Ollama
        Write-Host "  Generating icon with Ollama..." -ForegroundColor Gray
        $iconParams = @{
            AssetType = "Icon"
            AssetName = "$($form.Id)Form"
            Prompt = "$($form.Name) - Abnormal segmented mech form with $($form.Theme) theme, $($form.Type) type, $($form.Segments.Count) segments"
            Parameters = @{
                Size = 64
                Shape = "Circle"
                ColorScheme = $form.Theme
                MechType = $form.Type
                Segmented = $true
                SegmentCount = $form.Segments.Count
            }
            UseCppBackend = $UseCppBackend
        }
        & $ollamaGenerator @iconParams
        
        # Generate VFX particles
        Write-Host "  Generating VFX particles..." -ForegroundColor Gray
        $vfxTypes = @("Enter", "Idle", "Exit")
        foreach ($vfxType in $vfxTypes) {
            $vfxParams = @{
                AssetType = "Particle"
                AssetName = "$($form.Id)$($vfxType)"
                Prompt = "$($form.Name) $($vfxType.ToLower()) particle effect with $($form.Theme) theme, $($form.Type) mech type, segmented design"
                Parameters = @{
                    Category = "mechForm"
                    Intensity = "medium"
                    ColorScheme = $form.Theme
                    MechType = $form.Type
                    Segmented = $true
                }
                UseCppBackend = $UseCppBackend
            }
            & $ollamaGenerator @vfxParams
        }
        
        # Generate segment sprites
        Write-Host "  Generating segment sprites..." -ForegroundColor Gray
        foreach ($segment in $form.Segments) {
            $segmentParams = @{
                AssetType = "Sprite"
                AssetName = "$($form.Id)_$segment"
                Prompt = "$($form.Name) $segment segment sprite, $($form.Theme) theme, $($form.Type) mech type, detailed and high-quality"
                Parameters = @{
                    Width = 96
                    Height = 96
                    Category = "mechSegment"
                    SegmentType = $segment
                    ColorScheme = $form.Theme
                    MechType = $form.Type
                }
                UseCppBackend = $UseCppBackend
            }
            & $ollamaGenerator @segmentParams
        }
        
        # Generate SFX
        Write-Host "  Generating sound effects..." -ForegroundColor Gray
        $sfxTypes = @("activate", "deactivate", "idle")
        foreach ($sfxType in $sfxTypes) {
            $sfxParams = @{
                AssetType = "Sound"
                AssetName = "$($form.Id)_$($sfxType)"
                Prompt = "$($form.Name) $sfxType sound effect, $($form.Theme) theme, $($form.Type) mech type, segmented design"
                Parameters = @{
                    Category = "mechForm"
                    MechType = $form.Type
                    Theme = $form.Theme
                    Segmented = $true
                }
                UseCppBackend = $UseCppBackend
            }
            & $ollamaGenerator @sfxParams
        }
        
        Write-Host "  ✓ $($form.Name) assets generated" -ForegroundColor Green
        
    } catch {
        Write-Error "Failed to generate assets for $($form.Name): $_"
    }
}

Write-Host "`n=== Asset Generation Complete ===" -ForegroundColor Cyan
Write-Host "Generated assets for $($forms.Count) abnormal segmented mech forms" -ForegroundColor Green
Write-Host 'Note: Segment sprites, animations, and complex VFX may require manual refinement' -ForegroundColor Yellow

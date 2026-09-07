# GenerateHorrorFormsAssets.ps1
# Generates assets for all horror-themed mech forms

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
    continue
}
 if ([string]::IsNullOrWhiteSpace($ollamaGenerator)) {
    Write-Host "  [FAIL] ollamaGenerator is null (${scriptPath}: '${scriptPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $ollamaGenerator)) {
    Write-Error "StarboundOllamaAssetGenerator.ps1 not found at $ollamaGenerator"
    exit 1
}
Write-Host "Using AI-assisted asset generation with Ollama for high-quality assets" -ForegroundColor Green

$forms = @(
    @{
        Id="eldritchAbomination"
        Name="Eldritch Abomination Mech"
        HorrorType="cosmic_eldritch"
        Theme="void_horror"
        ColorScheme=@("deep_purple", "void_black", "sickly_green")
    },
    @{
        Id="necroticReaper"
        Name="Necrotic Reaper Mech"
        HorrorType="undead_necrotic"
        Theme="death_horror"
        ColorScheme=@("bone_white", "necrotic_green", "dark_gray")
    },
    @{
        Id="parasiticNightmare"
        Name="Parasitic Nightmare Mech"
        HorrorType="parasitic_infestation"
        Theme="corruption_horror"
        ColorScheme=@("flesh_pink", "corruption_purple", "sick_yellow")
    },
    @{
        Id="fleshWeaver"
        Name="Flesh Weaver Mech"
        HorrorType="body_horror"
        Theme="biomechanical_horror"
        ColorScheme=@("raw_red", "muscle_purple", "tendon_white")
    },
    @{
        Id="phantomShroud"
        Name="Phantom Shroud Mech"
        HorrorType="spectral_psychological"
        Theme="ghost_horror"
        ColorScheme=@("spectral_blue", "ethereal_white", "ghostly_gray")
    }
)

Write-Host "Generating assets for $($forms.Count) horror-themed mech forms..." -ForegroundColor Cyan
Write-Host "WARNING: Horror assets may contain disturbing imagery" -ForegroundColor Yellow

foreach ($form in $forms) {
    Write-Host "`n=== $($form.Name) ($($form.HorrorType)) ===" -ForegroundColor Magenta
    
    # Validate $ModPath before Join-Path
$formPath = Join-Path $ModPath "Data\Config\Mechs\$($form.Id)Form.json"
 if ([string]::IsNullOrWhiteSpace($formPath)) {
        Write-Host "  [FAIL] formPath is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
        continue
    }
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
            Prompt = "$($form.Name) - Horror themed mech form with $($form.HorrorType) horror type, $($form.Theme) theme, disturbing imagery"
            Parameters = @{
                Size = 64
                Shape = "Circle"
                ColorScheme = $form.Theme
                HorrorType = $form.HorrorType
                Colors = $form.ColorScheme
                Disturbing = $true
            }
            UseCppBackend = $UseCppBackend
        }
        & $ollamaGenerator @iconParams
        
        # Generate VFX particles (horror-specific)
        Write-Host "  Generating horror VFX particles..." -ForegroundColor Gray
        $vfxTypes = @("Enter", "Idle", "Exit")
        foreach ($vfxType in $vfxTypes) {
            $vfxParams = @{
                AssetType = "Particle"
                AssetName = "$($form.Id)$($vfxType)"
                Prompt = "$($form.Name) $($vfxType.ToLower()) particle effect with $($form.Theme) theme, $($form.HorrorType) horror type, disturbing visuals"
                Parameters = @{
                    Category = "mechForm"
                    Intensity = "high"
                    ColorScheme = $form.Theme
                    HorrorType = $form.HorrorType
                    Disturbing = $true
                }
                UseCppBackend = $UseCppBackend
            }
            & $ollamaGenerator @vfxParams
        }
        
        # Generate ability-specific VFX
        Write-Host "  Generating ability VFX..." -ForegroundColor Gray
        $abilityVFX = switch ($form.Id) {
            "eldritchAbomination" { @("gaze", "tentacles", "rift", "geometry") }
            "necroticReaper" { @("lifeDrain", "raiseUndead", "scythe", "aura") }
            "parasiticNightmare" { @("implant", "cloud", "swarm", "drain") }
            "fleshWeaver" { @("morph", "regenerate", "spawn", "tendril") }
            "phantomShroud" { @("terrorWave", "phase", "haunt", "possession") }
        }
        
        foreach ($ability in $abilityVFX) {
            $abilityParams = @{
                AssetType = "Particle"
                AssetName = "$($form.Id)_$ability"
                Prompt = "$($form.Name) $ability ability particle effect with $($form.Theme) theme, $($form.HorrorType) horror type, disturbing visuals"
                Parameters = @{
                    Category = "ability"
                    AbilityType = $ability
                    ColorScheme = $form.Theme
                    HorrorType = $form.HorrorType
                }
                UseCppBackend = $UseCppBackend
            }
            & $ollamaGenerator @abilityParams
        }
        
        # Generate SFX (horror-themed)
        Write-Host "  Generating horror sound effects..." -ForegroundColor Gray
        $sfxTypes = @("activate", "deactivate", "idle", "attack", "hurt")
        foreach ($sfxType in $sfxTypes) {
            $sfxParams = @{
                AssetType = "Sound"
                AssetName = "$($form.Id)_$($sfxType)"
                Prompt = "$($form.Name) $sfxType sound effect with $($form.Theme) theme, $($form.HorrorType) horror type, disturbing audio"
                Parameters = @{
                    Category = "mechForm"
                    HorrorType = $form.HorrorType
                    Theme = $form.Theme
                    Disturbing = $true
                }
                UseCppBackend = $UseCppBackend
            }
            & $ollamaGenerator @sfxParams
        }
        
        # Generate animation sprites
        Write-Host "  Generating animation sprites..." -ForegroundColor Gray
        $animations = @("idle", "move", "ability1", "ability2", "ability3", "ability4")
        foreach ($anim in $animations) {
            $animParams = @{
                AssetType = "Animation"
                AssetName = "$($form.Id)_$anim"
                Prompt = "$($form.Name) $anim animation with $($form.Theme) theme, $($form.HorrorType) horror type, disturbing visuals"
                Parameters = @{
                    FrameCount = 8
                    FrameSize = @(96, 96)
                    Category = "mechForm"
                    HorrorType = $form.HorrorType
                    AnimationType = $anim
                }
                UseCppBackend = $UseCppBackend
            }
            & $ollamaGenerator @animParams
        }
        
        Write-Host "  ✓ $($form.Name) assets generated" -ForegroundColor Green
        
    } catch {
        Write-Error "Failed to generate assets for $($form.Name): $_"
    }
}

Write-Host "`n=== Asset Generation Complete ===" -ForegroundColor Cyan
Write-Host "Generated assets for $($forms.Count) horror-themed mech forms" -ForegroundColor Green
Write-Host "Note: Horror assets may require manual review for appropriateness" -ForegroundColor Yellow

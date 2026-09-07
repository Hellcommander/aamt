# GenerateQuadrapedFormsAssets.ps1
# Generates assets for all quadraped mech forms

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
    @{Id="wolfPack"; Name="Wolf Pack Mech"; Theme="pack_hunter"; Animal="wolf"},
    @{Id="tankBeast"; Name="Tank Beast Mech"; Theme="defensive"; Animal="tank"},
    @{Id="scorpionStrike"; Name="Scorpion Strike Mech"; Theme="ambush"; Animal="scorpion"},
    @{Id="saberCat"; Name="Saber Cat Mech"; Theme="predator"; Animal="saber_cat"},
    @{Id="spiderWeaver"; Name="Spider Weaver Mech"; Theme="trapper"; Animal="spider"}
)

Write-Host "Generating assets for $($forms.Count) quadraped mech forms..." -ForegroundColor Cyan

foreach ($form in $forms) {
    Write-Host "`n=== $($form.Name) ($($form.Animal)) ===" -ForegroundColor Yellow
    
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
            Prompt = "$($form.Name) - Quadraped $($form.Animal) themed mech form with $($form.Theme) theme"
            Parameters = @{
                Size = 64
                Shape = "Circle"
                ColorScheme = $form.Theme
                Animal = $form.Animal
                Quadraped = $true
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
                Prompt = "$($form.Name) $($vfxType.ToLower()) particle effect with $($form.Theme) theme, $($form.Animal) animal, quadraped mech"
                Parameters = @{
                    Category = "mechForm"
                    Intensity = "medium"
                    ColorScheme = $form.Theme
                    Animal = $form.Animal
                    Quadraped = $true
                }
                UseCppBackend = $UseCppBackend
            }
            & $ollamaGenerator @vfxParams
        }
        
        # Generate SFX
        Write-Host "  Generating sound effects..." -ForegroundColor Gray
        $sfxTypes = @("activate", "deactivate", "idle")
        foreach ($sfxType in $sfxTypes) {
            $sfxParams = @{
                AssetType = "Sound"
                AssetName = "$($form.Id)_$($sfxType)"
                Prompt = "$($form.Name) $sfxType sound effect, $($form.Theme) theme, $($form.Animal) animal, quadraped mech"
                Parameters = @{
                    Category = "mechForm"
                    Animal = $form.Animal
                    Theme = $form.Theme
                    Quadraped = $true
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
Write-Host "Generated assets for $($forms.Count) quadraped mech forms" -ForegroundColor Green

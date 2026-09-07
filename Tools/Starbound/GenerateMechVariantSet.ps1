# GenerateMechVariantSet.ps1
# Generates a complete variant mech set with visual cohesion
# All forms in a variant set share color scheme, art style, and design language

param(
    [string]$VariantName = "voidCorrupted",
    [bool]$UseCppBackend = $true,
    [switch]$SkipExisting,
    [string[]]$FormsToGenerate = @()  # Empty = all 10 base forms
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

# Load variant system config
$variantConfig = Get-Content "$modPath\Data\Config\Mechs\MechVariantSystem.json" | ConvertFrom-Json

# Find variant template
$variantTemplate = $null
if ($variantConfig.variantTemplates.variantExamples) {
    $variantTemplate = $variantConfig.variantTemplates.variantExamples | Where-Object { $_.id -eq $VariantName } | Select-Object -First 1
}

if (-not $variantTemplate) {
    Write-Host "Variant '$VariantName' not found. Using base template." -ForegroundColor Yellow
    $variantTemplate = $variantConfig.variantTemplates.baseTemplate
    $variantTemplate.id = $VariantName
}

# Base forms to generate
$baseForms = @("biped", "hookSlinger", "centipede", "rhino", "jet", "bladeCyclone", "stealth", "magma", "gorilla", "walker")
if ($FormsToGenerate.Count -gt 0) {
    $baseForms = $baseForms | Where-Object { $FormsToGenerate -contains $_ }
}

Write-Host "=== Generating Variant Mech Set: $($variantTemplate.name) ===" -ForegroundColor Cyan
Write-Host "Variant ID: $VariantName" -ForegroundColor Yellow
Write-Host "Forms to generate: $($baseForms.Count)" -ForegroundColor Yellow
Write-Host "Color Scheme: Primary=$($variantTemplate.colorScheme.primary), Accent=$($variantTemplate.colorScheme.accent)" -ForegroundColor Gray
Write-Host "Art Style: $($variantTemplate.artStyle.shading) shading, $($variantTemplate.designLanguage.aesthetic) aesthetic" -ForegroundColor Gray
Write-Host "IMPORTANT: All forms must include visible cockpit with alpha channel for player visibility" -ForegroundColor Yellow

# Create variant directory structure
$variantDir = "$modPath\sprites\forms\variants\$VariantName"
$variantIconDir = "$modPath\interface\icons\forms\variants\$VariantName"
if (-not (Test-Path $variantDir)) {
    New-Item -ItemType Directory -Path $variantDir -Force | Out-Null
}
if (-not (Test-Path $variantIconDir)) {
    New-Item -ItemType Directory -Path $variantIconDir -Force | Out-Null
}

# Build AI prompt context for visual cohesion
$colorScheme = $variantTemplate.colorScheme
$artStyle = $variantTemplate.artStyle
$designLanguage = $variantTemplate.designLanguage

$cohesionPrompt = @"
VARIANT THEME: $($variantTemplate.name)
COLOR SCHEME: Primary RGB($($colorScheme.primary[0]),$($colorScheme.primary[1]),$($colorScheme.primary[2])), Accent RGB($($colorScheme.accent[0]),$($colorScheme.accent[1]),$($colorScheme.accent[2]))
ART STYLE: $($artStyle.shading) shading, $($artStyle.pixelArt) pixel art, $($artStyle.paletteLimit) color palette
DESIGN LANGUAGE: $($designLanguage.aesthetic), $($designLanguage.material), $($designLanguage.details)
"@

foreach ($formId in $baseForms) {
    Write-Host "`n[Form] Generating $formId variant..." -ForegroundColor Green
    
    # 1. Generate Form Icon (48x48)
    Write-Host "  [1/3] Generating form icon..." -ForegroundColor White
    $iconPath = "$variantIconDir\$formId.png"
    
    if (-not ($SkipExisting -and (Test-Path $iconPath))) {
        $params = @{
            AssetType = "Icon"
            AssetName = "variant_${VariantName}_${formId}"
            Size = 48
            Shape = "Circle"
            UseCppBackend = $UseCppBackend
            Parameters = @{
                VariantName = $VariantName
                FormID = $formId
                ColorScheme = $colorScheme
                ArtStyle = $artStyle
                DesignLanguage = $designLanguage
                CohesionPrompt = $cohesionPrompt
                ReferenceBase = $true
            }
        }
        
        & "$scriptPath\StarboundOllamaAssetGenerator.ps1" @params
    }
    
    # 2. Generate Animation Spritesheets (136 frames)
    Write-Host "  [2/3] Generating animation spritesheets..." -ForegroundColor White
    $animPath = "$variantDir\${formId}_animations.png"
    
    if (-not ($SkipExisting -and (Test-Path $animPath))) {
        # Load cockpit spec for this form
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
            AssetName = "variant_${VariantName}_${formId}_animations"
            UseCppBackend = $UseCppBackend
            Parameters = @{
                VariantName = $VariantName
                FormID = $formId
                FrameCount = 136
                FrameSize = @(96, 96)
                ColorScheme = $colorScheme
                ArtStyle = $artStyle
                DesignLanguage = $designLanguage
                CohesionPrompt = $cohesionPrompt
                ReferenceBase = $true
                MaintainStyle = $true
                IncludeCockpit = $true
                CockpitSpec = $cockpitSpec
                AlphaChannel = $true
                PlayerVisible = $true
            }
        }
        
        & "$scriptPath\StarboundOllamaAssetGenerator.ps1" @params
    }
    
    # 3. Generate VFX Particles (enter/exit)
    Write-Host "  [3/3] Generating VFX particles..." -ForegroundColor White
    $vfxEnterPath = "$modPath\particles\variants\$VariantName\${formId}Enter.particle"
    $vfxExitPath = "$modPath\particles\variants\$VariantName\${formId}Exit.particle"
    
    if (-not ($SkipExisting -and (Test-Path $vfxEnterPath))) {
        $params = @{
            AssetType = "Particle"
            AssetName = "variant_${VariantName}_${formId}_enter"
            UseCppBackend = $UseCppBackend
            Parameters = @{
                VariantName = $VariantName
                FormID = $formId
                Type = "enter"
                ColorScheme = $colorScheme
                ArtStyle = $artStyle
            }
        }
        
        & "$scriptPath\StarboundOllamaAssetGenerator.ps1" @params
    }
    
    if (-not ($SkipExisting -and (Test-Path $vfxExitPath))) {
        $params = @{
            AssetType = "Particle"
            AssetName = "variant_${VariantName}_${formId}_exit"
            UseCppBackend = $UseCppBackend
            Parameters = @{
                VariantName = $VariantName
                FormID = $formId
                Type = "exit"
                ColorScheme = $colorScheme
                ArtStyle = $artStyle
            }
        }
        
        & "$scriptPath\StarboundOllamaAssetGenerator.ps1" @params
    }
}

Write-Host "`n=== Variant Set Generation Complete ===" -ForegroundColor Cyan
Write-Host "Generated variant '$($variantTemplate.name)' with $($baseForms.Count) forms" -ForegroundColor Green
Write-Host "All forms share consistent color scheme, art style, and design language" -ForegroundColor Gray

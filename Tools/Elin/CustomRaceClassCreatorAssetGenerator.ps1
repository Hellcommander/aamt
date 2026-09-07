<#
.SYNOPSIS
    Comprehensive Asset Generator for CustomRaceClassCreator Mod
    AI-Assisted Modding Tools (AAMT) - Elin Toolset

.DESCRIPTION
    Generates missing assets for the CustomRaceClassCreator mod using AI and tools.
    Supports icons, sprites, textures, materials, and prefabs for all 38+ asset sets.
    
    Features:
    - AI-powered asset specification generation
    - Tool-based asset creation (Blender, PIL, etc.)
    - Progress tracking with detailed meters
    - Asset type-specific AI models
    - Missing asset detection
    - Asset improvement mode

# Load shared asset generation settings
$settingsPath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "..\\AssetGenerationSettings.ps1"
if (Test-Path $settingsPath) {
    . $settingsPath
}

.PARAMETER ModPath
    Path to CustomRaceClassCreator mod directory

.PARAMETER AssetTypes
    Comma-separated list of asset types to generate (icons, sprites, textures, materials, prefabs)
    Default: all

.PARAMETER Systems
    Comma-separated list of magic systems to process (or "all" for all systems)
    Default: all

.PARAMETER ScanOnly
    Only scan for missing assets, don't generate

.PARAMETER ImproveExisting
    Improve existing placeholder/default assets

.PARAMETER UseAI
    Use Ollama AI for asset specifications

.PARAMETER OllamaModel
    Ollama model to use (default: auto-select based on asset type)

.EXAMPLE
    .\CustomRaceClassCreatorAssetGenerator.ps1 -ModPath "E:\SteamLibrary\steamapps\common\Elin\Package\Mod\CustomRaceClassCreator" -ScanOnly

.EXAMPLE
    .\CustomRaceClassCreatorAssetGenerator.ps1 -ModPath "E:\SteamLibrary\steamapps\common\Elin\Package\Mod\CustomRaceClassCreator" -AssetTypes "icons,sprites" -Systems "DragonMagic,BloodMagic"

.EXAMPLE
    .\CustomRaceClassCreatorAssetGenerator.ps1 -ModPath "E:\SteamLibrary\steamapps\common\Elin\Package\Mod\CustomRaceClassCreator" -AssetTypes "textures" -UseAI -UseBundlesAsReference
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)]
    [string]$ModPath,
    
    [string]$AssetTypes = "all",
    
    [string]$Systems = "all",
    
    [switch]$ScanOnly,
    
    [switch]$ImproveExisting,
    
    [switch]$UseAI,
    
    [string]$OllamaModel = "",
    
    [switch]$ForceRegenerate,
    
    [switch]$SkipIfBundleExists,
    
    [switch]$UseBundlesAsReference,
    
    [string]$UnityPath = ""
)

$ErrorActionPreference = "Stop"

# Import unified tool detection and integration
$sharedPath = Join-Path (Split-Path $PSScriptRoot -Parent) "Shared"
Import-Module (Join-Path $sharedPath "ToolDetection.psm1") -ErrorAction SilentlyContinue
Import-Module (Join-Path $sharedPath "ToolsetIntegration.psm1") -ErrorAction SilentlyContinue
Import-Module (Join-Path $sharedPath "OllamaIntegration.psm1") -ErrorAction SilentlyContinue
Import-Module (Join-Path $sharedPath "UnityVersionResolver.psm1") -ErrorAction SilentlyContinue
Import-Module (Join-Path $sharedPath "UnityAssetExport.psm1") -ErrorAction SilentlyContinue
Import-Module (Join-Path $PSScriptRoot "ElinAssetRender.psm1") -Force -ErrorAction SilentlyContinue

# Initialize tools for CustomRaceClassCreator asset generation
$tools = Initialize-ToolsetTools `
    -RequiredTools @() `
    -OptionalTools @("Ollama", "Python", "Blender", "ImageMagick")

# Show tool status
Show-ToolsetStatus -ToolsetName "Elin (CustomRaceClassCreator)" `
    -RequiredTools @() `
    -OptionalTools @("Ollama", "Python", "Blender", "ImageMagick")
Write-Host ""

# Use Ollama if available and requested
if ($UseAI) {
    $ollamaAvailable = Use-OllamaIfAvailable
    if (-not $ollamaAvailable) {
        Write-Host "⚠ Warning: Ollama not available, but -UseAI was specified" -ForegroundColor Yellow
        Write-Host "  Continuing without AI features..." -ForegroundColor Gray
        $UseAI = $false
    } else {
        Write-Host "✓ Ollama integration enabled" -ForegroundColor Green
    }
}

# Store ModPath globally for Unity integration
$script:ModPath = $ModPath

# ============================================================
# CONFIGURATION
# ============================================================

# Ollama URL (from shared module, but can be overridden)
if (-not $script:OllamaUrl) {
    $script:OllamaUrl = "http://localhost:11434"
    $script:OllamaApiUrl = "$script:OllamaUrl/api"
}

# Asset type to task type mapping (uses Shared OllamaIntegration tier system)
# The shared module automatically routes dark tone content to "dark_tone" tier
# wizardlm-uncensored is reserved for dark_tone/escalation tiers via shared module
$script:AssetTaskTypes = @{
    "icons" = "visual"                          # Uses visual tier (auto-routes to dark_tone if needed)
    "sprites" = "visual"                        # Uses visual tier (auto-routes to dark_tone if needed)
    "textures" = "visual"                       # Uses visual tier (auto-routes to dark_tone if needed)
    "materials" = "code"                        # Technical specs use code tier
    "prefabs" = "code"                          # Technical specs use code tier
    "feat_icons" = "visual"                    # Uses visual tier (auto-routes to dark_tone if needed)
    "spell_icons" = "visual"                   # Uses visual tier (auto-routes to dark_tone if needed)
    "spell_assets" = "visual"                  # Uses visual tier (auto-routes to dark_tone if needed)
}

# All 38+ asset systems
$script:AllSystems = @(
    "DragonMagic", "DreamMagic", "ElementMagic", "WispMagic", "DruidicMagic",
    "Crossmagic", "RiverMagic", "Pollution", "ArcaneSaturation", "BardicMagic",
    "SpiritMagic", "Geomancy", "Necromancy", "BloodMagic", "Golemancy",
    "SpectreMagic", "Technomancy", "TerrainMagic", "WeatherMagic", "RuneMagic",
    "EtherwindMagic", "Geoscience", "DynamicSpells", "SlotMagic",
    "PactMagic", "RitualMagic", "SlotMachine", "AIAssistant", "PCCMutation",
    "QuestPlus", "SpriteAlter", "CombatPlus", "EditorWindows", "UI", "UIButtons",
    "SpellEffects", "ComputeShaders"
)

# Asset type configurations
$script:AssetConfigs = @{
    "icons" = @{
        Size = 32
        Format = "PNG"
        Folder = "Icons"
        Extensions = @(".png", ".jpg")
        PlaceholderPatterns = @("placeholder", "default", "temp", "missing")
    }
    "sprites" = @{
        Size = @(32, 48, 64)
        Format = "PNG"
        Folder = "Sprites"
        Extensions = @(".png", ".jpg")
        PlaceholderPatterns = @("placeholder", "default", "temp", "missing")
    }
    "textures" = @{
        Size = @(256, 512, 1024)
        Format = "PNG"
        Folder = "Textures"
        Extensions = @(".png", ".jpg", ".tga")
        PlaceholderPatterns = @("placeholder", "default", "temp", "missing", "white", "black", "gray")
        Priority = 1  # High priority - textures are critical
    }
    "materials" = @{
        Format = "MAT"
        Folder = "Materials"
        Extensions = @(".mat", ".asset")
        PlaceholderPatterns = @("placeholder", "default", "temp", "missing")
    }
    "prefabs" = @{
        Format = "PREFAB"
        Folder = "Prefabs"
        Extensions = @(".prefab", ".asset")
        PlaceholderPatterns = @("placeholder", "default", "temp", "missing")
    }
    "feat_icons" = @{
        Size = 32
        Format = "PNG"
        Folder = "FeatIcons"
        Extensions = @(".png", ".jpg")
        PlaceholderPatterns = @("placeholder", "default", "temp", "missing")
    }
    "spell_icons" = @{
        Size = 32
        Format = "PNG"
        Folder = "SpellIcons"
        Extensions = @(".png", ".jpg")
        PlaceholderPatterns = @("placeholder", "default", "temp", "missing")
    }
    "spell_assets" = @{
        Size = 32
        Format = "PNG"
        Folder = "SpellAssets"
        Extensions = @(".png", ".jpg", ".prefab", ".mat")
        PlaceholderPatterns = @("placeholder", "default", "temp", "missing")
        Description = "Complete spell asset set (icon, FX, projectile, mesh, material)"
    }
}

# Progress tracking
$script:Progress = @{
    TotalAssets = 0
    ProcessedAssets = 0
    GeneratedAssets = 0
    ImprovedAssets = 0
    SkippedAssets = 0
    FailedAssets = 0
    ReferenceBasedAssets = 0
    CurrentSystem = ""
    CurrentAsset = ""
    StartTime = Get-Date
}

# ============================================================
# ASSETBUNDLE SCANNING
# ============================================================

function Scan-AssetBundles {
    param(
        [string]$ModPath,
        [string]$SystemName,
        [string]$AssetType
    )
    
    $foundAssets = @()
    
    # Check AssetBundle locations
    $bundlePaths = @(
        Join-Path $ModPath "Assets\AssetBundles\Windows"
        Join-Path $ModPath "Assets\UI\AssetBundles\Windows"
        Join-Path $ModPath "Assets\AssetBundles\Linux"
        Join-Path $ModPath "Assets\AssetBundles\macOS"
    )
    
    foreach ($bundlePath in $bundlePaths) {
        if (-not (Test-Path $bundlePath)) { continue }
        
        # Look for relevant bundles
        $bundleFiles = Get-ChildItem -Path $bundlePath -File -Filter "*.assetbundle" -ErrorAction SilentlyContinue
        
        foreach ($bundle in $bundleFiles) {
            # Check if bundle might contain assets for this system
            $bundleName = $bundle.BaseName.ToLower()
            $systemLower = $SystemName.ToLower()
            
            if ($bundleName -like "*$systemLower*" -or 
                $bundleName -like "*$AssetType*" -or
                $bundleName -like "*texture*" -or
                $bundleName -like "*ui*" -or
                $bundleName -like "*icon*") {
                
                # Try to get bundle info
                $bundleInfo = Get-AssetBundleInfo -BundlePath $bundle.FullName
                if ($bundleInfo) {
                    $foundAssets += $bundleInfo
                }
            }
        }
    }
    
    return $foundAssets
}

function Get-AssetBundleInfo {
    param([string]$BundlePath)
    
    try {
        # Check bundle file size (larger = more content)
        $bundleFile = Get-Item $BundlePath -ErrorAction SilentlyContinue
        if (-not $bundleFile) { return $null }
        
        $fileSize = $bundleFile.Length
        
        # Quality assessment based on file size
        # Small bundles (< 10KB) likely don't have textures
        # Medium bundles (10KB - 1MB) might have some assets
        # Large bundles (> 1MB) likely have quality assets
        $quality = if ($fileSize -gt 1MB) {
            "high"
        } elseif ($fileSize -gt 100KB) {
            "medium"
        } elseif ($fileSize -gt 10KB) {
            "low"
        } else {
            "minimal"
        }
        
        # Try to extract asset list using Python/Unity tools
        $assetList = Extract-AssetBundleContents -BundlePath $BundlePath
        
        return @{
            Path = $BundlePath
            Size = $fileSize
            Quality = $quality
            Assets = $assetList
            LastModified = $bundleFile.LastWriteTime
        }
    }
    catch {
        return $null
    }
}

function Extract-AssetBundleContents {
    param([string]$BundlePath)
    
    # Try using Python with Unity AssetBundle extractor if available
    # Or use AssetStudio command-line if installed
    # For now, return basic info
    
    try {
        # Check if AssetStudio is available
        $assetStudio = Get-Command "AssetStudioCLI" -ErrorAction SilentlyContinue
        if ($assetStudio) {
            $tempOutput = Join-Path $env:TEMP "bundle_scan_$(Get-Random)"
            $result = & $assetStudio.Source -i $BundlePath -o $tempOutput -t texture 2>&1
            if ($LASTEXITCODE -eq 0 -and (Test-Path $tempOutput)) {
                $extracted = Get-CachedChildItem -Path $tempOutput -Recurse -File | Where-Object {
                    $_.Extension -match '\.(png|jpg|tga|dds)$'
                }
                Remove-Item $tempOutput -Recurse -Force -ErrorAction SilentlyContinue
                return $extracted | ForEach-Object { @{ Name = $_.Name; Path = $_.FullName; Size = $_.Length } }
            }
        }
    }
    catch {
        # AssetStudio not available, continue
    }
    
    # Fallback: Use Python script to read bundle manifest if possible
    $pythonScript = @"
import sys
import os

bundle_path = r"$BundlePath"

# Try to read bundle header/manifest
# Unity AssetBundles have a header we can partially parse
try:
    with open(bundle_path, 'rb') as f:
        # Read first bytes to check format
        header = f.read(16)
        # Unity AssetBundle signature check
        if header[:7] == b'UnityFS' or header[:4] == b'Unity':
            # Bundle appears valid
            file_size = os.path.getsize(bundle_path)
            print(f"VALID:{file_size}")
        else:
            print("INVALID")
except Exception as e:
    print(f"ERROR:{str(e)}")
"@
    
    try {
        $tempPy = Join-Path $env:TEMP "bundle_check_$(Get-Random).py"
        [System.IO.File]::WriteAllText($tempPy, $pythonScript, (New-Object System.Text.UTF8Encoding $false))
        
        $pythonCmd = Get-Command "python" -ErrorAction SilentlyContinue
        if (-not $pythonCmd) { $pythonCmd = Get-Command "python3" -ErrorAction SilentlyContinue }
        
        if ($pythonCmd) {
            $result = & $pythonCmd.Source $tempPy 2>&1
            Remove-Item $tempPy -Force
            if ($result -match "VALID:") {
                return @(@{ Name = "Unknown"; Path = $BundlePath; Size = [long]($result -replace '.*VALID:', '') })
            }
        }
    }
    catch {
        # Python check failed
    }
    
    return @()
}

function Find-UsableAssetsFromBundles {
    param(
        [string]$ModPath,
        [string]$SystemName,
        [string]$AssetType,
        [string]$TargetPath
    )
    
    # First, check for already-extracted assets in Resources folders
    $resourcesPath = Join-Path $ModPath "Assets\Resources\$SystemName"
    if (Test-Path $resourcesPath) {
        $extractedAssets = Get-CachedChildItem -Path $resourcesPath -Recurse -File | Where-Object {
            $ext = $_.Extension.ToLower()
            $name = $_.Name.ToLower()
            $size = $_.Length
            
            # Check if it's a quality asset (not placeholder)
            $isPlaceholder = $script:AssetConfigs[$AssetType].PlaceholderPatterns | Where-Object { $name -like "*$_*" }
            $hasValidExtension = $script:AssetConfigs[$AssetType].Extensions -contains $ext
            $isRelevant = $false
            
            if ($AssetType -eq "textures") {
                $isRelevant = $hasValidExtension -and $size -gt 10KB -and -not $isPlaceholder
            }
            elseif ($AssetType -eq "icons") {
                $isRelevant = $hasValidExtension -and $size -gt 1KB -and -not $isPlaceholder
            }
            elseif ($AssetType -eq "sprites") {
                $isRelevant = $hasValidExtension -and $size -gt 2KB -and -not $isPlaceholder
            }
            
            return $isRelevant
        }
        
        if ($extractedAssets.Count -gt 0) {
            Write-Host "  [Found] $($extractedAssets.Count) existing quality asset(s) in Resources folder" -ForegroundColor Cyan
            return $extractedAssets | ForEach-Object {
                @{
                    Source = $_.FullName
                    Name = $_.Name
                    Size = $_.Length
                    Quality = if ($_.Length -gt 100KB) { "high" } elseif ($_.Length -gt 10KB) { "medium" } else { "low" }
                    BundlePath = "Resources"
                    IsExtracted = $true
                }
            }
        }
    }
    
    # Scan bundles for usable assets
    $bundleAssets = Scan-AssetBundles -ModPath $ModPath -SystemName $SystemName -AssetType $AssetType
    
    $usableAssets = @()
    
    foreach ($bundleInfo in $bundleAssets) {
        if ($bundleInfo.Quality -in @("high", "medium")) {
            # Check if assets match what we need
            foreach ($asset in $bundleInfo.Assets) {
                $assetName = $asset.Name.ToLower()
                
                # Check if asset matches our needs
                $isRelevant = $false
                if ($AssetType -eq "textures") {
                    $isRelevant = $assetName -match '\.(png|jpg|tga|dds)$' -and 
                                 ($assetName -like "*texture*" -or $assetName -like "*$($SystemName.ToLower())*" -or $asset.Size -gt 50KB)
                }
                elseif ($AssetType -eq "icons") {
                    $isRelevant = $assetName -match '\.(png|jpg)$' -and 
                                 ($assetName -like "*icon*" -or ($asset.Size -gt 1KB -and $asset.Size -lt 100KB))
                }
                elseif ($AssetType -eq "sprites") {
                    $isRelevant = $assetName -match '\.(png|jpg)$' -and 
                                 ($assetName -like "*sprite*" -or ($asset.Size -gt 2KB -and $asset.Size -lt 500KB))
                }
                
                if ($isRelevant -and $asset.Size -gt 1KB) {
                    # Check quality threshold
                    $minSize = switch ($AssetType) {
                        "textures" { 10KB }  # Textures should be substantial
                        "icons" { 1KB }      # Icons can be small
                        "sprites" { 2KB }   # Sprites medium
                        default { 1KB }
                    }
                    
                    if ($asset.Size -ge $minSize) {
                        $usableAssets += @{
                            Source = $asset.Path
                            Name = $asset.Name
                            Size = $asset.Size
                            Quality = $bundleInfo.Quality
                            BundlePath = $bundleInfo.Path
                            IsExtracted = $false
                        }
                    }
                }
            }
        }
    }
    
    return $usableAssets
}

function Analyze-AssetReference {
    param(
        [string]$AssetPath,
        [string]$AssetType
    )
    
    if (-not (Test-Path $AssetPath)) {
        return $null
    }
    
    try {
        # Use Python/PIL to analyze the image
        $pythonScript = @"
from PIL import Image
import json
import colorsys

asset_path = r"$AssetPath"
asset_type = "$AssetType"

try:
    img = Image.open(asset_path)
    width, height = img.size
    
    # Convert to RGB if needed
    if img.mode != 'RGB':
        img = img.convert('RGB')
    
    # Get pixel data
    pixels = list(img.getdata())
    
    # Analyze colors
    color_counts = {}
    total_pixels = len(pixels)
    
    # Sample colors (every Nth pixel for performance)
    sample_rate = max(1, total_pixels // 10000)
    sampled_pixels = pixels[::sample_rate]
    
    # Dominant colors
    color_buckets = {}
    for r, g, b in sampled_pixels:
        # Quantize to reduce color space
        bucket = (r // 32 * 32, g // 32 * 32, b // 32 * 32)
        color_buckets[bucket] = color_buckets.get(bucket, 0) + 1
    
    # Get top colors
    top_colors = sorted(color_buckets.items(), key=lambda x: x[1], reverse=True)[:5]
    dominant_colors = [f"#{r:02x}{g:02x}{b:02x}" for (r, g, b), count in top_colors]
    
    # Calculate average brightness
    avg_brightness = sum(sum(pixel) / 3 for pixel in sampled_pixels) / len(sampled_pixels)
    brightness = "bright" if avg_brightness > 180 else "medium" if avg_brightness > 100 else "dark"
    
    # Analyze patterns (simple edge detection)
    # Check for gradients, solid colors, or complex patterns
    color_variance = sum(
        abs(sum(p1) - sum(p2)) 
        for p1, p2 in zip(sampled_pixels[:-1], sampled_pixels[1:])
    ) / len(sampled_pixels)
    
    pattern_type = "gradient" if color_variance < 50 else "complex" if color_variance > 200 else "textured"
    
    # Analyze contrast
    min_brightness = min(sum(p) / 3 for p in sampled_pixels)
    max_brightness = max(sum(p) / 3 for p in sampled_pixels)
    contrast = max_brightness - min_brightness
    contrast_level = "high" if contrast > 150 else "medium" if contrast > 80 else "low"
    
    # Style assessment
    style = {
        "colors": dominant_colors,
        "brightness": brightness,
        "pattern": pattern_type,
        "contrast": contrast_level,
        "size": {"width": width, "height": height},
        "quality": "high" if width >= 256 and height >= 256 else "medium" if width >= 128 else "low"
    }
    
    print(json.dumps(style))
    
except Exception as e:
    print(f"ERROR:{str(e)}")
"@
        
        $tempPy = Join-Path $env:TEMP "analyze_asset_$(Get-Random).py"
        [System.IO.File]::WriteAllText($tempPy, $pythonScript, (New-Object System.Text.UTF8Encoding $false))
        
        $pythonCmd = Get-Command "python" -ErrorAction SilentlyContinue
        if (-not $pythonCmd) { $pythonCmd = Get-Command "python3" -ErrorAction SilentlyContinue }
        
        if ($pythonCmd) {
            $result = & $pythonCmd.Source $tempPy 2>&1
            Remove-Item $tempPy -Force
            
            if ($result -notmatch "ERROR:") {
                try {
                    $style = $result | ConvertFrom-Json
                    return $style
                }
                catch {
                    # JSON parse failed
                }
            }
        }
    }
    catch {
        # Analysis failed
    }
    
    return $null
}

function Get-ReferenceBasedSpec {
    param(
        [object]$ReferenceStyle,
        [string]$SystemName,
        [string]$AssetType,
        [string]$TaskType = "visual",
        [string]$ModelName = ""
    )
    
    if (-not $ReferenceStyle) {
        return $null
    }
    
    # Create enhanced prompt using reference style
    $referenceInfo = @"
Reference Asset Analysis:
- Dominant Colors: $($ReferenceStyle.colors -join ', ')
- Brightness: $($ReferenceStyle.brightness)
- Pattern Type: $($ReferenceStyle.pattern)
- Contrast: $($ReferenceStyle.contrast)
- Quality: $($ReferenceStyle.quality)
- Size: $($ReferenceStyle.size.width)×$($ReferenceStyle.size.height)
"@
    
    $prompt = @"
Create an improved $AssetType specification for $SystemName based on this reference asset analysis.

$referenceInfo

Requirements:
1. Use similar color palette but enhance it (make it more vibrant/magical)
2. Match or improve the pattern style ($($ReferenceStyle.pattern))
3. Maintain or increase contrast level ($($ReferenceStyle.contrast))
4. Create a HIGHER QUALITY version than the reference
5. Add magical/theme-appropriate enhancements
6. Ensure the asset fits the $SystemName theme

Generate a JSON specification with:
- colors: Array of 3-5 hex colors (enhanced from reference)
- pattern: Pattern type (enhanced from reference)
- brightness: Brightness level
- contrast: Contrast level
- size: Recommended size (at least as large as reference)
- enhancements: Array of improvements over reference

Return ONLY valid JSON, no other text.
"@
    
    # Use Shared OllamaIntegration - automatically handles dark tone detection and tier routing
    $specJson = Invoke-OllamaChat -Prompt $prompt -TaskType $TaskType -SystemPrompt "You are a game asset designer. Generate JSON specifications only." -ModelName $ModelName
    
    if ($specJson) {
        try {
            # Try to extract JSON from response
            if ($specJson -match '\{.*\}') {
                $jsonMatch = $Matches[0]
                $spec = $jsonMatch | ConvertFrom-Json
                return $spec
            }
        }
        catch {
            # JSON parse failed, return null to use default
        }
    }
    
    return $null
}

function Extract-ReferenceAsset {
    param(
        [object]$AssetInfo,
        [string]$TempDir
    )
    
    try {
        # If already extracted, use it directly
        if ($AssetInfo.IsExtracted -and (Test-Path $AssetInfo.Source)) {
            $refPath = Join-Path $TempDir "reference_$(Split-Path $AssetInfo.Source -Leaf)"
            Copy-Item -Path $AssetInfo.Source -Destination $refPath -Force
            return $refPath
        }
        
        # Try to extract from bundle
        $assetStudio = Get-Command "AssetStudioCLI" -ErrorAction SilentlyContinue
        if ($assetStudio) {
            $extractOutput = Join-Path $TempDir "extracted"
            New-Item -ItemType Directory -Path $extractOutput -Force | Out-Null
            
            try {
                $result = & $assetStudio.Source -i $AssetInfo.BundlePath -o $extractOutput -t texture 2>&1
                if ($LASTEXITCODE -eq 0 -and (Test-Path $extractOutput)) {
                    $extracted = Get-ChildItem -Path $extractOutput -Recurse -File | Where-Object {
                        $_.Extension -match '\.(png|jpg|tga|dds)$'
                    } | Select-Object -First 1
                    
                    if ($extracted) {
                        $refPath = Join-Path $TempDir "reference_$($extracted.Name)"
                        Copy-Item -Path $extracted.FullName -Destination $refPath -Force
                        Remove-Item $extractOutput -Recurse -Force
                        return $refPath
                    }
                }
            }
            catch {
                # Extraction failed
            }
            finally {
                if (Test-Path $extractOutput) {
                    Remove-Item $extractOutput -Recurse -Force -ErrorAction SilentlyContinue
                }
            }
        }
    }
    catch {
        # Extraction failed
    }
    
    return $null
}

function Copy-AssetFromBundle {
    param(
        [object]$AssetInfo,
        [string]$TargetPath
    )
    
    try {
        # If asset is already extracted (in Resources), copy it
        if ($AssetInfo.IsExtracted -and (Test-Path $AssetInfo.Source)) {
            $targetDir = Split-Path $TargetPath -Parent
            if (-not (Test-Path $targetDir)) {
                New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
            }
            
            # Only copy if target doesn't exist or is smaller (upgrade)
            if (-not (Test-Path $TargetPath) -or ((Get-Item $TargetPath).Length -lt $AssetInfo.Size)) {
                Copy-Item -Path $AssetInfo.Source -Destination $TargetPath -Force
                return $true
            }
            else {
                Write-Host "  [Info] Target asset already exists and is same/larger size" -ForegroundColor Gray
                return $true
            }
        }
        elseif (-not $AssetInfo.IsExtracted) {
            # Need to extract from bundle
            # Check if AssetStudio is available for extraction
            $assetStudio = Get-Command "AssetStudioCLI" -ErrorAction SilentlyContinue
            if ($assetStudio) {
                $tempOutput = Join-Path $env:TEMP "bundle_extract_$(Get-Random)"
                New-Item -ItemType Directory -Path $tempOutput -Force | Out-Null
                
                try {
                    # Extract textures from bundle
                    $result = & $assetStudio.Source -i $AssetInfo.BundlePath -o $tempOutput -t texture 2>&1
                    if ($LASTEXITCODE -eq 0 -and (Test-Path $tempOutput)) {
                        $extracted = Get-ChildItem -Path $tempOutput -Recurse -File -Filter "*$($AssetInfo.Name)*" | Select-Object -First 1
                        if ($extracted) {
                            $targetDir = Split-Path $TargetPath -Parent
                            if (-not (Test-Path $targetDir)) {
                                New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
                            }
                            Copy-Item -Path $extracted.FullName -Destination $TargetPath -Force
                            Remove-Item $tempOutput -Recurse -Force
                            return $true
                        }
                    }
                }
                catch {
                    # Extraction failed
                }
                finally {
                    if (Test-Path $tempOutput) {
                        Remove-Item $tempOutput -Recurse -Force -ErrorAction SilentlyContinue
                    }
                }
            }
            
            Write-Host "  [Info] Asset in bundle needs extraction. Install AssetStudio for automatic extraction." -ForegroundColor Yellow
            Write-Host "  [Info] Bundle: $($AssetInfo.BundlePath)" -ForegroundColor Gray
            return $false
        }
    }
    catch {
        Write-Host "  [Warning] Could not copy asset: $_" -ForegroundColor Yellow
        return $false
    }
}

# ============================================================
# UNITY INTEGRATION
# ============================================================

function Find-UnityEditor {
    param(
        [string]$ModPath,
        [string]$ManualPath = ""
    )
    
    # Strict: resolve from the live Elin game binary. Never grab a random Hub Editor.
    $elinGame = if ($env:ELIN_GAME_ROOT) { $env:ELIN_GAME_ROOT } else { "E:\SteamLibrary\steamapps\common\Elin" }
    if (-not (Get-Command Resolve-UnityEditorForGame -ErrorAction SilentlyContinue)) {
        $shared = Join-Path (Split-Path $PSScriptRoot -Parent) "Shared\UnityVersionResolver.psm1"
        if (Test-Path $shared) {
            Import-Module $shared -Force
        }
    }
    if ((Get-Command Resolve-UnityEditorForGame -ErrorAction SilentlyContinue) -and (Test-Path $elinGame)) {
        $m = Resolve-UnityEditorForGame -GameRoot $elinGame -ManualPath $ManualPath
        if ($m.EditorExe) { return $m.EditorExe }
        Write-Host "  [Unity] $($m.InstallHint)" -ForegroundColor Cyan
        return $null
    }

    if ($ManualPath -and (Test-Path $ManualPath) -and (Get-Command Get-GameUnityVersion -ErrorAction SilentlyContinue)) {
        $req = Get-GameUnityVersion -GameRoot $elinGame
        if ($req -and (Get-Command Find-MatchingUnityEditor -ErrorAction SilentlyContinue)) {
            return Find-MatchingUnityEditor -RequiredVersion $req -ManualPath $ManualPath
        }
    }

    Write-Host "  [Unity] Matching Editor not found. Install Elin's Unity into E:\tools\Unity_Editor\{version}\" -ForegroundColor Yellow
    return $null
}

function Invoke-UnityEditorScript {
    param(
        [string]$UnityPath,
        [string]$ModPath,
        [string]$ScriptPath,
        [string]$MethodName,
        [hashtable]$Parameters = @{},
        [int]$TimeoutSeconds = 300
    )
    
    if (-not $UnityPath -or -not (Test-Path $UnityPath)) {
        Write-Host "  [Warning] Unity editor not found" -ForegroundColor Yellow
        return $false
    }
    
    # Create Unity editor script if it doesn't exist
    $editorScriptsDir = Join-Path $ModPath "Assets\Editor"
    if (-not (Test-Path $editorScriptsDir)) {
        New-Item -ItemType Directory -Path $editorScriptsDir -Force | Out-Null
    }
    
    # Create simple Unity editor script using only Unity 2021.3.45f1 built-in APIs
    $scriptContent = @"
using UnityEngine;
using UnityEditor;
using System.IO;

public class AssetGeneratorEditor
{
    public static void GenerateAsset()
    {
        string methodName = "$MethodName";
        string modPath = @"$ModPath";
        
        // Parameters
        $($Parameters.GetEnumerator() | ForEach-Object { "string $($_.Key) = `"$($_.Value)`";" })
        
        try
        {
            switch (methodName)
            {
                case "GenerateMaterial":
                    GenerateMaterial(modPath, $($Parameters.Keys -join ', '));
                    break;
                case "GeneratePrefab":
                    GeneratePrefab(modPath, $($Parameters.Keys -join ', '));
                    break;
                case "GenerateShader":
                    GenerateShader(modPath, $($Parameters.Keys -join ', '));
                    break;
                case "RefreshAssetDatabase":
                    RefreshAssetDatabase();
                    break;
                default:
                    Debug.LogError($\"Unknown method: {methodName}\");
                    EditorApplication.Exit(1);
                    return;
            }
            
            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh();
            Debug.Log(\"Asset generation completed successfully\");
            EditorApplication.Exit(0);
        }
        catch (System.Exception e)
        {
            Debug.LogError($\"Asset generation failed: {e.Message}\");
            Debug.LogError($\"Stack trace: {e.StackTrace}\");
            EditorApplication.Exit(1);
        }
    }
    
    static void GenerateMaterial(string modPath, string systemName, string texturePath, string shaderName)
    {
        string materialPath = $\"Assets/Resources/{systemName}/Materials/{systemName}_Material.mat\";
        string fullPath = Path.Combine(modPath, materialPath);
        string dir = Path.GetDirectoryName(fullPath);
        
        if (!Directory.Exists(dir))
            Directory.CreateDirectory(dir);
        
        Material mat = new Material(Shader.Find(shaderName ?? \"Standard\"));
        
        if (!string.IsNullOrEmpty(texturePath) && File.Exists(texturePath))
        {
            // Convert absolute path to relative asset path
            string relativeTexturePath = texturePath.Replace(modPath + Path.DirectorySeparatorChar, \"\").Replace(Path.DirectorySeparatorChar, '/');
            if (!relativeTexturePath.StartsWith(\"Assets/\"))
            {
                // Try to find texture in Assets folder
                string textureName = Path.GetFileName(texturePath);
                string[] guids = AssetDatabase.FindAssets(textureName);
                if (guids.Length > 0)
                {
                    relativeTexturePath = AssetDatabase.GUIDToAssetPath(guids[0]);
                }
            }
            
            Texture2D tex = AssetDatabase.LoadAssetAtPath<Texture2D>(relativeTexturePath);
            if (tex != null)
            {
                mat.mainTexture = tex;
                if (mat.HasProperty(\"_MainTex\")) mat.SetTexture(\"_MainTex\", tex);
                Debug.Log($\"Material assigned texture: {relativeTexturePath}\");
            }
            else
            {
                Debug.LogWarning($\"Texture not found at: {relativeTexturePath}\");
            }
        }

        // Optional PBR siblings: Textures/Skins/{stem}_*.png (stem matches GeneratePbrSkin sanitization)
        {
            string skinDir = Path.Combine(modPath, $\"Assets/Resources/{systemName}/Textures/Skins\");
            string stem = System.Text.RegularExpressions.Regex.Replace(systemName, \"[^A-Za-z0-9_]\", \"_\");
            if (mat.mainTexture == null)
                TryAssignMap(mat, skinDir, stem + \"_diffuse.png\", \"_MainTex\", false);
            TryAssignMap(mat, skinDir, stem + \"_normal.png\", \"_BumpMap\", true);
            // Prefer packed metallicgloss (R=metal, A=smoothness); fall back to metallic-only
            if (!TryAssignMap(mat, skinDir, stem + \"_metallicgloss.png\", \"_MetallicGlossMap\", false))
                TryAssignMap(mat, skinDir, stem + \"_metallic.png\", \"_MetallicGlossMap\", false);
            TryAssignMap(mat, skinDir, stem + \"_emission.png\", \"_EmissionMap\", false);
            if (File.Exists(Path.Combine(skinDir, stem + \"_emission.png\")))
            {
                mat.EnableKeyword(\"_EMISSION\");
                mat.globalIlluminationFlags = MaterialGlobalIlluminationFlags.RealtimeEmissive;
            }
            if (mat.HasProperty(\"_MetallicGlossMap\") && mat.GetTexture(\"_MetallicGlossMap\") != null)
                mat.EnableKeyword(\"_METALLICGLOSSMAP\");
        }
        
        AssetDatabase.CreateAsset(mat, materialPath);
        Debug.Log($\"Material created: {materialPath}\");
    }

    static bool TryAssignMap(Material mat, string skinDir, string fileName, string property, bool asNormal)
    {
        string full = Path.Combine(skinDir, fileName);
        if (!File.Exists(full)) return false;
        string rel = full.Replace(\"\\\\\", \"/\").Replace(Application.dataPath.Replace(\"Assets\", \"\"), \"\");
        // Prefer AssetDatabase lookup by file name
        string[] guids = AssetDatabase.FindAssets(Path.GetFileNameWithoutExtension(fileName));
        Texture2D map = null;
        foreach (string g in guids)
        {
            string p = AssetDatabase.GUIDToAssetPath(g);
            if (p.EndsWith(fileName.Replace(\"\\\\\", \"/\")) || p.Contains(\"/Skins/\"))
            {
                map = AssetDatabase.LoadAssetAtPath<Texture2D>(p);
                if (map != null) break;
            }
        }
        if (map == null) return false;
        if (mat.HasProperty(property))
        {
            mat.SetTexture(property, map);
            if (asNormal) mat.EnableKeyword(\"_NORMALMAP\");
            Debug.Log($\"Material assigned {property}: {fileName}\");
            return true;
        }
        return false;
    }
    
    static void GeneratePrefab(string modPath, string systemName, string prefabName)
    {
        string prefabFileName = prefabName ?? $\"{systemName}_Prefab\";
        string prefabPath = $\"Assets/Resources/{systemName}/Prefabs/{prefabFileName}.prefab\";
        string fullPath = Path.Combine(modPath, prefabPath);
        string dir = Path.GetDirectoryName(fullPath);
        
        if (!Directory.Exists(dir))
            Directory.CreateDirectory(dir);

        AssetDatabase.Refresh();
        string stem = System.Text.RegularExpressions.Regex.Replace(systemName, \"[^A-Za-z0-9_]\", \"_\");
        string[] meshPaths = new string[] {
            $\"Assets/Resources/{systemName}/Meshes/{stem}.fbx\",
            $\"Assets/Resources/{systemName}/Meshes/{systemName}.fbx\",
            $\"Assets/Resources/{systemName}/Meshes/{prefabFileName}.fbx\",
            \"Assets/Resources/Meshes/\" + stem + \".fbx\"
        };

        GameObject go = null;
        string usedMesh = null;
        foreach (string meshPath in meshPaths)
        {
            if (!File.Exists(Path.Combine(modPath, meshPath.Replace('/', Path.DirectorySeparatorChar))))
                continue;
            GameObject model = AssetDatabase.LoadAssetAtPath<GameObject>(meshPath);
            if (model != null)
            {
                go = (GameObject)PrefabUtility.InstantiatePrefab(model);
                if (go != null)
                {
                    go.name = prefabFileName;
                    usedMesh = meshPath;
                    break;
                }
            }
            Mesh mesh = AssetDatabase.LoadAssetAtPath<Mesh>(meshPath);
            if (mesh != null)
            {
                go = new GameObject(prefabFileName);
                MeshFilter mf = go.AddComponent<MeshFilter>();
                mf.sharedMesh = mesh;
                go.AddComponent<MeshRenderer>();
                usedMesh = meshPath;
                break;
            }
        }
        if (go == null)
            go = new GameObject(prefabFileName);

        string matPath = $\"Assets/Resources/{systemName}/Materials/{systemName}_Material.mat\";
        Material mat = AssetDatabase.LoadAssetAtPath<Material>(matPath);
        if (mat != null)
        {
            Renderer[] renderers = go.GetComponentsInChildren<Renderer>(true);
            foreach (Renderer r in renderers)
                r.sharedMaterial = mat;
        }

        PrefabUtility.SaveAsPrefabAsset(go, prefabPath);
        Object.DestroyImmediate(go);
        if (usedMesh != null)
            Debug.Log($\"Prefab created with mesh {usedMesh}: {prefabPath}\");
        else
            Debug.LogWarning($\"Prefab created without FBX (empty root): {prefabPath}\");
    }
    
    static void RefreshAssetDatabase()
    {
        AssetDatabase.Refresh();
        Debug.Log(\"Asset database refreshed\");
    }
    
    static void GenerateShader(string modPath, string systemName, string shaderName)
    {
        string shaderFileName = shaderName ?? $\"{systemName}_Shader\";
        string shaderPath = $\"Assets/Resources/{systemName}/Shaders/{shaderFileName}.shader\";
        string fullPath = Path.Combine(modPath, shaderPath);
        string dir = Path.GetDirectoryName(fullPath);
        
        if (!Directory.Exists(dir))
            Directory.CreateDirectory(dir);
        
        string shaderCode = $\"Shader \\\"{shaderFileName}\\\"
{{
    Properties
    {{
        _MainTex (\\\"Texture\\\", 2D) = \\\"white\\\" {{}}
        _Color (\\\"Color\\\", Color) = (1,1,1,1)
    }}
    SubShader
    {{
        Tags {{ \\\"RenderType\\\"=\\\"Opaque\\\" }}
        LOD 100
        
        Pass
        {{
            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #include \\\"UnityCG.cginc\\\"
            
            struct appdata {{ float4 vertex : POSITION; float2 uv : TEXCOORD0; }};
            struct v2f {{ float2 uv : TEXCOORD0; float4 vertex : SV_POSITION; }};
            
            sampler2D _MainTex;
            float4 _MainTex_ST;
            float4 _Color;
            
            v2f vert (appdata v) {{ v2f o; o.vertex = UnityObjectToClipPos(v.vertex); o.uv = TRANSFORM_TEX(v.uv, _MainTex); return o; }}
            float4 frag (v2f i) : SV_Target {{ return tex2D(_MainTex, i.uv) * _Color; }}
            ENDCG
        }}
    }}
}}\";
        
        File.WriteAllText(fullPath, shaderCode);
        AssetDatabase.ImportAsset(shaderPath);
        Debug.Log($\"Shader created: {shaderPath}\");
    }
}
"@
    
    $editorScriptPath = Join-Path $editorScriptsDir "AssetGeneratorEditor.cs"
    $enc = New-Object System.Text.UTF8Encoding $false
    [System.IO.File]::WriteAllText($editorScriptPath, $scriptContent, $enc)
    
    try {
        # Run Unity in batch mode to execute the script
        $projectPath = $ModPath
        
        # Verify project path is a valid Unity project
        $projectSettingsPath = Join-Path $projectPath "ProjectSettings"
        $assetsPath = Join-Path $projectPath "Assets"
        if (-not (Test-Path $projectSettingsPath) -or -not (Test-Path $assetsPath)) {
            Write-Host "  [Warning] Path does not appear to be a valid Unity project: $projectPath" -ForegroundColor Yellow
            Write-Host "  [Info] Expected: ProjectSettings/ and Assets/ folders" -ForegroundColor Gray
            return $false
        }
        
        $logFile = Join-Path $env:TEMP "unity_asset_gen_$(Get-Random).log"
        
        $quotedProject = '"' + ($projectPath -replace '"', '') + '"'
        $quotedLog = '"' + ($logFile -replace '"', '') + '"'
        $argString = "-batchmode -quit -projectPath $quotedProject -executeMethod AssetGeneratorEditor.GenerateAsset -logFile $quotedLog"
        
        # Start process in background job for timeout handling
        $job = Start-Job -ScriptBlock {
            param($UnityPath, $ArgString)
            $process = Start-Process -FilePath $UnityPath -ArgumentList $ArgString -PassThru -NoNewWindow -Wait
            return $process.ExitCode
        } -ArgumentList $UnityPath, $argString
        
        # Wait for job with timeout
        $completed = Wait-Job -Job $job -Timeout $TimeoutSeconds
        if ($completed) {
            $exitCode = Receive-Job -Job $job
            Remove-Job -Job $job -Force
            $process = [PSCustomObject]@{ ExitCode = $exitCode }
        } else {
            # Timeout occurred - stop the job and Unity process
            Write-Host "  [Warning] Unity execution timed out after $TimeoutSeconds seconds" -ForegroundColor Yellow
            Stop-Job -Job $job -ErrorAction SilentlyContinue
            Remove-Job -Job $job -Force -ErrorAction SilentlyContinue
            # Try to kill Unity process if still running
            Get-Process -Name "Unity" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
            return $false
        }
        
        # Check Unity log for errors
        if (Test-Path $logFile) {
            $logContent = Get-Content $logFile -Raw
            $logLines = Get-Content $logFile
            
            # Check for fatal errors or compilation issues
            if ($logContent -match "fatal error|Aborting batchmode|Exception:|Error:|Compilation failed|Scripts have compiler errors") {
                Write-Host "  [Error] Unity reported errors:" -ForegroundColor Red
                
                # Show relevant error lines (last 20 lines, focusing on errors)
                $errorLines = $logLines | Select-Object -Last 20
                $foundError = $false
                foreach ($line in $errorLines) {
                    if ($line -match "error|Error|ERROR|Exception|fatal|Aborting|compiler|Compilation") {
                        Write-Host "    $line" -ForegroundColor Red
                        $foundError = $true
                    } elseif ($foundError -and $line.Trim() -ne "") {
                        # Show context lines after errors
                        Write-Host "    $line" -ForegroundColor DarkGray
                    }
                }
                
                # Check for compilation errors specifically
                if ($logContent -match "Scripts have compiler errors|Compilation failed") {
                    Write-Host "  [Warning] Unity project has compilation errors. Fix errors in Unity Editor first." -ForegroundColor Yellow
                    Write-Host "  [Info] Open the project in Unity Editor to see compilation errors" -ForegroundColor Gray
                }
                
                Write-Host "  [Info] Full Unity log: $logFile" -ForegroundColor Gray
                return $false
            }
            
            # Check for success
            if ($process.ExitCode -eq 0 -and $logContent -match "Asset created|Material created|Prefab created|Shader created") {
                Remove-Item $logFile -Force -ErrorAction SilentlyContinue
                return $true
            }
        }
        
        if ($process.ExitCode -ne 0) {
            Write-Host "  [Warning] Unity exited with code: $($process.ExitCode)" -ForegroundColor Yellow
            if (Test-Path $logFile) {
                Write-Host "  [Info] Check Unity log for details: $logFile" -ForegroundColor Gray
                # Show a snippet of the log
                $logLines = Get-Content $logFile -Tail 5
                Write-Host "  [Log snippet]:" -ForegroundColor Gray
                $logLines | ForEach-Object { Write-Host "    $_" -ForegroundColor DarkGray }
            }
            return $false
        }
    }
    catch {
        Write-Host "  [Error] Unity execution failed: $_" -ForegroundColor Red
        return $false
    }
    
    return $false
}

function Generate-UnityMaterial {
    param(
        [string]$ModPath,
        [string]$SystemName,
        [string]$TexturePath,
        [string]$ShaderName = "Standard",
        [string]$UnityPath = ""
    )
    
    $unityPath = Find-UnityEditor -ModPath $ModPath -ManualPath $UnityPath
    if (-not $unityPath) {
        Write-Host "  [Warning] Unity not found, skipping material generation" -ForegroundColor Yellow
        return $false
    }
    
    return Invoke-UnityEditorScript -UnityPath $unityPath -ModPath $ModPath `
        -MethodName "GenerateMaterial" `
        -Parameters @{
            systemName = $SystemName
            texturePath = $TexturePath
            shaderName = $ShaderName
        }
}

function Generate-UnityPrefab {
    param(
        [string]$ModPath,
        [string]$SystemName,
        [string]$PrefabName,
        [string]$UnityPath = ""
    )
    
    $unityPath = Find-UnityEditor -ModPath $ModPath -ManualPath $UnityPath
    if (-not $unityPath) {
        Write-Host "  [Warning] Unity not found, skipping prefab generation" -ForegroundColor Yellow
        return $false
    }
    
    return Invoke-UnityEditorScript -UnityPath $unityPath -ModPath $ModPath `
        -MethodName "GeneratePrefab" `
        -Parameters @{
            systemName = $SystemName
            prefabName = $PrefabName
        }
}

function Generate-SpellAssetsWithEnhancedGenerator {
    <#
    .SYNOPSIS
    Generates spell assets using the enhanced C# AssetGenerator with advanced features.
    
    .DESCRIPTION
    Uses the AssetGenerationPipeline to generate spell assets with:
    - Advanced mesh shapes (torus, spiral, wave, vortex)
    - Enhanced material generation with shader support
    - Procedural texture patterns
    - Mesh optimization and simplification
    - Description-based generation (spell description is primary source)
    #>
    param(
        [Parameter(Mandatory=$true)]
        [string]$ModPath,
        
        [Parameter(Mandatory=$true)]
        [string]$SpellId,
        
        [Parameter(Mandatory=$true)]
        [string]$SpellName,
        
        [string]$SpellDescription = "",
        
        [string]$Element = "Neutral",
        
        [string]$Style = "Classic",
        
        [string]$Quality = "Medium",
        
        [switch]$GenerateProjectile = $true,
        
        [switch]$GenerateImpact = $true,
        
        [switch]$GenerateIcon = $true,
        
        [switch]$GenerateCast = $false,
        
        [string]$UnityPath = ""
    )
    
    $unityPath = Find-UnityEditor -ModPath $ModPath -ManualPath $UnityPath
    if (-not $unityPath) {
        Write-Host "  [Warning] Unity not found, cannot use enhanced asset generator" -ForegroundColor Yellow
        Write-Host "  [Info] Falling back to basic asset generation..." -ForegroundColor Gray
        Write-Host "  [Tip] Use -UnityPath parameter to specify Unity.exe location manually" -ForegroundColor Gray
        return $false
    }
    
    Write-Host "  [Enhanced Generator] Generating spell assets for: $SpellName" -ForegroundColor Cyan
    if ($SpellDescription) {
        Write-Host "    Description: $SpellDescription" -ForegroundColor Gray
        Write-Host "    [Using description-based generation]" -ForegroundColor Green
    }
    Write-Host "    Element: $Element, Style: $Style, Quality: $Quality" -ForegroundColor Gray
    
    $params = @{
        spellId = $SpellId
        spellName = $SpellName
        element = $Element
        style = $Style
        quality = $Quality
    }
    
    if ($SpellDescription) {
        $params["spellDescription"] = $SpellDescription
    }
    
    return Invoke-UnityEditorScript -UnityPath $unityPath -ModPath $ModPath `
        -MethodName "GenerateSpellAssets" `
        -Parameters $params `
        -TimeoutSeconds 600
}

function Generate-UnityShader {
    param(
        [string]$ModPath,
        [string]$SystemName,
        [string]$ShaderName,
        [string]$UnityPath = ""
    )
    
    $unityPath = Find-UnityEditor -ModPath $ModPath -ManualPath $UnityPath
    if (-not $unityPath) {
        Write-Host "  [Warning] Unity not found, skipping shader generation" -ForegroundColor Yellow
        return $false
    }
    
    return Invoke-UnityEditorScript -UnityPath $unityPath -ModPath $ModPath `
        -MethodName "GenerateShader" `
        -Parameters @{
            systemName = $SystemName
            shaderName = $ShaderName
        }
}

function Import-UnityAssets {
    <#
    .SYNOPSIS
    Import assets directly into Unity
    
    .DESCRIPTION
    Imports assets into Unity using the UnityAssetImporter. Supports single files, directories, and batch imports.
    
    .PARAMETER ModPath
    Path to the mod directory
    
    .PARAMETER AssetPaths
    Array of asset file paths to import
    
    .PARAMETER DirectoryPath
    Directory path to import all assets from
    
    .PARAMETER Recursive
    Import assets recursively from subdirectories
    
    .PARAMETER ForceReimport
    Force reimport of existing assets
    
    .PARAMETER RefreshDatabase
    Refresh Unity asset database after import
    
    .EXAMPLE
    Import-UnityAssets -ModPath "E:\...\CustomRaceClassCreator" -DirectoryPath "Assets/Generated" -Recursive
    
    .EXAMPLE
    Import-UnityAssets -ModPath "E:\...\CustomRaceClassCreator" -AssetPaths @("Assets/texture.png", "Assets/material.mat")
    #>
    param(
        [Parameter(Mandatory=$true)]
        [string]$ModPath,
        
        [string[]]$AssetPaths = @(),
        
        [string]$DirectoryPath = "",
        
        [switch]$Recursive,
        
        [switch]$ForceReimport,
        
        [switch]$RefreshDatabase,
        
        [string]$UnityPath = ""
    )
    
    $unityPath = Find-UnityEditor -ModPath $ModPath -ManualPath $UnityPath
    if (-not $unityPath) {
        Write-Host "  [Warning] Unity not found, cannot import assets" -ForegroundColor Yellow
        return $false
    }
    
    $params = @{
        modPath = $ModPath
    }
    
    if ($AssetPaths.Count -gt 0) {
        $params["importType"] = "files"
        $params["assetPaths"] = ($AssetPaths -join ",")
    } elseif ($DirectoryPath) {
        $params["importType"] = "directory"
        $params["directoryPath"] = $DirectoryPath
        $params["recursive"] = $Recursive.IsPresent
    } else {
        Write-Host "  [Error] Must specify either -AssetPaths or -DirectoryPath" -ForegroundColor Red
        return $false
    }
    
    $params["forceReimport"] = $ForceReimport.IsPresent
    $params["refreshDatabase"] = $RefreshDatabase.IsPresent
    
    Write-Host "  [Unity Import] Importing assets..." -ForegroundColor Cyan
    return Invoke-UnityEditorScript -UnityPath $unityPath -ModPath $ModPath `
        -MethodName "ImportAssets" `
        -Parameters $params `
        -TimeoutSeconds 600
}

function Refresh-UnityAssetDatabase {
    <#
    .SYNOPSIS
    Refresh Unity asset database
    
    .DESCRIPTION
    Refreshes the Unity asset database, causing Unity to re-scan and reimport changed assets.
    
    .PARAMETER ModPath
    Path to the mod directory
    
    .EXAMPLE
    Refresh-UnityAssetDatabase -ModPath "E:\...\CustomRaceClassCreator"
    #>
    param(
        [Parameter(Mandatory=$true)]
        [string]$ModPath,
        
        [string]$UnityPath = ""
    )
    
    $unityPath = Find-UnityEditor -ModPath $ModPath -ManualPath $UnityPath
    if (-not $unityPath) {
        Write-Host "  [Warning] Unity not found, cannot refresh asset database" -ForegroundColor Yellow
        return $false
    }
    
    Write-Host "  [Unity] Refreshing asset database..." -ForegroundColor Cyan
    return Invoke-UnityEditorScript -UnityPath $unityPath -ModPath $ModPath `
        -MethodName "RefreshAssetDatabase" `
        -Parameters @{} `
        -TimeoutSeconds 60
}

# ============================================================
# HELPER FUNCTIONS
# ============================================================

# Note: Model selection is handled by Shared OllamaIntegration.psm1
# The shared module automatically:
# - Routes visual tasks to "visual" tier (llama3.1:8b by default)
# - Detects dark tone content and routes to "dark_tone" tier
# - Escalates to "escalation" tier if models refuse
# No custom model selection needed - use Invoke-OllamaRequest with appropriate TaskType

function Write-ProgressBar {
    param(
        [int]$Percent,
        [string]$Activity = "Processing",
        [string]$Status = ""
    )
    
    $barLength = 50
    $filled = [Math]::Floor($Percent / 100 * $barLength)
    $empty = $barLength - $filled
    $bar = "[" + ("=" * $filled) + (" " * $empty) + "]"
    
    Write-Host "`r$Activity $bar $Percent% - $Status" -NoNewline
}

function Invoke-OllamaChat {
    param(
        [string]$Prompt,
        [string]$TaskType = "visual",
        [string]$SystemPrompt = "",
        [string]$ModelName = ""
    )
    
    # Use Shared OllamaIntegration module - it handles tier routing automatically
    # For visual tasks, it auto-detects dark tone and routes to dark_tone tier
    if (Get-Command Invoke-OllamaRequest -ErrorAction SilentlyContinue) {
        return Invoke-OllamaRequest -Prompt $Prompt -TaskType $TaskType -SystemPrompt $SystemPrompt -ModelName $ModelName -UseChatAPI -AutoEscalate
    }
    
    $messages = @()
    if (-not [string]::IsNullOrWhiteSpace($SystemPrompt)) {
        $messages += @{
            role = "system"
            content = $SystemPrompt
        }
    }
    $messages += @{
        role = "user"
        content = $Prompt
    }
    
    $requestBody = @{
        model = $ModelName
        messages = $messages
        stream = $false
    } | ConvertTo-Json -Depth 10
    
    try {
        $response = Invoke-RestMethod -Uri "$script:OllamaApiUrl/chat" -Method Post -Body $requestBody -ContentType "application/json" -TimeoutSec 120
        
        if ($response.message -and $response.message.content) {
            return $response.message.content.Trim()
        }
    }
    catch {
        Write-Host "  [Warning] AI call failed: $_" -ForegroundColor Yellow
    }
    
    return $null
}

function Find-MissingAssets {
    param(
        [string]$SystemName,
        [string]$AssetType
    )
    
    $config = $script:AssetConfigs[$AssetType]
    if (-not $config) { return @() }
    
    $resourcesPath = Join-Path $ModPath "Assets\Resources\$SystemName"
    if (-not (Test-Path $resourcesPath)) {
        # System folder doesn't exist - needs textures
        if ($AssetType -eq "textures") {
            $texturePath = Join-Path $resourcesPath "Textures"
            return @(@{
                System = $SystemName
                Type = $AssetType
                Path = $texturePath
                Reason = "System folder missing - needs textures"
            })
        }
        return @()
    }
    
    $missingAssets = @()
    
    # For textures, check Materials folder specifically (Unity materials reference textures)
    if ($AssetType -eq "textures") {
        $materialsPath = Join-Path $resourcesPath "Materials"
        $texturesPath = Join-Path $resourcesPath "Textures"
        
        # Check if materials exist but textures are missing
        if (Test-Path $materialsPath) {
            $materialFiles = Get-CachedChildItem -Path $materialsPath -File -Recurse -Filter "*.mat"
            if ($materialFiles.Count -gt 0) {
                # Materials exist, check for corresponding textures
                if (-not (Test-Path $texturesPath)) {
                    $missingAssets += @{
                        System = $SystemName
                        Type = $AssetType
                        Path = $texturesPath
                        Reason = "Materials exist but no textures folder"
                    }
                }
                else {
                    $textureFiles = Get-CachedChildItem -Path $texturesPath -File -Recurse | Where-Object {
                        $ext = $_.Extension.ToLower()
                        $name = $_.Name.ToLower()
                        $isPlaceholder = $config.PlaceholderPatterns | Where-Object { $name -like "*$_*" }
                        $hasValidExtension = $config.Extensions -contains $ext
                        return (-not $isPlaceholder -and $hasValidExtension)
                    }
                    
                    if ($textureFiles.Count -eq 0) {
                        $missingAssets += @{
                            System = $SystemName
                            Type = $AssetType
                            Path = $texturesPath
                            Reason = "Materials exist but only placeholder textures"
                        }
                    }
                }
            }
        }
        
        # Also check if textures folder is missing entirely
        if (-not (Test-Path $texturesPath)) {
            $missingAssets += @{
                System = $SystemName
                Type = $AssetType
                Path = $texturesPath
                Reason = "Textures folder missing"
            }
        }
    }
    
    # General check for other asset types
    $expectedFolders = @($config.Folder, "Prefabs", "Materials", "Textures", "Icons", "Sprites")
    
    foreach ($folder in $expectedFolders) {
        $folderPath = Join-Path $resourcesPath $folder
        if (Test-Path $folderPath) {
            $files = Get-CachedChildItem -Path $folderPath -File -Recurse | Where-Object {
                $ext = $_.Extension.ToLower()
                $name = $_.Name.ToLower()
                
                # Check if it's a placeholder or missing
                $isPlaceholder = $config.PlaceholderPatterns | Where-Object { $name -like "*$_*" }
                $hasValidExtension = $config.Extensions -contains $ext
                
                if ($isPlaceholder -or (-not $hasValidExtension)) {
                    return $true
                }
                return $false
            }
            
            if ($files.Count -eq 0 -and $folder -eq $config.Folder) {
                $missingAssets += @{
                    System = $SystemName
                    Type = $AssetType
                    Path = $folderPath
                    Reason = "Empty folder"
                }
            }
        }
        elseif ($folder -eq $config.Folder) {
            $missingAssets += @{
                System = $SystemName
                Type = $AssetType
                Path = $folderPath
                Reason = "Folder missing"
            }
        }
    }
    
    return $missingAssets
}

function Get-SystemTextureTheme {
    param([string]$SystemName)
    
    # System-specific texture themes with detailed color palettes and patterns
    $themes = @{
        "DragonMagic" = @{
            Colors = @("#FF6B35", "#F7931E", "#FFD23F", "#FF1744", "#8B0000")
            Pattern = "scales, flames, dragon scales, fiery gradients"
            Style = "fiery, powerful, ancient, mystical"
            TextureType = "organic scales with metallic highlights, fire patterns"
            NormalMap = "strong surface detail, scale-like bumps"
            Emission = "bright orange-red glow, fire-like intensity"
            Description = "Dragon-themed textures with fiery colors, scale patterns, and magical glow"
        }
        "BloodMagic" = @{
            Colors = @("#8B0000", "#DC143C", "#FF1744", "#4B0000", "#FF6B6B")
            Pattern = "blood drops, veins, organic flow, liquid patterns"
            Style = "dark, visceral, organic, menacing"
            TextureType = "liquid-like, organic flow, blood splatter patterns"
            NormalMap = "smooth with subtle liquid ripples"
            Emission = "deep red glow, pulsing effect"
            Description = "Blood-themed textures with dark reds, organic patterns, and visceral details"
        }
        "Necromancy" = @{
            Colors = @("#2C1810", "#4A4A4A", "#8B7355", "#1A1A1A", "#6B4423")
            Pattern = "bones, decay, cracks, ancient symbols, runes"
            Style = "dark, decayed, ancient, gothic"
            TextureType = "weathered, cracked, bone-like, ancient stone"
            NormalMap = "strong cracks and surface detail"
            Emission = "dim green or purple glow, ethereal"
            Description = "Necromantic textures with dark tones, decay patterns, and ancient symbols"
        }
        "ElementMagic" = @{
            Colors = @("#FF6B35", "#4A90E2", "#50C878", "#FFD700", "#9370DB")
            Pattern = "elemental symbols, swirling energy, elemental fusion"
            Style = "vibrant, dynamic, elemental, magical"
            TextureType = "swirling energy, elemental fusion, dynamic patterns"
            NormalMap = "smooth with energy ripples"
            Emission = "bright multi-colored glow, elemental intensity"
            Description = "Elemental magic textures with vibrant colors, swirling patterns, and magical energy"
        }
        "DruidicMagic" = @{
            Colors = @("#228B22", "#32CD32", "#8FBC8F", "#556B2F", "#6B8E23")
            Pattern = "leaves, vines, bark, natural growth, organic"
            Style = "natural, organic, earthy, life-giving"
            TextureType = "bark texture, leaf patterns, natural growth"
            NormalMap = "strong bark texture, leaf veins"
            Emission = "soft green glow, life energy"
            Description = "Druidic textures with natural greens, organic patterns, and life energy"
        }
        "Ice" = @{
            Colors = @("#B0E0E6", "#87CEEB", "#4682B4", "#E0F6FF", "#ADD8E6")
            Pattern = "ice crystals, frost, snowflakes, frozen patterns"
            Style = "cold, crystalline, sharp, pristine"
            TextureType = "ice crystal formations, frost patterns, crystalline"
            NormalMap = "sharp crystal facets, frost detail"
            Emission = "bright blue-white glow, cold light"
            Description = "Ice-themed textures with cool blues, crystal patterns, and frost details"
        }
        "Lightning" = @{
            Colors = @("#FFD700", "#FFA500", "#FFFF00", "#FFE135", "#FFC125")
            Pattern = "lightning bolts, electric arcs, energy discharge"
            Style = "electric, energetic, sharp, dynamic"
            TextureType = "lightning patterns, electric discharge, energy arcs"
            NormalMap = "smooth with electric ripples"
            Emission = "bright yellow-white glow, electric intensity"
            Description = "Lightning textures with bright yellows, electric patterns, and energetic glow"
        }
        "CombatPlus" = @{
            Colors = @("#8B0000", "#DC143C", "#FF4500", "#B22222", "#FF6347")
            Pattern = "weapon marks, battle scars, combat symbols"
            Style = "aggressive, battle-worn, intense, martial"
            TextureType = "weathered metal, battle damage, combat wear"
            NormalMap = "strong battle damage, scratches"
            Emission = "red-orange glow, combat intensity"
            Description = "Combat-themed textures with reds, battle damage, and martial patterns"
        }
        "Technomancy" = @{
            Colors = @("#00CED1", "#1E90FF", "#4169E1", "#0000CD", "#00BFFF")
            Pattern = "circuits, tech patterns, digital, geometric"
            Style = "futuristic, technological, precise, digital"
            TextureType = "circuit board patterns, tech lines, digital"
            NormalMap = "smooth with tech detail"
            Emission = "bright cyan-blue glow, tech energy"
            Description = "Technomancy textures with tech blues, circuit patterns, and digital aesthetics"
        }
        "SpiritMagic" = @{
            Colors = @("#9370DB", "#8A2BE2", "#BA55D3", "#DA70D6", "#DDA0DD")
            Pattern = "spirits, ethereal patterns, ghostly forms, mystical"
            Style = "ethereal, ghostly, mystical, otherworldly"
            TextureType = "ethereal patterns, spirit forms, translucent"
            NormalMap = "subtle ethereal ripples"
            Emission = "purple-white glow, spirit energy"
            Description = "Spirit magic textures with purples, ethereal patterns, and ghostly aesthetics"
        }
    }
    
    # Return theme or default
    if ($themes.ContainsKey($SystemName)) {
        return $themes[$SystemName]
    }
    
    # Default theme
    return @{
        Colors = @("#4A90E2", "#9370DB", "#FF6B35", "#50C878", "#FFD700")
        Pattern = "magical swirls, energy patterns, mystical symbols"
        Style = "magical, mystical, vibrant, dynamic"
        TextureType = "swirling energy, magical patterns, dynamic"
        NormalMap = "smooth with energy ripples"
        Emission = "bright multi-colored glow, magical intensity"
        Description = "Magical textures with vibrant colors, energy patterns, and mystical aesthetics"
    }
}

function Generate-AssetSpecification {
    param(
        [string]$SystemName,
        [string]$AssetType,
        [string]$AssetName = ""
    )
    
    if (-not $UseAI) {
        return $null
    }
    
    # Get task type for this asset (uses Shared tier system)
    $taskType = $script:AssetTaskTypes[$AssetType]
    if (-not $taskType) {
        $taskType = "visual"  # Default to visual for unknown types
    }
    
    # Get system-specific theme
    $theme = Get-SystemTextureTheme -SystemName $SystemName
    
    # Enhanced system prompts with more context
    $systemPrompt = switch ($AssetType) {
        "icons" { 
            "You are a professional game icon designer specializing in pixel art and game UI. You create detailed, readable icons that work at small sizes. Generate precise JSON specifications for game icons with detailed color palettes, style descriptions, and visual properties."
        }
        "sprites" { 
            "You are a professional game sprite artist specializing in 2D game assets. You create detailed, animated-ready sprites with proper color palettes and style consistency. Generate precise JSON specifications for game sprites with detailed descriptions."
        }
        "textures" { 
            "You are a professional game texture artist specializing in procedural and hand-painted textures. You understand texture mapping, normal maps, emission maps, and material properties. Generate detailed JSON specifications for game textures with comprehensive descriptions, color palettes, pattern types, and material properties."
        }
        "materials" { 
            "You are a technical artist specializing in Unity materials and shaders. You understand PBR workflows, shader properties, and material optimization. Generate precise JSON specifications for Unity materials with detailed shader properties and texture assignments."
        }
        "prefabs" { 
            "You are a Unity developer specializing in prefab creation and game object composition. You understand component systems, optimization, and game-ready assets. Generate precise JSON specifications for Unity prefabs with detailed component descriptions."
        }
        default { 
            "You are a professional game asset designer with expertise in multiple asset types. Generate detailed JSON specifications for game assets with comprehensive descriptions and properties."
        }
    }
    
    # Build enhanced prompt with system-specific details
    $colorPalette = $theme.Colors -join ", "
    $patternDescription = $theme.Pattern
    $styleDescription = $theme.Style
    $textureType = $theme.TextureType
    $normalMapDesc = $theme.NormalMap
    $emissionDesc = $theme.Emission
    $systemDescription = $theme.Description
    
    $prompt = @"
Generate a detailed JSON specification for a $AssetType asset for the $SystemName system in the CustomRaceClassCreator mod for Elin.

=== ASSET CONTEXT ===
Asset Name: $AssetName
System: $SystemName
Asset Type: $AssetType

=== SYSTEM THEME ===
$systemDescription
Style: $styleDescription
Texture Type: $textureType
Pattern Style: $patternDescription

=== COLOR PALETTE ===
Recommended colors for ${SystemName}:
$colorPalette

Use 3-5 colors from this palette, ensuring good contrast and visual hierarchy.
Primary color should be the most dominant, secondary for accents, and tertiary for details.

=== TEXTURE REQUIREMENTS ===
For textures specifically, consider:
- Pattern Type: $patternDescription
- Normal Map: $normalMapDesc
- Emission Map: $emissionDesc
- Base Texture: $textureType

=== GAME STYLE REQUIREMENTS ===
- Must match Elin game style (pixel art aesthetic, high contrast, readable at small sizes)
- Must be appropriate for the $SystemName magic/feature system theme
- Must be game-ready (no external dependencies, optimized for Unity)
- Should have clear visual identity that matches the system's theme
- Consider both base texture and supporting maps (normal, emission, alpha)

=== OUTPUT FORMAT ===
Generate a detailed JSON specification with this structure:
{
  "name": "descriptive_asset_name",
  "description": "detailed description of the asset's appearance, style, and purpose",
  "colors": ["#hex1", "#hex2", "#hex3", "#hex4", "#hex5"],
  "colorDescription": "explanation of how colors are used and their purpose",
  "style": "detailed style description matching $styleDescription",
  "pattern": "specific pattern type: $patternDescription",
  "textureType": "$textureType",
  "normalMap": "$normalMapDesc",
  "emissionMap": "$emissionDesc",
  "size": [width, height],
  "properties": {
    "brightness": 0.0-1.0,
    "contrast": 0.0-1.0,
    "saturation": 0.0-1.0,
    "glowIntensity": 0.0-2.0,
    "metallic": 0.0-1.0,
    "smoothness": 0.0-1.0,
    "transparency": 0.0-1.0
  },
  "enhancements": ["specific visual enhancement 1", "specific visual enhancement 2"]
}

=== IMPORTANT ===
- Be specific and detailed in descriptions
- Use the provided color palette as a guide but feel free to suggest variations
- Consider the system's theme ($SystemName) in all aspects
- For textures, specify pattern types, normal map details, and emission properties
- Ensure colors have good contrast for readability
- Output ONLY valid JSON, no explanations, no markdown, no code blocks
"@
    
    # Use Shared OllamaIntegration - it automatically handles dark tone detection and tier routing
    $result = Invoke-OllamaChat -Prompt $prompt -TaskType $taskType -SystemPrompt $systemPrompt -ModelName $OllamaModel
    
    if ($result) {
        # Extract JSON
        $jsonMatch = $result -match '\{[\s\S]*\}'
        if ($jsonMatch) {
            try {
                $spec = $matches[0] | ConvertFrom-Json
                return $spec
            }
            catch {
                Write-Host "  [Warning] Could not parse AI JSON response" -ForegroundColor Yellow
            }
        }
    }
    
    return $null
}

function Generate-AssetWithTool {
    param(
        [string]$SystemName,
        [string]$AssetType,
        [object]$Spec,
        [string]$OutputPath,
        [string]$ModPath = $script:ModPath,
        [string]$UnityPath = ""
    )
    
    $config = $script:AssetConfigs[$AssetType]
    if (-not $config) {
        Write-Host "  [Error] Unknown asset type: $AssetType" -ForegroundColor Red
        return $false
    }
    
    # Create output directory
    $outputDir = Split-Path $OutputPath -Parent
    if (-not (Test-Path $outputDir)) {
        New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
    }
    
    switch ($AssetType) {
        "icons" {
            return Generate-IconAsset -Spec $Spec -OutputPath $OutputPath -Size $config.Size
        }
        "sprites" {
            return Generate-SpriteAsset -Spec $Spec -OutputPath $OutputPath -Size $config.Size
        }
        "textures" {
            $result = Generate-TextureAsset -Spec $Spec -OutputPath $OutputPath -Size $config.Size -SystemName $SystemName
            # Texture generation is the primary goal - materials can be created in Unity Editor later
            # Unity is primarily for bundling, not asset generation
            if ($result) {
                Write-Host "  [Info] Unique texture created. Use Unity Editor to create materials and build bundles when ready." -ForegroundColor Gray
            }
            return $result
        }
        "materials" {
            # Find associated texture first
            $texturePath = Join-Path (Split-Path $OutputPath -Parent) "..\Textures"
            $textureFile = Get-ChildItem -Path $texturePath -Filter "*$SystemName*.png" -ErrorAction SilentlyContinue | Select-Object -First 1
            $texPath = if ($textureFile) { $textureFile.FullName } else { "" }
            
            return Generate-UnityMaterial -ModPath $ModPath -SystemName $SystemName -TexturePath $texPath -UnityPath $UnityPath
        }
        "prefabs" {
            $prefabName = [System.IO.Path]::GetFileNameWithoutExtension($OutputPath)
            return Generate-UnityPrefab -ModPath $ModPath -SystemName $SystemName -PrefabName $prefabName -UnityPath $UnityPath
        }
        "feat_icons" {
            return Generate-IconAsset -Spec $Spec -OutputPath $OutputPath -Size $config.Size
        }
        "spell_icons" {
            return Generate-IconAsset -Spec $Spec -OutputPath $OutputPath -Size $config.Size
        }
        "spell_assets" {
            # Use enhanced C# AssetGenerator for spell assets
            # Extract spell information from Spec or use SystemName defaults
            $spellId = if ($Spec.spellId) { $Spec.spellId } else { ($SystemName -replace '[^a-zA-Z0-9]', '').ToLower() }
            $spellName = if ($Spec.spellName) { $Spec.spellName } else { $SystemName }
            $element = if ($Spec.element) { $Spec.element } else { 
                # Infer element from system name
                if ($SystemName -like "*Fire*" -or $SystemName -like "*Dragon*") { "Fire" }
                elseif ($SystemName -like "*Ice*" -or $SystemName -like "*Frost*") { "Ice" }
                elseif ($SystemName -like "*Nature*" -or $SystemName -like "*Druidic*") { "Nature" }
                elseif ($SystemName -like "*Blood*" -or $SystemName -like "*Necro*") { "Dark" }
                elseif ($SystemName -like "*Lightning*" -or $SystemName -like "*Electric*") { "Lightning" }
                else { "Neutral" }
            }
            $style = if ($Spec.style) { $Spec.style } else { "Classic" }
            $quality = if ($Spec.quality) { $Spec.quality } else { "Medium" }
            
            Write-Host "  [Enhanced Generator] Generating spell assets for $spellName..." -ForegroundColor Cyan
            # Extract spell description from Spec if available
            $spellDescription = if ($Spec.description) { $Spec.description } else { "" }
            
            $result = Generate-SpellAssetsWithEnhancedGenerator `
                -ModPath $ModPath `
                -SpellId $spellId `
                -SpellName $spellName `
                -SpellDescription $spellDescription `
                -Element $element `
                -Style $style `
                -Quality $quality `
                -UnityPath $UnityPath
            
            if ($result) {
                Write-Host "  [OK] Spell assets generated via enhanced C# pipeline" -ForegroundColor Green
                return $true
            } else {
                Write-Host "  [Fallback] Enhanced generator unavailable, using basic generation..." -ForegroundColor Yellow
                # Fallback to basic spell icon generation
                return Generate-IconAsset -Spec $Spec -OutputPath $OutputPath -Size 32
            }
        }
        default {
            Write-Host "  [Warning] Asset type $AssetType not yet implemented for tool generation" -ForegroundColor Yellow
            return $false
        }
    }
}

function Generate-IconAsset {
    param(
        [object]$Spec,
        [string]$OutputPath,
        [int]$Size
    )
    
    try {
        # Prefer local SD / rich procedural via generate_asset_image.py
        if (Get-Command Invoke-ElinAssetImage -ErrorAction SilentlyContinue) {
            $ok = Invoke-ElinAssetImage -Spec $Spec -OutputPath $OutputPath -AssetType icon -Size $Size -Sd auto -MetaKind sprite
            if ($ok) {
                Write-Host "  [OK] Icon via local AI/procedural pipeline" -ForegroundColor Green
                return $true
            }
            Write-Host "  [Info] Local AI path missed; trying legacy fallbacks..." -ForegroundColor Gray
        }

        # Use Elin spell asset generator if available
        $elinScript = Join-Path $PSScriptRoot "ElinSpellAssetGenerator.ps1"
        if (Test-Path $elinScript) {
            $iconName = [System.IO.Path]::GetFileNameWithoutExtension($OutputPath)
            $tempDir = Join-Path $env:TEMP "pcc_asset_gen_$(Get-Random)"
            New-Item -ItemType Directory -Path $tempDir -Force | Out-Null
            
            $colors = if ($Spec.colors) { $Spec.colors -join "," } else { "#4caf50,#81c784" }
            $description = if ($Spec.description) { $Spec.description } else { "Icon for $iconName" }
            
            # Generate using Elin tool
            $result = & $elinScript -SpellDescription $description -GenerateIcon -OutputDir $tempDir -SpellName $iconName
            
            if ($LASTEXITCODE -eq 0) {
                $generatedIcon = Get-CachedChildItem -Path $tempDir -Recurse -Filter "*.png" -File | Select-Object -First 1
                if ($generatedIcon) {
                    Copy-Item $generatedIcon.FullName $OutputPath -Force
                    Remove-Item $tempDir -Recurse -Force
                    return $true
                }
            }
            
            Remove-Item $tempDir -Recurse -Force -ErrorAction SilentlyContinue
        }
        
        # Fallback: Use PIL/Pillow directly
        $pythonScript = @"
from PIL import Image, ImageDraw
import sys

size = $Size
output = r"$OutputPath"

# Create icon
img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

# Draw simple icon
center = size // 2
radius = size // 3
draw.ellipse([center-radius, center-radius, center+radius, center+radius], 
             fill=(76, 175, 80, 255), outline=(129, 199, 132, 255), width=2)

img.save(output, 'PNG')
print("OK")
"@
        
        $tempPy = Join-Path $env:TEMP "pcc_gen_icon_$(Get-Random).py"
        [System.IO.File]::WriteAllText($tempPy, $pythonScript, (New-Object System.Text.UTF8Encoding $false))
        
        $pythonCmd = Get-Command "python" -ErrorAction SilentlyContinue
        if (-not $pythonCmd) { $pythonCmd = Get-Command "python3" -ErrorAction SilentlyContinue }
        
        if ($pythonCmd) {
            $result = & $pythonCmd.Source $tempPy 2>&1
            Remove-Item $tempPy -Force
            if ($result -match "OK") {
                return $true
            }
        }
        
        return $false
    }
    catch {
        Write-Host "  [Error] Icon generation failed: $_" -ForegroundColor Red
        return $false
    }
}

function Generate-SpriteAsset {
    param(
        [object]$Spec,
        [string]$OutputPath,
        [array]$Size
    )
    
    # Similar to icon but with different sizes
    return Generate-IconAsset -Spec $Spec -OutputPath $OutputPath -Size ($Size[0])
}

function Generate-TextureAsset {
    param(
        [object]$Spec,
        [string]$OutputPath,
        [array]$Size,
        [string]$SystemName = ""
    )
    
    try {
        # Determine texture size (use first size from array or default to 512)
        $textureSize = if ($Size -and $Size.Count -gt 0) { $Size[0] } else { 512 }

        # Prefer local SD / rich procedural (writes Unity .meta for textures)
        if (Get-Command Invoke-ElinAssetImage -ErrorAction SilentlyContinue) {
            $specObj = $Spec
            if ($SystemName -and ($specObj -is [hashtable] -or $specObj.PSObject)) {
                try {
                    if ($specObj -is [hashtable]) {
                        if (-not $specObj.ContainsKey("theme")) { $specObj["theme"] = $SystemName }
                        if (-not $specObj.ContainsKey("system")) { $specObj["system"] = $SystemName }
                    } else {
                        if (-not $specObj.theme) { $specObj | Add-Member theme $SystemName -Force }
                        if (-not $specObj.system) { $specObj | Add-Member system $SystemName -Force }
                    }
                } catch { }
            }
            $ok = Invoke-ElinAssetImage -Spec $specObj -OutputPath $OutputPath -AssetType texture -Size $textureSize -Sd auto -MetaKind default
            if ($ok) {
                Write-Host "  [OK] Texture via local AI/procedural pipeline" -ForegroundColor Green
                if (Get-Command Invoke-ElinPbrSkin -ErrorAction SilentlyContinue) {
                    $skinDir = Join-Path (Split-Path -Parent $OutputPath) "Skins"
                    $skinName = ($SystemName -replace '[^A-Za-z0-9_]', '_')
                    if (-not $skinName) { $skinName = "texture" }
                    Write-Host "  [PBR] Generating skin maps beside texture..." -ForegroundColor Cyan
                    [void](Invoke-ElinPbrSkin -OutputDir $skinDir -Name $skinName -Spec $specObj -Quality standard -Size $textureSize)
                }
                return $true
            }
            Write-Host "  [Info] Local AI texture path missed; trying inline PIL..." -ForegroundColor Gray
        }
        
        # Get colors from spec or use system defaults
        $colors = if ($Spec.colors -and $Spec.colors.Count -gt 0) {
            $Spec.colors
        } else {
            Get-SystemDefaultColors -SystemName $SystemName
        }
        
        # Get texture style/pattern from spec
        $style = if ($Spec.style) { $Spec.style.ToLower() } else { "procedural" }
        
        # Generate texture using Python with PIL and noise
        $pythonScript = @"
from PIL import Image, ImageDraw, ImageFilter
import random
import math

# Configuration
size = $textureSize
output = r"$OutputPath"
system_name = "$SystemName"
style = "$style"

# Parse colors
colors_hex = $($colors | ConvertTo-Json)
def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

colors_rgb = [hex_to_rgb(c) for c in colors_hex] if colors_hex else [(76, 175, 80), (129, 199, 132)]

# Create base image
img = Image.new('RGB', (size, size), colors_rgb[0])
pixels = img.load()

# Generate texture based on system and style
random.seed(hash(system_name) % 10000)  # Deterministic based on system name

if 'fire' in system_name.lower() or 'flame' in style or 'burn' in style:
    # Fire texture - gradient with noise
    for y in range(size):
        for x in range(size):
            # Vertical gradient (fire rises)
            gradient = 1.0 - (y / size)
            # Add noise
            noise = random.random() * 0.3
            # Create fire colors
            r = int(min(255, colors_rgb[0][0] * gradient + noise * 100))
            g = int(min(255, colors_rgb[0][1] * gradient * 0.7 + noise * 50))
            b = int(min(255, colors_rgb[0][2] * gradient * 0.5))
            pixels[x, y] = (r, g, b)
    
elif 'ice' in system_name.lower() or 'frost' in style or 'cold' in style:
    # Ice texture - crystalline pattern
    for y in range(size):
        for x in range(size):
            # Create crystalline pattern
            angle = math.atan2(y - size/2, x - size/2)
            dist = math.sqrt((x - size/2)**2 + (y - size/2)**2) / (size/2)
            pattern = math.sin(angle * 6) * math.cos(dist * 10) * 0.3 + 0.7
            # Ice blue tint
            r = int(colors_rgb[0][0] * pattern)
            g = int(colors_rgb[0][1] * pattern)
            b = int(min(255, colors_rgb[0][2] * pattern + 50))
            pixels[x, y] = (r, g, b)
    
elif 'earth' in system_name.lower() or 'stone' in style or 'rock' in style or 'geomancy' in system_name.lower():
    # Earth/stone texture - noise-based
    for y in range(size):
        for x in range(size):
            # Perlin-like noise
            noise_val = (random.random() + random.random() + random.random()) / 3.0
            # Stone colors
            r = int(colors_rgb[0][0] * (0.7 + noise_val * 0.3))
            g = int(colors_rgb[0][1] * (0.7 + noise_val * 0.3))
            b = int(colors_rgb[0][2] * (0.7 + noise_val * 0.3))
            pixels[x, y] = (r, g, b)
    
elif 'water' in system_name.lower() or 'river' in system_name.lower() or 'liquid' in style:
    # Water texture - wave pattern
    for y in range(size):
        for x in range(size):
            # Wave pattern
            wave = math.sin((x + y) * 0.1) * math.cos(x * 0.05) * 0.3 + 0.7
            # Water blue
            r = int(colors_rgb[0][0] * wave)
            g = int(colors_rgb[0][1] * wave)
            b = int(min(255, colors_rgb[0][2] * wave + 30))
            pixels[x, y] = (r, g, b)
    
elif 'nature' in system_name.lower() or 'druidic' in system_name.lower() or 'plant' in style:
    # Nature texture - organic pattern
    for y in range(size):
        for x in range(size):
            # Organic noise
            noise = (random.random() + random.random()) / 2.0
            # Nature green
            r = int(colors_rgb[0][0] * (0.6 + noise * 0.4))
            g = int(colors_rgb[0][1] * (0.7 + noise * 0.3))
            b = int(colors_rgb[0][2] * (0.6 + noise * 0.4))
            pixels[x, y] = (r, g, b)
    
elif 'blood' in system_name.lower() or 'necromancy' in system_name.lower() or 'dark' in style:
    # Dark/blood texture - swirling pattern
    for y in range(size):
        for x in range(size):
            # Swirling pattern
            angle = math.atan2(y - size/2, x - size/2)
            dist = math.sqrt((x - size/2)**2 + (y - size/2)**2) / (size/2)
            swirl = math.sin(angle * 3 + dist * 5) * 0.3 + 0.7
            # Dark red/purple
            r = int(colors_rgb[0][0] * swirl)
            g = int(colors_rgb[0][1] * swirl * 0.6)
            b = int(colors_rgb[0][2] * swirl * 0.7)
            pixels[x, y] = (r, g, b)
    
elif 'magic' in system_name.lower() or 'arcane' in system_name.lower() or 'energy' in style:
    # Magic/arcane texture - energy pattern
    for y in range(size):
        for x in range(size):
            # Energy wave
            dist = math.sqrt((x - size/2)**2 + (y - size/2)**2) / (size/2)
            energy = math.sin(dist * 8) * 0.3 + 0.7
            # Magical colors
            r = int(colors_rgb[0][0] * energy)
            g = int(colors_rgb[0][1] * energy)
            b = int(min(255, colors_rgb[0][2] * energy + 40))
            pixels[x, y] = (r, g, b)
    
elif 'combat' in system_name.lower() or 'plus' in system_name.lower():
    # Combat/Plus systems - metallic/tech texture
    for y in range(size):
        for x in range(size):
            # Tech pattern with grid-like structure
            grid_x = (x % (size // 8)) / (size // 8)
            grid_y = (y % (size // 8)) / (size // 8)
            pattern = (math.sin(grid_x * math.pi) + math.sin(grid_y * math.pi)) * 0.25 + 0.75
            # Metallic/combat colors
            r = int(colors_rgb[0][0] * pattern)
            g = int(colors_rgb[0][1] * pattern * 0.8)
            b = int(colors_rgb[0][2] * pattern * 0.7)
            pixels[x, y] = (r, g, b)
    
else:
    # Default procedural texture - noise with gradient
    for y in range(size):
        for x in range(size):
            # Gradient from center
            dist = math.sqrt((x - size/2)**2 + (y - size/2)**2) / (size/2 * math.sqrt(2))
            gradient = 1.0 - dist * 0.5
            # Add noise
            noise = random.random() * 0.2
            # Use colors
            r = int(colors_rgb[0][0] * (gradient + noise))
            g = int(colors_rgb[0][1] * (gradient + noise))
            b = int(colors_rgb[0][2] * (gradient + noise))
            pixels[x, y] = (r, g, b)

# Apply slight blur for smoother texture
img = img.filter(ImageFilter.GaussianBlur(radius=1))

# Save texture
img.save(output, 'PNG')
print("OK")
"@
        
        $tempPy = Join-Path $env:TEMP "pcc_gen_texture_$(Get-Random).py"
        [System.IO.File]::WriteAllText($tempPy, $pythonScript, (New-Object System.Text.UTF8Encoding $false))
        
        $pythonCmd = Get-Command "python" -ErrorAction SilentlyContinue
        if (-not $pythonCmd) { $pythonCmd = Get-Command "python3" -ErrorAction SilentlyContinue }
        
        if ($pythonCmd) {
            $result = & $pythonCmd.Source $tempPy 2>&1
            Remove-Item $tempPy -Force
            if ($result -match "OK" -or (Test-Path $OutputPath)) {
                return $true
            }
        }
        
        return $false
    }
    catch {
        Write-Host "  [Error] Texture generation failed: $_" -ForegroundColor Red
        return $false
    }
}

function Get-SystemDefaultColors {
    param([string]$SystemName)
    
    $systemColors = @{
        "DragonMagic" = @("#ff6b35", "#f7931e", "#ffd23f")
        "Fire" = @("#ff4444", "#ff8844", "#ffaa44")
        "Ice" = @("#88ccff", "#aaddff", "#cceeff")
        "Earth" = @("#8b7355", "#a0826d", "#b8956f")
        "Water" = @("#4a90e2", "#5ba3f5", "#6cb6ff")
        "Nature" = @("#4caf50", "#81c784", "#a5d6a7")
        "DruidicMagic" = @("#2e7d32", "#4caf50", "#66bb6a")
        "BloodMagic" = @("#8b0000", "#a52a2a", "#dc143c")
        "CombatPlus" = @("#c62828", "#d32f2f", "#ef5350")
        "QuestPlus" = @("#1976d2", "#2196f3", "#42a5f5")
        "SpriteAlter" = @("#7b1fa2", "#9c27b0", "#ba68c8")
        "Necromancy" = @("#2d5016", "#4a7c2a", "#6b9f3d")
        "Arcane" = @("#6a0dad", "#8b00ff", "#9370db")
        "Magic" = @("#6a0dad", "#8b00ff", "#9370db")
    }
    
    foreach ($key in $systemColors.Keys) {
        if ($SystemName -like "*$key*") {
            return $systemColors[$key]
        }
    }
    
    # Default colors
    return @("#4caf50", "#81c784", "#a5d6a7")
}

# ============================================================
# MAIN PROCESSING
# ============================================================

Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  CustomRaceClassCreator Asset Generator" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# Validate mod path
if (-not (Test-Path $ModPath)) {
    Write-Host "Error: Mod path not found: $ModPath" -ForegroundColor Red
    exit 1
}

$assetsPath = Join-Path $ModPath "Assets\Resources"
if (-not (Test-Path $assetsPath)) {
    Write-Host "Error: Assets\Resources folder not found in mod path" -ForegroundColor Red
    exit 1
}

# Parse asset types (prioritize textures if "all" is selected)
$assetTypesList = if ($AssetTypes -eq "all") {
    # Prioritize textures first
    @("textures") + ($script:AssetConfigs.Keys | Where-Object { $_ -ne "textures" })
} else {
    $AssetTypes -split "," | ForEach-Object { $_.Trim() }
}

# Parse systems
$systemsList = if ($Systems -eq "all") {
    $script:AllSystems
} else {
    $Systems -split "," | ForEach-Object { $_.Trim() }
}

Write-Host "Mod Path: $ModPath" -ForegroundColor Gray
Write-Host "Asset Types: $($assetTypesList -join ', ')" -ForegroundColor Gray
Write-Host "Systems: $($systemsList.Count) systems" -ForegroundColor Gray
Write-Host "Mode: $(if ($ScanOnly) { 'Scan Only' } elseif ($ImproveExisting) { 'Improve Existing' } else { 'Generate Missing' })" -ForegroundColor Gray
Write-Host "AI: $(if ($UseAI) { 'Enabled' } else { 'Disabled (using defaults)' })" -ForegroundColor Gray
Write-Host ""

# Check AI connection if using AI
if ($UseAI) {
    Write-Host "--- AI Connection ---" -ForegroundColor Cyan
    if (Get-Command Test-OllamaConnection -ErrorAction SilentlyContinue) {
        if (-not (Test-OllamaConnection)) {
            Write-Host "`n⚠ WARNING: Ollama not available. Continuing without AI suggestions." -ForegroundColor Yellow
            Write-Host "  The asset generator will run but won't provide AI-powered specifications." -ForegroundColor Gray
            $UseAI = $false
        }
        else {
            Write-Host "✓ AI connection established" -ForegroundColor Green
        }
    }
    else {
        Write-Host "  Checking Ollama connection..." -ForegroundColor Cyan
        try {
            $null = Invoke-RestMethod -Uri "$script:OllamaApiUrl/tags" -Method Get -TimeoutSec 3 -ErrorAction Stop
            Write-Host "✓ AI connection established" -ForegroundColor Green
        }
        catch {
            Write-Host "⚠ WARNING: Ollama not available. Continuing without AI suggestions." -ForegroundColor Yellow
            $UseAI = $false
        }
    }
    Write-Host ""
}

# Scan for missing assets
Write-Host "Scanning for missing assets..." -ForegroundColor Cyan
$missingAssets = @()

foreach ($system in $systemsList) {
    foreach ($assetType in $assetTypesList) {
        $missing = Find-MissingAssets -SystemName $system -AssetType $assetType
        $missingAssets += $missing
    }
}

$script:Progress.TotalAssets = $missingAssets.Count
Write-Host "Found $($missingAssets.Count) missing/placeholder assets" -ForegroundColor Green
Write-Host ""

if ($ScanOnly) {
    # Display scan results
    $missingAssets | Group-Object -Property System, Type | ForEach-Object {
        Write-Host "$($_.Name): $($_.Count) assets" -ForegroundColor Yellow
    }
    exit 0
}

# Generate assets
Write-Host "Generating assets..." -ForegroundColor Cyan
Write-Host ""

foreach ($asset in $missingAssets) {
    $script:Progress.ProcessedAssets++
    $script:Progress.CurrentSystem = $asset.System
    $script:Progress.CurrentAsset = "$($asset.Type) in $($asset.System)"
    
    $percent = [Math]::Floor(($script:Progress.ProcessedAssets / $script:Progress.TotalAssets) * 100)
    Write-ProgressBar -Percent $percent -Activity "Generating" -Status "$($asset.System) - $($asset.Type)"
    
    # Generate specification
    $spec = Generate-AssetSpecification -SystemName $asset.System -AssetType $asset.Type
    
    # Determine output path with proper naming
    if ($asset.Type -eq "textures") {
        # For textures, use system-appropriate names
        $textureName = switch -Wildcard ($asset.System) {
            "*Magic" { "$($asset.System -replace 'Magic', '')_texture" }
            "*Plus" { "$($asset.System -replace 'Plus', '')_texture" }
            default { "$($asset.System)_texture" }
        }
        $textureName = $textureName.ToLower() -replace '[^a-z0-9_]', '_'
        $outputPath = Join-Path $asset.Path "$textureName.png"
    } else {
        $assetName = "$($asset.System)_$($asset.Type)_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
        $outputPath = Join-Path $asset.Path "$assetName.png"
    }
    
    # Check AssetBundles for existing high-quality assets first
    $referenceAsset = $null
    $referenceStyle = $null
    
    if (-not $ForceRegenerate) {
        $usableAssets = Find-UsableAssetsFromBundles -ModPath $ModPath -SystemName $asset.System -AssetType $asset.Type -TargetPath $outputPath
        
        if ($usableAssets.Count -gt 0) {
            # Use best quality asset from bundle as reference
            $bestAsset = $usableAssets | Sort-Object -Property @{Expression={if($_.Quality -eq "high"){3}elseif($_.Quality -eq "medium"){2}else{1}}}, Size -Descending | Select-Object -First 1
            
            Write-Host "`n  [Found] Reference asset in bundle: $($bestAsset.Name) ($([math]::Round($bestAsset.Size/1KB, 2)) KB, $($bestAsset.Quality) quality)" -ForegroundColor Cyan
            
            if ($SkipIfBundleExists -and $bestAsset.Quality -eq "high") {
                $script:Progress.SkippedAssets++
                Write-Host "  [Skip] High-quality bundle asset exists, skipping generation" -ForegroundColor Yellow
                continue
            }
            
            # Use bundle asset as reference to create improved version
            if ($UseBundlesAsReference) {
                # Extract and analyze reference asset
                $tempRefDir = Join-Path $env:TEMP "asset_ref_$(Get-Random)"
                New-Item -ItemType Directory -Path $tempRefDir -Force | Out-Null
                
                try {
                    $refPath = Extract-ReferenceAsset -AssetInfo $bestAsset -TempDir $tempRefDir
                    
                    if ($refPath -and (Test-Path $refPath)) {
                        Write-Host "  [Analyzing] Reference asset for style extraction..." -ForegroundColor Cyan
                        $referenceStyle = Analyze-AssetReference -AssetPath $refPath -AssetType $asset.Type
                        
                        if ($referenceStyle) {
                            Write-Host "  [Reference] Colors: $($referenceStyle.colors -join ', '), Pattern: $($referenceStyle.pattern), Quality: $($referenceStyle.quality)" -ForegroundColor Gray
                            $referenceAsset = $bestAsset
                        }
                    }
                }
                finally {
                    if (Test-Path $tempRefDir) {
                        Remove-Item $tempRefDir -Recurse -Force -ErrorAction SilentlyContinue
                    }
                }
            }
            
            # If not using as reference, try to copy it directly
            if (-not $UseBundlesAsReference -or -not $referenceStyle) {
                $copied = Copy-AssetFromBundle -AssetInfo $bestAsset -TargetPath $outputPath
                if ($copied) {
                    $script:Progress.GeneratedAssets++
                    Write-Host "  [OK] Used existing asset from bundle" -ForegroundColor Green
                    continue
                }
                else {
                    Write-Host "  [Info] Could not extract from bundle, generating improved asset based on reference" -ForegroundColor Yellow
                }
            }
        }
    }
    
    # Generate improved asset using reference if available
    if ($referenceStyle -and $UseBundlesAsReference -and $UseAI) {
        Write-Host "  [Enhancing] Generating improved asset based on reference style..." -ForegroundColor Cyan
        
        # Get task type for this asset (uses Shared tier system)
        $taskType = $script:AssetTaskTypes[$asset.Type]
        if (-not $taskType) {
            $taskType = "visual"  # Default to visual
        }
        
        # Generate enhanced spec based on reference (uses Shared tier system)
        $enhancedSpec = Get-ReferenceBasedSpec -ReferenceStyle $referenceStyle -SystemName $asset.System -AssetType $asset.Type -TaskType $taskType -ModelName $OllamaModel
        
        if ($enhancedSpec) {
            Write-Host "  [Enhanced] Using AI-generated spec based on reference" -ForegroundColor Green
            $spec = $enhancedSpec
            $script:Progress.ReferenceBasedAssets++
        }
        else {
            Write-Host "  [Fallback] Using reference colors with default pattern" -ForegroundColor Yellow
            # Enhance spec with reference colors
            if ($spec.colors -and $referenceStyle.colors) {
                $spec.colors = $referenceStyle.colors
            }
            if ($referenceStyle.size) {
                $spec.size = $referenceStyle.size
            }
            $script:Progress.ReferenceBasedAssets++
        }
    }
    
    # Generate asset (improved version if reference was used)
    # Note: Unity is primarily for bundling, not asset generation
    # Focus on generating source assets (textures, icons) that Unity can bundle later
    $success = Generate-AssetWithTool -SystemName $asset.System -AssetType $asset.Type -Spec $spec -OutputPath $outputPath -ModPath $ModPath -UnityPath $UnityPath
    
    if ($success) {
        $script:Progress.GeneratedAssets++
        Write-Host "`n  [OK] Generated: $($asset.System) - $($asset.Type)" -ForegroundColor Green
        
        # For textures specifically, note that Unity can bundle them later
        if ($asset.Type -eq "textures") {
            Write-Host "  [Info] Texture created. Use Unity Editor to build asset bundles when ready." -ForegroundColor Gray
        }
    } else {
        # For materials/prefabs, failure is less critical since Unity is for bundling
        if ($asset.Type -in @("materials", "prefabs")) {
            Write-Host "`n  [Warning] $($asset.Type) generation skipped (Unity bundling can be done later)" -ForegroundColor Yellow
            Write-Host "  [Info] Source assets (textures/icons) were generated successfully" -ForegroundColor Gray
            $script:Progress.SkippedAssets++
        } else {
            $script:Progress.FailedAssets++
            Write-Host "`n  [FAIL] Failed: $($asset.System) - $($asset.Type)" -ForegroundColor Red
        }
    }
}

Write-Host "`n"
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Summary" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "Total Assets: $($script:Progress.TotalAssets)" -ForegroundColor White
Write-Host "Generated: $($script:Progress.GeneratedAssets)" -ForegroundColor Green
if ($script:Progress.ReferenceBasedAssets -gt 0) {
    Write-Host "Improved (reference-based): $($script:Progress.ReferenceBasedAssets)" -ForegroundColor Magenta
}
Write-Host "Skipped (bundle assets): $($script:Progress.SkippedAssets)" -ForegroundColor Cyan
Write-Host "Failed: $($script:Progress.FailedAssets)" -ForegroundColor Red
Write-Host "Time: $((Get-Date) - $script:Progress.StartTime)" -ForegroundColor Gray
Write-Host ""

# Optional: build AssetBundles when the exact Elin Unity Editor is installed.
if ((Get-Command Invoke-AamtUnityAssetBundles -ErrorAction SilentlyContinue) -and
    (Get-Command Resolve-UnityEditorForGame -ErrorAction SilentlyContinue) -and
    $script:Progress.GeneratedAssets -gt 0 -and
    -not $ScanOnly) {
    $elinGame = "E:\SteamLibrary\steamapps\common\Elin"
    $match = Resolve-UnityEditorForGame -GameRoot $elinGame -ManualPath $UnityPath -Quiet
    if ($match.EditorExe -and (Test-Path (Join-Path $ModPath "Assets"))) {
        Write-Host "Building AssetBundles with Unity $($match.MatchedVersion)..." -ForegroundColor Cyan
        $built = Invoke-AamtUnityAssetBundles -ProjectPath $ModPath -GameRoot $elinGame -ManualUnityPath $UnityPath -EnsureProject
        if ($built) {
            Write-Host "  [OK] AssetBundles written under Assets\AssetBundles\Windows" -ForegroundColor Green
        }
    } elseif (-not $match.EditorExe) {
        Write-Host "Skipping AssetBundle build — matching Editor not installed." -ForegroundColor Yellow
        Write-Host "  $($match.InstallHint)" -ForegroundColor Cyan
    }
}


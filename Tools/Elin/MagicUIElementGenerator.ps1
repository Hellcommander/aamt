<#
.SYNOPSIS
    Magic-Themed UI Element Generator for CustomRaceClassCreator

.DESCRIPTION
    Generates interesting UI elements (buttons, panels, frames, icons) based on magic system themes.
    Creates visually distinct UI components for each magic system with appropriate colors, patterns, and effects.

.PARAMETER ModPath
    Path to CustomRaceClassCreator mod directory

.PARAMETER SystemName
    Magic system name (e.g., "DragonMagic", "BloodMagic", "Necromancy")

.PARAMETER UIElementType
    Type of UI element to generate (button, panel, frame, icon, badge, progressbar, all)

.PARAMETER UseAI
    Use Ollama AI for design specifications

.PARAMETER OllamaModel
    Ollama model to use (default: wizardlm-uncensored:latest)

.EXAMPLE
    .\MagicUIElementGenerator.ps1 -ModPath "E:\...\CustomRaceClassCreator" -SystemName "DragonMagic" -UIElementType "all" -UseAI

.EXAMPLE
    .\MagicUIElementGenerator.ps1 -ModPath "E:\...\CustomRaceClassCreator" -SystemName "BloodMagic" -UIElementType "button,panel" -UseAI
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)]
    [string]$ModPath,
    
    [Parameter(Mandatory=$false)]
    [string]$SystemName = "all",
    
    [Parameter(Mandatory=$false)]
    [string]$UIElementType = "all",
    
    [switch]$UseAI,
    
    [string]$OllamaModel = ""  # Auto-selects based on content (llama3.1:8b for regular, wizardlm-uncensored for taboo)
)

$ErrorActionPreference = "Stop"

# Load shared asset generation settings
$settingsPath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "..\\AssetGenerationSettings.ps1"
if (Test-Path $settingsPath) {
    . $settingsPath
}

# Import unified tool detection and integration
$sharedPath = Join-Path (Split-Path $PSScriptRoot -Parent) "Shared"
Import-Module (Join-Path $sharedPath "ToolDetection.psm1") -ErrorAction SilentlyContinue
Import-Module (Join-Path $sharedPath "ToolsetIntegration.psm1") -ErrorAction SilentlyContinue
Import-Module (Join-Path $sharedPath "OllamaIntegration.psm1") -ErrorAction SilentlyContinue
Import-Module (Join-Path $sharedPath "UnityAssetExport.psm1") -ErrorAction SilentlyContinue
Import-Module (Join-Path $PSScriptRoot "ElinAssetRender.psm1") -Force -ErrorAction SilentlyContinue

# Initialize tools
$tools = Initialize-ToolsetTools `
    -RequiredTools @() `
    -OptionalTools @("Ollama", "Python", "ImageMagick")

# Show tool status
Show-ToolsetStatus -ToolsetName "Elin" `
    -RequiredTools @() `
    -OptionalTools @("Ollama", "Python", "ImageMagick")
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

# ============================================================
# CONFIGURATION
# ============================================================

if (-not $script:OllamaUrl) {
    $script:OllamaUrl = "http://localhost:11434"
    $script:OllamaApiUrl = "$script:OllamaUrl/api"
}

# Magic system themes
$script:MagicThemes = @{
    "DragonMagic" = @{
        Colors = @("#ff6b35", "#f7931e", "#ffd23f", "#ff4444")
        Pattern = "scales"
        Style = "fiery_dragon"
        Glow = $true
    }
    "BloodMagic" = @{
        Colors = @("#8b0000", "#a52a2a", "#dc143c", "#ff1744")
        Pattern = "dripping"
        Style = "bloody"
        Glow = $true
    }
    "Necromancy" = @{
        Colors = @("#2d5016", "#4a7c2a", "#6b9f3d", "#8bc34a")
        Pattern = "skull_bones"
        Style = "necrotic"
        Glow = $true
    }
    "Ice" = @{
        Colors = @("#88ccff", "#aaddff", "#cceeff", "#e3f2fd")
        Pattern = "crystalline"
        Style = "frost"
        Glow = $true
    }
    "Fire" = @{
        Colors = @("#ff4444", "#ff8844", "#ffaa44", "#ffd23f")
        Pattern = "flames"
        Style = "burning"
        Glow = $true
    }
    "Nature" = @{
        Colors = @("#2e7d32", "#4caf50", "#66bb6a", "#81c784")
        Pattern = "leaves"
        Style = "organic"
        Glow = $false
    }
    "DruidicMagic" = @{
        Colors = @("#1b5e20", "#2e7d32", "#4caf50", "#66bb6a")
        Pattern = "vines"
        Style = "druidic"
        Glow = $false
    }
    "Arcane" = @{
        Colors = @("#6a0dad", "#8b00ff", "#9370db", "#ba68c8")
        Pattern = "runes"
        Style = "mystical"
        Glow = $true
    }
    "Geomancy" = @{
        Colors = @("#5d4037", "#6d4c41", "#8d6e63", "#a1887f")
        Pattern = "stone"
        Style = "earthy"
        Glow = $false
    }
    "Technomancy" = @{
        Colors = @("#00bcd4", "#26c6da", "#4dd0e1", "#80deea")
        Pattern = "circuits"
        Style = "tech"
        Glow = $true
    }
}

# UI element configurations
$script:UIElementConfigs = @{
    "button" = @{
        Size = @(120, 40)
        States = @("normal", "hover", "pressed", "disabled")
        Description = "Interactive button with hover and pressed states"
    }
    "panel" = @{
        Size = @(200, 150)
        Variants = @("default", "header", "footer", "sidebar")
        Description = "Container panel with optional header/footer"
    }
    "frame" = @{
        Size = @(100, 100)
        Styles = @("border", "ornate", "minimal", "decorative")
        Description = "Decorative frame for content"
    }
    "icon" = @{
        Size = @(32, 32)
        Types = @("small", "medium", "large")
        Description = "System icon"
    }
    "badge" = @{
        Size = @(48, 48)
        Types = @("notification", "status", "level")
        Description = "Badge for notifications or status"
    }
    "progressbar" = @{
        Size = @(200, 20)
        States = @("empty", "quarter", "half", "threequarter", "full")
        Description = "Progress bar with fill states"
    }
}

# All magic systems
$script:AllSystems = @(
    "DragonMagic", "DreamMagic", "ElementMagic", "WispMagic", "DruidicMagic",
    "Crossmagic", "RiverMagic", "Pollution", "ArcaneSaturation", "BardicMagic",
    "SpiritMagic", "Geomancy", "Necromancy", "BloodMagic", "Golemancy",
    "SpectreMagic", "Technomancy", "TerrainMagic", "WeatherMagic", "RuneMagic",
    "EtherwindMagic", "Geoscience", "DynamicSpells", "SlotMagic"
)

# Progress tracking
$script:Progress = @{
    Total = 0
    Processed = 0
    Generated = 0
    Failed = 0
    StartTime = Get-Date
}

# ============================================================
# ASSETBUNDLE SCANNING
# ============================================================

function Scan-UIElementBundles {
    param(
        [string]$ModPath,
        [string]$SystemName
    )
    
    $foundAssets = @()
    
    # Check UI bundles
    $bundlePaths = @(
        Join-Path $ModPath "Assets\UI\AssetBundles\Windows"
        Join-Path $ModPath "Assets\AssetBundles\Windows"
    )
    
    foreach ($bundlePath in $bundlePaths) {
        if (-not (Test-Path $bundlePath)) { continue }
        
        # Look for UI-related bundles
        $bundleFiles = Get-ChildItem -Path $bundlePath -File -Filter "*.assetbundle" -ErrorAction SilentlyContinue | Where-Object {
            $name = $_.BaseName.ToLower()
            $name -like "*ui*" -or $name -like "*button*" -or $name -like "*panel*" -or 
            $name -like "*$($SystemName.ToLower())*"
        }
        
        foreach ($bundle in $bundleFiles) {
            $bundleFile = Get-Item $bundle.FullName
            $fileSize = $bundleFile.Length
            
            # Quality assessment (UI elements can be smaller)
            $quality = if ($fileSize -gt 200KB) { "high" } elseif ($fileSize -gt 20KB) { "medium" } else { "low" }
            
            if ($quality -in @("high", "medium")) {
                $foundAssets += @{
                    Path = $bundle.FullName
                    Size = $fileSize
                    Quality = $quality
                    System = $SystemName
                }
            }
        }
    }
    
    return $foundAssets
}

function Check-BundleForUIElements {
    param(
        [string]$ModPath,
        [string]$SystemName,
        [string]$ElementType
    )
    
    $bundles = Scan-UIElementBundles -ModPath $ModPath -SystemName $SystemName
    
    if ($bundles.Count -gt 0) {
        $bestBundle = $bundles | Sort-Object -Property @{Expression={if($_.Quality -eq "high"){3}elseif($_.Quality -eq "medium"){2}else{1}}}, Size -Descending | Select-Object -First 1
        Write-Host "  [Found] UI bundle: $([System.IO.Path]::GetFileName($bestBundle.Path)) ($([math]::Round($bestBundle.Size/1KB, 2)) KB, $($bestBundle.Quality) quality)" -ForegroundColor Cyan
        return $true
    }
    
    return $false
}

# ============================================================
# HELPER FUNCTIONS
# ============================================================

function Write-ProgressBar {
    param(
        [int]$Percent,
        [string]$Activity = "Generating",
        [string]$Status = ""
    )
    
    $barLength = 50
    $filled = [Math]::Floor($Percent / 100 * $barLength)
    $empty = $barLength - $filled
    $bar = "[" + ("=" * $filled) + (" " * $empty) + "]"
    
    Write-Host "`r$Activity $bar $Percent% - $Status" -NoNewline
}

function Get-SystemTheme {
    param([string]$SystemName)
    
    # Direct match
    if ($script:MagicThemes.ContainsKey($SystemName)) {
        return $script:MagicThemes[$SystemName]
    }
    
    # Partial match
    foreach ($key in $script:MagicThemes.Keys) {
        if ($SystemName -like "*$key*" -or $key -like "*$SystemName*") {
            return $script:MagicThemes[$key]
        }
    }
    
    # Extract base theme
    if ($SystemName -like "*Fire*" -or $SystemName -like "*Dragon*") {
        return $script:MagicThemes["Fire"]
    }
    elseif ($SystemName -like "*Ice*" -or $SystemName -like "*Frost*") {
        return $script:MagicThemes["Ice"]
    }
    elseif ($SystemName -like "*Nature*" -or $SystemName -like "*Druidic*") {
        return $script:MagicThemes["Nature"]
    }
    elseif ($SystemName -like "*Blood*" -or $SystemName -like "*Necro*") {
        return $script:MagicThemes["BloodMagic"]
    }
    elseif ($SystemName -like "*Arcane*" -or $SystemName -like "*Magic*") {
        return $script:MagicThemes["Arcane"]
    }
    
    # Default arcane theme
    return $script:MagicThemes["Arcane"]
}

function Invoke-OllamaChat {
    param(
        [string]$Prompt,
        [string]$ModelName,
        [string]$SystemPrompt = ""
    )
    
    # Use shared module if available
    if (Get-Command Invoke-OllamaRequest -ErrorAction SilentlyContinue) {
        return Invoke-OllamaRequest -Prompt $Prompt -TaskType "visual" -SystemPrompt $SystemPrompt -ModelName $ModelName -UseChatAPI
    }
    
    # Fallback implementation - use llama3.1:8b for regular content
    # wizardlm-uncensored should only be used for taboo/mutation content
    if ([string]::IsNullOrWhiteSpace($ModelName)) {
        $ModelName = "llama3.1:8b"
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

function Generate-UIElementSpec {
    param(
        [string]$SystemName,
        [string]$ElementType,
        [object]$Theme
    )
    
    if (-not $UseAI) {
        return @{
            colors = $Theme.Colors
            pattern = $Theme.Pattern
            style = $Theme.Style
            glow = $Theme.Glow
        }
    }
    
    $systemPrompt = "You are a UI/UX designer specializing in game interface design. Generate JSON specifications for magic-themed UI elements."
    
    $prompt = @"
Generate a JSON specification for a $ElementType UI element for the $SystemName magic system.

Requirements:
- Must match the $($Theme.Style) style
- Use colors: $($Theme.Colors -join ', ')
- Pattern theme: $($Theme.Pattern)
- Should be visually interesting and game-appropriate
- Must be readable and functional

Output JSON:
{
  "colors": ["#hex1", "#hex2", "#hex3"],
  "pattern": "pattern_name",
  "style": "style_description",
  "glow": true/false,
  "effects": ["effect1", "effect2"],
  "details": "design_details"
}

Output ONLY valid JSON, no explanations.
"@
    
    $result = Invoke-OllamaChat -Prompt $prompt -ModelName $OllamaModel -SystemPrompt $systemPrompt
    
    if ($result) {
        $jsonMatch = $result -match '\{[\s\S]*\}'
        if ($jsonMatch) {
            try {
                $spec = $matches[0] | ConvertFrom-Json
                return $spec
            }
            catch {
                Write-Host "  [Warning] Could not parse AI JSON" -ForegroundColor Yellow
            }
        }
    }
    
    return @{
        colors = $Theme.Colors
        pattern = $Theme.Pattern
        style = $Theme.Style
        glow = $Theme.Glow
    }
}

function Generate-UIButton {
    param(
        [string]$SystemName,
        [object]$Spec,
        [string]$OutputDir
    )
    
    $config = $script:UIElementConfigs["button"]
    $theme = Get-SystemTheme -SystemName $SystemName

    # Prefer local SD / rich procedural per button state (Unity GUI .meta)
    if (Get-Command Invoke-ElinAssetImage -ErrorAction SilentlyContinue) {
        $states = @("normal", "hover", "pressed", "disabled")
        $allOk = $true
        foreach ($state in $states) {
            $out = Join-Path $OutputDir "button_$state.png"
            $stateSpec = @{
                colors = @($Spec.colors)
                theme = "$SystemName magic UI button $state"
                style = if ($Spec.style) { $Spec.style } else { "stylized" }
                pattern = if ($Spec.pattern) { $Spec.pattern } else { "ornate" }
                effects = @("rim-light", $(if ($Spec.glow) { "glow" } else { "" })) | Where-Object { $_ }
                description = "fantasy RPG UI button $state state for $SystemName, wide horizontal, rounded, game UI chrome"
                element = "button"
                size = 256
            }
            $ok = Invoke-ElinAssetImage -Spec $stateSpec -OutputPath $out -AssetType icon -Size 256 -Sd auto -MetaKind gui
            if (-not $ok) { $allOk = $false; break }
        }
        if ($allOk) {
            Write-Host "  [OK] UI buttons via local AI pipeline ($SystemName)" -ForegroundColor Green
            return $true
        }
        Write-Host "  [Info] Local AI buttons incomplete; falling back to procedural PIL..." -ForegroundColor Gray
    }
    
    $pythonScript = @"
from PIL import Image, ImageDraw, ImageFilter
import math
import random

system_name = "$SystemName"
colors_hex = $($Spec.colors | ConvertTo-Json)
output_dir = r"$OutputDir"

def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

colors = [hex_to_rgb(c) for c in colors_hex] if colors_hex else [(255, 107, 53), (247, 147, 30)]

# Generate button states
states = ["normal", "hover", "pressed", "disabled"]
width, height = 120, 40

for state in states:
    img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Base color varies by state
    if state == "normal":
        base_color = colors[0]
        brightness = 1.0
    elif state == "hover":
        base_color = colors[1] if len(colors) > 1 else colors[0]
        brightness = 1.2
    elif state == "pressed":
        base_color = colors[0]
        brightness = 0.8
    else:  # disabled
        base_color = tuple(int(c * 0.5) for c in colors[0])
        brightness = 0.5
    
    # Adjust brightness
    base_color = tuple(min(255, int(c * brightness)) for c in base_color)
    
    # Draw button shape with rounded corners
    corner_radius = 8
    # Main button body
    draw.rounded_rectangle([2, 2, width-2, height-2], radius=corner_radius, fill=base_color + (255,))
    
    # Highlight on top
    highlight_color = tuple(min(255, c + 30) for c in base_color)
    draw.rounded_rectangle([2, 2, width-2, height//2], radius=corner_radius, fill=highlight_color + (200,))
    
    # Shadow/border
    shadow_color = tuple(max(0, c - 40) for c in base_color)
    draw.rounded_rectangle([0, 0, width, height], radius=corner_radius, outline=shadow_color + (255,), width=2)
    
    # Add pattern based on theme
    pattern = "$($Spec.pattern)".lower()
    if "scale" in pattern or "dragon" in pattern:
        # Scale pattern
        for y in range(5, height-5, 8):
            for x in range(5, width-5, 12):
                draw.ellipse([x, y, x+8, y+6], outline=shadow_color + (100,), width=1)
    elif "drip" in pattern or "blood" in pattern:
        # Dripping pattern
        for i in range(3):
            x = width // 4 + i * (width // 4)
            points = [(x, 5), (x-3, 15), (x+3, 15), (x, 25)]
            draw.polygon(points, fill=shadow_color + (150,))
    elif "rune" in pattern or "arcane" in pattern:
        # Rune symbols
        for i in range(2):
            x = width // 3 + i * (width // 3)
            # Simple rune shape
            draw.line([x, 8, x, height-8], fill=shadow_color + (200,), width=2)
            draw.line([x-4, height//2, x+4, height//2], fill=shadow_color + (200,), width=2)
    
    # Glow effect if enabled
    if $($Spec.glow):
        glow_img = img.copy()
        glow_img = glow_img.filter(ImageFilter.GaussianBlur(radius=2))
        img = Image.alpha_composite(glow_img, img)
    
    # Save button state
    output_path = f"{output_dir}/button_{state}.png"
    img.save(output_path, 'PNG')
    print(f"OK:{state}")

print("DONE")
"@
    
    return Execute-PythonScript -Script $pythonScript -Description "UI Button"
}

function Generate-UIPanel {
    param(
        [string]$SystemName,
        [object]$Spec,
        [string]$OutputDir
    )
    
    $config = $script:UIElementConfigs["panel"]
    $theme = Get-SystemTheme -SystemName $SystemName

    if (Get-Command Invoke-ElinAssetImage -ErrorAction SilentlyContinue) {
        $variants = @("default", "header", "footer", "sidebar")
        $allOk = $true
        foreach ($variant in $variants) {
            $out = Join-Path $OutputDir "panel_$variant.png"
            $panelSpec = @{
                colors = @($Spec.colors)
                theme = "$SystemName magic UI panel $variant"
                style = if ($Spec.style) { $Spec.style } else { "stylized" }
                pattern = if ($Spec.pattern) { $Spec.pattern } else { "ornate" }
                description = "fantasy RPG UI panel $variant for $SystemName, rectangular window chrome, game UI"
                element = "panel"
                size = 512
            }
            $ok = Invoke-ElinAssetImage -Spec $panelSpec -OutputPath $out -AssetType icon -Size 512 -Sd auto -MetaKind gui
            if (-not $ok) { $allOk = $false; break }
        }
        if ($allOk) {
            Write-Host "  [OK] UI panels via local AI pipeline ($SystemName)" -ForegroundColor Green
            return $true
        }
        Write-Host "  [Info] Local AI panels incomplete; falling back to procedural PIL..." -ForegroundColor Gray
    }
    
    $pythonScript = @"
from PIL import Image, ImageDraw, ImageFilter
import math

system_name = "$SystemName"
colors_hex = $($Spec.colors | ConvertTo-Json)
output_dir = r"$OutputDir"

def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

colors = [hex_to_rgb(c) for c in colors_hex] if colors_hex else [(106, 13, 173), (139, 0, 255)]

width, height = 200, 150
variants = ["default", "header", "footer", "sidebar"]

for variant in variants:
    img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Panel background
    base_color = colors[0]
    bg_color = tuple(c // 3 for c in base_color) + (200,)  # Darker, semi-transparent
    draw.rectangle([0, 0, width, height], fill=bg_color)
    
    # Border
    border_color = base_color + (255,)
    draw.rectangle([0, 0, width-1, height-1], outline=border_color, width=3)
    
    # Decorative corner elements
    corner_size = 20
    corner_color = colors[1] if len(colors) > 1 else base_color
    
    # Top-left corner
    draw.polygon([(0, 0), (corner_size, 0), (0, corner_size)], fill=corner_color + (180,))
    # Top-right corner
    draw.polygon([(width, 0), (width-corner_size, 0), (width, corner_size)], fill=corner_color + (180,))
    # Bottom-left corner
    draw.polygon([(0, height), (corner_size, height), (0, height-corner_size)], fill=corner_color + (180,))
    # Bottom-right corner
    draw.polygon([(width, height), (width-corner_size, height), (width, height-corner_size)], fill=corner_color + (180,))
    
    # Variant-specific elements
    if variant == "header":
        # Header bar
        header_color = base_color + (220,)
        draw.rectangle([0, 0, width, 30], fill=header_color)
        draw.line([0, 30, width, 30], fill=border_color, width=2)
    elif variant == "footer":
        # Footer bar
        footer_color = base_color + (220,)
        draw.rectangle([0, height-30, width, height], fill=footer_color)
        draw.line([0, height-30, width, height-30], fill=border_color, width=2)
    elif variant == "sidebar":
        # Sidebar accent
        accent_color = base_color + (220,)
        draw.rectangle([0, 0, 40, height], fill=accent_color)
        draw.line([40, 0, 40, height], fill=border_color, width=2)
    
    # Pattern overlay
    pattern = "$($Spec.pattern)".lower()
    if "rune" in pattern:
        # Runic border pattern
        for i in range(4):
            x = width // 5 * (i + 1)
            draw.line([x, 5, x, 15], fill=corner_color + (150,), width=2)
            draw.line([x-2, 10, x+2, 10], fill=corner_color + (150,), width=2)
    
    # Glow effect
    if $($Spec.glow):
        glow_img = img.copy()
        glow_img = glow_img.filter(ImageFilter.GaussianBlur(radius=1))
        img = Image.alpha_composite(glow_img, img)
    
    output_path = f"{output_dir}/panel_{variant}.png"
    img.save(output_path, 'PNG')
    print(f"OK:{variant}")

print("DONE")
"@
    
    return Execute-PythonScript -Script $pythonScript -Description "UI Panel"
}

function Generate-UIFrame {
    param(
        [string]$SystemName,
        [object]$Spec,
        [string]$OutputDir
    )
    
    $config = $script:UIElementConfigs["frame"]
    $theme = Get-SystemTheme -SystemName $SystemName

    if (Get-Command Invoke-ElinAssetImage -ErrorAction SilentlyContinue) {
        $styles = @("border", "ornate", "minimal", "decorative")
        $allOk = $true
        foreach ($styleName in $styles) {
            $out = Join-Path $OutputDir "frame_$styleName.png"
            $frameSpec = @{
                colors = @($Spec.colors)
                theme = "$SystemName magic UI frame $styleName"
                style = $styleName
                pattern = if ($Spec.pattern) { $Spec.pattern } else { "ornate" }
                description = "fantasy RPG UI frame $styleName for $SystemName, hollow rectangular border, transparent center, game UI chrome"
                element = "frame"
                size = 256
            }
            $ok = Invoke-ElinAssetImage -Spec $frameSpec -OutputPath $out -AssetType icon -Size 256 -Sd auto -MetaKind gui
            if (-not $ok) { $allOk = $false; break }
        }
        if ($allOk) {
            Write-Host "  [OK] UI frames via local AI pipeline ($SystemName)" -ForegroundColor Green
            return $true
        }
        Write-Host "  [Info] Local AI frames incomplete; falling back to procedural PIL..." -ForegroundColor Gray
    }
    
    $pythonScript = @"
from PIL import Image, ImageDraw, ImageFilter
import math

system_name = "$SystemName"
colors_hex = $($Spec.colors | ConvertTo-Json)
output_dir = r"$OutputDir"

def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

colors = [hex_to_rgb(c) for c in colors_hex] if colors_hex else [(106, 13, 173), (139, 0, 255)]

width, height = 100, 100
styles = ["border", "ornate", "minimal", "decorative"]

for style in styles:
    img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    base_color = colors[0]
    accent_color = colors[1] if len(colors) > 1 else base_color
    
    if style == "border":
        # Simple border frame
        border_width = 8
        draw.rectangle([0, 0, width, height], outline=base_color + (255,), width=border_width)
        # Inner highlight
        draw.rectangle([border_width//2, border_width//2, width-border_width//2, height-border_width//2], 
                      outline=accent_color + (180,), width=2)
    
    elif style == "ornate":
        # Ornate decorative frame
        border_width = 12
        # Outer frame
        draw.rectangle([0, 0, width, height], outline=base_color + (255,), width=border_width)
        # Corner decorations
        corner_size = 15
        for corner_x, corner_y in [(0, 0), (width, 0), (0, height), (width, height)]:
            if corner_x == 0 and corner_y == 0:
                draw.polygon([(0, 0), (corner_size, 0), (0, corner_size)], fill=accent_color + (200,))
            elif corner_x == width and corner_y == 0:
                draw.polygon([(width, 0), (width-corner_size, 0), (width, corner_size)], fill=accent_color + (200,))
            elif corner_x == 0 and corner_y == height:
                draw.polygon([(0, height), (corner_size, height), (0, height-corner_size)], fill=accent_color + (200,))
            else:
                draw.polygon([(width, height), (width-corner_size, height), (width, height-corner_size)], fill=accent_color + (200,))
        # Side decorations
        for i in range(3):
            y = height // 4 * (i + 1)
            draw.ellipse([width//2-3, y-3, width//2+3, y+3], fill=accent_color + (180,))
    
    elif style == "minimal":
        # Minimal thin frame
        draw.rectangle([2, 2, width-2, height-2], outline=base_color + (255,), width=2)
    
    else:  # decorative
        # Decorative with pattern
        border_width = 10
        draw.rectangle([0, 0, width, height], outline=base_color + (255,), width=border_width)
        # Pattern along edges
        pattern = "$($Spec.pattern)".lower()
        if "rune" in pattern:
            for i in range(4):
                x = width // 5 * (i + 1)
                draw.line([x, 0, x, border_width], fill=accent_color + (200,), width=2)
                draw.line([x, height-border_width, x, height], fill=accent_color + (200,), width=2)
                draw.line([0, x, border_width, x], fill=accent_color + (200,), width=2)
                draw.line([width-border_width, x, width, x], fill=accent_color + (200,), width=2)
    
    # Glow effect
    if $($Spec.glow):
        glow_img = img.copy()
        glow_img = glow_img.filter(ImageFilter.GaussianBlur(radius=2))
        img = Image.alpha_composite(glow_img, img)
    
    output_path = f"{output_dir}/frame_{style}.png"
    img.save(output_path, 'PNG')
    print(f"OK:{style}")

print("DONE")
"@
    
    return Execute-PythonScript -Script $pythonScript -Description "UI Frame"
}

function Generate-ProgressBar {
    param(
        [string]$SystemName,
        [object]$Spec,
        [string]$OutputDir
    )

    if (Get-Command Invoke-ElinAssetImage -ErrorAction SilentlyContinue) {
        $fills = @(@{Name="empty"; Desc="empty"}, @{Name="quarter"; Desc="25 percent filled"}, @{Name="half"; Desc="half filled"}, @{Name="threequarter"; Desc="75 percent filled"}, @{Name="full"; Desc="completely filled"})
        $allOk = $true
        foreach ($f in $fills) {
            $out = Join-Path $OutputDir "progressbar_$($f.Name).png"
            $barSpec = @{
                colors = @($Spec.colors)
                theme = "$SystemName magic UI progress bar $($f.Name)"
                style = if ($Spec.style) { $Spec.style } else { "stylized" }
                description = "fantasy RPG horizontal progress bar $($f.Desc) for $SystemName, game UI chrome"
                element = "progressbar"
                size = 256
            }
            $ok = Invoke-ElinAssetImage -Spec $barSpec -OutputPath $out -AssetType icon -Size 256 -Sd auto -MetaKind gui
            if (-not $ok) { $allOk = $false; break }
        }
        if ($allOk) {
            Write-Host "  [OK] Progress bars via local AI pipeline ($SystemName)" -ForegroundColor Green
            return $true
        }
        Write-Host "  [Info] Local AI progress bars incomplete; falling back to procedural PIL..." -ForegroundColor Gray
    }

    $config = $script:UIElementConfigs["progressbar"]
    $theme = Get-SystemTheme -SystemName $SystemName
    
    $pythonScript = @"
from PIL import Image, ImageDraw, ImageFilter
import math

system_name = "$SystemName"
colors_hex = $($Spec.colors | ConvertTo-Json)
output_dir = r"$OutputDir"

def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

colors = [hex_to_rgb(c) for c in colors_hex] if colors_hex else [(106, 13, 173), (139, 0, 255)]

width, height = 200, 20
states = ["empty", "quarter", "half", "threequarter", "full"]
fill_amounts = [0.0, 0.25, 0.5, 0.75, 1.0]

for state, fill_amount in zip(states, fill_amounts):
    img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Background track
    bg_color = tuple(c // 4 for c in colors[0]) + (200,)
    draw.rounded_rectangle([0, 0, width, height], radius=height//2, fill=bg_color)
    
    # Fill bar
    fill_width = int(width * fill_amount)
    if fill_width > 0:
        fill_color = colors[0] + (255,)
        draw.rounded_rectangle([2, 2, fill_width-2, height-2], radius=(height-4)//2, fill=fill_color)
        
        # Highlight on top
        highlight_color = colors[1] if len(colors) > 1 else tuple(min(255, c + 40) for c in colors[0])
        highlight_color = highlight_color + (180,)
        draw.rounded_rectangle([2, 2, fill_width-2, height//2], radius=(height-4)//2, fill=highlight_color)
        
        # Glow effect
        if $($Spec.glow) and fill_amount > 0:
            glow_img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
            glow_draw = ImageDraw.Draw(glow_img)
            glow_draw.rounded_rectangle([0, 0, fill_width, height], radius=height//2, fill=fill_color + (100,))
            glow_img = glow_img.filter(ImageFilter.GaussianBlur(radius=2))
            img = Image.alpha_composite(glow_img, img)
    
    # Border
    border_color = tuple(c // 2 for c in colors[0]) + (255,)
    draw.rounded_rectangle([0, 0, width, height], radius=height//2, outline=border_color, width=2)
    
    output_path = f"{output_dir}/progressbar_{state}.png"
    img.save(output_path, 'PNG')
    print(f"OK:{state}")

print("DONE")
"@
    
    return Execute-PythonScript -Script $pythonScript -Description "Progress Bar"
}

function Generate-UIIcon {
    param(
        [string]$SystemName,
        [object]$Spec,
        [string]$OutputDir
    )
    
    $config = $script:UIElementConfigs["icon"]
    $theme = Get-SystemTheme -SystemName $SystemName

    if (Get-Command Invoke-ElinAssetImage -ErrorAction SilentlyContinue) {
        $sizes = @(@{Name="small"; Px=64}, @{Name="medium"; Px=128}, @{Name="large"; Px=256})
        $allOk = $true
        foreach ($s in $sizes) {
            $out = Join-Path $OutputDir "icon_$($s.Name).png"
            $iconSpec = @{
                colors = @($Spec.colors)
                theme = "$SystemName magic UI icon"
                style = if ($Spec.style) { $Spec.style } else { "stylized" }
                pattern = if ($Spec.pattern) { $Spec.pattern } else { "rune" }
                description = "fantasy RPG UI icon for $SystemName magic system, single centered glyph"
                element = "icon"
                size = $s.Px
            }
            $ok = Invoke-ElinAssetImage -Spec $iconSpec -OutputPath $out -AssetType icon -Size $s.Px -Sd auto -MetaKind gui
            if (-not $ok) { $allOk = $false; break }
        }
        if ($allOk) {
            Write-Host "  [OK] UI icons via local AI pipeline ($SystemName)" -ForegroundColor Green
            return $true
        }
        Write-Host "  [Info] Local AI icons incomplete; falling back to procedural PIL..." -ForegroundColor Gray
    }
    
    $pythonScript = @"
from PIL import Image, ImageDraw, ImageFilter
import math

system_name = "$SystemName"
colors_hex = $($Spec.colors | ConvertTo-Json)
output_dir = r"$OutputDir"

def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

colors = [hex_to_rgb(c) for c in colors_hex] if colors_hex else [(106, 13, 173), (139, 0, 255)]

sizes = [("small", 24), ("medium", 32), ("large", 48)]

for size_name, size in sizes:
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    base_color = colors[0]
    accent_color = colors[1] if len(colors) > 1 else base_color
    center = size // 2
    
    # Background circle
    draw.ellipse([2, 2, size-2, size-2], fill=base_color + (255,), outline=accent_color + (255,), width=2)
    
    # Pattern based on theme
    pattern = "$($Spec.pattern)".lower()
    if "rune" in pattern or "arcane" in pattern:
        # Rune symbol
        draw.line([center, center-6, center, center+6], fill=accent_color + (255,), width=2)
        draw.line([center-4, center, center+4, center], fill=accent_color + (255,), width=2)
    elif "scale" in pattern or "dragon" in pattern:
        # Scale pattern
        for i in range(3):
            y = center - 4 + i * 4
            draw.ellipse([center-6, y-2, center+6, y+2], outline=accent_color + (200,), width=1)
    elif "drip" in pattern or "blood" in pattern:
        # Drip pattern
        draw.polygon([(center, 4), (center-3, size-4), (center+3, size-4)], fill=accent_color + (255,))
    else:
        # Default symbol
        draw.ellipse([center-4, center-4, center+4, center+4], fill=accent_color + (255,))
    
    # Glow effect
    if $($Spec.glow):
        glow_img = img.copy()
        glow_img = glow_img.filter(ImageFilter.GaussianBlur(radius=1))
        img = Image.alpha_composite(glow_img, img)
    
    output_path = f"{output_dir}/icon_{size_name}.png"
    img.save(output_path, 'PNG')
    print(f"OK:{size_name}")

print("DONE")
"@
    
    return Execute-PythonScript -Script $pythonScript -Description "UI Icon"
}

function Generate-UIBadge {
    param(
        [string]$SystemName,
        [object]$Spec,
        [string]$OutputDir
    )
    
    $config = $script:UIElementConfigs["badge"]
    $theme = Get-SystemTheme -SystemName $SystemName

    if (Get-Command Invoke-ElinAssetImage -ErrorAction SilentlyContinue) {
        $types = @("notification", "status", "level")
        $allOk = $true
        foreach ($badgeType in $types) {
            $out = Join-Path $OutputDir "badge_$badgeType.png"
            $badgeSpec = @{
                colors = @($Spec.colors)
                theme = "$SystemName magic UI badge $badgeType"
                style = if ($Spec.style) { $Spec.style } else { "stylized" }
                pattern = if ($Spec.pattern) { $Spec.pattern } else { "rune" }
                description = "fantasy RPG UI badge $badgeType for $SystemName, small circular emblem, game UI"
                element = "badge"
                size = 128
            }
            $ok = Invoke-ElinAssetImage -Spec $badgeSpec -OutputPath $out -AssetType icon -Size 128 -Sd auto -MetaKind gui
            if (-not $ok) { $allOk = $false; break }
        }
        if ($allOk) {
            Write-Host "  [OK] UI badges via local AI pipeline ($SystemName)" -ForegroundColor Green
            return $true
        }
        Write-Host "  [Info] Local AI badges incomplete; falling back to procedural PIL..." -ForegroundColor Gray
    }
    
    $pythonScript = @"
from PIL import Image, ImageDraw, ImageFilter
import math

system_name = "$SystemName"
colors_hex = $($Spec.colors | ConvertTo-Json)
output_dir = r"$OutputDir"

def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

colors = [hex_to_rgb(c) for c in colors_hex] if colors_hex else [(106, 13, 173), (139, 0, 255)]

size = 48
types = ["notification", "status", "level"]

for badge_type in types:
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    base_color = colors[0]
    accent_color = colors[1] if len(colors) > 1 else base_color
    center = size // 2
    
    # Badge shape (rounded square or circle)
    if badge_type == "notification":
        # Circle badge
        draw.ellipse([4, 4, size-4, size-4], fill=base_color + (255,), outline=accent_color + (255,), width=3)
        # Exclamation mark
        draw.ellipse([center-2, center-6, center+2, center-2], fill=accent_color + (255,))
        draw.ellipse([center-2, center+2, center+2, center+6], fill=accent_color + (255,))
    elif badge_type == "status":
        # Rounded square
        draw.rounded_rectangle([4, 4, size-4, size-4], radius=8, fill=base_color + (255,), outline=accent_color + (255,), width=3)
        # Check mark
        draw.line([center-6, center, center-2, center+4], fill=accent_color + (255,), width=3)
        draw.line([center-2, center+4, center+6, center-4], fill=accent_color + (255,), width=3)
    else:  # level
        # Hexagon badge
        points = []
        for i in range(6):
            angle = math.radians(i * 60)
            x = center + int((size//2 - 4) * math.cos(angle))
            y = center + int((size//2 - 4) * math.sin(angle))
            points.append((x, y))
        draw.polygon(points, fill=base_color + (255,), outline=accent_color + (255,), width=2)
        # Number/level indicator
        draw.ellipse([center-6, center-6, center+6, center+6], fill=accent_color + (255,))
    
    # Glow effect
    if $($Spec.glow):
        glow_img = img.copy()
        glow_img = glow_img.filter(ImageFilter.GaussianBlur(radius=2))
        img = Image.alpha_composite(glow_img, img)
    
    output_path = f"{output_dir}/badge_{badge_type}.png"
    img.save(output_path, 'PNG')
    print(f"OK:{badge_type}")

print("DONE")
"@
    
    return Execute-PythonScript -Script $pythonScript -Description "UI Badge"
}

function Execute-PythonScript {
    param(
        [string]$Script,
        [string]$Description
    )
    
    try {
        $tempPy = Join-Path $env:TEMP "pcc_ui_gen_$(Get-Random).py"
        [System.IO.File]::WriteAllText($tempPy, $Script, (New-Object System.Text.UTF8Encoding $false))
        
        $pythonCmd = Get-Command "python" -ErrorAction SilentlyContinue
        if (-not $pythonCmd) { $pythonCmd = Get-Command "python3" -ErrorAction SilentlyContinue }
        
        if ($pythonCmd) {
            $result = & $pythonCmd.Source $tempPy 2>&1
            Remove-Item $tempPy -Force
            if ($result -match "DONE" -or $result -match "OK:") {
                return $true
            }
        }
        
        return $false
    }
    catch {
        Write-Host "  [Error] $Description generation failed: $_" -ForegroundColor Red
        return $false
    }
}

# ============================================================
# MAIN PROCESSING
# ============================================================

Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Magic UI Element Generator" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# Validate mod path
if (-not (Test-Path $ModPath)) {
    Write-Host "Error: Mod path not found: $ModPath" -ForegroundColor Red
    exit 1
}

# Parse systems
$systemsList = if ($SystemName -eq "all") {
    $script:AllSystems
} else {
    $SystemName -split "," | ForEach-Object { $_.Trim() }
}

# Parse element types
$elementTypesList = if ($UIElementType -eq "all") {
    $script:UIElementConfigs.Keys
} else {
    $UIElementType -split "," | ForEach-Object { $_.Trim() }
}

Write-Host "Mod Path: $ModPath" -ForegroundColor Gray
Write-Host "Systems: $($systemsList.Count) systems" -ForegroundColor Gray
Write-Host "Element Types: $($elementTypesList -join ', ')" -ForegroundColor Gray
Write-Host "AI: $(if ($UseAI) { 'Enabled' } else { 'Disabled' })" -ForegroundColor Gray
Write-Host ""

# Calculate total
$script:Progress.Total = $systemsList.Count * $elementTypesList.Count

Write-Host "Generating UI elements..." -ForegroundColor Cyan
Write-Host ""

foreach ($system in $systemsList) {
    $theme = Get-SystemTheme -SystemName $system
    Write-Host "System: $system" -ForegroundColor Yellow
    Write-Host "  Theme: $($theme.Style), Pattern: $($theme.Pattern)" -ForegroundColor Gray
    
    # Check for existing UI assets in bundles
    $hasBundleUI = Check-BundleForUIElements -ModPath $ModPath -SystemName $system -ElementType "all"
    if ($hasBundleUI) {
        Write-Host "  [Info] High-quality UI assets found in bundles for $system" -ForegroundColor Cyan
    }
    
    # Create output directory
    $uiOutputDir = Join-Path $ModPath "Assets\Resources\$system\UI"
    if (-not (Test-Path $uiOutputDir)) {
        New-Item -ItemType Directory -Path $uiOutputDir -Force | Out-Null
    }
    
    foreach ($elementType in $elementTypesList) {
        $script:Progress.Processed++
        $percent = [Math]::Floor(($script:Progress.Processed / $script:Progress.Total) * 100)
        Write-ProgressBar -Percent $percent -Activity "Generating" -Status "$system - $elementType"
        
        # Generate specification
        $spec = Generate-UIElementSpec -SystemName $system -ElementType $elementType -Theme $theme
        
        # Generate element
        $success = $false
        switch ($elementType) {
            "button" {
                $success = Generate-UIButton -SystemName $system -Spec $spec -OutputDir $uiOutputDir
            }
            "panel" {
                $success = Generate-UIPanel -SystemName $system -Spec $spec -OutputDir $uiOutputDir
            }
            "frame" {
                $success = Generate-UIFrame -SystemName $system -Spec $spec -OutputDir $uiOutputDir
            }
            "progressbar" {
                $success = Generate-ProgressBar -SystemName $system -Spec $spec -OutputDir $uiOutputDir
            }
            "icon" {
                $success = Generate-UIIcon -SystemName $system -Spec $spec -OutputDir $uiOutputDir
            }
            "badge" {
                $success = Generate-UIBadge -SystemName $system -Spec $spec -OutputDir $uiOutputDir
            }
            default {
                Write-Host "`n  [Skip] $elementType not yet implemented" -ForegroundColor Yellow
            }
        }
        
        if ($success) {
            $script:Progress.Generated++
            Write-Host "`n  [OK] Generated $elementType for $system" -ForegroundColor Green
        } else {
            $script:Progress.Failed++
            Write-Host "`n  [FAIL] Failed $elementType for $system" -ForegroundColor Red
        }
    }
    
    Write-Host ""
}

Write-Host "`n"
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Summary" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "Total Elements: $($script:Progress.Total)" -ForegroundColor White
Write-Host "Generated: $($script:Progress.Generated)" -ForegroundColor Green
Write-Host "Failed: $($script:Progress.Failed)" -ForegroundColor Red
Write-Host "Time: $((Get-Date) - $script:Progress.StartTime)" -ForegroundColor Gray
Write-Host ""
Write-Host "UI elements saved to: Assets\Resources\[SystemName]\UI\" -ForegroundColor Cyan
Write-Host ""


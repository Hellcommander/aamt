<#
.SYNOPSIS
    Slot Magic Asset Generator - Creates Better Slot Machine UI Elements
    AI-Assisted Modding Tools (AAMT) - Elin Toolset

.DESCRIPTION
    Generates high-quality slot machine assets including:
    - Slot reels with frames
    - Slot symbols (magic-themed)
    - Slot machine panels
    - Win/loss indicators
    - Animated slot effects

.PARAMETER ModPath
    Path to CustomRaceClassCreator mod directory

.PARAMETER UseAI
    Use Ollama AI for symbol design

.PARAMETER OllamaModel
    Ollama model to use (default: wizardlm-uncensored:latest)

.EXAMPLE
    .\SlotMagicAssetGenerator.ps1 -ModPath "E:\...\CustomRaceClassCreator" -UseAI
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)]
    [string]$ModPath,
    
    [switch]$UseAI,
    
    [string]$OllamaModel = "",  # Auto-selects based on content (llama3.1:8b for regular, wizardlm-uncensored for taboo)
    
    [switch]$SkipIfBundleExists
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

# Slot symbol types (magic-themed)
$script:SlotSymbols = @(
    @{ Name = "fire"; Colors = @("#ff4444", "#ff8844", "#ffaa44"); Pattern = "flame" }
    @{ Name = "ice"; Colors = @("#88ccff", "#aaddff", "#cceeff"); Pattern = "crystal" }
    @{ Name = "lightning"; Colors = @("#ffd700", "#ffed4e", "#fff9c4"); Pattern = "bolt" }
    @{ Name = "star"; Colors = @("#9370db", "#ba68c8", "#ce93d8"); Pattern = "star" }
    @{ Name = "gem"; Colors = @("#00bcd4", "#26c6da", "#4dd0e1"); Pattern = "diamond" }
    @{ Name = "skull"; Colors = @("#2d5016", "#4a7c2a", "#6b9f3d"); Pattern = "skull" }
    @{ Name = "dragon"; Colors = @("#ff6b35", "#f7931e", "#ffd23f"); Pattern = "dragon" }
    @{ Name = "rune"; Colors = @("#6a0dad", "#8b00ff", "#9370db"); Pattern = "rune" }
    @{ Name = "coin"; Colors = @("#ffd700", "#ffed4e", "#fff9c4"); Pattern = "coin" }
    @{ Name = "crown"; Colors = @("#ff6b35", "#ffd23f", "#fff9c4"); Pattern = "crown" }
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

function Scan-SlotAssetBundles {
    param([string]$ModPath)
    
    $foundAssets = @()
    
    # Check for slot-related bundles
    $bundlePaths = @(
        Join-Path $ModPath "Assets\AssetBundles\Windows"
        Join-Path $ModPath "Assets\UI\AssetBundles\Windows"
    )
    
    foreach ($bundlePath in $bundlePaths) {
        if (-not (Test-Path $bundlePath)) { continue }
        
        # Look for slot machine bundles
        $bundleFiles = Get-ChildItem -Path $bundlePath -File -Filter "*.assetbundle" -ErrorAction SilentlyContinue | Where-Object {
            $name = $_.BaseName.ToLower()
            $name -like "*slot*" -or $name -like "*machine*" -or $name -like "*reel*"
        }
        
        foreach ($bundle in $bundleFiles) {
            $bundleFile = Get-Item $bundle.FullName
            $fileSize = $bundleFile.Length
            
            # Quality assessment
            $quality = if ($fileSize -gt 500KB) { "high" } elseif ($fileSize -gt 50KB) { "medium" } else { "low" }
            
            if ($quality -in @("high", "medium")) {
                $foundAssets += @{
                    Path = $bundle.FullName
                    Size = $fileSize
                    Quality = $quality
                    LastModified = $bundleFile.LastWriteTime
                }
            }
        }
    }
    
    return $foundAssets
}

function Check-BundleForSlotAssets {
    param(
        [string]$ModPath,
        [string]$AssetName
    )
    
    $bundles = Scan-SlotAssetBundles -ModPath $ModPath
    
    foreach ($bundle in $bundles) {
        if ($bundle.Quality -eq "high") {
            Write-Host "  [Found] High-quality slot bundle: $([System.IO.Path]::GetFileName($bundle.Path)) ($([math]::Round($bundle.Size/1KB, 2)) KB)" -ForegroundColor Cyan
            Write-Host "  [Info] Consider extracting assets from bundle instead of generating" -ForegroundColor Yellow
            return $true
        }
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

function Invoke-OllamaChat {
    param(
        [string]$Prompt,
        [string]$ModelName
    )
    
    # Use shared module if available
    if (Get-Command Invoke-OllamaRequest -ErrorAction SilentlyContinue) {
        $systemPrompt = "You are a game UI designer specializing in slot machine symbols. Generate JSON specifications."
        return Invoke-OllamaRequest -Prompt $Prompt -TaskType "visual" -SystemPrompt $systemPrompt -ModelName $ModelName -UseChatAPI
    }
    
    # Fallback implementation - use llama3.1:8b for regular content
    # wizardlm-uncensored should only be used for taboo/mutation content
    if ([string]::IsNullOrWhiteSpace($ModelName)) {
        $ModelName = "llama3.1:8b"
    }
    
    $requestBody = @{
        model = $ModelName
        messages = @(
            @{
                role = "system"
                content = "You are a game UI designer specializing in slot machine symbols. Generate JSON specifications."
            },
            @{
                role = "user"
                content = $Prompt
            }
        )
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

function Generate-SlotReel {
    param(
        [string]$OutputDir
    )

    if (Get-Command Invoke-ElinAssetImage -ErrorAction SilentlyContinue) {
        $frameOut = Join-Path $OutputDir "slot_reel_frame.png"
        $bgOut = Join-Path $OutputDir "slot_reel_background.png"
        $frameOk = Invoke-ElinAssetImage -Spec @{
            colors = @("#d4af37", "#ffdf7f", "#8b7323")
            theme = "slot machine reel frame"
            style = "ornate"
            description = "fantasy casino slot reel gold metallic frame, tall vertical window, game UI"
            size = 256
        } -OutputPath $frameOut -AssetType icon -Size 256 -Sd auto -MetaKind gui
        $bgOk = Invoke-ElinAssetImage -Spec @{
            colors = @("#14141e", "#2a2a3a", "#d4af37")
            theme = "slot machine reel background"
            style = "minimal"
            description = "dark slot reel background panel, tall vertical, subtle vignette, game UI"
            size = 256
        } -OutputPath $bgOut -AssetType icon -Size 256 -Sd auto -MetaKind gui
        if ($frameOk -and $bgOk) {
            Write-Host "  [OK] Slot reel via local AI" -ForegroundColor Green
            return $true
        }
        Write-Host "  [Info] Local AI reel incomplete; procedural fallback" -ForegroundColor Gray
    }
    
    $pythonScript = @"
from PIL import Image, ImageDraw, ImageFilter
import math

output_dir = r"$OutputDir"
reel_width, reel_height = 80, 240  # Tall reel for multiple symbols

# Generate reel frame
img = Image.new('RGBA', (reel_width, reel_height), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

# Reel frame colors (gold/metallic)
frame_color = (212, 175, 55, 255)  # Gold
shadow_color = (139, 115, 35, 255)  # Dark gold
highlight_color = (255, 223, 127, 255)  # Light gold
bg_color = (20, 20, 30, 240)  # Dark background

# Background
draw.rectangle([0, 0, reel_width, reel_height], fill=bg_color)

# Outer frame (3D effect)
draw.rectangle([0, 0, reel_width, reel_height], outline=shadow_color, width=4)
draw.rectangle([2, 2, reel_width-2, reel_height-2], outline=frame_color, width=3)
draw.rectangle([4, 4, reel_width-4, reel_height-4], outline=highlight_color, width=2)

# Inner visible area (where symbols show)
inner_margin = 8
draw.rectangle([inner_margin, inner_margin, reel_width-inner_margin, reel_height-inner_margin], 
              outline=(60, 60, 80, 255), width=2)

# Corner decorations
corner_size = 12
corner_color = (255, 215, 0, 200)  # Gold corners

# Top-left corner
draw.polygon([(0, 0), (corner_size, 0), (0, corner_size)], fill=corner_color)
# Top-right corner
draw.polygon([(reel_width, 0), (reel_width-corner_size, 0), (reel_width, corner_size)], fill=corner_color)
# Bottom-left corner
draw.polygon([(0, reel_height), (corner_size, reel_height), (0, reel_height-corner_size)], fill=corner_color)
# Bottom-right corner
draw.polygon([(reel_width, reel_height), (reel_width-corner_size, reel_height), (reel_width, reel_height-corner_size)], fill=corner_color)

# Divider lines between symbol positions (3 symbols visible)
symbol_height = (reel_height - inner_margin * 2) // 3
for i in range(1, 3):
    y = inner_margin + i * symbol_height
    draw.line([inner_margin, y, reel_width-inner_margin, y], fill=(100, 100, 120, 150), width=1)

# Glow effect
glow_img = img.copy()
glow_img = glow_img.filter(ImageFilter.GaussianBlur(radius=1))
img = Image.alpha_composite(glow_img, img)

# Save reel frame
output_path = f"{output_dir}/slot_reel_frame.png"
img.save(output_path, 'PNG')
print("OK:reel_frame")

# Generate reel background (for spinning effect)
bg_img = Image.new('RGBA', (reel_width - inner_margin * 2, reel_height - inner_margin * 2), (30, 30, 40, 255))
bg_draw = ImageDraw.Draw(bg_img)

# Subtle pattern
for y in range(0, bg_img.height, 4):
    bg_draw.line([(0, y), (bg_img.width, y)], fill=(40, 40, 50, 50), width=1)

bg_output = f"{output_dir}/slot_reel_background.png"
bg_img.save(bg_output, 'PNG')
print("OK:reel_background")

print("DONE")
"@
    
    return Execute-PythonScript -Script $pythonScript -Description "Slot Reel"
}

function Generate-SlotSymbol {
    param(
        [object]$Symbol,
        [string]$OutputDir
    )

    $out = Join-Path $OutputDir "slot_symbol_$($Symbol.Name).png"
    if (Get-Command Invoke-ElinAssetImage -ErrorAction SilentlyContinue) {
        $spec = @{
            colors = @($Symbol.Colors)
            theme = "slot machine symbol $($Symbol.Name)"
            pattern = if ($Symbol.Pattern) { $Symbol.Pattern } else { "gem" }
            style = "stylized"
            description = "fantasy slot machine symbol $($Symbol.Name), single centered icon, clean silhouette"
            size = 128
        }
        $ok = Invoke-ElinAssetImage -Spec $spec -OutputPath $out -AssetType icon -Size 128 -Sd auto -MetaKind gui
        if ($ok) {
            Write-Host "  [OK] Slot symbol $($Symbol.Name) via local AI" -ForegroundColor Green
            return $true
        }
        Write-Host "  [Info] Local AI miss for $($Symbol.Name); procedural fallback" -ForegroundColor Gray
    }
    
    $pythonScript = @"
from PIL import Image, ImageDraw, ImageFilter
import math
import random

symbol_name = "$($Symbol.Name)"
colors_hex = $($Symbol.Colors | ConvertTo-Json)
pattern = "$($Symbol.Pattern)"
output_dir = r"$OutputDir"

def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

colors = [hex_to_rgb(c) for c in colors_hex]
size = 64  # Symbol size

# Create symbol
img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

base_color = colors[0]
accent_color = colors[1] if len(colors) > 1 else base_color
highlight_color = colors[2] if len(colors) > 2 else accent_color
center = size // 2

# Background circle/hexagon
bg_color = tuple(c // 4 for c in base_color) + (200,)
draw.ellipse([4, 4, size-4, size-4], fill=bg_color)

# Draw symbol based on pattern
if pattern == "flame" or symbol_name == "fire":
    # Flame symbol
    flame_points = [
        (center, size-8),
        (center-8, size-16),
        (center-4, size-24),
        (center, size-32),
        (center+4, size-24),
        (center+8, size-16)
    ]
    draw.polygon(flame_points, fill=base_color + (255,))
    # Inner flame
    inner_points = [
        (center, size-12),
        (center-4, size-20),
        (center, size-28),
        (center+4, size-20)
    ]
    draw.polygon(inner_points, fill=accent_color + (255,))
    # Tip highlight
    draw.ellipse([center-2, size-32, center+2, size-28], fill=highlight_color + (255,))

elif pattern == "crystal" or symbol_name == "ice":
    # Crystal/ice symbol
    # Main crystal
    crystal_points = [
        (center, 8),
        (center-12, size-8),
        (center, size-4),
        (center+12, size-8)
    ]
    draw.polygon(crystal_points, fill=base_color + (255,), outline=accent_color + (255,), width=2)
    # Facets
    draw.line([center, 8, center-6, size-6], fill=highlight_color + (200,), width=2)
    draw.line([center, 8, center+6, size-6], fill=highlight_color + (200,), width=2)
    draw.line([center-6, size-6, center+6, size-6], fill=highlight_color + (200,), width=2)

elif pattern == "bolt" or symbol_name == "lightning":
    # Lightning bolt
    bolt_points = [
        (center-8, 8),
        (center-4, size//3),
        (center, size//3),
        (center+4, size*2//3),
        (center, size*2//3),
        (center+8, size-8),
        (center+4, size*2//3),
        (center, size*2//3),
        (center-4, size//3),
        (center, size//3)
    ]
    draw.polygon(bolt_points, fill=base_color + (255,))
    # Inner highlight
    inner_bolt = [
        (center-4, 12),
        (center-2, size//3+4),
        (center+2, size//3+4),
        (center+2, size*2//3-4),
        (center-2, size*2//3-4),
        (center+4, size-12)
    ]
    draw.polygon(inner_bolt, fill=highlight_color + (255,))

elif pattern == "star" or symbol_name == "star":
    # Star symbol
    star_points = []
    for i in range(10):
        angle = math.radians(i * 36 - 90)
        r = size // 3 if i % 2 == 0 else size // 6
        x = center + int(r * math.cos(angle))
        y = center + int(r * math.sin(angle))
        star_points.append((x, y))
    draw.polygon(star_points, fill=base_color + (255,), outline=accent_color + (255,), width=2)
    # Center highlight
    draw.ellipse([center-4, center-4, center+4, center+4], fill=highlight_color + (255,))

elif pattern == "diamond" or symbol_name == "gem":
    # Diamond/gem symbol
    diamond_points = [
        (center, 8),
        (center-16, center),
        (center, size-8),
        (center+16, center)
    ]
    draw.polygon(diamond_points, fill=base_color + (255,), outline=accent_color + (255,), width=2)
    # Facets
    draw.polygon([(center, 8), (center-8, center-8), (center, center), (center+8, center-8)], fill=highlight_color + (200,))
    draw.polygon([(center, center), (center-8, center+8), (center, size-8), (center+8, center+8)], fill=accent_color + (200,))

elif pattern == "skull" or symbol_name == "skull":
    # Skull symbol
    # Skull shape
    draw.ellipse([center-12, 8, center+12, size//2], fill=base_color + (255,), outline=accent_color + (255,), width=2)
    # Eye sockets
    draw.ellipse([center-8, size//4, center-4, size//3], fill=(0, 0, 0, 255))
    draw.ellipse([center+4, size//4, center+8, size//3], fill=(0, 0, 0, 255))
    # Jaw
    jaw_points = [
        (center-10, size//2),
        (center-6, size-8),
        (center+6, size-8),
        (center+10, size//2)
    ]
    draw.polygon(jaw_points, fill=base_color + (255,), outline=accent_color + (255,), width=2)

elif pattern == "dragon" or symbol_name == "dragon":
    # Dragon symbol (simplified)
    # Dragon head
    draw.ellipse([center-14, 8, center+14, size//2], fill=base_color + (255,), outline=accent_color + (255,), width=2)
    # Horns
    draw.polygon([(center-12, 8), (center-16, 4), (center-10, 12)], fill=accent_color + (255,))
    draw.polygon([(center+12, 8), (center+16, 4), (center+10, 12)], fill=accent_color + (255,))
    # Body/tail
    draw.ellipse([center-8, size//2, center+8, size-8], fill=base_color + (255,), outline=accent_color + (255,), width=2)

elif pattern == "rune" or symbol_name == "rune":
    # Rune symbol
    # Main rune shape
    draw.line([center, 8, center, size-8], fill=base_color + (255,), width=4)
    draw.line([center-12, center, center+12, center], fill=base_color + (255,), width=4)
    # Decorative elements
    draw.line([center-8, 12, center+8, 12], fill=accent_color + (255,), width=2)
    draw.line([center-8, size-12, center+8, size-12], fill=accent_color + (255,), width=2)
    # Corner marks
    for x, y in [(center-10, 10), (center+10, 10), (center-10, size-10), (center+10, size-10)]:
        draw.ellipse([x-2, y-2, x+2, y+2], fill=highlight_color + (255,))

elif pattern == "coin" or symbol_name == "coin":
    # Coin symbol
    draw.ellipse([center-16, center-16, center+16, center+16], fill=base_color + (255,), outline=accent_color + (255,), width=3)
    # Coin design
    draw.ellipse([center-12, center-12, center+12, center+12], outline=highlight_color + (255,), width=2)
    # Value mark
    draw.line([center-6, center, center+6, center], fill=highlight_color + (255,), width=2)
    draw.line([center, center-6, center, center+6], fill=highlight_color + (255,), width=2)

elif pattern == "crown" or symbol_name == "crown":
    # Crown symbol
    crown_points = [
        (center-16, size-8),
        (center-12, size//2),
        (center-8, size//3),
        (center-4, size//2),
        (center, 8),
        (center+4, size//2),
        (center+8, size//3),
        (center+12, size//2),
        (center+16, size-8)
    ]
    draw.polygon(crown_points, fill=base_color + (255,), outline=accent_color + (255,), width=2)
    # Gems on crown
    for x in [center-8, center, center+8]:
        draw.ellipse([x-3, size//3-3, x+3, size//3+3], fill=highlight_color + (255,))

else:
    # Default: magical symbol
    draw.ellipse([center-16, center-16, center+16, center+16], fill=base_color + (255,), outline=accent_color + (255,), width=3)
    draw.ellipse([center-8, center-8, center+8, center+8], fill=highlight_color + (255,))

# Glow effect
glow_img = img.copy()
glow_img = glow_img.filter(ImageFilter.GaussianBlur(radius=2))
img = Image.alpha_composite(glow_img, img)

# Save symbol
output_path = f"{output_dir}/slot_symbol_{symbol_name}.png"
img.save(output_path, 'PNG')
print(f"OK:{symbol_name}")

print("DONE")
"@
    
    return Execute-PythonScript -Script $pythonScript -Description "Slot Symbol: $($Symbol.Name)"
}

function Generate-SlotMachinePanel {
    param(
        [string]$OutputDir
    )

    if (Get-Command Invoke-ElinAssetImage -ErrorAction SilentlyContinue) {
        $out = Join-Path $OutputDir "slot_machine_panel.png"
        $ok = Invoke-ElinAssetImage -Spec @{
            colors = @("#1e1428", "#d4af37", "#8b00ff")
            theme = "magical casino slot machine panel"
            style = "ornate"
            description = "fantasy slot machine main panel, gold frame on dark purple, game UI chrome"
            size = 512
        } -OutputPath $out -AssetType icon -Size 512 -Sd auto -MetaKind gui
        if ($ok) {
            Write-Host "  [OK] Slot panel via local AI" -ForegroundColor Green
            return $true
        }
        Write-Host "  [Info] Local AI panel miss; procedural fallback" -ForegroundColor Gray
    }
    
    $pythonScript = @"
from PIL import Image, ImageDraw, ImageFilter
import math

output_dir = r"$OutputDir"
panel_width, panel_height = 300, 400

# Main slot machine panel
img = Image.new('RGBA', (panel_width, panel_height), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

# Panel colors (casino/magical theme)
bg_color = (30, 20, 40, 255)  # Dark purple
frame_color = (212, 175, 55, 255)  # Gold
accent_color = (139, 0, 255, 255)  # Purple
highlight_color = (255, 223, 127, 255)  # Light gold

# Background
draw.rectangle([0, 0, panel_width, panel_height], fill=bg_color)

# Outer frame
draw.rectangle([0, 0, panel_width, panel_height], outline=frame_color, width=6)
draw.rectangle([3, 3, panel_width-3, panel_height-3], outline=accent_color, width=4)

# Decorative top section
top_height = 60
draw.rectangle([0, 0, panel_width, top_height], fill=(40, 30, 50, 255))
draw.rounded_rectangle([10, 10, panel_width-10, top_height-10], radius=8, 
                      fill=accent_color + (180,), outline=frame_color, width=2)

# Reel area (3 reels side by side)
reel_area_y = top_height + 20
reel_area_height = 240
reel_width = 80
reel_spacing = 10
start_x = (panel_width - (reel_width * 3 + reel_spacing * 2)) // 2

for i in range(3):
    reel_x = start_x + i * (reel_width + reel_spacing)
    # Reel frame outline
    draw.rounded_rectangle([reel_x, reel_area_y, reel_x + reel_width, reel_area_y + reel_area_height], 
                          radius=8, outline=frame_color, width=3)
    # Inner glow
    draw.rounded_rectangle([reel_x + 2, reel_area_y + 2, reel_x + reel_width - 2, reel_area_y + reel_area_height - 2], 
                          outline=accent_color + (150,), width=1)

# Control panel area (bottom)
control_y = reel_area_y + reel_area_height + 20
control_height = 60
draw.rectangle([0, control_y, panel_width, panel_height], fill=(25, 15, 35, 255))

# Spin button area
button_width = 100
button_x = (panel_width - button_width) // 2
draw.rounded_rectangle([button_x, control_y + 10, button_x + button_width, control_y + control_height - 10], 
                      radius=12, fill=accent_color + (220,), outline=frame_color, width=3)
# Button highlight
draw.rounded_rectangle([button_x + 2, control_y + 12, button_x + button_width - 2, control_y + 22], 
                      radius=10, fill=highlight_color + (150,))

# Decorative elements
# Corner decorations
corner_size = 20
corner_color = frame_color + (200,)
draw.polygon([(0, 0), (corner_size, 0), (0, corner_size)], fill=corner_color)
draw.polygon([(panel_width, 0), (panel_width-corner_size, 0), (panel_width, corner_size)], fill=corner_color)
draw.polygon([(0, panel_height), (corner_size, panel_height), (0, panel_height-corner_size)], fill=corner_color)
draw.polygon([(panel_width, panel_height), (panel_width-corner_size, panel_height), (panel_width, panel_height-corner_size)], fill=corner_color)

# Side decorations (runic patterns)
for y in [top_height + 5, panel_height - 25]:
    for x in [15, panel_width - 15]:
        # Simple rune mark
        draw.line([x, y, x, y+10], fill=accent_color + (150,), width=2)
        draw.line([x-3, y+5, x+3, y+5], fill=accent_color + (150,), width=2)

# Glow effect
glow_img = img.copy()
glow_img = glow_img.filter(ImageFilter.GaussianBlur(radius=2))
img = Image.alpha_composite(glow_img, img)

# Save panel
output_path = f"{output_dir}/slot_machine_panel.png"
img.save(output_path, 'PNG')
print("OK:panel")

print("DONE")
"@
    
    return Execute-PythonScript -Script $pythonScript -Description "Slot Machine Panel"
}

function Generate-WinIndicator {
    param(
        [string]$OutputDir
    )

    if (Get-Command Invoke-ElinAssetImage -ErrorAction SilentlyContinue) {
        $winOut = Join-Path $OutputDir "slot_win_indicator.png"
        $lossOut = Join-Path $OutputDir "slot_loss_indicator.png"
        $winOk = Invoke-ElinAssetImage -Spec @{
            colors = @("#ffd700", "#ffdf7f", "#d4af37")
            theme = "slot machine WIN indicator"
            style = "stylized"
            description = "fantasy casino WIN burst emblem, gold star glow, celebration UI badge, no text"
            size = 256
        } -OutputPath $winOut -AssetType icon -Size 256 -Sd auto -MetaKind gui
        $lossOk = Invoke-ElinAssetImage -Spec @{
            colors = @("#646464", "#303030", "#8b0000")
            theme = "slot machine LOSS indicator"
            style = "minimal"
            description = "fantasy casino LOSS emblem, muted gray circle with slash, UI badge, no text"
            size = 256
        } -OutputPath $lossOut -AssetType icon -Size 256 -Sd auto -MetaKind gui
        if ($winOk -and $lossOk) {
            Write-Host "  [OK] Win/loss indicators via local AI" -ForegroundColor Green
            return $true
        }
        Write-Host "  [Info] Local AI win/loss incomplete; procedural fallback" -ForegroundColor Gray
    }
    
    $pythonScript = @"
from PIL import Image, ImageDraw, ImageFilter
import math

output_dir = r"$OutputDir"

# Win indicator (flashing/glowing effect)
size = 200
img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

center = size // 2

# Win colors (gold/green for success)
win_colors = [
    (255, 215, 0, 255),  # Gold
    (255, 223, 127, 255),  # Light gold
    (212, 175, 55, 255),  # Dark gold
]

# Outer glow rings
for i, color in enumerate(win_colors):
    radius = size // 2 - i * 10
    alpha = 200 - i * 50
    draw.ellipse([center-radius, center-radius, center+radius, center+radius], 
                outline=color[:3] + (alpha,), width=4)

# "WIN" text area (represented as star burst)
star_points = []
for i in range(16):
    angle = math.radians(i * 22.5)
    r = size // 3 if i % 2 == 0 else size // 5
    x = center + int(r * math.cos(angle))
    y = center + int(r * math.sin(angle))
    star_points.append((x, y))
draw.polygon(star_points, fill=win_colors[0] + (220,), outline=win_colors[1] + (255,), width=3)

# Center highlight
draw.ellipse([center-20, center-20, center+20, center+20], fill=win_colors[1] + (255,))

# Glow effect
glow_img = img.copy()
glow_img = glow_img.filter(ImageFilter.GaussianBlur(radius=4))
img = Image.alpha_composite(glow_img, img)

output_path = f"{output_dir}/slot_win_indicator.png"
img.save(output_path, 'PNG')
print("OK:win")

# Loss indicator (subtle, not too negative)
loss_img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
loss_draw = ImageDraw.Draw(loss_img)

loss_color = (100, 100, 100, 200)  # Gray
loss_draw.ellipse([center-30, center-30, center+30, center+30], 
                 outline=loss_color, width=4)
loss_draw.line([center-20, center, center+20, center], fill=loss_color, width=4)

loss_output = f"{output_dir}/slot_loss_indicator.png"
loss_img.save(loss_output, 'PNG')
print("OK:loss")

print("DONE")
"@
    
    return Execute-PythonScript -Script $pythonScript -Description "Win/Loss Indicators"
}

function Execute-PythonScript {
    param(
        [string]$Script,
        [string]$Description
    )
    
    try {
        $tempPy = Join-Path $env:TEMP "pcc_slot_gen_$(Get-Random).py"
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
Write-Host "  Slot Magic Asset Generator" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# Validate mod path
if (-not (Test-Path $ModPath)) {
    Write-Host "Error: Mod path not found: $ModPath" -ForegroundColor Red
    exit 1
}

# Create output directory
$slotOutputDir = Join-Path $ModPath "Assets\Resources\SlotMachine\UI"
if (-not (Test-Path $slotOutputDir)) {
    New-Item -ItemType Directory -Path $slotOutputDir -Force | Out-Null
}

Write-Host "Mod Path: $ModPath" -ForegroundColor Gray
Write-Host "Output: $slotOutputDir" -ForegroundColor Gray
Write-Host "AI: $(if ($UseAI) { 'Enabled' } else { 'Disabled' })" -ForegroundColor Gray
Write-Host ""

# Check AssetBundles for existing slot assets
Write-Host "Scanning AssetBundles for existing slot assets..." -ForegroundColor Cyan
$hasBundleAssets = Check-BundleForSlotAssets -ModPath $ModPath -AssetName "slot"
if ($hasBundleAssets) {
    if ($SkipIfBundleExists) {
        Write-Host "  [Skip] High-quality assets found in bundles, skipping generation" -ForegroundColor Yellow
        Write-Host "  [Info] Use existing bundle assets or run without -SkipIfBundleExists to generate new ones" -ForegroundColor Gray
        exit 0
    } else {
        Write-Host "  [Info] High-quality assets found in bundles. Consider using those first." -ForegroundColor Yellow
        Write-Host "  [Info] Generating new assets anyway (use -SkipIfBundleExists to skip generation)" -ForegroundColor Gray
    }
}
Write-Host ""

# Calculate total
$script:Progress.Total = 1 + $script:SlotSymbols.Count + 1 + 1  # Reel + Symbols + Panel + Indicators

Write-Host "Generating slot machine assets..." -ForegroundColor Cyan
Write-Host ""

# Generate slot reel
Write-Host "Generating slot reel..." -ForegroundColor Yellow
$success = Generate-SlotReel -OutputDir $slotOutputDir
if ($success) {
    $script:Progress.Generated++
    Write-Host "  [OK] Slot reel generated" -ForegroundColor Green
} else {
    $script:Progress.Failed++
    Write-Host "  [FAIL] Slot reel generation failed" -ForegroundColor Red
}
$script:Progress.Processed++

Write-Host ""

# Generate slot symbols
Write-Host "Generating slot symbols..." -ForegroundColor Yellow
foreach ($symbol in $script:SlotSymbols) {
    $script:Progress.Processed++
    $percent = [Math]::Floor(($script:Progress.Processed / $script:Progress.Total) * 100)
    Write-ProgressBar -Percent $percent -Activity "Generating" -Status "Symbol: $($symbol.Name)"
    
    $success = Generate-SlotSymbol -Symbol $symbol -OutputDir $slotOutputDir
    if ($success) {
        $script:Progress.Generated++
        Write-Host "`n  [OK] Symbol: $($symbol.Name)" -ForegroundColor Green
    } else {
        $script:Progress.Failed++
        Write-Host "`n  [FAIL] Symbol: $($symbol.Name)" -ForegroundColor Red
    }
}

Write-Host ""

# Generate slot machine panel
Write-Host "Generating slot machine panel..." -ForegroundColor Yellow
$success = Generate-SlotMachinePanel -OutputDir $slotOutputDir
if ($success) {
    $script:Progress.Generated++
    Write-Host "  [OK] Slot machine panel generated" -ForegroundColor Green
} else {
    $script:Progress.Failed++
    Write-Host "  [FAIL] Panel generation failed" -ForegroundColor Red
}
$script:Progress.Processed++

Write-Host ""

# Generate win/loss indicators
Write-Host "Generating win/loss indicators..." -ForegroundColor Yellow
$success = Generate-WinIndicator -OutputDir $slotOutputDir
if ($success) {
    $script:Progress.Generated++
    Write-Host "  [OK] Win/loss indicators generated" -ForegroundColor Green
} else {
    $script:Progress.Failed++
    Write-Host "  [FAIL] Indicator generation failed" -ForegroundColor Red
}
$script:Progress.Processed++

Write-Host "`n"
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Summary" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "Total Assets: $($script:Progress.Total)" -ForegroundColor White
Write-Host "Generated: $($script:Progress.Generated)" -ForegroundColor Green
Write-Host "Failed: $($script:Progress.Failed)" -ForegroundColor Red
Write-Host "Time: $((Get-Date) - $script:Progress.StartTime)" -ForegroundColor Gray
Write-Host ""
Write-Host "Assets saved to: Assets\Resources\SlotMachine\UI\" -ForegroundColor Cyan
Write-Host ""
Write-Host "Generated Files:" -ForegroundColor Yellow
Write-Host "  - slot_reel_frame.png (reel container)" -ForegroundColor Gray
Write-Host "  - slot_reel_background.png (reel background)" -ForegroundColor Gray
Write-Host "  - slot_symbol_*.png (10 magic-themed symbols)" -ForegroundColor Gray
Write-Host "  - slot_machine_panel.png (main UI panel)" -ForegroundColor Gray
Write-Host "  - slot_win_indicator.png (win effect)" -ForegroundColor Gray
Write-Host "  - slot_loss_indicator.png (loss indicator)" -ForegroundColor Gray
Write-Host ""


<#
.SYNOPSIS
    Generates spell assets for the game Elin using AI and procedural generation.
    AI-Assisted Modding Tools (AAMT) - Elin Toolset

.DESCRIPTION
    Creates Elin-compatible spell assets including:
    - Spell icons (32×32)
    - Spell effects/FX (32×32 or 64×64, multi-frame)
    - Spell projectiles (32×32, 1-4 frames)
    - Buff/Debuff icons (16×16)

# Load shared asset generation settings
$settingsPath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "..\\AssetGenerationSettings.ps1"
if (Test-Path $settingsPath) {
    . $settingsPath
}

.PARAMETER SpellDescription
    Description of the spell (e.g., "Nature Magic - Verdant Pulse: a burst of green life energy")

.PARAMETER SpellName
    Name of the spell (auto-generated if not provided)

.PARAMETER OutputDir
    Output directory for Elin assets

.PARAMETER GenerateIcon
    Generate spell icon (32×32)

.PARAMETER GenerateFX
    Generate spell effect animation (multi-frame)

.PARAMETER GenerateProjectile
    Generate projectile frames

.PARAMETER GenerateBuff
    Generate buff/debuff icon (16×16)

.PARAMETER GenerateAll
    Generate all asset types

.PARAMETER FXFrames
    Number of frames for FX animation (default: 4)

.PARAMETER ProjectileFrames
    Number of frames for projectile (default: 2)

.PARAMETER UseAI
    Use Ollama to generate asset specifications

.EXAMPLE
    .\ElinSpellAssetGenerator.ps1 -SpellDescription "Nature Magic - Verdant Pulse" -GenerateAll

.EXAMPLE
    .\ElinSpellAssetGenerator.ps1 -SpellDescription "Fireball spell" -GenerateIcon -GenerateFX -FXFrames 6
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)]
    [string]$SpellDescription,
    
    [string]$SpellName = "",
    
    [string]$OutputDir = "ElinAssets",
    
    [switch]$GenerateIcon,
    
    [switch]$GenerateFX,
    
    [switch]$GenerateProjectile,
    
    [switch]$GenerateBuff,
    
    [switch]$GenerateAll,
    
    [int]$FXFrames = 4,
    
    [int]$ProjectileFrames = 2,
    
    [switch]$UseAI,
    
    [string]$OllamaModel = "",

    # Optional Unity packaging via Shared/game_asset_kind.py
    [switch]$ExportUnity,
    [string]$ModPath = "",
    [string]$SystemName = "SpellMagic",
    [switch]$Mesh,
    [switch]$NoSd,
    [switch]$Defs,
    [string]$ElinRoot = "E:\SteamLibrary\steamapps\common\Elin"
)

$ErrorActionPreference = "Stop"

# Import unified tool detection and integration
$sharedPath = Join-Path (Split-Path $PSScriptRoot -Parent) "Shared"
Import-Module (Join-Path $sharedPath "ToolDetection.psm1") -ErrorAction SilentlyContinue
Import-Module (Join-Path $sharedPath "ToolsetIntegration.psm1") -ErrorAction SilentlyContinue
Import-Module (Join-Path $sharedPath "OllamaIntegration.psm1") -ErrorAction SilentlyContinue

# Initialize tools
$tools = Initialize-ToolsetTools `
    -RequiredTools @("Python") `
    -OptionalTools @("Ollama", "ImageMagick")

# Check required tools
if (-not $tools.AllRequiredAvailable) {
    Write-Host ""
    Write-Host "ERROR: Missing required tools for Elin spell asset generation" -ForegroundColor Red
    Show-ToolsetStatus -ToolsetName "Elin" `
        -RequiredTools @("Python") `
        -OptionalTools @("Ollama", "ImageMagick")
    exit 1
}

# Use Ollama if available and requested
if ($UseAI) {
    $ollamaAvailable = Use-OllamaIfAvailable
    if (-not $ollamaAvailable) {
        Write-Host "⚠ Warning: Ollama not available, but -UseAI was specified" -ForegroundColor Yellow
        Write-Host "  Continuing without AI features..." -ForegroundColor Gray
        $UseAI = $false
    }
}

# ============================================================
# CONFIGURATION
# ============================================================

$script:PythonScript = Join-Path $PSScriptRoot "elin_spell_assets.py"
if (-not $script:OllamaUrl) {
    $script:OllamaUrl = "http://localhost:11434"
    $script:OllamaApiUrl = "$script:OllamaUrl/api"
}

# Elin asset specifications
$script:ElinSpecs = @{
    IconSize = 32
    FXSize = 32  # Can be 64 for larger effects
    ProjectileSize = 32
    BuffSize = 16
    MaxPaletteColors = 4
    Style = "painterly, high-contrast, soft edges, readable at 1x scale"
}

# Note: Model selection uses Shared OllamaIntegration.psm1 tier system
# The shared module automatically:
# - Routes visual tasks to "visual" tier (llama3.1:8b by default)
# - Detects dark tone content via Test-DarkTone and routes to "dark_tone" tier
# - Escalates to "escalation" tier if models refuse
# No custom model selection needed - use Invoke-OllamaRequest with TaskType="visual"

# ============================================================
# HELPER FUNCTIONS
# ============================================================

function Invoke-OllamaChat {
    param(
        [string]$Prompt,
        [string]$ModelName
    )
    
    # Use Shared OllamaIntegration module - automatically handles dark tone detection and tier routing
    if (Get-Command Invoke-OllamaRequest -ErrorAction SilentlyContinue) {
        $systemPrompt = "You are a game asset designer specializing in spell icons and effects. Generate JSON specifications for game assets."
        # AutoEscalate enables automatic dark tone detection and tier routing
        return Invoke-OllamaRequest -Prompt $Prompt -TaskType "visual" -SystemPrompt $systemPrompt -ModelName $ModelName -UseChatAPI -AutoEscalate
    }
    
    # Fallback implementation (should not be needed if Shared module is loaded)
    if ([string]::IsNullOrWhiteSpace($ModelName)) {
        $ModelName = "llama3.1:8b"  # Default fallback
    }
    
    $requestBody = @{
        model = $ModelName
        messages = @(
            @{
                role = "system"
                content = "You are a game asset designer specializing in spell icons and effects. Generate JSON specifications for game assets."
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
        Write-Host "  Error calling Ollama: $_" -ForegroundColor Yellow
    }
    
    return $null
}

function Generate-SpellSpec {
    param(
        [string]$Description,
        [string]$ModelName
    )
    
    Write-Host "Generating spell asset specification..." -ForegroundColor Cyan
    
    $prompt = @"
Generate a JSON specification for Elin spell assets based on this description:

$Description

Requirements:
- Icon: 32×32, single frame, high readability, painterly style
- FX: 32×32 or 64×64, 2-6 frames, horizontal strip, expanding/motion effect
- Projectile: 32×32, 1-4 frames, directional variant
- Buff: 16×16, simplified version of icon

Output JSON with this structure:
{
  "spellName": "spell name",
  "icon": {
    "shape": "description",
    "colors": ["#hex1", "#hex2", "#hex3"],
    "contrast": "high",
    "lighting": "soft rim light"
  },
  "fx": {
    "frames": 4,
    "motion": "expanding pulse",
    "colors": ["#hex1", "#hex2"],
    "glow": true,
    "size": 32
  },
  "projectile": {
    "shape": "description",
    "frames": 2,
    "colors": ["#hex1", "#hex2"]
  },
  "buff": {
    "colors": ["#hex1", "#hex2"],
    "simplified": true
  }
}

Output ONLY valid JSON, no explanations, no markdown.
"@
    
    # Use Shared OllamaIntegration - automatically handles dark tone detection and tier routing
    $result = Invoke-OllamaChat -Prompt $prompt -ModelName $ModelName
    
    if ($result) {
        # Extract JSON from response
        $jsonMatch = $result -match '\{[\s\S]*\}'
        if ($jsonMatch) {
            try {
                $spec = $matches[0] | ConvertFrom-Json
                return $spec
            }
            catch {
                Write-Host "  Warning: Could not parse JSON, using defaults" -ForegroundColor Yellow
            }
        }
    }
    
    # Return default spec
    return @{
        spellName = if ([string]::IsNullOrWhiteSpace($SpellName)) { ($SpellDescription -split '-')[0].Trim() } else { $SpellName }
        icon = @{
            shape = "magical symbol"
            colors = @("#4caf50", "#81c784", "#2e7d32")
            contrast = "high"
            lighting = "soft rim light"
        }
        fx = @{
            frames = $FXFrames
            motion = "expanding pulse"
            colors = @("#66bb6a", "#a5d6a7")
            glow = $true
            size = 32
        }
        projectile = @{
            shape = "energy shard"
            frames = $ProjectileFrames
            colors = @("#4caf50", "#81c784")
        }
        buff = @{
            colors = @("#4caf50", "#81c784")
            simplified = $true
        }
    }
}

function Find-Blender {
    $blender = Get-Command "blender" -ErrorAction SilentlyContinue
    if ($blender) {
        return $blender.Source
    }
    
    $commonPaths = @(
        "D:\tools\Blender Foundation\Blender 5.0\blender.exe",
        "${env:ProgramFiles}\Blender Foundation\Blender *\blender.exe"
    )
    
    foreach ($pathPattern in $commonPaths) {
        $parent = Split-Path $pathPattern -Parent
        if (Test-Path $parent) {
            $matches = Get-ChildItem -Path $parent -Filter (Split-Path $pathPattern -Leaf) -ErrorAction SilentlyContinue
            if ($matches) {
                return $matches[0].FullName
            }
        }
    }
    
    return $null
}

# ============================================================
# MAIN EXECUTION
# ============================================================

Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Elin Spell Asset Generator" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "Spell: $SpellDescription" -ForegroundColor Gray
Write-Host ""

# Determine what to generate
if ($GenerateAll) {
    $GenerateIcon = $true
    $GenerateFX = $true
    $GenerateProjectile = $true
    $GenerateBuff = $true
}

if (-not ($GenerateIcon -or $GenerateFX -or $GenerateProjectile -or $GenerateBuff)) {
    Write-Host "Error: No asset types selected. Use -GenerateAll or specify types." -ForegroundColor Red
    exit 1
}

# Generate spell specification
$spellSpec = if ($UseAI) {
    Generate-SpellSpec -Description $SpellDescription -ModelName $OllamaModel
} else {
    # Use simple defaults
    @{
        spellName = if ([string]::IsNullOrWhiteSpace($SpellName)) { ($SpellDescription -replace '[^\w\s]', '' -replace '\s+', '_').Substring(0, [Math]::Min(30, $SpellDescription.Length)) } else { $SpellName }
        icon = @{
            shape = "magical symbol"
            colors = @("#4caf50", "#81c784")
            contrast = "high"
        }
        fx = @{
            frames = $FXFrames
            motion = "expanding"
            colors = @("#66bb6a", "#a5d6a7")
        }
        projectile = @{
            frames = $ProjectileFrames
            colors = @("#4caf50", "#81c784")
        }
        buff = @{
            colors = @("#4caf50", "#81c784")
        }
    }
}

$spellName = $spellSpec.spellName
$safeName = ($spellName -replace '[^\w\s]', '' -replace '\s+', '_').ToLower()

Write-Host "Spell Name: $spellName" -ForegroundColor Green
Write-Host ""

# Create output structure
$OutputDir = [System.IO.Path]::GetFullPath($OutputDir)
$iconDir = Join-Path $OutputDir "icons"
$fxDir = Join-Path $OutputDir "fx"
$projectileDir = Join-Path $OutputDir "projectiles"
$buffDir = Join-Path $OutputDir "buffs"

foreach ($dir in @($OutputDir, $iconDir, $fxDir, $projectileDir, $buffDir)) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
}

# Check Python
$pythonCmd = Get-Command "python" -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    $pythonCmd = Get-Command "python3" -ErrorAction SilentlyContinue
}
if (-not $pythonCmd) {
    Write-Host "Error: Python not found" -ForegroundColor Red
    exit 1
}

# Check Python script
if (-not (Test-Path $script:PythonScript)) {
    Write-Host "Error: Python script not found: $script:PythonScript" -ForegroundColor Red
    exit 1
}

# Generate assets
Write-Host "Generating Elin spell assets..." -ForegroundColor Cyan
Write-Host ""

# Save spec to JSON for Python script
$specPath = Join-Path $env:TEMP "elin_spell_spec_$(Get-Random).json"
$json = $spellSpec | ConvertTo-Json -Depth 10
[System.IO.File]::WriteAllText($specPath, $json, (New-Object System.Text.UTF8Encoding $false))

# Build Python command arguments
$pythonArgs = @(
    $script:PythonScript,
    "--spec", $specPath,
    "--output", $OutputDir,
    "--name", $safeName
)

if ($GenerateIcon) { $pythonArgs += "--icon" }
if ($GenerateFX) { 
    $pythonArgs += "--fx"
    $pythonArgs += "--fx-frames"
    $pythonArgs += $FXFrames.ToString()
}
if ($GenerateProjectile) { 
    $pythonArgs += "--projectile"
    $pythonArgs += "--proj-frames"
    $pythonArgs += $ProjectileFrames.ToString()
}
if ($GenerateBuff) { $pythonArgs += "--buff" }

try {
    # Use & operator to invoke Python directly (better argument handling)
    Write-Host "Running: $($pythonCmd.Source) $($pythonArgs -join ' ')" -ForegroundColor Gray
    & $pythonCmd.Source $pythonArgs
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
        Write-Host "  Complete" -ForegroundColor Cyan
        Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
        Write-Host ""
        
        # List generated files
        $allFiles = Get-CachedChildItem -LiteralPath $OutputDir -Recurse -File | Sort-Object FullName
        if ($allFiles.Count -gt 0) {
            Write-Host "Generated assets:" -ForegroundColor Green
            foreach ($file in $allFiles) {
                $size = [math]::Round($file.Length / 1KB, 2)
                $relativePath = $file.FullName.Replace($OutputDir, '').TrimStart('\', '/')
                Write-Host "  - $relativePath ($size KB)" -ForegroundColor Gray
            }
        }
        
        Write-Host ""
        Write-Host "Assets ready for Elin:" -ForegroundColor Yellow
        Write-Host "  Output directory: $OutputDir" -ForegroundColor White

        if ($Defs -and -not $ExportUnity) {
            $defsPy = Join-Path $sharedPath "game_asset_defs.py"
            Write-Host ""
            Write-Host "Writing Elin ability def (*_elin_ability.json)..." -ForegroundColor Cyan
            & $pythonCmd.Source @(
                $defsPy,
                "--elin-ability-from-folder",
                "--out-dir", $OutputDir,
                "--name", $safeName,
                "--theme", $SpellDescription,
                "--system", "Elin"
            )
            if ($LASTEXITCODE -ne 0) {
                Write-Warning "Elin ability def write exited $LASTEXITCODE"
            }
        }

        if ($ExportUnity) {
            if (-not $ModPath) {
                Write-Warning "ExportUnity requested but -ModPath missing; skipping Unity layout"
            } else {
                $sharedGen = Join-Path $sharedPath "GenerateGameAsset.ps1"
                if (-not (Test-Path $sharedGen)) {
                    Write-Warning "Shared GenerateGameAsset.ps1 not found: $sharedGen"
                } else {
                    Write-Host ""
                    Write-Host "Exporting Unity spell pack (Shared game_asset_kind)..." -ForegroundColor Cyan
                    $unityArgs = @{
                        Kind = "spell"
                        Theme = $SpellDescription
                        Name = $safeName
                        ModPath = $ModPath
                        SystemName = $SystemName
                        NoOllama = $(-not $UseAI)
                        FxFrames = $FXFrames
                        ProjFrames = $ProjectileFrames
                        ElinRoot = $ElinRoot
                    }
                    if ($Mesh) { $unityArgs.Mesh = $true }
                    if ($NoSd) { $unityArgs.NoSd = $true }
                    if ($Defs) { $unityArgs.Defs = $true }
                    & $sharedGen @unityArgs
                    if ($LASTEXITCODE -ne 0) {
                        Write-Warning "Unity spell export exited $LASTEXITCODE"
                    }
                }
            }
        }

        if ($Defs) {
            $deploy = Join-Path $PSScriptRoot "Deploy-AamtElinAbility.ps1"
            $deploySrc = $OutputDir
            if ($ExportUnity -and $ModPath) {
                $nested = Join-Path $ModPath "Assets\Resources\$SystemName\Spells\$safeName"
                if (Test-Path $nested) { $deploySrc = $nested }
            }
            if (Test-Path $deploy) {
                Write-Host ""
                Write-Host "Deploying ability def + icon to BepInEx injector..." -ForegroundColor Cyan
                & $deploy -SourceDir $deploySrc -ElinRoot $ElinRoot
            } else {
                Write-Warning "Deploy script missing: $deploy"
            }
        }
    } else {
        Write-Host "Error: Asset generation failed (exit code: $LASTEXITCODE)" -ForegroundColor Red
        exit 1
    }
}
catch {
    Write-Host "Error: $_" -ForegroundColor Red
    exit 1
}
finally {
    # Clean up temp spec file
    if (Test-Path $specPath) {
        Remove-Item $specPath -ErrorAction SilentlyContinue
    }
}


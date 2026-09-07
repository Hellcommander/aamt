<#
.SYNOPSIS
    AI-powered asset maker and tweaker for Transcendence mods using Ollama.

.DESCRIPTION
    This tool uses local AI models via Ollama to assist with mod asset creation:
    - Generate ship/item names and descriptions
    - Create XML configurations
    - Optimize asset metadata
    - Generate credits and documentation

# AI-Assisted Modding Tools (AAMT) - Transcendence Toolset

# Load shared asset generation settings
$settingsPath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "..\\AssetGenerationSettings.ps1"
if (Test-Path $settingsPath) {
    . $settingsPath
}

# Import unified tool detection and integration
$sharedPath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "..\Shared"
Import-Module (Join-Path $sharedPath "ToolDetection.psm1") -ErrorAction SilentlyContinue
Import-Module (Join-Path $sharedPath "ToolsetIntegration.psm1") -ErrorAction SilentlyContinue

# Initialize tools for AssetMakerAI
$tools = Initialize-ToolsetTools `
    -RequiredTools @("Ollama") `
    -OptionalTools @("ImageMagick", "Blender", "Python", "StableDiffusion")

# Check required tools
if (-not $tools.AllRequiredAvailable) {
    Write-Host "`nERROR: Missing required tools for AssetMakerAI" -ForegroundColor Red
    Show-ToolsetStatus -ToolsetName "Transcendence - AssetMakerAI" `
        -RequiredTools @("Ollama") `
        -OptionalTools @("ImageMagick", "Blender", "Python", "StableDiffusion")
    exit 1
}

# Use Ollama integration
Use-OllamaIfAvailable | Out-Null
    - Suggest improvements for assets

.PARAMETER OllamaPath
    Path to Ollama executable (auto-detected if not provided)

.PARAMETER Model
    Ollama model to use (default: llama3.2 or available model)

.PARAMETER Action
    Action to perform: GenerateName, GenerateDescription, CreateXML, OptimizeAsset, GenerateCredits, SuggestImprovements

.PARAMETER AssetType
    Type of asset: Ship, Item, Weapon, Station, etc.

.PARAMETER InputData
    Input data for AI processing (file path, text, or JSON)

.PARAMETER OutputPath
    Output directory for generated files

.PARAMETER InstallOllama
    Automatically download and install Ollama if not found

.EXAMPLE
    .\AssetMakerAI.ps1 -Action GenerateName -AssetType Ship -InputData "A fast scout ship"

.EXAMPLE
    .\AssetMakerAI.ps1 -Action CreateXML -AssetType Item -InputData "item_description.json"

.EXAMPLE
    .\AssetMakerAI.ps1 -Action OptimizeAsset -InputData "MyMod\Assets\ship.png"
#>

[CmdletBinding()]
param(
    [string]$OllamaPath = "",
    
    [string]$Model = "",
    
    [ValidateSet("GenerateName", "GenerateDescription", "CreateXML", "OptimizeAsset", "GenerateCredits", "SuggestImprovements", "BatchProcess", "Generate3DModel", "GenerateTexture", "AssembleSpritesheet", "BatchTextures")]
    [string]$Action = "GenerateName",
    
    [ValidateSet("Ship", "Item", "Weapon", "Station", "Projectile", "Effect", "Other")]
    [string]$AssetType = "Ship",
    
    [string]$InputData = "",
    
    [string]$OutputPath = "",
    
    [switch]$InstallOllama,
    
    [switch]$ListModels,
    
    [switch]$CheckOllama,
    
    [string]$BlenderPath = "",
    
    [ValidateSet("OBJ", "FBX", "GLB", "GLTF", "STL", "PLY")]
    [string]$ModelFormat = "OBJ",
    
    [ValidateSet("LowPoly", "Medium", "HighDetail", "Procedural")]
    [string]$DetailLevel = "Medium",
    
    [ValidateSet("Procedural", "Diffusion", "Hybrid")]
    [string]$TextureMethod = "Diffusion",
    
    [int]$TextureSize = 256,
    
    [int]$TileSize = 128,
    
    [int]$SpritesheetColumns = 8,
    
    [string]$SpritesheetPath = "",
    
    [Parameter(Mandatory=$false)]
    [switch]$LaunchControlRoom,
    
    [Parameter(Mandatory=$false)]
    [string]$ControlRoomWatchDir = ""
)

$ErrorActionPreference = "Stop"

# ============================================================
# CONFIGURATION
# ============================================================

$script:OllamaUrl = "http://localhost:11434"
$script:OllamaApiUrl = "$script:OllamaUrl/api"
$script:OllamaDownloadUrl = "https://github.com/ollama/ollama/releases/latest/download/OllamaSetup.exe"
$script:OllamaDefaultPath = "${env:LOCALAPPDATA}\Programs\Ollama\ollama.exe"
$script:DefaultModel = "llama3.2"  # Good balance of quality and speed
$script:SdkPath = Join-Path $PSScriptRoot "SDK"

# ============================================================
# OLLAMA DETECTION & MANAGEMENT
# ============================================================

function Find-Ollama {
    <#
    .SYNOPSIS
      Finds Ollama installation using unified tool detection with fallback to manual detection
    #>
    Write-Host "Detecting Ollama installation..." -ForegroundColor Cyan
    
    # 1. Check if path was provided by user (highest priority)
    if (-not [string]::IsNullOrWhiteSpace($OllamaPath)) {
        $providedPath = $OllamaPath.Trim()
        
        if (Test-Path $providedPath -PathType Leaf) {
            Write-Host "  Found via provided path: $providedPath" -ForegroundColor Green
            return $providedPath
        } elseif (Test-Path $providedPath -PathType Container) {
            $ollamaExe = Join-Path $providedPath "ollama.exe"
            if (Test-Path $ollamaExe) {
                Write-Host "  Found via provided path: $ollamaExe" -ForegroundColor Green
                return $ollamaExe
            }
        }
    }
    
    # 2. Use unified tool detection (if available)
    if (Get-Command Get-ToolInfo -ErrorAction SilentlyContinue) {
        $ollamaInfo = Get-ToolInfo -ToolName "Ollama"
        if ($ollamaInfo.Available -and $ollamaInfo.Path) {
            Write-Host "  Found via unified detection: $($ollamaInfo.Path)" -ForegroundColor Green
            return $ollamaInfo.Path
        }
    }
    
    # 3. Fallback: Check PATH (command lookup)
    $ollama = Get-Command "ollama" -ErrorAction SilentlyContinue
    if ($ollama) {
        Write-Host "  Found via PATH: $($ollama.Source)" -ForegroundColor Green
        return $ollama.Source
    }
    
    # 4. Check Windows Registry (Uninstall keys)
    try {
        $registryKeys = @(
            "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*",
            "HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*"
        )
        
        foreach ($regPath in $registryKeys) {
            $installed = Get-ItemProperty $regPath -ErrorAction SilentlyContinue | 
                Where-Object { $_.DisplayName -like "*Ollama*" -and -not [string]::IsNullOrWhiteSpace($_.InstallLocation) }
            
            if ($installed) {
                foreach ($install in $installed) {
                    $installPath = $install.InstallLocation.Trim()
                    if (-not [string]::IsNullOrWhiteSpace($installPath) -and (Test-Path $installPath)) {
                        $ollamaExe = Join-Path $installPath "ollama.exe"
                        if (Test-Path $ollamaExe) {
                            Write-Host "  Found via registry: $ollamaExe" -ForegroundColor Green
                            return $ollamaExe
                        }
                    }
                }
            }
        }
    }
    catch {
        Write-Host "  Registry check failed: $_" -ForegroundColor Yellow
    }
    
    # 5. Check common installation paths
    $commonPaths = @(
        "${env:LOCALAPPDATA}\Programs\Ollama",
        "${env:ProgramFiles}\Ollama",
        "${env:ProgramFiles(x86)}\Ollama",
        "C:\Program Files\Ollama",
        "C:\Program Files (x86)\Ollama"
    )
    
    foreach ($basePath in $commonPaths) {
        if (Test-Path $basePath) {
            $ollamaExe = Join-Path $basePath "ollama.exe"
            if (Test-Path $ollamaExe) {
                Write-Host "  Found via common path: $ollamaExe" -ForegroundColor Green
                return $ollamaExe
            }
        }
    }
    
    Write-Host "  Ollama not found automatically" -ForegroundColor Yellow
    return $null
}

function Test-OllamaRunning {
    <#
    .SYNOPSIS
      Checks if Ollama service is running
    #>
    try {
        $response = Invoke-RestMethod -Uri "$script:OllamaApiUrl/tags" -Method Get -TimeoutSec 2 -ErrorAction Stop
        return $true
    }
    catch {
        return $false
    }
}

function Start-OllamaService {
    <#
    .SYNOPSIS
      Starts Ollama service
    #>
    param([string]$OllamaExePath)
    
    if ([string]::IsNullOrWhiteSpace($OllamaExePath) -or -not (Test-Path $OllamaExePath)) {
        Write-Host "Error: Ollama executable not found" -ForegroundColor Red
        return $false
    }
    
    Write-Host "Starting Ollama service..." -ForegroundColor Cyan
    
    try {
        # Check if already running
        if (Test-OllamaRunning) {
            Write-Host "  Ollama service is already running" -ForegroundColor Green
            return $true
        }
        
        # Start Ollama in background
        Start-Process -FilePath $OllamaExePath -WindowStyle Hidden -ErrorAction Stop
        
        # Wait for service to start (max 30 seconds)
        $maxWait = 30
        $waited = 0
        while (-not (Test-OllamaRunning) -and $waited -lt $maxWait) {
            Start-Sleep -Seconds 1
            $waited++
            Write-Host "  Waiting for Ollama to start... ($waited/$maxWait)" -ForegroundColor Gray
        }
        
        if (Test-OllamaRunning) {
            Write-Host "  ✓ Ollama service started" -ForegroundColor Green
            return $true
        } else {
            Write-Host "  ✗ Ollama service failed to start within $maxWait seconds" -ForegroundColor Red
            return $false
        }
    }
    catch {
        Write-Host "  ✗ Error starting Ollama: $_" -ForegroundColor Red
        return $false
    }
}

function Get-AvailableModels {
    <#
    .SYNOPSIS
      Gets list of available Ollama models
    #>
    try {
        $response = Invoke-RestMethod -Uri "$script:OllamaApiUrl/tags" -Method Get -TimeoutSec 5
        $models = $response.models | ForEach-Object { $_.name }
        return $models
    }
    catch {
        Write-Host "  Error getting models: $_" -ForegroundColor Red
        return @()
    }
}

function Get-RecommendedModel {
    <#
    .SYNOPSIS
      Gets recommended model based on available models
    #>
    $available = Get-AvailableModels
    
    if ($available.Count -eq 0) {
        Write-Host "  No models available. Install one with: ollama pull llama3.2" -ForegroundColor Yellow
        return $script:DefaultModel
    }
    
    # Prefer models in this order (check for exact matches and versions)
    $preferred = @("llama3.2", "llama3.1", "llama3", "mistral", "phi3", "gemma2", "wizardlm")
    
    foreach ($pref in $preferred) {
        $match = $available | Where-Object { $_ -like "$pref*" }
        if ($match) {
            return $match[0]
        }
    }
    
    # Return first available model
    Write-Host "  Using available model: $($available[0])" -ForegroundColor Gray
    return $available[0]
}

function Invoke-OllamaChat {
    <#
    .SYNOPSIS
      Sends a chat request to Ollama and returns the response
    #>
    param(
        [string]$Prompt,
        [string]$ModelName,
        [hashtable]$SystemPrompt = @{}
    )
    
    if (-not (Test-OllamaRunning)) {
        Write-Host "Error: Ollama service is not running" -ForegroundColor Red
        Write-Host "  Start Ollama service or run: ollama serve" -ForegroundColor Yellow
        return $null
    }
    
    $systemMessage = if ($SystemPrompt.Count -gt 0) {
        $SystemPrompt.Values | Select-Object -First 1
    } else {
        "You are a helpful assistant for creating game mod assets. Provide concise, practical responses."
    }
    
    $requestBody = @{
        model = $ModelName
        messages = @(
            @{
                role = "system"
                content = $systemMessage
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
        } else {
            Write-Host "  Warning: Unexpected response format" -ForegroundColor Yellow
            return $null
        }
    }
    catch {
        Write-Host "  Error calling Ollama API: $_" -ForegroundColor Red
        if ($_.Exception.Response.StatusCode -eq 404) {
            Write-Host "  Model '$ModelName' may not be installed. Run: ollama pull $ModelName" -ForegroundColor Yellow
        }
        return $null
    }
}

# ============================================================
# ASSET GENERATION FUNCTIONS
# ============================================================

function Generate-AssetName {
    <#
    .SYNOPSIS
      Generates a name for a game asset using AI
    #>
    param(
        [string]$AssetType,
        [string]$Description,
        [string]$ModelName
    )
    
    $systemPrompt = "You are a creative game asset namer. Generate concise, thematic names for game assets that fit the Transcendence universe. Return only the name, no explanation."
    
    $prompt = "Generate a name for a $AssetType in the Transcendence space game. Description: $Description. The name should be 1-3 words, thematic, and fit the game's style."
    
    Write-Host "Generating name for $AssetType..." -ForegroundColor Cyan
    $result = Invoke-OllamaChat -Prompt $prompt -ModelName $ModelName -SystemPrompt @{ System = $systemPrompt }
    
    if ($result) {
        # Clean up the response (remove quotes, extra text)
        $name = $result -replace '^["'']+|["'']+$', '' -replace '^Name:\s*', '' -replace '\s*\(.*?\)\s*$', ''
        $name = $name.Trim()
        Write-Host "  Generated name: $name" -ForegroundColor Green
        return $name
    }
    
    return $null
}

function Generate-AssetDescription {
    <#
    .SYNOPSIS
      Generates a description for a game asset using AI
    #>
    param(
        [string]$AssetType,
        [string]$AssetName,
        [string]$ModelName
    )
    
    $systemPrompt = "You are a game writer creating descriptions for space game assets. Write concise, engaging descriptions that fit the Transcendence universe style."
    
    $prompt = "Write a brief description (2-3 sentences) for a $AssetType named '$AssetName' in the Transcendence space game. Make it engaging and fit the game's lore."
    
    Write-Host "Generating description for $AssetName..." -ForegroundColor Cyan
    $result = Invoke-OllamaChat -Prompt $prompt -ModelName $ModelName -SystemPrompt @{ System = $systemPrompt }
    
    if ($result) {
        Write-Host "  Generated description" -ForegroundColor Green
        return $result
    }
    
    return $null
}

function Get-CodeModel {
    <#
    .SYNOPSIS
      Gets the code model (CodeLlama-34B) from dual-model router for code/XML tasks
    #>
    try {
        $routerScript = Join-Path (Join-Path $PSScriptRoot "..") "Common\ollama_model_router.py"
        if (Test-Path $routerScript) {
            $result = python $routerScript -c "from ollama_model_router import get_code_model; print(get_code_model())" 2>$null
            if ($result -and $result.Trim()) {
                return $result.Trim()
            }
        }
    } catch {
        # Fallback if router not available
    }
    
    # Fallback: try to detect CodeLlama-34B directly
    $available = Get-AvailableModels
    $codellama34 = $available | Where-Object { $_ -like "*codellama*34*" -or $_ -like "*codellama:34*" } | Select-Object -First 1
    if ($codellama34) {
        return $codellama34
    }
    
    # Final fallback
    return Get-RecommendedModel
}

function Generate-AssetXML {
    <#
    .SYNOPSIS
      Generates XML configuration for a game asset using AI (uses CodeLlama-34B via dual-model router)
    #>
    param(
        [string]$AssetType,
        [string]$AssetName,
        [string]$Description,
        [string]$ModelName,
        [hashtable]$AdditionalData = @{}
    )
    
    # Use code model (CodeLlama-34B) for XML generation if model not specified
    if ([string]::IsNullOrWhiteSpace($ModelName)) {
        $ModelName = Get-CodeModel
        Write-Host "  Using code model for XML generation: $ModelName" -ForegroundColor Gray
    }
    
    $systemPrompt = "You are an expert in Transcendence mod XML syntax. Generate valid XML code for game assets following the Transcendence API 57+ format."
    
    $dataJson = $AdditionalData | ConvertTo-Json -Compress
    $prompt = @"
Generate XML code for a $AssetType in Transcendence game (API 57+).

Asset Name: $AssetName
Description: $Description
Additional Data: $dataJson

Requirements:
- Use proper XML syntax with DOCTYPE if needed
- Include appropriate UNID (use placeholder like 0xDD000001)
- Follow Transcendence XML structure for $AssetType
- Include name, description, and basic attributes
- Use proper entity references if needed

Return only the XML code, no explanations.
"@
    
    Write-Host "Generating XML for $AssetName..." -ForegroundColor Cyan
    $result = Invoke-OllamaChat -Prompt $prompt -ModelName $ModelName -SystemPrompt @{ System = $systemPrompt }
    
    if ($result) {
        # Extract XML from code blocks if present
        if ($result -match '```xml\s*(.*?)\s*```' -or $result -match '```\s*(.*?)\s*```') {
            $result = $matches[1]
        }
        
        Write-Host "  Generated XML" -ForegroundColor Green
        return $result.Trim()
    }
    
    return $null
}

function Optimize-AssetMetadata {
    <#
    .SYNOPSIS
      Optimizes asset metadata using AI suggestions
    #>
    param(
        [string]$InputFile,
        [string]$ModelName
    )
    
    if (-not (Test-Path $InputFile)) {
        Write-Host "Error: Input file not found: $InputFile" -ForegroundColor Red
        return $null
    }
    
    $content = Get-Content $InputFile -Raw
    
    $systemPrompt = "You are an expert in game asset optimization. Provide suggestions to improve asset metadata, naming, and organization."
    
    $prompt = @"
Review and optimize this game asset metadata:

$content

Provide:
1. Improved naming suggestions
2. Better descriptions
3. Organization improvements
4. Any issues or inconsistencies

Format as a structured list.
"@
    
    Write-Host "Optimizing asset metadata..." -ForegroundColor Cyan
    $result = Invoke-OllamaChat -Prompt $prompt -ModelName $ModelName -SystemPrompt @{ System = $systemPrompt }
    
    if ($result) {
        Write-Host "  Generated optimization suggestions" -ForegroundColor Green
        return $result
    }
    
    return $null
}

function Generate-CreditsText {
    <#
    .SYNOPSIS
      Generates credits text for mod assets
    #>
    param(
        [string]$ModName,
        [string[]]$AssetNames,
        [string]$ModelName
    )
    
    $assetsList = $AssetNames -join ", "
    
    $systemPrompt = "You are a professional credits writer. Create clear, professional credits text for game mods."
    
    $prompt = @"
Generate credits text for a Transcendence mod named '$ModName'.

Assets included: $assetsList

Create a professional credits section that:
- Thanks contributors
- Lists asset sources
- Includes proper attribution
- Follows modding community standards

Format as plain text, ready to include in a mod README or credits file.
"@
    
    Write-Host "Generating credits text..." -ForegroundColor Cyan
    $result = Invoke-OllamaChat -Prompt $prompt -ModelName $ModelName -SystemPrompt @{ System = $systemPrompt }
    
    if ($result) {
        Write-Host "  Generated credits text" -ForegroundColor Green
        return $result
    }
    
    return $null
}

function Find-Blender {
    <#
    .SYNOPSIS
      Finds Blender installation (simplified version)
    #>
    if (-not [string]::IsNullOrWhiteSpace($BlenderPath) -and (Test-Path $BlenderPath)) {
        return $BlenderPath
    }
    
    # Check command
    $blender = Get-Command "blender" -ErrorAction SilentlyContinue
    if ($blender) {
        return $blender.Source
    }
    
    # Check common paths
    $commonPaths = @(
        "D:\tools\Blender Foundation\Blender 5.0\blender.exe",
        "${env:ProgramFiles}\Blender Foundation\Blender *\blender.exe",
        "${env:ProgramFiles(x86)}\Blender Foundation\Blender *\blender.exe"
    )
    
    foreach ($pathPattern in $commonPaths) {
        $matches = Get-ChildItem -Path (Split-Path $pathPattern -Parent) -Filter (Split-Path $pathPattern -Leaf) -ErrorAction SilentlyContinue
        if ($matches) {
            return $matches[0].FullName
        }
    }
    
    return $null
}

function Generate-BlenderPythonCode {
    <#
    .SYNOPSIS
      Generates Blender Python code from a description using Ollama
    #>
    param(
        [string]$Description,
        [string]$OutputPath,
        [string]$ModelFormat,
        [string]$DetailLevel,
        [string]$ModelName
    )
    
    $formatLower = $ModelFormat.ToLower()
    $detailInstructions = switch ($DetailLevel) {
        "LowPoly" { "Use low-poly geometry with minimal vertices. Keep it simple and game-ready." }
        "Medium" { "Use moderate detail with smooth surfaces. Balance between quality and performance." }
        "HighDetail" { "Use high-detail geometry with fine features. Suitable for close-up renders." }
        "Procedural" { "Use procedural generation techniques with modifiers and nodes." }
    }
    
    $systemPrompt = "You are a Blender Python scripting expert. Generate only valid Python code using bpy (Blender Python API). Use correct API methods. Do not include explanations, comments, or markdown code blocks. Output pure Python code only."
    
    $prompt = @"
Generate Blender Python code that creates a 3D model based on this description:

$Description

CRITICAL: Use ONLY valid Blender Python API methods. Common mistakes to avoid:
- DO NOT use bpy.context.scene.objects.remove() - it doesn't exist
- DO NOT use bpy.ops.mesh.delete() - delete objects, not meshes
- DO NOT use bpy.context.scene.origin or bpy.context.scene.scale_all - these don't exist
- DO use bpy.ops.object.select_all() and bpy.ops.object.delete() to clear scene
- DO use bpy.ops.mesh.primitive_*_add() for basic shapes
- DO use bmesh for complex mesh operations

Requirements:
- Use only bpy and bmesh (Blender Python API, no external addons)
- Create a single mesh object
- Export the model to: '$OutputPath' (use raw string: r'$OutputPath')
- Export format: $ModelFormat ($formatLower)
- Detail level: $detailInstructions
- Delete ALL default objects first: bpy.ops.object.select_all(action='SELECT') then bpy.ops.object.delete(use_global=False)
- Use proper bpy.ops for export (Blender 5.0+ API):
  * OBJ: bpy.ops.wm.obj_export(filepath=r'$OutputPath')
  * FBX: bpy.ops.export_scene.fbx(filepath=r'$OutputPath')
  * GLB: bpy.ops.export_scene.gltf(filepath=r'$OutputPath', export_format='GLB')
  * GLTF: bpy.ops.export_scene.gltf(filepath=r'$OutputPath', export_format='GLTF_SEPARATE')
  * STL: bpy.ops.export_mesh.stl(filepath=r'$OutputPath')
- Position model at origin (0,0,0) - set location after creation
- Scale appropriately (typical game asset: 1-5 Blender units)

CORRECT Example for a simple cube with rounded edges:
import bpy

# Clear default scene
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# Create cube (primitive_*_add does NOT accept bevel parameters)
bpy.ops.mesh.primitive_cube_add(size=2, location=(0, 0, 0))
obj = bpy.context.active_object
obj.name = "Model"

# Add bevel modifier AFTER creation (not as parameter to primitive_*_add)
bpy.ops.object.modifier_add(type='BEVEL')
obj.modifiers["Bevel"].width = 0.1
obj.modifiers["Bevel"].segments = 2
bpy.ops.object.modifier_apply(modifier="Bevel")

# Export (Blender 5.0+ uses wm.obj_export, not export_scene.obj)
bpy.ops.wm.obj_export(filepath=r'$OutputPath')

IMPORTANT: 
- primitive_*_add() only accepts: size, location, rotation, scale
- Modifiers must be added separately using bpy.ops.object.modifier_add()
- Always apply modifiers before export if you want them baked into the mesh

Output ONLY valid Python code, no explanations, no markdown, no code fences.
"@
    
    Write-Host "Generating Blender Python code..." -ForegroundColor Cyan
    $result = Invoke-OllamaChat -Prompt $prompt -ModelName $ModelName -SystemPrompt @{ System = $systemPrompt }
    
    if ($result) {
        # Clean up the response - remove markdown code blocks if present
        $code = $result
        
        # Remove ```python or ``` markers
        $code = $code -replace '```python\s*', '' -replace '```\s*', ''
        
        # Remove any leading/trailing whitespace
        $code = $code.Trim()
        
        Write-Host "  Generated Python code ($($code.Length) characters)" -ForegroundColor Green
        return $code
    }
    
    return $null
}

function Execute-BlenderPython {
    <#
    .SYNOPSIS
      Executes a Python script in Blender headless mode
    #>
    param(
        [string]$PythonScript,
        [string]$BlenderExePath
    )
    
    if (-not $BlenderExePath -or -not (Test-Path $BlenderExePath)) {
        Write-Host "Error: Blender executable not found" -ForegroundColor Red
        return $false
    }
    
    if (-not (Test-Path $PythonScript)) {
        Write-Host "Error: Python script not found: $PythonScript" -ForegroundColor Red
        return $false
    }
    
    Write-Host "Executing Blender Python script..." -ForegroundColor Cyan
    Write-Host "  Script: $PythonScript" -ForegroundColor Gray
    Write-Host "  Blender: $BlenderExePath" -ForegroundColor Gray
    
    try {
        # Determine if we need to use cmd.exe for .cmd files or run directly
        if ($BlenderExePath -match '\.cmd$') {
            # For .cmd files, we need to extract the actual blender.exe path
            # Or use cmd.exe to run it
            $blenderArgs = "/c `"$BlenderExePath`" --background --python `"$PythonScript`""
            $process = Start-Process -FilePath "cmd.exe" -ArgumentList $blenderArgs -Wait -NoNewWindow -PassThru
        } else {
            # For .exe files, run directly
            $blenderArgs = "--background --python `"$PythonScript`""
            $process = Start-Process -FilePath $BlenderExePath -ArgumentList $blenderArgs -Wait -NoNewWindow -PassThru
        }
        
        if ($process.ExitCode -eq 0) {
            Write-Host "  ✓ Blender execution completed successfully" -ForegroundColor Green
            return $true
        } else {
            Write-Host "  ✗ Blender execution failed (exit code: $($process.ExitCode))" -ForegroundColor Red
            return $false
        }
    }
    catch {
        Write-Host "  ✗ Error executing Blender: $_" -ForegroundColor Red
        return $false
    }
}

function Generate-3DModel {
    <#
    .SYNOPSIS
      Complete pipeline: Generate 3D model from description using Ollama + Blender
    #>
    param(
        [string]$Description,
        [string]$OutputPath,
        [string]$ModelFormat,
        [string]$DetailLevel,
        [string]$ModelName,
        [string]$BlenderExePath
    )
    
    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host "  Generating 3D Model from Description" -ForegroundColor Cyan
    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Description: $Description" -ForegroundColor Gray
    Write-Host "Format: $ModelFormat" -ForegroundColor Gray
    Write-Host "Detail: $DetailLevel" -ForegroundColor Gray
    Write-Host ""
    
    # Ensure output directory exists
    $outputDir = Split-Path $OutputPath -Parent
    if (-not [string]::IsNullOrWhiteSpace($outputDir) -and -not (Test-Path $outputDir)) {
        New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
    }
    
    # Generate Blender Python code using Ollama
    $pythonCode = Generate-BlenderPythonCode -Description $Description -OutputPath $OutputPath -ModelFormat $ModelFormat -DetailLevel $DetailLevel -ModelName $ModelName
    
    if (-not $pythonCode) {
        Write-Host "Error: Failed to generate Blender Python code" -ForegroundColor Red
        return $false
    }
    
    # Save Python code to temporary file
    $tempScript = Join-Path $env:TEMP "blender_gen_$(Get-Random).py"
    try {
        [System.IO.File]::WriteAllText($tempScript, $pythonCode, [System.Text.UTF8Encoding]::new($false))
        Write-Host "  Saved Python script: $tempScript" -ForegroundColor Gray
        Write-Host ""
        
        # Execute in Blender
        $success = Execute-BlenderPython -PythonScript $tempScript -BlenderExePath $BlenderExePath
        
        if ($success) {
            # Check if output file was created
            if (Test-Path $OutputPath) {
                $fileSize = (Get-Item $OutputPath).Length / 1KB
                Write-Host ""
                Write-Host "  ✓ Model generated successfully!" -ForegroundColor Green
                Write-Host "  Output: $OutputPath ($([math]::Round($fileSize, 2)) KB)" -ForegroundColor Green
                return $true
            } else {
                Write-Host ""
                Write-Host "  ⚠ Blender executed but output file not found: $OutputPath" -ForegroundColor Yellow
                Write-Host "  Check the Python script for export path issues" -ForegroundColor Yellow
                return $false
            }
        } else {
            return $false
        }
    }
    finally {
        # Optionally keep the script for debugging, or delete it
        # Remove-Item -LiteralPath $tempScript -Force -ErrorAction SilentlyContinue
        Write-Host "  Python script saved at: $tempScript (for debugging)" -ForegroundColor Gray
    }
}

function Generate-TextureProcedural {
    <#
    .SYNOPSIS
      Generates procedural texture using Blender texture baker (preferred) or Ollama-generated code
    #>
    param(
        [string]$Description,
        [string]$OutputPath,
        [int]$TextureSize,
        [string]$ModelName,
        [string]$BlenderExePath
    )
    
    Write-Host "Generating procedural texture..." -ForegroundColor Cyan
    Write-Host "  Description: $Description" -ForegroundColor Gray
    Write-Host "  Size: ${TextureSize}x${TextureSize}" -ForegroundColor Gray
    
    # Try to use the texture baker script first (more reliable)
    $bakerScript = Join-Path $PSScriptRoot "..\Common\bake_texture.py"
    
    if (Test-Path $bakerScript) {
        # Map description to material type or generate JSON
        $materialType = $null
        
        # Simple keyword matching for common materials
        $descLower = $Description.ToLower()
        if ($descLower -match 'wood|wooden|timber') {
            $materialType = "wood"
        } elseif ($descLower -match 'stone|rock|brick') {
            $materialType = "stone"
        } elseif ($descLower -match 'metal|iron|steel|rust') {
            $materialType = "metal"
        }
        
        if ($materialType) {
            Write-Host "  Using material type: $materialType" -ForegroundColor Gray
            
            # Use the texture baker
            $blenderArgs = "--background --python `"$bakerScript`" -- --material `"$materialType`" --size $TextureSize --output `"$OutputPath`" --pass DIFFUSE"
            
            try {
                if ($BlenderExePath -match '\.cmd$') {
                    $blenderArgs = "/c `"$BlenderExePath`" $blenderArgs"
                    $process = Start-Process -FilePath "cmd.exe" -ArgumentList $blenderArgs -Wait -NoNewWindow -PassThru
                } else {
                    $process = Start-Process -FilePath $BlenderExePath -ArgumentList $blenderArgs -Wait -NoNewWindow -PassThru
                }
                
                if ($process.ExitCode -eq 0 -and (Test-Path $OutputPath)) {
                    Write-Host "  ✓ Texture baked: $OutputPath" -ForegroundColor Green
                    return $true
                }
            }
            catch {
                Write-Host "  Warning: Texture baker failed, falling back to Ollama generation" -ForegroundColor Yellow
            }
        }
    }
    
    # Fallback: Generate Blender Python code using Ollama
    Write-Host "  Generating material code with Ollama..." -ForegroundColor Gray
    
    $systemPrompt = "You are a Blender Python scripting expert for procedural texture generation. Generate only valid Python code using bpy. Output pure Python code only."
    
    $prompt = @"
Generate Blender Python code that creates a procedural texture based on this description:

$Description

Requirements:
- Create a material with procedural nodes (use Shader Editor)
- Use Blender's built-in texture nodes (Noise, Voronoi, Wave, etc.)
- Bake the material to an image texture
- Export as PNG: '$OutputPath'
- Image size: ${TextureSize}x${TextureSize}
- Make it seamless/tileable if possible
- Use appropriate colors and patterns for the description

CORRECT Example structure:
import bpy

# Clear default scene
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# Create plane for texture
bpy.ops.mesh.primitive_plane_add(size=2, location=(0, 0, 0))
plane = bpy.context.active_object

# Create material with nodes
mat = bpy.data.materials.new(name="TextureMaterial")
mat.use_nodes = True
nodes = mat.node_tree.nodes
links = mat.node_tree.links
nodes.clear()

# Add nodes (example)
tex_coord = nodes.new(type='ShaderNodeTexCoord')
mapping = nodes.new(type='ShaderNodeMapping')
noise = nodes.new(type='ShaderNodeTexNoise')
color_ramp = nodes.new(type='ShaderNodeValToRGB')
principled = nodes.new(type='ShaderNodeBsdfPrincipled')
output = nodes.new(type='ShaderNodeOutputMaterial')

# Connect nodes
links.new(tex_coord.outputs['Generated'], mapping.inputs['Vector'])
links.new(mapping.outputs['Vector'], noise.inputs['Vector'])
links.new(noise.outputs['Fac'], color_ramp.inputs['Fac'])
links.new(color_ramp.outputs['Color'], principled.inputs['Base Color'])
links.new(principled.outputs['BSDF'], output.inputs['Surface'])

# Assign material
plane.data.materials.append(mat)

# Create image for baking
img = bpy.data.images.new("Texture", width=$TextureSize, height=$TextureSize)
img.filepath_raw = r'$OutputPath'
img.file_format = 'PNG'

# Set up for baking
bpy.context.scene.render.engine = 'CYCLES'
bpy.context.view_layer.objects.active = plane
plane.select_set(True)

# Create image texture node
tex_node = nodes.new(type='ShaderNodeTexImage')
tex_node.image = img
nodes.active = tex_node

# Bake
bpy.ops.object.bake(type='DIFFUSE')
img.save()

Output ONLY valid Python code, no explanations, no markdown.
"@
    
    $pythonCode = Invoke-OllamaChat -Prompt $prompt -ModelName $ModelName -SystemPrompt @{ System = $systemPrompt }
    
    if (-not $pythonCode) {
        return $false
    }
    
    # Clean up code
    $pythonCode = $pythonCode -replace '```python\s*', '' -replace '```\s*', '' -replace '```', ''
    $pythonCode = $pythonCode.Trim()
    
    # Save and execute
    $tempScript = Join-Path $env:TEMP "texture_gen_$(Get-Random).py"
    [System.IO.File]::WriteAllText($tempScript, $pythonCode, [System.Text.UTF8Encoding]::new($false))
    
    $success = Execute-BlenderPython -PythonScript $tempScript -BlenderExePath $BlenderExePath
    
    if ($success -and (Test-Path $OutputPath)) {
        Write-Host "  ✓ Texture generated: $OutputPath" -ForegroundColor Green
        return $true
    }
    
    return $false
}

function Add-ToSpritesheet {
    <#
    .SYNOPSIS
      Adds a texture tile to a spritesheet, finding the first empty slot
    #>
    param(
        [string]$TilePath,
        [string]$SpritesheetPath,
        [int]$TileSize,
        [int]$Columns
    )
    
    if (-not (Test-Path $TilePath)) {
        Write-Host "Error: Tile not found: $TilePath" -ForegroundColor Red
        return $false
    }
    
    # Check if ImageMagick is available
    $magick = Get-Command "magick" -ErrorAction SilentlyContinue
    
    if ($magick) {
        Write-Host "Using ImageMagick for spritesheet assembly..." -ForegroundColor Gray
        
        # Check if spritesheet exists
        if (-not (Test-Path $SpritesheetPath)) {
            # Create new spritesheet (8x8 grid by default, can expand)
            $rows = 8
            $sheetWidth = $TileSize * $Columns
            $sheetHeight = $TileSize * $rows
            
            # Create transparent spritesheet
            & $magick -size "${sheetWidth}x${sheetHeight}" xc:transparent PNG32:$SpritesheetPath
            Write-Host "  Created new spritesheet: ${sheetWidth}x${sheetHeight}" -ForegroundColor Gray
        }
        
        # Find first empty slot
        $sheetInfo = & $magick identify $SpritesheetPath
        $sheetDims = $sheetInfo -match '(\d+)x(\d+)'
        if ($sheetDims) {
            $sheetWidth = [int]($matches[1])
            $sheetHeight = [int]($matches[2])
        }
        
        $rows = [Math]::Floor($sheetHeight / $TileSize)
        $maxSlots = $Columns * $rows
        
        # Try to find empty slot by checking alpha channel
        $foundSlot = $false
        for ($i = 0; $i -lt $maxSlots; $i++) {
            $col = $i % $Columns
            $row = [Math]::Floor($i / $Columns)
            $x = $col * $TileSize
            $y = $row * $TileSize
            
            # Check if this region is empty (has transparency)
            $tempCheck = Join-Path $env:TEMP "spritesheet_check_$(Get-Random).png"
            & $magick $SpritesheetPath -crop "${TileSize}x${TileSize}+${x}+${y}" $tempCheck 2>&1 | Out-Null
            
            # Check if mostly transparent
            $alphaInfo = & $magick identify -format "%[mean]" $tempCheck 2>&1
            Remove-Item $tempCheck -ErrorAction SilentlyContinue
            
            if ($alphaInfo -match '^0\.?0*$' -or $alphaInfo -eq '0') {
                # Empty slot found, paste tile here
                $tileResized = Join-Path $env:TEMP "tile_resized_$(Get-Random).png"
                & $magick $TilePath -resize "${TileSize}x${TileSize}" $tileResized 2>&1 | Out-Null
                
                & $magick $SpritesheetPath -geometry "+${x}+${y}" -composite $tileResized $SpritesheetPath 2>&1 | Out-Null
                
                Remove-Item $tileResized -ErrorAction SilentlyContinue
                
                Write-Host "  ✓ Added tile to spritesheet at slot $i (row $row, col $col)" -ForegroundColor Green
                $foundSlot = $true
                break
            }
        }
        
        if (-not $foundSlot) {
            Write-Host "  ⚠ No empty slots found, appending to end" -ForegroundColor Yellow
            # Expand spritesheet or create new row
            # For now, just report
            Write-Host "  Manual expansion needed" -ForegroundColor Yellow
        }
        
        return $true
    } else {
        Write-Host "ImageMagick not found. Creating manifest for manual spritesheet assembly." -ForegroundColor Yellow
        Write-Host "  Install ImageMagick or use Python PIL script" -ForegroundColor Gray
        
        # Create manifest entry
        $manifestPath = "$SpritesheetPath.manifest.txt"
        $manifestEntry = "Tile: $TilePath`nSize: ${TileSize}x${TileSize}`n`n"
        Add-Content -Path $manifestPath -Value $manifestEntry
        
        return $false
    }
}

function Generate-Texture {
    <#
    .SYNOPSIS
      Complete texture generation pipeline
    #>
    param(
        [string]$Description,
        [string]$OutputPath,
        [string]$TextureMethod,
        [int]$TextureSize,
        [string]$ModelName,
        [string]$BlenderExePath,
        [string]$SpritesheetPath = "",
        [int]$TileSize = 128,
        [int]$Columns = 8
    )
    
    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host "  Generating Texture" -ForegroundColor Cyan
    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host ""
    
    $success = $false
    
    switch ($TextureMethod) {
        "Procedural" {
            if (-not $BlenderExePath) {
                $BlenderExePath = Find-Blender
            }
            
            if (-not $BlenderExePath) {
                Write-Host "Error: Blender not found for procedural texture generation" -ForegroundColor Red
                return $false
            }
            
            $success = Generate-TextureProcedural -Description $Description -OutputPath $OutputPath -TextureSize $TextureSize -ModelName $ModelName -BlenderExePath $BlenderExePath
        }
        
        "Diffusion" {
            Write-Host "Shared SD3.5 via tx_ai_pipeline..." -ForegroundColor Cyan
            $pipe = Join-Path $PSScriptRoot "tx_ai_pipeline.py"
            $py = (Get-Command python -ErrorAction SilentlyContinue).Source
            if (-not $py -or -not (Test-Path -LiteralPath $pipe)) {
                Write-Host "Error: python / tx_ai_pipeline.py not found" -ForegroundColor Red
                return $false
            }
            $parent = Split-Path -Parent $OutputPath
            if ($parent -and -not (Test-Path -LiteralPath $parent)) {
                New-Item -ItemType Directory -Path $parent -Force | Out-Null
            }
            $size = [Math]::Max(512, [int]$TextureSize)
            & $py $pipe image --prompt $Description --out $OutputPath --kind texture --size $size
            $success = ($LASTEXITCODE -eq 0 -and (Test-Path -LiteralPath $OutputPath))
        }
        
        "Hybrid" {
            Write-Host "Hybrid: SD albedo via tx_ai_pipeline (derived maps in skins CLI)..." -ForegroundColor Cyan
            $pipe = Join-Path $PSScriptRoot "tx_ai_pipeline.py"
            $py = (Get-Command python -ErrorAction SilentlyContinue).Source
            if (-not $py -or -not (Test-Path -LiteralPath $pipe)) {
                Write-Host "Error: python / tx_ai_pipeline.py not found" -ForegroundColor Red
                return $false
            }
            $outDir = Split-Path -Parent $OutputPath
            $base = [IO.Path]::GetFileNameWithoutExtension($OutputPath)
            if (-not $base) { $base = "texture" }
            if ($outDir -and -not (Test-Path -LiteralPath $outDir)) {
                New-Item -ItemType Directory -Path $outDir -Force | Out-Null
            }
            & $py $pipe skins --name $base --out-dir $outDir --theme $Description --quality standard
            $albedo = Get-ChildItem -LiteralPath $outDir -Filter "${base}_diffuse.png" -File -ErrorAction SilentlyContinue | Select-Object -First 1
            if ($albedo) {
                Copy-Item -LiteralPath $albedo.FullName -Destination $OutputPath -Force
                $success = $true
            }
        }
    }
    
    if ($success -and -not [string]::IsNullOrWhiteSpace($SpritesheetPath)) {
        Write-Host ""
        Write-Host "Adding texture to spritesheet..." -ForegroundColor Cyan
        Add-ToSpritesheet -TilePath $OutputPath -SpritesheetPath $SpritesheetPath -TileSize $TileSize -Columns $Columns
    }
    
    return $success
}

function Batch-GenerateTextures {
    <#
    .SYNOPSIS
      Batch generate multiple textures from descriptions
    #>
    param(
        [string[]]$Descriptions,
        [string]$OutputDir,
        [string]$TextureMethod,
        [int]$TextureSize,
        [string]$ModelName,
        [string]$BlenderExePath,
        [string]$SpritesheetPath = "",
        [int]$TileSize = 128,
        [int]$Columns = 8
    )
    
    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host "  Batch Texture Generation" -ForegroundColor Cyan
    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Generating $($Descriptions.Count) textures..." -ForegroundColor Cyan
    Write-Host ""
    
    if (-not (Test-Path $OutputDir)) {
        New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
    }
    
    $successCount = 0
    $index = 0
    
    foreach ($desc in $Descriptions) {
        $index++
        Write-Host "[$index/$($Descriptions.Count)] $desc" -ForegroundColor Cyan
        
        $safeName = ($desc -replace '[^\w\s]', '' -replace '\s+', '_').Substring(0, [Math]::Min(40, $desc.Length))
        $texturePath = Join-Path $OutputDir "${safeName}.png"
        
        $success = Generate-Texture -Description $desc -OutputPath $texturePath -TextureMethod $TextureMethod -TextureSize $TextureSize -ModelName $ModelName -BlenderExePath $BlenderExePath -SpritesheetPath $SpritesheetPath -TileSize $TileSize -Columns $Columns
        
        if ($success) {
            $successCount++
        }
        
        Write-Host ""
    }
    
    Write-Host "Batch complete: $successCount/$($Descriptions.Count) textures generated" -ForegroundColor $(if ($successCount -eq $Descriptions.Count) { "Green" } else { "Yellow" })
    
    return $successCount
}

# ============================================================
# MAIN EXECUTION
# ============================================================

Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Transcendence Asset Maker AI" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# Check Ollama installation
if ($CheckOllama -or $ListModels) {
    $ollamaExe = Find-Ollama
    
    if ($ollamaExe) {
        Write-Host "Ollama found: $ollamaExe" -ForegroundColor Green
        
        if (Test-OllamaRunning) {
            Write-Host "Ollama service: Running" -ForegroundColor Green
            
            if ($ListModels) {
                Write-Host ""
                Write-Host "Available models:" -ForegroundColor Cyan
                $models = Get-AvailableModels
                if ($models.Count -gt 0) {
                    foreach ($model in $models) {
                        Write-Host "  - $model" -ForegroundColor Gray
                    }
                } else {
                    Write-Host "  No models installed. Run: ollama pull llama3.2" -ForegroundColor Yellow
                }
            }
        } else {
            Write-Host "Ollama service: Not running" -ForegroundColor Yellow
            Write-Host "  Start with: ollama serve" -ForegroundColor Gray
            Write-Host "  Or run this script to auto-start" -ForegroundColor Gray
        }
    } else {
        Write-Host "Ollama not found" -ForegroundColor Red
        Write-Host "  Download from: https://ollama.ai/download" -ForegroundColor Yellow
        Write-Host "  Or use: -InstallOllama" -ForegroundColor Yellow
    }
    
    exit 0
}

# Find and start Ollama
$ollamaExe = Find-Ollama

if (-not $ollamaExe) {
    if ($InstallOllama) {
        Write-Host "Ollama not found. Installation not yet implemented." -ForegroundColor Yellow
        Write-Host "  Please download from: https://ollama.ai/download" -ForegroundColor Yellow
        Write-Host "  Or install manually: $script:OllamaDownloadUrl" -ForegroundColor Gray
    } else {
        Write-Host "Error: Ollama not found" -ForegroundColor Red
        Write-Host "  Use -CheckOllama to verify installation" -ForegroundColor Yellow
        Write-Host "  Use -InstallOllama to download (not yet implemented)" -ForegroundColor Yellow
        Write-Host "  Download manually: https://ollama.ai/download" -ForegroundColor Yellow
    }
    exit 1
}

# Start Ollama service if not running
if (-not (Test-OllamaRunning)) {
    Write-Host "Starting Ollama service..." -ForegroundColor Cyan
    $started = Start-OllamaService -OllamaExePath $ollamaExe
    if (-not $started) {
        Write-Host "Error: Could not start Ollama service" -ForegroundColor Red
        Write-Host "  Try running manually: ollama serve" -ForegroundColor Yellow
        exit 1
    }
    Write-Host ""
}

# Get model to use
if ([string]::IsNullOrWhiteSpace($Model)) {
    $Model = Get-RecommendedModel
    Write-Host "Using model: $Model" -ForegroundColor Green
    Write-Host ""
} else {
    Write-Host "Using specified model: $Model" -ForegroundColor Green
    Write-Host ""
}

# Determine output path
if ([string]::IsNullOrWhiteSpace($OutputPath)) {
    $OutputPath = Join-Path $PSScriptRoot "AI_Generated_Assets"
}

if (-not (Test-Path $OutputPath)) {
    New-Item -ItemType Directory -Path $OutputPath -Force | Out-Null
}

# Execute action
switch ($Action) {
    "GenerateName" {
        if ([string]::IsNullOrWhiteSpace($InputData)) {
            Write-Host "Error: InputData required for GenerateName" -ForegroundColor Red
            exit 1
        }
        
        $name = Generate-AssetName -AssetType $AssetType -Description $InputData -ModelName $Model
        if ($name) {
            $outputFile = Join-Path $OutputPath "generated_name.txt"
            [System.IO.File]::WriteAllText($outputFile, $name, [System.Text.UTF8Encoding]::new($false))
            Write-Host ""
            Write-Host "Saved to: $outputFile" -ForegroundColor Green
        }
    }
    
    "GenerateDescription" {
        if ([string]::IsNullOrWhiteSpace($InputData)) {
            Write-Host "Error: Asset name required for GenerateDescription" -ForegroundColor Red
            exit 1
        }
        
        $description = Generate-AssetDescription -AssetType $AssetType -AssetName $InputData -ModelName $Model
        if ($description) {
            $outputFile = Join-Path $OutputPath "generated_description.txt"
            [System.IO.File]::WriteAllText($outputFile, $description, [System.Text.UTF8Encoding]::new($false))
            Write-Host ""
            Write-Host "Saved to: $outputFile" -ForegroundColor Green
        }
    }
    
    "CreateXML" {
        if ([string]::IsNullOrWhiteSpace($InputData)) {
            Write-Host "Error: Asset name required for CreateXML" -ForegroundColor Red
            exit 1
        }
        
        # Try to load additional data from file if InputData is a path
        $additionalData = @{}
        if (Test-Path $InputData) {
            try {
                $fileContent = Get-Content $InputData -Raw | ConvertFrom-Json
                $additionalData = $fileContent | ConvertTo-Hashtable
            }
            catch {
                # Not JSON, use as asset name
                $assetName = $InputData
            }
        } else {
            $assetName = $InputData
        }
        
        $xml = Generate-AssetXML -AssetType $AssetType -AssetName $assetName -Description "" -ModelName $Model -AdditionalData $additionalData
        if ($xml) {
            $outputFile = Join-Path $OutputPath "$assetName.xml"
            [System.IO.File]::WriteAllText($outputFile, $xml, [System.Text.UTF8Encoding]::new($false))
            Write-Host ""
            Write-Host "Saved to: $outputFile" -ForegroundColor Green
        }
    }
    
    "OptimizeAsset" {
        if ([string]::IsNullOrWhiteSpace($InputData) -or -not (Test-Path $InputData)) {
            Write-Host "Error: InputData must be a valid file path" -ForegroundColor Red
            exit 1
        }
        
        $suggestions = Optimize-AssetMetadata -InputFile $InputData -ModelName $Model
        if ($suggestions) {
            $outputFile = Join-Path $OutputPath "optimization_suggestions.txt"
            [System.IO.File]::WriteAllText($outputFile, $suggestions, [System.Text.UTF8Encoding]::new($false))
            Write-Host ""
            Write-Host "Saved to: $outputFile" -ForegroundColor Green
        }
    }
    
    "GenerateCredits" {
        if ([string]::IsNullOrWhiteSpace($InputData)) {
            Write-Host "Error: Mod name required for GenerateCredits" -ForegroundColor Red
            exit 1
        }
        
        $credits = Generate-CreditsText -ModName $InputData -AssetNames @() -ModelName $Model
        if ($credits) {
            $outputFile = Join-Path $OutputPath "CREDITS.txt"
            [System.IO.File]::WriteAllText($outputFile, $credits, [System.Text.UTF8Encoding]::new($false))
            Write-Host ""
            Write-Host "Saved to: $outputFile" -ForegroundColor Green
        }
    }
    
    "Generate3DModel" {
        # Launch control room if requested
        $watchDir = $null
        if ($LaunchControlRoom) {
            $controlRoomScript = Join-Path $PSScriptRoot "AssetGeneratorControlRoom.ps1"
            if (Test-Path $controlRoomScript) {
                $watchDir = if ([string]::IsNullOrWhiteSpace($ControlRoomWatchDir)) {
                    $tempWatchDir = Join-Path $env:TEMP "AssetGenerator_$(Get-Random)"
                    if (-not (Test-Path $tempWatchDir)) {
                        New-Item -ItemType Directory -Path $tempWatchDir -Force | Out-Null
                    }
                    $tempWatchDir
                } else {
                    if (-not (Test-Path $ControlRoomWatchDir)) {
                        New-Item -ItemType Directory -Path $ControlRoomWatchDir -Force | Out-Null
                    }
                    $ControlRoomWatchDir
                }
                
                $controlRoomArgs = @(
                    "-AssetType", "Model",
                    "-DrawingPath", (if ($InputData -like "*.png" -or $InputData -like "*.jpg") { $InputData } else { "" }),
                    "-OllamaModel", $Model,
                    "-WatchDirectory", $watchDir,
                    "-AutoExport"
                )
                
                Start-Process -FilePath "pwsh" -ArgumentList "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "`"$controlRoomScript`"", $controlRoomArgs -WindowStyle Normal
                Write-Host "Control Room launched" -ForegroundColor Cyan
                Write-Host "  Watch directory: $watchDir" -ForegroundColor Gray
                Start-Sleep -Seconds 2  # Give GUI time to initialize
            }
        }
        
        if ([string]::IsNullOrWhiteSpace($InputData)) {
            Write-Host "Error: Description required for Generate3DModel" -ForegroundColor Red
            Write-Host "  Example: -InputData 'a simple low-poly fantasy tree'" -ForegroundColor Yellow
            exit 1
        }
        
        # Find Blender
        $blenderExe = Find-Blender
        if (-not $blenderExe) {
            Write-Host "Error: Blender not found" -ForegroundColor Red
            Write-Host "  Install Blender from: https://www.blender.org/" -ForegroundColor Yellow
            Write-Host "  Or specify path: -BlenderPath 'C:\Path\To\Blender\blender.exe'" -ForegroundColor Yellow
            exit 1
        }
        
        Write-Host "Blender found: $blenderExe" -ForegroundColor Green
        Write-Host ""
        
        # Determine output path (use watch directory if control room is active)
        $modelOutputPath = if ($watchDir) {
            $modelName = ($InputData -replace '[^\w\s]', '' -replace '\s+', '_').Substring(0, [Math]::Min(30, $InputData.Length))
            Join-Path $watchDir "$modelName.$($ModelFormat.ToLower())"
        } elseif ([string]::IsNullOrWhiteSpace($OutputPath)) {
            $modelName = ($InputData -replace '[^\w\s]', '' -replace '\s+', '_').Substring(0, [Math]::Min(30, $InputData.Length))
            Join-Path $PSScriptRoot "AI_Generated_Assets" "$modelName.$($ModelFormat.ToLower())"
        } else {
            # If OutputPath is a directory, create filename
            if (Test-Path $OutputPath -PathType Container) {
                $modelName = ($InputData -replace '[^\w\s]', '' -replace '\s+', '_').Substring(0, [Math]::Min(30, $InputData.Length))
                Join-Path $OutputPath "$modelName.$($ModelFormat.ToLower())"
            } else {
                $OutputPath
            }
        }
        
        # Generate the 3D model
        $success = Generate-3DModel -Description $InputData -OutputPath $modelOutputPath -ModelFormat $ModelFormat -DetailLevel $DetailLevel -ModelName $Model -BlenderExePath $blenderExe
        
        if ($success) {
            Write-Host ""
            Write-Host "Model saved to: $modelOutputPath" -ForegroundColor Green
        } else {
            Write-Host ""
            Write-Host "Model generation failed. Check the Python script for errors." -ForegroundColor Red
            exit 1
        }
    }
    
    "GenerateTexture" {
        # Launch control room if requested
        $watchDir = $null
        if ($LaunchControlRoom) {
            $controlRoomScript = Join-Path $PSScriptRoot "AssetGeneratorControlRoom.ps1"
            if (Test-Path $controlRoomScript) {
                $watchDir = if ([string]::IsNullOrWhiteSpace($ControlRoomWatchDir)) {
                    $tempWatchDir = Join-Path $env:TEMP "AssetGenerator_$(Get-Random)"
                    if (-not (Test-Path $tempWatchDir)) {
                        New-Item -ItemType Directory -Path $tempWatchDir -Force | Out-Null
                    }
                    $tempWatchDir
                } else {
                    if (-not (Test-Path $ControlRoomWatchDir)) {
                        New-Item -ItemType Directory -Path $ControlRoomWatchDir -Force | Out-Null
                    }
                    $ControlRoomWatchDir
                }
                
                $controlRoomArgs = @(
                    "-AssetType", "Texture",
                    "-DrawingPath", (if ($InputData -like "*.png" -or $InputData -like "*.jpg") { $InputData } else { "" }),
                    "-OllamaModel", $Model,
                    "-WatchDirectory", $watchDir,
                    "-AutoExport"
                )
                
                Start-Process -FilePath "pwsh" -ArgumentList "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "`"$controlRoomScript`"", $controlRoomArgs -WindowStyle Normal
                Write-Host "Control Room launched" -ForegroundColor Cyan
                Write-Host "  Watch directory: $watchDir" -ForegroundColor Gray
                Start-Sleep -Seconds 2
            }
        }
        
        if ([string]::IsNullOrWhiteSpace($InputData)) {
            Write-Host "Error: Description required for GenerateTexture" -ForegroundColor Red
            Write-Host "  Example: -InputData 'cracked stone texture, low contrast'" -ForegroundColor Yellow
            exit 1
        }
        
        # Find Blender if using procedural method
        $blenderExe = $null
        if ($TextureMethod -eq "Procedural") {
            $blenderExe = Find-Blender
            if (-not $blenderExe) {
                Write-Host "Error: Blender not found for procedural texture generation" -ForegroundColor Red
                exit 1
            }
            Write-Host "Blender found: $blenderExe" -ForegroundColor Green
        }
        
        # Determine output path (use watch directory if control room is active)
        $textureOutputPath = if ($watchDir) {
            $textureName = ($InputData -replace '[^\w\s]', '' -replace '\s+', '_').Substring(0, [Math]::Min(40, $InputData.Length))
            Join-Path $watchDir "${textureName}.png"
        } elseif ([string]::IsNullOrWhiteSpace($OutputPath)) {
            $textureName = ($InputData -replace '[^\w\s]', '' -replace '\s+', '_').Substring(0, [Math]::Min(40, $InputData.Length))
            Join-Path $PSScriptRoot "AI_Generated_Assets" "${textureName}.png"
        } else {
            if (Test-Path $OutputPath -PathType Container) {
                $textureName = ($InputData -replace '[^\w\s]', '' -replace '\s+', '_').Substring(0, [Math]::Min(40, $InputData.Length))
                Join-Path $OutputPath "${textureName}.png"
            } else {
                $OutputPath
            }
        }
        
        # Generate texture
        $success = Generate-Texture -Description $InputData -OutputPath $textureOutputPath -TextureMethod $TextureMethod -TextureSize $TextureSize -ModelName $Model -BlenderExePath $blenderExe -SpritesheetPath $SpritesheetPath -TileSize $TileSize -Columns $SpritesheetColumns
        
        if ($success) {
            Write-Host ""
            Write-Host "Texture saved to: $textureOutputPath" -ForegroundColor Green
        } else {
            Write-Host ""
            Write-Host "Texture generation failed." -ForegroundColor Red
            exit 1
        }
    }
    
    "AssembleSpritesheet" {
        if ([string]::IsNullOrWhiteSpace($InputData)) {
            Write-Host "Error: InputData must be a directory path containing texture files" -ForegroundColor Red
            exit 1
        }
        
        if (-not (Test-Path $InputData -PathType Container)) {
            Write-Host "Error: Directory not found: $InputData" -ForegroundColor Red
            exit 1
        }
        
        if ([string]::IsNullOrWhiteSpace($SpritesheetPath)) {
            $SpritesheetPath = Join-Path $InputData "spritesheet.png"
        }
        
        Write-Host "Assembling spritesheet from: $InputData" -ForegroundColor Cyan
        Write-Host "Output: $SpritesheetPath" -ForegroundColor Gray
        Write-Host ""
        
        $textures = Get-ChildItem -LiteralPath $InputData -Filter "*.png" -File | Sort-Object Name
        
        if ($textures.Count -eq 0) {
            Write-Host "No PNG textures found in directory" -ForegroundColor Yellow
            exit 1
        }
        
        Write-Host "Found $($textures.Count) texture(s)" -ForegroundColor Gray
        Write-Host ""
        
        $addedCount = 0
        foreach ($texture in $textures) {
            Write-Host "Adding: $($texture.Name)" -ForegroundColor Gray
            $success = Add-ToSpritesheet -TilePath $texture.FullName -SpritesheetPath $SpritesheetPath -TileSize $TileSize -Columns $SpritesheetColumns
            if ($success) {
                $addedCount++
            }
        }
        
        Write-Host ""
        Write-Host "Spritesheet assembly complete: $addedCount/$($textures.Count) textures added" -ForegroundColor Green
        Write-Host "Spritesheet saved to: $SpritesheetPath" -ForegroundColor Green
    }
    
    "BatchTextures" {
        if ([string]::IsNullOrWhiteSpace($InputData)) {
            Write-Host "Error: InputData must be a file path containing descriptions (one per line)" -ForegroundColor Red
            exit 1
        }
        
        if (Test-Path $InputData) {
            # Load descriptions from file
            $descriptions = Get-Content $InputData | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
        } else {
            # Treat as comma-separated list
            $descriptions = $InputData -split ',' | ForEach-Object { $_.Trim() } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
        }
        
        if ($descriptions.Count -eq 0) {
            Write-Host "Error: No descriptions found" -ForegroundColor Red
            exit 1
        }
        
        # Determine output directory
        $outputDir = if ([string]::IsNullOrWhiteSpace($OutputPath)) {
            Join-Path $PSScriptRoot "AI_Generated_Assets\Textures"
        } else {
            $OutputPath
        }
        
        # Find Blender if needed
        $blenderExe = $null
        if ($TextureMethod -eq "Procedural") {
            $blenderExe = Find-Blender
            if (-not $blenderExe) {
                Write-Host "Error: Blender not found for procedural texture generation" -ForegroundColor Red
                exit 1
            }
        }
        
        # Batch generate
        $successCount = Batch-GenerateTextures -Descriptions $descriptions -OutputDir $outputDir -TextureMethod $TextureMethod -TextureSize $TextureSize -ModelName $Model -BlenderExePath $blenderExe -SpritesheetPath $SpritesheetPath -TileSize $TileSize -Columns $SpritesheetColumns
        
        Write-Host ""
        if (-not [string]::IsNullOrWhiteSpace($SpritesheetPath)) {
            Write-Host "Spritesheet saved to: $SpritesheetPath" -ForegroundColor Green
        }
    }
    
    default {
        Write-Host "Error: Unknown action: $Action" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Complete" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""


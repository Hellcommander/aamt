#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Real-time GUI control room for Qud tile generation with AI assistance.
    
.DESCRIPTION
    WPF-based GUI that provides:
    - Live preview of generated tiles
    - Real-time chat with Ollama
    - Prompt tweaking and regeneration
    - Integration with Blender tile baker
    - File watching for automatic preview updates
#>

param(
    [Parameter(Mandatory=$false)]
    [string]$DrawingPath = "",
    
    [Parameter(Mandatory=$false)]
    [string]$RegistryPath = "",
    
    [Parameter(Mandatory=$false)]
    [string]$AssetId = "",
    
    [Parameter(Mandatory=$false)]
    [string]$OllamaModel = "",
    
    [Parameter(Mandatory=$false)]
    [string]$BlenderPath = "",
    
    [Parameter(Mandatory=$false)]
    [int]$TileSize = 32
)

$ErrorActionPreference = "Stop"

# AI-Assisted Modding Tools (AAMT) - Caves of Qud Toolset

# Load shared asset generation settings
$settingsPath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "..\\AssetGenerationSettings.ps1"
if (Test-Path $settingsPath) {
    . $settingsPath
}
$PSScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

# Import unified tool detection and integration
$sharedPath = Join-Path (Split-Path -Parent (Split-Path -Parent $PSScriptRoot)) "Shared"
Import-Module (Join-Path $sharedPath "ToolDetection.psm1") -ErrorAction SilentlyContinue
Import-Module (Join-Path $sharedPath "ToolsetIntegration.psm1") -ErrorAction SilentlyContinue

# Initialize tools for Qud AI tile generation
$tools = Initialize-ToolsetTools `
    -RequiredTools @("Blender", "ImageMagick") `
    -OptionalTools @("Ollama")

if (-not $tools.AllRequiredAvailable) {
    Write-Host "`nERROR: Missing required tools for Qud AI tile generation" -ForegroundColor Red
    Show-ToolsetStatus -ToolsetName "Caves of Qud" `
        -RequiredTools @("Blender", "ImageMagick") `
        -OptionalTools @("Ollama")
    exit 1
}

# Use Ollama if available
if ($tools.Tools["Ollama"].Available) {
    Use-OllamaIfAvailable | Out-Null
    Write-Host "[OK] Ollama integration enabled" -ForegroundColor Green
} else {
    Write-Host "[WARNING] Ollama not available - AI features will be limited" -ForegroundColor Yellow
}

# ------------------------------------------------------------
# Load Required Assemblies
# ------------------------------------------------------------

Add-Type -AssemblyName PresentationFramework, PresentationCore, System.Windows.Forms, System.Drawing

# Import Ollama functions from AssetMakerAI
$assetMakerPath = Join-Path $PSScriptRoot "AssetMakerAI.ps1"
if (Test-Path $assetMakerPath) {
    . $assetMakerPath -ErrorAction SilentlyContinue
}

# Fallback Ollama functions if not imported
if (-not (Get-Command "Invoke-OllamaChat" -ErrorAction SilentlyContinue)) {
    $script:OllamaUrl = "http://localhost:11434"
    $script:OllamaApiUrl = "$script:OllamaUrl/api"
    
    function Test-OllamaRunning {
        try {
            $response = Invoke-RestMethod -Uri "$script:OllamaApiUrl/tags" -Method Get -TimeoutSec 2 -ErrorAction Stop
            return $true
        }
        catch {
            return $false
        }
    }
    
    function Invoke-OllamaChat {
        param(
            [string]$Prompt,
            [string]$ModelName,
            [hashtable]$SystemPrompt = @{}
        )
        
        if (-not (Test-OllamaRunning)) {
            return $null
        }
        
        $systemMessage = if ($SystemPrompt.Count -gt 0) {
            $SystemPrompt.Values | Select-Object -First 1
        } else {
            "You are a helpful assistant for creating game mod assets."
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
            }
            
            return $null
        }
        catch {
            return $null
        }
    }
}

# ------------------------------------------------------------
# Configuration
# ------------------------------------------------------------

$script:OllamaModel = if ([string]::IsNullOrWhiteSpace($OllamaModel)) {
    "llama3.2"
} else {
    $OllamaModel
}

$script:TempDir = Join-Path $env:TEMP "QudTileAIGenerator_$(Get-Random)"
if (-not (Test-Path $script:TempDir)) {
    New-Item -ItemType Directory -Path $script:TempDir -Force | Out-Null
}

$script:CurrentSpecPath = Join-Path $script:TempDir "current_spec.json"
$script:CurrentTilePath = Join-Path $script:TempDir "preview_tile.png"
$script:PromptHistory = @()
$script:CurrentSpec = $null

# ------------------------------------------------------------
# Helper Functions
# ------------------------------------------------------------

function Find-Blender {
    if (-not [string]::IsNullOrWhiteSpace($BlenderPath)) {
        $providedPath = $BlenderPath.Trim()
        if (Test-Path $providedPath) {
            return $providedPath
        }
    }
    
    $envVars = @("BLENDER_PATH", "BLENDER_DIR", "BLENDER_HOME")
    foreach ($envVar in $envVars) {
        $envPath = [System.Environment]::GetEnvironmentVariable($envVar)
        if (-not [string]::IsNullOrWhiteSpace($envPath) -and (Test-Path $envPath)) {
            $blenderExe = if (Test-Path $envPath -PathType Container) {
                Join-Path $envPath "blender.exe"
            } else {
                $envPath
            }
            if (Test-Path $blenderExe) {
                return $blenderExe
            }
        }
    }
    
    $blender = Get-Command "blender" -ErrorAction SilentlyContinue
    if ($blender) {
        return $blender.Source
    }
    
    $commonPaths = @(
        "D:\tools\Blender Foundation",
        "${env:ProgramFiles}\Blender Foundation"
    )
    
    foreach ($basePath in $commonPaths) {
        if (Test-Path $basePath) {
            $blenderDirs = Get-ChildItem -LiteralPath $basePath -Directory -ErrorAction SilentlyContinue |
                Where-Object { $_.Name -match '^Blender' } |
                Sort-Object Name -Descending
            
            foreach ($dir in $blenderDirs) {
                $blenderExe = Join-Path $dir.FullName "blender.exe"
                if (Test-Path $blenderExe) {
                    return $blenderExe
                }
            }
        }
    }
    
    return $null
}

function Update-PreviewImage {
    param([string]$ImagePath)
    
    if (-not (Test-Path $ImagePath)) {
        return $false
    }
    
    try {
        $window.Dispatcher.Invoke([action]{
            try {
                $bitmap = New-Object System.Windows.Media.Imaging.BitmapImage
                $bitmap.BeginInit()
                $bitmap.CacheOption = [System.Windows.Media.Imaging.BitmapCacheOption]::OnLoad
                $bitmap.UriSource = New-Object System.Uri((Resolve-Path $ImagePath).Path)
                $bitmap.EndInit()
                $bitmap.Freeze()
                
                $PreviewImage.Source = $bitmap
                return $true
            }
            catch {
                Write-Log "Error updating preview: $_"
                return $false
            }
        })
        return $true
    }
    catch {
        Write-Log "Error in preview update: $_"
        return $false
    }
}

function Write-Log {
    param([string]$Message)
    
    $timestamp = Get-Date -Format "HH:mm:ss"
    $logMessage = "[$timestamp] $Message"
    
    $window.Dispatcher.Invoke([action]{
        $LogBox.AppendText("$logMessage`r`n")
        $LogBox.ScrollToEnd()
    })
}

function Update-Status {
    param([string]$Message)
    
    $window.Dispatcher.Invoke([action]{
        $StatusText.Text = $Message
    })
}

function Invoke-BlenderBake {
    param(
        [string]$DrawingPath,
        [string]$SpecPath,
        [int]$Size,
        [string]$OutputPath
    )
    
    $blenderExe = Find-Blender
    if (-not $blenderExe) {
        Write-Log "Error: Blender not found"
        return $false
    }
    
    $bakerScript = Join-Path $PSScriptRoot "qud_tile_baker.py"
    if (-not (Test-Path $bakerScript)) {
        Write-Log "Error: qud_tile_baker.py not found"
        return $false
    }
    
    # Load spec if available
    $palette = "#ffffff,#000000"
    $style = "painterly"
    $quality = "standard"
    
    if (Test-Path $SpecPath) {
        try {
            $spec = Get-Content $SpecPath -Raw -Encoding UTF8 | ConvertFrom-Json
            if ($spec.material -and $spec.material.palette) {
                $palette = ($spec.material.palette | ForEach-Object { $_.hex }) -join ","
            }
            if ($spec.material -and $spec.material.style) {
                $style = $spec.material.style
            }
            if ($spec.material -and $spec.material.quality) {
                $quality = $spec.material.quality
            }
        }
        catch {
            Write-Log "Warning: Could not load spec, using defaults"
        }
    }
    
    $blenderArgs = @(
        "--background",
        "--python", "`"$bakerScript`"",
        "--",
        "--drawing", "`"$DrawingPath`"",
        "--size", $Size,
        "--palette", "`"$palette`"",
        "--style", $style,
        "--quality", $quality,
        "--output", "`"$OutputPath`""
    )
    
    Write-Log "Starting Blender bake..."
    Write-Log "  Drawing: $DrawingPath"
    Write-Log "  Output: $OutputPath"
    
    try {
        $process = Start-Process -FilePath $blenderExe -ArgumentList $blenderArgs -Wait -NoNewWindow -PassThru
        
        if ($process.ExitCode -eq 0 -and (Test-Path $OutputPath)) {
            Write-Log "Bake complete!"
            return $true
        } else {
            Write-Log "Bake failed (exit code: $($process.ExitCode))"
            return $false
        }
    }
    catch {
        Write-Log "Error running Blender: $_"
        return $false
    }
}

function Invoke-AIGeneration {
    param(
        [string]$UserPrompt,
        [string]$DrawingPath,
        [array]$History = @()
    )
    
    if (-not (Test-OllamaRunning)) {
        Write-Log "Error: Ollama is not running"
        Update-Status "Error: Ollama not running"
        return $null
    }
    
    # Build prompt with context
    $contextPrompt = @"
You are an expert procedural texture designer for Caves of Qud tiles.

The user has provided a line drawing that will be used as a mask/shape source.
Generate a material specification JSON for this tile.

User Request: $UserPrompt

Drawing: $DrawingPath

Previous Context:
$($History -join "`n")

Generate a JSON specification with this structure:
{
  "material": {
    "style": "painterly|pixel|flat|procedural",
    "palette": [
      {"hex": "#xxxxxx", "usage": "..."}
    ],
    "contrast": "low|medium|high",
    "quality": "draft|standard|high|ultra",
    "proceduralLayers": [...]
  }
}

Output ONLY valid JSON, no commentary.
"@
    
    Write-Log "Sending prompt to AI..."
    Update-Status "Generating with AI..."
    
    $response = Invoke-OllamaChat -Prompt $contextPrompt -ModelName $script:OllamaModel -SystemPrompt @{
        System = "You are an expert procedural texture designer. Output ONLY valid JSON with no commentary."
    }
    
    if ($response) {
        Write-Log "AI response received"
        
        # Extract JSON from response
        $jsonMatch = $response -match '\{[\s\S]*\}'
        if ($jsonMatch) {
            try {
                $spec = $matches[0] | ConvertFrom-Json
                $script:CurrentSpec = $spec
                
                # Save spec
                $spec | ConvertTo-Json -Depth 10 | Set-Content -Path $script:CurrentSpecPath -Encoding UTF8
                
                Write-Log "Spec saved to: $script:CurrentSpecPath"
                return $spec
            }
            catch {
                Write-Log "Error parsing JSON: $_"
                return $null
            }
        } else {
            Write-Log "No JSON found in response"
            return $null
        }
    } else {
        Write-Log "No response from AI"
        return $null
    }
}

# ------------------------------------------------------------
# WPF GUI
# ------------------------------------------------------------

[xml]$xaml = @"
<Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
        Title="Qud Tile AI Generator - Control Room" Height="700" Width="1200"
        WindowStartupLocation="CenterScreen">
  <Grid Margin="8">
    <Grid.ColumnDefinitions>
      <ColumnDefinition Width="2*"/>
      <ColumnDefinition Width="3*"/>
    </Grid.ColumnDefinitions>
    <Grid.RowDefinitions>
      <RowDefinition Height="Auto"/>
      <RowDefinition Height="3*"/>
      <RowDefinition Height="Auto"/>
      <RowDefinition Height="*"/>
    </Grid.RowDefinitions>

    <!-- Header -->
    <TextBlock Grid.Row="0" Grid.ColumnSpan="2" Text="Qud Tile AI Generator" 
               FontSize="18" FontWeight="Bold" Margin="0,0,0,8"/>

    <!-- Preview (Left) -->
    <GroupBox Grid.Row="1" Grid.Column="0" Header="Live Preview" Margin="4">
      <Grid>
        <Border BorderBrush="Gray" BorderThickness="1" Background="Black">
          <Image Name="PreviewImage" Stretch="Uniform" />
        </Border>
        <TextBlock Name="PreviewPlaceholder" Text="No preview available" 
                   HorizontalAlignment="Center" VerticalAlignment="Center"
                   Foreground="Gray" FontSize="14"/>
      </Grid>
    </GroupBox>

    <!-- Chat + Controls (Right) -->
    <GroupBox Grid.Row="1" Grid.Column="1" Header="AI Chat &amp; Controls" Margin="4">
      <Grid>
        <Grid.RowDefinitions>
          <RowDefinition Height="*"/>
          <RowDefinition Height="Auto"/>
          <RowDefinition Height="*"/>
          <RowDefinition Height="Auto"/>
        </Grid.RowDefinitions>

        <!-- Prompt Input -->
        <TextBox Grid.Row="0" Name="PromptBox" AcceptsReturn="True" TextWrapping="Wrap"
                 VerticalScrollBarVisibility="Auto" FontSize="12"
                 Text="Use this sketch as a silhouette. Make it more crystalline, cooler palette, strong rim light."/>

        <!-- Control Buttons -->
        <StackPanel Grid.Row="1" Orientation="Horizontal" Margin="0,8,0,8">
          <Button Name="SendPromptButton" Content="Send to AI" Width="120" Height="30" Margin="0,0,8,0"/>
          <Button Name="BakeTileButton" Content="Bake Tile" Width="120" Height="30" Margin="0,0,8,0"/>
          <Button Name="RegenerateButton" Content="Regenerate" Width="120" Height="30" Margin="0,0,8,0"/>
          <Button Name="SaveFinalButton" Content="Save Final" Width="120" Height="30"/>
        </StackPanel>

        <!-- AI Response -->
        <TextBox Grid.Row="2" Name="AIResponseBox" IsReadOnly="True" TextWrapping="Wrap"
                 VerticalScrollBarVisibility="Auto" FontSize="11" Background="#F5F5F5"/>

        <!-- Settings -->
        <Expander Grid.Row="3" Header="Settings" Margin="0,8,0,0">
          <StackPanel Margin="8">
            <Grid>
              <Grid.ColumnDefinitions>
                <ColumnDefinition Width="Auto"/>
                <ColumnDefinition Width="*"/>
              </Grid.ColumnDefinitions>
              <Grid.RowDefinitions>
                <RowDefinition Height="Auto"/>
                <RowDefinition Height="Auto"/>
                <RowDefinition Height="Auto"/>
                <RowDefinition Height="Auto"/>
              </Grid.RowDefinitions>

              <TextBlock Grid.Row="0" Grid.Column="0" Text="Drawing:" Margin="0,4" VerticalAlignment="Center"/>
              <StackPanel Grid.Row="0" Grid.Column="1" Orientation="Horizontal" Margin="8,4">
                <TextBox Name="DrawingPathBox" Width="300" Margin="0,0,4,0"/>
                <Button Name="BrowseDrawingButton" Content="Browse..." Width="80"/>
              </StackPanel>

              <TextBlock Grid.Row="1" Grid.Column="0" Text="Tile Size:" Margin="0,4" VerticalAlignment="Center"/>
              <ComboBox Grid.Row="1" Grid.Column="1" Name="TileSizeCombo" Width="100" Margin="8,4" SelectedIndex="1">
                <ComboBoxItem Content="24 (Classic)"/>
                <ComboBoxItem Content="32 (Default)"/>
                <ComboBoxItem Content="48 (High-Res)"/>
              </ComboBox>

              <TextBlock Grid.Row="2" Grid.Column="0" Text="Ollama Model:" Margin="0,4" VerticalAlignment="Center"/>
              <TextBox Grid.Row="2" Grid.Column="1" Name="ModelBox" Width="200" Margin="8,4" Text="llama3.2"/>

              <TextBlock Grid.Row="3" Grid.Column="0" Text="Output Path:" Margin="0,4" VerticalAlignment="Center"/>
              <StackPanel Grid.Row="3" Grid.Column="1" Orientation="Horizontal" Margin="8,4">
                <TextBox Name="OutputPathBox" Width="300" Margin="0,0,4,0"/>
                <Button Name="BrowseOutputButton" Content="Browse..." Width="80"/>
              </StackPanel>
            </Grid>
          </StackPanel>
        </Expander>
      </Grid>
    </GroupBox>

    <!-- Status Bar -->
    <Border Grid.Row="2" Grid.ColumnSpan="2" Background="#E0E0E0" Padding="4" Margin="0,8,0,0">
      <TextBlock Name="StatusText" Text="Ready." FontWeight="Bold"/>
    </Border>

    <!-- Log -->
    <GroupBox Grid.Row="3" Grid.ColumnSpan="2" Header="Log" Margin="4,8,4,0">
      <TextBox Name="LogBox" AcceptsReturn="True" TextWrapping="Wrap"
               VerticalScrollBarVisibility="Auto" IsReadOnly="True"
               FontFamily="Consolas" FontSize="10" Background="Black" Foreground="Lime"/>
    </GroupBox>
  </Grid>
</Window>
"@

$reader = New-Object System.Xml.XmlNodeReader $xaml
$window = [Windows.Markup.XamlReader]::Load($reader)

# Get UI elements
$PreviewImage = $window.FindName("PreviewImage")
$PreviewPlaceholder = $window.FindName("PreviewPlaceholder")
$PromptBox = $window.FindName("PromptBox")
$SendPromptBtn = $window.FindName("SendPromptButton")
$BakeTileBtn = $window.FindName("BakeTileButton")
$RegenerateBtn = $window.FindName("RegenerateButton")
$SaveFinalBtn = $window.FindName("SaveFinalButton")
$StatusText = $window.FindName("StatusText")
$LogBox = $window.FindName("LogBox")
$AIResponseBox = $window.FindName("AIResponseBox")
$DrawingPathBox = $window.FindName("DrawingPathBox")
$BrowseDrawingBtn = $window.FindName("BrowseDrawingButton")
$TileSizeCombo = $window.FindName("TileSizeCombo")
$ModelBox = $window.FindName("ModelBox")
$OutputPathBox = $window.FindName("OutputPathBox")
$BrowseOutputBtn = $window.FindName("BrowseOutputButton")

# Initialize
if (-not [string]::IsNullOrWhiteSpace($DrawingPath)) {
    $DrawingPathBox.Text = $DrawingPath
}
$OutputPathBox.Text = Join-Path $PSScriptRoot "QudTiles"

# File watcher for preview updates
$fileWatcher = New-Object System.IO.FileSystemWatcher
$fileWatcher.Path = $script:TempDir
$fileWatcher.Filter = "*.png"
$fileWatcher.NotifyFilter = [System.IO.NotifyFilters]::FileName, [System.IO.NotifyFilters]::LastWrite
$fileWatcher.EnableRaisingEvents = $true

$fileWatcherAction = {
    param([System.IO.FileSystemEventArgs]$e)
    $filePath = $e.FullPath
    if (Test-Path $filePath -and $filePath -like "*.png") {
        Start-Sleep -Milliseconds 200  # Wait for file to be fully written
        Update-PreviewImage -ImagePath $filePath
        $window.Dispatcher.Invoke([action]{
            $PreviewPlaceholder.Visibility = "Collapsed"
        })
    }
}

$createdHandler = Register-ObjectEvent -InputObject $fileWatcher -EventName "Created" -Action $fileWatcherAction
$changedHandler = Register-ObjectEvent -InputObject $fileWatcher -EventName "Changed" -Action $fileWatcherAction

# ------------------------------------------------------------
# Event Handlers
# ------------------------------------------------------------

$BrowseDrawingBtn.Add_Click({
    $dialog = New-Object System.Windows.Forms.OpenFileDialog
    $dialog.Filter = "Image Files (*.png;*.jpg;*.jpeg)|*.png;*.jpg;*.jpeg|All Files (*.*)|*.*"
    $dialog.Title = "Select Line Drawing"
    
    if ($dialog.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) {
        $DrawingPathBox.Text = $dialog.FileName
        Write-Log "Selected drawing: $($dialog.FileName)"
    }
})

$BrowseOutputBtn.Add_Click({
    $dialog = New-Object System.Windows.Forms.FolderBrowserDialog
    $dialog.Description = "Select Output Directory"
    
    if ($dialog.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) {
        $OutputPathBox.Text = $dialog.SelectedPath
        Write-Log "Output directory: $($dialog.SelectedPath)"
    }
})

$SendPromptBtn.Add_Click({
    $prompt = $PromptBox.Text
    if ([string]::IsNullOrWhiteSpace($prompt)) {
        Write-Log "Error: Prompt is empty"
        return
    }
    
    $drawingPath = $DrawingPathBox.Text
    if (-not (Test-Path $drawingPath)) {
        Write-Log "Error: Drawing file not found: $drawingPath"
        Update-Status "Error: Drawing file not found"
        return
    }
    
    $script:OllamaModel = $ModelBox.Text
    if ([string]::IsNullOrWhiteSpace($script:OllamaModel)) {
        $script:OllamaModel = "llama3.2"
    }
    
    # Add to history
    $script:PromptHistory += $prompt
    
    # Run AI generation in background
    $job = Start-Job -ScriptBlock {
        param($prompt, $drawing, $model, $history, $scriptRoot)
        
        # Import functions
        . (Join-Path $scriptRoot "AssetMakerAI.ps1") -ErrorAction SilentlyContinue
        
        # Fallback Ollama function
        if (-not (Get-Command "Invoke-OllamaChat" -ErrorAction SilentlyContinue)) {
            $script:OllamaUrl = "http://localhost:11434"
            $script:OllamaApiUrl = "$script:OllamaUrl/api"
            
            function Test-OllamaRunning {
                try {
                    Invoke-RestMethod -Uri "$script:OllamaApiUrl/tags" -Method Get -TimeoutSec 2 -ErrorAction Stop | Out-Null
                    return $true
                }
                catch { return $false }
            }
            
            function Invoke-OllamaChat {
                param([string]$Prompt, [string]$ModelName, [hashtable]$SystemPrompt = @{})
                
                if (-not (Test-OllamaRunning)) { return $null }
                
                $systemMessage = if ($SystemPrompt.Count -gt 0) {
                    $SystemPrompt.Values | Select-Object -First 1
                } else {
                    "You are a helpful assistant."
                }
                
                $requestBody = @{
                    model = $ModelName
                    messages = @(
                        @{ role = "system"; content = $systemMessage },
                        @{ role = "user"; content = $Prompt }
                    )
                    stream = $false
                } | ConvertTo-Json -Depth 10
                
                try {
                    $response = Invoke-RestMethod -Uri "$script:OllamaApiUrl/chat" -Method Post -Body $requestBody -ContentType "application/json" -TimeoutSec 120
                    return $response.message.content.Trim()
                }
                catch {
                    return $null
                }
            }
        }
        
        # Generate spec
        $contextPrompt = "User Request: $prompt`nDrawing: $drawing`nPrevious: $($history -join '; ')"
        $response = Invoke-OllamaChat -Prompt $contextPrompt -ModelName $model -SystemPrompt @{
            System = "You are an expert procedural texture designer. Output ONLY valid JSON."
        }
        
        return @{
            Response = $response
            Success = $null -ne $response
        }
    } -ArgumentList $prompt, $drawingPath, $script:OllamaModel, ($script:PromptHistory[0..($script:PromptHistory.Count-2)]), $PSScriptRoot
    
    Write-Log "AI generation started (Job ID: $($job.Id))"
    Update-Status "Generating with AI..."
    $SendPromptBtn.IsEnabled = $false
    
    # Monitor job
    $timer = New-Object System.Windows.Threading.DispatcherTimer
    $timer.Interval = [TimeSpan]::FromMilliseconds(500)
    $timer.Add_Tick({
        if ($job.State -eq "Completed") {
            $timer.Stop()
            $result = Receive-Job $job
            Remove-Job $job
            
            $SendPromptBtn.IsEnabled = $true
            
            if ($result.Success) {
                $AIResponseBox.Text = $result.Response
                Write-Log "AI response received"
                
                # Extract and save JSON
                $jsonMatch = $result.Response -match '\{[\s\S]*\}'
                if ($jsonMatch) {
                    try {
                        $spec = $matches[0] | ConvertFrom-Json
                        $spec | ConvertTo-Json -Depth 10 | Set-Content -Path $script:CurrentSpecPath -Encoding UTF8
                        $script:CurrentSpec = $spec
                        Write-Log "Spec saved to: $script:CurrentSpecPath"
                        Update-Status "AI generation complete - Ready to bake"
                    }
                    catch {
                        Write-Log "Error parsing JSON: $_"
                        Update-Status "Error: Invalid JSON response"
                    }
                }
            } else {
                Write-Log "AI generation failed"
                Update-Status "Error: AI generation failed"
            }
        }
    })
    $timer.Start()
})

$BakeTileBtn.Add_Click({
    $drawingPath = $DrawingPathBox.Text
    if (-not (Test-Path $drawingPath)) {
        Write-Log "Error: Drawing file not found"
        Update-Status "Error: Drawing file not found"
        return
    }
    
    $tileSizeIndex = $TileSizeCombo.SelectedIndex
    $tileSize = @(24, 32, 48)[$tileSizeIndex]
    
    Write-Log "Starting tile bake..."
    Update-Status "Baking tile..."
    $BakeTileBtn.IsEnabled = $false
    
    # Run bake in background
    $job = Start-Job -ScriptBlock {
        param($drawing, $spec, $size, $output, $scriptRoot)
        
        $blenderExe = $null
        $commonPaths = @(
            "D:\tools\Blender Foundation",
            "${env:ProgramFiles}\Blender Foundation"
        )
        
        foreach ($basePath in $commonPaths) {
            if (Test-Path $basePath) {
                $blenderDirs = Get-ChildItem -LiteralPath $basePath -Directory -ErrorAction SilentlyContinue |
                    Where-Object { $_.Name -match '^Blender' } |
                    Sort-Object Name -Descending
                
                foreach ($dir in $blenderDirs) {
                    $blenderExe = Join-Path $dir.FullName "blender.exe"
                    if (Test-Path $blenderExe) {
                        break
                    }
                }
            }
            if ($blenderExe) { break }
        }
        
        if (-not $blenderExe) {
            $blender = Get-Command "blender" -ErrorAction SilentlyContinue
            if ($blender) {
                $blenderExe = $blender.Source
            }
        }
        
        if (-not $blenderExe) {
            return @{ Success = $false; Message = "Blender not found" }
        }
        
        $bakerScript = Join-Path $scriptRoot "qud_tile_baker.py"
        
        # Load spec
        $palette = "#ffffff,#000000"
        $style = "painterly"
        $quality = "standard"
        
        if (Test-Path $spec) {
            try {
                $specData = Get-Content $spec -Raw -Encoding UTF8 | ConvertFrom-Json
                if ($specData.material -and $specData.material.palette) {
                    $palette = ($specData.material.palette | ForEach-Object { $_.hex }) -join ","
                }
                if ($specData.material -and $specData.material.style) {
                    $style = $specData.material.style
                }
                if ($specData.material -and $specData.material.quality) {
                    $quality = $specData.material.quality
                }
            }
            catch { }
        }
        
        $blenderArgs = @(
            "--background",
            "--python", "`"$bakerScript`"",
            "--",
            "--drawing", "`"$drawing`"",
            "--size", $size,
            "--palette", "`"$palette`"",
            "--style", $style,
            "--quality", $quality,
            "--output", "`"$output`""
        )
        
        try {
            $process = Start-Process -FilePath $blenderExe -ArgumentList $blenderArgs -Wait -NoNewWindow -PassThru
            
            return @{
                Success = ($process.ExitCode -eq 0 -and (Test-Path $output))
                Message = if ($process.ExitCode -eq 0) { "Bake complete" } else { "Bake failed" }
            }
        }
        catch {
            return @{ Success = $false; Message = "Error: $_" }
        }
    } -ArgumentList $drawingPath, $script:CurrentSpecPath, $tileSize, $script:CurrentTilePath, $PSScriptRoot
    
    # Monitor job
    $timer = New-Object System.Windows.Threading.DispatcherTimer
    $timer.Interval = [TimeSpan]::FromMilliseconds(500)
    $timer.Add_Tick({
        if ($job.State -eq "Completed") {
            $timer.Stop()
            $result = Receive-Job $job
            Remove-Job $job
            
            $BakeTileBtn.IsEnabled = $true
            
            if ($result.Success) {
                Write-Log "Tile bake complete!"
                Update-Status "Tile baked successfully"
                Update-PreviewImage -ImagePath $script:CurrentTilePath
            } else {
                Write-Log "Bake failed: $($result.Message)"
                Update-Status "Error: Bake failed"
            }
        }
    })
    $timer.Start()
})

$RegenerateBtn.Add_Click({
    if ($script:PromptHistory.Count -gt 0) {
        $lastPrompt = $script:PromptHistory[-1]
        $PromptBox.Text = "$lastPrompt (refined)"
        $SendPromptBtn.RaiseEvent([System.Windows.RoutedEventArgs]::new([System.Windows.Controls.Button]::ClickEvent))
    } else {
        Write-Log "No previous prompt to regenerate"
    }
})

$SaveFinalBtn.Add_Click({
    if (-not (Test-Path $script:CurrentTilePath)) {
        Write-Log "Error: No tile to save"
        Update-Status "Error: No tile generated yet"
        return
    }
    
    $outputDir = $OutputPathBox.Text
    if (-not (Test-Path $outputDir)) {
        New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
    }
    
    $tileName = if (-not [string]::IsNullOrWhiteSpace($AssetId)) {
        $AssetId
    } else {
        "qud_tile_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
    }
    
    $finalPath = Join-Path $outputDir "$tileName.png"
    Copy-Item -Path $script:CurrentTilePath -Destination $finalPath -Force
    
    Write-Log "Tile saved to: $finalPath"
    Update-Status "Tile saved successfully"
})

# Initialize log
Write-Log "Qud Tile AI Generator started"
Write-Log "Temp directory: $script:TempDir"

if (Test-OllamaRunning) {
    Write-Log "Ollama is running"
    Update-Status "Ready - Ollama connected"
} else {
    Write-Log "Warning: Ollama is not running"
    Update-Status "Warning: Ollama not running"
}

# Show window
$window.ShowDialog() | Out-Null

# Cleanup
$fileWatcher.EnableRaisingEvents = $false
if ($createdHandler) { Unregister-Event -SourceIdentifier $createdHandler.Name -ErrorAction SilentlyContinue }
if ($changedHandler) { Unregister-Event -SourceIdentifier $changedHandler.Name -ErrorAction SilentlyContinue }
$fileWatcher.Dispose()
if (Test-Path $script:TempDir) {
    Remove-Item -LiteralPath $script:TempDir -Recurse -Force -ErrorAction SilentlyContinue
}


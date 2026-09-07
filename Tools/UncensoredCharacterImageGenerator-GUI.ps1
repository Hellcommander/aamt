# UncensoredCharacterImageGenerator-GUI.ps1
# AI-Assisted Modding Tools (AAMT)
# GUI version of the Uncensored Character Image Generator
# Provides a user-friendly interface for generating character images

# Force STA mode for GUI
if ([System.Threading.Thread]::CurrentThread.GetApartmentState() -ne [System.Threading.ApartmentState]::STA) {
    Write-Host "ERROR: Must run in STA mode for GUI" -ForegroundColor Red
    Write-Host "Run with: powershell -STA -File UncensoredCharacterImageGenerator-GUI.ps1" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

Add-Type -AssemblyName System.Windows.Forms, System.Drawing -ErrorAction Stop

$ErrorActionPreference = "Continue"
$PSScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
if ([string]::IsNullOrWhiteSpace($PSScriptRoot)) {
    $PSScriptRoot = $PWD.Path
}
$mainScript = Join-Path $PSScriptRoot "UncensoredCharacterImageGenerator.ps1"
if ([string]::IsNullOrWhiteSpace($mainScript) -or -not (Test-Path $mainScript)) {
    [System.Windows.Forms.MessageBox]::Show("Error: Main script not found at: $mainScript", "Error", "OK", "Error")
    exit 1
}

# ============================================================================
# GUI FORM
# ============================================================================

$form = New-Object System.Windows.Forms.Form
$form.Text = "Uncensored Character Image Generator"
$form.Size = New-Object System.Drawing.Size(900, 850)
$form.StartPosition = "CenterScreen"
$form.FormBorderStyle = "FixedDialog"
$form.MaximizeBox = $false
$form.MinimizeBox = $true

# ============================================================================
# CONTROLS
# ============================================================================

# Character Name
$lblCharacterName = New-Object System.Windows.Forms.Label
$lblCharacterName.Text = "Character Name:"
$lblCharacterName.Location = New-Object System.Drawing.Point(10, 10)
$lblCharacterName.Size = New-Object System.Drawing.Size(150, 20)
$form.Controls.Add($lblCharacterName)

$txtCharacterName = New-Object System.Windows.Forms.TextBox
$txtCharacterName.Location = New-Object System.Drawing.Point(170, 10)
$txtCharacterName.Size = New-Object System.Drawing.Size(300, 20)
$txtCharacterName.Text = "Character"
$form.Controls.Add($txtCharacterName)

# Game Type
$lblGameType = New-Object System.Windows.Forms.Label
$lblGameType.Text = "Game Type:"
$lblGameType.Location = New-Object System.Drawing.Point(10, 40)
$lblGameType.Size = New-Object System.Drawing.Size(150, 20)
$form.Controls.Add($lblGameType)

$cmbGameType = New-Object System.Windows.Forms.ComboBox
$cmbGameType.Location = New-Object System.Drawing.Point(170, 40)
$cmbGameType.Size = New-Object System.Drawing.Size(300, 20)
$cmbGameType.DropDownStyle = "DropDownList"
$cmbGameType.Items.AddRange(@("Generic", "RimWorld", "CDDA", "Qud", "Tome", "Elin"))
$cmbGameType.SelectedIndex = 0
$form.Controls.Add($cmbGameType)

# Description
$lblDescription = New-Object System.Windows.Forms.Label
$lblDescription.Text = "Character Description:"
$lblDescription.Location = New-Object System.Drawing.Point(10, 70)
$lblDescription.Size = New-Object System.Drawing.Size(200, 20)
$form.Controls.Add($lblDescription)

$txtDescription = New-Object System.Windows.Forms.TextBox
$txtDescription.Location = New-Object System.Drawing.Point(10, 95)
$txtDescription.Size = New-Object System.Drawing.Size(860, 150)
$txtDescription.Multiline = $true
$txtDescription.ScrollBars = "Vertical"
$txtDescription.Text = "A warm smile spreads over an old face freckled by time and a million crumbs of salt. He shrinks under a hunched back and drums the ground beneath him with a short and barb-crowned tail. A second pair of arms rise over the slump of his shoulders, where hands meet and fingers lace to form another face, this one vacant and prehistoric, no mouth and eyes desert-white."
$form.Controls.Add($txtDescription)

# Mutations
$lblMutations = New-Object System.Windows.Forms.Label
$lblMutations.Text = "Mutations (one per line):"
$lblMutations.Location = New-Object System.Drawing.Point(10, 255)
$lblMutations.Size = New-Object System.Drawing.Size(200, 20)
$form.Controls.Add($lblMutations)

$txtMutations = New-Object System.Windows.Forms.TextBox
$txtMutations.Location = New-Object System.Drawing.Point(10, 280)
$txtMutations.Size = New-Object System.Drawing.Size(420, 100)
$txtMutations.Multiline = $true
$txtMutations.ScrollBars = "Vertical"
$txtMutations.Text = "Multiple Arms"
$form.Controls.Add($txtMutations)

# Traits
$lblTraits = New-Object System.Windows.Forms.Label
$lblTraits.Text = "Traits (one per line):"
$lblTraits.Location = New-Object System.Drawing.Point(450, 255)
$lblTraits.Size = New-Object System.Drawing.Size(200, 20)
$form.Controls.Add($lblTraits)

$txtTraits = New-Object System.Windows.Forms.TextBox
$txtTraits.Location = New-Object System.Drawing.Point(450, 280)
$txtTraits.Size = New-Object System.Drawing.Size(420, 100)
$txtTraits.Multiline = $true
$txtTraits.ScrollBars = "Vertical"
$txtTraits.Text = "Hunched Back`nBarb-Crowned Tail`nHands Forming Face`nBody Horror"
$form.Controls.Add($txtTraits)

# Image Dimensions - Preset
$lblResolutionPreset = New-Object System.Windows.Forms.Label
$lblResolutionPreset.Text = "Resolution Preset:"
$lblResolutionPreset.Location = New-Object System.Drawing.Point(10, 390)
$lblResolutionPreset.Size = New-Object System.Drawing.Size(120, 20)
$form.Controls.Add($lblResolutionPreset)

$cmbResolutionPreset = New-Object System.Windows.Forms.ComboBox
$cmbResolutionPreset.Location = New-Object System.Drawing.Point(140, 390)
$cmbResolutionPreset.Size = New-Object System.Drawing.Size(200, 20)
$cmbResolutionPreset.DropDownStyle = "DropDownList"
$cmbResolutionPreset.Items.AddRange(@(
    # Small Square
    "512x512 (Square, Small)",
    "768x768 (Square, Medium)",
    "1024x1024 (Square, Standard)",
    # Standard Square
    "1536x1536 (Square, Large)",
    "2048x2048 (Square, Very Large)",
    "3072x3072 (Square, Ultra)",
    # Portrait Formats
    "1024x1536 (Portrait 2:3)",
    "1024x1792 (Portrait 9:16)",
    "1080x1920 (Portrait, Full HD)",
    "1440x2560 (Portrait, QHD)",
    "2160x3840 (Portrait, 4K UHD)",
    # Landscape Formats
    "1536x1024 (Landscape 3:2)",
    "1792x1024 (Landscape 16:9)",
    "1920x1080 (Landscape, Full HD / 1080p)",
    "2560x1440 (Landscape, QHD / 1440p)",
    "3840x2160 (Landscape, 4K UHD)",
    # Custom
    "Custom"
))
$cmbResolutionPreset.SelectedIndex = 2  # Default to 1024x1024
$form.Controls.Add($cmbResolutionPreset)

# Image Dimensions - Manual
$lblDimensions = New-Object System.Windows.Forms.Label
$lblDimensions.Text = "Custom Dimensions:"
$lblDimensions.Location = New-Object System.Drawing.Point(350, 390)
$lblDimensions.Size = New-Object System.Drawing.Size(120, 20)
$form.Controls.Add($lblDimensions)

$lblWidth = New-Object System.Windows.Forms.Label
$lblWidth.Text = "Width:"
$lblWidth.Location = New-Object System.Drawing.Point(480, 390)
$lblWidth.Size = New-Object System.Drawing.Size(50, 20)
$form.Controls.Add($lblWidth)

$numWidth = New-Object System.Windows.Forms.NumericUpDown
$numWidth.Location = New-Object System.Drawing.Point(535, 390)
$numWidth.Size = New-Object System.Drawing.Size(80, 20)
$numWidth.Minimum = 256
$numWidth.Maximum = 4096
$numWidth.Value = 1024
$numWidth.Increment = 64
$form.Controls.Add($numWidth)

$lblHeight = New-Object System.Windows.Forms.Label
$lblHeight.Text = "Height:"
$lblHeight.Location = New-Object System.Drawing.Point(625, 390)
$lblHeight.Size = New-Object System.Drawing.Size(50, 20)
$form.Controls.Add($lblHeight)

$numHeight = New-Object System.Windows.Forms.NumericUpDown
$numHeight.Location = New-Object System.Drawing.Point(680, 390)
$numHeight.Size = New-Object System.Drawing.Size(80, 20)
$numHeight.Minimum = 256
$numHeight.Maximum = 4096
$numHeight.Value = 1024
$numHeight.Increment = 64
$form.Controls.Add($numHeight)

# Note about high resolutions
$lblResolutionNote = New-Object System.Windows.Forms.Label
$lblResolutionNote.Text = "Note: 4K and large resolutions require significant VRAM and time"
$lblResolutionNote.Location = New-Object System.Drawing.Point(10, 415)
$lblResolutionNote.Size = New-Object System.Drawing.Size(500, 15)
$lblResolutionNote.ForeColor = [System.Drawing.Color]::Gray
$lblResolutionNote.Font = New-Object System.Drawing.Font($lblResolutionNote.Font.FontFamily, 8)
$form.Controls.Add($lblResolutionNote)

# Options
$chkSkipEnhancement = New-Object System.Windows.Forms.CheckBox
$chkSkipEnhancement.Text = "Skip Ollama Enhancement (use raw description)"
$chkSkipEnhancement.Location = New-Object System.Drawing.Point(10, 435)
$chkSkipEnhancement.Size = New-Object System.Drawing.Size(400, 20)
$chkSkipEnhancement.Checked = $false
$form.Controls.Add($chkSkipEnhancement)

$chkAIEnhancement = New-Object System.Windows.Forms.CheckBox
$chkAIEnhancement.Text = "AI Image Enhancement (analyze and improve generated image)"
$chkAIEnhancement.Location = New-Object System.Drawing.Point(10, 460)
$chkAIEnhancement.Size = New-Object System.Drawing.Size(400, 20)
$chkAIEnhancement.Checked = $false
$form.Controls.Add($chkAIEnhancement)

$chkRegenerateImproved = New-Object System.Windows.Forms.CheckBox
$chkRegenerateImproved.Text = "Regenerate with AI improvements (creates improved version)"
$chkRegenerateImproved.Location = New-Object System.Drawing.Point(420, 460)
$chkRegenerateImproved.Size = New-Object System.Drawing.Size(400, 20)
$chkRegenerateImproved.Checked = $false
$chkRegenerateImproved.Enabled = $false  # Enabled when AIEnhancement is checked
$form.Controls.Add($chkRegenerateImproved)

$chkVerbose = New-Object System.Windows.Forms.CheckBox
$chkVerbose.Text = "Verbose Output"
$chkVerbose.Location = New-Object System.Drawing.Point(10, 485)
$chkVerbose.Size = New-Object System.Drawing.Size(200, 20)
$chkVerbose.Checked = $false
$form.Controls.Add($chkVerbose)

# API URLs
$lblOllamaUrl = New-Object System.Windows.Forms.Label
$lblOllamaUrl.Text = "Ollama URL:"
$lblOllamaUrl.Location = New-Object System.Drawing.Point(10, 510)
$lblOllamaUrl.Size = New-Object System.Drawing.Size(100, 20)
$form.Controls.Add($lblOllamaUrl)

$txtOllamaUrl = New-Object System.Windows.Forms.TextBox
$txtOllamaUrl.Location = New-Object System.Drawing.Point(120, 510)
$txtOllamaUrl.Size = New-Object System.Drawing.Size(200, 20)
$txtOllamaUrl.Text = "http://localhost:11434"
$form.Controls.Add($txtOllamaUrl)

$lblStableDiffusionUrl = New-Object System.Windows.Forms.Label
$lblStableDiffusionUrl.Text = "Stable Diffusion URL:"
$lblStableDiffusionUrl.Location = New-Object System.Drawing.Point(330, 510)
$lblStableDiffusionUrl.Size = New-Object System.Drawing.Size(150, 20)
$form.Controls.Add($lblStableDiffusionUrl)

$txtStableDiffusionUrl = New-Object System.Windows.Forms.TextBox
$txtStableDiffusionUrl.Location = New-Object System.Drawing.Point(490, 510)
$txtStableDiffusionUrl.Size = New-Object System.Drawing.Size(200, 20)
$txtStableDiffusionUrl.Text = "http://localhost:8000"
$form.Controls.Add($txtStableDiffusionUrl)

# Output Path
$lblOutputPath = New-Object System.Windows.Forms.Label
$lblOutputPath.Text = "Output Path (leave empty for auto):"
$lblOutputPath.Location = New-Object System.Drawing.Point(10, 540)
$lblOutputPath.Size = New-Object System.Drawing.Size(200, 20)
$form.Controls.Add($lblOutputPath)

$txtOutputPath = New-Object System.Windows.Forms.TextBox
$txtOutputPath.Location = New-Object System.Drawing.Point(10, 565)
$txtOutputPath.Size = New-Object System.Drawing.Size(700, 20)
$txtOutputPath.Text = ""
$form.Controls.Add($txtOutputPath)

$btnBrowseOutput = New-Object System.Windows.Forms.Button
$btnBrowseOutput.Text = "Browse..."
$btnBrowseOutput.Location = New-Object System.Drawing.Point(720, 563)
$btnBrowseOutput.Size = New-Object System.Drawing.Size(75, 25)
$form.Controls.Add($btnBrowseOutput)

# Status/Output
$lblStatus = New-Object System.Windows.Forms.Label
$lblStatus.Text = "Status: Ready"
$lblStatus.Location = New-Object System.Drawing.Point(10, 595)
$lblStatus.Size = New-Object System.Drawing.Size(400, 20)
$lblStatus.ForeColor = [System.Drawing.Color]::Green
$form.Controls.Add($lblStatus)

$txtOutput = New-Object System.Windows.Forms.TextBox
$txtOutput.Location = New-Object System.Drawing.Point(10, 620)
$txtOutput.Size = New-Object System.Drawing.Size(860, 150)
$txtOutput.Multiline = $true
$txtOutput.ScrollBars = "Both"
$txtOutput.ReadOnly = $true
$txtOutput.Font = New-Object System.Drawing.Font("Consolas", 9)
$form.Controls.Add($txtOutput)

# Buttons
$btnGenerate = New-Object System.Windows.Forms.Button
$btnGenerate.Text = "Generate Image"
$btnGenerate.Location = New-Object System.Drawing.Point(10, 780)
$btnGenerate.Size = New-Object System.Drawing.Size(150, 35)
$btnGenerate.BackColor = [System.Drawing.Color]::LightGreen
$form.Controls.Add($btnGenerate)

$btnClear = New-Object System.Windows.Forms.Button
$btnClear.Text = "Clear Output"
$btnClear.Location = New-Object System.Drawing.Point(170, 765)
$btnClear.Size = New-Object System.Drawing.Size(100, 35)
$form.Controls.Add($btnClear)

$btnClose = New-Object System.Windows.Forms.Button
$btnClose.Text = "Close"
$btnClose.Location = New-Object System.Drawing.Point(800, 765)
$btnClose.Size = New-Object System.Drawing.Size(70, 35)
$form.Controls.Add($btnClose)

# ============================================================================
# FUNCTIONS
# ============================================================================

function Add-Output {
    param([string]$Message, [string]$Color = "Black")
    $txtOutput.AppendText("$Message`r`n")
    $txtOutput.SelectionStart = $txtOutput.Text.Length
    $txtOutput.ScrollToCaret()
    $form.Update()
}

function Update-Status {
    param([string]$Message, [string]$Color = "Green")
    $lblStatus.Text = "Status: $Message"
    $lblStatus.ForeColor = [System.Drawing.Color]::$Color
    $form.Update()
}

function Invoke-GenerateImage {
    # Clear output
    $txtOutput.Clear()
    Update-Status "Generating..." "Blue"
    
    # Get values from form
    $characterName = $txtCharacterName.Text.Trim()
    $gameType = $cmbGameType.SelectedItem.ToString()
    # Use Set-Variable to avoid conflict with optimized Description parameter from loaded functions
    Set-Variable -Name "description" -Value $txtDescription.Text.Trim() -Scope Local -Force
    
    if ([string]::IsNullOrWhiteSpace($description)) {
        [System.Windows.Forms.MessageBox]::Show("Please enter a character description.", "Error", "OK", "Error")
        Update-Status "Error: No description" "Red"
        return
    }
    
    # Parse mutations
    $mutations = @()
    if (-not [string]::IsNullOrWhiteSpace($txtMutations.Text)) {
        $mutations = $txtMutations.Text -split "`r?`n" | Where-Object { $_.Trim() -ne "" } | ForEach-Object { $_.Trim() }
    }
    
    # Parse traits
    $traits = @()
    if (-not [string]::IsNullOrWhiteSpace($txtTraits.Text)) {
        $traits = $txtTraits.Text -split "`r?`n" | Where-Object { $_.Trim() -ne "" } | ForEach-Object { $_.Trim() }
    }
    
    $width = [int]$numWidth.Value
    $height = [int]$numHeight.Value
    $ollamaUrl = $txtOllamaUrl.Text.Trim()
    $stableDiffusionUrl = $txtStableDiffusionUrl.Text.Trim()
    $outputPath = $txtOutputPath.Text.Trim()
    $skipEnhancement = $chkSkipEnhancement.Checked
    $aiEnhancement = $chkAIEnhancement.Checked
    $regenerateImproved = $chkRegenerateImproved.Checked
    $verbose = $chkVerbose.Checked
    
    Add-Output "=== Starting Image Generation ==="
    Add-Output "Character: $characterName"
    Add-Output "Game Type: $gameType"
    Add-Output "Mutations: $($mutations.Count)"
    if ($mutations.Count -gt 0) {
        Add-Output "  - $($mutations -join ', ')"
    }
    Add-Output "Traits: $($traits.Count)"
    if ($traits.Count -gt 0) {
        Add-Output "  - $($traits -join ', ')"
    }
    Add-Output "Dimensions: ${width}x${height}"
    Add-Output ""
    
    # Disable generate button
    $btnGenerate.Enabled = $false
    $form.Update()
    
    try {
        # Import shared modules first
        $sharedPath = Join-Path $PSScriptRoot "Shared"
        $ollamaModule = Join-Path $sharedPath "OllamaIntegration.psm1"
        if (Test-Path $ollamaModule) {
            Import-Module $ollamaModule -Force -ErrorAction SilentlyContinue
            Add-Output "Loaded Ollama integration module"
        }
        
        # Dot-source the main script to get functions (but skip execution)
        Add-Output "Loading functions from main script..."
        if ([string]::IsNullOrWhiteSpace($mainScript) -or -not (Test-Path $mainScript)) {
            throw "Main script not found: $mainScript"
        }
        $scriptContent = Get-Content -Path $mainScript -Raw -ErrorAction Stop
        
        # Remove the main execution section
        $mainExecutionPattern = '(?s)# ============================================================\s*# MAIN EXECUTION.*$'
        $functionSection = $scriptContent -replace $mainExecutionPattern, ''
        
        # Execute just the function definitions
        Invoke-Expression $functionSection
        
        Add-Output "Functions loaded"
        Add-Output ""
        
        # Build full description
        Add-Output "Building character description..."
        $fullDescription = Build-CharacterDescription `
            -BaseDescription $description `
            -Mutations $mutations `
            -Traits $traits `
            -GameType $gameType
        
        Add-Output "Base description built"
        
        # Enhance with Ollama (unless skipped)
        if (-not $skipEnhancement) {
            Add-Output "Enhancing description with Ollama..."
            $enhancedDescription = Enhance-DescriptionWithOllama `
                -Description $fullDescription `
                -CharacterName $characterName `
                -GameType $gameType
            Add-Output "Description enhanced"
        } else {
            $enhancedDescription = $fullDescription
            Add-Output "Skipping Ollama enhancement (using raw description)"
        }
        
        # Determine output path
        if ([string]::IsNullOrWhiteSpace($outputPath)) {
            $safeName = $characterName -replace '[^\w\s-]', '' -replace '\s+', '_'
            $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
            $outputPath = Join-Path $PSScriptRoot "generated_${safeName}_${timestamp}.png"
        }
        
        # Ensure output directory exists
        if ([string]::IsNullOrWhiteSpace($outputPath)) {
            throw "Output path cannot be empty"
        }
        $outputDir = Split-Path -Parent $outputPath
        if ([string]::IsNullOrWhiteSpace($outputDir)) {
            $outputDir = $PSScriptRoot
            $outputPath = Join-Path $outputDir (Split-Path -Leaf $outputPath)
        }
        if ([string]::IsNullOrWhiteSpace($outputDir)) {
            $outputDir = $PWD.Path
            $outputPath = Join-Path $outputDir (Split-Path -Leaf $outputPath)
        }
        if (-not (Test-Path -Path $outputDir)) {
            New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
        }
        
        Add-Output "Output path: $outputPath"
        Add-Output ""
        
        # Generate image
        Add-Output "Generating image with Stable Diffusion..."
        $imagePath = Generate-ImageWithStableDiffusion `
            -Prompt $enhancedDescription `
            -Width $width `
            -Height $height `
            -ApiUrl $stableDiffusionUrl `
            -OutputPath $outputPath
        
        Add-Output ""
        Add-Output "Image generated successfully!"
        Add-Output "  Output: $imagePath"
        
        # AI Enhancement (if requested)
        if ($aiEnhancement) {
            Add-Output ""
            Add-Output "=== AI Image Enhancement ==="
            $enhancedImagePath = Enhance-ImageWithAI `
                -ImagePath $imagePath `
                -OriginalPrompt $enhancedDescription `
                -CharacterName $characterName `
                -GameType $gameType `
                -Width $width `
                -Height $height `
                -OllamaUrl $ollamaUrl `
                -StableDiffusionUrl $stableDiffusionUrl `
                -RegenerateImproved:$regenerateImproved `
                -Verbose:$verbose
            
            if ($enhancedImagePath -ne $imagePath) {
                $imagePath = $enhancedImagePath
                Add-Output "  Using AI-enhanced image: $imagePath"
            }
        }
        
        # Save metadata
        if ([string]::IsNullOrWhiteSpace($outputPath)) {
            throw "Cannot save metadata: output path is empty"
        }
        $metadataPath = $outputPath -replace '\.png$', '_metadata.json'
        if ([string]::IsNullOrWhiteSpace($metadataPath)) {
            $metadataPath = Join-Path (Split-Path -Parent $outputPath) "$(Split-Path -LeafBase $outputPath)_metadata.json"
        }
        $metadata = @{
            CharacterName = $characterName
            GameType = $gameType
            Mutations = $mutations
            Traits = $traits
            OriginalDescription = $description
            EnhancedDescription = $enhancedDescription
            Dimensions = @{
                Width = $width
                Height = $height
            }
            GeneratedAt = (Get-Date -Format "yyyy-MM-dd HH:mm:ss")
            AIEnhanced = $aiEnhancement
            Regenerated = $regenerateImproved
            Notes = 'Generated with uncensored routing system - handles any content that might be blocked'
        }
        $metadata | ConvertTo-Json -Depth 10 | Set-Content -Path $metadataPath -Encoding UTF8
        Add-Output "  Metadata: $metadataPath"
        
        Add-Output ""
        Add-Output "=== Generation Complete ==="
        Update-Status "Success!" "Green"
        $successMsg = "Image generated successfully!`n`nOutput: $imagePath"
        [System.Windows.Forms.MessageBox]::Show($successMsg, "Success", "OK", "Information")
    } catch {
        $errorMsg = $_.Exception.Message
        Add-Output ""
        Add-Output "ERROR: $errorMsg"
        if ($_.Exception.InnerException) {
            Add-Output "Inner Exception: $($_.Exception.InnerException.Message)"
        }
        Add-Output ""
        Add-Output "Stack Trace:"
        Add-Output $_.ScriptStackTrace
        Update-Status "Error: $errorMsg" "Red"
        [System.Windows.Forms.MessageBox]::Show("Error: $errorMsg", "Error", "OK", "Error")
    } finally {
        $btnGenerate.Enabled = $true
    }
}

# ============================================================================
# EVENT HANDLERS
# ============================================================================

$btnGenerate.Add_Click({
    Invoke-GenerateImage
})

$btnClear.Add_Click({
    $txtOutput.Clear()
    Update-Status "Ready" "Green"
})

$btnBrowseOutput.Add_Click({
    $saveDialog = New-Object System.Windows.Forms.SaveFileDialog
    $saveDialog.Filter = "PNG Files (*.png)|*.png|All Files (*.*)|*.*"
    $saveDialog.Title = "Save Image As..."
    if ($saveDialog.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) {
        $txtOutputPath.Text = $saveDialog.FileName
    }
})

$btnClose.Add_Click({
    $form.Close()
})

# Resolution preset change handler
$cmbResolutionPreset.Add_SelectedIndexChanged({
    $preset = $cmbResolutionPreset.SelectedItem.ToString()
    if ($preset -ne "Custom") {
        # Parse preset format: 1024x1024 with optional description in parentheses
        if ($preset -match '(\d+)x(\d+)') {
            $width = [int]$matches[1]
            $height = [int]$matches[2]
            $numWidth.Value = $width
            $numHeight.Value = $height
        }
    }
})

# AI Enhancement checkbox handler (enable/disable regenerate option)
$chkAIEnhancement.Add_CheckedChanged({
    $chkRegenerateImproved.Enabled = $chkAIEnhancement.Checked
})

# ============================================================================
# SHOW FORM
# ============================================================================

Add-Output "Uncensored Character Image Generator - GUI"
Add-Output "Ready to generate images..."
Add-Output ""

[System.Windows.Forms.Application]::EnableVisualStyles()
[void]$form.ShowDialog()

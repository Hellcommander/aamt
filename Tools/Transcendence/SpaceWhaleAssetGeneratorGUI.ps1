<#
.SYNOPSIS
    Space Whale Asset Generator GUI
    User-friendly interface for SD3 texture generation and quality asset generation
    
.DESCRIPTION
    Provides a graphical interface with:
    - Toggleable options for all features
    - Dropdown menus for texture types, modes, etc.
    - Image preview for last completed asset
    - Progress tracking
    - Settings persistence
#>

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

# ============================================================
# CONFIGURATION
# ============================================================

$script:ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$script:SettingsFile = Join-Path $script:ScriptDir "SpaceWhaleAssetGeneratorGUI_Settings.json"
$script:LastImagePath = $null
$script:GenerationRunning = $false
$script:WarningCount = 0
$script:ErrorCount = 0
$script:CurrentStage = ""
$script:TotalStages = 0
$script:CompletedStages = 0
$script:LastOutputLength = 0

# ============================================================
# SETTINGS MANAGEMENT
# ============================================================

function Load-Settings {
    if (Test-Path $script:SettingsFile) {
        try {
            $settings = Get-Content $script:SettingsFile -Raw | ConvertFrom-Json
            return $settings
        } catch {
            Write-Host "Failed to load settings: $_" -ForegroundColor Yellow
        }
    }
    
    # Default settings
    return @{
        outputDir = "Output\SpaceWhaleAssets_HQ"
        shipRegistry = "space_whale_ship_example.json"
        visualRegistry = "space_whale_visual_language_registry.json"
        draftCount = 6
        refineCount = 3
        finalCount = 2
        enableRefinement = $true
        useSd3 = $true  # SD3 enabled by default, auto-detects required assets
        sd3TextureType = "all"
        sd3Variations = 3
        sd3Fast = $false
        shipId = ""
        quickMode = $false
        skipDraft = $false
        skipAssess = $false
        skipRefine = $false
        skipSelect = $false
        skipIntegrate = $false
        skipSpritesheet = $false
        skipItems = $false
        resume = $false
        skipCompleted = $false
        lastImageDir = ""
    }
}

function Save-Settings {
    param([hashtable]$Settings)
    
    try {
        $Settings | ConvertTo-Json -Depth 10 | Out-File $script:SettingsFile -Encoding UTF8
    } catch {
        [System.Windows.Forms.MessageBox]::Show(
            "Failed to save settings: $_",
            "Settings Error",
            [System.Windows.Forms.MessageBoxButtons]::OK,
            [System.Windows.Forms.MessageBoxIcon]::Warning
        )
    }
}

# ============================================================
# GUI CREATION
# ============================================================

function Create-MainForm {
    $settings = Load-Settings
    
    # Create main form
    $form = New-Object System.Windows.Forms.Form
    $form.Text = "Space Whale Asset Generator"
    $form.Size = New-Object System.Drawing.Size(900, 950)
    $form.StartPosition = "CenterScreen"
    $form.FormBorderStyle = "FixedDialog"
    $form.MaximizeBox = $false
    $form.BackColor = [System.Drawing.Color]::FromArgb(30, 30, 30)
    $form.ForeColor = [System.Drawing.Color]::White
    
    $yPos = 20
    
    # Title
    $titleLabel = New-Object System.Windows.Forms.Label
    $titleLabel.Location = New-Object System.Drawing.Point(20, $yPos)
    $titleLabel.Size = New-Object System.Drawing.Size(860, 30)
    $titleLabel.Text = "Space Whale Asset Generator - Control Panel"
    $titleLabel.Font = New-Object System.Drawing.Font("Segoe UI", 14, [System.Drawing.FontStyle]::Bold)
    $titleLabel.ForeColor = [System.Drawing.Color]::Cyan
    $form.Controls.Add($titleLabel)
    
    $yPos += 50
    
    # ============================================================
    # GENERATOR MODE SELECTION
    # ============================================================
    
    $modeGroupBox = New-Object System.Windows.Forms.GroupBox
    $modeGroupBox.Location = New-Object System.Drawing.Point(20, $yPos)
    $modeGroupBox.Size = New-Object System.Drawing.Size(420, 100)
    $modeGroupBox.Text = "Generator Mode"
    $modeGroupBox.ForeColor = [System.Drawing.Color]::Cyan
    $form.Controls.Add($modeGroupBox)
    
    $qualityRadio = New-Object System.Windows.Forms.RadioButton
    $qualityRadio.Location = New-Object System.Drawing.Point(20, 25)
    $qualityRadio.Size = New-Object System.Drawing.Size(380, 30)
    $qualityRadio.Text = "Quality Asset Generator (Multi-stage pipeline, fewer high-quality assets)"
    $qualityRadio.Checked = $true
    $qualityRadio.ForeColor = [System.Drawing.Color]::White
    $modeGroupBox.Controls.Add($qualityRadio)
    
    $sd3Radio = New-Object System.Windows.Forms.RadioButton
    $sd3Radio.Location = New-Object System.Drawing.Point(20, 60)
    $sd3Radio.Size = New-Object System.Drawing.Size(380, 30)
    $sd3Radio.Text = "SD3 Texture Generator (Creative textures and design drafts only)"
    $sd3Radio.ForeColor = [System.Drawing.Color]::White
    $modeGroupBox.Controls.Add($sd3Radio)
    
    # ============================================================
    # IMAGE PREVIEW
    # ============================================================
    
    $previewGroupBox = New-Object System.Windows.Forms.GroupBox
    $previewGroupBox.Location = New-Object System.Drawing.Point(460, $yPos)
    $previewGroupBox.Size = New-Object System.Drawing.Size(400, 300)
    $previewGroupBox.Text = "Last Generated Asset Preview"
    $previewGroupBox.ForeColor = [System.Drawing.Color]::Cyan
    $form.Controls.Add($previewGroupBox)
    
    $previewBox = New-Object System.Windows.Forms.PictureBox
    $previewBox.Location = New-Object System.Drawing.Point(10, 25)
    $previewBox.Size = New-Object System.Drawing.Size(380, 240)
    $previewBox.BorderStyle = "FixedSingle"
    $previewBox.BackColor = [System.Drawing.Color]::Black
    $previewBox.SizeMode = "Zoom"
    $previewGroupBox.Controls.Add($previewBox)
    
    $previewLabel = New-Object System.Windows.Forms.Label
    $previewLabel.Location = New-Object System.Drawing.Point(10, 270)
    $previewLabel.Size = New-Object System.Drawing.Size(380, 20)
    $previewLabel.Text = "No image generated yet"
    $previewLabel.ForeColor = [System.Drawing.Color]::Gray
    $previewLabel.TextAlign = "MiddleCenter"
    $previewGroupBox.Controls.Add($previewLabel)
    
    $yPos += 110
    
    # ============================================================
    # BASIC SETTINGS
    # ============================================================
    
    $basicGroupBox = New-Object System.Windows.Forms.GroupBox
    $basicGroupBox.Location = New-Object System.Drawing.Point(20, $yPos)
    $basicGroupBox.Size = New-Object System.Drawing.Size(420, 180)
    $basicGroupBox.Text = "Basic Settings"
    $basicGroupBox.ForeColor = [System.Drawing.Color]::Cyan
    $form.Controls.Add($basicGroupBox)
    
    # Output Directory
    $outputLabel = New-Object System.Windows.Forms.Label
    $outputLabel.Location = New-Object System.Drawing.Point(10, 25)
    $outputLabel.Size = New-Object System.Drawing.Size(100, 20)
    $outputLabel.Text = "Output Directory:"
    $outputLabel.ForeColor = [System.Drawing.Color]::White
    $basicGroupBox.Controls.Add($outputLabel)
    
    $outputTextBox = New-Object System.Windows.Forms.TextBox
    $outputTextBox.Location = New-Object System.Drawing.Point(120, 25)
    $outputTextBox.Size = New-Object System.Drawing.Size(210, 20)
    $outputTextBox.Text = $settings.outputDir
    $outputTextBox.BackColor = [System.Drawing.Color]::FromArgb(50, 50, 50)
    $outputTextBox.ForeColor = [System.Drawing.Color]::White
    $basicGroupBox.Controls.Add($outputTextBox)
    
    $outputBrowseBtn = New-Object System.Windows.Forms.Button
    $outputBrowseBtn.Location = New-Object System.Drawing.Point(340, 23)
    $outputBrowseBtn.Size = New-Object System.Drawing.Size(60, 25)
    $outputBrowseBtn.Text = "Browse"
    $outputBrowseBtn.BackColor = [System.Drawing.Color]::FromArgb(60, 60, 60)
    $outputBrowseBtn.ForeColor = [System.Drawing.Color]::White
    $outputBrowseBtn.FlatStyle = "Flat"
    $basicGroupBox.Controls.Add($outputBrowseBtn)
    
    $outputBrowseBtn.Add_Click({
        $folderBrowser = New-Object System.Windows.Forms.FolderBrowserDialog
        $folderBrowser.SelectedPath = $outputTextBox.Text
        if ($folderBrowser.ShowDialog() -eq "OK") {
            $outputTextBox.Text = $folderBrowser.SelectedPath
        }
    })
    
    # Ship ID
    $shipIdLabel = New-Object System.Windows.Forms.Label
    $shipIdLabel.Location = New-Object System.Drawing.Point(10, 60)
    $shipIdLabel.Size = New-Object System.Drawing.Size(100, 20)
    $shipIdLabel.Text = "Ship ID Filter:"
    $shipIdLabel.ForeColor = [System.Drawing.Color]::White
    $basicGroupBox.Controls.Add($shipIdLabel)
    
    $shipIdCombo = New-Object System.Windows.Forms.ComboBox
    $shipIdCombo.Location = New-Object System.Drawing.Point(120, 60)
    $shipIdCombo.Size = New-Object System.Drawing.Size(280, 20)
    $shipIdCombo.DropDownStyle = "DropDown"
    $shipIdCombo.BackColor = [System.Drawing.Color]::FromArgb(50, 50, 50)
    $shipIdCombo.ForeColor = [System.Drawing.Color]::White
    $shipIdCombo.Items.AddRange(@("(All Ships)", "leviathan_alpha", "serpent_void"))
    $shipIdCombo.SelectedIndex = 0
    if ($settings.shipId) {
        $shipIdCombo.Text = $settings.shipId
    }
    $basicGroupBox.Controls.Add($shipIdCombo)
    
    # Draft Count
    $draftLabel = New-Object System.Windows.Forms.Label
    $draftLabel.Location = New-Object System.Drawing.Point(10, 95)
    $draftLabel.Size = New-Object System.Drawing.Size(100, 20)
    $draftLabel.Text = "Draft Count:"
    $draftLabel.ForeColor = [System.Drawing.Color]::White
    $basicGroupBox.Controls.Add($draftLabel)
    
    $draftNumeric = New-Object System.Windows.Forms.NumericUpDown
    $draftNumeric.Location = New-Object System.Drawing.Point(120, 95)
    $draftNumeric.Size = New-Object System.Drawing.Size(80, 20)
    $draftNumeric.Minimum = 1
    $draftNumeric.Maximum = 20
    $draftNumeric.Value = $settings.draftCount
    $draftNumeric.BackColor = [System.Drawing.Color]::FromArgb(50, 50, 50)
    $draftNumeric.ForeColor = [System.Drawing.Color]::White
    $basicGroupBox.Controls.Add($draftNumeric)
    
    # Final Count
    $finalLabel = New-Object System.Windows.Forms.Label
    $finalLabel.Location = New-Object System.Drawing.Point(220, 95)
    $finalLabel.Size = New-Object System.Drawing.Size(80, 20)
    $finalLabel.Text = "Final Count:"
    $finalLabel.ForeColor = [System.Drawing.Color]::White
    $basicGroupBox.Controls.Add($finalLabel)
    
    $finalNumeric = New-Object System.Windows.Forms.NumericUpDown
    $finalNumeric.Location = New-Object System.Drawing.Point(310, 95)
    $finalNumeric.Size = New-Object System.Drawing.Size(80, 20)
    $finalNumeric.Minimum = 1
    $finalNumeric.Maximum = 10
    $finalNumeric.Value = $settings.finalCount
    $finalNumeric.BackColor = [System.Drawing.Color]::FromArgb(50, 50, 50)
    $finalNumeric.ForeColor = [System.Drawing.Color]::White
    $basicGroupBox.Controls.Add($finalNumeric)
    
    # Quick Mode
    $quickCheckBox = New-Object System.Windows.Forms.CheckBox
    $quickCheckBox.Location = New-Object System.Drawing.Point(10, 130)
    $quickCheckBox.Size = New-Object System.Drawing.Size(150, 30)
    $quickCheckBox.Text = "Quick Mode"
    $quickCheckBox.Checked = $settings.quickMode
    $quickCheckBox.ForeColor = [System.Drawing.Color]::White
    $basicGroupBox.Controls.Add($quickCheckBox)
    
    # Refinement Enabled
    $refineCheckBox = New-Object System.Windows.Forms.CheckBox
    $refineCheckBox.Location = New-Object System.Drawing.Point(170, 130)
    $refineCheckBox.Size = New-Object System.Drawing.Size(150, 30)
    $refineCheckBox.Text = "Enable Refinement"
    $refineCheckBox.Checked = $settings.enableRefinement
    $refineCheckBox.ForeColor = [System.Drawing.Color]::White
    $basicGroupBox.Controls.Add($refineCheckBox)
    
    $yPos += 190
    
    # ============================================================
    # SD3 SETTINGS
    # ============================================================
    
    $sd3GroupBox = New-Object System.Windows.Forms.GroupBox
    $sd3GroupBox.Location = New-Object System.Drawing.Point(20, $yPos)
    $sd3GroupBox.Size = New-Object System.Drawing.Size(420, 180)
    $sd3GroupBox.Text = "SD3 Texture Generation"
    $sd3GroupBox.ForeColor = [System.Drawing.Color]::Cyan
    $form.Controls.Add($sd3GroupBox)
    
    # Enable SD3 (enabled by default, auto-detects required assets)
    $sd3EnableCheckBox = New-Object System.Windows.Forms.CheckBox
    $sd3EnableCheckBox.Location = New-Object System.Drawing.Point(10, 25)
    $sd3EnableCheckBox.Size = New-Object System.Drawing.Size(200, 30)
    $sd3EnableCheckBox.Text = "SD3 Textures (Auto-enabled)"
    $sd3EnableCheckBox.Checked = $settings.useSd3
    $sd3EnableCheckBox.ForeColor = [System.Drawing.Color]::White
    $sd3GroupBox.Controls.Add($sd3EnableCheckBox)
    
    # SD3 Fast Mode
    $sd3FastCheckBox = New-Object System.Windows.Forms.CheckBox
    $sd3FastCheckBox.Location = New-Object System.Drawing.Point(170, 25)
    $sd3FastCheckBox.Size = New-Object System.Drawing.Size(200, 30)
    $sd3FastCheckBox.Text = "Fast Mode (skip design drafts)"
    $sd3FastCheckBox.Checked = $settings.sd3Fast
    $sd3FastCheckBox.ForeColor = [System.Drawing.Color]::White
    $sd3GroupBox.Controls.Add($sd3FastCheckBox)
    
    # SD3 Texture Type
    $sd3TypeLabel = New-Object System.Windows.Forms.Label
    $sd3TypeLabel.Location = New-Object System.Drawing.Point(10, 65)
    $sd3TypeLabel.Size = New-Object System.Drawing.Size(100, 20)
    $sd3TypeLabel.Text = "Texture Type:"
    $sd3TypeLabel.ForeColor = [System.Drawing.Color]::White
    $sd3GroupBox.Controls.Add($sd3TypeLabel)
    
    $sd3TypeCombo = New-Object System.Windows.Forms.ComboBox
    $sd3TypeCombo.Location = New-Object System.Drawing.Point(120, 65)
    $sd3TypeCombo.Size = New-Object System.Drawing.Size(280, 20)
    $sd3TypeCombo.DropDownStyle = "DropDownList"
    $sd3TypeCombo.BackColor = [System.Drawing.Color]::FromArgb(50, 50, 50)
    $sd3TypeCombo.ForeColor = [System.Drawing.Color]::White
    $sd3TypeCombo.Items.AddRange(@("all", "blender", "projectile", "design_draft", "full_ship_artwork"))
    $sd3TypeCombo.SelectedItem = $settings.sd3TextureType
    $sd3GroupBox.Controls.Add($sd3TypeCombo)
    
    # SD3 Variations
    $sd3VarLabel = New-Object System.Windows.Forms.Label
    $sd3VarLabel.Location = New-Object System.Drawing.Point(10, 100)
    $sd3VarLabel.Size = New-Object System.Drawing.Size(100, 20)
    $sd3VarLabel.Text = "Variations:"
    $sd3VarLabel.ForeColor = [System.Drawing.Color]::White
    $sd3GroupBox.Controls.Add($sd3VarLabel)
    
    $sd3VarNumeric = New-Object System.Windows.Forms.NumericUpDown
    $sd3VarNumeric.Location = New-Object System.Drawing.Point(120, 100)
    $sd3VarNumeric.Size = New-Object System.Drawing.Size(80, 20)
    $sd3VarNumeric.Minimum = 1
    $sd3VarNumeric.Maximum = 10
    $sd3VarNumeric.Value = $settings.sd3Variations
    $sd3VarNumeric.BackColor = [System.Drawing.Color]::FromArgb(50, 50, 50)
    $sd3VarNumeric.ForeColor = [System.Drawing.Color]::White
    $sd3GroupBox.Controls.Add($sd3VarNumeric)
    
    # SD3 Info Label
    $sd3InfoLabel = New-Object System.Windows.Forms.Label
    $sd3InfoLabel.Location = New-Object System.Drawing.Point(10, 135)
    $sd3InfoLabel.Size = New-Object System.Drawing.Size(390, 35)
    $sd3InfoLabel.Text = "SD3 automatically detects ships from registry and generates all required textures (Blender, Projectiles, Design Drafts, Full Ship Artwork) using Stable Diffusion 3 Medium with image-to-image mode."
    $sd3InfoLabel.ForeColor = [System.Drawing.Color]::Gray
    $sd3GroupBox.Controls.Add($sd3InfoLabel)
    
    $yPos += 190
    
    # ============================================================
    # STAGE SKIP FLAGS
    # ============================================================
    
    $stageGroupBox = New-Object System.Windows.Forms.GroupBox
    $stageGroupBox.Location = New-Object System.Drawing.Point(20, $yPos)
    $stageGroupBox.Size = New-Object System.Drawing.Size(420, 140)
    $stageGroupBox.Text = "Pipeline Stages (Quality Generator)"
    $stageGroupBox.ForeColor = [System.Drawing.Color]::Cyan
    $form.Controls.Add($stageGroupBox)
    
    $skipDraftCheckBox = New-Object System.Windows.Forms.CheckBox
    $skipDraftCheckBox.Location = New-Object System.Drawing.Point(10, 25)
    $skipDraftCheckBox.Size = New-Object System.Drawing.Size(130, 25)
    $skipDraftCheckBox.Text = "Skip Draft"
    $skipDraftCheckBox.Checked = $settings.skipDraft
    $skipDraftCheckBox.ForeColor = [System.Drawing.Color]::White
    $stageGroupBox.Controls.Add($skipDraftCheckBox)
    
    $skipAssessCheckBox = New-Object System.Windows.Forms.CheckBox
    $skipAssessCheckBox.Location = New-Object System.Drawing.Point(150, 25)
    $skipAssessCheckBox.Size = New-Object System.Drawing.Size(130, 25)
    $skipAssessCheckBox.Text = "Skip Assess"
    $skipAssessCheckBox.Checked = $settings.skipAssess
    $skipAssessCheckBox.ForeColor = [System.Drawing.Color]::White
    $stageGroupBox.Controls.Add($skipAssessCheckBox)
    
    $skipRefineCheckBox = New-Object System.Windows.Forms.CheckBox
    $skipRefineCheckBox.Location = New-Object System.Drawing.Point(290, 25)
    $skipRefineCheckBox.Size = New-Object System.Drawing.Size(120, 25)
    $skipRefineCheckBox.Text = "Skip Refine"
    $skipRefineCheckBox.Checked = $settings.skipRefine
    $skipRefineCheckBox.ForeColor = [System.Drawing.Color]::White
    $stageGroupBox.Controls.Add($skipRefineCheckBox)
    
    $skipSelectCheckBox = New-Object System.Windows.Forms.CheckBox
    $skipSelectCheckBox.Location = New-Object System.Drawing.Point(10, 55)
    $skipSelectCheckBox.Size = New-Object System.Drawing.Size(130, 25)
    $skipSelectCheckBox.Text = "Skip Select"
    $skipSelectCheckBox.Checked = $settings.skipSelect
    $skipSelectCheckBox.ForeColor = [System.Drawing.Color]::White
    $stageGroupBox.Controls.Add($skipSelectCheckBox)
    
    $skipIntegrateCheckBox = New-Object System.Windows.Forms.CheckBox
    $skipIntegrateCheckBox.Location = New-Object System.Drawing.Point(150, 55)
    $skipIntegrateCheckBox.Size = New-Object System.Drawing.Size(130, 25)
    $skipIntegrateCheckBox.Text = "Skip Integrate"
    $skipIntegrateCheckBox.Checked = $settings.skipIntegrate
    $skipIntegrateCheckBox.ForeColor = [System.Drawing.Color]::White
    $stageGroupBox.Controls.Add($skipIntegrateCheckBox)
    
    $skipSpritesheetCheckBox = New-Object System.Windows.Forms.CheckBox
    $skipSpritesheetCheckBox.Location = New-Object System.Drawing.Point(290, 55)
    $skipSpritesheetCheckBox.Size = New-Object System.Drawing.Size(120, 25)
    $skipSpritesheetCheckBox.Text = "Skip Spritesheet"
    $skipSpritesheetCheckBox.Checked = $settings.skipSpritesheet
    $skipSpritesheetCheckBox.ForeColor = [System.Drawing.Color]::White
    $stageGroupBox.Controls.Add($skipSpritesheetCheckBox)
    
    $skipItemsCheckBox = New-Object System.Windows.Forms.CheckBox
    $skipItemsCheckBox.Location = New-Object System.Drawing.Point(10, 85)
    $skipItemsCheckBox.Size = New-Object System.Drawing.Size(130, 25)
    $skipItemsCheckBox.Text = "Skip Items"
    $skipItemsCheckBox.Checked = $settings.skipItems
    $skipItemsCheckBox.ForeColor = [System.Drawing.Color]::White
    $stageGroupBox.Controls.Add($skipItemsCheckBox)
    
    # Resume Options
    $resumeCheckBox = New-Object System.Windows.Forms.CheckBox
    $resumeCheckBox.Location = New-Object System.Drawing.Point(150, 85)
    $resumeCheckBox.Size = New-Object System.Drawing.Size(130, 25)
    $resumeCheckBox.Text = "Resume"
    $resumeCheckBox.Checked = $settings.resume
    $resumeCheckBox.ForeColor = [System.Drawing.Color]::White
    $stageGroupBox.Controls.Add($resumeCheckBox)
    
    $skipCompletedCheckBox = New-Object System.Windows.Forms.CheckBox
    $skipCompletedCheckBox.Location = New-Object System.Drawing.Point(290, 85)
    $skipCompletedCheckBox.Size = New-Object System.Drawing.Size(120, 25)
    $skipCompletedCheckBox.Text = "Skip Completed"
    $skipCompletedCheckBox.Checked = $settings.skipCompleted
    $skipCompletedCheckBox.ForeColor = [System.Drawing.Color]::White
    $stageGroupBox.Controls.Add($skipCompletedCheckBox)
    
    $yPos += 150
    
    # ============================================================
    # PROGRESS AREA
    # ============================================================
    
    $progressGroupBox = New-Object System.Windows.Forms.GroupBox
    $progressGroupBox.Location = New-Object System.Drawing.Point(460, $yPos - 40)
    $progressGroupBox.Size = New-Object System.Drawing.Size(400, 180)
    $progressGroupBox.Text = "Generation Progress"
    $progressGroupBox.ForeColor = [System.Drawing.Color]::Cyan
    $form.Controls.Add($progressGroupBox)
    
    # Overall Progress Bar
    $progressBar = New-Object System.Windows.Forms.ProgressBar
    $progressBar.Location = New-Object System.Drawing.Point(10, 25)
    $progressBar.Size = New-Object System.Drawing.Size(380, 25)
    $progressBar.Style = "Continuous"
    $progressGroupBox.Controls.Add($progressBar)
    
    # Progress Percentage Label
    $progressPercentLabel = New-Object System.Windows.Forms.Label
    $progressPercentLabel.Location = New-Object System.Drawing.Point(10, 55)
    $progressPercentLabel.Size = New-Object System.Drawing.Size(380, 20)
    $progressPercentLabel.Text = "0% Complete"
    $progressPercentLabel.ForeColor = [System.Drawing.Color]::Cyan
    $progressPercentLabel.Font = New-Object System.Drawing.Font("Segoe UI", 9, [System.Drawing.FontStyle]::Bold)
    $progressPercentLabel.TextAlign = "MiddleCenter"
    $progressGroupBox.Controls.Add($progressPercentLabel)
    
    # Current Stage Label
    $progressLabel = New-Object System.Windows.Forms.Label
    $progressLabel.Location = New-Object System.Drawing.Point(10, 80)
    $progressLabel.Size = New-Object System.Drawing.Size(380, 40)
    $progressLabel.Text = "Ready to generate assets"
    $progressLabel.ForeColor = [System.Drawing.Color]::White
    $progressGroupBox.Controls.Add($progressLabel)
    
    # Status Counters (Warnings/Errors)
    $statusLabel = New-Object System.Windows.Forms.Label
    $statusLabel.Location = New-Object System.Drawing.Point(10, 125)
    $statusLabel.Size = New-Object System.Drawing.Size(380, 45)
    $statusLabel.Text = "Warnings: 0 | Errors: 0"
    $statusLabel.ForeColor = [System.Drawing.Color]::LightGray
    $statusLabel.Font = New-Object System.Drawing.Font("Consolas", 9)
    $progressGroupBox.Controls.Add($statusLabel)
    
    # ============================================================
    # OUTPUT LOG
    # ============================================================
    
    $logGroupBox = New-Object System.Windows.Forms.GroupBox
    $logGroupBox.Location = New-Object System.Drawing.Point(20, $yPos)
    $logGroupBox.Size = New-Object System.Drawing.Size(420, 160)
    $logGroupBox.Text = "Output Log"
    $logGroupBox.ForeColor = [System.Drawing.Color]::Cyan
    $form.Controls.Add($logGroupBox)
    
    $logTextBox = New-Object System.Windows.Forms.TextBox
    $logTextBox.Location = New-Object System.Drawing.Point(10, 25)
    $logTextBox.Size = New-Object System.Drawing.Size(400, 125)
    $logTextBox.Multiline = $true
    $logTextBox.ScrollBars = "Vertical"
    $logTextBox.BackColor = [System.Drawing.Color]::Black
    $logTextBox.ForeColor = [System.Drawing.Color]::LightGreen
    $logTextBox.Font = New-Object System.Drawing.Font("Consolas", 8)
    $logTextBox.ReadOnly = $true
    $logGroupBox.Controls.Add($logTextBox)
    
    # ============================================================
    # WARNINGS AND ERRORS BOX
    # ============================================================
    
    $errorsGroupBox = New-Object System.Windows.Forms.GroupBox
    $errorsGroupBox.Location = New-Object System.Drawing.Point(460, $yPos + 10)
    $errorsGroupBox.Size = New-Object System.Drawing.Size(400, 160)
    $errorsGroupBox.Text = "Warnings & Errors"
    $errorsGroupBox.ForeColor = [System.Drawing.Color]::Yellow
    $form.Controls.Add($errorsGroupBox)
    
    $errorsTextBox = New-Object System.Windows.Forms.TextBox
    $errorsTextBox.Location = New-Object System.Drawing.Point(10, 25)
    $errorsTextBox.Size = New-Object System.Drawing.Size(380, 125)
    $errorsTextBox.Multiline = $true
    $errorsTextBox.ScrollBars = "Vertical"
    $errorsTextBox.BackColor = [System.Drawing.Color]::FromArgb(40, 0, 0)
    $errorsTextBox.ForeColor = [System.Drawing.Color]::Orange
    $errorsTextBox.Font = New-Object System.Drawing.Font("Consolas", 8)
    $errorsTextBox.ReadOnly = $true
    $errorsGroupBox.Controls.Add($errorsTextBox)
    
    $yPos += 170
    
    # ============================================================
    # ACTION BUTTONS
    # ============================================================
    
    $generateBtn = New-Object System.Windows.Forms.Button
    $generateBtn.Location = New-Object System.Drawing.Point(20, $yPos)
    $generateBtn.Size = New-Object System.Drawing.Size(200, 40)
    $generateBtn.Text = "Generate Assets"
    $generateBtn.Font = New-Object System.Drawing.Font("Segoe UI", 12, [System.Drawing.FontStyle]::Bold)
    $generateBtn.BackColor = [System.Drawing.Color]::FromArgb(0, 120, 215)
    $generateBtn.ForeColor = [System.Drawing.Color]::White
    $generateBtn.FlatStyle = "Flat"
    $form.Controls.Add($generateBtn)
    
    $openOutputBtn = New-Object System.Windows.Forms.Button
    $openOutputBtn.Location = New-Object System.Drawing.Point(240, $yPos)
    $openOutputBtn.Size = New-Object System.Drawing.Size(150, 40)
    $openOutputBtn.Text = "Open Output Folder"
    $openOutputBtn.BackColor = [System.Drawing.Color]::FromArgb(60, 60, 60)
    $openOutputBtn.ForeColor = [System.Drawing.Color]::White
    $openOutputBtn.FlatStyle = "Flat"
    $form.Controls.Add($openOutputBtn)
    
    $openOutputBtn.Add_Click({
        if (Test-Path $outputTextBox.Text) {
            Start-Process "explorer.exe" -ArgumentList $outputTextBox.Text
        } else {
            [System.Windows.Forms.MessageBox]::Show(
                "Output directory does not exist: $($outputTextBox.Text)",
                "Directory Not Found",
                [System.Windows.Forms.MessageBoxButtons]::OK,
                [System.Windows.Forms.MessageBoxIcon]::Warning
            )
        }
    })
    
    $refreshPreviewBtn = New-Object System.Windows.Forms.Button
    $refreshPreviewBtn.Location = New-Object System.Drawing.Point(410, $yPos)
    $refreshPreviewBtn.Size = New-Object System.Drawing.Size(150, 40)
    $refreshPreviewBtn.Text = "Refresh Preview"
    $refreshPreviewBtn.BackColor = [System.Drawing.Color]::FromArgb(60, 60, 60)
    $refreshPreviewBtn.ForeColor = [System.Drawing.Color]::White
    $refreshPreviewBtn.FlatStyle = "Flat"
    $form.Controls.Add($refreshPreviewBtn)
    
    $saveSettingsBtn = New-Object System.Windows.Forms.Button
    $saveSettingsBtn.Location = New-Object System.Drawing.Point(580, $yPos)
    $saveSettingsBtn.Size = New-Object System.Drawing.Size(130, 40)
    $saveSettingsBtn.Text = "Save Settings"
    $saveSettingsBtn.BackColor = [System.Drawing.Color]::FromArgb(60, 60, 60)
    $saveSettingsBtn.ForeColor = [System.Drawing.Color]::White
    $saveSettingsBtn.FlatStyle = "Flat"
    $form.Controls.Add($saveSettingsBtn)
    
    $closeBtn = New-Object System.Windows.Forms.Button
    $closeBtn.Location = New-Object System.Drawing.Point(730, $yPos)
    $closeBtn.Size = New-Object System.Drawing.Size(130, 40)
    $closeBtn.Text = "Close"
    $closeBtn.BackColor = [System.Drawing.Color]::FromArgb(60, 60, 60)
    $closeBtn.ForeColor = [System.Drawing.Color]::White
    $closeBtn.FlatStyle = "Flat"
    $form.Controls.Add($closeBtn)
    
    $closeBtn.Add_Click({
        $form.Close()
    })
    
    # ============================================================
    # EVENT HANDLERS
    # ============================================================
    
    # Helper function to ensure a value is always a single integer
    function Get-SafeInteger {
        param($Value)
        
        if ($null -eq $Value) {
            return 0
        }
        
        if ($Value -is [System.Array]) {
            if ($Value.Length -gt 0) {
                $Value = $Value[0]
            } else {
                return 0
            }
        }
        
        try {
            return [int]$Value
        } catch {
            return 0
        }
    }
    
    function Parse-OutputLine {
        param([string]$Line)
        
        # Detect warnings and errors
        if ($Line -match "WARNING|Warning|warn:") {
            $script:WarningCount++
            $errorsTextBox.AppendText("[WARNING] $Line`r`n")
            $errorsTextBox.SelectionStart = $errorsTextBox.Text.Length
            $errorsTextBox.ScrollToCaret()
        } elseif ($Line -match "ERROR|Error|error:|FAILED|Failed|Exception") {
            $script:ErrorCount++
            $errorsTextBox.AppendText("[ERROR] $Line`r`n")
            $errorsTextBox.SelectionStart = $errorsTextBox.Text.Length
            $errorsTextBox.ScrollToCaret()
        }
        
        # Detect stage progress from Python script
        if ($Line -match "Stage (\d+)/(\d+):\s*(.+)") {
            try {
                # Extract match values safely - ensure we get single values, not arrays
                $match1 = $Matches[1]
                $match2 = $Matches[2]
                $match3 = $Matches[3]
                
                # Convert to strings, handling arrays
                $stageNumStr = if ($match1 -is [System.Array]) { $match1[0].ToString() } else { $match1.ToString() }
                $totalStagesStr = if ($match2 -is [System.Array]) { $match2[0].ToString() } else { $match2.ToString() }
                $stageName = if ($match3 -is [System.Array]) { $match3[0].ToString() } else { $match3.ToString() }
                
                # Convert to integers safely
                $stageNum = 0
                $totalStages = 0
                if ([int]::TryParse($stageNumStr, [ref]$stageNum) -and 
                    [int]::TryParse($totalStagesStr, [ref]$totalStages)) {
                    
                    # Ensure we have single integer values before subtraction
                    $stageNumInt = Get-SafeInteger -Value $stageNum
                    $totalStagesInt = Get-SafeInteger -Value $totalStages
                    
                    # Calculate completed stages (subtract 1 safely)
                    # Use explicit integer arithmetic to avoid array issues
                    if ($stageNumInt -gt 0) {
                        $completedValue = $stageNumInt
                        $completedValue = [int]$completedValue - [int]1
                        $script:CompletedStages = Get-SafeInteger -Value $completedValue
                    } else {
                        $script:CompletedStages = 0
                    }
                    $script:TotalStages = $totalStagesInt
                    $script:CurrentStage = $stageName
                }
            } catch {
                # Ignore parsing errors
            }
        }
        
        # Detect SD3 texture generation progress
        if ($Line -match "\[(\d+)/(\d+)\]\s+(.+)") {
            try {
                # Extract match values safely - ensure we get single values, not arrays
                $match1 = $Matches[1]
                $match2 = $Matches[2]
                $match3 = $Matches[3]
                
                # Convert to strings, handling arrays
                $currentStepStr = if ($match1 -is [System.Array]) { $match1[0].ToString() } else { $match1.ToString() }
                $totalStepsStr = if ($match2 -is [System.Array]) { $match2[0].ToString() } else { $match2.ToString() }
                $stepName = if ($match3 -is [System.Array]) { $match3[0].ToString() } else { $match3.ToString() }
                
                # Convert to integers safely
                $currentStep = 0
                $totalSteps = 0
                if ([int]::TryParse($currentStepStr, [ref]$currentStep) -and 
                    [int]::TryParse($totalStepsStr, [ref]$totalSteps)) {
                    
                    # Ensure we have single integer values
                    $currentStepInt = [int]$currentStep
                    $totalStepsInt = [int]$totalSteps
                    
                    $script:CurrentStage = $stepName
                    
                    # Calculate progress percentage
                    if ($totalStepsInt -gt 0) {
                        $percent = [int](($currentStepInt / $totalStepsInt) * 100)
                        $progressBar.Value = [Math]::Min($percent, 100)
                        $progressPercentLabel.Text = "$percent% Complete"
                    }
                }
            } catch {
                # Ignore parsing errors
            }
        }
        
        # Update status counters
        $statusLabel.Text = "Warnings: $($script:WarningCount) | Errors: $($script:ErrorCount)"
        if ($script:ErrorCount -gt 0) {
            $statusLabel.ForeColor = [System.Drawing.Color]::Red
        } elseif ($script:WarningCount -gt 0) {
            $statusLabel.ForeColor = [System.Drawing.Color]::Yellow
        } else {
            $statusLabel.ForeColor = [System.Drawing.Color]::LightGreen
        }
    }
    
    function Update-PreviewImage {
        param([string]$ImagePath)
        
        try {
            if (Test-Path $ImagePath) {
                $script:LastImagePath = $ImagePath
                # Dispose old image to avoid file locks
                if ($previewBox.Image) {
                    $previewBox.Image.Dispose()
                }
                $image = [System.Drawing.Image]::FromFile($ImagePath)
                $previewBox.Image = $image
                $previewLabel.Text = Split-Path -Leaf $ImagePath
                $previewLabel.ForeColor = [System.Drawing.Color]::LightGreen
            }
        } catch {
            $previewLabel.Text = "Failed to load image: $_"
            $previewLabel.ForeColor = [System.Drawing.Color]::Red
        }
    }
    
    function Find-LatestImage {
        param([string]$OutputDir)
        
        if (-not (Test-Path $OutputDir)) {
            return $null
        }
        
        # Search for latest PNG in Best, FullShipArtwork, DesignDrafts, Blender directories
        $searchDirs = @(
            (Join-Path $OutputDir "Best\full_ship_artwork"),
            (Join-Path $OutputDir "Best\design_draft"),
            (Join-Path $OutputDir "Best\blender"),
            (Join-Path $OutputDir "Stage1_Draft\Textures\FullShipArtwork"),
            (Join-Path $OutputDir "Stage1_Draft\Textures\DesignDrafts"),
            (Join-Path $OutputDir "Stage1_Draft\Textures\Blender"),
            (Join-Path $OutputDir "Stage6_Spritesheets")
        )
        
        $latestImage = $null
        $latestTime = [DateTime]::MinValue
        
        foreach ($dir in $searchDirs) {
            if (Test-Path $dir) {
                $images = Get-ChildItem -Path $dir -Filter "*.png" -ErrorAction SilentlyContinue | 
                          Sort-Object LastWriteTime -Descending | 
                          Select-Object -First 1
                
                if ($images -and $images.LastWriteTime -gt $latestTime) {
                    $latestImage = $images.FullName
                    $latestTime = $images.LastWriteTime
                }
            }
        }
        
        return $latestImage
    }
    
    $refreshPreviewBtn.Add_Click({
        $latestImage = Find-LatestImage -OutputDir $outputTextBox.Text
        if ($latestImage) {
            Update-PreviewImage -ImagePath $latestImage
        } else {
            [System.Windows.Forms.MessageBox]::Show(
                "No images found in output directory.",
                "No Images",
                [System.Windows.Forms.MessageBoxButtons]::OK,
                [System.Windows.Forms.MessageBoxIcon]::Information
            )
        }
    })
    
    $saveSettingsBtn.Add_Click({
        $settingsToSave = @{
            outputDir = $outputTextBox.Text
            shipRegistry = $settings.shipRegistry
            visualRegistry = $settings.visualRegistry
            draftCount = $draftNumeric.Value
            refineCount = 3
            finalCount = $finalNumeric.Value
            enableRefinement = $refineCheckBox.Checked
            useSd3 = $sd3EnableCheckBox.Checked
            sd3TextureType = $sd3TypeCombo.SelectedItem
            sd3Variations = $sd3VarNumeric.Value
            sd3Fast = $sd3FastCheckBox.Checked
            shipId = if ($shipIdCombo.Text -eq "(All Ships)") { "" } else { $shipIdCombo.Text }
            quickMode = $quickCheckBox.Checked
            skipDraft = $skipDraftCheckBox.Checked
            skipAssess = $skipAssessCheckBox.Checked
            skipRefine = $skipRefineCheckBox.Checked
            skipSelect = $skipSelectCheckBox.Checked
            skipIntegrate = $skipIntegrateCheckBox.Checked
            skipSpritesheet = $skipSpritesheetCheckBox.Checked
            skipItems = $skipItemsCheckBox.Checked
            resume = $resumeCheckBox.Checked
            skipCompleted = $skipCompletedCheckBox.Checked
            lastImageDir = $outputTextBox.Text
        }
        
        Save-Settings -Settings $settingsToSave
        
        [System.Windows.Forms.MessageBox]::Show(
            "Settings saved successfully!",
            "Settings Saved",
            [System.Windows.Forms.MessageBoxButtons]::OK,
            [System.Windows.Forms.MessageBoxIcon]::Information
        )
    })
    
    $generateBtn.Add_Click({
        if ($script:GenerationRunning) {
            [System.Windows.Forms.MessageBox]::Show(
                "Generation is already running. Please wait for it to complete.",
                "Generation In Progress",
                [System.Windows.Forms.MessageBoxButtons]::OK,
                [System.Windows.Forms.MessageBoxIcon]::Warning
            )
            return
        }
        
        # Reset counters
        $script:GenerationRunning = $true
        $script:WarningCount = 0
        $script:ErrorCount = 0
        $script:CurrentStage = ""
        $script:TotalStages = 0
        $script:CompletedStages = 0
        $script:LastOutputLength = 0
        
        $generateBtn.Enabled = $false
        $generateBtn.Text = "Generating..."
        $logTextBox.Clear()
        $errorsTextBox.Clear()
        $progressBar.Value = 0
        $progressPercentLabel.Text = "0% Complete"
        $progressLabel.Text = "Starting generation..."
        $statusLabel.Text = "Warnings: 0 | Errors: 0"
        $statusLabel.ForeColor = [System.Drawing.Color]::LightGray
        
        # Build command based on selected mode
        if ($qualityRadio.Checked) {
            # Quality Asset Generator
            $pythonScript = Join-Path $script:ScriptDir "space_whale_quality_asset_generator.py"
            
            if (-not (Test-Path $pythonScript)) {
                [System.Windows.Forms.MessageBox]::Show(
                    "Python script not found: $pythonScript",
                    "Script Not Found",
                    [System.Windows.Forms.MessageBoxButtons]::OK,
                    [System.Windows.Forms.MessageBoxIcon]::Error
                )
                $script:GenerationRunning = $false
                $generateBtn.Enabled = $true
                $generateBtn.Text = "Generate Assets"
                return
            }
            
            $args = @(
                $pythonScript,
                "--output", $outputTextBox.Text
            )
            
            if ($quickCheckBox.Checked) { $args += "--quick" }
            if ($draftNumeric.Value -ne 6) { $args += @("--draft-count", $draftNumeric.Value) }
            if ($finalNumeric.Value -ne 2) { $args += @("--final-count", $finalNumeric.Value) }
            if (-not $refineCheckBox.Checked) { $args += "--no-refinement" }
            
            # SD3 is enabled by default, only pass --no-sd3 if disabled
            if (-not $sd3EnableCheckBox.Checked) {
                $args += "--no-sd3"
            } else {
                # SD3 is enabled by default, but pass texture type and variations if customized
                if ($sd3TypeCombo.SelectedItem -ne "all") {
                    $args += @("--sd3-texture-type", $sd3TypeCombo.SelectedItem)
                }
                if ($sd3VarNumeric.Value -ne 3) {
                    $args += @("--sd3-variations", $sd3VarNumeric.Value)
                }
                if ($sd3FastCheckBox.Checked) { $args += "--sd3-fast" }
            }
            
            if ($shipIdCombo.Text -ne "(All Ships)" -and $shipIdCombo.Text.Length -gt 0) {
                $args += @("--ship-id", $shipIdCombo.Text)
            }
            
            if ($skipDraftCheckBox.Checked) { $args += "--skip-draft" }
            if ($skipAssessCheckBox.Checked) { $args += "--skip-assess" }
            if ($skipRefineCheckBox.Checked) { $args += "--skip-refine" }
            if ($skipSelectCheckBox.Checked) { $args += "--skip-select" }
            if ($skipIntegrateCheckBox.Checked) { $args += "--skip-integrate" }
            if ($skipSpritesheetCheckBox.Checked) { $args += "--skip-spritesheet" }
            if ($skipItemsCheckBox.Checked) { $args += "--skip-items" }
            if ($resumeCheckBox.Checked) { $args += "--resume" }
            if ($skipCompletedCheckBox.Checked) { $args += "--skip-completed" }
            
            $logTextBox.AppendText("Starting Quality Asset Generator...`r`n")
            $logTextBox.AppendText("Command: python $($args -join ' ')`r`n`r`n")
            
            # Start generation in background
            $job = Start-Job -ScriptBlock {
                param($PythonArgs)
                & python $PythonArgs 2>&1
            } -ArgumentList (,$args)
            
        } else {
            # SD3 Texture Generator
            $psScript = Join-Path $script:ScriptDir "SpaceWhaleSD3TextureGenerator.ps1"
            
            if (-not (Test-Path $psScript)) {
                [System.Windows.Forms.MessageBox]::Show(
                    "PowerShell script not found: $psScript",
                    "Script Not Found",
                    [System.Windows.Forms.MessageBoxButtons]::OK,
                    [System.Windows.Forms.MessageBoxIcon]::Error
                )
                $script:GenerationRunning = $false
                $generateBtn.Enabled = $true
                $generateBtn.Text = "Generate Assets"
                return
            }
            
            $shipReg = Join-Path $script:ScriptDir "space_whale_ship_example.json"
            $visReg = Join-Path $script:ScriptDir "space_whale_visual_language_registry.json"
            
            $psArgs = @{
                ShipRegistry = $shipReg
                VisualRegistry = $visReg
                OutputDir = Join-Path $outputTextBox.Text "Stage1_Draft\Textures"
                TextureType = $sd3TypeCombo.SelectedItem
                Variations = $sd3VarNumeric.Value
            }
            
            if ($shipIdCombo.Text -ne "(All Ships)" -and $shipIdCombo.Text.Length -gt 0) {
                $psArgs.ShipId = $shipIdCombo.Text
            }
            
            # Check if reference textures exist
            $refDir = Join-Path $outputTextBox.Text "Stage1_Draft\Textures"
            if (Test-Path $refDir) {
                $psArgs.ReferenceTextureDir = $refDir
                $psArgs.ImageStrength = 0.7
            }
            
            if (-not $sd3FastCheckBox.Checked -and $sd3TypeCombo.SelectedItem -eq "all") {
                $psArgs.IncludeFullShipArtwork = $true
            }
            
            $logTextBox.AppendText("Starting SD3 Texture Generator...`r`n")
            $logTextBox.AppendText("Script: $psScript`r`n")
            $logTextBox.AppendText("Settings: $($psArgs | ConvertTo-Json -Compress)`r`n`r`n")
            
            # Start generation in background
            $job = Start-Job -ScriptBlock {
                param($ScriptPath, $Arguments)
                & powershell -NoProfile -ExecutionPolicy Bypass -File $ScriptPath @Arguments 2>&1
            } -ArgumentList $psScript, $psArgs
        }
        
        # Monitor job progress
        $timer = New-Object System.Windows.Forms.Timer
        $timer.Interval = 500  # 500ms for more responsive updates
        $script:LastOutputLength = 0
        
        $timer.Add_Tick({
            try {
                # Check if job is still running
                if ($job.State -eq "Completed" -or $job.State -eq "Failed" -or $job.State -eq "Stopped") {
                    $timer.Stop()
                    
                    # Get remaining job output
                    $newOutput = Receive-Job -Job $job
                    
                    # Ensure we have an array, even if Receive-Job returns a single object or null
                    if ($null -eq $newOutput) {
                        $newOutput = @()
                    } elseif ($newOutput -isnot [System.Array]) {
                        $newOutput = @($newOutput)
                    }
                    
                    # Process and display new output
                    foreach ($item in $newOutput) {
                        if ($null -ne $item) {
                            $lineStr = $item.ToString()
                            $logTextBox.AppendText("$lineStr`r`n")
                            Parse-OutputLine -Line $lineStr
                        }
                    }
                    
                    $logTextBox.SelectionStart = $logTextBox.Text.Length
                    $logTextBox.ScrollToCaret()
                    
                    Remove-Job -Job $job
                    
                    if ($job.State -eq "Completed") {
                        $progressBar.Value = 100
                        $progressPercentLabel.Text = "100% Complete"
                        $progressLabel.Text = "Generation complete!"
                        $progressLabel.ForeColor = [System.Drawing.Color]::LightGreen
                        
                        # Auto-refresh preview
                        $latestImage = Find-LatestImage -OutputDir $outputTextBox.Text
                        if ($latestImage) {
                            Update-PreviewImage -ImagePath $latestImage
                        }
                        
                        $summaryMsg = "Asset generation completed successfully!`r`n`r`n"
                        $summaryMsg += "Warnings: $($script:WarningCount)`r`n"
                        $summaryMsg += "Errors: $($script:ErrorCount)"
                        
                        [System.Windows.Forms.MessageBox]::Show(
                            $summaryMsg,
                            "Generation Complete",
                            [System.Windows.Forms.MessageBoxButtons]::OK,
                            [System.Windows.Forms.MessageBoxIcon]::Information
                        )
                    } else {
                        $progressLabel.Text = "Generation failed!"
                        $progressLabel.ForeColor = [System.Drawing.Color]::Red
                        $progressPercentLabel.ForeColor = [System.Drawing.Color]::Red
                        
                        [System.Windows.Forms.MessageBox]::Show(
                            "Asset generation failed. Check the output log and errors box for details.`r`n`r`nErrors: $($script:ErrorCount)",
                            "Generation Failed",
                            [System.Windows.Forms.MessageBoxButtons]::OK,
                            [System.Windows.Forms.MessageBoxIcon]::Error
                        )
                    }
                    
                    $script:GenerationRunning = $false
                    $generateBtn.Enabled = $true
                    $generateBtn.Text = "Generate Assets"
                } else {
                    # Get new job output (non-blocking)
                    $newOutput = Receive-Job -Job $job -Keep
                    
                    if ($newOutput) {
                        # Ensure we have an array, even if Receive-Job returns a single object
                        if ($null -eq $newOutput) {
                            $newOutput = @()
                        } elseif ($newOutput -isnot [System.Array]) {
                            $newOutput = @($newOutput)
                        }
                        
                        # Convert all output to strings and process immediately
                        foreach ($item in $newOutput) {
                            if ($null -ne $item) {
                                try {
                                    $line = $item.ToString()
                                    if ($null -ne $line -and $line.Length -gt 0) {
                                        $logTextBox.AppendText("$line`r`n")
                                        Parse-OutputLine -Line $line
                                    }
                                } catch {
                                    # Skip problematic items
                                }
                            }
                        }
                        
                        # Update scroll position
                        $logTextBox.SelectionStart = $logTextBox.Text.Length
                        $logTextBox.ScrollToCaret()
                    }
                    
                    # Update current stage display
                    if ($script:CurrentStage) {
                        $progressLabel.Text = "Current: $($script:CurrentStage)"
                    }
                    
                    # Calculate progress based on stages if available
                    try {
                        # Ensure variables are single integers, not arrays
                        $totalStagesValue = if ($script:TotalStages -is [System.Array]) { 
                            [int]$script:TotalStages[0] 
                        } else { 
                            [int]$script:TotalStages 
                        }
                        
                        $completedStagesValue = if ($script:CompletedStages -is [System.Array]) { 
                            [int]$script:CompletedStages[0] 
                        } else { 
                            [int]$script:CompletedStages 
                        }
                        
                        if ($totalStagesValue -gt 0 -and $completedStagesValue -ge 0) {
                            if ($totalStagesValue -gt 0) {
                                # Ensure all values are definitely integers before arithmetic
                                $completedInt = [int]$completedStagesValue
                                $totalInt = [int]$totalStagesValue
                                
                                $percent = [int](($completedInt / $totalInt) * 100)
                                $progressBar.Value = [Math]::Min($percent, 99)  # Keep at 99% until truly complete
                                $nextStage = [int]($completedInt + 1)
                                $progressPercentLabel.Text = "$percent% Complete (Stage $nextStage/$totalInt)"
                            }
                        }
                    } catch {
                        # Ignore calculation errors
                    }
                    
                    # Try to find new images for preview
                    $latestImage = Find-LatestImage -OutputDir $outputTextBox.Text
                    if ($latestImage -and $latestImage -ne $script:LastImagePath) {
                        Update-PreviewImage -ImagePath $latestImage
                    }
                }
            } catch {
                $timer.Stop()
                $logTextBox.AppendText("Error monitoring progress: $_`r`n")
                $errorsTextBox.AppendText("[ERROR] Progress monitor exception: $_`r`n")
                $script:ErrorCount++
                $script:GenerationRunning = $false
                $generateBtn.Enabled = $true
                $generateBtn.Text = "Generate Assets"
            }
        })
        
        $timer.Start()
    })
    
    # Load initial preview if available
    if ($settings.lastImageDir) {
        $latestImage = Find-LatestImage -OutputDir $settings.lastImageDir
        if ($latestImage) {
            Update-PreviewImage -ImagePath $latestImage
        }
    }
    
    # Show form
    $form.ShowDialog() | Out-Null
    
    # Cleanup
    if ($previewBox.Image) {
        $previewBox.Image.Dispose()
    }
}

# ============================================================
# MAIN ENTRY POINT
# ============================================================

try {
    Create-MainForm
} catch {
    [System.Windows.Forms.MessageBox]::Show(
        "Fatal error: $_",
        "Error",
        [System.Windows.Forms.MessageBoxButtons]::OK,
        [System.Windows.Forms.MessageBoxIcon]::Error
    )
    exit 1
}

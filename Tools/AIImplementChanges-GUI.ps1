# ============================================================================
# AIImplementChanges-GUI.ps1
# ============================================================================
# GUI version of AI-Powered Code Change Implementation Tool
# ============================================================================

param(
    [Parameter(Mandatory=$false)]
    [string]$Path = ".",
    

# Load shared asset generation settings
$settingsPath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) ".\\AssetGenerationSettings.ps1"
if (Test-Path $settingsPath) {
    . $settingsPath
}
    [Parameter(Mandatory=$false)]
    [switch]$DryRun = $false,
    
    [Parameter(Mandatory=$false)]
    [switch]$Backup = $true,
    
    [Parameter(Mandatory=$false)]
    [switch]$ShowDetails = $false,
    
    [Parameter(Mandatory=$false)]
    [string]$OllamaModel = "codellama:34b",
    
    [Parameter(Mandatory=$false)]
    [string]$OllamaUrl = "http://localhost:11434",
    
    [Parameter(Mandatory=$false)]
    [int]$MaxCodeLength = 8000,
    
    [Parameter(Mandatory=$false)]
    [int]$MaxAITimePerFile = 300,
    
    [Parameter(Mandatory=$false)]
    [switch]$Interactive = $false,
    
    [Parameter(Mandatory=$false)]
    [string]$Focus = "All",
    
    [Parameter(Mandatory=$false)]
    [string]$LogFile = ""  # Path to log file with recommended changes
)

# Force STA mode for GUI
if ([System.Threading.Thread]::CurrentThread.GetApartmentState() -ne [System.Threading.ApartmentState]::STA) {
    Write-Host "ERROR: Must run in STA mode for GUI" -ForegroundColor Red
    Write-Host "Run with: powershell -STA -File AIImplementChanges-GUI.ps1" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

Add-Type -AssemblyName System.Windows.Forms, System.Drawing -ErrorAction Stop

$ErrorActionPreference = "Continue"
$PSScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

# ============================================================================
# CONFIGURATION
# ============================================================================

$Script:Config = @{
    Path = $Path
    DryRun = $DryRun
    Backup = $Backup
    Verbose = $ShowDetails
    OllamaModel = $OllamaModel
    OllamaUrl = $OllamaUrl
    OllamaApiUrl = "$OllamaUrl/api"
    MaxCodeLength = $MaxCodeLength
    MaxAITimePerFile = $MaxAITimePerFile
    Interactive = $Interactive
    Focus = $Focus
    LogFile = $LogFile
    FilesProcessed = 0
    FilesModified = 0
    TotalChanges = 0
    AIAnalyses = 0
    ChangesApplied = 0
    ChangesSkipped = 0
    StartTime = Get-Date
    IsRunning = $false
    ShouldStop = $false
    CurrentFile = ""
    CurrentPhase = "Initializing"
    TotalFiles = 0
    FileIndex = 0
}

# ============================================================================
# GUI FORM
# ============================================================================

$form = New-Object System.Windows.Forms.Form
$form.Text = "AI-Powered Code Change Implementation Tool - Drag & Drop Files/Folders Here"
$form.Size = New-Object System.Drawing.Size(1000, 700)
$form.StartPosition = "CenterScreen"
$form.FormBorderStyle = "FixedDialog"
$form.MaximizeBox = $false
$form.MinimizeBox = $false
$form.AllowDrop = $true  # Enable drag and drop

# Title
$titleLabel = New-Object System.Windows.Forms.Label
$titleLabel.Location = New-Object System.Drawing.Point(20, 10)
$titleLabel.Size = New-Object System.Drawing.Size(960, 30)
$titleLabel.Font = New-Object System.Drawing.Font("Segoe UI", 14, [System.Drawing.FontStyle]::Bold)
$titleLabel.Text = "AI-Powered Code Change Implementation"
$form.Controls.Add($titleLabel)

# Status Label
$statusLabel = New-Object System.Windows.Forms.Label
$statusLabel.Location = New-Object System.Drawing.Point(20, 50)
$statusLabel.Size = New-Object System.Drawing.Size(960, 25)
$statusLabel.Font = New-Object System.Drawing.Font("Segoe UI", 10)
$statusLabel.Text = "Initializing..."
$form.Controls.Add($statusLabel)

# Progress Bar
$progressBar = New-Object System.Windows.Forms.ProgressBar
$progressBar.Location = New-Object System.Drawing.Point(20, 80)
$progressBar.Size = New-Object System.Drawing.Size(960, 30)
$progressBar.Style = "Continuous"
$progressBar.Maximum = 100
$progressBar.Minimum = 0
$progressBar.Value = 0
$form.Controls.Add($progressBar)

# Time Info
$timeLabel = New-Object System.Windows.Forms.Label
$timeLabel.Location = New-Object System.Drawing.Point(20, 120)
$timeLabel.Size = New-Object System.Drawing.Size(960, 20)
$timeLabel.Font = New-Object System.Drawing.Font("Segoe UI", 9)
$timeLabel.Text = "Elapsed: 0:00 | Remaining: Calculating..."
$form.Controls.Add($timeLabel)

# Stats Panel
$statsPanel = New-Object System.Windows.Forms.Panel
$statsPanel.Location = New-Object System.Drawing.Point(20, 150)
$statsPanel.Size = New-Object System.Drawing.Size(960, 80)
$statsPanel.BorderStyle = "FixedSingle"
$form.Controls.Add($statsPanel)

$statsLabel = New-Object System.Windows.Forms.Label
$statsLabel.Location = New-Object System.Drawing.Point(10, 10)
$statsLabel.Size = New-Object System.Drawing.Size(940, 60)
$statsLabel.Font = New-Object System.Drawing.Font("Consolas", 9)
$statsLabel.Text = "Files: 0/0 | Modified: 0 | Changes: 0 | AI Analyses: 0 | Applied: 0 | Skipped: 0"
$statsPanel.Controls.Add($statsLabel)

# Log TextBox
$logBox = New-Object System.Windows.Forms.RichTextBox
$logBox.Location = New-Object System.Drawing.Point(20, 240)
$logBox.Size = New-Object System.Drawing.Size(960, 380)
$logBox.ReadOnly = $true
$logBox.Font = New-Object System.Drawing.Font("Consolas", 9)
$logBox.BackColor = [System.Drawing.Color]::Black
$logBox.ForeColor = [System.Drawing.Color]::LightGreen
$form.Controls.Add($logBox)

# Buttons
$stopButton = New-Object System.Windows.Forms.Button
$stopButton.Location = New-Object System.Drawing.Point(20, 630)
$stopButton.Size = New-Object System.Drawing.Size(100, 30)
$stopButton.Text = "Stop"
$stopButton.Enabled = $false
$form.Controls.Add($stopButton)

$closeButton = New-Object System.Windows.Forms.Button
$closeButton.Location = New-Object System.Drawing.Point(880, 630)
$closeButton.Size = New-Object System.Drawing.Size(100, 30)
$closeButton.Text = "Close"
$closeButton.Enabled = $false
$form.Controls.Add($closeButton)

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

function Add-Log {
    param(
        [string]$Message,
        [string]$Type = "Info"
    )
    
    $timestamp = Get-Date -Format "HH:mm:ss"
    $color = switch ($Type) {
        "Info"    { [System.Drawing.Color]::Cyan }
        "Success" { [System.Drawing.Color]::Green }
        "Warning" { [System.Drawing.Color]::Yellow }
        "Error"   { [System.Drawing.Color]::Red }
        default    { [System.Drawing.Color]::White }
    }
    
    $prefix = switch ($Type) {
        "Info"    { "[*]" }
        "Success" { "[+]" }
        "Warning" { "[!]" }
        "Error"   { "[-]" }
        default   { "[.]" }
    }
    
    $logBox.SelectionStart = $logBox.TextLength
    $logBox.SelectionLength = 0
    $logBox.SelectionColor = $color
    $logBox.AppendText("[$timestamp] $prefix $Message`r`n")
    $logBox.SelectionColor = $logBox.ForeColor
    $logBox.ScrollToCaret()
    [System.Windows.Forms.Application]::DoEvents()
}

function Update-Progress {
    param(
        [int]$Percent,
        [string]$Status = "",
        [string]$Phase = ""
    )
    
    if ($Percent -ge 0 -and $Percent -le 100) {
        $progressBar.Value = $Percent
    }
    
    if ($Status) {
        $statusLabel.Text = $Status
    }
    
    if ($Phase) {
        $Script:Config.CurrentPhase = $Phase
    }
    
    # Update time
    $elapsed = (Get-Date) - $Script:Config.StartTime
    $elapsedStr = "{0:mm\:ss}" -f $elapsed
    
    if ($Percent -gt 0 -and $Script:Config.TotalFiles -gt 0) {
        $remaining = [TimeSpan]::FromSeconds(($elapsed.TotalSeconds / $Percent) * (100 - $Percent))
        $remainingStr = "{0:mm\:ss}" -f $remaining
    } else {
        $remainingStr = "Calculating..."
    }
    
    $timeLabel.Text = "Elapsed: $elapsedStr | Remaining: $remainingStr | Phase: $Phase"
    
    # Update stats
    $statsLabel.Text = "Files: $($Script:Config.FileIndex)/$($Script:Config.TotalFiles) | Modified: $($Script:Config.FilesModified) | Changes: $($Script:Config.TotalChanges) | AI: $($Script:Config.AIAnalyses) | Applied: $($Script:Config.ChangesApplied) | Skipped: $($Script:Config.ChangesSkipped)"
    
    [System.Windows.Forms.Application]::DoEvents()
}

# ============================================================================
# LOAD MAIN SCRIPT FUNCTIONS
# ============================================================================

$mainScriptPath = Join-Path $PSScriptRoot "AIImplementChanges.ps1"
if (-not (Test-Path $mainScriptPath)) {
    [System.Windows.Forms.MessageBox]::Show("Main script not found: $mainScriptPath", "Error", "OK", "Error")
    $form.Close()
    exit 1
}

# Override Write-Status before loading main script
function Write-Status {
    param(
        [string]$Message,
        [string]$Type = "Info"
    )
    Add-Log $Message $Type
}

# Dot-source the main script with GuiMode=true
. $mainScriptPath -Path $Script:Config.Path -DryRun:$Script:Config.DryRun -Backup:$Script:Config.Backup -ShowDetails:$Script:Config.Verbose -OllamaModel $Script:Config.OllamaModel -OllamaUrl $Script:Config.OllamaUrl -MaxCodeLength $Script:Config.MaxCodeLength -MaxAITimePerFile $Script:Config.MaxAITimePerFile -Interactive:$Script:Config.Interactive -Focus $Script:Config.Focus -LogFile $Script:Config.LogFile -GuiMode:$true

# Re-override Write-Status after sourcing
function Write-Status {
    param(
        [string]$Message,
        [string]$Type = "Info"
    )
    Add-Log $Message $Type
}

# ============================================================================
# DRAG AND DROP HANDLERS
# ============================================================================

$form.Add_DragEnter({
    param($sender, $e)
    
    if ($Script:Config.IsRunning) {
        $e.Effect = [System.Windows.Forms.DragDropEffects]::None
        return
    }
    
    if ($e.Data.GetDataPresent([System.Windows.Forms.DataFormats]::FileDrop)) {
        $e.Effect = [System.Windows.Forms.DragDropEffects]::Copy
    } else {
        $e.Effect = [System.Windows.Forms.DragDropEffects]::None
    }
})

$form.Add_DragOver({
    param($sender, $e)
    
    if ($Script:Config.IsRunning) {
        $e.Effect = [System.Windows.Forms.DragDropEffects]::None
        return
    }
    
    if ($e.Data.GetDataPresent([System.Windows.Forms.DataFormats]::FileDrop)) {
        $e.Effect = [System.Windows.Forms.DragDropEffects]::Copy
    } else {
        $e.Effect = [System.Windows.Forms.DragDropEffects]::None
    }
})

$form.Add_DragDrop({
    param($sender, $e)
    
    if ($Script:Config.IsRunning) {
        Add-Log "Cannot change path while processing is running" "Warning"
        return
    }
    
    try {
        $droppedFiles = $e.Data.GetData([System.Windows.Forms.DataFormats]::FileDrop)
        
        if ($droppedFiles -and $droppedFiles.Count -gt 0) {
            $droppedPath = $droppedFiles[0]
            
            # Check if it's a file or folder
            if (Test-Path $droppedPath -PathType Container) {
                # It's a folder
                $Script:Config.Path = $droppedPath
                Add-Log "Dropped folder: $droppedPath" "Success"
                $statusLabel.Text = "Ready to process: $droppedPath"
                Update-Progress 0 "Ready" "Ready"
            } elseif (Test-Path $droppedPath -PathType Leaf) {
                # It's a file - use its parent directory
                $Script:Config.Path = Split-Path -Parent $droppedPath
                Add-Log "Dropped file: $droppedPath" "Info"
                Add-Log "Using parent folder: $($Script:Config.Path)" "Info"
                $statusLabel.Text = "Ready to process: $($Script:Config.Path)"
                Update-Progress 0 "Ready" "Ready"
            } else {
                Add-Log "Invalid path: $droppedPath" "Error"
            }
        }
    } catch {
        Add-Log "Error handling drag and drop: $_" "Error"
    }
})

# Add visual feedback for drag and drop
$form.Add_DragEnter({
    param($sender, $e)
    if (-not $Script:Config.IsRunning -and $e.Data.GetDataPresent([System.Windows.Forms.DataFormats]::FileDrop)) {
        $form.BackColor = [System.Drawing.Color]::LightBlue
    }
})

$form.Add_DragLeave({
    param($sender, $e)
    $form.BackColor = [System.Drawing.SystemColors]::Control
})

$form.Add_DragDrop({
    param($sender, $e)
    $form.BackColor = [System.Drawing.SystemColors]::Control
})

# ============================================================================
# MAIN PROCESSING
# ============================================================================

$stopButton.Add_Click({
    $Script:Config.ShouldStop = $true
    $stopButton.Enabled = $false
    Add-Log "Stop requested by user..." "Warning"
})

$closeButton.Add_Click({
    if ($Script:Config.IsRunning) {
        $Script:Config.ShouldStop = $true
    } else {
        $form.Close()
    }
})

# Add a "Start Processing" button that appears when path is set
$startButton = New-Object System.Windows.Forms.Button
$startButton.Location = New-Object System.Drawing.Point(130, 630)
$startButton.Size = New-Object System.Drawing.Size(150, 30)
$startButton.Text = "Start Processing"
$startButton.Enabled = $false
$startButton.Visible = $false
$form.Controls.Add($startButton)

# Update start button visibility when path changes
function Update-StartButton {
    if ($Script:Config.Path -and (Test-Path $Script:Config.Path) -and -not $Script:Config.IsRunning) {
        $startButton.Enabled = $true
        $startButton.Visible = $true
    } else {
        $startButton.Enabled = $false
        $startButton.Visible = $false
    }
}

$startButton.Add_Click({
    if (-not $Script:Config.IsRunning -and $Script:Config.Path -and (Test-Path $Script:Config.Path)) {
        # Start processing with current path
        Start-Processing
    }
})

function Start-Processing {
    if ($Script:Config.IsRunning) {
        return
    }
    
    $Script:Config.IsRunning = $true
    $startButton.Enabled = $false
    $stopButton.Enabled = $true
    $closeButton.Enabled = $false
    
    # Clear log
    $logBox.Clear()
    
    # Start processing thread (reuse existing thread logic)
    if ($processingThread -and $processingThread.IsAlive) {
        $processingThread.Abort()
    }
    
    $processingThread = [System.Threading.Thread]::new({
        param($Config, $Form, $LogBox, $ProgressBar, $StatusLabel, $TimeLabel, $StatsLabel)
        
        $Script:Config = $Config
        $Script:Config.IsRunning = $true
        $Script:Config.ShouldStop = $false
        
        try {
            # Initialize
            $form.Invoke([System.Action]{
                Add-Log "Starting AI Implementation Tool..." "Info"
                Update-Progress 0 "Initializing..." "Initializing"
            })
            
            # Resolve path
            $resolvedPath = Resolve-Path $Script:Config.Path -ErrorAction SilentlyContinue
            if (-not $resolvedPath) {
                $form.Invoke([System.Action]{
                    Add-Log "Path not found: $($Script:Config.Path)" "Error"
                })
                return
            }
            
            $Script:Config.Path = $resolvedPath.Path
            $form.Invoke([System.Action]{
                Add-Log "Processing: $($Script:Config.Path)" "Info"
                Update-Progress 5 "Detecting API version..." "Detecting"
            })
            
            # Detect API version
            $apiVersion = Get-ApiVersion -SearchPath $Script:Config.Path
            $form.Invoke([System.Action]{
                Add-Log "API Version: $apiVersion" "Info"
                Update-Progress 10 "Checking AI availability..." "Checking"
            })
            
            # Check AI availability
            if (-not (Test-OllamaAvailable)) {
                $form.Invoke([System.Action]{
                    Add-Log "Ollama not available - cannot proceed" "Error"
                })
                return
            }
            
            $form.Invoke([System.Action]{
                Add-Log "Ollama service is available" "Success"
                Update-Progress 15 "Scanning files..." "Scanning"
            })
            
            # Check if log file is provided
            $logChanges = $null
            if ($Script:Config.LogFile -and (Test-Path $Script:Config.LogFile)) {
                $form.Invoke([System.Action]{
                    Add-Log "Loading changes from log file: $($Script:Config.LogFile)" "Info"
                    Update-Progress 12 "Loading log file..." "Loading"
                })
                $logChanges = Parse-LogFile -LogFilePath $Script:Config.LogFile
                if ($logChanges -and $logChanges.Count -gt 0) {
                    $form.Invoke([System.Action]{
                        Add-Log "Loaded $($logChanges.Count) changes from log file" "Success"
                        Add-Log "Will implement changes one by one" "Info"
                    })
                } else {
                    $form.Invoke([System.Action]{
                        Add-Log "No changes found in log file, falling back to AI analysis" "Warning"
                    })
                    $logChanges = $null
                }
            }
            
            # Get files to process
            $allFiles = Get-ChildItem -Path $Script:Config.Path -Recurse -Include "*.cpp", "*.h", "*.hpp" -ErrorAction SilentlyContinue | Where-Object { -not $_.PSIsContainer }
            $Script:Config.TotalFiles = $allFiles.Count
            
            $form.Invoke([System.Action]{
                Add-Log "Found $($Script:Config.TotalFiles) files to process" "Info"
            })
            
            if ($Script:Config.TotalFiles -eq 0) {
                $form.Invoke([System.Action]{
                    Add-Log "No files found to process" "Warning"
                    Update-Progress 100 "Complete" "Complete"
                })
                return
            }
            
            # Process files
            foreach ($file in $allFiles) {
                if ($Script:Config.ShouldStop) {
                    $form.Invoke([System.Action]{
                        Add-Log "Processing stopped by user" "Warning"
                    })
                    break
                }
                
                $Script:Config.FileIndex++
                $percent = 15 + ([int](($Script:Config.FileIndex / $Script:Config.TotalFiles) * 85))
                $Script:Config.CurrentFile = $file.Name
                
                $form.Invoke([System.Action]{
                    Add-Log "Processing: $($file.Name) ($($Script:Config.FileIndex)/$($Script:Config.TotalFiles))" "Info"
                    Update-Progress $percent "Processing: $($file.Name)" "Processing"
                })
                
                try {
                    # Use log file changes if available, otherwise use AI
                    if ($logChanges -and $logChanges.Count -gt 0) {
                        $result = Process-FileWithLogChanges -FilePath $file.FullName -LogChanges $logChanges
                    } else {
                        $result = Process-FileWithAI -FilePath $file.FullName -ApiVersion $apiVersion
                    }
                    
                    $Script:Config.FilesProcessed++
                    
                    if ($result.Modified) {
                        $Script:Config.FilesModified++
                        $Script:Config.TotalChanges += $result.Changes
                        
                        $form.Invoke([System.Action]{
                            Add-Log "  Modified: $($result.Changes) change(s)" "Success"
                            foreach ($log in $result.ChangeLog) {
                                Add-Log "    $log" "Info"
                            }
                        })
                        
                        # Save file if not dry run
                        if (-not $Script:Config.DryRun) {
                            if ($Script:Config.Backup) {
                                Copy-Item -Path $file.FullName -Destination "$($file.FullName).backup" -Force -ErrorAction SilentlyContinue
                            }
                            [System.IO.File]::WriteAllText($file.FullName, $result.Content, [System.Text.Encoding]::UTF8)
                            $form.Invoke([System.Action]{
                                Add-Log "  Saved changes" "Success"
                            })
                        } else {
                            $form.Invoke([System.Action]{
                                Add-Log "  (Dry run - changes not saved)" "Info"
                            })
                        }
                    } else {
                        $form.Invoke([System.Action]{
                            Add-Log "  No changes needed" "Info"
                        })
                    }
                    
                } catch {
                    $form.Invoke([System.Action]{
                        Add-Log "  Error processing $($file.Name): $_" "Error"
                    })
                }
            }
            
            # Final summary
            $form.Invoke([System.Action]{
                Update-Progress 100 "Complete" "Complete"
                Add-Log "`nAI implementation complete!" "Success"
                Add-Log "Files Processed: $($Script:Config.FilesProcessed)" "Info"
                Add-Log "Files Modified: $($Script:Config.FilesModified)" "Info"
                Add-Log "Total Changes Applied: $($Script:Config.ChangesApplied)" "Info"
                Add-Log "Changes Skipped: $($Script:Config.ChangesSkipped)" "Info"
                Add-Log "AI Analyses: $($Script:Config.AIAnalyses)" "Info"
            })
            
        } catch {
            $form.Invoke([System.Action]{
                Add-Log "Fatal error: $_" "Error"
                Add-Log $_.ScriptStackTrace "Error"
            })
        } finally {
            $Script:Config.IsRunning = $false
            $form.Invoke([System.Action]{
                $stopButton.Enabled = $false
                $closeButton.Enabled = $true
                Update-StartButton
            })
        }
    })
    
    # Start processing thread
    $processingThread.IsBackground = $true
    $processingThread.Start($Script:Config, $form, $logBox, $progressBar, $statusLabel, $timeLabel, $statsLabel)
}

# Start processing in background thread
$processingThread = [System.Threading.Thread]::new({
    param($Config, $Form, $LogBox, $ProgressBar, $StatusLabel, $TimeLabel, $StatsLabel)
    
    $Script:Config = $Config
    $Script:Config.IsRunning = $true
    $Script:Config.ShouldStop = $false
    
    try {
        # Initialize
        $form.Invoke([System.Action]{
            Add-Log "Starting AI Implementation Tool..." "Info"
            Update-Progress 0 "Initializing..." "Initializing"
        })
        
        # Resolve path
        $resolvedPath = Resolve-Path $Script:Config.Path -ErrorAction SilentlyContinue
        if (-not $resolvedPath) {
            $form.Invoke([System.Action]{
                Add-Log "Path not found: $($Script:Config.Path)" "Error"
            })
            return
        }
        
        $Script:Config.Path = $resolvedPath.Path
        $form.Invoke([System.Action]{
            Add-Log "Processing: $($Script:Config.Path)" "Info"
            Update-Progress 5 "Detecting API version..." "Detecting"
        })
        
        # Detect API version
        $apiVersion = Get-ApiVersion -SearchPath $Script:Config.Path
        $form.Invoke([System.Action]{
            Add-Log "API Version: $apiVersion" "Info"
            Update-Progress 10 "Checking AI availability..." "Checking"
        })
        
        # Check AI availability
        if (-not (Test-OllamaAvailable)) {
            $form.Invoke([System.Action]{
                Add-Log "Ollama not available - cannot proceed" "Error"
            })
            return
        }
        
        $form.Invoke([System.Action]{
            Add-Log "Ollama service is available" "Success"
            Update-Progress 15 "Scanning files..." "Scanning"
        })
        
        # Get files to process
        $allFiles = Get-ChildItem -Path $Script:Config.Path -Recurse -Include "*.cpp", "*.h", "*.hpp" -ErrorAction SilentlyContinue | Where-Object { -not $_.PSIsContainer }
        $Script:Config.TotalFiles = $allFiles.Count
        
        $form.Invoke([System.Action]{
            Add-Log "Found $($Script:Config.TotalFiles) files to process" "Info"
        })
        
        if ($Script:Config.TotalFiles -eq 0) {
            $form.Invoke([System.Action]{
                Add-Log "No files found to process" "Warning"
                Update-Progress 100 "Complete" "Complete"
            })
            return
        }
        
        # Process files
        foreach ($file in $allFiles) {
            if ($Script:Config.ShouldStop) {
                $form.Invoke([System.Action]{
                    Add-Log "Processing stopped by user" "Warning"
                })
                break
            }
            
            $Script:Config.FileIndex++
            $percent = 15 + ([int](($Script:Config.FileIndex / $Script:Config.TotalFiles) * 85))
            $Script:Config.CurrentFile = $file.Name
            
            $form.Invoke([System.Action]{
                Add-Log "Processing: $($file.Name) ($($Script:Config.FileIndex)/$($Script:Config.TotalFiles))" "Info"
                Update-Progress $percent "Processing: $($file.Name)" "Processing"
            })
            
            try {
                $result = Process-FileWithAI -FilePath $file.FullName -ApiVersion $apiVersion
                
                $Script:Config.FilesProcessed++
                
                if ($result.Modified) {
                    $Script:Config.FilesModified++
                    $Script:Config.TotalChanges += $result.Changes
                    
                    $form.Invoke([System.Action]{
                        Add-Log "  Modified: $($result.Changes) change(s)" "Success"
                        foreach ($log in $result.ChangeLog) {
                            Add-Log "    $log" "Info"
                        }
                    })
                    
                    # Save file if not dry run
                    if (-not $Script:Config.DryRun) {
                        if ($Script:Config.Backup) {
                            Copy-Item -Path $file.FullName -Destination "$($file.FullName).backup" -Force -ErrorAction SilentlyContinue
                        }
                        [System.IO.File]::WriteAllText($file.FullName, $result.Content, [System.Text.Encoding]::UTF8)
                        $form.Invoke([System.Action]{
                            Add-Log "  Saved changes" "Success"
                        })
                    } else {
                        $form.Invoke([System.Action]{
                            Add-Log "  (Dry run - changes not saved)" "Info"
                        })
                    }
                } else {
                    $form.Invoke([System.Action]{
                        Add-Log "  No changes needed" "Info"
                    })
                }
                
            } catch {
                $form.Invoke([System.Action]{
                    Add-Log "  Error processing $($file.Name): $_" "Error"
                })
            }
        }
        
        # Final summary
        $form.Invoke([System.Action]{
            Update-Progress 100 "Complete" "Complete"
            Add-Log "`nAI implementation complete!" "Success"
            Add-Log "Files Processed: $($Script:Config.FilesProcessed)" "Info"
            Add-Log "Files Modified: $($Script:Config.FilesModified)" "Info"
            Add-Log "Total Changes Applied: $($Script:Config.ChangesApplied)" "Info"
            Add-Log "Changes Skipped: $($Script:Config.ChangesSkipped)" "Info"
            Add-Log "AI Analyses: $($Script:Config.AIAnalyses)" "Info"
        })
        
    } catch {
        $form.Invoke([System.Action]{
            Add-Log "Fatal error: $_" "Error"
            Add-Log $_.ScriptStackTrace "Error"
        })
    } finally {
        $Script:Config.IsRunning = $false
        $form.Invoke([System.Action]{
            $stopButton.Enabled = $false
            $closeButton.Enabled = $true
        })
    }
})

# Initialize start button state
Update-StartButton

# If path was provided via parameter and is valid, auto-start
if ($Script:Config.Path -and (Test-Path $Script:Config.Path) -and -not $Script:Config.Path -eq ".") {
    # Auto-start processing if valid path provided
    $form.Add_Shown({
        Start-Processing
    })
} else {
    # Show instructions if no path provided
    $form.Add_Shown({
        Add-Log "Drag and drop a folder or file to begin, or use -Path parameter" "Info"
        Add-Log "The tool will process all C++ files (.cpp, .h, .hpp) in the selected folder" "Info"
        Update-StartButton
    })
}

# Show form
$form.Add_FormClosing({
    if ($Script:Config.IsRunning) {
        $Script:Config.ShouldStop = $true
        if ($processingThread -and $processingThread.IsAlive) {
            $processingThread.Join(2000)
        }
    }
})

$form.ShowDialog() | Out-Null


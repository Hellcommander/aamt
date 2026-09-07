# ============================================================================
# AutoUpdate-CPP20-API-GUI.ps1
# ============================================================================
# GUI version with progress tracking and infinite loop prevention
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
    [switch]$SkipOnlineCheck = $false,
    
    [Parameter(Mandatory=$false)]
    [switch]$UseAI = $true,
    
    [Parameter(Mandatory=$false)]
    [string]$OllamaModel = "codellama:34b",  # Consider "codellama:13b" or "codellama:7b" for faster processing
    
    [Parameter(Mandatory=$false)]
    [string]$OllamaUrl = "http://localhost:11434",
    
    [Parameter(Mandatory=$false)]
    [switch]$FastMode = $false,  # Skip AI verification for known-safe changes (much faster)
    
    [Parameter(Mandatory=$false)]
    [int]$MaxAITimePerFile = 120,  # Reduced from 300s (5 min) to 120s (2 min) for faster processing
    
    [Parameter(Mandatory=$false)]
    [int]$MaxTotalTime = 3600,  # 1 hour max total time
    
    [Parameter(Mandatory=$false)]
    [int]$MaxIterations = 3  # Max iterations per file to prevent infinite loops
)

# Force STA mode for GUI
if ([System.Threading.Thread]::CurrentThread.GetApartmentState() -ne [System.Threading.ApartmentState]::STA) {
    Write-Host "ERROR: Must run in STA mode for GUI" -ForegroundColor Red
    Write-Host "Run with: powershell -STA -File AutoUpdate-CPP20-API-GUI.ps1" -ForegroundColor Yellow
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
    SkipOnlineCheck = $SkipOnlineCheck
    UseAI = $UseAI
    OllamaModel = $OllamaModel
    OllamaUrl = $OllamaUrl
    OllamaApiUrl = "$OllamaUrl/api"
    FastMode = $FastMode
    ApiVersion = $null
    FilesProcessed = 0
    FilesModified = 0
    TotalChanges = 0
    MigrationRules = @()
    AIVerifications = 0
    AISuggestions = 0
    MaxAITimePerFile = $MaxAITimePerFile
    MaxTotalTime = $MaxTotalTime
    MaxIterations = $MaxIterations
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
$form.Text = "Auto C++20 Migration Tool - Progress"
$form.Size = New-Object System.Drawing.Size(1000, 700)
$form.StartPosition = "CenterScreen"
$form.FormBorderStyle = "FixedDialog"
$form.MaximizeBox = $false
$form.MinimizeBox = $false

# Title
$titleLabel = New-Object System.Windows.Forms.Label
$titleLabel.Location = New-Object System.Drawing.Point(20, 10)
$titleLabel.Size = New-Object System.Drawing.Size(960, 30)
$titleLabel.Font = New-Object System.Drawing.Font("Segoe UI", 14, [System.Drawing.FontStyle]::Bold)
$titleLabel.Text = "Auto C++20 Migration Tool"
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
$statsLabel.Text = "Files Processed: 0 | Files Modified: 0 | Changes: 0 | AI Verifications: 0"
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
    $statsLabel.Text = "Files: $($Script:Config.FileIndex)/$($Script:Config.TotalFiles) | Modified: $($Script:Config.FilesModified) | Changes: $($Script:Config.TotalChanges) | AI: $($Script:Config.AIVerifications)"
    
    [System.Windows.Forms.Application]::DoEvents()
}

function Test-TimeLimit {
    $elapsed = (Get-Date) - $Script:Config.StartTime
    if ($elapsed.TotalSeconds -gt $Script:Config.MaxTotalTime) {
        Add-Log "Maximum time limit ($($Script:Config.MaxTotalTime)s) exceeded!" "Error"
        return $false
    }
    return $true
}

# ============================================================================
# LOAD MAIN SCRIPT FUNCTIONS (from AutoUpdate-CPP20-API.ps1)
# ============================================================================

$mainScriptPath = Join-Path $PSScriptRoot "AutoUpdate-CPP20-API.ps1"
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

# Dot-source the main script with GuiMode=true to load functions without executing main code
. $mainScriptPath -Path $Script:Config.Path -DryRun:$Script:Config.DryRun -Backup:$Script:Config.Backup -ShowDetails:$Script:Config.Verbose -SkipOnlineCheck:$Script:Config.SkipOnlineCheck -UseAI:$Script:Config.UseAI -OllamaModel $Script:Config.OllamaModel -OllamaUrl $Script:Config.OllamaUrl -FastMode:$Script:Config.FastMode -MaxAITimePerFile $MaxAITimePerFile -MaxTotalTime $MaxTotalTime -MaxIterations $MaxIterations -GuiMode:$true

# Pass timeout settings to main script config (ensure they're set)
$Script:Config.MaxAITimePerFile = $MaxAITimePerFile
$Script:Config.MaxTotalTime = $MaxTotalTime
$Script:Config.MaxIterations = $MaxIterations

# Re-override Write-Status after sourcing (in case it was redefined)
function Write-Status {
    param(
        [string]$Message,
        [string]$Type = "Info"
    )
    Add-Log $Message $Type
}

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

# Start processing in background thread using RunspacePool (PowerShell-native threading)
# Create runspace pool for background processing
$runspacePool = [RunspaceFactory]::CreateRunspacePool(1, 1)
$runspacePool.ApartmentState = [System.Threading.ApartmentState]::STA
$runspacePool.ThreadOptions = [System.Management.Automation.Runspaces.PSThreadOptions]::UseNewThread
$runspacePool.Open()

# Create scriptblock that will run in the runspace (pass variables as parameters)
$threadScriptBlock = {
    param(
        [hashtable]$Config,
        [System.Windows.Forms.Form]$Form,
        [System.Windows.Forms.RichTextBox]$LogBox,
        [System.Windows.Forms.ProgressBar]$ProgressBar,
        [System.Windows.Forms.Label]$StatusLabel,
        [System.Windows.Forms.Label]$TimeLabel,
        [System.Windows.Forms.Label]$StatsLabel,
        [System.Windows.Forms.Button]$StopButton,
        [System.Windows.Forms.Button]$CloseButton,
        [string]$MainScriptPath
    )
    
    # Set variables in script scope
    $Script:Config = $Config
    $Script:Config.IsRunning = $true
    $Script:Config.ShouldStop = $false
    
    $form = $Form
    $logBox = $LogBox
    $progressBar = $ProgressBar
    $statusLabel = $StatusLabel
    $timeLabel = $TimeLabel
    $statsLabel = $StatsLabel
    $stopButton = $StopButton
    $closeButton = $CloseButton
    $mainScriptPath = $MainScriptPath
    
    try {
        # Initialize
        $form.Invoke([System.Action]{
            Add-Log "Starting C++20 Migration Tool..." "Info"
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
        $Script:Config.ApiVersion = Get-ApiVersion -SearchPath $Script:Config.Path
        $form.Invoke([System.Action]{
            Add-Log "API Version: $($Script:Config.ApiVersion)" "Info"
            Update-Progress 10 "Loading migration rules..." "Loading"
        })
        
        # Load migration rules
        $Script:Config.MigrationRules = Get-Cpp20MigrationRules -ApiVersion $Script:Config.ApiVersion
        $form.Invoke([System.Action]{
            Add-Log "Loaded $($Script:Config.MigrationRules.Count) migration rules" "Info"
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
        
        # Process files with progress tracking and infinite loop prevention
        $iterationCount = @{}  # Track iterations per file
        
        foreach ($file in $allFiles) {
            if ($Script:Config.ShouldStop -or -not (Test-TimeLimit)) {
                $form.Invoke([System.Action]{
                    Add-Log "Processing stopped by user or time limit" "Warning"
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
            
            # Prevent infinite loops - max iterations per file
            if (-not $iterationCount.ContainsKey($file.FullName)) {
                $iterationCount[$file.FullName] = 0
            }
            
            if ($iterationCount[$file.FullName] -ge $Script:Config.MaxIterations) {
                $form.Invoke([System.Action]{
                    Add-Log "  Skipping $($file.Name) - max iterations ($($Script:Config.MaxIterations)) reached" "Warning"
                })
                continue
            }
            
            $iterationCount[$file.FullName]++
            
            try {
                # Apply migration rules directly (same as batch version for speed)
                # Direct execution is faster than jobs - jobs add ~100-500ms overhead per file
                # Timeout protection is handled within Apply-MigrationRules via AI job timeouts
                $result = Apply-MigrationRules -FilePath $file.FullName -Rules $Script:Config.MigrationRules
                
                $Script:Config.FilesProcessed++
                
                if ($result.Modified) {
                    $Script:Config.FilesModified++
                    $Script:Config.TotalChanges += $result.Changes
                    
                    $form.Invoke([System.Action]{
                        Add-Log "  Modified: $($result.Changes) changes" "Success"
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
                    
                    # AI suggestions
                    if ($result.AIAnalysis) {
                        $Script:Config.AIVerifications++
                        if ($result.AIAnalysis.Suggestions.Count -gt 0) {
                            $Script:Config.AISuggestions++
                            $form.Invoke([System.Action]{
                                Add-Log "  AI Suggestions:" "Info"
                                foreach ($suggestion in $result.AIAnalysis.Suggestions) {
                                    Add-Log "    + $suggestion" "Info"
                                }
                            })
                        }
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
            Add-Log "`nMigration complete!" "Success"
            Add-Log "Files Processed: $($Script:Config.FilesProcessed)" "Info"
            Add-Log "Files Modified: $($Script:Config.FilesModified)" "Info"
            Add-Log "Total Changes: $($Script:Config.TotalChanges)" "Info"
            Add-Log "AI Verifications: $($Script:Config.AIVerifications)" "Info"
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
}

# Submit scriptblock to runspace pool (PowerShell-native background processing)
# Convert scriptblock to string and add parameters
$scriptText = $threadScriptBlock.ToString()
$powershell = [PowerShell]::Create()
$powershell.RunspacePool = $runspacePool
$null = $powershell.AddScript($scriptText)
$null = $powershell.AddArgument($Script:Config)
$null = $powershell.AddArgument($form)
$null = $powershell.AddArgument($logBox)
$null = $powershell.AddArgument($progressBar)
$null = $powershell.AddArgument($statusLabel)
$null = $powershell.AddArgument($timeLabel)
$null = $powershell.AddArgument($statsLabel)
$null = $powershell.AddArgument($stopButton)
$null = $powershell.AddArgument($closeButton)
$null = $powershell.AddArgument($mainScriptPath)

# Start processing asynchronously
$asyncResult = $powershell.BeginInvoke()
$stopButton.Enabled = $true

# Store PowerShell instance for cleanup
$script:processingPowerShell = $powershell
$script:processingRunspacePool = $runspacePool
$script:processingAsyncResult = $asyncResult

# Stop button handler
$stopButton.Add_Click({
    if ($Script:Config.IsRunning) {
        $Script:Config.ShouldStop = $true
        $stopButton.Enabled = $false
        Add-Log "Stopping processing..." "Warning"
    }
})

# Show form
$form.Add_FormClosing({
    if ($Script:Config.IsRunning) {
        $Script:Config.ShouldStop = $true
        # Wait for PowerShell to finish (with timeout)
        if ($script:processingPowerShell -and $script:processingPowerShell.InvocationStateInfo.State -eq 'Running') {
            $script:processingPowerShell.Stop()
            if ($script:processingAsyncResult) {
                $null = $script:processingPowerShell.EndInvoke($script:processingAsyncResult)
            }
        }
        # Cleanup runspace pool
        if ($script:processingRunspacePool) {
            $script:processingRunspacePool.Close()
            $script:processingRunspacePool.Dispose()
        }
    }
})

$form.ShowDialog() | Out-Null

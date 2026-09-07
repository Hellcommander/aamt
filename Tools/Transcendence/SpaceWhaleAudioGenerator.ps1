# Space Whale Audio Generator
# Generates audio assets for space whale communication system
# Enhanced with quality checking, progress tracking, and better integration

param(
    [Parameter(Mandatory=$false)]
    [string]$RegistryPath = "space_whale_audio_registry.json",
    
    [Parameter(Mandatory=$false)]
    [string]$OutputDir = "Output/Audio",
    
    [Parameter(Mandatory=$false)]
    [int]$Variations = 3,
    
    [Parameter(Mandatory=$false)]
    [ValidateSet("auto","stable-audio","library","procedural")]
    [string]$Engine = "auto",

    [Parameter(Mandatory=$false)]
    [string]$Model = "medium",

    [Parameter(Mandatory=$false)]
    [ValidateRange(0.0, 1.0)]
    [double]$Strength = 0.7,
    
    [Parameter(Mandatory=$false)]
    [switch]$SkipGeneration,
    
    [Parameter(Mandatory=$false)]
    [switch]$QualityCheck,
    
    [Parameter(Mandatory=$false)]
    [switch]$Resume,
    
    [Parameter(Mandatory=$false)]
    [switch]$SkipCompleted
)

$ErrorActionPreference = "Stop"

# Load shared asset generation settings
$settingsPath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "..\\AssetGenerationSettings.ps1"
if (Test-Path $settingsPath) {
    . $settingsPath
}

# Import CPU offload module if available
$cpuOffloadModule = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "Common\OllamaCpuOffload.psm1"
if (Test-Path $cpuOffloadModule) {
    Import-Module $cpuOffloadModule -ErrorAction SilentlyContinue
}

# Import quality system if available
$qualitySystemPath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "space_whale_quality_system.py"
if (-not (Test-Path $qualitySystemPath)) {
    $qualitySystemPath = Join-Path $PSScriptRoot "space_whale_quality_system.py"
}
$qualitySystemAvailable = Test-Path $qualitySystemPath

Write-Host "Space Whale Audio Generator (Shared SA3 + D:\assets\audio)" -ForegroundColor Cyan
Write-Host "=======================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Features:" -ForegroundColor Yellow
Write-Host "  - Retrieve from D:\assets\audio, condition Stable Audio 3 (init_audio)" -ForegroundColor Gray
Write-Host "  - 20-level quality assessment system" -ForegroundColor Gray
Write-Host "  - Progress tracking and reporting" -ForegroundColor Gray
Write-Host "  - Resume capability" -ForegroundColor Gray
Write-Host ""

# Check if registry exists
if (-not (Test-Path $RegistryPath)) {
    Write-Host "ERROR: Registry file not found: $RegistryPath" -ForegroundColor Red
    exit 1
}

# Create output directory
if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
}

# Load registry
$registry = Get-Content $RegistryPath | ConvertFrom-Json
$sounds = $registry.audio.sounds

Write-Host "Found $($sounds.Count) sound(s) in registry" -ForegroundColor Green
Write-Host ""

# Display communication channels
$channels = $registry.audio.communicationChannels
Write-Host "Communication Channels:" -ForegroundColor Yellow
foreach ($channelName in $channels.PSObject.Properties.Name) {
    $channel = $channels.$channelName
    $enabled = if ($channel.enabled) { "ENABLED" } else { "DISABLED" }
    Write-Host "  $channelName : $enabled ($($channel.range) range, $($channel.fidelity) fidelity)" -ForegroundColor Gray
}
Write-Host ""

# Check for existing outputs if resume mode
$existingFiles = @()
if ($Resume -or $SkipCompleted) {
    if (Test-Path $OutputDir) {
        $existingFiles = Get-ChildItem -Path $OutputDir -Filter "*.wav" -Recurse -ErrorAction SilentlyContinue
        if ($existingFiles.Count -gt 0) {
            Write-Host "Resume mode: Found $($existingFiles.Count) existing audio files" -ForegroundColor Yellow
            if ($SkipCompleted) {
                Write-Host "  Skipping completed sounds (use --Resume without --SkipCompleted to regenerate)" -ForegroundColor Gray
            }
        }
    }
}

if (-not $SkipGeneration) {
    # Check for Python and required libraries
    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($null -eq $python) {
        Write-Host "WARNING: Python not found. Skipping audio generation." -ForegroundColor Yellow
        Write-Host "Install Python and required libraries (numpy, soundfile, scipy)" -ForegroundColor Yellow
    } else {
        Write-Host ""
        Write-Host "Generating audio files..." -ForegroundColor Yellow
        Write-Host "  Variations per sound: $Variations" -ForegroundColor Gray
        if ($Resume) {
            Write-Host "  Resume mode: Enabled" -ForegroundColor Gray
        }
        Write-Host ""
        
        $generatorScript = "space_whale_audio_generator.py"
        # Script is already in Transcendence directory, so use current directory
        $scriptPath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) $generatorScript
        # If not found, try in current directory
        if (-not (Test-Path $scriptPath)) {
            $scriptPath = Join-Path $PSScriptRoot $generatorScript
        }
        
        if (Test-Path $scriptPath) {
            $startTime = Get-Date
            
            # Calculate total tasks for progress bar
            $totalTasks = $sounds.Count * $Variations
            if ($Variations -eq 1) {
                $totalTasks = $sounds.Count
            }
            
            try {
                # Build command arguments
                $scriptArgs = @(
                    $scriptPath,
                    "--registry", $RegistryPath,
                    "--output", $OutputDir,
                    "--variations", $Variations,
                    "--engine", $Engine,
                    "--strength", "$Strength"
                )
                if ($Model) {
                    $scriptArgs += @("--model", $Model)
                }
                
                # Add resume flag if specified
                if ($Resume) {
                    $scriptArgs += "--resume"
                }
                if ($SkipCompleted) {
                    $scriptArgs += "--skip-completed"
                }
                
                Write-Host "Running: python $($scriptArgs -join ' ')" -ForegroundColor DarkGray
                Write-Host ""
                
                # Create process to capture output in real-time
                $processInfo = New-Object System.Diagnostics.ProcessStartInfo
                $processInfo.FileName = "python"
                $processInfo.Arguments = ($scriptArgs | ForEach-Object { if ($_ -match '\s') { "`"$_`"" } else { $_ } }) -join ' '
                $processInfo.UseShellExecute = $false
                $processInfo.RedirectStandardOutput = $true
                $processInfo.RedirectStandardError = $true
                $processInfo.CreateNoWindow = $true
                
                $process = New-Object System.Diagnostics.Process
                $process.StartInfo = $processInfo
                
                # String builders for output
                $outputBuilder = New-Object System.Text.StringBuilder
                $errorBuilder = New-Object System.Text.StringBuilder
                
                # Progress tracking
                $currentProgress = 0
                $lastProgressUpdate = 0
                
                # Event handlers for real-time output
                $outputHandler = {
                    if (-not [string]::IsNullOrWhiteSpace($EventArgs.Data)) {
                        $line = $EventArgs.Data
                        [void]$outputBuilder.AppendLine($line)
                        
                        # Parse progress line: "  Progress: 150/1650 (9%) [Skipped: 0]"
                        if ($line -match 'Progress:\s+(\d+)/(\d+)\s+\((\d+)%\)') {
                            $currentProgress = [int]$matches[1]
                            $totalFromOutput = [int]$matches[2]
                            $percent = [int]$matches[3]
                            
                            # Update progress bar
                            $percentComplete = ($currentProgress / $totalTasks) * 100
                            $activity = "Generating Audio Files"
                            $status = "Progress: $currentProgress/$totalTasks ($([math]::Round($percentComplete, 1))%)"
                            
                            Write-Progress -Activity $activity -Status $status -PercentComplete $percentComplete
                            $lastProgressUpdate = $currentProgress
                        } elseif ($line -match '\[OK\]|✓|Generated:') {
                            # Show individual file generation without blocking progress
                            # (progress bar handles the main display)
                        } else {
                            # Show other output lines
                            Write-Host $line
                        }
                    }
                }
                
                $errorHandler = {
                    if (-not [string]::IsNullOrWhiteSpace($EventArgs.Data)) {
                        $line = $EventArgs.Data
                        [void]$errorBuilder.AppendLine($line)
                        Write-Host $line -ForegroundColor Red
                    }
                }
                
                # Register event handlers
                $eventOutput = Register-ObjectEvent -InputObject $process -EventName OutputDataReceived -Action $outputHandler
                $eventError = Register-ObjectEvent -InputObject $process -EventName ErrorDataReceived -Action $errorHandler
                
                # Start process
                [void]$process.Start()
                $process.BeginOutputReadLine()
                $process.BeginErrorReadLine()
                
                # Wait for completion with timeout (optional - set to 0 for no timeout)
                $process.WaitForExit()
                
                # Unregister events
                Unregister-Event -SourceIdentifier $eventOutput.Name
                Unregister-Event -SourceIdentifier $eventError.Name
                
                # Complete progress bar
                Write-Progress -Activity "Generating Audio Files" -Completed
                
                $exitCode = $process.ExitCode
                $endTime = Get-Date
                $duration = ($endTime - $startTime).TotalSeconds
                
                # Get remaining output
                $remainingOutput = $outputBuilder.ToString()
                if ($remainingOutput) {
                    $remainingOutput -split "`n" | Where-Object { $_ -notmatch 'Progress:' } | ForEach-Object {
                        if ($_ -notmatch '^\s*$') {
                            Write-Host $_
                        }
                    }
                }
                
                Write-Host ""
                if ($exitCode -eq 0) {
                    Write-Host "✓ Audio generation complete!" -ForegroundColor Green
                    Write-Host "  Duration: $([math]::Round($duration, 1)) seconds" -ForegroundColor Gray
                    Write-Host "  Files processed: $currentProgress/$totalTasks" -ForegroundColor Gray
                    
                    # Count generated files
                    $generatedFiles = Get-ChildItem -Path $OutputDir -Filter "*.wav" -Recurse -ErrorAction SilentlyContinue
                    if ($generatedFiles) {
                        Write-Host "  Generated files: $($generatedFiles.Count)" -ForegroundColor Gray
                    }
                } else {
                    Write-Host "⚠ WARNING: Audio generation may have failed (exit code: $exitCode)" -ForegroundColor Yellow
                    $errorOutput = $errorBuilder.ToString()
                    if ($errorOutput) {
                        Write-Host "Error output:" -ForegroundColor Red
                        Write-Host $errorOutput -ForegroundColor Red
                    }
                }
            } catch {
                Write-Host ""
                Write-Host "✗ ERROR: Audio generation failed: $_" -ForegroundColor Red
                Write-Host "Exception Type: $($_.Exception.GetType().FullName)" -ForegroundColor Gray
                Write-Host "Stack: $($_.ScriptStackTrace)" -ForegroundColor Gray
                if ($_.Exception.InnerException) {
                    Write-Host "Inner Exception: $($_.Exception.InnerException.Message)" -ForegroundColor Gray
                }
            }
        } else {
            Write-Host "WARNING: Generator script not found: $scriptPath" -ForegroundColor Yellow
        }
    }
}

# Quality checking
if ($QualityCheck -or $qualitySystemAvailable) {
    Write-Host ""
    Write-Host "Quality Assessment:" -ForegroundColor Yellow
    
    # Check if quality checker script exists
    $qualityCheckerScript = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "space_whale_quality_checker.py"
    # If not found, try in current directory
    if (-not (Test-Path $qualityCheckerScript)) {
        $qualityCheckerScript = Join-Path $PSScriptRoot "space_whale_quality_checker.py"
    }
    if (Test-Path $qualityCheckerScript) {
        try {
            $qualityOutputDir = Split-Path -Parent $OutputDir
            if (-not $qualityOutputDir) {
                $qualityOutputDir = "Output"
            }
            
            Write-Host "  Running quality checker..." -ForegroundColor Gray
            $qualityOutput = & python $qualityCheckerScript --output-dir $qualityOutputDir 2>&1
            $qualityExitCode = $LASTEXITCODE
            
            if ($qualityOutput) {
                Write-Host $qualityOutput
            }
            
            if ($qualityExitCode -eq 0) {
                Write-Host "  ✓ Quality check complete" -ForegroundColor Green
            }
        } catch {
            Write-Host "  ⚠ Quality check error: $_" -ForegroundColor Yellow
        }
    } else {
        Write-Host "  Quality checker script not found (optional)" -ForegroundColor Gray
    }
}

# Display sound list
Write-Host ""
Write-Host "Sound Definitions:" -ForegroundColor Yellow
foreach ($sound in $sounds) {
    $channel = $sound.channel.ToUpper()
    $type = $sound.type
    
    # Check if this sound has been generated (if resume mode)
    $soundGenerated = $false
    if ($existingFiles) {
        $soundFiles = $existingFiles | Where-Object { $_.Name -like "*$($sound.id)*" }
        if ($soundFiles) {
            $soundGenerated = $true
        }
    }
    
    $status = if ($soundGenerated) { "[EXISTS]" } else { "[PENDING]" }
    $statusColor = if ($soundGenerated) { "DarkGreen" } else { "DarkYellow" }
    
    Write-Host "  $status $($sound.id) : $($sound.name)" -ForegroundColor $statusColor
    Write-Host "    Channel: $channel, Type: $type, Duration: $($sound.duration.min)-$($sound.duration.max)s" -ForegroundColor DarkGray
    if ($soundGenerated) {
        Write-Host "    Files: $($soundFiles.Count) variations" -ForegroundColor DarkGray
    }
}

Write-Host ""
Write-Host ("=" * 60) -ForegroundColor Cyan
Write-Host "Audio registry processing complete!" -ForegroundColor Green
Write-Host "Output directory: $OutputDir" -ForegroundColor Cyan

# Summary
if (Test-Path $OutputDir) {
    $allAudioFiles = Get-ChildItem -Path $OutputDir -Filter "*.wav" -Recurse -ErrorAction SilentlyContinue
    if ($allAudioFiles) {
        Write-Host ""
        Write-Host "Summary:" -ForegroundColor Yellow
        Write-Host "  Total audio files: $($allAudioFiles.Count)" -ForegroundColor Gray
        Write-Host "  Total size: $([math]::Round(($allAudioFiles | Measure-Object -Property Length -Sum).Sum / 1MB, 2)) MB" -ForegroundColor Gray
        
        # Group by sound ID
        $soundGroups = $allAudioFiles | Group-Object { 
            if ($_.Name -match '^([^_]+)') { $matches[1] } else { "unknown" }
        }
        Write-Host "  Sounds with variations: $($soundGroups.Count)" -ForegroundColor Gray
    }
}

Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Review generated audio files" -ForegroundColor Gray
Write-Host "  2. Test audio playback and quality" -ForegroundColor Gray
if ($qualitySystemAvailable) {
    Write-Host "  3. Run quality check: .\SpaceWhaleAudioGenerator.ps1 -QualityCheck" -ForegroundColor Gray
}
Write-Host "  4. Integrate audio into game assets" -ForegroundColor Gray


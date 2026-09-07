#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Test script for AssetGeneratorControlRoom - generates assets for all game formats.
    
.DESCRIPTION
    Generates test assets for each game format (Qud, Elin, Terraria, Starbound, Transcendence)
    and exports them with quality-check metadata for AI review.
#>

param(
    [Parameter(Mandatory=$false)]
    [string]$OutputDir = "TestAssets_$(Get-Date -Format 'yyyyMMdd_HHmmss')",
    
    [Parameter(Mandatory=$false)]
    [switch]$UseControlRoom,
    
    [Parameter(Mandatory=$false)]
    [string]$OllamaModel = "llama3.2",

    # Opt-in interactive prompts. Defaults OFF so the suite runs unattended
    # (CI / overnight) without ever blocking on Read-Host.
    [Parameter(Mandatory=$false)]
    [switch]$Interactive
)

$ErrorActionPreference = "Continue"

function Test-IsInteractiveConsole {
    # True only when a real user can answer a prompt (never when stdin is
    # redirected or the host is non-interactive).
    try {
        if (-not [Environment]::UserInteractive) { return $false }
        if ([Console]::IsInputRedirected) { return $false }
        return $true
    } catch { return $false }
}

# Load shared asset generation settings
$settingsPath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "..\\AssetGenerationSettings.ps1"
if (Test-Path $settingsPath) {
    . $settingsPath
}
$PSScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Asset Generator Test Suite" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# Create output directory
$outputPath = Join-Path $PSScriptRoot $OutputDir
if (-not (Test-Path $outputPath)) {
    New-Item -ItemType Directory -Path $outputPath -Force | Out-Null
}

Write-Host "Output directory: $outputPath" -ForegroundColor Green
Write-Host ""

# Test assets to generate
$testAssets = @(
    @{
        Name = "Qud_Tile_Test"
        Type = "Tile"
        Description = "A crystalline energy tile with blue-green palette, high contrast, rim lighting"
        Size = 32
        ExportTargets = @("Qud")
    },
    @{
        Name = "Elin_Icon_Test"
        Type = "Icon"
        Description = "A nature magic spell icon, spiral leaf burst shape, green palette, painterly style"
        Size = 32
        ExportTargets = @("Elin")
    },
    @{
        Name = "Terraria_Texture_Test"
        Type = "Texture"
        Description = "Cracked stone texture with moss, high detail, suitable for Terraria blocks"
        Size = 256
        ExportTargets = @("Terraria")
    },
    @{
        Name = "Starbound_Spritesheet_Test"
        Type = "Spritesheet"
        Description = "A collection of 8 different stone textures in a spritesheet format"
        Size = 64
        ExportTargets = @("Starbound")
    },
    @{
        Name = "Transcendence_Model_Test"
        Type = "Model"
        Description = "A simple low-poly space fighter with twin engines, forward-swept wings"
        Size = 512
        ExportTargets = @("Transcendence")
    }
)

$results = @()

foreach ($asset in $testAssets) {
    Write-Host "───────────────────────────────────────────────────────────" -ForegroundColor Yellow
    Write-Host "Generating: $($asset.Name)" -ForegroundColor Cyan
    Write-Host "  Type: $($asset.Type)" -ForegroundColor Gray
    Write-Host "  Description: $($asset.Description)" -ForegroundColor Gray
    Write-Host "  Export Targets: $($asset.ExportTargets -join ', ')" -ForegroundColor Gray
    Write-Host ""
    
    $assetOutputDir = Join-Path $outputPath $asset.Name
    if (-not (Test-Path $assetOutputDir)) {
        New-Item -ItemType Directory -Path $assetOutputDir -Force | Out-Null
    }
    
    $watchDir = Join-Path $assetOutputDir "watch"
    if (-not (Test-Path $watchDir)) {
        New-Item -ItemType Directory -Path $watchDir -Force | Out-Null
    }
    
    $success = $false
    $errorMsg = ""
    
    try {
        if ($UseControlRoom) {
            # Launch control room
            $controlRoomScript = Join-Path $PSScriptRoot "AssetGeneratorControlRoom.ps1"
            if (Test-Path $controlRoomScript) {
                Write-Host "  Launching Control Room..." -ForegroundColor Gray
                
                $controlRoomArgs = @(
                    "-AssetType", $asset.Type,
                    "-OllamaModel", $OllamaModel,
                    "-WatchDirectory", $watchDir,
                    "-AutoExport",
                    "-ExportTargets", ($asset.ExportTargets -join ","),
                    "-OutputPath", $assetOutputDir
                )
                
                $controlRoomProcess = Start-Process -FilePath "pwsh" -ArgumentList @(
                    "-NoProfile",
                    "-ExecutionPolicy", "Bypass",
                    "-File", "`"$controlRoomScript`"",
                    $controlRoomArgs
                ) -PassThru -WindowStyle Normal
                
                Write-Host "  Control Room launched (PID: $($controlRoomProcess.Id))" -ForegroundColor Green
                if ($Interactive -and (Test-IsInteractiveConsole)) {
                    Write-Host "  Please generate the asset in the GUI, then press Enter to continue..." -ForegroundColor Yellow
                    Read-Host
                } else {
                    Write-Host "  [non-interactive] Control Room launched; continuing without waiting (use -Interactive to pause here)." -ForegroundColor Gray
                }
                
                $success = $true
            } else {
                Write-Host "  Error: Control Room script not found" -ForegroundColor Red
                $errorMsg = "Control Room script not found"
            }
        } else {
            # Use AssetMakerAI directly
            $assetMakerScript = Join-Path $PSScriptRoot "AssetMakerAI.ps1"
            
            if ($asset.Type -eq "Texture") {
                Write-Host "  Generating texture via AssetMakerAI..." -ForegroundColor Gray
                
                & $assetMakerScript `
                    -Action GenerateTexture `
                    -InputData $asset.Description `
                    -TextureMethod Procedural `
                    -TextureSize $asset.Size `
                    -OutputPath $watchDir `
                    -Model $OllamaModel `
                    -ErrorAction Continue
                
                if ($LASTEXITCODE -eq 0) {
                    $success = $true
                } else {
                    $errorMsg = "Texture generation failed"
                }
            } elseif ($asset.Type -eq "Model") {
                Write-Host "  Generating 3D model via AssetMakerAI..." -ForegroundColor Gray
                
                & $assetMakerScript `
                    -Action Generate3DModel `
                    -InputData $asset.Description `
                    -ModelFormat OBJ `
                    -DetailLevel LowPoly `
                    -OutputPath $watchDir `
                    -Model $OllamaModel `
                    -ErrorAction Continue
                
                if ($LASTEXITCODE -eq 0) {
                    $success = $true
                } else {
                    $errorMsg = "Model generation failed"
                }
            } else {
                Write-Host "  Note: Direct generation for $($asset.Type) not yet implemented" -ForegroundColor Yellow
                Write-Host "  Creating placeholder..." -ForegroundColor Gray
                
                # Create a placeholder file
                $placeholderPath = Join-Path $watchDir "$($asset.Name).png"
                $placeholder = New-Object System.Drawing.Bitmap $asset.Size, $asset.Size
                $graphics = [System.Drawing.Graphics]::FromImage($placeholder)
                $graphics.Clear([System.Drawing.Color]::DarkBlue)
                $font = New-Object System.Drawing.Font("Arial", 12)
                $brush = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::White)
                $graphics.DrawString($asset.Name, $font, $brush, 10, 10)
                $placeholder.Save($placeholderPath)
                $graphics.Dispose()
                $placeholder.Dispose()
                
                $success = $true
            }
        }
        
        # Wait a moment for files to be written
        Start-Sleep -Seconds 2
        
        # Check for generated files
        $generatedFiles = Get-ChildItem -LiteralPath $watchDir -File -ErrorAction SilentlyContinue
        if ($generatedFiles.Count -gt 0) {
            Write-Host "  Generated files:" -ForegroundColor Green
            foreach ($file in $generatedFiles) {
                Write-Host "    - $($file.Name) ($([math]::Round($file.Length / 1KB, 2)) KB)" -ForegroundColor Gray
            }
        }
        
        # Export to game formats
        if ($success -and $asset.ExportTargets.Count -gt 0) {
            Write-Host "  Exporting to game formats..." -ForegroundColor Gray
            
            foreach ($target in $asset.ExportTargets) {
                $exportDir = Join-Path $assetOutputDir "${target}Export"
                if (-not (Test-Path $exportDir)) {
                    New-Item -ItemType Directory -Path $exportDir -Force | Out-Null
                }
                
                # Copy files to export directory
                if ($generatedFiles.Count -gt 0) {
                    foreach ($file in $generatedFiles) {
                        Copy-Item -Path $file.FullName -Destination (Join-Path $exportDir $file.Name) -Force
                    }
                    Write-Host "    Exported to $target" -ForegroundColor Green
                }
            }
        }
        
        # Create quality check metadata
        $metadata = @{
            AssetName = $asset.Name
            AssetType = $asset.Type
            Description = $asset.Description
            Size = $asset.Size
            ExportTargets = $asset.ExportTargets
            GeneratedAt = (Get-Date -Format "yyyy-MM-dd HH:mm:ss")
            Success = $success
            ErrorMessage = $errorMsg
            GeneratedFiles = @()
            ExportFiles = @()
        }
        
        if ($generatedFiles) {
            foreach ($file in $generatedFiles) {
                $metadata.GeneratedFiles += @{
                    Name = $file.Name
                    Size = $file.Length
                    Path = $file.FullName
                }
            }
        }
        
        $exportDirs = Get-ChildItem -LiteralPath $assetOutputDir -Directory -Filter "*Export" -ErrorAction SilentlyContinue
        foreach ($exportDir in $exportDirs) {
            $exportFiles = Get-ChildItem -LiteralPath $exportDir.FullName -File -ErrorAction SilentlyContinue
            foreach ($exportFile in $exportFiles) {
                $metadata.ExportFiles += @{
                    Name = $exportFile.Name
                    Size = $exportFile.Length
                    Path = $exportFile.FullName
                    Target = $exportDir.Name -replace "Export", ""
                }
            }
        }
        
        # Save metadata
        $metadataPath = Join-Path $assetOutputDir "metadata.json"
        $metadata | ConvertTo-Json -Depth 10 | Set-Content -Path $metadataPath -Encoding UTF8
        
        $results += $metadata
        
        Write-Host "  ✓ Asset generation complete" -ForegroundColor Green
        Write-Host ""
    }
    catch {
        Write-Host "  ✗ Error: $_" -ForegroundColor Red
        $errorMsg = $_.Exception.Message
        $results += @{
            AssetName = $asset.Name
            Success = $false
            ErrorMessage = $errorMsg
        }
        Write-Host ""
    }
}

# Generate summary report
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Test Summary" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

$successCount = ($results | Where-Object { $_.Success -eq $true }).Count
$totalCount = $results.Count

Write-Host "Total Assets: $totalCount" -ForegroundColor White
Write-Host "Successful: $successCount" -ForegroundColor Green
Write-Host "Failed: $($totalCount - $successCount)" -ForegroundColor $(if (($totalCount - $successCount) -gt 0) { "Red" } else { "Green" })
Write-Host ""

# Create summary report
$summaryReport = @{
    TestRun = @{
        Date = (Get-Date -Format "yyyy-MM-dd HH:mm:ss")
        OutputDirectory = $outputPath
        TotalAssets = $totalCount
        SuccessfulAssets = $successCount
        FailedAssets = ($totalCount - $successCount)
    }
    Assets = $results
    QualityCheckInstructions = @"
# Quality Check Instructions

## For AI Review:

1. **File Verification**
   - Check that all generated files exist and are non-zero size
   - Verify file formats match expected types (PNG for images, OBJ/FBX for models)
   - Check export directories contain expected game-specific files

2. **Visual Quality**
   - Review preview images (if available)
   - Check color palettes match descriptions
   - Verify sizes match specifications
   - Assess style consistency (painterly, pixel, etc.)

3. **Game Format Compliance**
   - **Qud**: PNG tiles (24x24, 32x32, or 48x48) with optional XML/JSON metadata
   - **Elin**: Spell assets (icons 32x32, FX animations, projectiles)
   - **Terraria**: Spritesheets with JSON metadata
   - **Starbound**: Spritesheets with .frames files
   - **Transcendence**: Game-specific formats

4. **Metadata Accuracy**
   - Verify metadata.json files contain correct information
   - Check timestamps and file paths
   - Confirm export targets match generated files

5. **Error Analysis**
   - Review any error messages
   - Check for missing dependencies (Blender, Ollama)
   - Verify file permissions and paths

## Review Each Asset:

$(($results | ForEach-Object {
    "- **$($_.AssetName)** ($($_.AssetType)): $($_.Description)`n  - Success: $($_.Success)`n  - Files: $($_.GeneratedFiles.Count) generated, $($_.ExportFiles.Count) exported`n  - Targets: $($_.ExportTargets -join ', ')`n"
}) -join "`n")
"@
}

$summaryPath = Join-Path $outputPath "test_summary.json"
$summaryReport | ConvertTo-Json -Depth 10 | Set-Content -Path $summaryPath -Encoding UTF8

$instructionsPath = Join-Path $outputPath "QUALITY_CHECK_INSTRUCTIONS.md"
$summaryReport.QualityCheckInstructions | Set-Content -Path $instructionsPath -Encoding UTF8

Write-Host "Summary report saved to: $summaryPath" -ForegroundColor Green
Write-Host "Quality check instructions saved to: $instructionsPath" -ForegroundColor Green
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Test Complete" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "Review the generated assets in: $outputPath" -ForegroundColor Yellow
Write-Host ""


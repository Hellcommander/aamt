#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Generate quality test assets for all game formats with proper generation.
#>

param(
    [Parameter(Mandatory=$false)]
    [string]$OutputDir = "QualityTestAssets_$(Get-Date -Format 'yyyyMMdd_HHmmss')",
    
    [Parameter(Mandatory=$false)]
    [string]$OllamaModel = "wizardlm-uncensored"
)

$ErrorActionPreference = "Continue"

# Load shared asset generation settings
$settingsPath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "..\\AssetGenerationSettings.ps1"
if (Test-Path $settingsPath) {
    . $settingsPath
}
$PSScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Quality Test Asset Generation" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# Create output directory
$outputPath = Join-Path $PSScriptRoot $OutputDir
if (-not (Test-Path $outputPath)) {
    New-Item -ItemType Directory -Path $outputPath -Force | Out-Null
}

Write-Host "Output directory: $outputPath" -ForegroundColor Green
Write-Host "Using Ollama model: $OllamaModel" -ForegroundColor Green
Write-Host ""

# Test assets with proper generation
$testAssets = @(
    @{
        Name = "Qud_Tile_Crystalline"
        Type = "Tile"
        Description = "A crystalline energy tile with blue-green palette, high contrast, rim lighting"
        Size = 32
        ExportTargets = @("Qud")
        GenerateMethod = "Texture"  # Use texture generation for tiles
    },
    @{
        Name = "Elin_Icon_NatureSpell"
        Type = "Icon"
        Description = "A nature magic spell icon, spiral leaf burst shape, green palette, painterly style"
        Size = 32
        ExportTargets = @("Elin")
        GenerateMethod = "Texture"
    },
    @{
        Name = "Terraria_Texture_Stone"
        Type = "Texture"
        Description = "Cracked stone texture with moss, high detail, suitable for Terraria blocks"
        Size = 256
        ExportTargets = @("Terraria")
        GenerateMethod = "Texture"
    },
    @{
        Name = "Starbound_Spritesheet_Stones"
        Type = "Spritesheet"
        Description = "A collection of 8 different stone textures: cracked, mossy, smooth, rough, polished, volcanic, icy, and crystal"
        Size = 64
        ExportTargets = @("Starbound")
        GenerateMethod = "BatchTextures"
    }
)

$results = @()

foreach ($asset in $testAssets) {
    Write-Host "───────────────────────────────────────────────────────────" -ForegroundColor Yellow
    Write-Host "Generating: $($asset.Name)" -ForegroundColor Cyan
    Write-Host "  Type: $($asset.Type)" -ForegroundColor Gray
    Write-Host "  Description: $($asset.Description)" -ForegroundColor Gray
    Write-Host "  Size: $($asset.Size)" -ForegroundColor Gray
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
    $generatedFiles = @()
    
    try {
        $assetMakerScript = Join-Path $PSScriptRoot "..\Transcendence\AssetMakerAI.ps1"
        
        if ($asset.GenerateMethod -eq "Texture") {
            Write-Host "  Generating texture..." -ForegroundColor Gray
            
            & $assetMakerScript `
                -Action GenerateTexture `
                -InputData $asset.Description `
                -TextureMethod Procedural `
                -TextureSize $asset.Size `
                -OutputPath $watchDir `
                -Model $OllamaModel `
                -ErrorAction Continue 2>&1 | Out-Null
            
            # Check for generated files
            Start-Sleep -Seconds 3
            $files = Get-ChildItem -LiteralPath $watchDir -Filter "*.png" -File -ErrorAction SilentlyContinue
            if ($files.Count -gt 0) {
                $success = $true
                $generatedFiles = $files
                Write-Host "  ✓ Texture generated: $($files[0].Name) ($([math]::Round($files[0].Length / 1KB, 2)) KB)" -ForegroundColor Green
            } else {
                $errorMsg = "No texture file generated"
            }
        }
        elseif ($asset.GenerateMethod -eq "BatchTextures") {
            Write-Host "  Generating batch textures for spritesheet..." -ForegroundColor Gray
            
            # Generate multiple textures
            $textureDescriptions = @(
                "Cracked stone texture, gray-brown, high detail",
                "Mossy stone texture, green-gray, organic",
                "Smooth stone texture, polished, gray",
                "Rough stone texture, jagged, dark gray",
                "Polished stone texture, shiny, light gray",
                "Volcanic stone texture, black-red, porous",
                "Icy stone texture, blue-white, crystalline",
                "Crystal stone texture, transparent-blue, geometric"
            )
            
            $descriptionsFile = Join-Path $watchDir "descriptions.txt"
            $textureDescriptions | Set-Content -Path $descriptionsFile -Encoding UTF8
            
            & $assetMakerScript `
                -Action BatchTextures `
                -InputData $descriptionsFile `
                -TextureMethod Procedural `
                -TextureSize $asset.Size `
                -OutputPath $watchDir `
                -Model $OllamaModel `
                -SpritesheetPath (Join-Path $watchDir "spritesheet.png") `
                -TileSize $asset.Size `
                -SpritesheetColumns 4 `
                -ErrorAction Continue 2>&1 | Out-Null
            
            Start-Sleep -Seconds 5
            $files = Get-ChildItem -LiteralPath $watchDir -Filter "*.png" -File -ErrorAction SilentlyContinue
            if ($files.Count -gt 0) {
                $success = $true
                $generatedFiles = $files
                Write-Host "  ✓ Generated $($files.Count) texture(s)" -ForegroundColor Green
                
                # Check for spritesheet
                $spritesheet = $files | Where-Object { $_.Name -eq "spritesheet.png" }
                if ($spritesheet) {
                    Write-Host "  ✓ Spritesheet created: $($spritesheet.Name) ($([math]::Round($spritesheet.Length / 1KB, 2)) KB)" -ForegroundColor Green
                }
            } else {
                $errorMsg = "No texture files generated"
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
                foreach ($file in $generatedFiles) {
                    $exportPath = Join-Path $exportDir $file.Name
                    Copy-Item -Path $file.FullName -Destination $exportPath -Force -ErrorAction SilentlyContinue
                }
                
                # Create game-specific metadata
                if ($target -eq "Qud") {
                    $qudMetadata = @{
                        name = $asset.Name
                        tileSize = $asset.Size
                        animated = $false
                        description = $asset.Description
                    }
                    $qudMetadata | ConvertTo-Json -Depth 10 | Set-Content -Path (Join-Path $exportDir "metadata.json") -Encoding UTF8
                }
                elseif ($target -eq "Terraria") {
                    $terrariaMetadata = @{
                        name = $asset.Name
                        tileSize = $asset.Size
                        items = 1
                        framesPerItem = 1
                        animationSpeed = 5
                    }
                    $terrariaMetadata | ConvertTo-Json -Depth 10 | Set-Content -Path (Join-Path $exportDir "${asset.Name}_terraria.json") -Encoding UTF8
                }
                elseif ($target -eq "Starbound") {
                    # Create .frames file for Starbound
                    $framesContent = @"
{
  "frames": [
    {
      "x": 0,
      "y": 0,
      "width": $($asset.Size),
      "height": $($asset.Size)
    }
  ]
}
"@
                    $framesPath = Join-Path $exportDir "$($asset.Name).frames"
                    $framesContent | Set-Content -Path $framesPath -Encoding UTF8
                }
                elseif ($target -eq "Elin") {
                    $elinMetadata = @{
                        name = $asset.Name
                        type = "icon"
                        size = $asset.Size
                        description = $asset.Description
                    }
                    $elinMetadata | ConvertTo-Json -Depth 10 | Set-Content -Path (Join-Path $exportDir "metadata.json") -Encoding UTF8
                }
                
                Write-Host "    ✓ Exported to $target" -ForegroundColor Green
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
        
        foreach ($file in $generatedFiles) {
            $metadata.GeneratedFiles += @{
                Name = $file.Name
                Size = $file.Length
                SizeKB = [math]::Round($file.Length / 1KB, 2)
                Path = $file.FullName
            }
        }
        
        $exportDirs = Get-ChildItem -LiteralPath $assetOutputDir -Directory -Filter "*Export" -ErrorAction SilentlyContinue
        foreach ($exportDir in $exportDirs) {
            $exportFiles = Get-ChildItem -LiteralPath $exportDir.FullName -File -ErrorAction SilentlyContinue
            foreach ($exportFile in $exportFiles) {
                $metadata.ExportFiles += @{
                    Name = $exportFile.Name
                    Size = $exportFile.Length
                    SizeKB = [math]::Round($exportFile.Length / 1KB, 2)
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

# Generate comprehensive quality check report
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Generating Quality Check Report" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

$successCount = ($results | Where-Object { $_.Success -eq $true }).Count
$totalCount = $results.Count

$qualityReport = @{
    TestRun = @{
        Date = (Get-Date -Format "yyyy-MM-dd HH:mm:ss")
        OutputDirectory = $outputPath
        TotalAssets = $totalCount
        SuccessfulAssets = $successCount
        FailedAssets = ($totalCount - $successCount)
        SuccessRate = [math]::Round(($successCount / $totalCount) * 100, 2)
    }
    Assets = $results
    QualityCheckCriteria = @{
        FileVerification = @(
            "All generated files exist and are non-zero size",
            "File formats match expected types (PNG for images)",
            "Export directories contain expected game-specific files",
            "File sizes are reasonable for asset type"
        )
        VisualQuality = @(
            "Color palettes match descriptions",
            "Sizes match specifications",
            "Style consistency (painterly, pixel, etc.)",
            "Visual clarity and detail appropriate for size"
        )
        GameFormatCompliance = @{
            Qud = @(
                "PNG tiles (24x24, 32x32, or 48x48)",
                "Optional XML/JSON metadata",
                "Proper naming conventions"
            )
            Elin = @(
                "Spell assets (icons 32x32)",
                "Metadata files present",
                "Proper format for game"
            )
            Terraria = @(
                "Spritesheets with JSON metadata",
                "Proper tile dimensions",
                "Animation metadata if applicable"
            )
            Starbound = @(
                "Spritesheets with .frames files",
                "Proper frame definitions",
                "Compatible dimensions"
            )
        }
        MetadataAccuracy = @(
            "metadata.json files contain correct information",
            "Timestamps are valid",
            "File paths are correct",
            "Export targets match generated files"
        )
    }
    ReviewInstructions = @"
# Quality Check Report for AI Review

## Test Summary
- **Total Assets**: $totalCount
- **Successful**: $successCount
- **Failed**: $($totalCount - $successCount)
- **Success Rate**: $([math]::Round(($successCount / $totalCount) * 100, 2))%

## Review Each Asset

$(($results | ForEach-Object {
    $status = if ($_.Success) { "✓ PASS" } else { "✗ FAIL" }
    $statusColor = if ($_.Success) { "green" } else { "red" }
    @"
### $($_.AssetName) - $status

- **Type**: $($_.AssetType)
- **Description**: $($_.Description)
- **Size**: $($_.Size)px
- **Export Targets**: $($_.ExportTargets -join ', ')
- **Generated Files**: $($_.GeneratedFiles.Count)
- **Exported Files**: $($_.ExportFiles.Count)
- **Generated At**: $($_.GeneratedAt)

**Files Generated:**
$($_.GeneratedFiles | ForEach-Object { "- $($_.Name) ($($_.SizeKB) KB)" } | Out-String)

**Files Exported:**
$($_.ExportFiles | ForEach-Object { "- $($_.Name) → $($_.Target) ($($_.SizeKB) KB)" } | Out-String)

$(if ($_.ErrorMessage) { "**Error**: $($_.ErrorMessage)" } else { "**Status**: Success" })

**Quality Check Points:**
1. [ ] File exists and is non-zero size
2. [ ] Format matches expected type
3. [ ] Size matches specification ($($_.Size)px)
4. [ ] Export files present for all targets
5. [ ] Metadata files created correctly
6. [ ] Visual quality appropriate (if previewable)

---
"@
}) -join "`n")
"@
}

$reportPath = Join-Path $outputPath "QUALITY_CHECK_REPORT.md"
$qualityReport.ReviewInstructions | Set-Content -Path $reportPath -Encoding UTF8

$jsonReportPath = Join-Path $outputPath "quality_check_report.json"
$qualityReport | ConvertTo-Json -Depth 10 | Set-Content -Path $jsonReportPath -Encoding UTF8

Write-Host "Quality check report saved to: $reportPath" -ForegroundColor Green
Write-Host "JSON report saved to: $jsonReportPath" -ForegroundColor Green
Write-Host ""

Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Test Complete" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "Review the generated assets in: $outputPath" -ForegroundColor Yellow
Write-Host "Quality check report: $reportPath" -ForegroundColor Yellow
Write-Host ""


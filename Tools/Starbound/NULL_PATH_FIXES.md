# Null Path Error Fixes

## Summary
Many generator scripts have null path errors when `$ModPath` or `$OutputDir` are null/empty. This document tracks fixes applied.

## Pattern to Fix
1. **Validate ModPath at script start:**
   ```powershell
   # Validate ModPath is not empty
   if ([string]::IsNullOrWhiteSpace($ModPath)) {
       Write-Host "Error: ModPath cannot be empty" -ForegroundColor Red
       exit 1
   }
   ```

2. **Validate paths before Join-Path:**
   ```powershell
   if ([string]::IsNullOrWhiteSpace($ModPath)) {
       Write-Host "  [FAIL] Cannot create path: ModPath is null or empty" -ForegroundColor Red
       continue  # or exit 1
   }
   $outputDir = Join-Path $ModPath "assets"
   ```

3. **Validate paths before New-Item:**
   ```powershell
   if ([string]::IsNullOrWhiteSpace($outputDir)) {
       Write-Host "  [FAIL] Cannot create directory: path is null" -ForegroundColor Red
       continue
   }
   if (-not (Test-Path $outputDir)) {
       try {
           New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
       } catch {
           Write-Host "  [FAIL] Cannot create directory '$outputDir': $_" -ForegroundColor Red
           continue
       }
   }
   ```

## Files Fixed
- ✅ `GenerateAnomalyAssets.ps1` - Added ModPath validation and path validation before directory creation
- ✅ `GenerateStarSystemAssets.ps1` - Added ModPath validation and path validation for all output directories
- ✅ `GenerateBladeCycloneFormAssets.ps1` - Added ModPath validation and OutputDir validation
- ✅ `StarboundParticleGenerator.ps1` - Fixed Write-Log function definition order
- ✅ `StarboundAssetGenerator.ps1` - Already has validation for AssetName and OutputDir

## Files Still Needing Fixes
All other `Generate*.ps1` scripts that use `$ModPath` or `$OutputDir` need similar validation.

## Helper Module
Created `PathValidationHelper.psm1` with helper functions:
- `Test-ValidPath` - Validates path variables
- `Join-PathSafe` - Safely joins paths with validation
- `New-DirectorySafe` - Safely creates directories with validation

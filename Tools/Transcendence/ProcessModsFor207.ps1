<#
.SYNOPSIS
  Process all mods using existing Transcendence Mod Tools
  
.DESCRIPTION
  Uses the existing Transcendence Mod Tools to:
  - Scan mods for errors and warnings
  - Fix auto-fixable issues (BOM, invalid symbols, etc.)
  - Format XML files to 2.0.7 style
  - This helps mods be compatible with 2.0.7 by fixing errors and formatting
  
  Note: This script uses the existing tools (FixMod.ps1, Format-XmlFile) which
  fix errors and format files. It does NOT update apiVersion attributes - that
  must be done manually.
  
.PARAMETER ExtensionsPath
  Path to Extensions folder (default: parent directory)
  
.PARAMETER ModFilter
  Optional: Only process mods matching this pattern
  
.PARAMETER DryRun
  Show what would be done without making changes
  
.EXAMPLE
  .\ProcessModsFor207.ps1
  Process all mods
  
.EXAMPLE
  .\ProcessModsFor207.ps1 -ModFilter "1237_*"
  Process specific mod
#>

[CmdletBinding()]
param(
    [string]$ExtensionsPath = "",
    [string]$ModFilter = "",
    [switch]$DryRun
)

$ErrorActionPreference = 'Continue'
$script:ToolsDir = $PSScriptRoot

# Determine Extensions path (sibling of Tools directory)
if ([string]::IsNullOrWhiteSpace($ExtensionsPath)) {
    $ExtensionsPath = Join-Path (Split-Path $script:ToolsDir -Parent) "Extensions"
}

Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Process Mods for 2.0.7 Compatibility" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "Using existing Transcendence Mod Tools to:" -ForegroundColor Yellow
Write-Host "  - Scan for errors and warnings" -ForegroundColor Gray
Write-Host "  - Fix auto-fixable issues" -ForegroundColor Gray
Write-Host "  - Format XML files" -ForegroundColor Gray
Write-Host ""
Write-Host "Extensions Path: $ExtensionsPath" -ForegroundColor Yellow
if ($DryRun) {
    Write-Host "MODE: DRY RUN (no changes will be made)" -ForegroundColor Yellow
}
Write-Host ""

# Load main tool
$mainTool = Join-Path $script:ToolsDir "TranscendenceModTools.ps1"
if (-not (Test-Path $mainTool)) {
    Write-Host "ERROR: TranscendenceModTools.ps1 not found" -ForegroundColor Red
    exit 1
}

# Get all mod directories
$modDirs = @(Get-ChildItem -LiteralPath $ExtensionsPath -Directory -ErrorAction SilentlyContinue | 
    Where-Object { 
        $name = $_.Name
        if ($name -eq 'Tools') { return $false }
        if (-not [string]::IsNullOrWhiteSpace($ModFilter)) {
            return $name -like $ModFilter
        }
        return $true
    })

Write-Host "Found $($modDirs.Count) mod(s) to process" -ForegroundColor Yellow
Write-Host ""

if ($modDirs.Count -eq 0) {
    Write-Host "No mods found to process." -ForegroundColor Yellow
    exit 0
}

$stats = @{
    ModsProcessed = 0
    ModsFixed = 0
    ModsSkipped = 0
    TotalIssues = 0
    FixedIssues = 0
    Errors = 0
}

# Process each mod
foreach ($modDir in $modDirs) {
    $modName = $modDir.Name
    Write-Host "Processing: $modName" -ForegroundColor Cyan
    
    $modPath = $modDir.FullName
    
    # Step 1: Scan for issues
    Write-Host "  [1/3] Scanning for issues..." -ForegroundColor Gray
    
    if ($DryRun) {
        Write-Host "    [DRY RUN] Would scan mod" -ForegroundColor DarkGray
    }
    else {
        try {
            # Use the main tool's auto-scan mode
            $scanResult = pwsh -NoProfile -ExecutionPolicy Bypass -File $mainTool -AutoScan -Path $modPath 2>&1
            $scanExitCode = $LASTEXITCODE
            $scanText = $scanResult | Out-String
            
            # Note: AutoScan exits with code 1 when it finds errors; that's not a crash.
            # Treat it as a failure only if we didn't get a normal scan summary.
            $scanLooksValid = ($scanText -match 'SCAN RESULTS')
            if (-not $scanLooksValid -and $scanExitCode -ne 0) {
                Write-Host "    Scan failed (exit $scanExitCode). Showing last output lines:" -ForegroundColor Red
                ($scanText -split "`r?`n" | Select-Object -Last 12) | ForEach-Object {
                    if ($_ -ne '') { Write-Host "      $_" -ForegroundColor DarkGray }
                }
                $stats.Errors++
                continue
            }
            
            # Prefer the tool's summary total
            $modIssues = 0
            if ($scanText -match 'Total Issues:\s*(\d+)') {
                $modIssues = [int]$matches[1]
            }
            else {
                # Fallback: sum per-file "Found N issue(s)" lines
                $issueMatches = [regex]::Matches($scanText, 'Found (\d+) issue\(s\)')
                foreach ($m in $issueMatches) {
                    $modIssues += [int]$m.Groups[1].Value
                }
            }
            
            if ($modIssues -gt 0) {
                Write-Host "    Found $modIssues issue(s)" -ForegroundColor Yellow
                $stats.TotalIssues += $modIssues
            }
            else {
                Write-Host "    No issues found" -ForegroundColor Green
            }
        }
        catch {
            Write-Host "    Error scanning: $_" -ForegroundColor Red
            $stats.Errors++
        }
    }
    
    # Step 2: Fix issues
    Write-Host "  [2/3] Fixing auto-fixable issues..." -ForegroundColor Gray
    
    if ($DryRun) {
        Write-Host "    [DRY RUN] Would fix issues" -ForegroundColor DarkGray
    }
    else {
        try {
            # Use FixMod.ps1 if available
            $fixScript = Join-Path $script:ToolsDir "FixMod.ps1"
            if (Test-Path $fixScript) {
                $fixResult = pwsh -NoProfile -ExecutionPolicy Bypass -File $fixScript -ModPath $modPath 2>&1
                
                # Check if fixes were applied
                if ($fixResult -match 'Files fixed:\s+(\d+)') {
                    $fixed = [int]$matches[1]
                    if ($fixed -gt 0) {
                        Write-Host "    Fixed $fixed file(s)" -ForegroundColor Green
                        $stats.FixedIssues += $fixed
                        $stats.ModsFixed++
                    }
                    else {
                        Write-Host "    No fixes needed" -ForegroundColor Gray
                    }
                }
            }
            else {
                Write-Host "    FixMod.ps1 not available" -ForegroundColor Yellow
            }
        }
        catch {
            Write-Host "    Error fixing: $_" -ForegroundColor Red
            $stats.Errors++
        }
    }
    
    # Step 3: Format files
    Write-Host "  [3/3] Formatting XML files..." -ForegroundColor Gray
    
    if ($DryRun) {
        Write-Host "    [DRY RUN] Would format files" -ForegroundColor DarkGray
    }
    else {
        try {
            # Load formatting module
            $formatModule = Join-Path $script:ToolsDir "TranscendenceModTools_Formatting.ps1"
            if (Test-Path $formatModule) {
                . $formatModule
                
                $xmlFiles = Get-ChildItem -LiteralPath $modPath -Filter '*.xml' -Recurse -ErrorAction SilentlyContinue
                $formattedCount = 0
                
                foreach ($file in $xmlFiles) {
                    try {
                        if (Get-Command Format-XmlFile -ErrorAction SilentlyContinue) {
                            $result = Format-XmlFile -FilePath $file.FullName -IndentChar "`t" -AlignAttributes
                            if ($result) {
                                $formattedCount++
                            }
                        }
                    }
                    catch {
                        # Skip files that can't be formatted
                    }
                }
                
                if ($formattedCount -gt 0) {
                    Write-Host "    Formatted $formattedCount file(s)" -ForegroundColor Green
                }
                else {
                    Write-Host "    No formatting needed" -ForegroundColor Gray
                }
            }
            else {
                Write-Host "    Formatting module not available" -ForegroundColor Yellow
            }
        }
        catch {
            Write-Host "    Error formatting: $_" -ForegroundColor Red
            $stats.Errors++
        }
    }
    
    $stats.ModsProcessed++
    Write-Host ""
}

# Summary
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  SUMMARY" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "Mods Processed: $($stats.ModsProcessed)" -ForegroundColor White
Write-Host "Mods Fixed:     $($stats.ModsFixed)" -ForegroundColor Green
Write-Host "Total Issues:   $($stats.TotalIssues)" -ForegroundColor White
Write-Host "Issues Fixed:   $($stats.FixedIssues)" -ForegroundColor Green
Write-Host "Errors:         $($stats.Errors)" -ForegroundColor $(if ($stats.Errors -gt 0) { 'Red' } else { 'Green' })
Write-Host ""

if ($DryRun) {
    Write-Host "This was a DRY RUN - no changes were made." -ForegroundColor Yellow
    Write-Host "Run without -DryRun to apply changes." -ForegroundColor Yellow
}

Write-Host "Done!" -ForegroundColor Green
Write-Host ""
Write-Host "Note: Use TranscendenceModTools.ps1 GUI for detailed scanning and fixing." -ForegroundColor Gray


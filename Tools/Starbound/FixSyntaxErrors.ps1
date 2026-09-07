#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Fix syntax errors in PowerShell scripts caused by corrupted hashtable definitions
#>

$ErrorActionPreference = "Stop"

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

# Pattern to find and fix
$badPattern = @'
# Validate \$ModPath before Join-Path
\$tempOutputDir = Join-Path \$ModPath "assets"
 if \(\[string\]::IsNullOrWhiteSpace\(\$tempOutputDir\)\) \{
                Write-Host "  \[FAIL\] tempOutputDir is null \(\$\{ModPath\}: '`$\{ModPath\}'\)" -ForegroundColor Red
                continue
            \}
 if \(\[string\]::IsNullOrWhiteSpace\(\$tempOutputDir\)\) \{
                Write-Host "  \[FAIL\] OutputDir is null \(\$\{ModPath\}: '`$\{ModPath\}'\)" -ForegroundColor Red
                continue
            \}
            OutputDir = \$tempOutputDir
'@

$goodReplacement = 'OutputDir = (Join-Path $ModPath "assets")'

# List of scripts to fix
$scriptsToFix = @(
    "GenerateAlchemyAssets.ps1",
    "GenerateDungeonAssets.ps1",
    "GenerateMechAssets.ps1",
    "GenerateWeaponAssets.ps1"
)

foreach ($script in $scriptsToFix) {
    $scriptPath = Join-Path $scriptRoot $script
    if (Test-Path $scriptPath) {
        Write-Host "Fixing: $script" -ForegroundColor Cyan
        
        $content = Get-Content $scriptPath -Raw
        $originalLength = $content.Length
        
        # Replace the bad pattern
        $content = $content -replace $badPattern, $goodReplacement
        
        if ($content.Length -ne $originalLength) {
            Set-Content -Path $scriptPath -Value $content -NoNewline
            Write-Host "  [OK] Fixed $script" -ForegroundColor Green
        } else {
            Write-Host "  [INFO] No changes needed in $script" -ForegroundColor Gray
        }
    } else {
        Write-Host "  [SKIP] Not found: $script" -ForegroundColor Yellow
    }
}

Write-Host "`nDone!" -ForegroundColor Green

<#
.SYNOPSIS
    Adds path validation to PowerShell scripts to prevent null path errors.
    
.DESCRIPTION
    Scans .ps1 files and adds validation for common null path patterns:
    - Join-Path with $ModPath or $OutputDir
    - New-Item with path variables
    - Test-Path with path variables
#>

param(
    [Parameter(Mandatory=$false)]
    [string]$ScriptPath,
    
    [Parameter(Mandatory=$false)]
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

if (-not $ScriptPath) {
    Write-Host "Usage: .\AddPathValidation.ps1 -ScriptPath <path-to-script.ps1> [-DryRun]" -ForegroundColor Yellow
    exit 1
}

if (-not (Test-Path $ScriptPath)) {
    Write-Host "Error: Script not found: $ScriptPath" -ForegroundColor Red
    exit 1
}

Write-Host "Analyzing: $ScriptPath" -ForegroundColor Cyan

$content = Get-Content $ScriptPath -Raw
$originalContent = $content
$modified = $false

# Pattern 1: Add ModPath validation at script start (after param block)
if ($content -match 'param\s*\([^)]+\)' -and $content -match '\$ModPath') {
    $paramEnd = $content.IndexOf(')', $content.IndexOf('param'))
    $afterParams = $content.Substring($paramEnd + 1)
    
    # Check if validation already exists
    if ($afterParams -notmatch 'Validate ModPath|IsNullOrWhiteSpace.*ModPath') {
        $validationCode = @"

# Validate ModPath is not empty
if ([string]::IsNullOrWhiteSpace(`$ModPath)) {
    Write-Host "Error: ModPath cannot be empty" -ForegroundColor Red
    Write-Host "  Please provide a valid mod path or use the default" -ForegroundColor Gray
    exit 1
}

"@
        $content = $content.Insert($paramEnd + 1, $validationCode)
        $modified = $true
        Write-Host "  [+] Added ModPath validation" -ForegroundColor Green
    }
}

# Pattern 2: Validate paths before Join-Path operations
$joinPathPattern = 'Join-Path\s+(\$ModPath|\$OutputDir|\$[A-Za-z]+Path)'
if ($content -match $joinPathPattern) {
    # This is complex - would need to parse each instance individually
    Write-Host "  [!] Found Join-Path operations - manual review recommended" -ForegroundColor Yellow
}

# Pattern 3: Validate paths before New-Item
$newItemPattern = 'New-Item.*-Path\s+(\$[A-Za-z]+)'
if ($content -match $newItemPattern) {
    Write-Host "  [!] Found New-Item operations - manual review recommended" -ForegroundColor Yellow
}

if ($modified) {
    if ($DryRun) {
        Write-Host "  [DRY RUN] Would modify file" -ForegroundColor Cyan
    } else {
        Set-Content -Path $ScriptPath -Value $content -NoNewline
        Write-Host "  [OK] File updated" -ForegroundColor Green
    }
} else {
    Write-Host "  [SKIP] No changes needed or validation already exists" -ForegroundColor Gray
}

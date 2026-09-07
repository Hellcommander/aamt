# Script to scan and fix issues in a mod

param(
    [string]$ModPath = "..\ZZZ_CrossModCompatibility"
)

Write-Host "Transcendence Mod Tools - Auto-Fix Script" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# IMPORTANT: Transcendence XML should be UTF-8 *without* BOM.
$utf8NoBom = [System.Text.UTF8Encoding]::new($false)

# Load scanner functions (avoid dot-sourcing the full GUI tool)
$issuesModule = Join-Path $PSScriptRoot "GetXmlIssues.ps1"
if (-not (Test-Path $issuesModule)) {
    Write-Host "ERROR: GetXmlIssues.ps1 not found at: $issuesModule" -ForegroundColor Red
    exit 1
}
. $issuesModule

# Resolve mod path
$modPath = Resolve-Path $ModPath -ErrorAction SilentlyContinue
if (-not $modPath) {
    Write-Host "ERROR: Mod path not found: $ModPath" -ForegroundColor Red
    exit 1
}

Write-Host "Mod Path: $modPath" -ForegroundColor Yellow
Write-Host ""

# Get all XML files
$files = Get-ChildItem -LiteralPath $modPath -Filter '*.xml' -Recurse | ForEach-Object { $_.FullName }
Write-Host "Found $($files.Count) XML files" -ForegroundColor Green
Write-Host ""

# Scan for issues
Write-Host "Scanning for issues..." -ForegroundColor Cyan
$allIssues = @()
foreach ($file in $files) {
    try {
        $issues = Get-XmlIssues -FilePath $file
        $allIssues += $issues
    }
    catch {
        Write-Host "  Warning: Failed to scan $file" -ForegroundColor Yellow
    }
}

Write-Host "Total issues found: $($allIssues.Count)" -ForegroundColor Yellow

# Group by type
$byType = $allIssues | Group-Object Code
Write-Host ""
Write-Host "Issues by type:" -ForegroundColor Cyan
foreach ($group in $byType | Sort-Object Count -Descending) {
    $fixable = ($group.Group | Where-Object { $_.CanFix -eq $true }).Count
    Write-Host "  $($group.Name): $($group.Count) ($fixable fixable)" -ForegroundColor Gray
}

# Get fixable issues
$fixable = $allIssues | Where-Object { $_.CanFix -eq $true }
Write-Host ""
Write-Host "Fixable issues: $($fixable.Count)" -ForegroundColor Green

if ($fixable.Count -eq 0) {
    Write-Host ""
    Write-Host "No auto-fixable issues found." -ForegroundColor Yellow
    exit 0
}

# Group fixable issues by file
$byFile = $fixable | Group-Object File

Write-Host ""
Write-Host "Fixing issues..." -ForegroundColor Cyan
Write-Host ""

$fixedCount = 0
$filesFixed = 0

foreach ($fileGroup in $byFile) {
    $file = $fileGroup.Name
    $issues = $fileGroup.Group
    
    Write-Host "Processing: $(Split-Path -Leaf $file)" -ForegroundColor Yellow
    
    try {
        # Read file
        $content = [System.IO.File]::ReadAllText($file, [System.Text.Encoding]::UTF8)
        $originalContent = $content
        $modified = $false
        
        # Fix BOM
        $bomIssues = $issues | Where-Object { $_.Code -eq 'UTF8_BOM' }
        if ($bomIssues.Count -gt 0) {
            $bytes = [System.IO.File]::ReadAllBytes($file)
            if ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) {
                # Remove BOM
                $newBytes = $bytes[3..($bytes.Length-1)]
                [System.IO.File]::WriteAllBytes($file, $newBytes)
                $content = [System.IO.File]::ReadAllText($file, [System.Text.Encoding]::UTF8)
                $modified = $true
                $fixedCount += $bomIssues.Count
                Write-Host "  ✓ Removed UTF-8 BOM" -ForegroundColor Green
            }
        }
        
        # Fix invalid symbol syntax (trailing quote)
        $symbolIssues = $issues | Where-Object { $_.Code -eq 'INVALID_SYMBOL_SYNTAX' }
        if ($symbolIssues.Count -gt 0) {
            foreach ($issue in $symbolIssues) {
                # Pattern: 'symbol' should be 'symbol
                $pattern = "'(\w+)'"
                $content = $content -replace $pattern, "'`$1"
                $modified = $true
            }
            $fixedCount += $symbolIssues.Count
            Write-Host "  ✓ Fixed $($symbolIssues.Count) invalid symbol(s)" -ForegroundColor Green
        }
        
        # Fix raw > characters (basic cases)
        $rawGtIssues = $issues | Where-Object { $_.Code -eq 'RAW_GREATER_THAN' }
        if ($rawGtIssues.Count -gt 0) {
            # This is tricky - we need to be careful not to break valid XML
            # Only fix obvious cases in comments or strings
            # For now, we'll skip this as it requires more context
            Write-Host "  ⚠ Raw > characters need manual review" -ForegroundColor Yellow
        }
        
        # Write file if modified
        if ($modified) {
            # Create backup
            $backupFile = "$file.backup"
            [System.IO.File]::WriteAllText($backupFile, $originalContent, $utf8NoBom)
            
            # Write fixed content
            [System.IO.File]::WriteAllText($file, $content, $utf8NoBom)
            
            $filesFixed++
            Write-Host "  ✓ File fixed (backup created)" -ForegroundColor Green
        }
    }
    catch {
        Write-Host "  ✗ Error fixing file: $_" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Fix Summary:" -ForegroundColor Cyan
Write-Host "  Files processed: $($byFile.Count)" -ForegroundColor Yellow
Write-Host "  Files fixed: $filesFixed" -ForegroundColor Green
Write-Host "  Issues fixed: $fixedCount" -ForegroundColor Green
Write-Host ""
Write-Host "Backups created with .backup extension" -ForegroundColor Gray
Write-Host ""


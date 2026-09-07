<#
.SYNOPSIS
  Fix UTF-8 BOM issues in XML files
  
.DESCRIPTION
  Scans for and removes UTF-8 BOM from XML files.
  The "<?XML prologue expected" error is usually caused by BOM.
  
.PARAMETER Path
  Path to file or folder to fix
  
.EXAMPLE
  .\FixBOM.ps1 -Path "..\Corporatecommandforeternityportaddon.xml"
  .\FixBOM.ps1 -Path "..\1237_UpgradedWingmen"
#>

param(
    [Parameter(Mandatory=$true)]
    [string]$Path
)

$ErrorActionPreference = 'Continue'

Write-Host "Fixing UTF-8 BOM issues..." -ForegroundColor Cyan
Write-Host ""

$resolvedPath = Resolve-Path $Path -ErrorAction SilentlyContinue
if (-not $resolvedPath) {
    Write-Host "ERROR: Path not found: $Path" -ForegroundColor Red
    exit 1
}

$resolvedPathStr = $resolvedPath.Path

$files = @()
if (Test-Path $resolvedPathStr -PathType Leaf) {
    if ($resolvedPathStr.EndsWith('.xml')) {
        $files = @($resolvedPathStr)
    }
}
else {
    $files = @(Get-ChildItem -LiteralPath $resolvedPathStr -Filter '*.xml' -Recurse -ErrorAction SilentlyContinue | ForEach-Object { $_.FullName })
}

if ($files.Count -eq 0) {
    Write-Host "No XML files found" -ForegroundColor Yellow
    exit 0
}

Write-Host "Found $($files.Count) XML file(s)" -ForegroundColor Yellow
Write-Host ""

$fixedCount = 0
$backupCount = 0

foreach ($file in $files) {
    try {
        $bytes = [System.IO.File]::ReadAllBytes($file)
        
        # Check for BOM
        if ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) {
            $fileName = Split-Path -Leaf $file
            Write-Host "Fixing: $fileName" -ForegroundColor Yellow
            
            # Create backup
            $backupFile = "$file.backup"
            if (-not (Test-Path $backupFile)) {
                Copy-Item $file $backupFile -Force
                $backupCount++
            }
            
            # Remove BOM
            $newBytes = $bytes[3..($bytes.Length-1)]
            [System.IO.File]::WriteAllBytes($file, $newBytes)
            
            $fixedCount++
            Write-Host "  ✓ BOM removed" -ForegroundColor Green
        }
    }
    catch {
        Write-Host "  ✗ Error: $_" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  SUMMARY" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "Files Scanned: $($files.Count)" -ForegroundColor White
Write-Host "Files Fixed:   $fixedCount" -ForegroundColor Green
Write-Host "Backups Created: $backupCount" -ForegroundColor Gray
Write-Host ""

if ($fixedCount -gt 0) {
    Write-Host "BOM issues fixed! Files backed up with .backup extension" -ForegroundColor Green
}
else {
    Write-Host "No BOM issues found" -ForegroundColor Green
}

Write-Host "Done!" -ForegroundColor Green


# Batch fix for missing unidHumanSpaceLibrary entity
param([string]$ExtensionsPath = "..")

$extensionsDir = if ([System.IO.Path]::IsPathRooted($ExtensionsPath)) { 
    $ExtensionsPath 
} else { 
    (Resolve-Path (Join-Path $PSScriptRoot $ExtensionsPath)).Path 
}

Write-Host "Fixing missing unidHumanSpaceLibrary in: $extensionsDir" -ForegroundColor Cyan
Write-Host ""

$utf8NoBom = [System.Text.UTF8Encoding]::new($false)

$files = Get-ChildItem -LiteralPath $extensionsDir -Filter '*.xml' -Recurse -File

$fixed = 0
$skipped = 0

foreach ($file in $files) {
    try {
        $content = [System.IO.File]::ReadAllText($file.FullName, [System.Text.Encoding]::UTF8)
        
        # Check if file uses unidHumanSpaceLibrary but doesn't declare it
        if ($content -match '&unidHumanSpaceLibrary;' -and $content -notmatch '<!ENTITY unidHumanSpaceLibrary') {
            # Check if there's a DOCTYPE
            if ($content -match '<!DOCTYPE\s+(\w+)\s*\[') {
                $doctypeName = $matches[1]
                $doctypeEnd = $content.IndexOf(']>')
                
                if ($doctypeEnd -gt 0) {
                    # Insert entity before closing
                    $beforeClose = $content.Substring(0, $doctypeEnd)
                    $afterClose = $content.Substring($doctypeEnd)
                    
                    # Check if there are already entities - add newline appropriately
                    if ($beforeClose.TrimEnd() -match '<!ENTITY\s+\w+') {
                        $content = $beforeClose + "`n<!ENTITY unidHumanSpaceLibrary`t`"0x00100000`">" + $afterClose
                    } else {
                        $content = $beforeClose + "`n<!ENTITY unidHumanSpaceLibrary`t`"0x00100000`">`n" + $afterClose
                    }
                    
                    # Create backup
                    $backupFile = "$($file.FullName).backup"
                    Copy-Item -LiteralPath $file.FullName -Destination $backupFile -Force
                    
                    # Write fixed content
                    [System.IO.File]::WriteAllText($file.FullName, $content, $utf8NoBom)
                    
                    Write-Host "Fixed: $($file.Name)" -ForegroundColor Green
                    $fixed++
                } else {
                    Write-Host "Skipped (no DOCTYPE end): $($file.Name)" -ForegroundColor Yellow
                    $skipped++
                }
            } else {
                Write-Host "Skipped (no DOCTYPE): $($file.Name)" -ForegroundColor Yellow
                $skipped++
            }
        }
    }
    catch {
        Write-Host "Error processing $($file.Name): $_" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Summary:" -ForegroundColor Cyan
Write-Host "  Files fixed: $fixed" -ForegroundColor Green
Write-Host "  Files skipped: $skipped" -ForegroundColor Yellow
Write-Host "  Backups created with .backup extension" -ForegroundColor Gray


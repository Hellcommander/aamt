# Script to fix common XML issues in mods
param([string]$ModPath = ".")

. .\GetXmlIssues.ps1

$utf8NoBom = [System.Text.UTF8Encoding]::new($false)

$extensionsDir = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
if (-not ([System.IO.Path]::IsPathRooted($ModPath))) {
    if ($ModPath -eq ".") {
        $fullPath = $extensionsDir
    }
    elseif ($ModPath.StartsWith('..\')) {
        $modName = $ModPath.Substring(3)
        $fullPath = Join-Path $extensionsDir $modName
    }
    else {
        $fullPath = Join-Path $extensionsDir $ModPath
    }
    $fullPath = [System.IO.Path]::GetFullPath($fullPath)
}
else {
    $fullPath = $ModPath
}

if (-not (Test-Path $fullPath)) {
    Write-Host "ERROR: Path does not exist: $fullPath" -ForegroundColor Red
    exit 1
}

Write-Host "Fixing common issues in: $fullPath" -ForegroundColor Cyan
Write-Host ""

# Get all XML files
$files = @()
if (Test-Path $fullPath -PathType Leaf) {
    if ($fullPath.EndsWith('.xml')) { 
        $files = @($fullPath) 
    }
}
else {
    $files = @(Get-ChildItem -LiteralPath $fullPath -Filter '*.xml' -Recurse | ForEach-Object { $_.FullName })
}

if ($files.Count -eq 0) {
    Write-Host 'No XML files found' -ForegroundColor Red
    exit 1
}

Write-Host "Found $($files.Count) XML file(s)" -ForegroundColor Green
Write-Host ""

$fixedCount = 0
$filesFixed = 0

foreach ($file in $files) {
    $fileName = Split-Path -Leaf $file
    Write-Host "Checking: $fileName" -NoNewline
    
    try {
        $issues = Get-XmlIssues -FilePath $file
        $wellformed = $issues | Where-Object { $_.Code -eq 'XML_WELLFORMED_ERROR' }
        
        if ($wellformed.Count -eq 0) {
            Write-Host " - OK" -ForegroundColor Green
            continue
        }
        
        Write-Host " - Found $($wellformed.Count) issue(s)" -ForegroundColor Yellow
        
        # Read file
        $content = [System.IO.File]::ReadAllText($file, [System.Text.Encoding]::UTF8)
        $originalContent = $content
        $modified = $false
        
        # Check for missing unidHumanSpaceLibrary
        if ($content -match '&unidHumanSpaceLibrary;' -and $content -notmatch '<!ENTITY unidHumanSpaceLibrary') {
            # Check if there's a DOCTYPE
            if ($content -match '<!DOCTYPE\s+(\w+)\s*\[') {
                $doctypeName = $matches[1]
                # Find the closing ]> of DOCTYPE
                $doctypeEnd = $content.IndexOf(']>')
                if ($doctypeEnd -gt 0) {
                    # Insert entity before closing
                    $beforeClose = $content.Substring(0, $doctypeEnd)
                    $afterClose = $content.Substring($doctypeEnd)
                    $content = $beforeClose + "`n<!ENTITY unidHumanSpaceLibrary`t`"0x00100000`">`n" + $afterClose
                    $modified = $true
                    Write-Host "    + Added unidHumanSpaceLibrary entity" -ForegroundColor Green
                }
            }
        }
        
        # Check for missing unidCoreTypesLibrary
        if ($content -match '&unidCoreTypesLibrary;' -and $content -notmatch '<!ENTITY unidCoreTypesLibrary') {
            if ($content -match '<!DOCTYPE\s+(\w+)\s*\[') {
                $doctypeEnd = $content.IndexOf(']>')
                if ($doctypeEnd -gt 0) {
                    $beforeClose = $content.Substring(0, $doctypeEnd)
                    $afterClose = $content.Substring($doctypeEnd)
                    $content = $beforeClose + "`n<!ENTITY unidCoreTypesLibrary`t`"0x00010001`">`n" + $afterClose
                    $modified = $true
                    Write-Host "    + Added unidCoreTypesLibrary entity" -ForegroundColor Green
                }
            }
        }
        
        # Check for missing unidRPGLibrary
        if ($content -match '&unidRPGLibrary;' -and $content -notmatch '<!ENTITY unidRPGLibrary') {
            if ($content -match '<!DOCTYPE\s+(\w+)\s*\[') {
                $doctypeEnd = $content.IndexOf(']>')
                if ($doctypeEnd -gt 0) {
                    $beforeClose = $content.Substring(0, $doctypeEnd)
                    $afterClose = $content.Substring($doctypeEnd)
                    $content = $beforeClose + "`n<!ENTITY unidRPGLibrary`t`"0x00010000`">`n" + $afterClose
                    $modified = $true
                    Write-Host "    + Added unidRPGLibrary entity" -ForegroundColor Green
                }
            }
        }
        
        # Check for missing rsItems1
        if ($content -match '&rsItems1;' -and $content -notmatch '<!ENTITY rsItems1') {
            if ($content -match '<!DOCTYPE\s+(\w+)\s*\[') {
                $doctypeEnd = $content.IndexOf(']>')
                if ($doctypeEnd -gt 0) {
                    $beforeClose = $content.Substring(0, $doctypeEnd)
                    $afterClose = $content.Substring($doctypeEnd)
                    $content = $beforeClose + "`n<!ENTITY rsItems1`t`t`"0x0000F11D`">`n" + $afterClose
                    $modified = $true
                    Write-Host "    + Added rsItems1 entity" -ForegroundColor Green
                }
            }
        }

        # Check for missing rsStations1 / rsItemsEI1 (current Core Types UNIDs)
        if ($content -match '&rsStations1;' -and $content -notmatch '<!ENTITY rsStations1') {
            if ($content -match '<!DOCTYPE\s+(\w+)\s*\[') {
                $doctypeEnd = $content.IndexOf(']>')
                if ($doctypeEnd -gt 0) {
                    $beforeClose = $content.Substring(0, $doctypeEnd)
                    $afterClose = $content.Substring($doctypeEnd)
                    $content = $beforeClose + "`n<!ENTITY rsStations1`t`"0x0000F103`">`n" + $afterClose
                    $modified = $true
                    Write-Host "    + Added rsStations1 entity" -ForegroundColor Green
                }
            }
        }
        if ($content -match '&rsItemsEI1;' -and $content -notmatch '<!ENTITY rsItemsEI1') {
            if ($content -match '<!DOCTYPE\s+(\w+)\s*\[') {
                $doctypeEnd = $content.IndexOf(']>')
                if ($doctypeEnd -gt 0) {
                    $beforeClose = $content.Substring(0, $doctypeEnd)
                    $afterClose = $content.Substring($doctypeEnd)
                    $content = $beforeClose + "`n<!ENTITY rsItemsEI1`t`"0x0000F150`">`n" + $afterClose
                    $modified = $true
                    Write-Host "    + Added rsItemsEI1 entity" -ForegroundColor Green
                }
            }
        }
        
        # Check for DTD markup issues (semicolon comments)
        if ($content -match '<!DOCTYPE\s+(\w+)\s*\[') {
            $doctypeStart = $content.IndexOf('<!DOCTYPE')
            $doctypeEnd = $content.IndexOf(']>', $doctypeStart)
            if ($doctypeEnd -gt 0) {
                $doctypeSection = $content.Substring($doctypeStart, $doctypeEnd - $doctypeStart + 2)
                # Check for semicolon comments in DOCTYPE
                if ($doctypeSection -match '(?m)^\s*;\s+') {
                    # Replace semicolon comments with XML comments
                    $doctypeSection = $doctypeSection -replace '(?m)^(\s*);\s+(.+)$', '$1<!-- $2 -->'
                    $beforeDoctype = $content.Substring(0, $doctypeStart)
                    $afterDoctype = $content.Substring($doctypeEnd + 2)
                    $content = $beforeDoctype + $doctypeSection + $afterDoctype
                    $modified = $true
                    Write-Host "    + Fixed semicolon comments in DOCTYPE" -ForegroundColor Green
                }
            }
        }
        
        # Write file if modified
        if ($modified) {
            # Create backup
            $backupFile = "$file.backup"
            [System.IO.File]::WriteAllText($backupFile, $originalContent, $utf8NoBom)
            
            # Write fixed content
            [System.IO.File]::WriteAllText($file, $content, $utf8NoBom)
            
            $filesFixed++
            $fixedCount++
            Write-Host "    ✓ File fixed (backup created)" -ForegroundColor Green
        }
    }
    catch {
        Write-Host " - ERROR: $_" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Fix Summary:" -ForegroundColor Cyan
Write-Host "  Files processed: $($files.Count)" -ForegroundColor Yellow
Write-Host "  Files fixed: $filesFixed" -ForegroundColor Green
Write-Host "  Issues fixed: $fixedCount" -ForegroundColor Green
Write-Host ""
Write-Host "Backups created with .backup extension" -ForegroundColor Gray
Write-Host ""


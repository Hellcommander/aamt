<#
.SYNOPSIS
    Fixes syntax errors in GenerateAlchemicalGrenadeLauncherAssets.ps1
    
.DESCRIPTION
    Fixes the incorrectly placed validation code inside hashtable definitions.
#>

$ErrorActionPreference = "Stop"
$file = "D:\games\Steam\steamapps\common\Transcendence\Tools\Starbound\GenerateAlchemicalGrenadeLauncherAssets.ps1"

$content = Get-Content $file -Raw
$originalContent = $content

# Pattern: validation code incorrectly placed inside hashtable
# We need to move the validation before the hashtable and fix the structure

$lines = $content -split "`r?`n"
$newLines = @()
$i = 0

while ($i -lt $lines.Count) {
    $line = $lines[$i]
    
    # Check if this line starts a hashtable with validation code inside
    if ($line -match '^\s*\$params = @\{' -and $i + 1 -lt $lines.Count) {
        # Look ahead to see if validation code is inside
        $j = $i + 1
        $hashtableLines = @($line)
        $foundValidation = $false
        
        while ($j -lt $lines.Count -and $lines[$j] -notmatch '^\s*\}\s*$') {
            if ($lines[$j] -match '# Validate \$ModPath before Join-Path') {
                $foundValidation = $true
                break
            }
            $hashtableLines += $lines[$j]
            $j++
        }
        
        if ($foundValidation) {
            # Extract the hashtable content before validation
            $hashtableStart = $hashtableLines -join "`n"
            
            # Find where validation starts
            $validationStart = $j
            while ($j -lt $lines.Count -and $lines[$j] -notmatch '^\s*OutputDir = \$tempOutputDir') {
                $j++
            }
            
            # Extract validation code
            $validationLines = @()
            $k = $validationStart
            while ($k -lt $lines.Count -and $k -lt $j + 2) {
                if ($lines[$k] -match '# Validate|Join-Path|IsNullOrWhiteSpace|Write-Host.*FAIL|continue') {
                    $validationLines += $lines[$k]
                }
                $k++
            }
            
            # Find the hashtable end
            while ($j -lt $lines.Count -and $lines[$j] -notmatch '^\s*\}\s*$') {
                $j++
            }
            
            # Reconstruct: validation first, then hashtable
            $newLines += "# Validate `$ModPath before Join-Path"
            $newLines += "            `$tempOutputDir = Join-Path `$ModPath `"assets`""
            $newLines += "            if ([string]::IsNullOrWhiteSpace(`$tempOutputDir)) {"
            $newLines += "                Write-Host `"  [FAIL] tempOutputDir is null (`${ModPath}: '`${ModPath}')`" -ForegroundColor Red"
            $newLines += "                continue"
            $newLines += "            }"
            $newLines += ""
            $newLines += "            `$params = @{"
            
            # Add hashtable content (skip validation lines)
            foreach ($hl in $hashtableLines) {
                if ($hl -notmatch '# Validate|Join-Path|IsNullOrWhiteSpace|Write-Host.*FAIL|continue|OutputDir = \$tempOutputDir') {
                    if ($hl -match '^\s*(AssetType|AssetName|Prompt|OllamaModel)\s*=') {
                        $newLines += $hl
                    }
                }
            }
            
            # Add OutputDir
            $newLines += "                OutputDir = `$tempOutputDir"
            $newLines += "            }"
            
            $i = $j + 1
            continue
        }
    }
    
    $newLines += $line
    $i++
}

$newContent = $newLines -join "`n"

if ($newContent -ne $originalContent) {
    Set-Content -Path $file -Value $newContent -NoNewline
    Write-Host "Fixed syntax errors" -ForegroundColor Green
} else {
    Write-Host "No changes needed" -ForegroundColor Yellow
}

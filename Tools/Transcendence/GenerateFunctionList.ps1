<#
.SYNOPSIS
  Generate a human-readable function list from API rules (forum-style format)
  
.DESCRIPTION
  This script reads an API rules JSON file and generates a human-readable
  function list in a format similar to the forum function reference.
  
.EXAMPLE
  .\GenerateFunctionList.ps1 -ApiVersion 57
  .\GenerateFunctionList.ps1 -ApiVersion 59 -OutputPath "FunctionList_API59.txt"
#>

param(
    [int]$ApiVersion = 57,
    [string]$OutputPath = $null,
    [string]$RulesPath = $null
)

$script:ScriptRoot = $PSScriptRoot

# Determine rules file path
if (-not $RulesPath) {
    $RulesPath = Join-Path $script:ScriptRoot "api_rules_$ApiVersion.json"
    if (-not (Test-Path $RulesPath)) {
        $RulesPath = Join-Path $script:ScriptRoot "api_rules.json"
    }
}

if (-not (Test-Path $RulesPath)) {
    Write-Host "ERROR: API rules file not found: $RulesPath" -ForegroundColor Red
    Write-Host "Run GenerateApiRules.ps1 first to generate the rules file." -ForegroundColor Yellow
    exit 1
}

# Determine output path
if (-not $OutputPath) {
    $OutputPath = Join-Path $script:ScriptRoot "FunctionList_API$ApiVersion.txt"
}

Write-Host "Generating function list..." -ForegroundColor Cyan
Write-Host "  Reading: $RulesPath" -ForegroundColor Gray
Write-Host "  Output:  $OutputPath" -ForegroundColor Gray
Write-Host ""

# Load API rules
$apiRules = Get-Content $RulesPath -Raw | ConvertFrom-Json

if (-not $apiRules.Functions) {
    Write-Host "ERROR: No functions found in API rules file" -ForegroundColor Red
    exit 1
}

# Get all function names and sort them
$functionNames = @($apiRules.Functions.PSObject.Properties.Name) | Sort-Object

Write-Host "Found $($functionNames.Count) functions" -ForegroundColor Green
Write-Host ""

# Function categories for better organization
$categories = @{
    'Math' = @('+', '-', '*', '/', 'add', 'subtract', 'multiply', 'divide', 'abs', 'min', 'max', 'mod', 'random', 'round', 'floor', 'ceil', 'sqrt', 'pow', 'exp', 'log', 'sin', 'cos', 'tan', 'asin', 'acos', 'atan')
    'Comparison' = @('=', '!=', '===', '!===', '<', '<=', '>', '>=', 'eq', 'ls', 'gr', 'leq', 'geq')
    'Logic' = @('and', 'or', 'not', 'if', 'switch')
    'List' = @('list', 'append', 'filter', 'map', 'find', 'count', 'item', '@', 'set', 'shuffle', 'sort')
    'String' = @('cat', 'strFind', 'strSubString', 'strLength', 'strCapitalize', 'strToLower', 'strToUpper')
    'Object' = @('obj', 'objGet', 'objSet', 'objGetData', 'objSetData', 'objGetProperty', 'objSetProperty', 'objGetName', 'objGetPos', 'objGetDistance')
    'Item' = @('itm', 'itmGet', 'itmSet', 'itmGetType', 'itmGetProperty', 'itmSetProperty', 'itmGetData', 'itmSetData')
    'Type' = @('typ', 'typGet', 'typSet', 'typGetData', 'typSetData', 'typGetProperty', 'typSetProperty', 'typGetName', 'typFind')
    'Ship' = @('shp', 'shpGet', 'shpSet', 'shpGetOrder', 'shpOrder', 'shpGetSpeed', 'shpGetPos')
    'Station' = @('sta', 'staGet', 'staSet', 'staGetDockedShips', 'staGetName')
    'System' = @('sys', 'sysGet', 'sysSet', 'sysCreate', 'sysFindObject', 'sysGetNodes', 'sysGetStargates')
    'Universe' = @('unv', 'unvGet', 'unvSet', 'unvFindObject', 'unvGetElapsedGameTime')
    'UI' = @('ui', 'uiGet', 'uiSet', 'uiShow', 'uiPlayMusic', 'uiGetKeyName', 'uiIsKeyPressed')
    'Debug' = @('dbg', 'dbgLog', 'dbgOutput', 'dbgGet', 'dbgSet', 'dbgEvalTimed', 'dbgApplyTimed')
    'XML' = @('xml', 'xmlCreate', 'xmlGet', 'xmlSet', 'xmlGetAttrib', 'xmlSetAttrib', 'xmlGetSubElement')
    'Vector' = @('vec', 'vector', 'v+', 'v-', 'v*', 'vDot', 'vecCreate', 'vecSetElement')
    'Block' = @('block', 'enum', 'enumWhile', 'for', 'loop', 'while', 'break', 'return')
    'Error' = @('error', 'errBlock', 'try', 'catch')
    'Other' = @()
}

# Categorize functions
$categorized = @{}
foreach ($funcName in $functionNames) {
    $found = $false
    foreach ($category in $categories.Keys) {
        if ($category -ne 'Other') {
            foreach ($prefix in $categories[$category]) {
                if ($funcName -like "$prefix*" -or $funcName -eq $prefix) {
                    if (-not $categorized[$category]) {
                        $categorized[$category] = @()
                    }
                    $categorized[$category] += $funcName
                    $found = $true
                    break
                }
            }
            if ($found) { break }
        }
    }
    if (-not $found) {
        if (-not $categorized['Other']) {
            $categorized['Other'] = @()
        }
        $categorized['Other'] += $funcName
    }
}

# Generate the function list (forum-style format)
$output = [System.Text.StringBuilder]::new()
[void]$output.AppendLine("Function List - API $($apiRules.ApiVersion)")
[void]$output.AppendLine("")
[void]$output.AppendLine("This is an auto-generated function list extracted from the game source code.")
[void]$output.AppendLine("For detailed function signatures and documentation, see:")
[void]$output.AppendLine("https://forums.kronosaur.com/viewtopic.php?t=9218")
[void]$output.AppendLine("")
[void]$output.AppendLine("Generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')")
[void]$output.AppendLine("Total Functions: $($functionNames.Count)")
[void]$output.AppendLine("")
[void]$output.AppendLine("=" * 80)
[void]$output.AppendLine("")

# Output by category
$categoryOrder = @('Math', 'Comparison', 'Logic', 'List', 'String', 'Block', 'Error', 
                   'Object', 'Item', 'Type', 'Ship', 'Station', 'System', 'Universe',
                   'UI', 'XML', 'Vector', 'Debug', 'Other')

foreach ($category in $categoryOrder) {
    if ($categorized[$category] -and $categorized[$category].Count -gt 0) {
        [void]$output.AppendLine("## $category Functions")
        [void]$output.AppendLine("")
        
        foreach ($funcName in $categorized[$category] | Sort-Object) {
            $funcInfo = $apiRules.Functions.$funcName
            $count = if ($funcInfo.Count) { $funcInfo.Count } else { 0 }
            $files = if ($funcInfo.Files) { $funcInfo.Files.Count } else { 0 }
            
            # Format similar to forum: (functionName [param1] [param2 ...]) -> description
            # Since we don't have signature info in JSON, use placeholder format
            [void]$output.AppendLine("($funcName [...]) -> Function")
            if ($count -gt 0 -and $files -gt 0) {
                [void]$output.AppendLine("  Usage: $count call(s) across $files file(s)")
            }
            [void]$output.AppendLine("")
        }
        
        [void]$output.AppendLine("")
    }
}

# Also output complete alphabetical list (compact format)
[void]$output.AppendLine("=" * 80)
[void]$output.AppendLine("## Complete Alphabetical Function List")
[void]$output.AppendLine("")
[void]$output.AppendLine("All $($functionNames.Count) functions in alphabetical order:")
[void]$output.AppendLine("")

# Group by first letter for easier navigation
$byLetter = @{}
foreach ($funcName in $functionNames) {
    $firstLetter = $funcName.Substring(0, 1).ToUpper()
    if (-not $byLetter[$firstLetter]) {
        $byLetter[$firstLetter] = @()
    }
    $byLetter[$firstLetter] += $funcName
}

foreach ($letter in ($byLetter.Keys | Sort-Object)) {
    [void]$output.AppendLine("### $letter")
    [void]$output.AppendLine("")
    foreach ($funcName in ($byLetter[$letter] | Sort-Object)) {
        $funcInfo = $apiRules.Functions.$funcName
        $count = if ($funcInfo.Count) { $funcInfo.Count } else { 0 }
        
        [void]$output.AppendLine("($funcName [...]) -> Function")
        if ($count -gt 0) {
            [void]$output.AppendLine("  Usage: $count call(s)")
        }
        [void]$output.AppendLine("")
    }
    [void]$output.AppendLine("")
}

# Save to file
$output.ToString() | Out-File -FilePath $OutputPath -Encoding UTF8

Write-Host "Function list generated successfully!" -ForegroundColor Green
Write-Host "File: $OutputPath" -ForegroundColor Gray
Write-Host "Functions: $($functionNames.Count)" -ForegroundColor Gray


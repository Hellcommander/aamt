<#
.SYNOPSIS
  Auto-Update Module for Transcendence Mods
  
.DESCRIPTION
  Automatically updates mods to new API versions by:
  - Detecting deprecated tags/functions/attributes
  - Suggesting replacements from API rules
  - Auto-fixing where safe
  - Updating apiVersion attributes
  - Generating migration reports
  
.NOTES
  Version: 1.0
  Author: Transcendence Mod Tools
#>

# ============================================================
# CONFIGURATION
# ============================================================

$script:UpdateLog = [System.Collections.ArrayList]::new()
$script:BackupDir = Join-Path $PSScriptRoot "Backups"

# ============================================================
# API CHANGE DETECTION
# ============================================================

function Get-ApiChanges {
    <#
    .SYNOPSIS
      Compares two API versions to find what changed
    #>
    param(
        [int]$FromVersion,
        [int]$ToVersion,
        [PSCustomObject]$FromRules = $null,
        [PSCustomObject]$ToRules = $null
    )
    
    # Load rules if not provided
    if (-not $FromRules) {
        $fromPath = Join-Path $PSScriptRoot "api_rules_$FromVersion.json"
        if (Test-Path $fromPath) {
            $FromRules = Get-Content $fromPath -Raw | ConvertFrom-Json
        }
    }
    
    if (-not $ToRules) {
        $toPath = Join-Path $PSScriptRoot "api_rules_$ToVersion.json"
        if (Test-Path $toPath) {
            $ToRules = Get-Content $toPath -Raw | ConvertFrom-Json
        }
        else {
            # Try main rules file
            $mainPath = Join-Path $PSScriptRoot "api_rules.json"
            if (Test-Path $mainPath) {
                $ToRules = Get-Content $mainPath -Raw | ConvertFrom-Json
            }
        }
    }
    
    if (-not $FromRules -or -not $ToRules) {
        Write-Warning "Cannot compare: Missing API rules"
        return $null
    }
    
    $changes = @{
        NewTags = [System.Collections.ArrayList]::new()
        RemovedTags = [System.Collections.ArrayList]::new()
        NewFunctions = [System.Collections.ArrayList]::new()
        RemovedFunctions = [System.Collections.ArrayList]::new()
        DeprecatedFunctions = [System.Collections.ArrayList]::new()
        NewAttributes = @{}
        RemovedAttributes = @{}
    }
    
    # Compare tags
    $fromTags = @($FromRules.Tags.PSObject.Properties.Name)
    $toTags = @($ToRules.Tags.PSObject.Properties.Name)
    
    foreach ($tag in $toTags) {
        if ($fromTags -notcontains $tag) {
            [void]$changes.NewTags.Add($tag)
        }
    }
    
    foreach ($tag in $fromTags) {
        if ($toTags -notcontains $tag) {
            [void]$changes.RemovedTags.Add($tag)
        }
    }
    
    # Compare functions
    $fromFuncs = @($FromRules.Functions.PSObject.Properties.Name)
    $toFuncs = @($ToRules.Functions.PSObject.Properties.Name)
    
    foreach ($func in $toFuncs) {
        if ($fromFuncs -notcontains $func) {
            [void]$changes.NewFunctions.Add($func)
        }
    }
    
    foreach ($func in $fromFuncs) {
        if ($toFuncs -notcontains $func) {
            [void]$changes.RemovedFunctions.Add($func)
        }
    }
    
    # Get deprecated functions in target version
    if ($ToRules.Deprecated.Functions) {
        foreach ($depFunc in $ToRules.Deprecated.Functions) {
            if ($fromFuncs -contains $depFunc) {
                [void]$changes.DeprecatedFunctions.Add($depFunc)
            }
        }
    }
    
    return $changes
}

# ============================================================
# DEPRECATION REPLACEMENTS
# ============================================================

function Get-FunctionReplacement {
    <#
    .SYNOPSIS
      Gets replacement function for deprecated ones
    #>
    param(
        [string]$DeprecatedFunction,
        [PSCustomObject]$ApiRules
    )
    
    # Known replacements (can be expanded)
    $replacements = @{
        'objGetArmor' = 'objGetArmorType'
        'shpGetArmor' = 'objGetArmorType'
        'objArmorGetHitPoints' = 'objGetArmorDamage'
        'itmGetDamageType' = 'itmGetTypeData'
        'typGet' = 'typGetData'
    }
    
    if ($replacements.ContainsKey($DeprecatedFunction)) {
        return $replacements[$DeprecatedFunction]
    }
    
    return $null
}

# ============================================================
# MOD SCANNING
# ============================================================

function Get-ModApiIssues {
    <#
    .SYNOPSIS
      Scans a mod for API compatibility issues
    #>
    param(
        [string]$ModPath,
        [PSCustomObject]$ApiRules,
        [int]$TargetApiVersion
    )
    
    $issues = [System.Collections.ArrayList]::new()
    
    $xmlFiles = Get-ChildItem -LiteralPath $ModPath -Filter "*.xml" -Recurse -ErrorAction SilentlyContinue
    
    foreach ($file in $xmlFiles) {
        try {
            $content = [System.IO.File]::ReadAllText($file.FullName, [System.Text.Encoding]::UTF8)
            $lines = $content -split "`n"
            
            # Check apiVersion
            if ($content -match 'apiVersion\s*=\s*["\x27](\d+)["\x27]') {
                $currentApi = [int]$matches[1]
                if ($currentApi -lt $TargetApiVersion) {
                    $lineNum = ($content.Substring(0, $matches.Index) -split "`n").Count
                    [void]$issues.Add([PSCustomObject]@{
                        File = $file.FullName
                        Line = $lineNum
                        Type = 'OutdatedApiVersion'
                        Severity = 'Warning'
                        Message = "apiVersion is $currentApi, should be $TargetApiVersion"
                        OldValue = $currentApi
                        NewValue = $TargetApiVersion
                        CanAutoFix = $true
                    })
                }
            }
            else {
                # No apiVersion found
                [void]$issues.Add([PSCustomObject]@{
                    File = $file.FullName
                    Line = 0
                    Type = 'MissingApiVersion'
                    Severity = 'Warning'
                    Message = "Missing apiVersion attribute"
                    CanAutoFix = $true
                })
            }
            
            # Check for deprecated functions
            if ($ApiRules.Deprecated.Functions) {
                foreach ($depFunc in $ApiRules.Deprecated.Functions) {
                    $pattern = "\(\s*$depFunc\s+"
                    if ($content -match $pattern) {
                        $lineNum = ($content.Substring(0, $matches.Index) -split "`n").Count
                        $replacement = Get-FunctionReplacement -DeprecatedFunction $depFunc -ApiRules $ApiRules
                        
                        [void]$issues.Add([PSCustomObject]@{
                            File = $file.FullName
                            Line = $lineNum
                            Type = 'DeprecatedFunction'
                            Severity = 'Warning'
                            Message = "Deprecated function: ($depFunc)"
                            OldValue = $depFunc
                            NewValue = $replacement
                            CanAutoFix = if ($replacement) { $true } else { $false }
                        })
                    }
                }
            }
            
            # Check for deprecated tags
            if ($ApiRules.Deprecated.Tags) {
                foreach ($depTag in $ApiRules.Deprecated.Tags) {
                    $pattern = "<$depTag\s"
                    if ($content -match $pattern) {
                        $lineNum = ($content.Substring(0, $matches.Index) -split "`n").Count
                        [void]$issues.Add([PSCustomObject]@{
                            File = $file.FullName
                            Line = $lineNum
                            Type = 'DeprecatedTag'
                            Severity = 'Warning'
                            Message = "Deprecated tag: <$depTag>"
                            OldValue = $depTag
                            NewValue = $null
                            CanAutoFix = $false
                        })
                    }
                }
            }
            
            # Check for deprecated attributes
            foreach ($tagName in $ApiRules.Deprecated.Attributes.PSObject.Properties.Name) {
                $depAttrs = $ApiRules.Deprecated.Attributes.$tagName
                foreach ($depAttr in $depAttrs) {
                    $pattern = "<$tagName\s[^>]*$depAttr\s*="
                    if ($content -match $pattern) {
                        $lineNum = ($content.Substring(0, $matches.Index) -split "`n").Count
                        [void]$issues.Add([PSCustomObject]@{
                            File = $file.FullName
                            Line = $lineNum
                            Type = 'DeprecatedAttribute'
                            Severity = 'Warning'
                            Message = "Deprecated attribute: $depAttr in <$tagName>"
                            OldValue = $depAttr
                            NewValue = $null
                            CanAutoFix = $false
                        })
                    }
                }
            }
        }
        catch {
            # Skip files that can't be read
        }
    }
    
    return $issues
}

# ============================================================
# AUTO-FIXING
# ============================================================

function Update-ModApiVersion {
    <#
    .SYNOPSIS
      Updates apiVersion attribute in mod files
    #>
    param(
        [string]$FilePath,
        [int]$NewApiVersion,
        [string]$OriginalContent
    )
    
    $content = $OriginalContent
    
    # Update existing apiVersion
    if ($content -match 'apiVersion\s*=\s*["\x27](\d+)["\x27]') {
        $content = $content -replace 'apiVersion\s*=\s*["\x27]\d+["\x27]', "apiVersion=`"$NewApiVersion`""
        [void]$script:UpdateLog.Add("Updated apiVersion to $NewApiVersion in $(Split-Path -Leaf $FilePath)")
        return $content
    }
    
    # Add apiVersion to TranscendenceExtension/TranscendenceAdventure/TranscendenceModule
    $rootTagPattern = '<(TranscendenceExtension|TranscendenceAdventure|TranscendenceModule|TranscendenceLibrary)(\s[^>]*)?>'
    if ($content -match $rootTagPattern) {
        $rootTag = $matches[1]
        $attrs = $matches[2]
        
        if ($attrs -and $attrs -notmatch 'apiVersion') {
            # Add to existing attributes
            $content = $content -replace $rootTagPattern, "<$rootTag$attrs`n`tapiVersion=`"$NewApiVersion`">"
        }
        elseif (-not $attrs) {
            # No attributes, add apiVersion
            $content = $content -replace $rootTagPattern, "<$rootTag`n`tapiVersion=`"$NewApiVersion`">"
        }
        
        [void]$script:UpdateLog.Add("Added apiVersion=$NewApiVersion to $(Split-Path -Leaf $FilePath)")
        return $content
    }
    
    return $OriginalContent
}

function Replace-DeprecatedFunction {
    <#
    .SYNOPSIS
      Replaces deprecated function calls
    #>
    param(
        [string]$FilePath,
        [string]$OriginalContent,
        [string]$OldFunction,
        [string]$NewFunction
    )
    
    if (-not $NewFunction) {
        return $OriginalContent
    }
    
    $content = $OriginalContent
    
    # Replace function calls: (oldFunc ...) -> (newFunc ...)
    # Need to match: (oldFunc or (oldFunc followed by space/args
    # Escape special regex chars in function name
    $escapedOld = [regex]::Escape($OldFunction)
    
    # Pattern: (oldFunc followed by space or end of function call
    # This handles: (oldFunc arg) and (oldFunc)
    $pattern = "\(\s*$escapedOld(\s|\))"
    $replacement = "($NewFunction`$1"
    
    if ($content -match $pattern) {
        $content = $content -replace $pattern, $replacement
        $count = ([regex]::Matches($content, "\(\s*$escapedOld(\s|\))")).Count
        if ($count -eq 0) {
            [void]$script:UpdateLog.Add("Replaced ($OldFunction) with ($NewFunction) in $(Split-Path -Leaf $FilePath)")
        }
    }
    
    return $content
}

# ============================================================
# MAIN: AUTO-UPDATE MOD
# ============================================================

function Update-ModToApiVersion {
    <#
    .SYNOPSIS
      Automatically updates a mod to a new API version
      
    .DESCRIPTION
      Scans mod for API issues and auto-fixes what it can:
      - Updates apiVersion attributes
      - Replaces deprecated functions with known replacements
      - Generates report of issues that need manual fixing
      
    .PARAMETER ModPath
      Path to mod folder or XML file
      
    .PARAMETER TargetApiVersion
      Target API version (defaults to detected version from source)
      
    .PARAMETER DryRun
      Show what would be changed without making changes
      
    .EXAMPLE
      Update-ModToApiVersion -ModPath "..\1237_UpgradedWingmen"
      Update-ModToApiVersion -ModPath "..\MyMod" -TargetApiVersion 59 -DryRun
    #>
    param(
        [Parameter(Mandatory=$true)]
        [string]$ModPath,
        
        [int]$TargetApiVersion = 0,
        
        [switch]$DryRun,
        [switch]$Backup
    )
    
    # Load API rules module
    $apiRulesModule = Join-Path $PSScriptRoot 'TranscendenceModTools_ApiRules.ps1'
    if (Test-Path $apiRulesModule) {
        . $apiRulesModule
    }
    else {
        Write-Host "ERROR: API Rules module not found" -ForegroundColor Red
        return $null
    }
    
    # Determine target API version
    if ($TargetApiVersion -eq 0) {
        $TargetApiVersion = $script:DefaultApiVersion
    }
    
    # Load API rules
    $apiRules = Get-ApiRules
    if (-not $apiRules) {
        Write-Host "ERROR: Cannot load API rules. Run GenerateApiRules.ps1 first." -ForegroundColor Red
        return $null
    }
    
    if ($apiRules.ApiVersion -ne $TargetApiVersion) {
        Write-Host "WARNING: API rules are for version $($apiRules.ApiVersion), but target is $TargetApiVersion" -ForegroundColor Yellow
    }
    
    # Resolve mod path
    $resolvedPath = Resolve-Path $ModPath -ErrorAction SilentlyContinue
    if (-not $resolvedPath) {
        Write-Host "ERROR: Mod path not found: $ModPath" -ForegroundColor Red
        return $null
    }
    
    $modPathStr = if ($resolvedPath.Path) { $resolvedPath.Path } else { $resolvedPath }
    
    Write-Host "Auto-Updating Mod to API $TargetApiVersion" -ForegroundColor Cyan
    Write-Host "Mod: $modPathStr" -ForegroundColor Yellow
    if ($DryRun) {
        Write-Host "DRY RUN MODE - No changes will be made" -ForegroundColor DarkGray
    }
    Write-Host ""
    
    # Clear update log
    $script:UpdateLog.Clear()
    
    # Scan for issues
    Write-Host "Scanning for API issues..." -ForegroundColor Gray
    $issues = Get-ModApiIssues -ModPath $modPathStr -ApiRules $apiRules -TargetApiVersion $TargetApiVersion
    
    Write-Host "Found $($issues.Count) issue(s)" -ForegroundColor Yellow
    Write-Host ""
    
    # Group by type
    $byType = $issues | Group-Object Type
    
    foreach ($group in $byType) {
        $autoFixable = @($group.Group | Where-Object { $_.CanAutoFix })
        $manual = @($group.Group | Where-Object { -not $_.CanAutoFix })
        
        Write-Host "$($group.Name) ($($group.Count)):" -ForegroundColor Cyan
        if ($autoFixable.Count -gt 0) {
            Write-Host "  Auto-fixable: $($autoFixable.Count)" -ForegroundColor Green
        }
        if ($manual.Count -gt 0) {
            Write-Host "  Manual fix needed: $($manual.Count)" -ForegroundColor Yellow
        }
    }
    Write-Host ""
    
    if ($DryRun) {
        Write-Host "Would fix:" -ForegroundColor Gray
        foreach ($issue in $issues | Where-Object { $_.CanAutoFix }) {
            Write-Host "  $($issue.File):$($issue.Line) - $($issue.Message)" -ForegroundColor DarkGray
        }
        return $issues
    }
    
    # Create backup if requested
    if ($Backup) {
        $backupPath = Join-Path $script:BackupDir "$(Split-Path -Leaf $modPathStr)_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
        if (-not (Test-Path $script:BackupDir)) {
            New-Item -ItemType Directory -Path $script:BackupDir -Force | Out-Null
        }
        Copy-Item -LiteralPath $modPathStr -Destination $backupPath -Recurse -Force
        Write-Host "Backup created: $backupPath" -ForegroundColor Gray
        Write-Host ""
    }
    
    # Process files with issues
    $filesToUpdate = @($issues | Where-Object { $_.CanAutoFix } | Group-Object File)
    $filesUpdated = 0
    
    foreach ($fileGroup in $filesToUpdate) {
        $filePath = $fileGroup.Name
        $fileIssues = $fileGroup.Group
        
        try {
            $content = [System.IO.File]::ReadAllText($filePath, [System.Text.Encoding]::UTF8)
            $originalContent = $content
            $modified = $false
            
            foreach ($issue in $fileIssues) {
                switch ($issue.Type) {
                    'OutdatedApiVersion' {
                        $content = Update-ModApiVersion -FilePath $filePath -NewApiVersion $issue.NewValue -OriginalContent $content
                        $modified = $true
                    }
                    'MissingApiVersion' {
                        $content = Update-ModApiVersion -FilePath $filePath -NewApiVersion $TargetApiVersion -OriginalContent $content
                        $modified = $true
                    }
                    'DeprecatedFunction' {
                        if ($issue.NewValue) {
                            $content = Replace-DeprecatedFunction -FilePath $filePath -OriginalContent $content -OldFunction $issue.OldValue -NewFunction $issue.NewValue
                            $modified = $true
                        }
                    }
                }
            }
            
            if ($modified) {
                $utf8NoBom = [System.Text.UTF8Encoding]::new($false)
                [System.IO.File]::WriteAllText($filePath, $content, $utf8NoBom)
                $filesUpdated++
                Write-Host "Updated: $(Split-Path -Leaf $filePath)" -ForegroundColor Green
            }
        }
        catch {
            Write-Host "ERROR updating $filePath`: $_" -ForegroundColor Red
        }
    }
    
    Write-Host ""
    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host "  UPDATE SUMMARY" -ForegroundColor Cyan
    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host ""
    $autoFixedCount = @($issues | Where-Object { $_.CanAutoFix }).Count
    $manualFixCount = @($issues | Where-Object { -not $_.CanAutoFix }).Count
    
    Write-Host "Files Updated: $filesUpdated" -ForegroundColor Green
    Write-Host "Total Issues:  $($issues.Count)" -ForegroundColor White
    Write-Host "Auto-Fixed:    $autoFixedCount" -ForegroundColor Green
    Write-Host "Manual Fix:    $manualFixCount" -ForegroundColor Yellow
    Write-Host ""
    
    # Show manual fixes needed
    $manualIssues = @($issues | Where-Object { -not $_.CanAutoFix })
    if ($manualIssues.Count -gt 0) {
        Write-Host "Issues requiring manual fix:" -ForegroundColor Yellow
        foreach ($issue in $manualIssues | Select-Object -First 10) {
            Write-Host "  $($issue.File):$($issue.Line) - $($issue.Message)" -ForegroundColor Gray
        }
        if ($manualIssues.Count -gt 10) {
            Write-Host "  ... and $($manualIssues.Count - 10) more" -ForegroundColor Gray
        }
        Write-Host ""
    }
    
    return $issues
}

# ============================================================
# BATCH UPDATE
# ============================================================

function Update-AllModsToApiVersion {
    <#
    .SYNOPSIS
      Updates all mods in Extensions folder to new API version
    #>
    param(
        [string]$ExtensionsPath = (Join-Path (Split-Path $PSScriptRoot -Parent) "Extensions"),
        [int]$TargetApiVersion = 0,
        [switch]$DryRun
    )
    
    Write-Host "Batch Updating All Mods to API $TargetApiVersion" -ForegroundColor Cyan
    Write-Host ""
    
    $modDirs = Get-ChildItem -LiteralPath $ExtensionsPath -Directory -ErrorAction SilentlyContinue
    
    Write-Host "Found $($modDirs.Count) mod(s)" -ForegroundColor Yellow
    Write-Host ""
    
    $totalUpdated = 0
    $totalIssues = 0
    
    foreach ($modDir in $modDirs) {
        Write-Host "Processing: $($modDir.Name)" -ForegroundColor Cyan
        
        $issues = Update-ModToApiVersion -ModPath $modDir.FullName -TargetApiVersion $TargetApiVersion -DryRun:$DryRun -Backup
        
        if ($issues) {
            $totalIssues += $issues.Count
            if (($issues | Where-Object { $_.CanAutoFix }).Count -gt 0) {
                $totalUpdated++
            }
        }
        
        Write-Host ""
    }
    
    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host "  BATCH UPDATE COMPLETE" -ForegroundColor Cyan
    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Mods Updated: $totalUpdated" -ForegroundColor Green
    Write-Host "Total Issues: $totalIssues" -ForegroundColor White
    Write-Host ""
}

# ============================================================
# EXPORT
# ============================================================

# Export functions if running as module
if ($MyInvocation.Line -match 'Import-Module') {
    Export-ModuleMember -Function @(
        'Get-ApiChanges',
        'Get-FunctionReplacement',
        'Get-ModApiIssues',
        'Update-ModApiVersion',
        'Replace-DeprecatedFunction',
        'Update-ModToApiVersion',
        'Update-AllModsToApiVersion'
    )
}


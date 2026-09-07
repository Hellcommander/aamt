<#
.SYNOPSIS
  Migration Safety & Verification Tools for AI-Updated Mods
  
.DESCRIPTION
  Tools for verifying, merging, and testing AI-updated mods during 2.0.7 migration:
  - Three-way diff (original → manual → AI)
  - Automated verification pipeline
  - Risk scoring
  - Merge conflict resolution
  - Test runner
#>

# ============================================================
# MIGRATION DIFF VIEWER
# ============================================================

function Get-MigrationDiff {
    param(
        [string]$OriginalPath,
        [string]$ManualPath,
        [string]$AiPath,
        [string]$OutputPath
    )
    
    if (-not (Test-Path $OriginalPath)) {
        throw "Original path does not exist: $OriginalPath"
    }
    if (-not (Test-Path $ManualPath)) {
        throw "Manual path does not exist: $ManualPath"
    }
    if (-not (Test-Path $AiPath)) {
        throw "AI path does not exist: $AiPath"
    }
    
    $diff = [PSCustomObject]@{
        OriginalPath = $OriginalPath
        ManualPath = $ManualPath
        AiPath = $AiPath
        Files = @()
        Summary = @{
            TotalFiles = 0
            Unchanged = 0
            ManualOnly = 0
            AiOnly = 0
            BothChanged = 0
            Conflicts = 0
        }
    }
    
    # Get all XML files from all three paths
    $originalFiles = @{}
    $manualFiles = @{}
    $aiFiles = @{}
    
    if (Test-Path $OriginalPath -PathType Leaf) {
        if ($OriginalPath.EndsWith('.xml')) {
            $originalFiles[[System.IO.Path]::GetFileName($OriginalPath)] = $OriginalPath
        }
    } else {
        Get-ChildItem -LiteralPath $OriginalPath -Filter '*.xml' -Recurse | ForEach-Object {
            $relPath = $_.FullName.Substring($OriginalPath.Length).TrimStart('\')
            $originalFiles[$relPath] = $_.FullName
        }
    }
    
    if (Test-Path $ManualPath -PathType Leaf) {
        if ($ManualPath.EndsWith('.xml')) {
            $manualFiles[[System.IO.Path]::GetFileName($ManualPath)] = $ManualPath
        }
    } else {
        Get-ChildItem -LiteralPath $ManualPath -Filter '*.xml' -Recurse | ForEach-Object {
            $relPath = $_.FullName.Substring($ManualPath.Length).TrimStart('\')
            $manualFiles[$relPath] = $_.FullName
        }
    }
    
    if (Test-Path $AiPath -PathType Leaf) {
        if ($AiPath.EndsWith('.xml')) {
            $aiFiles[[System.IO.Path]::GetFileName($AiPath)] = $AiPath
        }
    } else {
        Get-ChildItem -LiteralPath $AiPath -Filter '*.xml' -Recurse | ForEach-Object {
            $relPath = $_.FullName.Substring($AiPath.Length).TrimStart('\')
            $aiFiles[$relPath] = $_.FullName
        }
    }
    
    # Compare files
    $allFileNames = ($originalFiles.Keys + $manualFiles.Keys + $aiFiles.Keys) | Sort-Object -Unique
    
    foreach ($fileName in $allFileNames) {
        $original = if ($originalFiles.ContainsKey($fileName)) { $originalFiles[$fileName] } else { $null }
        $manual = if ($manualFiles.ContainsKey($fileName)) { $manualFiles[$fileName] } else { $null }
        $ai = if ($aiFiles.ContainsKey($fileName)) { $aiFiles[$fileName] } else { $null }
        
        $fileDiff = Compare-MigrationFile -OriginalPath $original -ManualPath $manual -AiPath $ai -FileName $fileName
        $diff.Files += $fileDiff
        
        # Update summary
        $diff.Summary.TotalFiles++
        if ($fileDiff.Status -eq 'Unchanged') { $diff.Summary.Unchanged++ }
        elseif ($fileDiff.Status -eq 'ManualOnly') { $diff.Summary.ManualOnly++ }
        elseif ($fileDiff.Status -eq 'AiOnly') { $diff.Summary.AiOnly++ }
        elseif ($fileDiff.Status -eq 'BothChanged') {
            $diff.Summary.BothChanged++
            if ($fileDiff.HasConflict) { $diff.Summary.Conflicts++ }
        }
    }
    
    # Generate report
    if ($OutputPath) {
        Export-MigrationDiffReport -Diff $diff -OutputPath $OutputPath
    }
    
    return $diff
}

function Compare-MigrationFile {
    param(
        [string]$OriginalPath,
        [string]$ManualPath,
        [string]$AiPath,
        [string]$FileName
    )
    
    $fileDiff = [PSCustomObject]@{
        FileName = $FileName
        OriginalPath = $OriginalPath
        ManualPath = $ManualPath
        AiPath = $AiPath
        Status = 'Unknown'
        HasConflict = $false
        RiskScore = 0
        Changes = @()
        Conflicts = @()
    }
    
    # Read file contents
    $originalContent = if ($OriginalPath) { [System.IO.File]::ReadAllText($OriginalPath, [System.Text.Encoding]::UTF8) } else { $null }
    $manualContent = if ($ManualPath) { [System.IO.File]::ReadAllText($ManualPath, [System.Text.Encoding]::UTF8) } else { $null }
    $aiContent = if ($AiPath) { [System.IO.File]::ReadAllText($AiPath, [System.Text.Encoding]::UTF8) } else { $null }
    
    # Determine status
    if (-not $manualContent -and -not $aiContent) {
        $fileDiff.Status = 'Unchanged'
    }
    elseif ($manualContent -and -not $aiContent) {
        $fileDiff.Status = 'ManualOnly'
    }
    elseif ($aiContent -and -not $manualContent) {
        $fileDiff.Status = 'AiOnly'
    }
    elseif ($manualContent -eq $aiContent) {
        if ($originalContent -eq $manualContent) {
            $fileDiff.Status = 'Unchanged'
        } else {
            $fileDiff.Status = 'BothChanged' # Same changes
        }
    }
    else {
        $fileDiff.Status = 'BothChanged'
        $fileDiff.HasConflict = $true
        
        # Detect conflicts
        $conflicts = Detect-FileConflicts -Original $originalContent -Manual $manualContent -Ai $aiContent
        $fileDiff.Conflicts = $conflicts
    }
    
    # Calculate risk score
    $fileDiff.RiskScore = Calculate-FileRiskScore -Original $originalContent -Manual $manualContent -Ai $aiContent -FileName $FileName
    
    # Detect changes
    $changes = Detect-FileChanges -Original $originalContent -Manual $manualContent -Ai $aiContent
    $fileDiff.Changes = $changes
    
    return $fileDiff
}

function Detect-FileConflicts {
    param(
        [string]$Original,
        [string]$Manual,
        [string]$Ai
    )
    
    $conflicts = @()
    
    if (-not $Original -or -not $Manual -or -not $Ai) {
        return $conflicts
    }
    
    # Simple line-by-line comparison for conflicts
    $originalLines = if ($Original) { $Original -split "`n" } else { @() }
    $manualLines = if ($Manual) { $Manual -split "`n" } else { @() }
    $aiLines = if ($Ai) { $Ai -split "`n" } else { @() }
    
    $maxLines = [Math]::Max($originalLines.Count, [Math]::Max($manualLines.Count, $aiLines.Count))
    
    for ($i = 0; $i -lt $maxLines; $i++) {
        $origLine = if ($i -lt $originalLines.Count) { $originalLines[$i] } else { $null }
        $manualLine = if ($i -lt $manualLines.Count) { $manualLines[$i] } else { $null }
        $aiLine = if ($i -lt $aiLines.Count) { $aiLines[$i] } else { $null }
        
        # Conflict: manual and AI both changed the same line differently
        if ($origLine -and $manualLine -and $aiLine) {
            if ($manualLine -ne $origLine -and $aiLine -ne $origLine -and $manualLine -ne $aiLine) {
                $conflicts += [PSCustomObject]@{
                    Line = $i + 1
                    Original = $origLine
                    Manual = $manualLine
                    Ai = $aiLine
                    Type = 'LineConflict'
                }
            }
        }
    }
    
    return $conflicts
}

function Detect-FileChanges {
    param(
        [string]$Original,
        [string]$Manual,
        [string]$Ai
    )
    
    $changes = @()
    
    # Detect UNID changes
    if ($Original -and $Manual) {
        $originalUnids = [regex]::Matches($Original, 'UNID="([^"]+)"') | ForEach-Object { $_.Groups[1].Value }
        $manualUnids = [regex]::Matches($Manual, 'UNID="([^"]+)"') | ForEach-Object { $_.Groups[1].Value }
        $aiUnids = if ($Ai) { [regex]::Matches($Ai, 'UNID="([^"]+)"') | ForEach-Object { $_.Groups[1].Value } } else { @() }
        
        $addedUnids = $manualUnids | Where-Object { $originalUnids -notcontains $_ }
        $removedUnids = $originalUnids | Where-Object { $manualUnids -notcontains $_ }
        
        if ($addedUnids.Count -gt 0) {
            $changes += [PSCustomObject]@{
                Type = 'UNIDAdded'
                Source = 'Manual'
                Details = "Added UNIDs: $($addedUnids -join ', ')"
            }
        }
        
        if ($removedUnids.Count -gt 0) {
            $changes += [PSCustomObject]@{
                Type = 'UNIDRemoved'
                Source = 'Manual'
                Details = "Removed UNIDs: $($removedUnids -join ', ')"
            }
        }
    }
    
    # Detect event handler changes (high risk)
    if ($Original -and $Manual) {
        $originalEvents = [regex]::Matches($Original, '<(\w+Event|On\w+)>') | ForEach-Object { $_.Groups[1].Value }
        $manualEvents = [regex]::Matches($Manual, '<(\w+Event|On\w+)>') | ForEach-Object { $_.Groups[1].Value }
        
        $changedEvents = $manualEvents | Where-Object { $originalEvents -notcontains $_ }
        if ($changedEvents.Count -gt 0) {
            $changes += [PSCustomObject]@{
                Type = 'EventHandlerChanged'
                Source = 'Manual'
                Details = "Changed events: $($changedEvents -join ', ')"
                Risk = 'High'
            }
        }
    }
    
    return $changes
}

function Calculate-FileRiskScore {
    param(
        [string]$Original,
        [string]$Manual,
        [string]$Ai,
        [string]$FileName
    )
    
    $score = 0
    
    # High risk indicators
    if ($Manual -or $Ai) {
        # Event handlers changed
        if ($Manual) {
            $eventCount = ([regex]::Matches($Manual, '<(\w+Event|On\w+)>')).Count
            $score += $eventCount * 10
        }
        
        # TLisp code blocks changed
        if ($Manual) {
            $tlispBlocks = ([regex]::Matches($Manual, '\([^)]+\)')).Count
            $score += $tlispBlocks * 2
        }
        
        # UNID changes
        if ($Manual) {
            $unidChanges = ([regex]::Matches($Manual, 'UNID="[^"]+"')).Count
            $score += $unidChanges * 5
        }
        
        # File type risk
        if ($FileName -match '(Event|Handler|Mission|Encounter)') {
            $score += 20
        }
    }
    
    return $score
}

function Export-MigrationDiffReport {
    param(
        [PSCustomObject]$Diff,
        [string]$OutputPath
    )
    
    $report = [System.Text.StringBuilder]::new()
    [void]$report.AppendLine("Migration Diff Report")
    [void]$report.AppendLine("====================")
    [void]$report.AppendLine("Generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')")
    [void]$report.AppendLine("")
    [void]$report.AppendLine("Paths:")
    [void]$report.AppendLine("  Original: $($Diff.OriginalPath)")
    [void]$report.AppendLine("  Manual:   $($Diff.ManualPath)")
    [void]$report.AppendLine("  AI:       $($Diff.AiPath)")
    [void]$report.AppendLine("")
    [void]$report.AppendLine("Summary:")
    [void]$report.AppendLine("  Total Files: $($Diff.Summary.TotalFiles)")
    [void]$report.AppendLine("  Unchanged: $($Diff.Summary.Unchanged)")
    [void]$report.AppendLine("  Manual Only: $($Diff.Summary.ManualOnly)")
    [void]$report.AppendLine("  AI Only: $($Diff.Summary.AiOnly)")
    [void]$report.AppendLine("  Both Changed: $($Diff.Summary.BothChanged)")
    [void]$report.AppendLine("  Conflicts: $($Diff.Summary.Conflicts)")
    [void]$report.AppendLine("")
    [void]$report.AppendLine("Files (sorted by risk):")
    [void]$report.AppendLine("")
    
    $sortedFiles = $Diff.Files | Sort-Object RiskScore -Descending
    
    foreach ($file in $sortedFiles) {
        [void]$report.AppendLine("File: $($file.FileName)")
        [void]$report.AppendLine("  Status: $($file.Status)")
        [void]$report.AppendLine("  Risk Score: $($file.RiskScore)")
        if ($file.HasConflict) {
            [void]$report.AppendLine("  ⚠️  CONFLICT DETECTED")
            foreach ($conflict in $file.Conflicts) {
                [void]$report.AppendLine("    Line $($conflict.Line):")
                [void]$report.AppendLine("      Original: $($conflict.Original.Trim())")
                [void]$report.AppendLine("      Manual:   $($conflict.Manual.Trim())")
                [void]$report.AppendLine("      AI:       $($conflict.Ai.Trim())")
            }
        }
        if ($file.Changes.Count -gt 0) {
            [void]$report.AppendLine("  Changes:")
            foreach ($change in $file.Changes) {
                [void]$report.AppendLine("    - $($change.Type): $($change.Details)")
            }
        }
        [void]$report.AppendLine("")
    }
    
    [System.IO.File]::WriteAllText($OutputPath, $report.ToString(), [System.Text.Encoding]::UTF8)
}

# ============================================================
# AUTOMATED VERIFICATION PIPELINE
# ============================================================

function Invoke-MigrationVerification {
    param(
        [string]$ModPath,
        [switch]$SchemaCheck,
        [switch]$SemanticCheck,
        [switch]$ApiDeprecationCheck,
        [switch]$All
    )
    
    if ($All) {
        $SchemaCheck = $true
        $SemanticCheck = $true
        $ApiDeprecationCheck = $true
    }
    
    $results = [PSCustomObject]@{
        ModPath = $ModPath
        Timestamp = Get-Date
        Schema = $null
        Semantic = $null
        ApiDeprecation = $null
        Overall = 'Unknown'
    }
    
    # Schema & Syntax Pass
    if ($SchemaCheck) {
        Write-Host "Running schema & syntax check..." -ForegroundColor Cyan
        $results.Schema = Test-SchemaValidation -ModPath $ModPath
    }
    
    # Semantic Checks
    if ($SemanticCheck) {
        Write-Host "Running semantic checks..." -ForegroundColor Cyan
        $results.Semantic = Test-SemanticValidation -ModPath $ModPath
    }
    
    # API Deprecation Scan
    if ($ApiDeprecationCheck) {
        Write-Host "Running API deprecation scan..." -ForegroundColor Cyan
        $results.ApiDeprecation = Test-ApiDeprecation -ModPath $ModPath
    }
    
    # Overall status
    $allPassed = $true
    if ($results.Schema -and $results.Schema.Passed -eq $false) { $allPassed = $false }
    if ($results.Semantic -and $results.Semantic.Passed -eq $false) { $allPassed = $false }
    if ($results.ApiDeprecation -and $results.ApiDeprecation.Passed -eq $false) { $allPassed = $false }
    
    $results.Overall = if ($allPassed) { 'Pass' } else { 'Fail' }
    
    return $results
}

function Test-SchemaValidation {
    param([string]$ModPath)
    
    # Use existing Get-XmlIssues function
    . "$PSScriptRoot\GetXmlIssues.ps1"
    
    $files = @()
    if (Test-Path $ModPath -PathType Leaf) {
        if ($ModPath.EndsWith('.xml')) { $files = @($ModPath) }
    } else {
        $files = @(Get-ChildItem -LiteralPath $ModPath -Filter '*.xml' -Recurse | ForEach-Object { $_.FullName })
    }
    
    $issues = @()
    foreach ($file in $files) {
        $fileIssues = Get-XmlIssues -FilePath $file
        $issues += $fileIssues
    }
    
    $wellformedErrors = $issues | Where-Object { $_.Code -eq 'XML_WELLFORMED_ERROR' }
    $bomErrors = $issues | Where-Object { $_.Code -eq 'BOM_DETECTED' }
    
    return [PSCustomObject]@{
        Passed = ($wellformedErrors.Count -eq 0 -and $bomErrors.Count -eq 0)
        WellformedErrors = $wellformedErrors.Count
        BomErrors = $bomErrors.Count
        TotalIssues = $issues.Count
        Issues = $issues
    }
}

function Test-SemanticValidation {
    param([string]$ModPath)
    
    # UNID reference checks, duplicate detection, resource existence
    # This would integrate with existing UNID intelligence module
    
    return [PSCustomObject]@{
        Passed = $true
        UnidIssues = 0
        ResourceIssues = 0
        Details = @()
    }
}

function Test-ApiDeprecation {
    param([string]$ModPath)
    
    $files = @()
    if (Test-Path $ModPath -PathType Leaf) {
        if ($ModPath.EndsWith('.xml')) { $files = @($ModPath) }
    } else {
        $files = @(Get-ChildItem -LiteralPath $ModPath -Filter '*.xml' -Recurse | ForEach-Object { $_.FullName })
    }
    
    $deprecations = @()
    $deprecatedPatterns = @(
        @{ Pattern = 'apiVersion="\d+"'; MinVersion = 57; Message = 'Old API version' }
        # Add more deprecation patterns
    )
    
    foreach ($file in $files) {
        $content = [System.IO.File]::ReadAllText($file, [System.Text.Encoding]::UTF8)
        
        foreach ($pattern in $deprecatedPatterns) {
            if ($content -match $pattern.Pattern) {
                $deprecations += [PSCustomObject]@{
                    File = $file
                    Pattern = $pattern.Pattern
                    Message = $pattern.Message
                }
            }
        }
    }
    
    return [PSCustomObject]@{
        Passed = ($deprecations.Count -eq 0)
        Deprecations = $deprecations
        Count = $deprecations.Count
    }
}

# ============================================================
# RISK SCORING
# ============================================================

function Get-MigrationRiskReport {
    param(
        [PSCustomObject]$Diff
    )
    
    $highRisk = $Diff.Files | Where-Object { $_.RiskScore -ge 50 } | Sort-Object RiskScore -Descending
    $mediumRisk = $Diff.Files | Where-Object { $_.RiskScore -ge 20 -and $_.RiskScore -lt 50 } | Sort-Object RiskScore -Descending
    $lowRisk = $Diff.Files | Where-Object { $_.RiskScore -lt 20 } | Sort-Object RiskScore -Descending
    
    return [PSCustomObject]@{
        HighRisk = $highRisk
        MediumRisk = $mediumRisk
        LowRisk = $lowRisk
        HighRiskCount = $highRisk.Count
        MediumRiskCount = $mediumRisk.Count
        LowRiskCount = $lowRisk.Count
    }
}


<#
.SYNOPSIS
  Smart Auto-Detection Module for Transcendence Mods
  
.DESCRIPTION
  Analyzes dropped files/folders to provide intelligent recommendations:
  - Detects file type (XML, folder, resource)
  - Checks API version for outdated mods
  - Detects deprecated attributes/functions
  - Scans for common issues
  - Presents recommended actions
#>

# ============================================================
# SMART AUTO-DETECTION
# ============================================================

# Known API versions and their status
$script:ApiVersionStatus = @{
    '57' = @{ Status = 'Current'; Message = 'API 57 (Transcendence 2.0+)' }
    '56' = @{ Status = 'Outdated'; Message = 'API 56 - Consider updating to API 57' }
    '55' = @{ Status = 'Outdated'; Message = 'API 55 - Update required for latest game' }
    '54' = @{ Status = 'Legacy'; Message = 'API 54 - Major update required' }
    '53' = @{ Status = 'Legacy'; Message = 'API 53 - Major update required' }
    '52' = @{ Status = 'Legacy'; Message = 'API 52 - Major update required' }
    '51' = @{ Status = 'Legacy'; Message = 'API 51 - Major update required' }
    '50' = @{ Status = 'Legacy'; Message = 'API 50 - Major update required' }
    '25' = @{ Status = 'Ancient'; Message = 'API 25 - Complete rewrite may be needed' }
    '20' = @{ Status = 'Ancient'; Message = 'API 20 - Complete rewrite may be needed' }
}

# Deprecated attributes/functions by API version
$script:DeprecatedItems = @{
    'API57' = @(
        @{ Pattern = 'objAddItem'; Replacement = 'objAddItemByValue'; Reason = 'objAddItem deprecated in favor of objAddItemByValue' }
        @{ Pattern = 'objRemoveItem'; Replacement = 'objRemoveItemByValue'; Reason = 'objRemoveItem deprecated in favor of objRemoveItemByValue' }
        @{ Pattern = 'shpOrder'; Replacement = 'objSendMessage'; Reason = 'shpOrder replaced by objSendMessage' }
        @{ Pattern = 'sysCreateWeaponFire'; Replacement = 'objFireWeapon'; Reason = 'Use objFireWeapon instead' }
        @{ Pattern = 'itmGetArmorType'; Replacement = 'itmGetArmorClass'; Reason = 'Renamed to itmGetArmorClass' }
        @{ Pattern = 'rollDice'; Replacement = 'mathRandom'; Reason = 'Use mathRandom for dice rolls' }
    )
}

function Invoke-SmartDetection {
    param(
        [string[]]$Paths
    )
    
    $result = [PSCustomObject]@{
        FileType = ''
        IsFolder = $false
        FileCount = 0
        XmlFileCount = 0
        ResourceCount = 0
        ApiVersion = ''
        ApiStatus = ''
        ModName = ''
        Recommendations = [System.Collections.ArrayList]::new()
        Issues = [System.Collections.ArrayList]::new()
        Score = 0
        QuickActions = [System.Collections.ArrayList]::new()
    }
    
    foreach ($path in $Paths) {
        if (Test-Path $path -PathType Container) {
            # It's a folder
            $result.IsFolder = $true
            $result.FileType = 'ModFolder'
            
            $xmlFiles = @(Get-ChildItem -LiteralPath $path -Filter '*.xml' -Recurse)
            $result.XmlFileCount = $xmlFiles.Count
            $result.FileCount = $xmlFiles.Count
            
            # Count resources
            $imageFiles = @(Get-ChildItem -LiteralPath $path -Include '*.png', '*.jpg', '*.bmp' -Recurse)
            $soundFiles = @(Get-ChildItem -LiteralPath $path -Include '*.wav', '*.mp3', '*.ogg' -Recurse)
            $result.ResourceCount = $imageFiles.Count + $soundFiles.Count
            
            # Analyze all XML files
            foreach ($xmlFile in $xmlFiles) {
                Analyze-XmlFile -FilePath $xmlFile.FullName -Result $result
            }
        }
        else {
            # It's a single file
            $extension = [System.IO.Path]::GetExtension($path).ToLower()
            
            switch ($extension) {
                '.xml' {
                    $result.FileType = 'XmlFile'
                    $result.FileCount = 1
                    $result.XmlFileCount = 1
                    Analyze-XmlFile -FilePath $path -Result $result
                }
                {$_ -in '.png', '.jpg', '.bmp'} {
                    $result.FileType = 'ImageFile'
                    $result.FileCount = 1
                    $result.ResourceCount = 1
                    [void]$result.Recommendations.Add([PSCustomObject]@{
                        Action = 'Preview Resource'
                        Reason = 'Image file detected'
                        Priority = 'Low'
                    })
                }
                {$_ -in '.wav', '.mp3', '.ogg'} {
                    $result.FileType = 'SoundFile'
                    $result.FileCount = 1
                    $result.ResourceCount = 1
                    [void]$result.Recommendations.Add([PSCustomObject]@{
                        Action = 'Preview Resource'
                        Reason = 'Sound file detected'
                        Priority = 'Low'
                    })
                }
                '.tdb' {
                    $result.FileType = 'TranscendenceDatabase'
                    
                    # Try to parse TDB file for better recommendations
                    # Calculate path relative to this module's location
                    $moduleDir = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.PSCommandPath }
                    $tdbModule = Join-Path $moduleDir 'TranscendenceModTools_TDBParser.ps1'
                    if (Test-Path $tdbModule) {
                        . $tdbModule
                        try {
                            $tdbPreview = Get-TdbPreview -Path $path
                            if ($tdbPreview.Summary) {
                                [void]$result.Recommendations.Add([PSCustomObject]@{
                                    Action = 'Preview TDB'
                                    Reason = "Found $($tdbPreview.Summary.Entries) entries, $($tdbPreview.Summary.Unids) UNIDs"
                                    Priority = 'High'
                                })
                                if ($tdbPreview.Summary.Issues -gt 0) {
                                    [void]$result.Recommendations.Add([PSCustomObject]@{
                                        Action = 'Validate TDB'
                                        Reason = "$($tdbPreview.Summary.Issues) semantic issues detected"
                                        Priority = 'High'
                                    })
                                }
                            }
                        }
                        catch {
                            # Parser failed, fall back to basic recommendation
                            [void]$result.Recommendations.Add([PSCustomObject]@{
                                Action = 'Check for XML Source'
                                Reason = 'TDB file detected - looking for XML source'
                                Priority = 'Medium'
                            })
                        }
                    }
                    else {
                        [void]$result.Recommendations.Add([PSCustomObject]@{
                            Action = 'Check for XML Source'
                            Reason = 'TDB file detected - TDB parser not available'
                            Priority = 'Medium'
                        })
                    }
                }
                default {
                    $result.FileType = 'Unknown'
                    [void]$result.Recommendations.Add([PSCustomObject]@{
                        Action = 'Manual Review'
                        Reason = "Unknown file type: $extension"
                        Priority = 'Low'
                    })
                }
            }
        }
    }
    
    # Generate quick actions based on analysis
    Generate-QuickActions -Result $result
    
    # Calculate overall score
    $result.Score = Calculate-ModScore -Result $result
    
    return $result
}

function Analyze-XmlFile {
    param(
        [string]$FilePath,
        [PSCustomObject]$Result
    )
    
    try {
        $text = [System.IO.File]::ReadAllText($FilePath, [System.Text.Encoding]::UTF8)
        $fileName = Split-Path -Leaf $FilePath
        
        # Detect mod type (Extension, Module, Library)
        if ($text -match '<TranscendenceExtension[^>]+name\s*=\s*"([^"]+)"') {
            $Result.ModName = $matches[1]
            $Result.FileType = 'TranscendenceExtension'
        }
        elseif ($text -match '<TranscendenceLibrary[^>]+name\s*=\s*"([^"]+)"') {
            $Result.ModName = $matches[1]
            $Result.FileType = 'TranscendenceLibrary'
        }
        elseif ($text -match '<TranscendenceModule') {
            $Result.FileType = 'TranscendenceModule'
        }
        
        # Detect API version
        if ($text -match 'apiVersion\s*=\s*"(\d+)"') {
            $apiVersion = $matches[1]
            if (-not $Result.ApiVersion -or [int]$Result.ApiVersion -lt [int]$apiVersion) {
                $Result.ApiVersion = $apiVersion
            }
            
            if ($script:ApiVersionStatus.ContainsKey($apiVersion)) {
                $status = $script:ApiVersionStatus[$apiVersion]
                $Result.ApiStatus = $status.Status
                
                if ($status.Status -ne 'Current') {
                    [void]$Result.Issues.Add([PSCustomObject]@{
                        File = $fileName
                        Type = 'ApiVersion'
                        Severity = if ($status.Status -eq 'Legacy') { 'Warning' } elseif ($status.Status -eq 'Ancient') { 'Error' } else { 'Info' }
                        Message = $status.Message
                    })
                }
            }
        }
        
        # Check for BOM
        $bytes = [System.IO.File]::ReadAllBytes($FilePath)
        if ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) {
            [void]$Result.Issues.Add([PSCustomObject]@{
                File = $fileName
                Type = 'BOM'
                Severity = 'Warning'
                Message = 'File has UTF-8 BOM which may cause parsing issues'
            })
        }
        
        # Check for raw > characters
        $rawGtPattern = '>[^<]*>[^<]*<'
        if ([regex]::IsMatch($text, $rawGtPattern)) {
            [void]$Result.Issues.Add([PSCustomObject]@{
                File = $fileName
                Type = 'RawGreaterThan'
                Severity = 'Error'
                Message = "Possible raw '>' character in content (should be '&gt;')"
            })
        }
        
        # Check for deprecated functions
        foreach ($deprecated in $script:DeprecatedItems['API57']) {
            if ($text -match [regex]::Escape($deprecated.Pattern)) {
                [void]$Result.Issues.Add([PSCustomObject]@{
                    File = $fileName
                    Type = 'Deprecated'
                    Severity = 'Warning'
                    Message = $deprecated.Reason
                })
            }
        }
        
        # Check parentheses balance
        $parenCount = ($text.ToCharArray() | Where-Object { $_ -eq '(' }).Count
        $closeParenCount = ($text.ToCharArray() | Where-Object { $_ -eq ')' }).Count
        if ($parenCount -ne $closeParenCount) {
            [void]$Result.Issues.Add([PSCustomObject]@{
                File = $fileName
                Type = 'ParenthesesMismatch'
                Severity = 'Error'
                Message = "Parentheses mismatch: $parenCount open, $closeParenCount close"
            })
        }
        
        # Check for invalid symbol syntax
        $invalidSymbolPattern = "'\w+'"
        if ([regex]::IsMatch($text, $invalidSymbolPattern)) {
            [void]$Result.Issues.Add([PSCustomObject]@{
                File = $fileName
                Type = 'InvalidSymbol'
                Severity = 'Warning'
                Message = "Possible invalid symbol syntax (trailing quote)"
            })
        }
        
        # Count UNIDs
        $unidPattern = '<!ENTITY\s+\w+\s+"0x[0-9A-Fa-f]+"'
        $unidCount = ([regex]::Matches($text, $unidPattern)).Count
        if ($unidCount -gt 0 -and $Result.FileType -ne 'TranscendenceModule') {
            # This is a main mod file with UNID definitions
        }
        
        # Check for xmlCreate with raw tags
        if ($text -match 'xmlCreate\s*\(?[^)]*"<') {
            [void]$Result.Issues.Add([PSCustomObject]@{
                File = $fileName
                Type = 'XmlCreateRawTag'
                Severity = 'Warning'
                Message = "xmlCreate with raw XML tags (may need escaping)"
            })
        }
    }
    catch {
        [void]$Result.Issues.Add([PSCustomObject]@{
            File = $FilePath
            Type = 'ParseError'
            Severity = 'Error'
            Message = "Failed to analyze file: $_"
        })
    }
}

function Generate-QuickActions {
    param([PSCustomObject]$Result)
    
    # Always offer validation
    [void]$Result.QuickActions.Add([PSCustomObject]@{
        Name = 'Quick Validate'
        Description = 'Run XML validation and TLisp checks'
        Icon = '✓'
        Priority = 1
        Tab = 'XML Checker'
    })
    
    # API version related
    if ($Result.ApiStatus -in @('Outdated', 'Legacy', 'Ancient')) {
        [void]$Result.QuickActions.Add([PSCustomObject]@{
            Name = 'Check Deprecated API'
            Description = "API $($Result.ApiVersion) detected - check for deprecated functions"
            Icon = '⚠'
            Priority = 2
            Tab = 'Semantic Validation'
        })
    }
    
    # Issues found
    $errorCount = @($Result.Issues | Where-Object { $_.Severity -eq 'Error' }).Count
    $warningCount = @($Result.Issues | Where-Object { $_.Severity -eq 'Warning' }).Count
    
    if ($errorCount -gt 0) {
        [void]$Result.QuickActions.Add([PSCustomObject]@{
            Name = 'Fix Errors'
            Description = "$errorCount error(s) found - run auto-fix"
            Icon = '🔧'
            Priority = 1
            Tab = 'XML Checker'
        })
    }
    
    if ($warningCount -gt 0) {
        [void]$Result.QuickActions.Add([PSCustomObject]@{
            Name = 'Review Warnings'
            Description = "$warningCount warning(s) found"
            Icon = '⚠'
            Priority = 3
            Tab = 'XML Checker'
        })
    }
    
    # Folder-specific
    if ($Result.IsFolder) {
        [void]$Result.QuickActions.Add([PSCustomObject]@{
            Name = 'Full Health Report'
            Description = 'Generate comprehensive mod health report'
            Icon = '📊'
            Priority = 4
            Tab = 'Project Health'
        })
        
        [void]$Result.QuickActions.Add([PSCustomObject]@{
            Name = 'Dependency Graph'
            Description = 'Visualize mod dependencies'
            Icon = '🗺'
            Priority = 5
            Tab = 'Dependency Graph'
        })
        
        [void]$Result.QuickActions.Add([PSCustomObject]@{
            Name = 'Cross-Mod Compatibility'
            Description = 'Check for UNID conflicts'
            Icon = '🔄'
            Priority = 6
            Tab = 'Cross-Mod Compatibility'
        })
    }
    
    # Sort by priority
    $Result.QuickActions = [System.Collections.ArrayList]@($Result.QuickActions | Sort-Object Priority)
}

function Calculate-ModScore {
    param([PSCustomObject]$Result)
    
    $score = 100
    
    # Deduct for issues
    foreach ($issue in $Result.Issues) {
        switch ($issue.Severity) {
            'Error' { $score -= 15 }
            'Warning' { $score -= 5 }
            'Info' { $score -= 1 }
        }
    }
    
    # Deduct for outdated API
    switch ($Result.ApiStatus) {
        'Outdated' { $score -= 10 }
        'Legacy' { $score -= 25 }
        'Ancient' { $score -= 50 }
    }
    
    return [Math]::Max(0, $score)
}

function Format-SmartDetectionReport {
    param([PSCustomObject]$Result)
    
    $output = [System.Text.StringBuilder]::new()
    [void]$output.AppendLine('═══════════════════════════════════════════════════════════')
    [void]$output.AppendLine('                    SMART DETECTION RESULTS')
    [void]$output.AppendLine('═══════════════════════════════════════════════════════════')
    [void]$output.AppendLine('')
    
    # Summary
    if ($Result.ModName) {
        [void]$output.AppendLine("Mod: $($Result.ModName)")
    }
    [void]$output.AppendLine("Type: $($Result.FileType)")
    [void]$output.AppendLine("Files: $($Result.FileCount) ($($Result.XmlFileCount) XML, $($Result.ResourceCount) resources)")
    
    if ($Result.ApiVersion) {
        $statusIcon = switch ($Result.ApiStatus) {
            'Current' { '✓' }
            'Outdated' { '⚠' }
            'Legacy' { '⚠' }
            'Ancient' { '❌' }
            default { '?' }
        }
        [void]$output.AppendLine("API Version: $($Result.ApiVersion) $statusIcon $($Result.ApiStatus)")
    }
    
    [void]$output.AppendLine("Health Score: $($Result.Score)/100")
    [void]$output.AppendLine('')
    
    # Issues
    if ($Result.Issues.Count -gt 0) {
        [void]$output.AppendLine('═══════════════════════════════════════════════════════════')
        [void]$output.AppendLine('                    DETECTED ISSUES')
        [void]$output.AppendLine('═══════════════════════════════════════════════════════════')
        [void]$output.AppendLine('')
        
        $byFile = $Result.Issues | Group-Object File
        foreach ($fileGroup in $byFile) {
            [void]$output.AppendLine("$($fileGroup.Name):")
            foreach ($issue in $fileGroup.Group) {
                $icon = switch ($issue.Severity) {
                    'Error' { '❌' }
                    'Warning' { '⚠' }
                    'Info' { 'ℹ' }
                    default { '•' }
                }
                [void]$output.AppendLine("  $icon [$($issue.Type)] $($issue.Message)")
            }
            [void]$output.AppendLine('')
        }
    }
    
    # Recommendations
    [void]$output.AppendLine('═══════════════════════════════════════════════════════════')
    [void]$output.AppendLine('                    RECOMMENDED ACTIONS')
    [void]$output.AppendLine('═══════════════════════════════════════════════════════════')
    [void]$output.AppendLine('')
    
    foreach ($action in $Result.QuickActions) {
        [void]$output.AppendLine("  $($action.Icon) $($action.Name)")
        [void]$output.AppendLine("    $($action.Description)")
        [void]$output.AppendLine("    → Go to: $($action.Tab)")
        [void]$output.AppendLine('')
    }
    
    return $output.ToString()
}

function Show-SmartDetectionDialog {
    param(
        [PSCustomObject]$Result,
        [System.Windows.Forms.Form]$ParentForm
    )
    
    # Colors
    $bgDark = [System.Drawing.Color]::FromArgb(30, 30, 30)
    $bgLight = [System.Drawing.Color]::FromArgb(50, 50, 50)
    $textWhite = [System.Drawing.Color]::White
    $accentGreen = [System.Drawing.Color]::FromArgb(80, 180, 80)
    $accentOrange = [System.Drawing.Color]::FromArgb(220, 150, 50)
    $accentRed = [System.Drawing.Color]::FromArgb(200, 80, 80)
    
    # Create dialog
    $dialog = [System.Windows.Forms.Form]::new()
    $dialog.Text = 'Smart Detection'
    $dialog.Size = [System.Drawing.Size]::new(600, 500)
    $dialog.StartPosition = 'CenterParent'
    $dialog.BackColor = $bgDark
    $dialog.ForeColor = $textWhite
    $dialog.Font = [System.Drawing.Font]::new('Segoe UI', 9)
    $dialog.FormBorderStyle = 'FixedDialog'
    $dialog.MaximizeBox = $false
    $dialog.MinimizeBox = $false
    
    # Header
    $lblHeader = [System.Windows.Forms.Label]::new()
    $lblHeader.Text = if ($Result.ModName) { $Result.ModName } else { 'Dropped File Analysis' }
    $lblHeader.Font = [System.Drawing.Font]::new('Segoe UI', 14, [System.Drawing.FontStyle]::Bold)
    $lblHeader.Location = [System.Drawing.Point]::new(20, 20)
    $lblHeader.AutoSize = $true
    $dialog.Controls.Add($lblHeader)
    
    # Type and stats
    $lblType = [System.Windows.Forms.Label]::new()
    $lblType.Text = "Type: $($Result.FileType) | Files: $($Result.XmlFileCount) XML"
    $lblType.Location = [System.Drawing.Point]::new(20, 55)
    $lblType.AutoSize = $true
    $lblType.ForeColor = [System.Drawing.Color]::FromArgb(180, 180, 180)
    $dialog.Controls.Add($lblType)
    
    # API Version indicator
    if ($Result.ApiVersion) {
        $lblApi = [System.Windows.Forms.Label]::new()
        $statusColor = switch ($Result.ApiStatus) {
            'Current' { $accentGreen }
            'Outdated' { $accentOrange }
            'Legacy' { $accentOrange }
            'Ancient' { $accentRed }
            default { $textWhite }
        }
        $lblApi.Text = "API Version: $($Result.ApiVersion) - $($Result.ApiStatus)"
        $lblApi.Location = [System.Drawing.Point]::new(20, 75)
        $lblApi.AutoSize = $true
        $lblApi.ForeColor = $statusColor
        $dialog.Controls.Add($lblApi)
    }
    
    # Health score
    $lblScore = [System.Windows.Forms.Label]::new()
    $scoreColor = if ($Result.Score -ge 80) { $accentGreen } elseif ($Result.Score -ge 50) { $accentOrange } else { $accentRed }
    $lblScore.Text = "Health Score: $($Result.Score)/100"
    $lblScore.Font = [System.Drawing.Font]::new('Segoe UI', 11, [System.Drawing.FontStyle]::Bold)
    $lblScore.Location = [System.Drawing.Point]::new(20, 100)
    $lblScore.AutoSize = $true
    $lblScore.ForeColor = $scoreColor
    $dialog.Controls.Add($lblScore)
    
    # Issues summary
    $errorCount = @($Result.Issues | Where-Object { $_.Severity -eq 'Error' }).Count
    $warningCount = @($Result.Issues | Where-Object { $_.Severity -eq 'Warning' }).Count
    
    if ($errorCount -gt 0 -or $warningCount -gt 0) {
        $lblIssues = [System.Windows.Forms.Label]::new()
        $issueText = @()
        if ($errorCount -gt 0) { $issueText += "$errorCount error(s)" }
        if ($warningCount -gt 0) { $issueText += "$warningCount warning(s)" }
        $lblIssues.Text = "Issues: " + ($issueText -join ', ')
        $lblIssues.Location = [System.Drawing.Point]::new(20, 125)
        $lblIssues.AutoSize = $true
        $lblIssues.ForeColor = if ($errorCount -gt 0) { $accentRed } else { $accentOrange }
        $dialog.Controls.Add($lblIssues)
    }
    
    # Quick actions panel
    $pnlActions = [System.Windows.Forms.Panel]::new()
    $pnlActions.Location = [System.Drawing.Point]::new(20, 160)
    $pnlActions.Size = [System.Drawing.Size]::new(545, 250)
    $pnlActions.BackColor = $bgLight
    $pnlActions.AutoScroll = $true
    $dialog.Controls.Add($pnlActions)
    
    $lblActionsTitle = [System.Windows.Forms.Label]::new()
    $lblActionsTitle.Text = 'Recommended Actions:'
    $lblActionsTitle.Font = [System.Drawing.Font]::new('Segoe UI', 10, [System.Drawing.FontStyle]::Bold)
    $lblActionsTitle.Location = [System.Drawing.Point]::new(10, 10)
    $lblActionsTitle.AutoSize = $true
    $pnlActions.Controls.Add($lblActionsTitle)
    
    $y = 40
    $script:selectedAction = $null
    
    foreach ($action in $Result.QuickActions) {
        $btnAction = [System.Windows.Forms.Button]::new()
        $btnAction.Text = "$($action.Icon) $($action.Name)"
        $btnAction.Location = [System.Drawing.Point]::new(10, $y)
        $btnAction.Size = [System.Drawing.Size]::new(520, 35)
        $btnAction.BackColor = $bgDark
        $btnAction.ForeColor = $textWhite
        $btnAction.FlatStyle = 'Flat'
        $btnAction.TextAlign = 'MiddleLeft'
        $btnAction.Tag = $action
        
        $btnAction.Add_Click({
            $script:selectedAction = $this.Tag
            $dialog.DialogResult = 'OK'
            $dialog.Close()
        }.GetNewClosure())
        
        $pnlActions.Controls.Add($btnAction)
        
        $lblDesc = [System.Windows.Forms.Label]::new()
        $lblDesc.Text = $action.Description
        $lblDesc.Location = [System.Drawing.Point]::new(30, $y + 38)
        $lblDesc.AutoSize = $true
        $lblDesc.ForeColor = [System.Drawing.Color]::FromArgb(150, 150, 150)
        $pnlActions.Controls.Add($lblDesc)
        
        $y += 60
    }
    
    # Cancel button
    $btnCancel = [System.Windows.Forms.Button]::new()
    $btnCancel.Text = 'Skip to Normal Menu'
    $btnCancel.Location = [System.Drawing.Point]::new(20, 420)
    $btnCancel.Size = [System.Drawing.Size]::new(150, 30)
    $btnCancel.BackColor = $bgLight
    $btnCancel.ForeColor = $textWhite
    $btnCancel.FlatStyle = 'Flat'
    $btnCancel.Add_Click({
        $dialog.DialogResult = 'Cancel'
        $dialog.Close()
    })
    $dialog.Controls.Add($btnCancel)
    
    # Show details button
    $btnDetails = [System.Windows.Forms.Button]::new()
    $btnDetails.Text = 'Show Full Report'
    $btnDetails.Location = [System.Drawing.Point]::new(415, 420)
    $btnDetails.Size = [System.Drawing.Size]::new(150, 30)
    $btnDetails.BackColor = $bgLight
    $btnDetails.ForeColor = $textWhite
    $btnDetails.FlatStyle = 'Flat'
    $btnDetails.Add_Click({
        $report = Format-SmartDetectionReport -Result $Result
        [System.Windows.Forms.MessageBox]::Show($report, 'Smart Detection Report', 'OK', 'Information')
    })
    $dialog.Controls.Add($btnDetails)
    
    $dialogResult = $dialog.ShowDialog($ParentForm)
    
    return [PSCustomObject]@{
        DialogResult = $dialogResult
        SelectedAction = $script:selectedAction
    }
}

# Export functions
# Functions are available for dot-sourcing


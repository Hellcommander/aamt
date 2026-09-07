<#
.SYNOPSIS
  Advanced Transcendence Mod Tools - Enhanced Features Module
  
.DESCRIPTION
  Advanced features for Transcendence mod development:
  - XML Structure Validator
  - TLisp Expression Checker
  - UNID Reference Checker
  - Multi-file Project Support
  - Auto-fix Suggestions
  - Documentation Lookup
#>

# ============================================================
# XML STRUCTURE VALIDATOR
# ============================================================

function Get-XmlStructureIssues {
    param([string]$FilePath)
    
    $issues = [System.Collections.ArrayList]::new()
    $text = [System.IO.File]::ReadAllText($FilePath, [System.Text.Encoding]::UTF8)
    $lines = $text -split "`n"
    
    # Tag stack for matching
    $tagStack = [System.Collections.Stack]::new()
    $lineNum = 0
    $inComment = $false
    $inCData = $false
    $inDoctype = $false
    $doctypeBracket = 0
    
    # Track seen attributes per element
    $elementAttrs = @{}
    $currentElement = $null
    $currentElementLine = 0
    
    foreach ($line in $lines) {
        $lineNum++
        $remaining = $line
        
        # Track comments
        if ($remaining.Contains('<!--')) {
            $inComment = $true
        }
        if ($remaining.Contains('-->')) {
            $inComment = $false
        }
        if ($remaining.Contains('<![CDATA[')) {
            $inCData = $true
        }
        if ($remaining.Contains(']]>')) {
            $inCData = $false
        }
        if ($remaining.ToUpper().Contains('<!DOCTYPE')) {
            $inDoctype = $true
        }
        if ($inDoctype) {
            if ($remaining.Contains('[')) { $doctypeBracket++ }
            if ($remaining.Contains(']')) { $doctypeBracket-- }
            if ($remaining.Contains('>') -and $doctypeBracket -eq 0) { $inDoctype = $false }
        }
        
        if ($inComment -or $inCData -or $inDoctype) { continue }
        
        # Find opening tags
        $openTagPattern = '<([a-zA-Z_][a-zA-Z0-9_:]*)([^>]*)>'
        $openMatches = [regex]::Matches($line, $openTagPattern)
        foreach ($m in $openMatches) {
            $tagName = $m.Groups[1].Value
            $attrs = $m.Groups[2].Value
            
            # Skip self-closing tags
            if ($attrs.TrimEnd().EndsWith('/')) { continue }
            
            # Check for duplicate attributes
            $attrPattern = '(\w+)\s*='
            $attrMatches = [regex]::Matches($attrs, $attrPattern)
            $seenAttrs = @{}
            foreach ($attrMatch in $attrMatches) {
                $attrName = $attrMatch.Groups[1].Value
                if ($seenAttrs.ContainsKey($attrName)) {
                    [void]$issues.Add([PSCustomObject]@{
                        File = $FilePath
                        Line = $lineNum
                        Code = 'DUPLICATE_ATTRIBUTE'
                        Severity = 'Error'
                        Message = "Duplicate attribute '$attrName' in <$tagName>"
                        CanFix = $false
                    })
                }
                else {
                    $seenAttrs[$attrName] = $true
                }
            }
            
            # Push to stack
            $tagStack.Push([PSCustomObject]@{ Name = $tagName; Line = $lineNum })
        }
        
        # Find closing tags
        $closeTagPattern = '</([a-zA-Z_][a-zA-Z0-9_:]*)>'
        $closeMatches = [regex]::Matches($line, $closeTagPattern)
        foreach ($m in $closeMatches) {
            $closeName = $m.Groups[1].Value
            
            if ($tagStack.Count -eq 0) {
                [void]$issues.Add([PSCustomObject]@{
                    File = $FilePath
                    Line = $lineNum
                    Code = 'UNEXPECTED_CLOSE_TAG'
                    Severity = 'Error'
                    Message = "Unexpected closing tag </$closeName> with no matching open tag"
                    CanFix = $false
                })
            }
            else {
                $top = $tagStack.Pop()
                if ($top.Name -ne $closeName) {
                    [void]$issues.Add([PSCustomObject]@{
                        File = $FilePath
                        Line = $lineNum
                        Code = 'TAG_MISMATCH'
                        Severity = 'Error'
                        Message = "Closing tag </$closeName> does not match open <$($top.Name)> from line $($top.Line)"
                        CanFix = $false
                    })
                    # Put it back
                    $tagStack.Push($top)
                }
            }
        }
    }
    
    # Check for unclosed tags
    while ($tagStack.Count -gt 0) {
        $top = $tagStack.Pop()
        [void]$issues.Add([PSCustomObject]@{
            File = $FilePath
            Line = $top.Line
            Code = 'UNCLOSED_TAG'
            Severity = 'Error'
            Message = "Unclosed tag <$($top.Name)>"
            CanFix = $false
        })
    }
    
    return $issues
}

# ============================================================
# TLISP EXPRESSION CHECKER
# ============================================================

function Get-TlispExpressionIssues {
    param([string]$FilePath)
    
    $issues = [System.Collections.ArrayList]::new()
    $text = [System.IO.File]::ReadAllText($FilePath, [System.Text.Encoding]::UTF8)
    $lines = $text -split "`n"
    
    # Find TLisp code blocks (Events, OnCreate, etc.)
    $inTlispBlock = $false
    $blockStartLine = 0
    $blockName = ''
    $lineNum = 0
    $parenStack = [System.Collections.Stack]::new()
    
    foreach ($line in $lines) {
        $lineNum++
        
        # Detect TLisp blocks
        if ($line -match '<(Events|On\w+|Globals|Script)') {
            $inTlispBlock = $true
            $blockStartLine = $lineNum
            $blockName = $matches[1]
            $parenStack.Clear()
            continue
        }
        
        if ($inTlispBlock) {
            if ($line -match '</(Events|On\w+|Globals|Script)') {
                # Check for unbalanced parentheses
                if ($parenStack.Count -gt 0) {
                    [void]$issues.Add([PSCustomObject]@{
                        File = $FilePath
                        Line = $blockStartLine
                        Code = 'TLISP_UNBALANCED_PARENS'
                        Severity = 'Error'
                        Message = "Unbalanced parentheses in <$blockName> block. $($parenStack.Count) unclosed '('"
                        CanFix = $false
                    })
                }
                $inTlispBlock = $false
                continue
            }
            
            # Count parentheses (simple approach)
            $openCount = ([regex]::Matches($line, '\(')).Count
            $closeCount = ([regex]::Matches($line, '\)')).Count
            
            for ($i = 0; $i -lt $openCount; $i++) {
                $parenStack.Push($lineNum)
            }
            for ($i = 0; $i -lt $closeCount; $i++) {
                if ($parenStack.Count -gt 0) {
                    $parenStack.Pop() | Out-Null
                }
                else {
                    [void]$issues.Add([PSCustomObject]@{
                        File = $FilePath
                        Line = $lineNum
                        Code = 'TLISP_EXTRA_CLOSE_PAREN'
                        Severity = 'Error'
                        Message = "Extra closing parenthesis ')' in <$blockName> block"
                        CanFix = $false
                    })
                }
            }
            
            # Check for suspicious constructs
            if ($line -match '\(@\s+(\w+)' -and $line -notmatch '\(@\s+\w+\s+') {
                [void]$issues.Add([PSCustomObject]@{
                    File = $FilePath
                    Line = $lineNum
                    Code = 'TLISP_SUSPICIOUS_AT'
                    Severity = 'Warning'
                    Message = "Suspicious (@ var) construct - may be missing arguments"
                    CanFix = $false
                })
            }
        }
    }
    
    return $issues
}

# ============================================================
# UNID REFERENCE CHECKER
# ============================================================

function Get-UnidReferenceIssues {
    param([string]$FilePath, [hashtable]$AllUnids = @{})
    
    $issues = [System.Collections.ArrayList]::new()
    $text = [System.IO.File]::ReadAllText($FilePath, [System.Text.Encoding]::UTF8)
    $lines = $text -split "`n"
    
    # Extract declared entities from DOCTYPE (to determine if entity causes parsing failure)
    $declaredEntities = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
    $doctypeMatch = [regex]::Match($text, '<!DOCTYPE\s+\w+\s*\[(.*?)\]>', [System.Text.RegularExpressions.RegexOptions]::Singleline)
    if ($doctypeMatch.Success) {
        $doctypeContent = $doctypeMatch.Groups[1].Value
        $entityDeclPattern = '<!ENTITY\s+(\w+)\s+["'']([^"'']+)["'']\s*>'
        $entityDeclMatches = [regex]::Matches($doctypeContent, $entityDeclPattern)
        foreach ($match in $entityDeclMatches) {
            $entityName = $match.Groups[1].Value
            [void]$declaredEntities.Add($entityName)
        }
    }
    
    # Extract UNID definitions from this file
    $unidDefs = @{}
    $unidDefPattern = '<!ENTITY\s+(\w+)\s+"(0x[0-9A-Fa-f]+)"'
    $matches = [regex]::Matches($text, $unidDefPattern, 'IgnoreCase')
    foreach ($m in $matches) {
        $entityName = $m.Groups[1].Value
        $unidValue = $m.Groups[2].Value
        
        # Check for duplicate UNID (with priority awareness)
        if ($AllUnids.ContainsKey($unidValue)) {
            $existing = $AllUnids[$unidValue]
            
            # Determine current UNID's range-based priority
            # Reference: https://wiki.kronosaur.com/doku.php/modding/unid_database
            function Get-UnidRangePriority {
                param([string]$UnidValue)
                $unidStr = $UnidValue -replace '^0x', ''
                try {
                    $unidInt = [Convert]::ToUInt32($unidStr, 16)
                    $high16 = ($unidInt -shr 16) -band 0xFFFF
                    if ($high16 -ge 0x0000 -and $high16 -le 0x9FFF) { return 1 }  # Game/DLC
                    if ($high16 -ge 0xF000 -and $high16 -le 0xFFFF) { return 2 }  # Dynamic
                    if ($high16 -ge 0xA000 -and $high16 -le 0xCFFF) { return 3 }  # Registered Extensions
                    if ($high16 -ge 0xD000 -and $high16 -le 0xEFFF) { return 4 }  # User UNIDs
                } catch { }
                return 5  # Unknown/Extensions - lowest priority
            }
            
            function Get-UnidRangeDescription {
                param([string]$UnidValue)
                $priority = Get-UnidRangePriority -UnidValue $UnidValue
                switch ($priority) {
                    1 { return "Game/DLC (0x0000-0x9FFF)" }
                    2 { return "Dynamic UNID (0xF000-0xFFFF)" }
                    3 { return "Registered Extension (0xA000-0xCFFF)" }
                    4 { return "User UNID (0xD000-0xEFFF)" }
                    default { return "Unknown Range" }
                }
            }
            
            $currentRangePriority = Get-UnidRangePriority -UnidValue $unidValue
            $currentRangeDesc = Get-UnidRangeDescription -UnidValue $unidValue
            $conflictDetected = $false
            $prioritySource = $null
            
            # Handle both single object and array of conflicts
            if ($existing -is [PSCustomObject]) {
                $prioritySource = $existing
                $existingPriority = if ($existing.Priority) { $existing.Priority } else { 5 }
                if ($existingPriority -lt $currentRangePriority) {
                    $conflictDetected = $true
                }
            }
            elseif ($existing -is [Array]) {
                # Find highest priority source
                $prioritySource = $existing | Sort-Object { if ($_.Priority) { $_.Priority } else { 5 } } | Select-Object -First 1
                $existingPriority = if ($prioritySource.Priority) { $prioritySource.Priority } else { 5 }
                if ($existingPriority -lt $currentRangePriority) {
                    $conflictDetected = $true
                }
            }
            else {
                # Legacy string format (fallback)
                $conflictDetected = $true
                $prioritySource = [PSCustomObject]@{ File = $existing; Priority = 5; Source = 'Unknown'; Range = 'Unknown' }
            }
            
            if ($conflictDetected) {
                $existingRange = if ($prioritySource.Range) { " ($($prioritySource.Range))" } else { "" }
                $sourceDesc = if ($prioritySource.Source) { "$($prioritySource.Source)$existingRange" } else { $prioritySource.File }
                $wikiRef = "Reference: https://wiki.kronosaur.com/doku.php/modding/unid_database"
                [void]$issues.Add([PSCustomObject]@{
                    File = $FilePath
                    Line = 0
                    Code = 'UNID_DUPLICATE'
                    Severity = 'Error'
                    Message = "UNID $unidValue ($currentRangeDesc) conflicts with higher-priority source: $sourceDesc. $wikiRef"
                    CanFix = $false
                })
            }
        }
        else {
            # Determine range-based priority for this UNID
            function Get-UnidRangePriority {
                param([string]$UnidValue)
                $unidStr = $UnidValue -replace '^0x', ''
                try {
                    $unidInt = [Convert]::ToUInt32($unidStr, 16)
                    $high16 = ($unidInt -shr 16) -band 0xFFFF
                    if ($high16 -ge 0x0000 -and $high16 -le 0x9FFF) { return 1 }
                    if ($high16 -ge 0xF000 -and $high16 -le 0xFFFF) { return 2 }
                    if ($high16 -ge 0xA000 -and $high16 -le 0xCFFF) { return 3 }
                    if ($high16 -ge 0xD000 -and $high16 -le 0xEFFF) { return 4 }
                } catch { }
                return 5
            }
            
            function Get-UnidRangeDescription {
                param([string]$UnidValue)
                $priority = Get-UnidRangePriority -UnidValue $UnidValue
                switch ($priority) {
                    1 { return "Game/DLC (0x0000-0x9FFF)" }
                    2 { return "Dynamic UNID (0xF000-0xFFFF)" }
                    3 { return "Registered Extension (0xA000-0xCFFF)" }
                    4 { return "User UNID (0xD000-0xEFFF)" }
                    default { return "Unknown Range" }
                }
            }
            
            $rangePriority = Get-UnidRangePriority -UnidValue $unidValue
            $rangeDesc = Get-UnidRangeDescription -UnidValue $unidValue
            
            # Add to registry with range-based priority
            $AllUnids[$unidValue] = [PSCustomObject]@{
                File = $FilePath
                Priority = $rangePriority
                Source = 'Extensions'
                Range = $rangeDesc
                UnidValue = $unidValue
            }
        }
        
        $unidDefs[$entityName] = $unidValue
    }
    
    # Extract UNID attribute definitions
    $unidAttrPattern = 'UNID\s*=\s*"([^"]+)"'
    $attrMatches = [regex]::Matches($text, $unidAttrPattern, 'IgnoreCase')
    foreach ($m in $attrMatches) {
        $unidRef = $m.Groups[1].Value
        $before = $text.Substring(0, $m.Index)
        $lineNum = ($before -split "`n").Count
        
        # Check if it's an entity reference
        if ($unidRef.StartsWith('&') -and $unidRef.EndsWith(';')) {
            $entityName = $unidRef.Substring(1, $unidRef.Length - 2)
            if (-not $unidDefs.ContainsKey($entityName)) {
                [void]$issues.Add([PSCustomObject]@{
                    File = $FilePath
                    Line = $lineNum
                    Code = 'UNID_ENTITY_UNDEFINED'
                    Severity = 'Error'
                    Message = "UNID entity '&$entityName;' is not defined"
                    CanFix = $false
                })
            }
        }
        # Check if it's a direct UNID value
        elseif ($unidRef -match '^0x[0-9A-Fa-f]{8}$') {
            # Valid format
        }
        else {
            [void]$issues.Add([PSCustomObject]@{
                File = $FilePath
                Line = $lineNum
                Code = 'UNID_INVALID_FORMAT'
                Severity = 'Warning'
                Message = "UNID format may be invalid: $unidRef (expected 0x followed by 8 hex digits or entity reference)"
                CanFix = $false
            })
        }
    }
    
    # Check for entity references in general
    $entityRefPattern = '&(\w+);'
    $entityMatches = [regex]::Matches($text, $entityRefPattern)
    foreach ($m in $entityMatches) {
        $entityName = $m.Groups[1].Value
        $before = $text.Substring(0, $m.Index)
        $lineNum = ($before -split "`n").Count
        
        # Built-in XML entities are always valid.
        if ($entityName -in @('amp', 'lt', 'gt', 'quot', 'apos')) { continue }
        
        # Skip if it's in a comment or DOCTYPE
        $line = $lines[$lineNum - 1]
        if ($line -match '<!--' -or $line -match '<!ENTITY' -or $line -match '<!DOCTYPE') { continue }
        
        if (-not $unidDefs.ContainsKey($entityName)) {
            # If entity is not declared in DOCTYPE, it causes XML parsing failure - report as Error
            # If entity is declared in DOCTYPE but not in local UNID definitions, it may be from base game - report as Warning
            $isDeclaredInDoctype = $declaredEntities.Contains($entityName)
            
            if (-not $isDeclaredInDoctype) {
                # Entity not in DOCTYPE - causes parsing failure
                [void]$issues.Add([PSCustomObject]@{
                    File = $FilePath
                    Line = $lineNum
                    Code = 'ENTITY_UNDECLARED'
                    Severity = 'Error'
                    Message = "Entity '&$entityName;' is not declared in DOCTYPE (causes XML parsing failure)"
                    CanFix = $false
                    IsCascadingCause = $true
                })
            }
            else {
                # Entity is in DOCTYPE but not in local UNID definitions - may be from base game or another mod
                [void]$issues.Add([PSCustomObject]@{
                    File = $FilePath
                    Line = $lineNum
                    Code = 'ENTITY_UNDEFINED'
                    Severity = 'Warning'
                    Message = "Entity '&$entityName;' is declared in DOCTYPE but not found in local UNID definitions (may be from base game or another mod)"
                    CanFix = $false
                })
            }
        }
    }
    
    return $issues
}

# ============================================================
# MULTI-FILE PROJECT SCANNER
# ============================================================

function Get-ProjectFiles {
    param([string]$ProjectPath)
    
    $files = @()
    
    if (Test-Path $ProjectPath -PathType Leaf) {
        if ($ProjectPath.EndsWith('.xml')) {
            return @($ProjectPath)
        }
    }
    else {
        $files = @(Get-ChildItem -LiteralPath $ProjectPath -Filter '*.xml' -Recurse | ForEach-Object { $_.FullName })
    }
    
    return $files
}

function Get-DeprecatedAttributeIssues {
    param([string]$FilePath)
    
    $issues = [System.Collections.ArrayList]::new()
    $text = [System.IO.File]::ReadAllText($FilePath, [System.Text.Encoding]::UTF8)
    $lines = $text -split "`n"
    
    # Deprecated attributes in API 57
    $deprecatedAttrs = @{
        'obsoleteVersion' = 'Consider using size-based types instead'
        'apiVersion' = @{
            pattern = 'apiVersion\s*=\s*"5[0-6]"'
            message = 'Consider updating to apiVersion="57"'
        }
    }
    
    $lineNum = 0
    foreach ($line in $lines) {
        $lineNum++
        
        # Check for old API versions
        if ($line -match 'apiVersion\s*=\s*"5[0-6]"') {
            [void]$issues.Add([PSCustomObject]@{
                File = $FilePath
                Line = $lineNum
                Code = 'DEPRECATED_API_VERSION'
                Severity = 'Warning'
                Message = 'Using API version 50-56. Consider updating to API 57'
                CanFix = $false
            })
        }
    }
    
    return $issues
}

function Get-IndentationIssues {
    param([string]$FilePath)
    
    $issues = [System.Collections.ArrayList]::new()
    $text = [System.IO.File]::ReadAllText($FilePath, [System.Text.Encoding]::UTF8)
    $lines = $text -split "`n"
    
    $hasTabs = $false
    $hasSpaces = $false
    $inconsistentLines = @()
    
    foreach ($line in $lines) {
        if ([string]::IsNullOrWhiteSpace($line)) { continue }
        if ($line.TrimStart().StartsWith('<!--')) { continue }
        if ($line.TrimStart().StartsWith('<?')) { continue }
        
        $leading = $line -replace '^(\s*).*$', '$1'
        if ($leading.Length -gt 0) {
            if ($leading.Contains("`t")) { $hasTabs = $true }
            if ($leading -match '^ +$') { $hasSpaces = $true }
            
            # Check for mixed tabs and spaces
            if ($leading -match "`t" -and $leading -match ' ') {
                $inconsistentLines += $line
            }
        }
    }
    
    # If both tabs and spaces are used, it's inconsistent
    if ($hasTabs -and $hasSpaces) {
        [void]$issues.Add([PSCustomObject]@{
            File = $FilePath
            Line = 0
            Code = 'INCONSISTENT_INDENTATION'
            Severity = 'Warning'
            Message = 'File uses both tabs and spaces for indentation'
            CanFix = $false
        })
    }
    
    return $issues
}

function Get-UnusedUnids {
    param([string[]]$Files)
    
    $unidDefs = @{}  # UNID -> (EntityName, File)
    $unidRefs = @{}   # UNID -> count of references
    
    # First pass: collect all UNID definitions
    foreach ($file in $Files) {
        $text = [System.IO.File]::ReadAllText($file, [System.Text.Encoding]::UTF8)
        $pattern = '<!ENTITY\s+(\w+)\s+"(0x[0-9A-Fa-f]+)"'
        $matches = [regex]::Matches($text, $pattern, 'IgnoreCase')
        
        foreach ($m in $matches) {
            $entityName = $m.Groups[1].Value
            $unidValue = $m.Groups[2].Value
            $unidDefs[$unidValue] = @{
                Entity = $entityName
                File = $file
            }
            $unidRefs[$unidValue] = 0
        }
    }
    
    # Second pass: count references
    foreach ($file in $Files) {
        $text = [System.IO.File]::ReadAllText($file, [System.Text.Encoding]::UTF8)
        
        # Find entity references
        $refPattern = '&(\w+);'
        $refMatches = [regex]::Matches($text, $refPattern)
        
        foreach ($m in $refMatches) {
            $entityName = $m.Groups[1].Value
            
            # Find which UNID this entity maps to
            foreach ($unid in $unidDefs.Keys) {
                if ($unidDefs[$unid].Entity -eq $entityName) {
                    $unidRefs[$unid]++
                    break
                }
            }
        }
    }
    
    # Find unused UNIDs
    $unused = @()
    foreach ($unid in $unidDefs.Keys) {
        if ($unidRefs[$unid] -eq 0) {
            $unused += [PSCustomObject]@{
                UNID = $unid
                Entity = $unidDefs[$unid].Entity
                File = $unidDefs[$unid].File
            }
        }
    }
    
    return $unused
}

function Get-ProjectHealthReport {
    param([string[]]$Files, [scriptblock]$GetXmlIssuesFunc)
    
    $report = [PSCustomObject]@{
        TotalFiles = $Files.Count
        FilesWithErrors = 0
        FilesWithWarnings = 0
        XmlErrors = 0
        MissingResources = 0
        UnusedUnids = 0
        DeprecatedAttributes = 0
        InconsistentIndentation = 0
        UnidDuplicates = 0
        TotalErrors = 0
        TotalWarnings = 0
        FileStatus = @{}
    }
    
    $allUnids = @{}
    $allIssues = @()
    $filesWithIndentIssues = @()
    
    foreach ($file in $Files) {
        $fileIssues = @()
        
        # Use the main Get-XmlIssues function if provided
        if ($GetXmlIssuesFunc) {
            $fileIssues += & $GetXmlIssuesFunc -FilePath $file
        }
        
        $fileIssues += Get-XmlStructureIssues -FilePath $file
        $fileIssues += Get-TlispExpressionIssues -FilePath $file
        $fileIssues += Get-UnidReferenceIssues -FilePath $file -AllUnids $allUnids
        $fileIssues += Get-ResourcePathIssues -FilePath $file
        $fileIssues += Get-DeprecatedAttributeIssues -FilePath $file
        
        $indentIssues = Get-IndentationIssues -FilePath $file
        if ($indentIssues.Count -gt 0) {
            $filesWithIndentIssues += $file
            $fileIssues += $indentIssues
        }
        
        $errors = @($fileIssues | Where-Object { $_.Severity -eq 'Error' })
        $warnings = @($fileIssues | Where-Object { $_.Severity -eq 'Warning' })
        
        if ($errors.Count -gt 0) { $report.FilesWithErrors++ }
        if ($warnings.Count -gt 0) { $report.FilesWithWarnings++ }
        
        $report.TotalErrors += $errors.Count
        $report.TotalWarnings += $warnings.Count
        
        # Count specific issue types
        $report.XmlErrors += @($fileIssues | Where-Object { 
            $_.Code -match 'XML_|TAG_|UNCLOSED|MISMATCH' 
        }).Count
        
        $report.FileStatus[$file] = [PSCustomObject]@{
            Errors = $errors.Count
            Warnings = $warnings.Count
            Issues = $fileIssues
        }
        
        $allIssues += $fileIssues
    }
    
    # Count specific metrics
    $report.MissingResources = @($allIssues | Where-Object { $_.Code -eq 'MISSING_RESOURCE' }).Count
    $report.DeprecatedAttributes = @($allIssues | Where-Object { $_.Code -eq 'DEPRECATED_API_VERSION' }).Count
    $report.UnidDuplicates = @($allIssues | Where-Object { $_.Code -eq 'UNID_DUPLICATE' }).Count
    $report.InconsistentIndentation = $filesWithIndentIssues.Count
    
    # Find unused UNIDs
    $unusedUnids = Get-UnusedUnids -Files $Files
    $report.UnusedUnids = $unusedUnids.Count
    
    return $report
}

# ============================================================
# DOCUMENTATION LOOKUP
# ============================================================

$script:ElementDocs = @{
    'TranscendenceExtension' = @{
        Description = 'Root element for Transcendence extensions'
        Attributes = @('UNID', 'apiVersion', 'version', 'name', 'release')
        Children = @('Modules', 'Library', 'Type', 'ItemType', 'ShipClass', 'StationType')
        Example = '<TranscendenceExtension UNID="&unidExtension;" apiVersion="57" version="1.0" name="My Mod">'
    }
    'TranscendenceLibrary' = @{
        Description = 'Root element for Transcendence libraries'
        Attributes = @('UNID', 'apiVersion', 'version', 'name')
        Children = @('Modules', 'Library', 'Type', 'ItemType', 'ShipClass', 'StationType')
        Example = '<TranscendenceLibrary UNID="&unidLibrary;" apiVersion="57">'
    }
    'TranscendenceModule' = @{
        Description = 'Root element for Transcendence modules'
        Attributes = @('UNID', 'apiVersion', 'version', 'name')
        Children = @('Type', 'ItemType', 'ShipClass', 'StationType')
        Example = '<TranscendenceModule UNID="&unidModule;" apiVersion="57">'
    }
    'ItemType' = @{
        Description = 'Defines an item (weapon, armor, device, etc.)'
        Attributes = @('UNID', 'name', 'level', 'value', 'mass', 'frequency', 'modifiers')
        Children = @('Language', 'Image', 'Type', 'Properties', 'Weapon', 'Armor', 'Device', 'Events')
        Example = '<ItemType UNID="&itMyWeapon;" name="My Weapon" level="5">'
    }
    'ShipClass' = @{
        Description = 'Defines a ship class'
        Attributes = @('UNID', 'name', 'class', 'manufacturer', 'level', 'score', 'mass')
        Children = @('Language', 'Image', 'Type', 'Properties', 'Armor', 'Devices', 'Items', 'AI', 'Events')
        Example = '<ShipClass UNID="&scMyShip;" name="My Ship" class="fighter" level="5">'
    }
    'StationType' = @{
        Description = 'Defines a station type'
        Attributes = @('UNID', 'name', 'sovereign', 'level', 'systemName', 'backgroundID')
        Children = @('Language', 'Image', 'Type', 'Properties', 'DockingPorts', 'Trade', 'Encounters', 'Events')
        Example = '<StationType UNID="&stMyStation;" name="My Station" level="5">'
    }
    'Events' = @{
        Description = 'Container for event handlers'
        Attributes = @()
        Children = @('OnCreate', 'OnDestroy', 'OnFireWeapon', 'OnDamage', 'OnUpdate', 'OnObjDestroyed')
        Example = '<Events><OnCreate>...</OnCreate></Events>'
    }
    'OnCreate' = @{
        Description = 'Event handler called when object is created'
        Attributes = @()
        Children = @('TLisp code block')
        Example = '<OnCreate>(block Nil (objSetData gSource ''myData true))</OnCreate>'
    }
    'OnFireWeapon' = @{
        Description = 'Event handler called when weapon fires'
        Attributes = @()
        Children = @('TLisp code block')
        Example = '<OnFireWeapon>(block Nil ...)</OnFireWeapon>'
    }
    'Device' = @{
        Description = 'Self-closing tag for device slot'
        Attributes = @('deviceID', 'item', 'chance', 'damaged', 'installed')
        Children = @('None - self-closing')
        Example = '<Device deviceID="primaryWeapon" item="&itLaserCannon;"/>'
    }
    'Module' = @{
        Description = 'References another XML module file'
        Attributes = @('filename')
        Children = @('None - self-closing')
        Example = '<Module filename="MyModule.xml"/>'
    }
}

function Get-ElementDocumentation {
    param([string]$ElementName)
    
    if ($script:ElementDocs.ContainsKey($ElementName)) {
        return $script:ElementDocs[$ElementName]
    }
    
    return $null
}

# ============================================================
# RESOURCE PATH VALIDATOR
# ============================================================

function Get-ResourcePathIssues {
    param([string]$FilePath)
    
    $issues = [System.Collections.ArrayList]::new()
    $text = [System.IO.File]::ReadAllText($FilePath, [System.Text.Encoding]::UTF8)
    $fileDir = [System.IO.Path]::GetDirectoryName($FilePath)
    $lines = $text -split "`n"
    
    # Find Image elements with bitmap/bitmask attributes
    $imagePattern = '<Image[^>]+(?:bitmap|bitmask)\s*=\s*"([^"]+)"'
    $imageMatches = [regex]::Matches($text, $imagePattern, 'IgnoreCase')
    
    foreach ($m in $imageMatches) {
        $resourcePath = $m.Groups[1].Value
        $before = $text.Substring(0, $m.Index)
        $lineNum = ($before -split "`n").Count
        
        # Resolve relative paths
        $fullPath = if ([System.IO.Path]::IsPathRooted($resourcePath)) {
            $resourcePath
        }
        else {
            Join-Path $fileDir $resourcePath
        }
        
        # Normalize path separators
        $fullPath = $fullPath -replace '\\', [System.IO.Path]::DirectorySeparatorChar
        
        if (-not (Test-Path $fullPath)) {
            [void]$issues.Add([PSCustomObject]@{
                File = $FilePath
                Line = $lineNum
                Code = 'MISSING_RESOURCE'
                Severity = 'Warning'
                Message = "Referenced resource not found: $resourcePath"
                CanFix = $false
            })
        }
    }
    
    # Find Sound elements
    $soundPattern = '<Sound[^>]+filename\s*=\s*"([^"]+)"'
    $soundMatches = [regex]::Matches($text, $soundPattern, 'IgnoreCase')
    
    foreach ($m in $soundMatches) {
        $resourcePath = $m.Groups[1].Value
        $before = $text.Substring(0, $m.Index)
        $lineNum = ($before -split "`n").Count
        
        $fullPath = if ([System.IO.Path]::IsPathRooted($resourcePath)) {
            $resourcePath
        }
        else {
            Join-Path $fileDir $resourcePath
        }
        
        $fullPath = $fullPath -replace '\\', [System.IO.Path]::DirectorySeparatorChar
        
        if (-not (Test-Path $fullPath)) {
            [void]$issues.Add([PSCustomObject]@{
                File = $FilePath
                Line = $lineNum
                Code = 'MISSING_RESOURCE'
                Severity = 'Warning'
                Message = "Referenced sound file not found: $resourcePath"
                CanFix = $false
            })
        }
    }
    
    return $issues
}

# Functions are available for dot-sourcing


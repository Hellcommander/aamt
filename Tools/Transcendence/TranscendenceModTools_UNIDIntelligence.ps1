<#
.SYNOPSIS
  Enhanced UNID Intelligence Module
  
.DESCRIPTION
  Advanced UNID features:
  - Show where each UNID is referenced
  - Detect "dangling" UNIDs that nothing uses
  - Detect UNIDs that are overridden by multiple mods
  - Suggest unused UNID ranges for new mods
#>

# ============================================================
# UNID INTELLIGENCE
# ============================================================

# UNID Range Information
$script:UnidRanges = @{
    ReservedKronosaur = @{ Start = 0x0000; End = 0x9FFF; Description = 'Reserved for Kronosaur Productions' }
    RegisteredExtensions = @{ Start = 0xA000; End = 0xCFFF; Description = 'Reserved for Registered Extensions' }
    UserUnids = @{ Start = 0xD000; End = 0xEFFF; Description = 'User UNIDs (available for mods)' }
    DynamicUnids = @{ Start = 0xF000; End = 0xFFFF; Description = 'Reserved for typCreate Dynamic UNIDs' }
    SpecialReserved = @(
        @{ Value = 0xD000; Description = 'Reserved (ministry uploaded issue-reproduction mods, wiki)' }
        @{ Start = 0x0070; End = 0x007F; Description = 'Reserved for compatibility libraries' }
        @{ Value = 0xEFFC; Description = 'Stable version patches' }
        @{ Value = 0xEFFD; Description = 'Alpha/beta/rc version patches' }
        @{ Value = 0xEFFE; Description = 'Expansion Library Template' }
        @{ Value = 0xEFFF; Description = 'Transcendence Next++ Feature previews' }
    )
}

function Get-UnidIntelligence {
    param(
        [string[]]$Files,
        [string[]]$AllModPaths = @()
    )
    
    $intelligence = @{
        Unids = @{}
        References = @{}
        DanglingUnids = @()
        OverrideConflicts = @()
        UnusedRanges = @()
    }
    
    $unidMap = @{}
    $unidDefinitions = @{}
    $unidReferences = @{}
    
    # First pass: Extract UNID definitions and build map
    foreach ($file in $Files) {
        $text = [System.IO.File]::ReadAllText($file, [System.Text.Encoding]::UTF8)
        
        # Extract UNID definitions
        $unidPattern = '<!ENTITY\s+(\w+)\s+"(0x[0-9A-Fa-f]+)"'
        $unidMatches = [regex]::Matches($text, $unidPattern, 'IgnoreCase')
        foreach ($m in $unidMatches) {
            $entityName = $m.Groups[1].Value
            $unidValue = $m.Groups[2].Value
            
            $unidMap[$entityName] = $unidValue
            $unidMap[$unidValue] = $entityName
            
            if (-not $unidDefinitions.ContainsKey($unidValue)) {
                $unidDefinitions[$unidValue] = @{
                    EntityName = $entityName
                    UNID = $unidValue
                    File = $file
                    Line = Get-LineNumber -Text $text -Position $m.Index
                    References = @()
                    ReferenceCount = 0
                }
            }
        }
    }
    
    # Second pass: Find all references
    foreach ($file in $Files) {
        $text = [System.IO.File]::ReadAllText($file, [System.Text.Encoding]::UTF8)
        
        # Find entity references
        $entityRefPattern = '&(\w+);'
        $entityRefMatches = [regex]::Matches($text, $entityRefPattern, 'IgnoreCase')
        
        foreach ($m in $entityRefMatches) {
            $entityName = $m.Groups[1].Value
            if ($unidMap.ContainsKey($entityName)) {
                $unidValue = $unidMap[$entityName]
                
                if (-not $unidReferences.ContainsKey($unidValue)) {
                    $unidReferences[$unidValue] = @()
                }
                
                $lineNum = Get-LineNumber -Text $text -Position $m.Index
                $unidReferences[$unidValue] += [PSCustomObject]@{
                    File = $file
                    Line = $lineNum
                    Context = Get-LineContext -Text $text -Position $m.Index
                }
            }
        }
        
        # Find direct UNID references (0x...)
        $directUnidPattern = '"(0x[0-9A-Fa-f]{8})"'
        $directUnidMatches = [regex]::Matches($text, $directUnidPattern, 'IgnoreCase')
        
        foreach ($m in $directUnidMatches) {
            $unidValue = $m.Groups[1].Value
            if ($unidDefinitions.ContainsKey($unidValue)) {
                if (-not $unidReferences.ContainsKey($unidValue)) {
                    $unidReferences[$unidValue] = @()
                }
                
                $lineNum = Get-LineNumber -Text $text -Position $m.Index
                $unidReferences[$unidValue] += [PSCustomObject]@{
                    File = $file
                    Line = $lineNum
                    Context = Get-LineContext -Text $text -Position $m.Index
                }
            }
        }
    }
    
    # Build intelligence
    foreach ($unid in $unidDefinitions.Keys) {
        $def = $unidDefinitions[$unid]
        $refs = if ($unidReferences.ContainsKey($unid)) { $unidReferences[$unid] } else { @() }
        
        $intelligence.Unids[$unid] = [PSCustomObject]@{
            UNID = $unid
            EntityName = $def.EntityName
            DefinedIn = $def.File
            DefinedAtLine = $def.Line
            ReferenceCount = $refs.Count
            References = $refs
            IsDangling = ($refs.Count -eq 0)
            Range = Get-UnidRange -Unid $unid
        }
        
        $intelligence.References[$unid] = $refs
        
        if ($refs.Count -eq 0) {
            $intelligence.DanglingUnids += [PSCustomObject]@{
                UNID = $unid
                EntityName = $def.EntityName
                File = $def.File
                Line = $def.Line
            }
        }
    }
    
    # Check for override conflicts (if multiple mod paths provided)
    if ($AllModPaths.Count -gt 1) {
        $intelligence.OverrideConflicts = Get-OverrideConflicts -AllModPaths $AllModPaths
    }
    
    # Suggest unused ranges
    $intelligence.UnusedRanges = Get-UnusedUnidRanges -Unids $intelligence.Unids.Keys
    
    return $intelligence
}

function Get-UnidRange {
    param([string]$Unid)
    
    $value = [Convert]::ToUInt32($Unid, 16)
    
    if ($value -ge 0x0000 -and $value -le 0x9FFF) {
        return 'Reserved (Kronosaur)'
    }
    elseif ($value -ge 0xA000 -and $value -le 0xCFFF) {
        return 'Reserved (Registered Extensions)'
    }
    elseif ($value -ge 0xD000 -and $value -le 0xEFFF) {
        return 'User UNID (Available)'
    }
    elseif ($value -ge 0xF000 -and $value -le 0xFFFF) {
        return 'Reserved (Dynamic)'
    }
    
    return 'Unknown'
}

function Get-OverrideConflicts {
    param([string[]]$AllModPaths)
    
    $conflicts = [System.Collections.ArrayList]::new()
    $unidToMods = @{}
    
    foreach ($modPath in $AllModPaths) {
        $files = @(Get-ChildItem -LiteralPath $modPath -Filter '*.xml' -Recurse -ErrorAction SilentlyContinue | ForEach-Object { $_.FullName })
        
        foreach ($file in $files) {
            $text = [System.IO.File]::ReadAllText($file, [System.Text.Encoding]::UTF8)
            
            # Find type definitions with UNID
            $typePattern = '<(ItemType|ShipClass|StationType|StationTypeOverride)[^>]+UNID\s*=\s*"([^"]+)"'
            $typeMatches = [regex]::Matches($text, $typePattern, 'IgnoreCase')
            
            foreach ($m in $typeMatches) {
                $unidRef = $m.Groups[2].Value
                
                # Resolve UNID
                $unidPattern = '<!ENTITY\s+(\w+)\s+"(0x[0-9A-Fa-f]+)"'
                $unidMatches = [regex]::Matches($text, $unidPattern, 'IgnoreCase')
                $unidMap = @{}
                foreach ($um in $unidMatches) {
                    $unidMap[$um.Groups[1].Value] = $um.Groups[2].Value
                }
                
                $unidValue = if ($unidRef.StartsWith('&') -and $unidRef.EndsWith(';')) {
                    $entityName = $unidRef.Substring(1, $unidRef.Length - 2)
                    if ($unidMap.ContainsKey($entityName)) { $unidMap[$entityName] } else { $null }
                }
                elseif ($unidRef -match '^0x[0-9A-Fa-f]{8}$') {
                    $unidRef
                }
                else {
                    $null
                }
                
                if ($unidValue) {
                    if (-not $unidToMods.ContainsKey($unidValue)) {
                        $unidToMods[$unidValue] = @()
                    }
                    
                    $modName = Split-Path -Leaf $modPath
                    if ($unidToMods[$unidValue] -notcontains $modName) {
                        $unidToMods[$unidValue] += $modName
                    }
                }
            }
        }
    }
    
    # Find conflicts (UNIDs defined in multiple mods)
    foreach ($unid in $unidToMods.Keys) {
        if ($unidToMods[$unid].Count -gt 1) {
            [void]$conflicts.Add([PSCustomObject]@{
                UNID = $unid
                Mods = $unidToMods[$unid]
                ConflictCount = $unidToMods[$unid].Count
            })
        }
    }
    
    return $conflicts
}

function Get-UnusedUnidRanges {
    param([string[]]$Unids)
    
    $suggestions = [System.Collections.ArrayList]::new()
    
    # Convert UNIDs to numeric values
    $usedValues = @()
    foreach ($unid in $Unids) {
        try {
            $value = [Convert]::ToUInt32($unid, 16)
            if ($value -ge 0xD000 -and $value -le 0xEFFF) {
                $usedValues += $value
            }
        }
        catch { }
    }
    
    $usedValues = $usedValues | Sort-Object
    
    # Find gaps in user UNID range
    $start = 0xD000
    $end = 0xEFFF
    
    # Avoid reserved ranges
    $reserved = @(0xD000, 0xEFFC, 0xEFFD, 0xEFFE, 0xEFFF)
    
    $current = $start
    $gapStart = $null
    
    while ($current -le $end) {
        if ($reserved -contains $current) {
            $current++
            continue
        }
        
        $isUsed = $usedValues -contains $current
        $isReserved = $false
        
        # Check special reserved ranges
        foreach ($res in $script:UnidRanges.SpecialReserved) {
            if ($res.ContainsKey('Start') -and $res.ContainsKey('End')) {
                if ($current -ge $res.Start -and $current -le $res.End) {
                    $isReserved = $true
                    break
                }
            }
        }
        
        if (-not $isUsed -and -not $isReserved) {
            if ($null -eq $gapStart) {
                $gapStart = $current
            }
        }
        else {
            if ($null -ne $gapStart) {
                $gapSize = $current - $gapStart
                if ($gapSize -ge 0x100) {  # At least 256 UNIDs
                    [void]$suggestions.Add([PSCustomObject]@{
                        Start = "0x$($gapStart.ToString('X8'))"
                        End = "0x$(($current - 1).ToString('X8'))"
                        Size = $gapSize
                        Description = "Available range: $gapSize UNIDs"
                    })
                }
                $gapStart = $null
            }
        }
        
        $current++
    }
    
    # Check final gap
    if ($null -ne $gapStart) {
        $gapSize = $end - $gapStart + 1
        if ($gapSize -ge 0x100) {
            [void]$suggestions.Add([PSCustomObject]@{
                Start = "0x$($gapStart.ToString('X8'))"
                End = "0x$($end.ToString('X8'))"
                Size = $gapSize
                Description = "Available range: $gapSize UNIDs"
            })
        }
    }
    
    return $suggestions
}

function Get-LineContext {
    param([string]$Text, [int]$Position)
    
    $before = $Text.Substring(0, $Position)
    $after = $Text.Substring($Position)
    
    $lineStart = $before.LastIndexOf("`n")
    $lineEnd = $after.IndexOf("`n")
    
    if ($lineEnd -eq -1) { $lineEnd = $after.Length }
    
    $line = $Text.Substring($lineStart + 1, $Position - $lineStart - 1 + $lineEnd)
    return $line.Trim()
}

function Get-LineNumber {
    param([string]$Text, [int]$Position)
    
    $before = $Text.Substring(0, $Position)
    return ([regex]::Matches($before, "`n")).Count + 1
}

# Export functions
# Functions are available for dot-sourcing


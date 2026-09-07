<#
.SYNOPSIS
  "What Changed?" Diff Mode Module
  
.DESCRIPTION
  Compares two versions of a mod or game XML:
  - Added types
  - Removed types
  - Changed attributes
  - New events
  - Deprecated fields
#>

# ============================================================
# DIFF MODE ANALYZER
# ============================================================

function Get-ModDiff {
    param(
        [string[]]$OldFiles,
        [string[]]$NewFiles,
        [hashtable]$OldEvents,
        [hashtable]$NewEvents
    )
    
    $diff = @{
        AddedTypes = @()
        RemovedTypes = @()
        ChangedTypes = @()
        AddedEvents = @()
        RemovedEvents = @()
        ChangedAttributes = @()
        DeprecatedFields = @()
    }
    
    # Parse old version
    $oldTypes = Get-AllTypes -Files $OldFiles
    $oldAttributes = Get-AllAttributes -Files $OldFiles
    
    # Parse new version
    $newTypes = Get-AllTypes -Files $NewFiles
    $newAttributes = Get-AllAttributes -Files $NewFiles
    
    # Find added types
    foreach ($unid in $newTypes.Keys) {
        if (-not $oldTypes.ContainsKey($unid)) {
            $diff.AddedTypes += $newTypes[$unid]
        }
    }
    
    # Find removed types
    foreach ($unid in $oldTypes.Keys) {
        if (-not $newTypes.ContainsKey($unid)) {
            $diff.RemovedTypes += $oldTypes[$unid]
        }
    }
    
    # Find changed types
    foreach ($unid in $newTypes.Keys) {
        if ($oldTypes.ContainsKey($unid)) {
            $oldType = $oldTypes[$unid]
            $newType = $newTypes[$unid]
            
            # Compare attributes
            $attrChanges = Compare-TypeAttributes -OldType $oldType -NewType $newType -OldAttributes $oldAttributes -NewAttributes $newAttributes
            if ($attrChanges.Count -gt 0) {
                $diff.ChangedTypes += [PSCustomObject]@{
                    UNID = $unid
                    Name = $newType.Name
                    Type = $newType.Type
                    AttributeChanges = $attrChanges
                }
                # Also add to ChangedAttributes for summary
                $diff.ChangedAttributes += $attrChanges | ForEach-Object {
                    [PSCustomObject]@{
                        Type = $newType.Name
                        TypeUNID = $unid
                        Attribute = $_.Attribute
                        OldValue = $_.OldValue
                        NewValue = $_.NewValue
                        Change = $_.Change
                    }
                }
            }
            
            # Compare events
            $eventChanges = Compare-TypeEvents -OldType $oldType -NewType $newType -OldEvents $OldEvents -NewEvents $NewEvents
            if ($eventChanges.Added.Count -gt 0 -or $eventChanges.Removed.Count -gt 0) {
                $diff.AddedEvents += $eventChanges.Added | ForEach-Object {
                    [PSCustomObject]@{
                        Type = $newType.Name
                        TypeUNID = $unid
                        Event = $_
                    }
                }
                $diff.RemovedEvents += $eventChanges.Removed | ForEach-Object {
                    [PSCustomObject]@{
                        Type = $oldType.Name
                        TypeUNID = $unid
                        Event = $_
                    }
                }
            }
        }
    }
    
    # Find deprecated fields
    $diff.DeprecatedFields = Get-DeprecatedFields -OldAttributes $oldAttributes -NewAttributes $newAttributes
    
    return $diff
}

function Get-AllTypes {
    param([string[]]$Files)
    
    $types = @{}
    $unidMap = @{}
    
    foreach ($file in $Files) {
        $text = [System.IO.File]::ReadAllText($file, [System.Text.Encoding]::UTF8)
        
        # Extract UNID definitions
        $unidPattern = '<!ENTITY\s+(\w+)\s+"(0x[0-9A-Fa-f]+)"'
        $unidMatches = [regex]::Matches($text, $unidPattern, 'IgnoreCase')
        foreach ($m in $unidMatches) {
            $unidMap[$m.Groups[1].Value] = $m.Groups[2].Value
            $unidMap[$m.Groups[2].Value] = $m.Groups[1].Value
        }
        
        # Find ItemTypes
        $itemPattern = '<ItemType[^>]+UNID\s*=\s*"([^"]+)"'
        $itemMatches = [regex]::Matches($text, $itemPattern, 'IgnoreCase')
        foreach ($m in $itemMatches) {
            $unidRef = $m.Groups[1].Value
            $unidValue = Resolve-UnidValue -UnidRef $unidRef -UnidMap $unidMap
            if ($unidValue) {
                $types[$unidValue] = [PSCustomObject]@{
                    UNID = $unidValue
                    Name = Get-EntityName -UnidRef $unidRef -UnidMap $unidMap
                    Type = 'ItemType'
                    File = $file
                }
            }
        }
        
        # Find ShipClasses
        $shipPattern = '<ShipClass[^>]+UNID\s*=\s*"([^"]+)"'
        $shipMatches = [regex]::Matches($text, $shipPattern, 'IgnoreCase')
        foreach ($m in $shipMatches) {
            $unidRef = $m.Groups[1].Value
            $unidValue = Resolve-UnidValue -UnidRef $unidRef -UnidMap $unidMap
            if ($unidValue) {
                $types[$unidValue] = [PSCustomObject]@{
                    UNID = $unidValue
                    Name = Get-EntityName -UnidRef $unidRef -UnidMap $unidMap
                    Type = 'ShipClass'
                    File = $file
                }
            }
        }
        
        # Find StationTypes
        $stationPattern = '<StationType[^>]+UNID\s*=\s*"([^"]+)"'
        $stationMatches = [regex]::Matches($text, $stationPattern, 'IgnoreCase')
        foreach ($m in $stationMatches) {
            $unidRef = $m.Groups[1].Value
            $unidValue = Resolve-UnidValue -UnidRef $unidRef -UnidMap $unidMap
            if ($unidValue) {
                $types[$unidValue] = [PSCustomObject]@{
                    UNID = $unidValue
                    Name = Get-EntityName -UnidRef $unidRef -UnidMap $unidMap
                    Type = 'StationType'
                    File = $file
                }
            }
        }
        
        # Find Sovereigns
        $sovereignPattern = '<Sovereign[^>]+UNID\s*=\s*"([^"]+)"'
        $sovereignMatches = [regex]::Matches($text, $sovereignPattern, 'IgnoreCase')
        foreach ($m in $sovereignMatches) {
            $unidRef = $m.Groups[1].Value
            $unidValue = Resolve-UnidValue -UnidRef $unidRef -UnidMap $unidMap
            if ($unidValue) {
                $types[$unidValue] = [PSCustomObject]@{
                    UNID = $unidValue
                    Name = Get-EntityName -UnidRef $unidRef -UnidMap $unidMap
                    Type = 'Sovereign'
                    File = $file
                }
            }
        }
        
        # Find Missions
        $missionPattern = '<MissionType[^>]+UNID\s*=\s*"([^"]+)"'
        $missionMatches = [regex]::Matches($text, $missionPattern, 'IgnoreCase')
        foreach ($m in $missionMatches) {
            $unidRef = $m.Groups[1].Value
            $unidValue = Resolve-UnidValue -UnidRef $unidRef -UnidMap $unidMap
            if ($unidValue) {
                $types[$unidValue] = [PSCustomObject]@{
                    UNID = $unidValue
                    Name = Get-EntityName -UnidRef $unidRef -UnidMap $unidMap
                    Type = 'MissionType'
                    File = $file
                }
            }
        }
    }
    
    return $types
}

function Get-AllEvents {
    param([string[]]$Files)
    
    $events = @{}
    $unidMap = @{}
    
    foreach ($file in $Files) {
        $text = [System.IO.File]::ReadAllText($file, [System.Text.Encoding]::UTF8)
        
        # Extract UNID definitions
        $unidPattern = '<!ENTITY\s+(\w+)\s+"(0x[0-9A-Fa-f]+)"'
        $unidMatches = [regex]::Matches($text, $unidPattern, 'IgnoreCase')
        foreach ($m in $unidMatches) {
            $unidMap[$m.Groups[1].Value] = $m.Groups[2].Value
            $unidMap[$m.Groups[2].Value] = $m.Groups[1].Value
        }
        
        # Find types and their events
        $typePattern = '<(ItemType|ShipClass|StationType|MissionType)[^>]+UNID\s*=\s*"([^"]+)"'
        $typeMatches = [regex]::Matches($text, $typePattern, 'IgnoreCase')
        
        foreach ($m in $typeMatches) {
            $unidRef = $m.Groups[2].Value
            $unidValue = Resolve-UnidValue -UnidRef $unidRef -UnidMap $unidMap
            if ($unidValue) {
                # Find events in this type
                $eventPattern = '<(On\w+)>'
                $eventMatches = [regex]::Matches($text, $eventPattern, 'IgnoreCase')
                
                if (-not $events.ContainsKey($unidValue)) {
                    $events[$unidValue] = @()
                }
                
                foreach ($em in $eventMatches) {
                    $eventName = $em.Groups[1].Value
                    if ($events[$unidValue] -notcontains $eventName) {
                        $events[$unidValue] += $eventName
                    }
                }
            }
        }
    }
    
    return $events
}

function Get-AllAttributes {
    param([string[]]$Files)
    
    $attributes = @{}
    $unidMap = @{}
    
    foreach ($file in $Files) {
        $text = [System.IO.File]::ReadAllText($file, [System.Text.Encoding]::UTF8)
        
        # Extract UNID definitions
        $unidPattern = '<!ENTITY\s+(\w+)\s+"(0x[0-9A-Fa-f]+)"'
        $unidMatches = [regex]::Matches($text, $unidPattern, 'IgnoreCase')
        foreach ($m in $unidMatches) {
            $unidMap[$m.Groups[1].Value] = $m.Groups[2].Value
            $unidMap[$m.Groups[2].Value] = $m.Groups[1].Value
        }
        
        # Find types and their attributes
        $typePattern = '<(ItemType|ShipClass|StationType|MissionType)[^>]+UNID\s*=\s*"([^"]+)"[^>]*>'
        $typeMatches = [regex]::Matches($text, $typePattern, 'IgnoreCase')
        
        foreach ($m in $typeMatches) {
            $unidRef = $m.Groups[2].Value
            $unidValue = Resolve-UnidValue -UnidRef $unidRef -UnidMap $unidMap
            if ($unidValue) {
                # Extract all attributes
                $attrPattern = '(\w+)\s*=\s*"([^"]*)"'
                $attrMatches = [regex]::Matches($m.Value, $attrPattern, 'IgnoreCase')
                
                if (-not $attributes.ContainsKey($unidValue)) {
                    $attributes[$unidValue] = @{}
                }
                
                foreach ($am in $attrMatches) {
                    $attrName = $am.Groups[1].Value
                    $attrValue = $am.Groups[2].Value
                    if ($attrName -ne 'UNID') {
                        $attributes[$unidValue][$attrName] = $attrValue
                    }
                }
            }
        }
    }
    
    return $attributes
}

function Compare-TypeAttributes {
    param(
        [PSCustomObject]$OldType,
        [PSCustomObject]$NewType,
        [hashtable]$OldAttributes,
        [hashtable]$NewAttributes
    )
    
    $changes = [System.Collections.ArrayList]::new()
    
    $oldAttrs = if ($OldAttributes.ContainsKey($OldType.UNID)) { $OldAttributes[$OldType.UNID] } else { @{} }
    $newAttrs = if ($NewAttributes.ContainsKey($NewType.UNID)) { $NewAttributes[$NewType.UNID] } else { @{} }
    
    # Find added attributes
    foreach ($attrName in $newAttrs.Keys) {
        if (-not $oldAttrs.ContainsKey($attrName)) {
            [void]$changes.Add([PSCustomObject]@{
                Attribute = $attrName
                OldValue = ''
                NewValue = $newAttrs[$attrName]
                Change = 'Added'
            })
        }
        elseif ($oldAttrs[$attrName] -ne $newAttrs[$attrName]) {
            [void]$changes.Add([PSCustomObject]@{
                Attribute = $attrName
                OldValue = $oldAttrs[$attrName]
                NewValue = $newAttrs[$attrName]
                Change = 'Modified'
            })
        }
    }
    
    # Find removed attributes
    foreach ($attrName in $oldAttrs.Keys) {
        if (-not $newAttrs.ContainsKey($attrName)) {
            [void]$changes.Add([PSCustomObject]@{
                Attribute = $attrName
                OldValue = $oldAttrs[$attrName]
                NewValue = ''
                Change = 'Removed'
            })
        }
    }
    
    return $changes
}

function Compare-TypeEvents {
    param(
        [PSCustomObject]$OldType,
        [PSCustomObject]$NewType,
        [hashtable]$OldEvents,
        [hashtable]$NewEvents
    )
    
    $oldEventsList = if ($OldEvents.ContainsKey($OldType.UNID)) { $OldEvents[$OldType.UNID] } else { @() }
    $newEventsList = if ($NewEvents.ContainsKey($NewType.UNID)) { $NewEvents[$NewType.UNID] } else { @() }
    
    return [PSCustomObject]@{
        Added = @($newEventsList | Where-Object { $oldEventsList -notcontains $_ })
        Removed = @($oldEventsList | Where-Object { $newEventsList -notcontains $_ })
    }
}

function Get-DeprecatedFields {
    param(
        [hashtable]$OldAttributes,
        [hashtable]$NewAttributes
    )
    
    $deprecated = [System.Collections.ArrayList]::new()
    
    # Known deprecated attributes
    $deprecatedAttrs = @(
        'obsoleteVersion',
        'oldApiVersion'
    )
    
    # Check for deprecated attributes in new version
    foreach ($unid in $NewAttributes.Keys) {
        foreach ($attr in $deprecatedAttrs) {
            if ($NewAttributes[$unid].ContainsKey($attr)) {
                [void]$deprecated.Add([PSCustomObject]@{
                    UNID = $unid
                    Attribute = $attr
                    Value = $NewAttributes[$unid][$attr]
                })
            }
        }
    }
    
    return $deprecated
}

function Resolve-UnidValue {
    param([string]$UnidRef, [hashtable]$UnidMap)
    
    if ($UnidRef.StartsWith('&') -and $UnidRef.EndsWith(';')) {
        $entityName = $UnidRef.Substring(1, $UnidRef.Length - 2)
        if ($UnidMap.ContainsKey($entityName)) {
            return $UnidMap[$entityName]
        }
    }
    elseif ($UnidRef -match '^0x[0-9A-Fa-f]{8}$') {
        return $UnidRef
    }
    
    return ''
}

function Get-EntityName {
    param([string]$UnidRef, [hashtable]$UnidMap)
    
    if ($UnidRef.StartsWith('&') -and $UnidRef.EndsWith(';')) {
        return $UnidRef.Substring(1, $UnidRef.Length - 2)
    }
    
    return $UnidRef
}

function Format-DiffReport {
    param([hashtable]$Diff)
    
    $output = [System.Text.StringBuilder]::new()
    [void]$output.AppendLine('═══════════════════════════════════════════════════════════')
    [void]$output.AppendLine('                    "WHAT CHANGED?" DIFF')
    [void]$output.AppendLine('═══════════════════════════════════════════════════════════')
    [void]$output.AppendLine('')
    
    # Summary
    [void]$output.AppendLine('SUMMARY:')
    [void]$output.AppendLine("  Added Types:        $($diff.AddedTypes.Count)")
    [void]$output.AppendLine("  Removed Types:      $($diff.RemovedTypes.Count)")
    [void]$output.AppendLine("  Changed Types:      $($diff.ChangedTypes.Count)")
    [void]$output.AppendLine("  Added Events:       $($diff.AddedEvents.Count)")
    [void]$output.AppendLine("  Removed Events:     $($diff.RemovedEvents.Count)")
    [void]$output.AppendLine("  Deprecated Fields:  $($diff.DeprecatedFields.Count)")
    [void]$output.AppendLine('')
    
    # Added Types
    if ($diff.AddedTypes.Count -gt 0) {
        [void]$output.AppendLine('═══════════════════════════════════════════════════════════')
        [void]$output.AppendLine('                    ADDED TYPES')
        [void]$output.AppendLine('═══════════════════════════════════════════════════════════')
        [void]$output.AppendLine('')
        
        foreach ($type in $diff.AddedTypes | Sort-Object Type, Name) {
            [void]$output.AppendLine("  ✅ $($type.Name) [$($type.Type)]")
            [void]$output.AppendLine("     UNID: $($type.UNID)")
            [void]$output.AppendLine("     File: $(Split-Path -Leaf $type.File)")
            [void]$output.AppendLine('')
        }
    }
    
    # Removed Types
    if ($diff.RemovedTypes.Count -gt 0) {
        [void]$output.AppendLine('═══════════════════════════════════════════════════════════')
        [void]$output.AppendLine('                    REMOVED TYPES')
        [void]$output.AppendLine('═══════════════════════════════════════════════════════════')
        [void]$output.AppendLine('')
        
        foreach ($type in $diff.RemovedTypes | Sort-Object Type, Name) {
            [void]$output.AppendLine("  ❌ $($type.Name) [$($type.Type)]")
            [void]$output.AppendLine("     UNID: $($type.UNID)")
            [void]$output.AppendLine("     File: $(Split-Path -Leaf $type.File)")
            [void]$output.AppendLine('')
        }
    }
    
    # Changed Types
    if ($diff.ChangedTypes.Count -gt 0) {
        [void]$output.AppendLine('═══════════════════════════════════════════════════════════')
        [void]$output.AppendLine('                    CHANGED TYPES')
        [void]$output.AppendLine('═══════════════════════════════════════════════════════════')
        [void]$output.AppendLine('')
        
        foreach ($type in $diff.ChangedTypes) {
            [void]$output.AppendLine("  🔄 $($type.Name) [$($type.Type)]")
            [void]$output.AppendLine("     UNID: $($type.UNID)")
            if ($type.AttributeChanges.Count -gt 0) {
                [void]$output.AppendLine("     Attribute Changes:")
                foreach ($change in $type.AttributeChanges) {
                    if ($change.Change -eq 'Added') {
                        [void]$output.AppendLine("       ✅ $($change.Attribute) = $($change.NewValue)")
                    }
                    elseif ($change.Change -eq 'Removed') {
                        [void]$output.AppendLine("       ❌ $($change.Attribute) = $($change.OldValue) (removed)")
                    }
                    else {
                        [void]$output.AppendLine("       🔄 $($change.Attribute): '$($change.OldValue)' → '$($change.NewValue)'")
                    }
                }
            }
            [void]$output.AppendLine('')
        }
    }
    
    # Added Events
    if ($diff.AddedEvents.Count -gt 0) {
        [void]$output.AppendLine('═══════════════════════════════════════════════════════════')
        [void]$output.AppendLine('                    ADDED EVENTS')
        [void]$output.AppendLine('═══════════════════════════════════════════════════════════')
        [void]$output.AppendLine('')
        
        foreach ($event in $diff.AddedEvents | Sort-Object Type, Event) {
            [void]$output.AppendLine("  ✅ $($event.Type) → $($event.Event)")
            [void]$output.AppendLine('')
        }
    }
    
    # Removed Events
    if ($diff.RemovedEvents.Count -gt 0) {
        [void]$output.AppendLine('═══════════════════════════════════════════════════════════')
        [void]$output.AppendLine('                    REMOVED EVENTS')
        [void]$output.AppendLine('═══════════════════════════════════════════════════════════')
        [void]$output.AppendLine('')
        
        foreach ($event in $diff.RemovedEvents | Sort-Object Type, Event) {
            [void]$output.AppendLine("  ❌ $($event.Type) → $($event.Event)")
            [void]$output.AppendLine('')
        }
    }
    
    # Deprecated Fields
    if ($diff.DeprecatedFields.Count -gt 0) {
        [void]$output.AppendLine('═══════════════════════════════════════════════════════════')
        [void]$output.AppendLine('                    DEPRECATED FIELDS')
        [void]$output.AppendLine('═══════════════════════════════════════════════════════════')
        [void]$output.AppendLine('')
        
        foreach ($field in $diff.DeprecatedFields) {
            [void]$output.AppendLine("  ⚠ UNID: $($field.UNID)")
            [void]$output.AppendLine("     Attribute: $($field.Attribute) = $($field.Value)")
            [void]$output.AppendLine('')
        }
    }
    
    [void]$output.AppendLine('═══════════════════════════════════════════════════════════')
    
    return $output.ToString()
}

# Export functions
# Functions are available for dot-sourcing


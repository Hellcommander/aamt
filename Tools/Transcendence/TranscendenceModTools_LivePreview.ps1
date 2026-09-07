<#
.SYNOPSIS
  Live Preview of Resolved Types Module
  
.DESCRIPTION
  Shows fully resolved type information:
  - Fully resolved attributes (after inheritance)
  - All events it implements
  - All resources it uses
  - All types it references
  - All types that reference it
#>

# ============================================================
# LIVE PREVIEW OF RESOLVED TYPES
# ============================================================

function Get-LivePreview {
    param(
        [string]$Unid,
        [string[]]$Files
    )
    
    $preview = [PSCustomObject]@{
        UNID = $Unid
        Type = ''
        Name = ''
        File = ''
        ResolvedAttributes = @{}
        AttributeSources = @{}
        Events = @()
        EventSources = @{}
        Resources = @{
            Images = @()
            Sounds = @()
            Icons = @()
        }
        References = @{
            Uses = @()
            Inherits = @()
            Spawns = @()
        }
        ReferencedBy = @()
        Conflicts = @()
    }
    
    # Build UNID map
    $unidMap = @{}
    foreach ($file in $Files) {
        $text = [System.IO.File]::ReadAllText($file, [System.Text.Encoding]::UTF8)
        $unidPattern = '<!ENTITY\s+(\w+)\s+"(0x[0-9A-Fa-f]+)"'
        $unidMatches = [regex]::Matches($text, $unidPattern, 'IgnoreCase')
        foreach ($m in $unidMatches) {
            $unidMap[$m.Groups[1].Value] = $m.Groups[2].Value
            $unidMap[$m.Groups[2].Value] = $m.Groups[1].Value
        }
    }
    
    # Find type definition
    $typeInfo = Get-TypeInfo -Unid $Unid -Files $Files -UnidMap $unidMap
    if (-not $typeInfo) {
        return $null
    }
    
    $preview.Type = $typeInfo.Type
    $preview.Name = $typeInfo.Name
    $preview.File = $typeInfo.File
    
    # Load semantic module for inheritance resolution
    $semModule = Join-Path $PSScriptRoot 'TranscendenceModTools_Semantic.ps1'
    if (Test-Path $semModule) {
        . $semModule
        
        # Build inheritance tree
        $tree = Get-InheritanceTree -Files $Files
        
        # Get resolved type
        $resolved = Get-ResolvedType -Unid $Unid -InheritanceTree $tree -TypeRegistry @{} -Files $Files
        
        $preview.ResolvedAttributes = $resolved.Attributes
        $preview.AttributeSources = $resolved.AttributeSources
        $preview.Events = $resolved.Events
        $preview.EventSources = $resolved.EventSources
        $preview.Conflicts = $resolved.Conflicts
    }
    else {
        # Fallback: just get current type attributes and events
        $preview.ResolvedAttributes = Get-TypeAttributes -Unid $Unid -Files $Files -UnidMap $unidMap
        $preview.Events = Get-TypeEvents -Unid $Unid -Files $Files -UnidMap $unidMap
    }
    
    # Get resources
    $resources = Get-TypeResources -Unid $Unid -Files $Files -UnidMap $unidMap
    $preview.Resources = $resources
    
    # Get references (types this type uses)
    $references = Get-TypeReferences -Unid $Unid -Files $Files -UnidMap $unidMap
    $preview.References = $references
    
    # Get reverse references (types that reference this type)
    $reverseRefs = Get-ReverseReferences -Unid $Unid -Files $Files -UnidMap $unidMap
    $preview.ReferencedBy = $reverseRefs
    
    return $preview
}

function Get-TypeInfo {
    param(
        [string]$Unid,
        [string[]]$Files,
        [hashtable]$UnidMap
    )
    
    foreach ($file in $Files) {
        $text = [System.IO.File]::ReadAllText($file, [System.Text.Encoding]::UTF8)
        
        # Try ItemType
        $itemPattern = '<ItemType[^>]+UNID\s*=\s*"([^"]+)"'
        $itemMatches = [regex]::Matches($text, $itemPattern, 'IgnoreCase')
        foreach ($m in $itemMatches) {
            $unidRef = $m.Groups[1].Value
            $unidValue = Resolve-UnidValue -UnidRef $unidRef -UnidMap $unidMap
            if ($unidValue -eq $Unid) {
                return [PSCustomObject]@{
                    Type = 'ItemType'
                    Name = Get-EntityName -UnidRef $unidRef -UnidMap $unidMap
                    File = $file
                }
            }
        }
        
        # Try ShipClass
        $shipPattern = '<ShipClass[^>]+UNID\s*=\s*"([^"]+)"'
        $shipMatches = [regex]::Matches($text, $shipPattern, 'IgnoreCase')
        foreach ($m in $shipMatches) {
            $unidRef = $m.Groups[1].Value
            $unidValue = Resolve-UnidValue -UnidRef $unidRef -UnidMap $unidMap
            if ($unidValue -eq $Unid) {
                return [PSCustomObject]@{
                    Type = 'ShipClass'
                    Name = Get-EntityName -UnidRef $unidRef -UnidMap $unidMap
                    File = $file
                }
            }
        }
        
        # Try StationType
        $stationPattern = '<StationType[^>]+UNID\s*=\s*"([^"]+)"'
        $stationMatches = [regex]::Matches($text, $stationPattern, 'IgnoreCase')
        foreach ($m in $stationMatches) {
            $unidRef = $m.Groups[1].Value
            $unidValue = Resolve-UnidValue -UnidRef $unidRef -UnidMap $unidMap
            if ($unidValue -eq $Unid) {
                return [PSCustomObject]@{
                    Type = 'StationType'
                    Name = Get-EntityName -UnidRef $unidRef -UnidMap $unidMap
                    File = $file
                }
            }
        }
        
        # Try Sovereign
        $sovereignPattern = '<Sovereign[^>]+UNID\s*=\s*"([^"]+)"'
        $sovereignMatches = [regex]::Matches($text, $sovereignPattern, 'IgnoreCase')
        foreach ($m in $sovereignMatches) {
            $unidRef = $m.Groups[1].Value
            $unidValue = Resolve-UnidValue -UnidRef $unidRef -UnidMap $unidMap
            if ($unidValue -eq $Unid) {
                return [PSCustomObject]@{
                    Type = 'Sovereign'
                    Name = Get-EntityName -UnidRef $unidRef -UnidMap $unidMap
                    File = $file
                }
            }
        }
        
        # Try MissionType
        $missionPattern = '<MissionType[^>]+UNID\s*=\s*"([^"]+)"'
        $missionMatches = [regex]::Matches($text, $missionPattern, 'IgnoreCase')
        foreach ($m in $missionMatches) {
            $unidRef = $m.Groups[1].Value
            $unidValue = Resolve-UnidValue -UnidRef $unidRef -UnidMap $unidMap
            if ($unidValue -eq $Unid) {
                return [PSCustomObject]@{
                    Type = 'MissionType'
                    Name = Get-EntityName -UnidRef $unidRef -UnidMap $unidMap
                    File = $file
                }
            }
        }
    }
    
    return $null
}

function Get-TypeResources {
    param(
        [string]$Unid,
        [string[]]$Files,
        [hashtable]$UnidMap
    )
    
    $resources = @{
        Images = @()
        Sounds = @()
        Icons = @()
    }
    
    foreach ($file in $Files) {
        $text = [System.IO.File]::ReadAllText($file, [System.Text.Encoding]::UTF8)
        
        # Find type definition
        $typePattern = '<(ItemType|ShipClass|StationType)[^>]+UNID\s*=\s*"([^"]+)"'
        $typeMatch = [regex]::Match($text, $typePattern, 'IgnoreCase')
        
        if ($typeMatch.Success) {
            $unidRef = $typeMatch.Groups[2].Value
            $unidValue = Resolve-UnidValue -UnidRef $unidRef -UnidMap $unidMap
            
            if ($unidValue -eq $Unid) {
                # Find image references
                $imagePattern = '(?:image|bitmap|imageID)\s*=\s*"([^"]+)"'
                $imageMatches = [regex]::Matches($text, $imagePattern, 'IgnoreCase')
                foreach ($m in $imageMatches) {
                    $imageRef = $m.Groups[1].Value
                    if ($imageRef -notin $resources.Images) {
                        $resources.Images += $imageRef
                    }
                }
                
                # Find sound references
                $soundPattern = '(?:sound|soundID)\s*=\s*"([^"]+)"'
                $soundMatches = [regex]::Matches($text, $soundPattern, 'IgnoreCase')
                foreach ($m in $soundMatches) {
                    $soundRef = $m.Groups[1].Value
                    if ($soundRef -notin $resources.Sounds) {
                        $resources.Sounds += $soundRef
                    }
                }
                
                # Find icon references
                $iconPattern = '(?:icon|iconID)\s*=\s*"([^"]+)"'
                $iconMatches = [regex]::Matches($text, $iconPattern, 'IgnoreCase')
                foreach ($m in $iconMatches) {
                    $iconRef = $m.Groups[1].Value
                    if ($iconRef -notin $resources.Icons) {
                        $resources.Icons += $iconRef
                    }
                }
                
                break
            }
        }
    }
    
    return $resources
}

function Get-TypeReferences {
    param(
        [string]$Unid,
        [string[]]$Files,
        [hashtable]$UnidMap
    )
    
    $references = @{
        Uses = @()
        Inherits = @()
        Spawns = @()
    }
    
    foreach ($file in $Files) {
        $text = [System.IO.File]::ReadAllText($file, [System.Text.Encoding]::UTF8)
        
        # Find type definition
        $typePattern = '<(ItemType|ShipClass|StationType)[^>]+UNID\s*=\s*"([^"]+)"'
        $typeMatch = [regex]::Match($text, $typePattern, 'IgnoreCase')
        
        if ($typeMatch.Success) {
            $unidRef = $typeMatch.Groups[2].Value
            $unidValue = Resolve-UnidValue -UnidRef $unidRef -UnidMap $unidMap
            
            if ($unidValue -eq $Unid) {
                # Find inherit
                $inheritMatch = [regex]::Match($typeMatch.Value, 'inherit\s*=\s*"([^"]+)"', 'IgnoreCase')
                if ($inheritMatch.Success) {
                    $inheritRef = $inheritMatch.Groups[1].Value
                    $inheritUnid = Resolve-UnidValue -UnidRef $inheritRef -UnidMap $unidMap
                    if ($inheritUnid) {
                        $references.Inherits += [PSCustomObject]@{
                            UNID = $inheritUnid
                            Name = Get-EntityName -UnidRef $inheritRef -UnidMap $unidMap
                            Relationship = 'Inherits'
                        }
                    }
                }
                
                # Find device/item references (uses)
                $devicePattern = '<Device[^>]+(?:deviceID|item)\s*=\s*"([^"]+)"'
                $deviceMatches = [regex]::Matches($text, $devicePattern, 'IgnoreCase')
                foreach ($m in $deviceMatches) {
                    $deviceRef = $m.Groups[1].Value
                    $deviceUnid = Resolve-UnidValue -UnidRef $deviceRef -UnidMap $unidMap
                    if ($deviceUnid) {
                        $references.Uses += [PSCustomObject]@{
                            UNID = $deviceUnid
                            Name = Get-EntityName -UnidRef $deviceRef -UnidMap $unidMap
                            Relationship = 'Uses'
                        }
                    }
                }
                
                # Find weapon references (uses)
                $weaponPattern = '<Weapon[^>]+type\s*=\s*"([^"]+)"'
                $weaponMatches = [regex]::Matches($text, $weaponPattern, 'IgnoreCase')
                foreach ($m in $weaponMatches) {
                    $weaponRef = $m.Groups[1].Value
                    $weaponUnid = Resolve-UnidValue -UnidRef $weaponRef -UnidMap $unidMap
                    if ($weaponUnid) {
                        $references.Uses += [PSCustomObject]@{
                            UNID = $weaponUnid
                            Name = Get-EntityName -UnidRef $weaponRef -UnidMap $unidMap
                            Relationship = 'Uses'
                        }
                    }
                }
                
                # Find armor references (uses)
                $armorPattern = '<Armor[^>]+armorID\s*=\s*"([^"]+)"'
                $armorMatches = [regex]::Matches($text, $armorPattern, 'IgnoreCase')
                foreach ($m in $armorMatches) {
                    $armorRef = $m.Groups[1].Value
                    $armorUnid = Resolve-UnidValue -UnidRef $armorRef -UnidMap $unidMap
                    if ($armorUnid) {
                        $references.Uses += [PSCustomObject]@{
                            UNID = $armorUnid
                            Name = Get-EntityName -UnidRef $armorRef -UnidMap $unidMap
                            Relationship = 'Uses'
                        }
                    }
                }
                
                # Find sovereign references (uses)
                $sovereignPattern = '(?:sovereign|defaultSovereign)\s*=\s*"([^"]+)"'
                $sovereignMatches = [regex]::Matches($text, $sovereignPattern, 'IgnoreCase')
                foreach ($m in $sovereignMatches) {
                    $sovereignRef = $m.Groups[1].Value
                    $sovereignUnid = Resolve-UnidValue -UnidRef $sovereignRef -UnidMap $unidMap
                    if ($sovereignUnid) {
                        $references.Uses += [PSCustomObject]@{
                            UNID = $sovereignUnid
                            Name = Get-EntityName -UnidRef $sovereignRef -UnidMap $unidMap
                            Relationship = 'Uses'
                        }
                    }
                }
                
                # Find spawn references (spawns)
                $spawnPattern = '(?:class|table)\s*=\s*"([^"]+)"'
                $spawnMatches = [regex]::Matches($text, $spawnPattern, 'IgnoreCase')
                foreach ($m in $spawnMatches) {
                    $spawnRef = $m.Groups[1].Value
                    $spawnUnid = Resolve-UnidValue -UnidRef $spawnRef -UnidMap $unidMap
                    if ($spawnUnid) {
                        $references.Spawns += [PSCustomObject]@{
                            UNID = $spawnUnid
                            Name = Get-EntityName -UnidRef $spawnRef -UnidMap $unidMap
                            Relationship = 'Spawns'
                        }
                    }
                }
                
                break
            }
        }
    }
    
    return $references
}

function Get-ReverseReferences {
    param(
        [string]$Unid,
        [string[]]$Files,
        [hashtable]$UnidMap
    )
    
    $reverseRefs = @()
    
    foreach ($file in $Files) {
        $text = [System.IO.File]::ReadAllText($file, [System.Text.Encoding]::UTF8)
        
        # Find all type definitions
        $typePattern = '<(ItemType|ShipClass|StationType)[^>]+UNID\s*=\s*"([^"]+)"'
        $typeMatches = [regex]::Matches($text, $typePattern, 'IgnoreCase')
        
        foreach ($typeMatch in $typeMatches) {
            $typeUnidRef = $typeMatch.Groups[2].Value
            $typeUnidValue = Resolve-UnidValue -UnidRef $typeUnidRef -UnidMap $unidMap
            
            if ($typeUnidValue -ne $Unid) {
                # Check if this type references our target UNID
                $typeName = Get-EntityName -UnidRef $typeUnidRef -UnidMap $unidMap
                
                # Check inherit
                $inheritMatch = [regex]::Match($typeMatch.Value, 'inherit\s*=\s*"([^"]+)"', 'IgnoreCase')
                if ($inheritMatch.Success) {
                    $inheritRef = $inheritMatch.Groups[1].Value
                    $inheritUnid = Resolve-UnidValue -UnidRef $inheritRef -UnidMap $unidMap
                    if ($inheritUnid -eq $Unid) {
                        $reverseRefs += [PSCustomObject]@{
                            UNID = $typeUnidValue
                            Name = $typeName
                            Type = $typeMatch.Groups[1].Value
                            Relationship = 'Inherited by'
                        }
                    }
                }
                
                # Check device/item references
                $devicePattern = '<Device[^>]+(?:deviceID|item)\s*=\s*"([^"]+)"'
                $deviceMatches = [regex]::Matches($text, $devicePattern, 'IgnoreCase')
                foreach ($m in $deviceMatches) {
                    $deviceRef = $m.Groups[1].Value
                    $deviceUnid = Resolve-UnidValue -UnidRef $deviceRef -UnidMap $unidMap
                    if ($deviceUnid -eq $Unid) {
                        $reverseRefs += [PSCustomObject]@{
                            UNID = $typeUnidValue
                            Name = $typeName
                            Type = $typeMatch.Groups[1].Value
                            Relationship = 'Used by'
                        }
                    }
                }
                
                # Check weapon references
                $weaponPattern = '<Weapon[^>]+type\s*=\s*"([^"]+)"'
                $weaponMatches = [regex]::Matches($text, $weaponPattern, 'IgnoreCase')
                foreach ($m in $weaponMatches) {
                    $weaponRef = $m.Groups[1].Value
                    $weaponUnid = Resolve-UnidValue -UnidRef $weaponRef -UnidMap $unidMap
                    if ($weaponUnid -eq $Unid) {
                        $reverseRefs += [PSCustomObject]@{
                            UNID = $typeUnidValue
                            Name = $typeName
                            Type = $typeMatch.Groups[1].Value
                            Relationship = 'Used by'
                        }
                    }
                }
                
                # Check armor references
                $armorPattern = '<Armor[^>]+armorID\s*=\s*"([^"]+)"'
                $armorMatches = [regex]::Matches($text, $armorPattern, 'IgnoreCase')
                foreach ($m in $armorMatches) {
                    $armorRef = $m.Groups[1].Value
                    $armorUnid = Resolve-UnidValue -UnidRef $armorRef -UnidMap $unidMap
                    if ($armorUnid -eq $Unid) {
                        $reverseRefs += [PSCustomObject]@{
                            UNID = $typeUnidValue
                            Name = $typeName
                            Type = $typeMatch.Groups[1].Value
                            Relationship = 'Used by'
                        }
                    }
                }
                
                # Check spawn references
                $spawnPattern = '(?:class|table)\s*=\s*"([^"]+)"'
                $spawnMatches = [regex]::Matches($text, $spawnPattern, 'IgnoreCase')
                foreach ($m in $spawnMatches) {
                    $spawnRef = $m.Groups[1].Value
                    $spawnUnid = Resolve-UnidValue -UnidRef $spawnRef -UnidMap $unidMap
                    if ($spawnUnid -eq $Unid) {
                        $reverseRefs += [PSCustomObject]@{
                            UNID = $typeUnidValue
                            Name = $typeName
                            Type = $typeMatch.Groups[1].Value
                            Relationship = 'Spawned by'
                        }
                    }
                }
            }
        }
    }
    
    return $reverseRefs
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

function Format-LivePreview {
    param([PSCustomObject]$Preview)
    
    if (-not $Preview) {
        return 'Type not found'
    }
    
    $output = [System.Text.StringBuilder]::new()
    [void]$output.AppendLine('═══════════════════════════════════════════════════════════')
    [void]$output.AppendLine('              LIVE PREVIEW OF RESOLVED TYPE')
    [void]$output.AppendLine('═══════════════════════════════════════════════════════════')
    [void]$output.AppendLine('')
    [void]$output.AppendLine("Type:      $($Preview.Type)")
    [void]$output.AppendLine("Name:      $($Preview.Name)")
    [void]$output.AppendLine("UNID:      $($Preview.UNID)")
    [void]$output.AppendLine("File:      $(Split-Path -Leaf $Preview.File)")
    [void]$output.AppendLine('')
    
    # Resolved Attributes
    [void]$output.AppendLine('═══════════════════════════════════════════════════════════')
    [void]$output.AppendLine('                    RESOLVED ATTRIBUTES')
    [void]$output.AppendLine('═══════════════════════════════════════════════════════════')
    [void]$output.AppendLine('')
    
    if ($Preview.ResolvedAttributes.Count -eq 0) {
        [void]$output.AppendLine('  (No attributes)')
    }
    else {
        foreach ($attr in ($Preview.ResolvedAttributes.Keys | Sort-Object)) {
            $source = if ($Preview.AttributeSources.ContainsKey($attr)) { $Preview.AttributeSources[$attr] } else { 'Unknown' }
            [void]$output.AppendLine("  $attr = $($Preview.ResolvedAttributes[$attr])")
            [void]$output.AppendLine("    Source: $source")
            [void]$output.AppendLine('')
        }
    }
    
    # Conflicts
    if ($Preview.Conflicts.Count -gt 0) {
        [void]$output.AppendLine('═══════════════════════════════════════════════════════════')
        [void]$output.AppendLine('                    OVERRIDE CONFLICTS')
        [void]$output.AppendLine('═══════════════════════════════════════════════════════════')
        [void]$output.AppendLine('')
        
        foreach ($conflict in $Preview.Conflicts) {
            [void]$output.AppendLine("  ⚠ $($conflict.Attribute)")
            [void]$output.AppendLine("    Parent: $($conflict.ParentValue)")
            [void]$output.AppendLine("    Child:  $($conflict.ChildValue)")
            [void]$output.AppendLine("    Source: $($conflict.Source)")
            [void]$output.AppendLine('')
        }
    }
    
    # Events
    [void]$output.AppendLine('═══════════════════════════════════════════════════════════')
    [void]$output.AppendLine('                         EVENTS')
    [void]$output.AppendLine('═══════════════════════════════════════════════════════════')
    [void]$output.AppendLine('')
    
    if ($Preview.Events.Count -eq 0) {
        [void]$output.AppendLine('  (No events)')
    }
    else {
        foreach ($event in ($Preview.Events | Sort-Object)) {
            $source = if ($Preview.EventSources.ContainsKey($event)) { $Preview.EventSources[$event] } else { 'Unknown' }
            [void]$output.AppendLine("  $event")
            [void]$output.AppendLine("    Source: $source")
            [void]$output.AppendLine('')
        }
    }
    
    # Resources
    [void]$output.AppendLine('═══════════════════════════════════════════════════════════')
    [void]$output.AppendLine('                        RESOURCES')
    [void]$output.AppendLine('═══════════════════════════════════════════════════════════')
    [void]$output.AppendLine('')
    
    if ($Preview.Resources.Images.Count -eq 0 -and $Preview.Resources.Sounds.Count -eq 0 -and $Preview.Resources.Icons.Count -eq 0) {
        [void]$output.AppendLine('  (No resources)')
    }
    else {
        if ($Preview.Resources.Images.Count -gt 0) {
            [void]$output.AppendLine('  Images:')
            foreach ($img in $Preview.Resources.Images) {
                [void]$output.AppendLine("    - $img")
            }
            [void]$output.AppendLine('')
        }
        
        if ($Preview.Resources.Sounds.Count -gt 0) {
            [void]$output.AppendLine('  Sounds:')
            foreach ($snd in $Preview.Resources.Sounds) {
                [void]$output.AppendLine("    - $snd")
            }
            [void]$output.AppendLine('')
        }
        
        if ($Preview.Resources.Icons.Count -gt 0) {
            [void]$output.AppendLine('  Icons:')
            foreach ($icon in $Preview.Resources.Icons) {
                [void]$output.AppendLine("    - $icon")
            }
            [void]$output.AppendLine('')
        }
    }
    
    # References (types this type uses)
    [void]$output.AppendLine('═══════════════════════════════════════════════════════════')
    [void]$output.AppendLine('                      REFERENCES')
    [void]$output.AppendLine('═══════════════════════════════════════════════════════════')
    [void]$output.AppendLine('')
    
    $hasRefs = $false
    if ($Preview.References.Inherits.Count -gt 0) {
        [void]$output.AppendLine('  Inherits:')
        foreach ($ref in $Preview.References.Inherits) {
            [void]$output.AppendLine("    - $($ref.Name) ($($ref.UNID))")
        }
        [void]$output.AppendLine('')
        $hasRefs = $true
    }
    
    if ($Preview.References.Uses.Count -gt 0) {
        [void]$output.AppendLine('  Uses:')
        foreach ($ref in $Preview.References.Uses) {
            [void]$output.AppendLine("    - $($ref.Name) ($($ref.UNID))")
        }
        [void]$output.AppendLine('')
        $hasRefs = $true
    }
    
    if ($Preview.References.Spawns.Count -gt 0) {
        [void]$output.AppendLine('  Spawns:')
        foreach ($ref in $Preview.References.Spawns) {
            [void]$output.AppendLine("    - $($ref.Name) ($($ref.UNID))")
        }
        [void]$output.AppendLine('')
        $hasRefs = $true
    }
    
    if (-not $hasRefs) {
        [void]$output.AppendLine('  (No references)')
        [void]$output.AppendLine('')
    }
    
    # Referenced By (types that reference this type)
    [void]$output.AppendLine('═══════════════════════════════════════════════════════════')
    [void]$output.AppendLine('                    REFERENCED BY')
    [void]$output.AppendLine('═══════════════════════════════════════════════════════════')
    [void]$output.AppendLine('')
    
    if ($Preview.ReferencedBy.Count -eq 0) {
        [void]$output.AppendLine('  (Not referenced by any types)')
    }
    else {
        $byRel = $Preview.ReferencedBy | Group-Object Relationship
        foreach ($relGroup in $byRel) {
            [void]$output.AppendLine("  $($relGroup.Name):")
            foreach ($ref in $relGroup.Group) {
                [void]$output.AppendLine("    - $($ref.Name) [$($ref.Type)] ($($ref.UNID))")
            }
            [void]$output.AppendLine('')
        }
    }
    
    [void]$output.AppendLine('═══════════════════════════════════════════════════════════')
    
    return $output.ToString()
}

function Get-AllTypes {
    param([string[]]$Files)
    
    $types = [System.Collections.ArrayList]::new()
    $unidMap = @{}
    
    # Build UNID map
    foreach ($file in $Files) {
        $text = [System.IO.File]::ReadAllText($file, [System.Text.Encoding]::UTF8)
        $unidPattern = '<!ENTITY\s+(\w+)\s+"(0x[0-9A-Fa-f]+)"'
        $unidMatches = [regex]::Matches($text, $unidPattern, 'IgnoreCase')
        foreach ($m in $unidMatches) {
            $unidMap[$m.Groups[1].Value] = $m.Groups[2].Value
            $unidMap[$m.Groups[2].Value] = $m.Groups[1].Value
        }
    }
    
    foreach ($file in $Files) {
        $text = [System.IO.File]::ReadAllText($file, [System.Text.Encoding]::UTF8)
        
        # Find ItemTypes
        $itemPattern = '<ItemType[^>]+UNID\s*=\s*"([^"]+)"'
        $itemMatches = [regex]::Matches($text, $itemPattern, 'IgnoreCase')
        foreach ($m in $itemMatches) {
            $unidRef = $m.Groups[1].Value
            $unidValue = Resolve-UnidValue -UnidRef $unidRef -UnidMap $unidMap
            if ($unidValue) {
                [void]$types.Add([PSCustomObject]@{
                    UNID = $unidValue
                    Name = Get-EntityName -UnidRef $unidRef -UnidMap $unidMap
                    Type = 'ItemType'
                })
            }
        }
        
        # Find ShipClasses
        $shipPattern = '<ShipClass[^>]+UNID\s*=\s*"([^"]+)"'
        $shipMatches = [regex]::Matches($text, $shipPattern, 'IgnoreCase')
        foreach ($m in $shipMatches) {
            $unidRef = $m.Groups[1].Value
            $unidValue = Resolve-UnidValue -UnidRef $unidRef -UnidMap $unidMap
            if ($unidValue) {
                [void]$types.Add([PSCustomObject]@{
                    UNID = $unidValue
                    Name = Get-EntityName -UnidRef $unidRef -UnidMap $unidMap
                    Type = 'ShipClass'
                })
            }
        }
        
        # Find StationTypes
        $stationPattern = '<StationType[^>]+UNID\s*=\s*"([^"]+)"'
        $stationMatches = [regex]::Matches($text, $stationPattern, 'IgnoreCase')
        foreach ($m in $stationMatches) {
            $unidRef = $m.Groups[1].Value
            $unidValue = Resolve-UnidValue -UnidRef $unidRef -UnidMap $unidMap
            if ($unidValue) {
                [void]$types.Add([PSCustomObject]@{
                    UNID = $unidValue
                    Name = Get-EntityName -UnidRef $unidRef -UnidMap $unidMap
                    Type = 'StationType'
                })
            }
        }
        
        # Find Sovereigns
        $sovereignPattern = '<Sovereign[^>]+UNID\s*=\s*"([^"]+)"'
        $sovereignMatches = [regex]::Matches($text, $sovereignPattern, 'IgnoreCase')
        foreach ($m in $sovereignMatches) {
            $unidRef = $m.Groups[1].Value
            $unidValue = Resolve-UnidValue -UnidRef $unidRef -UnidMap $unidMap
            if ($unidValue) {
                [void]$types.Add([PSCustomObject]@{
                    UNID = $unidValue
                    Name = Get-EntityName -UnidRef $unidRef -UnidMap $unidMap
                    Type = 'Sovereign'
                })
            }
        }
        
        # Find Missions
        $missionPattern = '<MissionType[^>]+UNID\s*=\s*"([^"]+)"'
        $missionMatches = [regex]::Matches($text, $missionPattern, 'IgnoreCase')
        foreach ($m in $missionMatches) {
            $unidRef = $m.Groups[1].Value
            $unidValue = Resolve-UnidValue -UnidRef $unidRef -UnidMap $unidMap
            if ($unidValue) {
                [void]$types.Add([PSCustomObject]@{
                    UNID = $unidValue
                    Name = Get-EntityName -UnidRef $unidRef -UnidMap $unidMap
                    Type = 'MissionType'
                })
            }
        }
    }
    
    return $types
}

# Functions are available for dot-sourcing


<#
.SYNOPSIS
  Semantic Validation Module for Transcendence Mods
  
.DESCRIPTION
  Source-aware validation that understands Transcendence's engine structure:
  - Semantic validation (beyond syntax)
  - Inheritance & override resolution
  - Event flow analysis
  - Enhanced UNID intelligence
  - Resource integrity checking
  - TML static analysis
#>

# ============================================================
# SEMANTIC VALIDATION
# ============================================================

function Get-SemanticIssues {
    param([string[]]$Files)
    
    $issues = [System.Collections.ArrayList]::new()
    $typeRegistry = @{}
    $unidMap = @{}
    
    # First pass: Build type registry
    foreach ($file in $Files) {
        $text = [System.IO.File]::ReadAllText($file, [System.Text.Encoding]::UTF8)
        
        # Extract UNID definitions
        $unidPattern = '<!ENTITY\s+(\w+)\s+"(0x[0-9A-Fa-f]+)"'
        $unidMatches = [regex]::Matches($text, $unidPattern, 'IgnoreCase')
        foreach ($m in $unidMatches) {
            $unidMap[$m.Groups[1].Value] = $m.Groups[2].Value
            $unidMap[$m.Groups[2].Value] = $m.Groups[1].Value
        }
        
        # Register ItemTypes
        $itemPattern = '<ItemType[^>]+UNID\s*=\s*"([^"]+)"'
        $itemMatches = [regex]::Matches($text, $itemPattern, 'IgnoreCase')
        foreach ($m in $itemMatches) {
            $unidRef = $m.Groups[1].Value
            $unidValue = Resolve-UnidValue -UnidRef $unidRef -UnidMap $unidMap
            $typeRegistry[$unidValue] = @{
                Type = 'ItemType'
                UNID = $unidValue
                Name = Get-EntityName -UnidRef $unidRef -UnidMap $unidMap
                File = $file
            }
        }
        
        # Register ShipClasses
        $shipPattern = '<ShipClass[^>]+UNID\s*=\s*"([^"]+)"'
        $shipMatches = [regex]::Matches($text, $shipPattern, 'IgnoreCase')
        foreach ($m in $shipMatches) {
            $unidRef = $m.Groups[1].Value
            $unidValue = Resolve-UnidValue -UnidRef $unidRef -UnidMap $unidMap
            $typeRegistry[$unidValue] = @{
                Type = 'ShipClass'
                UNID = $unidValue
                Name = Get-EntityName -UnidRef $unidRef -UnidMap $unidMap
                File = $file
            }
        }
        
        # Register StationTypes
        $stationPattern = '<StationType[^>]+UNID\s*=\s*"([^"]+)"'
        $stationMatches = [regex]::Matches($text, $stationPattern, 'IgnoreCase')
        foreach ($m in $stationMatches) {
            $unidRef = $m.Groups[1].Value
            $unidValue = Resolve-UnidValue -UnidRef $unidRef -UnidMap $unidMap
            $typeRegistry[$unidValue] = @{
                Type = 'StationType'
                UNID = $unidValue
                Name = Get-EntityName -UnidRef $unidRef -UnidMap $unidMap
                File = $file
            }
        }
        
        # Register ArmorClasses (ItemType with Armor element)
        $armorPattern = '<ItemType[^>]+UNID\s*=\s*"([^"]+)"[^>]*>.*?<Armor'
        $armorMatches = [regex]::Matches($text, $armorPattern, [System.Text.RegularExpressions.RegexOptions]::Singleline -bor [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
        foreach ($m in $armorMatches) {
            $unidRef = $m.Groups[1].Value
            $unidValue = Resolve-UnidValue -UnidRef $unidRef -UnidMap $unidMap
            if (-not $typeRegistry.ContainsKey($unidValue)) {
                $typeRegistry[$unidValue] = @{
                    Type = 'ArmorClass'
                    UNID = $unidValue
                    Name = Get-EntityName -UnidRef $unidRef -UnidMap $unidMap
                    File = $file
                }
            }
            else {
                $typeRegistry[$unidValue].Type = 'ItemType/ArmorClass'
            }
        }
    }
    
    # Second pass: Validate references
    foreach ($file in $Files) {
        $text = [System.IO.File]::ReadAllText($file, [System.Text.Encoding]::UTF8)
        $lines = $text -split "`r?`n"
        
        # Check ShipClass armor references
        $shipPattern = '<ShipClass[^>]+UNID\s*=\s*"([^"]+)"'
        $shipMatches = [regex]::Matches($text, $shipPattern, 'IgnoreCase')
        foreach ($m in $shipMatches) {
            $shipUnidRef = $m.Groups[1].Value
            $shipUnid = Resolve-UnidValue -UnidRef $shipUnidRef -UnidMap $unidMap
            
            # Check Armor references
            $armorRefPattern = 'armorID\s*=\s*"([^"]+)"'
            $armorRefMatches = [regex]::Matches($text, $armorRefPattern, 'IgnoreCase')
            foreach ($arm in $armorRefMatches) {
                $armorRef = $arm.Groups[1].Value
                $armorUnid = Resolve-UnidValue -UnidRef $armorRef -UnidMap $unidMap
                
                if ($armorUnid -and -not $typeRegistry.ContainsKey($armorUnid)) {
                    $lineNum = Get-LineNumber -Text $text -Position $arm.Index
                    [void]$issues.Add([PSCustomObject]@{
                        File = $file
                        Line = $lineNum
                        Severity = 'Error'
                        Code = 'SEMANTIC_MISSING_ARMOR'
                        Message = "ShipClass '$shipUnidRef' references nonexistent ArmorClass '$armorRef'"
                        Category = 'Semantic Validation'
                    })
                }
            }
            
            # Check ArmorSection references
            $armorSectionPattern = '<ArmorSection[^>]+armorID\s*=\s*"([^"]+)"'
            $armorSectionMatches = [regex]::Matches($text, $armorSectionPattern, 'IgnoreCase')
            foreach ($as in $armorSectionMatches) {
                $armorRef = $as.Groups[1].Value
                $armorUnid = Resolve-UnidValue -UnidRef $armorRef -UnidMap $unidMap
                
                if ($armorUnid -and -not $typeRegistry.ContainsKey($armorUnid)) {
                    $lineNum = Get-LineNumber -Text $text -Position $as.Index
                    [void]$issues.Add([PSCustomObject]@{
                        File = $file
                        Line = $lineNum
                        Severity = 'Error'
                        Code = 'SEMANTIC_MISSING_ARMOR'
                        Message = "ArmorSection references nonexistent ArmorClass '$armorRef'"
                        Category = 'Semantic Validation'
                    })
                }
            }
        }
        
        # Check StationType armor references
        $stationPattern = '<StationType[^>]+UNID\s*=\s*"([^"]+)"'
        $stationMatches = [regex]::Matches($text, $stationPattern, 'IgnoreCase')
        foreach ($m in $stationMatches) {
            $stationUnidRef = $m.Groups[1].Value
            $stationUnid = Resolve-UnidValue -UnidRef $stationUnidRef -UnidMap $unidMap
            
            # Check armorID references
            $armorRefPattern = 'armorID\s*=\s*"([^"]+)"'
            $armorRefMatches = [regex]::Matches($text, $armorRefPattern, 'IgnoreCase')
            foreach ($arm in $armorRefMatches) {
                $armorRef = $arm.Groups[1].Value
                $armorUnid = Resolve-UnidValue -UnidRef $armorRef -UnidMap $unidMap
                
                if ($armorUnid -and -not $typeRegistry.ContainsKey($armorUnid)) {
                    $lineNum = Get-LineNumber -Text $text -Position $arm.Index
                    [void]$issues.Add([PSCustomObject]@{
                        File = $file
                        Line = $lineNum
                        Severity = 'Error'
                        Code = 'SEMANTIC_MISSING_ARMOR'
                        Message = "StationType '$stationUnidRef' references nonexistent ArmorClass '$armorRef'"
                        Category = 'Semantic Validation'
                    })
                }
            }
        }
        
        # Check Device references
        $devicePattern = '<Device[^>]+(?:deviceID|item)\s*=\s*"([^"]+)"'
        $deviceMatches = [regex]::Matches($text, $devicePattern, 'IgnoreCase')
        foreach ($dm in $deviceMatches) {
            $deviceRef = $dm.Groups[1].Value
            $deviceUnid = Resolve-UnidValue -UnidRef $deviceRef -UnidMap $unidMap
            
            if ($deviceUnid -and -not $typeRegistry.ContainsKey($deviceUnid)) {
                $lineNum = Get-LineNumber -Text $text -Position $dm.Index
                [void]$issues.Add([PSCustomObject]@{
                    File = $file
                    Line = $lineNum
                    Severity = 'Error'
                    Code = 'SEMANTIC_MISSING_DEVICE'
                    Message = "Device references nonexistent ItemType '$deviceRef'"
                    Category = 'Semantic Validation'
                })
            }
        }
        
        # Check Weapon type references
        $weaponPattern = '<Weapon[^>]+type\s*=\s*"([^"]+)"'
        $weaponMatches = [regex]::Matches($text, $weaponPattern, 'IgnoreCase')
        foreach ($wm in $weaponMatches) {
            $weaponRef = $wm.Groups[1].Value
            $weaponUnid = Resolve-UnidValue -UnidRef $weaponRef -UnidMap $unidMap
            
            if ($weaponUnid -and -not $typeRegistry.ContainsKey($weaponUnid)) {
                $lineNum = Get-LineNumber -Text $text -Position $wm.Index
                [void]$issues.Add([PSCustomObject]@{
                    File = $file
                    Line = $lineNum
                    Severity = 'Error'
                    Code = 'SEMANTIC_MISSING_WEAPON'
                    Message = "Weapon references nonexistent weapon type '$weaponRef'"
                    Category = 'Semantic Validation'
                })
            }
        }
        
        # Check inherit references
        $inheritPattern = 'inherit\s*=\s*"([^"]+)"'
        $inheritMatches = [regex]::Matches($text, $inheritPattern, 'IgnoreCase')
        foreach ($im in $inheritMatches) {
            $inheritRef = $im.Groups[1].Value
            $inheritUnid = Resolve-UnidValue -UnidRef $inheritRef -UnidMap $unidMap
            
            if ($inheritUnid -and -not $typeRegistry.ContainsKey($inheritUnid)) {
                $lineNum = Get-LineNumber -Text $text -Position $im.Index
                [void]$issues.Add([PSCustomObject]@{
                    File = $file
                    Line = $lineNum
                    Severity = 'Warning'
                    Code = 'SEMANTIC_MISSING_INHERIT'
                    Message = "Type inherits from nonexistent type '$inheritRef' (may be base game type)"
                    Category = 'Semantic Validation'
                })
            }
        }
    }
    
    return $issues
}

# ============================================================
# INHERITANCE & OVERRIDE RESOLUTION
# ============================================================

function Get-InheritanceTree {
    param([string[]]$Files)
    
    $types = @{}
    $unidMap = @{}
    
    # Build type registry with inheritance info
    foreach ($file in $Files) {
        $text = [System.IO.File]::ReadAllText($file, [System.Text.Encoding]::UTF8)
        
        # Extract UNID definitions
        $unidPattern = '<!ENTITY\s+(\w+)\s+"(0x[0-9A-Fa-f]+)"'
        $unidMatches = [regex]::Matches($text, $unidPattern, 'IgnoreCase')
        foreach ($m in $unidMatches) {
            $unidMap[$m.Groups[1].Value] = $m.Groups[2].Value
            $unidMap[$m.Groups[2].Value] = $m.Groups[1].Value
        }
        
        # Find types with inheritance
        $typePattern = '<(ItemType|ShipClass|StationType)[^>]+UNID\s*=\s*"([^"]+)"[^>]*>'
        $typeMatches = [regex]::Matches($text, $typePattern, 'IgnoreCase')
        
        foreach ($m in $typeMatches) {
            $typeName = $m.Groups[1].Value
            $unidRef = $m.Groups[2].Value
            $unidValue = Resolve-UnidValue -UnidRef $unidRef -UnidMap $unidMap
            
            # Check for inherit attribute
            $inheritMatch = [regex]::Match($m.Value, 'inherit\s*=\s*"([^"]+)"', 'IgnoreCase')
            $inheritRef = if ($inheritMatch.Success) { $inheritMatch.Groups[1].Value } else { $null }
            
            $types[$unidValue] = [PSCustomObject]@{
                Type = $typeName
                UNID = $unidValue
                Name = Get-EntityName -UnidRef $unidRef -UnidMap $unidMap
                Inherits = if ($inheritRef) { Resolve-UnidValue -UnidRef $inheritRef -UnidMap $unidMap } else { $null }
                InheritRef = $inheritRef
                File = $file
            }
        }
    }
    
    # Build inheritance tree
    $tree = @{}
    foreach ($unid in $types.Keys) {
        $type = $types[$unid]
        $tree[$unid] = @{
            Type = $type
            Children = @()
            Parents = @()
        }
    }
    
    # Link parent-child relationships
    foreach ($unid in $tree.Keys) {
        $type = $tree[$unid].Type
        if ($type.Inherits) {
            if ($tree.ContainsKey($type.Inherits)) {
                $tree[$unid].Parents += $tree[$type.Inherits]
                $tree[$type.Inherits].Children += $tree[$unid]
            }
        }
    }
    
    return $tree
}

function Get-ResolvedType {
    param(
        [string]$Unid,
        [hashtable]$InheritanceTree,
        [hashtable]$TypeRegistry,
        [string[]]$Files
    )
    
    if (-not $InheritanceTree.ContainsKey($Unid)) {
        return $null
    }
    
    $type = $InheritanceTree[$Unid].Type
    $resolved = [PSCustomObject]@{
        UNID = $type.UNID
        Name = $type.Name
        Type = $type.Type
        Attributes = @{}
        AttributeSources = @{}  # Track where each attribute comes from
        Events = @()
        EventSources = @{}  # Track where each event comes from
        Inherits = $type.Inherits
        InheritChain = @()
        Conflicts = @()
        File = $type.File
    }
    
    # Build inheritance chain
    $chain = @()
    $current = $type
    while ($current.Inherits -and $InheritanceTree.ContainsKey($current.Inherits)) {
        $chain += $current.Inherits
        $current = $InheritanceTree[$current.Inherits].Type
    }
    $resolved.InheritChain = $chain
    
    # Parse attributes from all files
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
    }
    
    # Parse attributes from parent types first (bottom-up)
    $parentChain = $chain.Clone()
    [array]::Reverse($parentChain)
    foreach ($parentUnid in $parentChain) {
        if ($InheritanceTree.ContainsKey($parentUnid)) {
            $parentType = $InheritanceTree[$parentUnid].Type
            $parentAttrs = Get-TypeAttributes -Unid $parentUnid -Files $Files -UnidMap $unidMap
            
            foreach ($attr in $parentAttrs.Keys) {
                if (-not $resolved.Attributes.ContainsKey($attr)) {
                    $resolved.Attributes[$attr] = $parentAttrs[$attr]
                    $resolved.AttributeSources[$attr] = "Parent: $($parentType.Name)"
                }
            }
        }
    }
    
    # Parse attributes from current type (overrides parent)
    $currentAttrs = Get-TypeAttributes -Unid $Unid -Files $Files -UnidMap $unidMap
    foreach ($attr in $currentAttrs.Keys) {
        # Check for conflicts
        if ($resolved.Attributes.ContainsKey($attr)) {
            $oldValue = $resolved.Attributes[$attr]
            $newValue = $currentAttrs[$attr]
            if ($oldValue -ne $newValue) {
                $resolved.Conflicts += [PSCustomObject]@{
                    Attribute = $attr
                    ParentValue = $oldValue
                    ChildValue = $newValue
                    Source = $resolved.AttributeSources[$attr]
                }
            }
        }
        
        $resolved.Attributes[$attr] = $currentAttrs[$attr]
        $resolved.AttributeSources[$attr] = "Self: $($type.Name)"
    }
    
    # Parse events
    $currentEvents = Get-TypeEvents -Unid $Unid -Files $Files -UnidMap $unidMap
    foreach ($event in $currentEvents) {
        $resolved.Events += $event
        $resolved.EventSources[$event] = "Self: $($type.Name)"
    }
    
    # Get events from parents
    foreach ($parentUnid in $parentChain) {
        if ($InheritanceTree.ContainsKey($parentUnid)) {
            $parentType = $InheritanceTree[$parentUnid].Type
            $parentEvents = Get-TypeEvents -Unid $parentUnid -Files $Files -UnidMap $unidMap
            
            foreach ($event in $parentEvents) {
                if (-not $resolved.Events.Contains($event)) {
                    $resolved.Events += $event
                    $resolved.EventSources[$event] = "Parent: $($parentType.Name)"
                }
            }
        }
    }
    
    return $resolved
}

function Get-TypeAttributes {
    param(
        [string]$Unid,
        [string[]]$Files,
        [hashtable]$UnidMap
    )
    
    $attributes = @{}
    
    foreach ($file in $Files) {
        $text = [System.IO.File]::ReadAllText($file, [System.Text.Encoding]::UTF8)
        
        # Find type definition
        $typePattern = '<(ItemType|ShipClass|StationType|StationTypeOverride)[^>]+UNID\s*=\s*"([^"]+)"'
        $typeMatches = [regex]::Matches($text, $typePattern, 'IgnoreCase')
        
        foreach ($m in $typeMatches) {
            $unidRef = $m.Groups[2].Value
            $unidValue = Resolve-UnidValue -UnidRef $unidRef -UnidMap $unidMap
            
            if ($unidValue -eq $Unid) {
                # Extract all attributes from the tag
                $tagContent = $m.Value
                $attrPattern = '(\w+)\s*=\s*"([^"]*)"'
                $attrMatches = [regex]::Matches($tagContent, $attrPattern, 'IgnoreCase')
                
                foreach ($am in $attrMatches) {
                    $attrName = $am.Groups[1].Value
                    $attrValue = $am.Groups[2].Value
                    
                    # Skip UNID attribute
                    if ($attrName -ne 'UNID') {
                        $attributes[$attrName] = $attrValue
                    }
                }
                
                break
            }
        }
    }
    
    return $attributes
}

function Get-TypeEvents {
    param(
        [string]$Unid,
        [string[]]$Files,
        [hashtable]$UnidMap
    )
    
    $events = @()
    
    foreach ($file in $Files) {
        $text = [System.IO.File]::ReadAllText($file, [System.Text.Encoding]::UTF8)
        
        # Find type definition
        $typePattern = '<(ItemType|ShipClass|StationType|StationTypeOverride)[^>]+UNID\s*=\s*"([^"]+)"'
        $typeMatch = [regex]::Match($text, $typePattern, 'IgnoreCase')
        
        if ($typeMatch.Success) {
            $unidRef = $typeMatch.Groups[2].Value
            $unidValue = Resolve-UnidValue -UnidRef $unidRef -UnidMap $unidMap
            
            if ($unidValue -eq $Unid) {
                # Find all event handlers
                $eventPattern = '<(On\w+)>'
                $eventMatches = [regex]::Matches($text, $eventPattern, 'IgnoreCase')
                
                foreach ($em in $eventMatches) {
                    $eventName = $em.Groups[1].Value
                    if (-not $events.Contains($eventName)) {
                        $events += $eventName
                    }
                }
                
                break
            }
        }
    }
    
    return $events
}

function Get-OverrideConflicts {
    param(
        [hashtable]$InheritanceTree,
        [string[]]$Files
    )
    
    $conflicts = [System.Collections.ArrayList]::new()
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
    
    # Check each type for override issues
    foreach ($unid in $InheritanceTree.Keys) {
        $node = $InheritanceTree[$unid]
        $type = $node.Type
        
        if ($type.Inherits) {
            $resolved = Get-ResolvedType -Unid $unid -InheritanceTree $InheritanceTree -TypeRegistry @{} -Files $Files
            
            # Check for problematic overrides
            foreach ($conflict in $resolved.Conflicts) {
                [void]$conflicts.Add([PSCustomObject]@{
                    Type = $type.Name
                    UNID = $unid
                    Attribute = $conflict.Attribute
                    ParentValue = $conflict.ParentValue
                    ChildValue = $conflict.ChildValue
                    Severity = 'Warning'
                    Message = "Type '$($type.Name)' overrides attribute '$($conflict.Attribute)' from parent (was: '$($conflict.ParentValue)', now: '$($conflict.ChildValue)')"
                    File = $type.File
                })
            }
            
            # Check for immutable attributes being overridden
            $immutableAttrs = @('immutable', 'virtual')
            foreach ($attr in $immutableAttrs) {
                if ($resolved.Attributes.ContainsKey($attr) -and $resolved.AttributeSources[$attr] -like "Self:*") {
                    $parentHasIt = $false
                    foreach ($parentUnid in $resolved.InheritChain) {
                        if ($InheritanceTree.ContainsKey($parentUnid)) {
                            $parentAttrs = Get-TypeAttributes -Unid $parentUnid -Files $Files -UnidMap $unidMap
                            if ($parentAttrs.ContainsKey($attr)) {
                                $parentHasIt = $true
                                break
                            }
                        }
                    }
                    
                    if ($parentHasIt) {
                        [void]$conflicts.Add([PSCustomObject]@{
                            Type = $type.Name
                            UNID = $unid
                            Attribute = $attr
                            Severity = 'Error'
                            Message = "Type '$($type.Name)' overrides immutable attribute '$attr' from parent - this may break parent's assumptions"
                            File = $type.File
                        })
                    }
                }
            }
        }
    }
    
    return $conflicts
}

# ============================================================
# EVENT FLOW ANALYZER
# ============================================================

# Known Transcendence events (engine calls these)
$script:KnownEvents = @{
    # Object lifecycle
    'OnCreate' = @{ Type = 'All'; Called = $true; Description = 'Called when object is created' }
    'OnDestroy' = @{ Type = 'All'; Called = $true; Description = 'Called when object is destroyed' }
    'OnUpdate' = @{ Type = 'All'; Called = $true; Description = 'Called every frame' }
    
    # Combat
    'OnFireWeapon' = @{ Type = 'ItemType'; Called = $true; Description = 'Called when weapon fires' }
    'OnDamage' = @{ Type = 'All'; Called = $true; Description = 'Called when object takes damage' }
    'OnDamageArmor' = @{ Type = 'All'; Called = $true; Description = 'Called when armor is damaged' }
    'OnDamageShields' = @{ Type = 'All'; Called = $true; Description = 'Called when shields are damaged' }
    'OnDestroyedByPlayer' = @{ Type = 'All'; Called = $true; Description = 'Called when destroyed by player' }
    
    # Ship events
    'OnDocked' = @{ Type = 'ShipClass'; Called = $true; Description = 'Called when ship docks' }
    'OnUndocked' = @{ Type = 'ShipClass'; Called = $true; Description = 'Called when ship undocks' }
    'OnOrdersChanged' = @{ Type = 'ShipClass'; Called = $true; Description = 'Called when ship orders change' }
    'OnEnteredSystem' = @{ Type = 'ShipClass'; Called = $true; Description = 'Called when ship enters system' }
    'OnLeftSystem' = @{ Type = 'ShipClass'; Called = $true; Description = 'Called when ship leaves system' }
    
    # Station events
    'OnPlayerEnteredSystem' = @{ Type = 'StationType'; Called = $true; Description = 'Called when player enters system' }
    'OnPlayerLeftSystem' = @{ Type = 'StationType'; Called = $true; Description = 'Called when player leaves system' }
    'OnPlayerDocked' = @{ Type = 'StationType'; Called = $true; Description = 'Called when player docks' }
    'OnPlayerUndocked' = @{ Type = 'StationType'; Called = $true; Description = 'Called when player undocks' }
    
    # Global events
    'OnGlobalObjAttacked' = @{ Type = 'All'; Called = $true; Description = 'Called when any object is attacked' }
    'OnGlobalObjDestroyed' = @{ Type = 'All'; Called = $true; Description = 'Called when any object is destroyed' }
    'OnGlobalUniverseCreated' = @{ Type = 'All'; Called = $true; Description = 'Called when universe is created' }
    'OnGlobalSystemCreated' = @{ Type = 'All'; Called = $true; Description = 'Called when system is created' }
    'OnGlobalSystemStarted' = @{ Type = 'All'; Called = $true; Description = 'Called when system starts' }
    
    # Item events
    'OnInstall' = @{ Type = 'ItemType'; Called = $true; Description = 'Called when item is installed' }
    'OnUninstall' = @{ Type = 'ItemType'; Called = $true; Description = 'Called when item is uninstalled' }
    'OnEnabled' = @{ Type = 'ItemType'; Called = $true; Description = 'Called when item is enabled' }
    'OnDisabled' = @{ Type = 'ItemType'; Called = $true; Description = 'Called when item is disabled' }
    
    # Object events
    'OnObjDestroyed' = @{ Type = 'All'; Called = $true; Description = 'Called when registered object is destroyed' }
    'OnObjDocked' = @{ Type = 'All'; Called = $true; Description = 'Called when registered object docks' }
    'OnObjEnteredGate' = @{ Type = 'All'; Called = $true; Description = 'Called when registered object enters gate' }
    
    # Mission events
    'OnMissionAccepted' = @{ Type = 'All'; Called = $true; Description = 'Called when mission is accepted' }
    'OnMissionCompleted' = @{ Type = 'All'; Called = $true; Description = 'Called when mission is completed' }
    'OnMissionFailed' = @{ Type = 'All'; Called = $true; Description = 'Called when mission fails' }
    
    # Trade events
    'OnTrade' = @{ Type = 'StationType'; Called = $true; Description = 'Called during trade' }
    'OnTradeCompleted' = @{ Type = 'StationType'; Called = $true; Description = 'Called when trade completes' }
    
    # Custom events (may not be called by engine)
    'OnEventHandlerInit' = @{ Type = 'All'; Called = $false; Description = 'Custom event - may not be called by engine' }
    'FireEvent' = @{ Type = 'All'; Called = $false; Description = 'Custom event - may not be called by engine' }
}

function Get-EventFlow {
    param([string[]]$Files)
    
    $events = @{}
    $unidMap = @{}
    $inheritanceTree = Get-InheritanceTree -Files $Files
    
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
        
        # Find all type definitions
        $typePattern = '<(ItemType|ShipClass|StationType|StationTypeOverride)[^>]+UNID\s*=\s*"([^"]+)"'
        $typeMatches = [regex]::Matches($text, $typePattern, 'IgnoreCase')
        
        foreach ($tm in $typeMatches) {
            $typeName = $tm.Groups[1].Value
            $unidRef = $tm.Groups[2].Value
            $unidValue = Resolve-UnidValue -UnidRef $unidRef -UnidMap $unidMap
            
            if (-not $events.ContainsKey($unidValue)) {
                $events[$unidValue] = @{
                    UNID = $unidValue
                    Name = Get-EntityName -UnidRef $unidRef -UnidMap $unidMap
                    Type = $typeName
                    EventHandlers = @()
                    EventHandlerDetails = @{}
                    InheritedEvents = @()
                    DuplicateEvents = @()
                    UnusedEvents = @()
                    File = $file
                }
            }
            
            # Find all event handlers in this type
            $eventPattern = '<(On\w+|FireEvent|Process\w+Event)>'
            $eventMatches = [regex]::Matches($text, $eventPattern, 'IgnoreCase')
            
            foreach ($em in $eventMatches) {
                $eventName = $em.Groups[1].Value
                
                # Check for duplicates
                if ($events[$unidValue].EventHandlers.Contains($eventName)) {
                    $events[$unidValue].DuplicateEvents += $eventName
                }
                else {
                    $events[$unidValue].EventHandlers += $eventName
                }
                
                # Get event details
                $lineNum = Get-LineNumber -Text $text -Position $em.Index
                $events[$unidValue].EventHandlerDetails[$eventName] = @{
                    Line = $lineNum
                    Source = 'Self'
                }
            }
        }
    }
    
    # Add inherited events
    foreach ($unid in $events.Keys) {
        if ($inheritanceTree.ContainsKey($unid)) {
            $node = $inheritanceTree[$unid]
            $type = $node.Type
            
            if ($type.Inherits) {
                $parentUnid = $type.Inherits
                if ($events.ContainsKey($parentUnid)) {
                    foreach ($parentEvent in $events[$parentUnid].EventHandlers) {
                        if (-not $events[$unid].EventHandlers.Contains($parentEvent)) {
                            $events[$unid].InheritedEvents += $parentEvent
                            $events[$unid].EventHandlerDetails[$parentEvent] = @{
                                Line = 0
                                Source = "Inherited from $($events[$parentUnid].Name)"
                            }
                        }
                    }
                }
            }
        }
    }
    
    # Check for unused events
    foreach ($unid in $events.Keys) {
        $typeInfo = $events[$unid]
        foreach ($eventName in $typeInfo.EventHandlers) {
            if ($script:KnownEvents.ContainsKey($eventName)) {
                $eventInfo = $script:KnownEvents[$eventName]
                if (-not $eventInfo.Called) {
                    $typeInfo.UnusedEvents += $eventName
                }
            }
            else {
                # Unknown event - likely custom, may not be called
                $typeInfo.UnusedEvents += $eventName
            }
        }
    }
    
    return $events
}

function Get-EventFlowReport {
    param([hashtable]$EventFlow)
    
    $report = [System.Collections.ArrayList]::new()
    
    foreach ($unid in $EventFlow.Keys | Sort-Object) {
        $typeInfo = $EventFlow[$unid]
        
        # Summary
        $report.Add([PSCustomObject]@{
            Type = 'Summary'
            TypeName = $typeInfo.Name
            UNID = $unid
            TotalEvents = $typeInfo.EventHandlers.Count
            ImplementedEvents = ($typeInfo.EventHandlers | Where-Object { $typeInfo.EventHandlerDetails[$_].Source -eq 'Self' }).Count
            InheritedEvents = $typeInfo.InheritedEvents.Count
            DuplicateEvents = $typeInfo.DuplicateEvents.Count
            UnusedEvents = $typeInfo.UnusedEvents.Count
            Details = ''
        })
        
        # Implemented events
        $implementedEvents = $typeInfo.EventHandlers | Where-Object { 
            $typeInfo.EventHandlerDetails.ContainsKey($_) -and 
            $typeInfo.EventHandlerDetails[$_].Source -eq 'Self' 
        }
        foreach ($event in $implementedEvents) {
            $known = $script:KnownEvents.ContainsKey($event)
            $called = if ($known) { $script:KnownEvents[$event].Called } else { $false }
            $status = if ($called) { '✓ Called by engine' } else { '⚠ May not be called' }
            
            $report.Add([PSCustomObject]@{
                Type = 'Implemented'
                TypeName = $typeInfo.Name
                UNID = $unid
                Event = $event
                Line = $typeInfo.EventHandlerDetails[$event].Line
                Status = $status
                Details = if ($known) { $script:KnownEvents[$event].Description } else { 'Custom event - may not be called by engine' }
            })
        }
        
        # Inherited events
        foreach ($event in $typeInfo.InheritedEvents) {
            $report.Add([PSCustomObject]@{
                Type = 'Inherited'
                TypeName = $typeInfo.Name
                UNID = $unid
                Event = $event
                Line = 0
                Status = 'Inherited'
                Details = $typeInfo.EventHandlerDetails[$event].Source
            })
        }
        
        # Duplicate events
        foreach ($event in $typeInfo.DuplicateEvents) {
            $report.Add([PSCustomObject]@{
                Type = 'Duplicate'
                TypeName = $typeInfo.Name
                UNID = $unid
                Event = $event
                Line = 0
                Status = '⚠ Duplicate handler'
                Details = 'Event handler defined multiple times - only last one will be used'
            })
        }
        
        # Unused events
        foreach ($event in $typeInfo.UnusedEvents) {
            $report.Add([PSCustomObject]@{
                Type = 'Unused'
                TypeName = $typeInfo.Name
                UNID = $unid
                Event = $event
                Line = $typeInfo.EventHandlerDetails[$event].Line
                Status = '⚠ May not be called'
                Details = if ($script:KnownEvents.ContainsKey($event)) { 'Known event but not called by engine' } else { 'Unknown event - likely custom and may not be called' }
            })
        }
    }
    
    return $report
}

# ============================================================
# HELPER FUNCTIONS
# ============================================================

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

function Get-LineNumber {
    param([string]$Text, [int]$Position)
    
    $before = $Text.Substring(0, $Position)
    return ([regex]::Matches($before, "`n")).Count + 1
}

# Export functions
# Functions are available for dot-sourcing


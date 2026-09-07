<#
.SYNOPSIS
  Enhanced Cross-File Dependency Graph Analyzer for Transcendence Mods
  
.DESCRIPTION
  Comprehensive dependency visualization:
  - ItemTypes, ShipClasses, StationTypes, Sovereigns, Encounters, Missions
  - Relationships: Uses, Spawns, Overrides, Inherits, Calls event on
#>

# ============================================================
# ENHANCED DEPENDENCY GRAPH ANALYZER
# ============================================================

function Get-DependencyGraph {
    param([string[]]$Files)
    
    $graph = @{
        ItemTypes = @{}
        ShipClasses = @{}
        StationTypes = @{}
        Sovereigns = @{}
        Encounters = @{}
        Missions = @{}
        Tables = @{}
        Relationships = [System.Collections.ArrayList]::new()
    }
    
    foreach ($file in $Files) {
        $text = [System.IO.File]::ReadAllText($file, [System.Text.Encoding]::UTF8)
        
        # Extract UNID definitions
        $unidPattern = '<!ENTITY\s+(\w+)\s+"(0x[0-9A-Fa-f]+)"'
        $unidMatches = [regex]::Matches($text, $unidPattern, 'IgnoreCase')
        $unidMap = @{}
        foreach ($m in $unidMatches) {
            $unidMap[$m.Groups[2].Value] = $m.Groups[1].Value
            $unidMap[$m.Groups[1].Value] = $m.Groups[2].Value
        }
        
        # Find ItemType definitions
        $itemPattern = '<ItemType[^>]+UNID\s*=\s*"([^"]+)"'
        $itemMatches = [regex]::Matches($text, $itemPattern, 'IgnoreCase')
        foreach ($m in $itemMatches) {
            $unidRef = $m.Groups[1].Value
            $unidValue = Resolve-Unid -UnidRef $unidRef -UnidMap $unidMap
            $itemName = Get-EntityName -UnidRef $unidRef -UnidMap $unidMap
            
            # Check for inherit
            $inheritMatch = [regex]::Match($m.Value, 'inherit\s*=\s*"([^"]+)"', 'IgnoreCase')
            if ($inheritMatch.Success) {
                $inheritRef = $inheritMatch.Groups[1].Value
                $inheritUnid = Resolve-Unid -UnidRef $inheritRef -UnidMap $unidMap
                [void]$graph.Relationships.Add([PSCustomObject]@{
                    From = $itemName
                    FromType = 'ItemType'
                    FromUNID = $unidValue
                    To = Get-EntityName -UnidRef $inheritRef -UnidMap $unidMap
                    ToType = 'ItemType'
                    ToUNID = $inheritUnid
                    Relationship = 'inherits'
                    File = $file
                })
            }
            
            # Find weapon references (uses)
            $weaponPattern = '<Weapon[^>]+type\s*=\s*"([^"]+)"'
            $weaponMatches = [regex]::Matches($text, $weaponPattern, 'IgnoreCase')
            foreach ($wm in $weaponMatches) {
                $weaponRef = $wm.Groups[1].Value
                $weaponUnid = Resolve-Unid -UnidRef $weaponRef -UnidMap $unidMap
                [void]$graph.Relationships.Add([PSCustomObject]@{
                    From = $itemName
                    FromType = 'ItemType'
                    FromUNID = $unidValue
                    To = Get-EntityName -UnidRef $weaponRef -UnidMap $unidMap
                    ToType = 'ItemType'
                    ToUNID = $weaponUnid
                    Relationship = 'uses'
                    File = $file
                })
            }
            
            # Find event handlers (calls event on)
            $eventPattern = '<(On\w+)>'
            $eventMatches = [regex]::Matches($text, $eventPattern, 'IgnoreCase')
            foreach ($em in $eventMatches) {
                # Check for objFireEvent, typFireEvent calls
                $eventBlock = Get-EventBlockContent -Text $text -EventMatch $em
                $fireEventPattern = '(?:obj|typ)FireEvent\s+([^\s\)]+)\s+["\']([^"\']+)["\']'
                $fireMatches = [regex]::Matches($eventBlock, $fireEventPattern, 'IgnoreCase')
                foreach ($fm in $fireMatches) {
                    $targetRef = $fm.Groups[1].Value
                    $eventName = $fm.Groups[2].Value
                    $targetUnid = Resolve-Unid -UnidRef $targetRef -UnidMap $unidMap
                    [void]$graph.Relationships.Add([PSCustomObject]@{
                        From = $itemName
                        FromType = 'ItemType'
                        FromUNID = $unidValue
                        To = Get-EntityName -UnidRef $targetRef -UnidMap $unidMap
                        ToType = 'ItemType'
                        ToUNID = $targetUnid
                        Relationship = 'calls_event_on'
                        EventName = $eventName
                        File = $file
                    })
                }
            }
            
            $graph.ItemTypes[$unidValue] = [PSCustomObject]@{
                Name = $itemName
                UNID = $unidValue
                Type = 'ItemType'
                File = $file
            }
        }
        
        # Find ShipClass definitions
        $shipPattern = '<ShipClass[^>]+UNID\s*=\s*"([^"]+)"'
        $shipMatches = [regex]::Matches($text, $shipPattern, 'IgnoreCase')
        foreach ($m in $shipMatches) {
            $unidRef = $m.Groups[1].Value
            $unidValue = Resolve-Unid -UnidRef $unidRef -UnidMap $unidMap
            $shipName = Get-EntityName -UnidRef $unidRef -UnidMap $unidMap
            
            # Check for inherit
            $inheritMatch = [regex]::Match($m.Value, 'inherit\s*=\s*"([^"]+)"', 'IgnoreCase')
            if ($inheritMatch.Success) {
                $inheritRef = $inheritMatch.Groups[1].Value
                $inheritUnid = Resolve-Unid -UnidRef $inheritRef -UnidMap $unidMap
                [void]$graph.Relationships.Add([PSCustomObject]@{
                    From = $shipName
                    FromType = 'ShipClass'
                    FromUNID = $unidValue
                    To = Get-EntityName -UnidRef $inheritRef -UnidMap $unidMap
                    ToType = 'ShipClass'
                    ToUNID = $inheritUnid
                    Relationship = 'inherits'
                    File = $file
                })
            }
            
            # Check for sovereign reference
            $sovereignMatch = [regex]::Match($m.Value, '(?:sovereign|defaultSovereign)\s*=\s*"([^"]+)"', 'IgnoreCase')
            if ($sovereignMatch.Success) {
                $sovereignRef = $sovereignMatch.Groups[1].Value
                $sovereignUnid = Resolve-Unid -UnidRef $sovereignRef -UnidMap $unidMap
                [void]$graph.Relationships.Add([PSCustomObject]@{
                    From = $shipName
                    FromType = 'ShipClass'
                    FromUNID = $unidValue
                    To = Get-EntityName -UnidRef $sovereignRef -UnidMap $unidMap
                    ToType = 'Sovereign'
                    ToUNID = $sovereignUnid
                    Relationship = 'uses'
                    File = $file
                })
            }
            
            # Find device references (uses)
            $devicePattern = '<Device[^>]+(?:deviceID|item)\s*=\s*"([^"]+)"'
            $deviceMatches = [regex]::Matches($text, $devicePattern, 'IgnoreCase')
            foreach ($dm in $deviceMatches) {
                $deviceRef = $dm.Groups[1].Value
                $deviceUnid = Resolve-Unid -UnidRef $deviceRef -UnidMap $unidMap
                [void]$graph.Relationships.Add([PSCustomObject]@{
                    From = $shipName
                    FromType = 'ShipClass'
                    FromUNID = $unidValue
                    To = Get-EntityName -UnidRef $deviceRef -UnidMap $unidMap
                    ToType = 'ItemType'
                    ToUNID = $deviceUnid
                    Relationship = 'uses'
                    File = $file
                })
            }
            
            # Find armor references (uses)
            $armorPattern = '<Armor[^>]+armorID\s*=\s*"([^"]+)"'
            $armorMatches = [regex]::Matches($text, $armorPattern, 'IgnoreCase')
            foreach ($am in $armorMatches) {
                $armorRef = $am.Groups[1].Value
                $armorUnid = Resolve-Unid -UnidRef $armorRef -UnidMap $unidMap
                [void]$graph.Relationships.Add([PSCustomObject]@{
                    From = $shipName
                    FromType = 'ShipClass'
                    FromUNID = $unidValue
                    To = Get-EntityName -UnidRef $armorRef -UnidMap $unidMap
                    ToType = 'ItemType'
                    ToUNID = $armorUnid
                    Relationship = 'uses'
                    File = $file
                })
            }
            
            # Find item references in <Items> (uses)
            $itemsPattern = '<Items>.*?</Items>'
            $itemsMatch = [regex]::Match($text, $itemsPattern, [System.Text.RegularExpressions.RegexOptions]::Singleline -bor [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
            if ($itemsMatch.Success) {
                $itemsContent = $itemsMatch.Value
                $itemRefPattern = 'item\s*=\s*"([^"]+)"'
                $itemRefMatches = [regex]::Matches($itemsContent, $itemRefPattern, 'IgnoreCase')
                foreach ($irm in $itemRefMatches) {
                    $itemRef = $irm.Groups[1].Value
                    $itemUnid = Resolve-Unid -UnidRef $itemRef -UnidMap $unidMap
                    [void]$graph.Relationships.Add([PSCustomObject]@{
                        From = $shipName
                        FromType = 'ShipClass'
                        FromUNID = $unidValue
                        To = Get-EntityName -UnidRef $itemRef -UnidMap $unidMap
                        ToType = 'ItemType'
                        ToUNID = $itemUnid
                        Relationship = 'uses'
                        File = $file
                    })
                }
            }
            
            $graph.ShipClasses[$unidValue] = [PSCustomObject]@{
                Name = $shipName
                UNID = $unidValue
                Type = 'ShipClass'
                File = $file
            }
        }
        
        # Find StationType definitions
        $stationPattern = '<StationType[^>]+UNID\s*=\s*"([^"]+)"'
        $stationMatches = [regex]::Matches($text, $stationPattern, 'IgnoreCase')
        foreach ($m in $stationMatches) {
            $unidRef = $m.Groups[1].Value
            $unidValue = Resolve-Unid -UnidRef $unidRef -UnidMap $unidMap
            $stationName = Get-EntityName -UnidRef $unidRef -UnidMap $unidMap
            
            # Check for inherit
            $inheritMatch = [regex]::Match($m.Value, 'inherit\s*=\s*"([^"]+)"', 'IgnoreCase')
            if ($inheritMatch.Success) {
                $inheritRef = $inheritMatch.Groups[1].Value
                $inheritUnid = Resolve-Unid -UnidRef $inheritRef -UnidMap $unidMap
                [void]$graph.Relationships.Add([PSCustomObject]@{
                    From = $stationName
                    FromType = 'StationType'
                    FromUNID = $unidValue
                    To = Get-EntityName -UnidRef $inheritRef -UnidMap $unidMap
                    ToType = 'StationType'
                    ToUNID = $inheritUnid
                    Relationship = 'inherits'
                    File = $file
                })
            }
            
            # Check for override
            if ($m.Value -match 'StationTypeOverride') {
                [void]$graph.Relationships.Add([PSCustomObject]@{
                    From = $stationName
                    FromType = 'StationType'
                    FromUNID = $unidValue
                    To = Get-EntityName -UnidRef $unidRef -UnidMap $unidMap
                    ToType = 'StationType'
                    ToUNID = $unidValue
                    Relationship = 'overrides'
                    File = $file
                })
            }
            
            # Check for sovereign reference (uses)
            $sovereignMatch = [regex]::Match($m.Value, 'sovereign\s*=\s*"([^"]+)"', 'IgnoreCase')
            if ($sovereignMatch.Success) {
                $sovereignRef = $sovereignMatch.Groups[1].Value
                $sovereignUnid = Resolve-Unid -UnidRef $sovereignRef -UnidMap $unidMap
                [void]$graph.Relationships.Add([PSCustomObject]@{
                    From = $stationName
                    FromType = 'StationType'
                    FromUNID = $unidValue
                    To = Get-EntityName -UnidRef $sovereignRef -UnidMap $unidMap
                    ToType = 'Sovereign'
                    ToUNID = $sovereignUnid
                    Relationship = 'uses'
                    File = $file
                })
            }
            
            # Find encounter definitions (spawns)
            $encounterPattern = '<Encounter[^>]*>'
            $encounterMatches = [regex]::Matches($text, $encounterPattern, 'IgnoreCase')
            if ($encounterMatches.Count -gt 0) {
                foreach ($em in $encounterMatches) {
                    [void]$graph.Relationships.Add([PSCustomObject]@{
                        From = $stationName
                        FromType = 'StationType'
                        FromUNID = $unidValue
                        To = 'Encounter'
                        ToType = 'Encounter'
                        ToUNID = ''
                        Relationship = 'spawns'
                        File = $file
                    })
                }
            }
            
            # Find ship references in <Ships> or <Reinforcements> (spawns)
            $shipsPattern = '<(?:Ships|Reinforcements)>.*?</(?:Ships|Reinforcements)>'
            $shipsMatch = [regex]::Match($text, $shipsPattern, [System.Text.RegularExpressions.RegexOptions]::Singleline -bor [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
            if ($shipsMatch.Success) {
                $shipsContent = $shipsMatch.Value
                
                # Find direct ship class references
                $shipClassPattern = 'class\s*=\s*"([^"]+)"'
                $shipClassMatches = [regex]::Matches($shipsContent, $shipClassPattern, 'IgnoreCase')
                foreach ($scm in $shipClassMatches) {
                    $shipRef = $scm.Groups[1].Value
                    $shipUnid = Resolve-Unid -UnidRef $shipRef -UnidMap $unidMap
                    [void]$graph.Relationships.Add([PSCustomObject]@{
                        From = $stationName
                        FromType = 'StationType'
                        FromUNID = $unidValue
                        To = Get-EntityName -UnidRef $shipRef -UnidMap $unidMap
                        ToType = 'ShipClass'
                        ToUNID = $shipUnid
                        Relationship = 'spawns'
                        File = $file
                    })
                }
                
                # Find table references
                $tablePattern = 'table\s*=\s*"([^"]+)"'
                $tableMatches = [regex]::Matches($shipsContent, $tablePattern, 'IgnoreCase')
                foreach ($tm in $tableMatches) {
                    $tableRef = $tm.Groups[1].Value
                    [void]$graph.Relationships.Add([PSCustomObject]@{
                        From = $stationName
                        FromType = 'StationType'
                        FromUNID = $unidValue
                        To = Get-EntityName -UnidRef $tableRef -UnidMap $unidMap
                        ToType = 'Table'
                        ToUNID = ''
                        Relationship = 'spawns'
                        File = $file
                    })
                }
            }
            
            $graph.StationTypes[$unidValue] = [PSCustomObject]@{
                Name = $stationName
                UNID = $unidValue
                Type = 'StationType'
                File = $file
            }
        }
        
        # Find Sovereign definitions
        $sovereignPattern = '<Sovereign[^>]+UNID\s*=\s*"([^"]+)"'
        $sovereignMatches = [regex]::Matches($text, $sovereignPattern, 'IgnoreCase')
        foreach ($m in $sovereignMatches) {
            $unidRef = $m.Groups[1].Value
            $unidValue = Resolve-Unid -UnidRef $unidRef -UnidMap $unidMap
            $sovereignName = Get-EntityName -UnidRef $unidRef -UnidMap $unidMap
            
            # Find relationships (uses)
            $relationshipPattern = '<Relationship[^>]+sovereign\s*=\s*"([^"]+)"'
            $relationshipMatches = [regex]::Matches($text, $relationshipPattern, 'IgnoreCase')
            foreach ($rm in $relationshipMatches) {
                $relatedRef = $rm.Groups[1].Value
                $relatedUnid = Resolve-Unid -UnidRef $relatedRef -UnidMap $unidMap
                [void]$graph.Relationships.Add([PSCustomObject]@{
                    From = $sovereignName
                    FromType = 'Sovereign'
                    FromUNID = $unidValue
                    To = Get-EntityName -UnidRef $relatedRef -UnidMap $unidMap
                    ToType = 'Sovereign'
                    ToUNID = $relatedUnid
                    Relationship = 'uses'
                    File = $file
                })
            }
            
            $graph.Sovereigns[$unidValue] = [PSCustomObject]@{
                Name = $sovereignName
                UNID = $unidValue
                Type = 'Sovereign'
                File = $file
            }
        }
        
        # Find MissionType definitions
        $missionPattern = '<MissionType[^>]+UNID\s*=\s*"([^"]+)"'
        $missionMatches = [regex]::Matches($text, $missionPattern, 'IgnoreCase')
        foreach ($m in $missionMatches) {
            $unidRef = $m.Groups[1].Value
            $unidValue = Resolve-Unid -UnidRef $unidRef -UnidMap $unidMap
            $missionName = Get-EntityName -UnidRef $unidRef -UnidMap $unidMap
            
            # Missions can reference stations, ships, items, etc. through events
            # This would require deeper analysis of mission event handlers
            
            $graph.Missions[$unidValue] = [PSCustomObject]@{
                Name = $missionName
                UNID = $unidValue
                Type = 'MissionType'
                File = $file
            }
        }
        
        # Find EncounterTable definitions
        $encounterTablePattern = '<(?:EncounterTable|ShipTable)[^>]+unid\s*=\s*"([^"]+)"'
        $encounterTableMatches = [regex]::Matches($text, $encounterTablePattern, 'IgnoreCase')
        foreach ($m in $encounterTableMatches) {
            $unidRef = $m.Groups[1].Value
            $unidValue = Resolve-Unid -UnidRef $unidRef -UnidMap $unidMap
            $tableName = Get-EntityName -UnidRef $unidRef -UnidMap $unidMap
            
            # Find ship/item references in table (spawns)
            $tableContent = Get-TableContent -Text $text -TableMatch $m
            $shipRefPattern = 'class\s*=\s*"([^"]+)"'
            $shipRefMatches = [regex]::Matches($tableContent, $shipRefPattern, 'IgnoreCase')
            foreach ($srm in $shipRefMatches) {
                $shipRef = $srm.Groups[1].Value
                $shipUnid = Resolve-Unid -UnidRef $shipRef -UnidMap $unidMap
                [void]$graph.Relationships.Add([PSCustomObject]@{
                    From = $tableName
                    FromType = 'Table'
                    FromUNID = $unidValue
                    To = Get-EntityName -UnidRef $shipRef -UnidMap $unidMap
                    ToType = 'ShipClass'
                    ToUNID = $shipUnid
                    Relationship = 'spawns'
                    File = $file
                })
            }
            
            $graph.Tables[$unidValue] = [PSCustomObject]@{
                Name = $tableName
                UNID = $unidValue
                Type = 'Table'
                File = $file
            }
        }
    }
    
    return $graph
}

function Get-EventBlockContent {
    param(
        [string]$Text,
        [System.Text.RegularExpressions.Match]$EventMatch
    )
    
    # Extract content between event tags
    $startPos = $EventMatch.Index
    $tagEnd = $Text.IndexOf('>', $startPos)
    if ($tagEnd -eq -1) { return '' }
    
    $endTag = "</$($EventMatch.Groups[1].Value)>"
    $endPos = $Text.IndexOf($endTag, $tagEnd)
    if ($endPos -eq -1) { return '' }
    
    return $Text.Substring($tagEnd + 1, $endPos - $tagEnd - 1)
}

function Get-TableContent {
    param(
        [string]$Text,
        [System.Text.RegularExpressions.Match]$TableMatch
    )
    
    # Extract content between table tags
    $startPos = $TableMatch.Index
    $tagEnd = $Text.IndexOf('>', $startPos)
    if ($tagEnd -eq -1) { return '' }
    
    # Find closing tag
    $tagName = if ($TableMatch.Value -match '<(\w+)') { $matches[1] } else { 'Table' }
    $endTag = "</$tagName>"
    $endPos = $Text.IndexOf($endTag, $tagEnd)
    if ($endPos -eq -1) { return '' }
    
    return $Text.Substring($tagEnd + 1, $endPos - $tagEnd - 1)
}

function Resolve-Unid {
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

function Format-DependencyGraph {
    param([hashtable]$Graph)
    
    $output = [System.Text.StringBuilder]::new()
    [void]$output.AppendLine('═══════════════════════════════════════════════════════════')
    [void]$output.AppendLine('              CROSS-FILE DEPENDENCY GRAPH')
    [void]$output.AppendLine('═══════════════════════════════════════════════════════════')
    [void]$output.AppendLine('')
    [void]$output.AppendLine('NODES:')
    [void]$output.AppendLine("  ItemTypes:      $($graph.ItemTypes.Count)")
    [void]$output.AppendLine("  ShipClasses:    $($graph.ShipClasses.Count)")
    [void]$output.AppendLine("  StationTypes:   $($graph.StationTypes.Count)")
    [void]$output.AppendLine("  Sovereigns:     $($graph.Sovereigns.Count)")
    [void]$output.AppendLine("  Missions:       $($graph.Missions.Count)")
    [void]$output.AppendLine("  Tables:         $($graph.Tables.Count)")
    [void]$output.AppendLine('')
    [void]$output.AppendLine("Total Relationships: $($graph.Relationships.Count)")
    [void]$output.AppendLine('')
    
    # Group by relationship type
    $byRelationship = $graph.Relationships | Group-Object Relationship
    
    foreach ($relGroup in $byRelationship | Sort-Object Name) {
        [void]$output.AppendLine('═══════════════════════════════════════════════════════════')
        [void]$output.AppendLine("$($relGroup.Name.ToUpper().Replace('_', ' '))")
        [void]$output.AppendLine('═══════════════════════════════════════════════════════════')
        [void]$output.AppendLine('')
        
        foreach ($rel in $relGroup.Group | Sort-Object FromType, From, To) {
            $eventInfo = if ($rel.EventName) { " (event: $($rel.EventName))" } else { '' }
            [void]$output.AppendLine("  $($rel.From) [$($rel.FromType)]")
            [void]$output.AppendLine("    → $($rel.To) [$($rel.ToType)]$eventInfo")
            [void]$output.AppendLine("")
        }
    }
    
    return $output.ToString()
}

function Get-DependencyGraphSummary {
    param([hashtable]$Graph)
    
    $summary = [PSCustomObject]@{
        TotalNodes = $graph.ItemTypes.Count + $graph.ShipClasses.Count + $graph.StationTypes.Count + $graph.Sovereigns.Count + $graph.Missions.Count + $graph.Tables.Count
        TotalRelationships = $graph.Relationships.Count
        RelationshipTypes = @{}
        NodeTypes = @{
            ItemTypes = $graph.ItemTypes.Count
            ShipClasses = $graph.ShipClasses.Count
            StationTypes = $graph.StationTypes.Count
            Sovereigns = $graph.Sovereigns.Count
            Missions = $graph.Missions.Count
            Tables = $graph.Tables.Count
        }
    }
    
    # Count relationship types
    $byRel = $graph.Relationships | Group-Object Relationship
    foreach ($relGroup in $byRel) {
        $summary.RelationshipTypes[$relGroup.Name] = $relGroup.Count
    }
    
    return $summary
}

# Functions are available for dot-sourcing


<#
.SYNOPSIS
  Migration Preview Mode - Show Resolved Types After Changes
  
.DESCRIPTION
  Preview how types will look after migration changes, showing:
  - Fully resolved attributes (after inheritance)
  - All events it implements
  - All resources it uses
  - All types it references
  - All types that reference it
#>

# ============================================================
# MIGRATION PREVIEW MODE
# ============================================================

function Get-MigrationPreview {
    param(
        [string]$ModPath,
        [string]$TypeUNID,
        [string]$Version = 'AI'  # 'Original', 'Manual', or 'AI'
    )
    
    # Load the appropriate version
    $files = @()
    if (Test-Path $ModPath -PathType Leaf) {
        if ($ModPath.EndsWith('.xml')) { $files = @($ModPath) }
    } else {
        $files = @(Get-ChildItem -LiteralPath $ModPath -Filter '*.xml' -Recurse | ForEach-Object { $_.FullName })
    }
    
    # Parse XML files to find the type
    $typeInfo = Find-TypeInFiles -Files $files -UNID $TypeUNID
    
    if (-not $typeInfo) {
        return [PSCustomObject]@{
            Found = $false
            Message = "Type with UNID $TypeUNID not found"
        }
    }
    
    # Resolve inheritance
    $resolved = Resolve-TypeInheritance -TypeInfo $typeInfo -AllFiles $files
    
    return [PSCustomObject]@{
        Found = $true
        TypeInfo = $typeInfo
        Resolved = $resolved
        Version = $Version
    }
}

function Find-TypeInFiles {
    param(
        [string[]]$Files,
        [string]$UNID
    )
    
    foreach ($file in $Files) {
        try {
            $content = [System.IO.File]::ReadAllText($file, [System.Text.Encoding]::UTF8)
            
            # Look for type with matching UNID
            $unidPattern = "UNID=`"([^`"]+)`""
            $typePattern = "<(\w+)\s+[^>]*UNID=`"$([regex]::Escape($UNID))`""
            
            if ($content -match $typePattern) {
                $typeName = $matches[1]
                
                # Extract type element
                $typeMatch = [regex]::Match($content, "<$typeName\s+[^>]*UNID=`"$([regex]::Escape($UNID))`"[^>]*>.*?</$typeName>", [System.Text.RegularExpressions.RegexOptions]::Singleline)
                
                if ($typeMatch.Success) {
                    return [PSCustomObject]@{
                        UNID = $UNID
                        TypeName = $typeName
                        File = $file
                        Content = $typeMatch.Value
                        Attributes = Extract-Attributes -Content $typeMatch.Value
                        Events = Extract-Events -Content $typeMatch.Value
                        Resources = Extract-Resources -Content $typeMatch.Value
                    }
                }
            }
        }
        catch {
            # Continue searching
        }
    }
    
    return $null
}

function Extract-Attributes {
    param([string]$Content)
    
    $attributes = @{}
    # Use double quotes with proper escaping for regex character class
    $attrPattern = "(\w+)=[""']([^""']+)[""']"
    $matches = [regex]::Matches($Content, $attrPattern)
    
    foreach ($match in $matches) {
        $name = $match.Groups[1].Value
        $value = $match.Groups[2].Value
        $attributes[$name] = $value
    }
    
    return $attributes
}

function Extract-Events {
    param([string]$Content)
    
    $events = @()
    $eventPattern = '<(\w+Event|On\w+)>'
    $matches = [regex]::Matches($Content, $eventPattern)
    
    foreach ($match in $matches) {
        $eventName = $match.Groups[1].Value
        
        # Extract event content
        $eventContentPattern = "<$([regex]::Escape($eventName))>(.*?)</$([regex]::Escape($eventName))>"
        $eventContentMatch = [regex]::Match($Content, $eventContentPattern, [System.Text.RegularExpressions.RegexOptions]::Singleline)
        
        $events += [PSCustomObject]@{
            Name = $eventName
            Content = if ($eventContentMatch.Success) { $eventContentMatch.Groups[1].Value } else { '' }
        }
    }
    
    return $events
}

function Extract-Resources {
    param([string]$Content)
    
    $resources = @()
    
    # Image resources
    # Use double quotes with proper escaping for regex character class
    $imagePattern = "imageID=[""']([^""']+)[""']"
    $imageMatches = [regex]::Matches($Content, $imagePattern)
    foreach ($match in $imageMatches) {
        $resources += [PSCustomObject]@{
            Type = 'Image'
            UNID = $match.Groups[1].Value
        }
    }
    
    # Sound resources
    # Use double quotes with proper escaping for regex character class
    $soundPattern = "soundID=[""']([^""']+)[""']"
    $soundMatches = [regex]::Matches($Content, $soundPattern)
    foreach ($match in $soundMatches) {
        $resources += [PSCustomObject]@{
            Type = 'Sound'
            UNID = $match.Groups[1].Value
        }
    }
    
    return $resources
}

function Resolve-TypeInheritance {
    param(
        [PSCustomObject]$TypeInfo,
        [string[]]$AllFiles
    )
    
    $resolved = [PSCustomObject]@{
        Attributes = @{}
        Events = @()
        Resources = @()
        InheritedFrom = @()
    }
    
    # Start with base type attributes
    foreach ($attr in $TypeInfo.Attributes.GetEnumerator()) {
        $resolved.Attributes[$attr.Key] = [PSCustomObject]@{
            Value = $attr.Value
            Source = 'Direct'
            SourceFile = $TypeInfo.File
        }
    }
    
    # Check for inherit attribute
    if ($TypeInfo.Attributes.ContainsKey('inherit')) {
        $inheritUNID = $TypeInfo.Attributes['inherit']
        
        # Find parent type
        $parentType = Find-TypeInFiles -Files $AllFiles -UNID $inheritUNID
        
        if ($parentType) {
            $resolved.InheritedFrom += $parentType.UNID
            
            # Recursively resolve parent
            $parentResolved = Resolve-TypeInheritance -TypeInfo $parentType -AllFiles $AllFiles
            
            # Merge parent attributes (parent takes precedence for conflicts)
            foreach ($attr in $parentResolved.Attributes.GetEnumerator()) {
                if (-not $resolved.Attributes.ContainsKey($attr.Key)) {
                    $resolved.Attributes[$attr.Key] = [PSCustomObject]@{
                        Value = $attr.Value.Value
                        Source = "Inherited from $($parentType.UNID)"
                        SourceFile = $parentType.File
                    }
                }
            }
            
            # Merge events
            $resolved.Events += $parentResolved.Events
            $resolved.Resources += $parentResolved.Resources
        }
    }
    
    # Add direct events and resources
    $resolved.Events += $TypeInfo.Events
    $resolved.Resources += $TypeInfo.Resources
    
    return $resolved
}

function Format-MigrationPreview {
    param(
        [PSCustomObject]$Preview
    )
    
    if (-not $Preview.Found) {
        return $Preview.Message
    }
    
    $output = [System.Text.StringBuilder]::new()
    
    [void]$output.AppendLine("Migration Preview: $($Preview.TypeInfo.TypeName)")
    [void]$output.AppendLine("Version: $($Preview.Version)")
    [void]$output.AppendLine("UNID: $($Preview.TypeInfo.UNID)")
    [void]$output.AppendLine("=" * 60)
    [void]$output.AppendLine("")
    
    # Resolved Attributes
    [void]$output.AppendLine("RESOLVED ATTRIBUTES:")
    [void]$output.AppendLine("-" * 60)
    foreach ($attr in $Preview.Resolved.Attributes.GetEnumerator()) {
        [void]$output.AppendLine("  $($attr.Key) = $($attr.Value.Value)")
        [void]$output.AppendLine("    Source: $($attr.Value.Source)")
        if ($attr.Value.SourceFile) {
            [void]$output.AppendLine("    File: $(Split-Path -Leaf $attr.Value.SourceFile)")
        }
    }
    [void]$output.AppendLine("")
    
    # Inheritance Chain
    if ($Preview.Resolved.InheritedFrom.Count -gt 0) {
        [void]$output.AppendLine("INHERITANCE CHAIN:")
        [void]$output.AppendLine("-" * 60)
        foreach ($parent in $Preview.Resolved.InheritedFrom) {
            [void]$output.AppendLine("  → $parent")
        }
        [void]$output.AppendLine("")
    }
    
    # Events
    [void]$output.AppendLine("EVENTS ($($Preview.Resolved.Events.Count)):")
    [void]$output.AppendLine("-" * 60)
    foreach ($event in $Preview.Resolved.Events) {
        [void]$output.AppendLine("  - $($event.Name)")
    }
    [void]$output.AppendLine("")
    
    # Resources
    if ($Preview.Resolved.Resources.Count -gt 0) {
        [void]$output.AppendLine("RESOURCES:")
        [void]$output.AppendLine("-" * 60)
        foreach ($resource in $Preview.Resolved.Resources) {
            [void]$output.AppendLine("  - $($resource.Type): $($resource.UNID)")
        }
        [void]$output.AppendLine("")
    }
    
    return $output.ToString()
}

function Compare-MigrationPreviews {
    param(
        [PSCustomObject]$OriginalPreview,
        [PSCustomObject]$AiPreview
    )
    
    $comparison = [PSCustomObject]@{
        AttributeChanges = @()
        EventChanges = @()
        ResourceChanges = @()
        InheritanceChanges = @()
    }
    
    if (-not $OriginalPreview.Found -or -not $AiPreview.Found) {
        return $comparison
    }
    
    # Compare attributes
    $originalAttrs = $OriginalPreview.Resolved.Attributes
    $aiAttrs = $AiPreview.Resolved.Attributes
    
    # Added attributes
    foreach ($attr in $aiAttrs.GetEnumerator()) {
        if (-not $originalAttrs.ContainsKey($attr.Key)) {
            $comparison.AttributeChanges += [PSCustomObject]@{
                Type = 'Added'
                Name = $attr.Key
                Value = $attr.Value.Value
            }
        }
        elseif ($originalAttrs[$attr.Key].Value -ne $attr.Value.Value) {
            $comparison.AttributeChanges += [PSCustomObject]@{
                Type = 'Changed'
                Name = $attr.Key
                OldValue = $originalAttrs[$attr.Key].Value
                NewValue = $attr.Value.Value
            }
        }
    }
    
    # Removed attributes
    foreach ($attr in $originalAttrs.GetEnumerator()) {
        if (-not $aiAttrs.ContainsKey($attr.Key)) {
            $comparison.AttributeChanges += [PSCustomObject]@{
                Type = 'Removed'
                Name = $attr.Key
                Value = $attr.Value.Value
            }
        }
    }
    
    # Compare events
    $originalEvents = $OriginalPreview.Resolved.Events | ForEach-Object { $_.Name } | Sort-Object
    $aiEvents = $AiPreview.Resolved.Events | ForEach-Object { $_.Name } | Sort-Object
    
    $addedEvents = $aiEvents | Where-Object { $originalEvents -notcontains $_ }
    $removedEvents = $originalEvents | Where-Object { $aiEvents -notcontains $_ }
    
    foreach ($event in $addedEvents) {
        $comparison.EventChanges += [PSCustomObject]@{
            Type = 'Added'
            Name = $event
        }
    }
    
    foreach ($event in $removedEvents) {
        $comparison.EventChanges += [PSCustomObject]@{
            Type = 'Removed'
            Name = $event
        }
    }
    
    return $comparison
}


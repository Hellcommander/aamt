<#
.SYNOPSIS
  XML Formatting and Beautification Module
  
.DESCRIPTION
  Auto-formatting features for Transcendence XML files:
  - Normalize indentation (tabs)
  - Align attributes
  - Break long lines
  - Consistent formatting
#>

# ============================================================
# XML AUTO-FORMATTER
# ============================================================

function Format-XmlFile {
    param(
        [string]$FilePath,
        [int]$IndentSize = 1,
        [string]$IndentChar = "`t",
        [switch]$AlignAttributes,
        [switch]$BreakLongLines,
        [int]$MaxLineLength = 120
    )
    
    try {
        $text = [System.IO.File]::ReadAllText($FilePath, [System.Text.Encoding]::UTF8)
        $formatted = Format-XmlString -XmlText $text -IndentSize $IndentSize -IndentChar $IndentChar -AlignAttributes:$AlignAttributes -BreakLongLines:$BreakLongLines -MaxLineLength $MaxLineLength
        
        # Create backup
        $backupPath = $FilePath + '.bak'
        Copy-Item -LiteralPath $FilePath -Destination $backupPath -Force
        
        # Write formatted
        $utf8NoBom = [System.Text.UTF8Encoding]::new($false)
        [System.IO.File]::WriteAllText($FilePath, $formatted, $utf8NoBom)
        
        return $true
    }
    catch {
        return $false
    }
}

function Format-XmlString {
    param(
        [string]$XmlText,
        [int]$IndentSize = 1,
        [string]$IndentChar = "`t",
        [switch]$AlignAttributes,
        [switch]$BreakLongLines,
        [int]$MaxLineLength = 120
    )
    
    # Use .NET XmlDocument for proper parsing and formatting
    try {
        $xmlDoc = [System.Xml.XmlDocument]::new()
        $xmlDoc.PreserveWhitespace = $false
        $xmlDoc.LoadXml($XmlText)
        
        # Use XmlWriterSettings for formatting
        $settings = [System.Xml.XmlWriterSettings]::new()
        $settings.Indent = $true
        $settings.IndentChars = $IndentChar
        $settings.NewLineChars = "`n"
        $settings.OmitXmlDeclaration = $false
        $settings.Encoding = [System.Text.Encoding]::UTF8
        
        $stringWriter = [System.IO.StringWriter]::new()
        $xmlWriter = [System.Xml.XmlWriter]::Create($stringWriter, $settings)
        $xmlDoc.WriteTo($xmlWriter)
        $xmlWriter.Close()
        
        $formatted = $stringWriter.ToString()
        
        # Post-process to match Transcendence 2.0.7 style
        $lines = $formatted -split "`r?`n"
        $output = [System.Collections.ArrayList]::new()
        $indentLevel = 0
        
        foreach ($line in $lines) {
            $trimmed = $line.Trim()
            
            if ([string]::IsNullOrWhiteSpace($trimmed)) {
                [void]$output.Add('')
                continue
            }
            
            # Skip XML declaration (already formatted)
            if ($trimmed.StartsWith('<?xml')) {
                [void]$output.Add($trimmed)
                continue
            }
            
            # Handle DOCTYPE - preserve as-is
            if ($trimmed.ToUpper().StartsWith('<!DOCTYPE')) {
                [void]$output.Add($trimmed)
                continue
            }
            
            # Calculate current indent
            $leadingWhitespace = $line -replace '^(.*?)(\S.*)$', '$1'
            $currentIndent = ($leadingWhitespace -replace "[^`t]", '').Length
            
            # Format attributes for Transcendence style (align with spaces after name)
            if ($trimmed -match '^<(\w+)([^>]*)>$' -and $AlignAttributes) {
                $tagName = $matches[1]
                $attrs = $matches[2].Trim()
                
                if ($attrs.Length -gt 0 -and -not $attrs.EndsWith('/')) {
                    # Parse attributes
                    $attrPattern = '(\w+)\s*=\s*"([^"]*)"'
                    $attrMatches = [regex]::Matches($attrs, $attrPattern)
                    
                    if ($attrMatches.Count -gt 1) {
                        $maxAttrNameLength = 0
                        foreach ($m in $attrMatches) {
                            $nameLen = $m.Groups[1].Value.Length
                            if ($nameLen -gt $maxAttrNameLength) {
                                $maxAttrNameLength = $nameLen
                            }
                        }
                        
                        $formattedAttrs = @()
                        foreach ($m in $attrMatches) {
                            $attrName = $m.Groups[1].Value
                            $attrValue = $m.Groups[2].Value
                            $padding = ' ' * ($maxAttrNameLength - $attrName.Length + 1)
                            $formattedAttrs += "`n$IndentChar$IndentChar$attrName$padding=`"$attrValue`""
                        }
                        
                        $indent = $IndentChar * $currentIndent
                        $formattedLine = "$indent<$tagName$($formattedAttrs -join '')>"
                        [void]$output.Add($formattedLine)
                    }
                    else {
                        [void]$output.Add($line)
                    }
                }
                else {
                    [void]$output.Add($line)
                }
            }
            else {
                [void]$output.Add($line)
            }
        }
        
        return $output -join "`n"
    }
    catch {
        # Fallback to simple formatting if XML parsing fails
        return Format-XmlStringSimple -XmlText $XmlText -IndentChar $IndentChar
    }
}

function Format-XmlStringSimple {
    param(
        [string]$XmlText,
        [string]$IndentChar = "`t"
    )
    
    $lines = $XmlText -split "`r?`n"
    $output = [System.Collections.ArrayList]::new()
    $indentLevel = 0
    $inComment = $false
    $inCData = $false
    $inDoctype = $false
    $doctypeBracket = 0
    
    foreach ($line in $lines) {
        $trimmed = $line.Trim()
        
        if ([string]::IsNullOrWhiteSpace($trimmed)) {
            [void]$output.Add('')
            continue
        }
        
        # Track state
        if ($trimmed.StartsWith('<!--')) { $inComment = $true }
        if ($trimmed.Contains('-->')) { $inComment = $false }
        if ($trimmed.Contains('<![CDATA[')) { $inCData = $true }
        if ($trimmed.Contains(']]>')) { $inCData = $false }
        if ($trimmed.ToUpper().StartsWith('<!DOCTYPE')) { $inDoctype = $true }
        if ($inDoctype) {
            if ($trimmed.Contains('[')) { $doctypeBracket++ }
            if ($trimmed.Contains(']')) { $doctypeBracket-- }
            if ($trimmed.Contains('>') -and $doctypeBracket -eq 0) { $inDoctype = $false }
        }
        
        # Skip formatting in special sections
        if ($inComment -or $inCData -or ($inDoctype -and $doctypeBracket -gt 0)) {
            [void]$output.Add($line)
            continue
        }
        
        # Handle XML declaration
        if ($trimmed.StartsWith('<?xml')) {
            [void]$output.Add($trimmed)
            continue
        }
        
        # Handle DOCTYPE
        if ($trimmed.ToUpper().StartsWith('<!DOCTYPE')) {
            [void]$output.Add($trimmed)
            continue
        }
        
        # Count opening/closing tags
        $openTags = ([regex]::Matches($trimmed, '<[^/!?][^>]*[^/]>')).Count
        $selfClosing = ([regex]::Matches($trimmed, '<[^/!?][^>]*/>')).Count
        $closeTags = ([regex]::Matches($trimmed, '</[^>]+>')).Count
        
        # Adjust indent level
        $currentIndent = $indentLevel
        
        # Format the line
        $indent = $IndentChar * ($currentIndent * 1)
        [void]$output.Add("$indent$trimmed")
        
        # Update indent level for next line
        if ($openTags -gt $selfClosing) {
            $indentLevel += ($openTags - $selfClosing)
        }
        if ($closeTags -gt 0) {
            $indentLevel = [Math]::Max(0, $indentLevel - $closeTags)
        }
    }
    
    return $output -join "`n"
}

# Export
# Functions are available for dot-sourcing


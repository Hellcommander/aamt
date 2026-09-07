<#
.SYNOPSIS
  Transcendence Mod Tools - Integrated XML Checker & Error Helper

.DESCRIPTION
  A unified GUI tool for Transcendence mod development:
  - Scan XML files for common issues
  - Diagnose error messages
  - Auto-fix certain problems
  
.EXAMPLE
  pwsh -File TranscendenceModTools.ps1
#>

[CmdletBinding()]
param(
    [string]$Path,
    [switch]$NoGui,
    [switch]$AutoScan,
    [switch]$ScanAndExit,
    
    # Diagnose game errors from Debug.log
    [switch]$DiagnoseLog,
    
    # Maximum number of recent errors to show from Debug.log
    [int]$MaxErrors = 20
)

# Store path in script scope so it's available in Show-MainGui function
if ($Path) {
    $script:InitialPath = $Path
}

# ============================================================
# ERROR PATTERN DATABASE
# ============================================================

$script:ErrorPatterns = @(
    @{
        Pattern = 'Unknown design type: ([0-9a-fA-F]+)'
        Code = 'STALE_VANILLA_UNID'
        Cause = "A DTD <!ENTITY> copies a vanilla name (svIndependent, baHumanTechShip, rsItemsNAMI1, ...) with a 1.0-era UNID. The name still exists; the hex ID moved or is unused."
        Solution = "Run Tools\Transcendence\Remap-VanillaDesignTypes.py --apply --backup. It converts obsolete official types (dsLoot -> dsRPGLoot, stCargoCrate -> stGenericCargoCrate, API54 armor names, moved resource UNIDs) to the current Human Space / RPG IDs."
        CanFix = $false
    },
    @{
        Pattern = 'Unknown image: ([0-9a-fA-F]+)'
        Code = 'STALE_VANILLA_IMAGE'
        Cause = "An imageID entity still points at an old resource UNID (for example 7013 used to be rsItemsNAMI1; it is now 0x0000F158)."
        Solution = "Run Tools\Transcendence\Remap-VanillaDesignTypes.py --apply --backup."
        CanFix = $false
    },
    @{
        Pattern = 'content expected'
        Code = 'XML_CONTENT_EXPECTED'
        Cause = "A literal '>' character in element content. Transcendence treats this as a tag close."
        Solution = "Replace '>' with '&gt;' in comments/code."
        CanFix = $true
    },
    @{
        Pattern = 'close tag </(\w+)> does not match open <(\w+)>'
        Code = 'XML_TAG_MISMATCH'
        Cause = "Closing tag name doesn't match opening tag."
        Solution = "Check line numbers and fix tag names."
        CanFix = $false
    },
    @{
        Pattern = 'Mismatched quote'
        Code = 'TLISP_QUOTE_MISMATCH'
        Cause = "String has opening quote without closing. Often caused by < or > in strings being parsed as XML."
        Solution = "Escape < and > as &lt; and &gt; in strings, especially in xmlCreate."
        CanFix = $true
    },
    @{
        Pattern = 'Identifiers must not use single quote'
        Code = 'TLISP_INVALID_SYMBOL'
        Cause = "Symbol literal has trailing quote. TLisp symbols use ONLY leading quote."
        Solution = "Remove trailing quote: 'symbol' -> 'symbol"
        CanFix = $true
    },
    @{
        Pattern = '<\?XML prologue expected'
        Code = 'XML_PROLOGUE_EXPECTED'
        Cause = "BOM or whitespace before first '<' character."
        Solution = "Remove BOM/whitespace before <?xml declaration."
        CanFix = $true
    },
    @{
        Pattern = 'element tag expected'
        Code = 'XML_ELEMENT_EXPECTED'
        Cause = "Parser expected element tag but found something else."
        Solution = "Check for malformed XML near the line."
        CanFix = $false
    },
    @{
        Pattern = 'Reference to undeclared entity'
        Code = 'ENTITY_UNDECLARED'
        Cause = "Entity reference used but not defined."
        Solution = "Add entity to DOCTYPE or check spelling."
        CanFix = $false
    },
    @{
        Pattern = 'Invalid entity:\s*(\w+)'
        Code = 'ENTITY_INVALID'
        Cause = "Entity reference '&entityName;' is not defined in DOCTYPE. The game cannot resolve this entity."
        Solution = "Add <!ENTITY entityName ""0xUNID""> to DOCTYPE section, or check for typos. Common prefixes: it=item, sc=ship, st=station, vt=virtual, rs=resource, ef=effect, sn=sound, sv=sovereign, ds=dockscreen, tb=table, ba=base."
        CanFix = $false
    },
    @{
        Pattern = 'attribute value must be quoted'
        Code = 'XML_ATTR_UNQUOTED'
        Cause = "Attribute value not in quotes."
        Solution = 'Use quotes: attribute="value"'
        CanFix = $false
    }
)

# ============================================================
# ISSUE DETECTION FUNCTIONS
# ============================================================

function Get-XmlIssues {
    param([string]$FilePath)
    
    $issues = [System.Collections.ArrayList]::new()
    
    try {
        $text = [System.IO.File]::ReadAllText($FilePath, [System.Text.Encoding]::UTF8)
        $lines = $text -split "`n"
    }
    catch {
        [void]$issues.Add([PSCustomObject]@{
            File = $FilePath
            Line = 0
            Code = 'FILE_READ_ERROR'
            Severity = 'Error'
            Message = "Cannot read file: $_"
            CanFix = $false
        })
        return $issues
    }
    
    # Check for BOM
    $bytes = [System.IO.File]::ReadAllBytes($FilePath)
    if ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) {
        [void]$issues.Add([PSCustomObject]@{
            File = $FilePath
            Line = 1
            Code = 'BOM_DETECTED'
            Severity = 'Error'
            Message = 'UTF-8 BOM detected. Transcendence requires no BOM.'
            CanFix = $true
        })
    }
    
    # Check for raw > in content (outside tags)
    $inTag = $false
    $inComment = $false
    $inCData = $false
    $inDoctype = $false
    $doctypeBracket = 0
    $lineNum = 0
    
    foreach ($line in $lines) {
        $lineNum++
        $col = 0
        
        for ($i = 0; $i -lt $line.Length; $i++) {
            $col++
            $ch = $line[$i]
            $remaining = $line.Substring($i)
            
            # Track state
            if (-not $inTag -and -not $inComment -and -not $inCData -and -not $inDoctype) {
                if ($remaining.StartsWith('<!--')) { $inComment = $true; $i += 3; continue }
                if ($remaining.StartsWith('<![CDATA[')) { $inCData = $true; $i += 8; continue }
                if ($remaining.ToUpper().StartsWith('<!DOCTYPE')) { $inDoctype = $true; $i += 8; continue }
                if ($ch -eq '<') { $inTag = $true; continue }
                
                # Raw > outside tags
                if ($ch -eq '>') {
                    [void]$issues.Add([PSCustomObject]@{
                        File = $FilePath
                        Line = $lineNum
                        Code = 'RAW_GT_IN_CONTENT'
                        Severity = 'Error'
                        Message = "Raw '>' in content will cause 'content expected' error."
                        CanFix = $true
                        Context = $line.Trim()
                    })
                }
            }
            elseif ($inTag) {
                if ($ch -eq '>') { $inTag = $false }
            }
            elseif ($inComment) {
                if ($remaining.StartsWith('-->')) { $inComment = $false; $i += 2 }
            }
            elseif ($inCData) {
                if ($remaining.StartsWith(']]>')) { $inCData = $false; $i += 2 }
            }
            elseif ($inDoctype) {
                if ($ch -eq '[') { $doctypeBracket++ }
                elseif ($ch -eq ']') { $doctypeBracket-- }
                elseif ($ch -eq '>' -and $doctypeBracket -eq 0) { $inDoctype = $false }
            }
        }
    }
    
    # Check for xmlCreate with raw XML
    $xmlCreatePattern = 'xmlCreate\s*\(?\s*"<'
    $matches = [regex]::Matches($text, $xmlCreatePattern, [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
    foreach ($m in $matches) {
        $before = $text.Substring(0, $m.Index)
        $line = ($before -split "`n").Count
        [void]$issues.Add([PSCustomObject]@{
            File = $FilePath
            Line = $line
            Code = 'XMLCREATE_RAW_XML'
            Severity = 'Warning'
            Message = 'xmlCreate with raw XML tags. Escape as &lt;Tag&gt;'
            CanFix = $true
        })
    }
    
    # Check for invalid symbol syntax 'symbol'
    $symbolPattern = "'([a-zA-Z_][a-zA-Z0-9_]*)'"
    $matches = [regex]::Matches($text, $symbolPattern)
    foreach ($m in $matches) {
        $before = $text.Substring(0, $m.Index)
        $line = ($before -split "`n").Count
        [void]$issues.Add([PSCustomObject]@{
            File = $FilePath
            Line = $line
            Code = 'INVALID_SYMBOL_SYNTAX'
            Severity = 'Error'
            Message = "Invalid symbol '$($m.Groups[1].Value)' - remove trailing quote"
            CanFix = $true
        })
    }
    
    # ==========================================================================
    # PRECISION XML VALIDATION - More exact than game's parser
    # Each error tells: WHAT was expected, WHAT was found, WHERE, HOW to fix
    # ==========================================================================
    
    # Check 1: File must start with '<' (Parser.cpp line 535-539)
    $firstChar = if ($text.Length -gt 0) { $text[0] } else { '' }
    $firstCharCode = if ($text.Length -gt 0) { [int][char]$text[0] } else { 0 }
    if ($firstChar -ne '<') {
        $foundDesc = switch ($firstCharCode) {
            0xEF { "UTF-8 BOM (0xEF 0xBB 0xBF)" }
            0xFE { "UTF-16 BE BOM (0xFE 0xFF)" }
            0xFF { "UTF-16 LE BOM (0xFF 0xFE)" }
            32 { "space character (0x20)" }
            9 { "tab character (0x09)" }
            10 { "newline (0x0A)" }
            13 { "carriage return (0x0D)" }
            default { "character '$firstChar' (0x$($firstCharCode.ToString('X2')))" }
        }
        [void]$issues.Add([PSCustomObject]@{
            File = $FilePath
            Line = 1
            Column = 1
            Code = 'FILE_NOT_START_WITH_LT'
            Severity = 'Error'
            Message = "EXPECTED: '<' as first character (start of XML declaration)"
            Context = "FOUND: $foundDesc"
            Fix = "Remove any bytes before '<?xml'. If BOM, save file as UTF-8 without BOM."
            CanFix = $false
        })
    }
    
    # Check 2: XML declaration format
    $xmlDeclMatch = [regex]::Match($text, '<\?xml\s+([^?]*)\?>')
    if (-not $xmlDeclMatch.Success -and $text.StartsWith('<?')) {
        $piEnd = $text.IndexOf('?>')
        $foundPI = if ($piEnd -gt 0) { $text.Substring(0, [Math]::Min($piEnd + 2, 50)) } else { $text.Substring(0, [Math]::Min(30, $text.Length)) }
        [void]$issues.Add([PSCustomObject]@{
            File = $FilePath
            Line = 1
            Column = 1
            Code = 'INVALID_XML_DECLARATION'
            Severity = 'Error'
            Message = "EXPECTED: <?xml version=""1.0"" encoding=""utf-8""?>"
            Context = "FOUND: $foundPI"
            Fix = "Ensure XML declaration has 'xml' (lowercase) followed by version attribute"
            CanFix = $false
        })
    }
    
    # Check 3: Content between XML declaration and DOCTYPE
    $xmlDeclEnd = $text.IndexOf('?>')
    if ($xmlDeclEnd -gt 0) {
        $doctypeStart = $text.IndexOf('<!DOCTYPE', [System.StringComparison]::OrdinalIgnoreCase)
        if ($doctypeStart -gt $xmlDeclEnd) {
            $between = $text.Substring($xmlDeclEnd + 2, $doctypeStart - $xmlDeclEnd - 2)
            $betweenTrimmed = $between.Trim()
            
            # Check for comments
            $commentMatch = [regex]::Match($between, '<!--(.*?)-->', [System.Text.RegularExpressions.RegexOptions]::Singleline)
            if ($commentMatch.Success) {
                $lineNum = ($text.Substring(0, $xmlDeclEnd + 2 + $between.IndexOf('<!--')) -split "`n").Count
                $commentPreview = $commentMatch.Groups[1].Value.Trim()
                if ($commentPreview.Length -gt 50) { $commentPreview = $commentPreview.Substring(0, 50) + "..." }
                [void]$issues.Add([PSCustomObject]@{
                    File = $FilePath
                    Line = $lineNum
                    Column = 1
                    Code = 'COMMENT_BEFORE_DOCTYPE'
                    Severity = 'Error'
                    Message = "EXPECTED: <!DOCTYPE immediately after <?xml...?> (only whitespace allowed)"
                    Context = "FOUND: Comment '<!--$commentPreview-->'"
                    Fix = "Move comment inside <TranscendenceExtension> root element, or after ]> of DOCTYPE"
                    CanFix = $false
                })
            }
            
            # Check for non-whitespace, non-comment content
            $betweenNoComments = $between -replace '(?s)<!--.*?-->', ''
            $betweenNoCommentsClean = $betweenNoComments -replace '\s', ''
            if ($betweenNoCommentsClean.Length -gt 0) {
                $lineNum = ($text.Substring(0, $xmlDeclEnd + 2) -split "`n").Count
                $contentPreview = $betweenNoCommentsClean.Substring(0, [Math]::Min(30, $betweenNoCommentsClean.Length))
                [void]$issues.Add([PSCustomObject]@{
                    File = $FilePath
                    Line = $lineNum
                    Column = 1
                    Code = 'CONTENT_BEFORE_DOCTYPE'
                    Severity = 'Error'
                    Message = "EXPECTED: Only whitespace between <?xml...?> and <!DOCTYPE"
                    Context = "FOUND: '$contentPreview'"
                    Fix = "Remove or move this content. Only whitespace/newlines allowed here."
                    CanFix = $false
                })
            }
        }
        elseif ($doctypeStart -eq -1) {
            # No DOCTYPE found - check what comes after XML declaration
            $afterXmlDecl = $text.Substring($xmlDeclEnd + 2).TrimStart()
            if (-not $afterXmlDecl.StartsWith('<TranscendenceExtension') -and
                -not $afterXmlDecl.StartsWith('<TranscendenceAdventure') -and
                -not $afterXmlDecl.StartsWith('<TranscendenceModule') -and
                -not $afterXmlDecl.StartsWith('<TranscendenceLibrary') -and
                -not $afterXmlDecl.StartsWith('<TranscendenceUniverse')) {
                $lineNum = ($text.Substring(0, $xmlDeclEnd + 2) -split "`n").Count
                $foundPreview = $afterXmlDecl.Substring(0, [Math]::Min(50, $afterXmlDecl.Length))
                [void]$issues.Add([PSCustomObject]@{
                    File = $FilePath
                    Line = $lineNum
                    Column = 1
                    Code = 'MISSING_DOCTYPE_OR_ROOT'
                    Severity = 'Error'
                    Message = "EXPECTED: <!DOCTYPE ...> or <TranscendenceExtension/Module/Adventure/Library/Universe>"
                    Context = "FOUND: '$foundPreview'"
                    Fix = "Add DOCTYPE declaration or root element after XML declaration"
                    CanFix = $false
                })
            }
        }
    }
    
    # Check 4: DOCTYPE structure
    $doctypeMatch = [regex]::Match($text, '<!DOCTYPE\s+(\w+)\s*\[', [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
    if ($doctypeMatch.Success) {
        $doctypeName = $doctypeMatch.Groups[1].Value
        $validRoots = @('TranscendenceExtension', 'TranscendenceAdventure', 'TranscendenceModule', 'TranscendenceLibrary', 'TranscendenceUniverse')
        if ($doctypeName -notin $validRoots) {
            $lineNum = ($text.Substring(0, $doctypeMatch.Index) -split "`n").Count
            [void]$issues.Add([PSCustomObject]@{
                File = $FilePath
                Line = $lineNum
                Column = $doctypeMatch.Index - $text.LastIndexOf("`n", $doctypeMatch.Index)
                Code = 'INVALID_DOCTYPE_NAME'
                Severity = 'Error'
                Message = "EXPECTED: DOCTYPE name to be one of: $($validRoots -join ', ')"
                Context = "FOUND: '$doctypeName'"
                Fix = "Change DOCTYPE to match your root element type (e.g., TranscendenceExtension)"
                CanFix = $false
            })
        }
        
        # Check DOCTYPE ends with ]>
        $doctypeEnd = $text.IndexOf(']>', $doctypeMatch.Index)
        if ($doctypeEnd -eq -1) {
            $lineNum = ($text.Substring(0, $doctypeMatch.Index) -split "`n").Count
            [void]$issues.Add([PSCustomObject]@{
                File = $FilePath
                Line = $lineNum
                Column = 1
                Code = 'DOCTYPE_NOT_CLOSED'
                Severity = 'Error'
                Message = "EXPECTED: DOCTYPE to end with ']>'"
                Context = "FOUND: DOCTYPE with '[' but no closing ']>'"
                Fix = "Add ']>' to close the DOCTYPE declaration before root element"
                CanFix = $false
            })
        }
    }
    
    # Check 5: Root element validation
    $rootElementPattern = '<(TranscendenceExtension|TranscendenceAdventure|TranscendenceModule|TranscendenceLibrary|TranscendenceUniverse)(\s[^>]*)?>'
    $rootMatches = [regex]::Matches($text, $rootElementPattern)
    if ($rootMatches.Count -eq 0) {
        # Try to find what the first element is
        $firstElementMatch = [regex]::Match($text, '<([a-zA-Z][a-zA-Z0-9_]*)[^>]*>')
        $foundElement = if ($firstElementMatch.Success) { $firstElementMatch.Groups[1].Value } else { "(no element found)" }
        [void]$issues.Add([PSCustomObject]@{
            File = $FilePath
            Line = 1
            Column = 1
            Code = 'WRONG_ROOT_ELEMENT'
            Severity = 'Error'
            Message = "EXPECTED: Root element <TranscendenceExtension>, <TranscendenceAdventure>, <TranscendenceModule>, <TranscendenceLibrary>, or <TranscendenceUniverse>"
            Context = "FOUND: <$foundElement>"
            Fix = "Wrap content in correct root element for mod type"
            CanFix = $false
        })
    }
    elseif ($rootMatches.Count -gt 1) {
        $lineNum = ($text.Substring(0, $rootMatches[1].Index) -split "`n").Count
        [void]$issues.Add([PSCustomObject]@{
            File = $FilePath
            Line = $lineNum
            Column = 1
            Code = 'MULTIPLE_ROOT_ELEMENTS'
            Severity = 'Error'
            Message = "EXPECTED: Exactly one root element"
            Context = "FOUND: $($rootMatches.Count) root elements ($($rootMatches[0].Groups[1].Value), $($rootMatches[1].Groups[1].Value)...)"
            Fix = "Remove duplicate root elements or merge content into single root"
            CanFix = $false
        })
    }
    
    # Check 6: Invalid element tag names (Parser.cpp IsValidElementTag lines 1510-1545)
    $invalidTagPattern = '<([^/!?\s][^\s/>]*)'
    $allTagMatches = [regex]::Matches($text, $invalidTagPattern)
    foreach ($tagMatch in $allTagMatches) {
        $tag = $tagMatch.Groups[1].Value
        # Skip special constructs
        if ($tag.StartsWith('!') -or $tag.StartsWith('?')) { continue }
        
        # Validate: must start with letter/underscore/colon, rest alphanum/underscore/colon/dot/hyphen
        if ($tag -notmatch '^[a-zA-Z_:][a-zA-Z0-9_:.\-]*$') {
            $lineNum = ($text.Substring(0, $tagMatch.Index) -split "`n").Count
            $invalidChar = [regex]::Match($tag, '[^a-zA-Z0-9_:.\-]')
            $charDesc = if ($invalidChar.Success) { 
                "character '$($invalidChar.Value)' (0x$([int][char]$invalidChar.Value.ToString('X2')))" 
            } else { 
                "first character '$($tag[0])'" 
            }
            [void]$issues.Add([PSCustomObject]@{
                File = $FilePath
                Line = $lineNum
                Column = $tagMatch.Index - $text.LastIndexOf("`n", [Math]::Max(0, $tagMatch.Index - 1))
                Code = 'INVALID_TAG_NAME'
                Severity = 'Error'
                Message = "EXPECTED: Tag name starting with letter/underscore/colon, containing only letters, numbers, underscore, colon, dot, hyphen"
                Context = "FOUND: '<$tag>' - invalid $charDesc"
                Fix = "Rename tag to use only valid XML name characters"
                CanFix = $false
            })
        }
    }
    
    # Check 7: Close tag mismatch with precise stack tracking
    $tagStack = [System.Collections.Generic.List[object]]::new()
    $tagPattern = '<(/?)([a-zA-Z_:][a-zA-Z0-9_:.\-]*)([^>]*?)(/?)>'
    $tagRegex = [regex]::new($tagPattern)
    $pos = 0
    $inComment = $false
    $inCData = $false
    
    while ($pos -lt $text.Length) {
        # Skip comments
        if ($pos + 4 -le $text.Length -and $text.Substring($pos, 4) -eq '<!--') {
            $commentEnd = $text.IndexOf('-->', $pos + 4)
            if ($commentEnd -eq -1) { break }
            $pos = $commentEnd + 3
            continue
        }
        # Skip CDATA
        if ($pos + 9 -le $text.Length -and $text.Substring($pos, 9) -eq '<![CDATA[') {
            $cdataEnd = $text.IndexOf(']]>', $pos + 9)
            if ($cdataEnd -eq -1) { break }
            $pos = $cdataEnd + 3
            continue
        }
        
        $match = $tagRegex.Match($text, $pos)
        if (-not $match.Success) { break }
        
        $isClose = $match.Groups[1].Value -eq '/'
        $tagName = $match.Groups[2].Value
        $isSelfClose = $match.Groups[4].Value -eq '/'
        $tagPos = $match.Index
        $tagLine = ($text.Substring(0, $tagPos) -split "`n").Count
        
        if ($isSelfClose) {
            # Self-closing, no stack change
        }
        elseif ($isClose) {
            # Close tag - pop stack and verify match
            if ($tagStack.Count -eq 0) {
                [void]$issues.Add([PSCustomObject]@{
                    File = $FilePath
                    Line = $tagLine
                    Column = $tagPos - $text.LastIndexOf("`n", [Math]::Max(0, $tagPos - 1))
                    Code = 'CLOSE_TAG_NO_OPEN'
                    Severity = 'Error'
                    Message = "EXPECTED: No close tag (tag stack is empty)"
                    Context = "FOUND: </$tagName> with no matching open tag"
                    Fix = "Remove this close tag or add corresponding <$tagName> before it"
                    CanFix = $false
                })
            }
            else {
                $top = $tagStack[$tagStack.Count - 1]
                if ($top.Name -ne $tagName) {
                    [void]$issues.Add([PSCustomObject]@{
                        File = $FilePath
                        Line = $tagLine
                        Column = $tagPos - $text.LastIndexOf("`n", [Math]::Max(0, $tagPos - 1))
                        Code = 'TAG_MISMATCH'
                        Severity = 'Error'
                        Message = "EXPECTED: </$($top.Name)> to close <$($top.Name)> from line $($top.Line)"
                        Context = "FOUND: </$tagName>"
                        Fix = "Change to </$($top.Name)> or fix the open tag on line $($top.Line)"
                        CanFix = $false
                    })
                }
                else {
                    $tagStack.RemoveAt($tagStack.Count - 1)
                }
            }
        }
        else {
            # Open tag - push to stack
            $tagStack.Add(@{ Name = $tagName; Line = $tagLine; Pos = $tagPos })
        }
        
        $pos = $match.Index + $match.Length
    }
    
    # Report unclosed tags
    foreach ($unclosed in $tagStack) {
        [void]$issues.Add([PSCustomObject]@{
            File = $FilePath
            Line = $unclosed.Line
            Column = 1
            Code = 'TAG_NOT_CLOSED'
            Severity = 'Error'
            Message = "EXPECTED: </$($unclosed.Name)> to close this tag"
            Context = "FOUND: <$($unclosed.Name)> opened on line $($unclosed.Line) but never closed"
            Fix = "Add </$($unclosed.Name)> before closing parent element"
            CanFix = $false
        })
    }
    
    # Check 8: Attribute syntax validation
    $attrPattern = '(\w+)\s*=\s*([''"]?)([^''"]*?)([''"]?)\s*(?=[/>\s])'
    $tagWithAttrsPattern = '<([a-zA-Z_:][a-zA-Z0-9_:.\-]*)\s+([^>]+?)/?>'
    $tagWithAttrsMatches = [regex]::Matches($text, $tagWithAttrsPattern)
    foreach ($tagMatch in $tagWithAttrsMatches) {
        $tagName = $tagMatch.Groups[1].Value
        $attrStr = $tagMatch.Groups[2].Value
        $tagLine = ($text.Substring(0, $tagMatch.Index) -split "`n").Count
        
        # Check for unquoted attribute values
        $unquotedPattern = '(\w+)\s*=\s*([^''"\s>][^\s>]*)'
        $unquotedMatches = [regex]::Matches($attrStr, $unquotedPattern)
        foreach ($uq in $unquotedMatches) {
            $attrName = $uq.Groups[1].Value
            $attrValue = $uq.Groups[2].Value
            # Skip if it's actually quoted (regex might catch partial)
            if ($attrValue -match '^[''"]') { continue }
            [void]$issues.Add([PSCustomObject]@{
                File = $FilePath
                Line = $tagLine
                Column = 1
                Code = 'UNQUOTED_ATTRIBUTE'
                Severity = 'Error'
                Message = "EXPECTED: Attribute value in quotes ($attrName=""..."")"
                Context = "FOUND: $attrName=$attrValue (no quotes)"
                Fix = "Change to $attrName=""$attrValue"""
                CanFix = $true
            })
        }
        
        # Check for mismatched quotes
        $mismatchedQuotePattern = '(\w+)\s*=\s*([''"])([^''"]*?)(?![''"])\s*(?=[/>\s])'
        # This is complex - skip for now, .NET parser catches it
    }
    
    # Check 9: Entity validation with precise context
    $entityPattern = '&([^;\s<>]+);?'
    $entityMatches = [regex]::Matches($text, $entityPattern)
    $standardEntities = @('lt', 'gt', 'amp', 'quot', 'apos', 'nbsp')
    
    foreach ($entityMatch in $entityMatches) {
        $entityFull = $entityMatch.Value
        $entityName = $entityMatch.Groups[1].Value
        $entityPos = $entityMatch.Index
        
        # Skip if in comment
        $beforeEntity = $text.Substring(0, $entityPos)
        $lastCommentOpen = $beforeEntity.LastIndexOf('<!--')
        $lastCommentClose = $beforeEntity.LastIndexOf('-->')
        if ($lastCommentOpen -gt $lastCommentClose) { continue }
        
        # Skip if in DOCTYPE
        $lastDoctypeOpen = $beforeEntity.LastIndexOf('<!DOCTYPE')
        $lastDoctypeClose = $beforeEntity.LastIndexOf(']>')
        if ($lastDoctypeOpen -gt $lastDoctypeClose) { continue }
        
        $entityLine = ($beforeEntity -split "`n").Count
        
        # Check if entity ends with semicolon
        if (-not $entityFull.EndsWith(';')) {
            [void]$issues.Add([PSCustomObject]@{
                File = $FilePath
                Line = $entityLine
                Column = $entityPos - $beforeEntity.LastIndexOf("`n")
                Code = 'ENTITY_NO_SEMICOLON'
                Severity = 'Error'
                Message = "EXPECTED: Entity reference to end with semicolon"
                Context = "FOUND: '&$entityName' without trailing ';'"
                Fix = "Change to '&$entityName;'"
                CanFix = $true
            })
            continue
        }
        
        # Check for illegal characters in entity name
        if ($entityName -match '[\s<>"''\\&]') {
            $badChar = [regex]::Match($entityName, '[\s<>"''\\&]').Value
            [void]$issues.Add([PSCustomObject]@{
                File = $FilePath
                Line = $entityLine
                Column = $entityPos - $beforeEntity.LastIndexOf("`n")
                Code = 'ENTITY_INVALID_CHAR'
                Severity = 'Error'
                Message = "EXPECTED: Entity name with only letters, numbers, underscore"
                Context = "FOUND: '&$entityName;' contains illegal character '$badChar'"
                Fix = "Remove illegal character or escape the '&' as '&amp;'"
                CanFix = $false
            })
        }
    }
    
    # Check XML well-formedness using .NET XmlReader
    try {
        $settings = [System.Xml.XmlReaderSettings]::new()
        $settings.IgnoreWhitespace = $false
        $settings.IgnoreComments = $false
        $settings.ProhibitDtd = $false
        $settings.XmlResolver = $null
        
        $reader = [System.Xml.XmlReader]::Create($FilePath, $settings)
        try {
            while ($reader.Read()) { }
        }
        finally {
            $reader.Close()
        }
    }
    catch {
        $errorMsg = $_.Exception.Message
        $lineMatch = [regex]::Match($errorMsg, 'line (\d+)')
        $lineNum = if ($lineMatch.Success) { [int]$lineMatch.Groups[1].Value } else { 0 }
        
        [void]$issues.Add([PSCustomObject]@{
            File = $FilePath
            Line = $lineNum
            Code = 'XML_WELLFORMED_ERROR'
            Severity = 'Error'
            Message = "XML parsing error: $errorMsg"
            CanFix = $false
        })
    }
    
    return $issues
}

# Helper function to get XML files (and handle TDB files by finding XML sources or parsing TDB directly)
function Get-XmlAndTdbFiles {
    param(
        [string]$Path,
        [bool]$Recurse = $true  # Default to recursive scanning to find all files in subdirectories
    )
    
    $xmlFiles = @()
    $tdbWarnings = @()
    $tdbFiles = @()
    
    # Load TDB parser module if available
    $tdbModule = Join-Path $PSScriptRoot 'TranscendenceModTools_TDBParser.ps1'
    if (Test-Path $tdbModule) {
        . $tdbModule
    }
    
    if (Test-Path $Path -PathType Leaf) {
        # Single file
        if ($Path -match '\.xml$') {
            $xmlFiles = @($Path)
        }
        elseif ($Path -match '\.(tdb|TDB)$') {
            # TDB file - check for XML source first
            $tdbName = [System.IO.Path]::GetFileNameWithoutExtension($Path)
            $tdbDir = [System.IO.Path]::GetDirectoryName($Path)
            
            $xmlSource = @(
                (Join-Path $tdbDir "$tdbName.xml"),
                (Join-Path $tdbDir "_Source\$tdbName.xml"),
                (Join-Path $tdbDir "${tdbName}_Source\$tdbName.xml")
            ) | Where-Object { Test-Path $_ }
            
            if ($xmlSource.Count -gt 0) {
                $xmlFiles = @($xmlSource[0])
            }
            else {
                # No XML source - can parse TDB directly if parser is available
                if (Test-Path $tdbModule) {
                    $tdbFiles += $Path
                }
                else {
                    $tdbWarnings += "TDB file cannot be scanned (no XML source and TDB parser not available): $(Split-Path -Leaf $Path)"
                }
            }
        }
    }
    else {
        # Directory
        $opts = @{ Filter = '*.xml' }
        if ($Recurse) { $opts.Recurse = $true }
        $xmlFiles = @(Get-ChildItem -LiteralPath $Path @opts | ForEach-Object { $_.FullName })
        
        # Check for TDB files
        $tdbOpts = @{ Include = '*.tdb','*.TDB' }
        if ($Recurse) { $tdbOpts.Recurse = $true }
        $allTdbFiles = @(Get-ChildItem -LiteralPath $Path @tdbOpts | 
            Select-Object -Unique -Property FullName | ForEach-Object { $_.FullName })
        
        foreach ($tdb in $allTdbFiles) {
            $tdbName = [System.IO.Path]::GetFileNameWithoutExtension($tdb)
            $tdbDir = [System.IO.Path]::GetDirectoryName($tdb)
            
            $xmlSource = @(
                (Join-Path $tdbDir "$tdbName.xml"),
                (Join-Path $tdbDir "_Source\$tdbName.xml"),
                (Join-Path $tdbDir "${tdbName}_Source\$tdbName.xml")
            ) | Where-Object { Test-Path $_ }
            
            if ($xmlSource.Count -gt 0 -and $xmlFiles -notcontains $xmlSource[0]) {
                $xmlFiles += $xmlSource[0]
            }
            elseif ($xmlSource.Count -eq 0) {
                # No XML source - can parse TDB directly if parser is available
                if (Test-Path $tdbModule) {
                    $tdbFiles += $tdb
                }
                else {
                    $tdbWarnings += "TDB file cannot be scanned (no XML source and TDB parser not available): $(Split-Path -Leaf $tdb)"
                }
            }
        }
    }
    
    return @{
        XmlFiles = $xmlFiles
        TdbFiles = $tdbFiles
        TdbWarnings = $tdbWarnings
    }
}

function Parse-ErrorMessage {
    param([string]$ErrorText)
    
    $results = [System.Collections.ArrayList]::new()
    
    # Extract line number
    $lineMatch = [regex]::Match($ErrorText, 'Line[:\s]*\(?(\d+)\)?')
    $lineNumber = if ($lineMatch.Success) { [int]$lineMatch.Groups[1].Value } else { 0 }
    
    # Extract file path
    $fileMatch = [regex]::Match($ErrorText, '([\w\\/\.\-_]+\.xml)', 'IgnoreCase')
    $filePath = if ($fileMatch.Success) { $fileMatch.Groups[1].Value } else { '' }
    
    foreach ($pattern in $script:ErrorPatterns) {
        if ($ErrorText -match $pattern.Pattern) {
            [void]$results.Add([PSCustomObject]@{
                Code = $pattern.Code
                Cause = $pattern.Cause
                Solution = $pattern.Solution
                Line = $lineNumber
                File = $filePath
                CanFix = $pattern.CanFix
            })
        }
    }
    
    if ($results.Count -eq 0) {
        [void]$results.Add([PSCustomObject]@{
            Code = 'UNKNOWN'
            Cause = 'Error pattern not recognized.'
            Solution = 'Check Transcendence forums or modding wiki.'
            Line = $lineNumber
            File = $filePath
            CanFix = $false
        })
    }
    
    return $results
}

# ============================================================
# DEBUG.LOG SCANNER
# ============================================================

<#
.SYNOPSIS
  Scans Debug.log for game errors and provides detailed diagnostics.
  
.DESCRIPTION
  Parses the Transcendence Debug.log file to find "Invalid entity" errors
  and other parsing failures. Provides actionable diagnostics including
  fuzzy matching for similar entity names.
#>
function Get-DebugLogErrors {
    param(
        [Parameter(Position=0)]
        [string]$DebugLogPath,
        
        [int]$MaxRecent = 50,
        
        [switch]$IncludeAllTypes
    )
    
    # Try to find Debug.log if not provided (optional - only if Transcendence is found)
    if ([string]::IsNullOrWhiteSpace($DebugLogPath)) {
        $transcendenceRoot = Find-TranscendenceRoot -StartPath $PSScriptRoot
        if ($transcendenceRoot) {
            $DebugLogPath = Join-Path $transcendenceRoot "Debug.log"
        }
        if (-not (Test-Path $DebugLogPath)) {
            return @{
                Success = $false
                Error = "Debug.log not found at: $DebugLogPath"
                Errors = @()
            }
        }
    }
    
    if (-not (Test-Path $DebugLogPath)) {
        return @{
            Success = $false
            Error = "Debug.log not found at: $DebugLogPath"
            Errors = @()
        }
    }
    
    $errors = [System.Collections.ArrayList]::new()
    $lines = [System.IO.File]::ReadAllLines($DebugLogPath)
    
    # Error patterns to detect
    $errorPatterns = @(
        @{
            Pattern = 'Error parsing ([^\s:]+):\s*([^:]+):\s*Line\((\d+)\):\s*Invalid entity:\s*(\w+)'
            Type = 'INVALID_ENTITY'
            Extract = { param($m) @{
                FilePath = $m.Groups[1].Value
                FileName = $m.Groups[2].Value
                Line = [int]$m.Groups[3].Value
                EntityName = $m.Groups[4].Value
            }}
        },
        @{
            Pattern = 'Error parsing ([^\s:]+):\s*([^:]+):\s*Line\((\d+)\):\s*(.+)'
            Type = 'PARSE_ERROR'
            Extract = { param($m) @{
                FilePath = $m.Groups[1].Value
                FileName = $m.Groups[2].Value
                Line = [int]$m.Groups[3].Value
                Message = $m.Groups[4].Value
            }}
        },
        @{
            Pattern = 'Unable to load extension:\s*(.+)'
            Type = 'EXTENSION_LOAD_FAILED'
            Extract = { param($m) @{
                ExtensionPath = $m.Groups[1].Value
            }}
        }
    )
    
    $lineNum = 0
    foreach ($line in $lines) {
        $lineNum++
        
        # Parse timestamp
        $timestampMatch = [regex]::Match($line, '^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s+(.*)$')
        $timestamp = if ($timestampMatch.Success) { $timestampMatch.Groups[1].Value } else { $null }
        $content = if ($timestampMatch.Success) { $timestampMatch.Groups[2].Value } else { $line }
        
        # Check each error pattern
        foreach ($ep in $errorPatterns) {
            $match = [regex]::Match($content, $ep.Pattern)
            if ($match.Success) {
                $extracted = & $ep.Extract $match
                
                $errorObj = [PSCustomObject]@{
                    Type = $ep.Type
                    Timestamp = $timestamp
                    LogLine = $lineNum
                    RawText = $line
                    Details = $extracted
                }
                
                [void]$errors.Add($errorObj)
                break
            }
        }
    }
    
    # Filter to most recent errors
    if ($errors.Count -gt $MaxRecent) {
        $errors = $errors[-$MaxRecent..-1]
    }
    
    return @{
        Success = $true
        LogPath = $DebugLogPath
        TotalErrors = $errors.Count
        Errors = @($errors)
    }
}

<#
.SYNOPSIS
  Builds a database of known entities from mod files.
  
.DESCRIPTION
  Scans Extensions and Collection folders to collect all defined
  entity names and their UNIDs for reference and fuzzy matching.
#>
<#
.SYNOPSIS
  Gets the Transcendence installation root from settings file or detects it.
  
.DESCRIPTION
  First checks for a settings file (TranscendenceTools.ini) in the Tools root.
  If found and contains TranscendencePath, uses that.
  Otherwise, searches common Steam installation locations.
#>
function Get-TranscendenceRootFromSettings {
    $toolPaths = Join-Path (Split-Path $PSScriptRoot -Parent) "Shared\ToolPaths.ps1"
    if (Test-Path $toolPaths) {
        . $toolPaths
        $path = Get-AamtTranscendencePath
        if ($path) { return $path }
    }

    # Legacy inline parse (same INI) if helper unavailable
    $toolsRoot = Split-Path $PSScriptRoot -Parent
    $settingsFile = Join-Path $toolsRoot "TranscendenceTools.ini"
    if (Test-Path $settingsFile) {
        $content = Get-Content $settingsFile -Raw
        if ($content -match '(?m)^\s*TranscendencePath\s*=\s*(.+)$') {
            $path = [System.Environment]::ExpandEnvironmentVariables($matches[1].Trim())
            if (Test-Path $path) { return $path }
        }
    }
    return $null
}

<#
.SYNOPSIS
  Detects the Transcendence installation root directory.
#>
function Find-TranscendenceRoot {
    param([string]$StartPath = $PSScriptRoot)
    
    # First, check settings file
    $settingsPath = Get-TranscendenceRootFromSettings
    if ($settingsPath) {
        return $settingsPath
    }
    
    # Then try common Steam installation locations
    $searchPaths = @(
        "${env:ProgramFiles(x86)}\Steam\steamapps\common\Transcendence",
        "${env:ProgramFiles}\Steam\steamapps\common\Transcendence",
        "$env:LOCALAPPDATA\Programs\Steam\steamapps\common\Transcendence",
        "$env:USERPROFILE\SteamLibrary\steamapps\common\Transcendence",
        "$env:USERPROFILE\Steam\steamapps\common\Transcendence"
    )
    
    # Check common drive letters for games partition (D:, E:, F:, etc.)
    $commonDrives = @('D', 'E', 'F', 'G', 'H')
    foreach ($drive in $commonDrives) {
        # Check for \games\Steam\ pattern (common for partitioned OS drives)
        $gamesPath = "${drive}:\games\Steam\steamapps\common\Transcendence"
        if (Test-Path $gamesPath) {
            $searchPaths += $gamesPath
        }
        
        # Check for \SteamLibrary\ pattern (common for additional Steam libraries)
        $steamLibraryPath = "${drive}:\SteamLibrary\steamapps\common\Transcendence"
        if (Test-Path $steamLibraryPath) {
            $searchPaths += $steamLibraryPath
        }
    }
    
    # Also try relative to script location
    $relativePaths = @(
        (Split-Path $StartPath -Parent),
        $StartPath
    )
    $searchPaths = $relativePaths + $searchPaths
    
    foreach ($path in $searchPaths) {
        if ([string]::IsNullOrWhiteSpace($path)) { continue }
        if (-not (Test-Path $path)) { continue }
        
        # Check for Transcendence.tdb (strong indicator)
        if (Test-Path (Join-Path $path "Transcendence.tdb")) {
            return $path
        }
        
        # Check for Extensions folder (common indicator)
        if (Test-Path (Join-Path $path "Extensions")) {
            return $path
        }
        
        # Check for Collection folder (common indicator)
        if (Test-Path (Join-Path $path "Collection")) {
            return $path
        }
    }
    
    # Fallback to old assumption if not found
    return (Split-Path $StartPath -Parent)
}

function Get-EntityDatabase {
    param(
        [string]$TranscendenceRoot
    )
    
    if ([string]::IsNullOrWhiteSpace($TranscendenceRoot)) {
        # Try to detect, but it's optional - most features work without it
        $TranscendenceRoot = Find-TranscendenceRoot -StartPath $PSScriptRoot
        if ([string]::IsNullOrWhiteSpace($TranscendenceRoot)) {
            # Return empty entities - tool can still work for single-file checking
            return @{}
        }
    }
    
    $entities = @{}  # EntityName -> { UNID, File, Prefix }

    $typeMapPath = Join-Path $PSScriptRoot 'VanillaDesignTypeMap.json'
    if (Test-Path -LiteralPath $typeMapPath) {
        try {
            $typeMap = Get-Content -LiteralPath $typeMapPath -Raw -Encoding UTF8 | ConvertFrom-Json
            foreach ($prop in $typeMap.unids.PSObject.Properties) {
                $entities[$prop.Name] = @{
                    Value = [string]$prop.Value
                    File = $typeMapPath
                    Prefix = ''
                }
            }
            if ($null -ne $typeMap.nameRemaps) {
                foreach ($prop in $typeMap.nameRemaps.PSObject.Properties) {
                    $oldName = $prop.Name
                    $newName = [string]$prop.Value
                    if ($entities.ContainsKey($newName) -and -not $entities.ContainsKey($oldName)) {
                        $entities[$oldName] = @{
                            Value = $entities[$newName].Value
                            File = $typeMapPath
                            Prefix = ''
                            ReplacedBy = $newName
                        }
                    }
                }
            }
        }
        catch { }
    }
    
    $extensionsPath = Join-Path $TranscendenceRoot "Extensions"
    $collectionPath = Join-Path $TranscendenceRoot "Collection"
    
    $searchPaths = @()
    if (Test-Path $extensionsPath) { $searchPaths += $extensionsPath }
    if (Test-Path $collectionPath) { $searchPaths += $collectionPath }
    
    foreach ($searchPath in $searchPaths) {
        $xmlFiles = Get-ChildItem -LiteralPath $searchPath -Filter '*.xml' -Recurse -ErrorAction SilentlyContinue
        
        foreach ($xmlFile in $xmlFiles) {
            try {
                $text = [System.IO.File]::ReadAllText($xmlFile.FullName, [System.Text.Encoding]::UTF8)
                
                # Extract entity definitions from DOCTYPE
                $entityDefPattern = '<!ENTITY\s+(\w+)\s+"([^"]+)"'
                $matches = [regex]::Matches($text, $entityDefPattern, 'IgnoreCase')
                
                foreach ($m in $matches) {
                    $entityName = $m.Groups[1].Value
                    $entityValue = $m.Groups[2].Value
                    
                    # Determine entity prefix (it=item, sc=ship, st=station, etc.)
                    $prefix = ''
                    if ($entityName -match '^([a-z]{2,3})[A-Z]') {
                        $prefix = $matches[1]
                    }
                    
                    if (-not $entities.ContainsKey($entityName)) {
                        $entities[$entityName] = @{
                            Value = $entityValue
                            File = $xmlFile.FullName
                            Prefix = $prefix
                        }
                    }
                }
            }
            catch { }
        }
    }
    
    return $entities
}

<#
.SYNOPSIS
  Finds similar entity names using fuzzy matching.
  
.DESCRIPTION
  Given an unknown entity name, finds similar entities from the database
  using Levenshtein distance and prefix matching.
#>
function Find-SimilarEntities {
    param(
        [Parameter(Mandatory)]
        [string]$EntityName,
        
        [hashtable]$EntityDatabase,
        
        [int]$MaxSuggestions = 5,
        
        [int]$MaxDistance = 3
    )
    
    if (-not $EntityDatabase -or $EntityDatabase.Count -eq 0) {
        return @()
    }
    
    # Simple Levenshtein distance function using 1D arrays for PowerShell compatibility
    function Get-LevenshteinDistance {
        param([string]$s1, [string]$s2)
        
        $n = $s1.Length
        $m = $s2.Length
        
        if ($n -eq 0) { return $m }
        if ($m -eq 0) { return $n }
        
        # Use two 1D arrays instead of 2D array for PowerShell compatibility
        $prevRow = [int[]]::new($m + 1)
        $currRow = [int[]]::new($m + 1)
        
        for ($j = 0; $j -le $m; $j++) { $prevRow[$j] = $j }
        
        for ($i = 1; $i -le $n; $i++) {
            $currRow[0] = $i
            
            for ($j = 1; $j -le $m; $j++) {
                $cost = if ($s1[$i - 1] -eq $s2[$j - 1]) { 0 } else { 1 }
                
                $deletion = $prevRow[$j] + 1
                $insertion = $currRow[$j - 1] + 1
                $substitution = $prevRow[$j - 1] + $cost
                
                $currRow[$j] = [Math]::Min([Math]::Min($deletion, $insertion), $substitution)
            }
            
            # Swap rows
            $temp = $prevRow
            $prevRow = $currRow
            $currRow = $temp
        }
        
        return $prevRow[$m]
    }
    
    $suggestions = [System.Collections.ArrayList]::new()
    
    # Extract prefix from the entity name (e.g., "it" from "itSolarArmor")
    $prefix = ''
    if ($EntityName -match '^([a-z]{2,3})') {
        $prefix = $matches[1]
    }
    
    foreach ($knownEntity in $EntityDatabase.Keys) {
        # Prioritize entities with the same prefix
        $knownPrefix = ''
        if ($knownEntity -match '^([a-z]{2,3})') {
            $knownPrefix = $matches[1]
        }
        
        $samePrefix = ($prefix -eq $knownPrefix)
        
        # Calculate distance
        $distance = Get-LevenshteinDistance -s1 $EntityName.ToLower() -s2 $knownEntity.ToLower()
        
        # Adjust score for prefix match
        $score = if ($samePrefix) { $distance } else { $distance + 2 }
        
        if ($distance -le $MaxDistance -or $samePrefix) {
            [void]$suggestions.Add([PSCustomObject]@{
                EntityName = $knownEntity
                Distance = $distance
                Score = $score
                SamePrefix = $samePrefix
                Value = $EntityDatabase[$knownEntity].Value
                File = $EntityDatabase[$knownEntity].File
            })
        }
    }
    
    # Sort by score (lower is better) and return top suggestions
    $sorted = $suggestions | Sort-Object Score | Select-Object -First $MaxSuggestions
    
    return @($sorted)
}

<#
.SYNOPSIS
  Diagnoses an "Invalid entity" error from Debug.log.
  
.DESCRIPTION
  Given an invalid entity error, provides detailed diagnostics including:
  - Where the entity is used
  - What type of entity it appears to be (item, ship, station, etc.)
  - Similar entities that may be the intended one
  - How to fix the issue
#>
function Get-InvalidEntityDiagnosis {
    param(
        [Parameter(Mandatory)]
        [string]$EntityName,
        
        [string]$FilePath,
        
        [int]$Line = 0,
        
        [hashtable]$EntityDatabase
    )
    
    $diagnosis = [PSCustomObject]@{
        EntityName = $EntityName
        File = $FilePath
        Line = $Line
        EntityType = 'Unknown'
        EntityTypeDescription = ''
        Suggestions = @()
        FixSteps = @()
    }
    
    # Determine entity type from prefix
    $entityPrefixes = @{
        'it' = @{ Type = 'ItemType'; Description = 'Item (weapon, armor, device, misc)' }
        'sc' = @{ Type = 'ShipClass'; Description = 'Ship class' }
        'st' = @{ Type = 'StationType'; Description = 'Station type' }
        'vt' = @{ Type = 'VirtualType'; Description = 'Virtual type (effect tables, etc.)' }
        'rs' = @{ Type = 'Resource'; Description = 'Resource (image, sound)' }
        'ef' = @{ Type = 'Effect'; Description = 'Effect type' }
        'sn' = @{ Type = 'Sound'; Description = 'Sound type' }
        'sv' = @{ Type = 'Sovereign'; Description = 'Sovereign (faction)' }
        'ds' = @{ Type = 'DockScreen'; Description = 'Dock screen' }
        'tb' = @{ Type = 'Table'; Description = 'Table (item/encounter tables)' }
        'ba' = @{ Type = 'Base'; Description = 'Base type (inheritance)' }
        'ev' = @{ Type = 'Event'; Description = 'Event type' }
        'ch' = @{ Type = 'Character'; Description = 'Character type' }
        'se' = @{ Type = 'SystemElement'; Description = 'System element' }
        'ov' = @{ Type = 'Overlay'; Description = 'Overlay type' }
        'pw' = @{ Type = 'Power'; Description = 'Power type' }
        'unid' = @{ Type = 'UNID'; Description = 'Extension/Library UNID' }
    }
    
    # Extract prefix (first 2-4 lowercase letters before first uppercase)
    $prefix = ''
    $prefixMatch = [regex]::Match($EntityName, '^([a-z]{2,4})')
    if ($prefixMatch.Success) {
        $prefix = $prefixMatch.Groups[1].Value
    }
    
    if ($prefix -and $entityPrefixes.ContainsKey($prefix)) {
        $diagnosis.EntityType = $entityPrefixes[$prefix].Type
        $diagnosis.EntityTypeDescription = $entityPrefixes[$prefix].Description
    }
    
    # Find similar entities
    if ($EntityDatabase -and $EntityDatabase.Count -gt 0) {
        $suggestions = Find-SimilarEntities -EntityName $EntityName -EntityDatabase $EntityDatabase -MaxSuggestions 5
        $diagnosis.Suggestions = $suggestions
    }
    
    # Build fix steps
    $fixSteps = @()
    $fixSteps += "1. Open the mod file: $FilePath"
    $fixSteps += "2. Go to line $Line"
    $fixSteps += "3. Check if '&$EntityName;' is spelled correctly"
    $fixSteps += "4. Ensure the entity is defined in the DOCTYPE section:"
    $fixSteps += "   <!ENTITY $EntityName ""0xYOURUNID"">"
    
    if ($diagnosis.Suggestions.Count -gt 0) {
        $fixSteps += "5. If this is a typo, you may have meant one of these:"
        foreach ($suggestion in $diagnosis.Suggestions) {
            $fixSteps += "   - $($suggestion.EntityName) (from $(Split-Path -Leaf $suggestion.File))"
        }
    }
    else {
        $fixSteps += "5. If referencing a base game entity, add the correct definition to your DOCTYPE"
        $fixSteps += "   Reference: https://wiki.kronosaur.com/doku.php/modding/unid_database"
    }
    
    $diagnosis.FixSteps = $fixSteps
    
    return $diagnosis
}

<#
.SYNOPSIS
  Scans Debug.log and provides diagnostics for all recent errors.
#>
function Get-DebugLogDiagnostics {
    param(
        [string]$DebugLogPath,
        [int]$MaxRecent = 20
    )
    
    $result = Get-DebugLogErrors -DebugLogPath $DebugLogPath -MaxRecent $MaxRecent
    
    if (-not $result.Success) {
        return $result
    }
    
    # Build entity database for fuzzy matching
    $entityDb = Get-EntityDatabase
    
    $diagnostics = [System.Collections.ArrayList]::new()
    
    foreach ($error in $result.Errors) {
        $diag = [PSCustomObject]@{
            Error = $error
            Diagnosis = $null
        }
        
        if ($error.Type -eq 'INVALID_ENTITY') {
            $diag.Diagnosis = Get-InvalidEntityDiagnosis `
                -EntityName $error.Details.EntityName `
                -FilePath $error.Details.FilePath `
                -Line $error.Details.Line `
                -EntityDatabase $entityDb
        }
        
        [void]$diagnostics.Add($diag)
    }
    
    return @{
        Success = $true
        LogPath = $result.LogPath
        TotalErrors = $result.TotalErrors
        Diagnostics = @($diagnostics)
        EntityDatabaseSize = $entityDb.Count
    }
}

# ============================================================
# GUI
# ============================================================

function Show-MainGui {
    Add-Type -AssemblyName System.Windows.Forms
    Add-Type -AssemblyName System.Drawing
    
    [System.Windows.Forms.Application]::EnableVisualStyles()
    
    # Colors
    $bgDark = [System.Drawing.Color]::FromArgb(25, 25, 30)
    $bgMedium = [System.Drawing.Color]::FromArgb(35, 35, 42)
    $bgLight = [System.Drawing.Color]::FromArgb(45, 45, 55)
    $accent = [System.Drawing.Color]::FromArgb(80, 140, 200)
    $accentGreen = [System.Drawing.Color]::FromArgb(70, 160, 70)
    $accentRed = [System.Drawing.Color]::FromArgb(200, 80, 80)
    $accentYellow = [System.Drawing.Color]::FromArgb(200, 180, 80)
    $textWhite = [System.Drawing.Color]::White
    $textGray = [System.Drawing.Color]::FromArgb(180, 180, 180)
    
    # Main Form
    $form = [System.Windows.Forms.Form]::new()
    $form.Text = 'Transcendence Mod Tools'
    $form.Size = [System.Drawing.Size]::new(1450, 800)
    $form.StartPosition = 'CenterScreen'
    $form.BackColor = $bgDark
    $form.ForeColor = $textWhite
    $form.Font = [System.Drawing.Font]::new('Segoe UI', 9)
    $form.AllowDrop = $true
    
    # Menu Bar
    $menuStrip = [System.Windows.Forms.MenuStrip]::new()
    $menuStrip.BackColor = $bgMedium
    $menuStrip.ForeColor = $textWhite
    
    # File Menu
    $fileMenu = [System.Windows.Forms.ToolStripMenuItem]::new('File')
    $fileMenu.ForeColor = $textWhite
    
    $exportItem = [System.Windows.Forms.ToolStripMenuItem]::new('Export Report...')
    $exportItem.ForeColor = $textWhite
    $fileMenu.DropDownItems.Add($exportItem) | Out-Null
    
    $exitItem = [System.Windows.Forms.ToolStripMenuItem]::new('Exit')
    $exitItem.ForeColor = $textWhite
    $fileMenu.DropDownItems.Add($exitItem) | Out-Null
    
    # Help Menu
    $helpMenu = [System.Windows.Forms.ToolStripMenuItem]::new('Help')
    $helpMenu.ForeColor = $textWhite
    
    $aboutItem = [System.Windows.Forms.ToolStripMenuItem]::new('About...')
    $aboutItem.ForeColor = $textWhite
    $helpMenu.DropDownItems.Add($aboutItem) | Out-Null
    
    $quickRefItem = [System.Windows.Forms.ToolStripMenuItem]::new('Quick Reference')
    $quickRefItem.ForeColor = $textWhite
    $helpMenu.DropDownItems.Add($quickRefItem) | Out-Null
    
    $menuStrip.Items.Add($fileMenu) | Out-Null
    $menuStrip.Items.Add($helpMenu) | Out-Null
    $form.MainMenuStrip = $menuStrip
    $form.Controls.Add($menuStrip)
    
    # Tab Control
    $tabs = [System.Windows.Forms.TabControl]::new()
    $tabs.Dock = 'Fill'
    $tabs.BackColor = $bgMedium
    $tabs.ForeColor = $textWhite
    $form.Controls.Add($tabs)
    
    # ============================================================
    # TAB 1: XML CHECKER
    # ============================================================
    $tabChecker = [System.Windows.Forms.TabPage]::new()
    $tabChecker.Text = '  XML Checker  '
    $tabChecker.BackColor = $bgDark
    $tabChecker.Padding = [System.Windows.Forms.Padding]::new(10)
    $tabs.TabPages.Add($tabChecker)
    
    # Path panel
    $pnlPath = [System.Windows.Forms.Panel]::new()
    $pnlPath.Dock = 'Top'
    $pnlPath.Height = 50
    $pnlPath.BackColor = $bgMedium
    $tabChecker.Controls.Add($pnlPath)
    
    $lblPath = [System.Windows.Forms.Label]::new()
    $lblPath.Text = 'Path:'
    $lblPath.Location = [System.Drawing.Point]::new(10, 15)
    $lblPath.AutoSize = $true
    $lblPath.ForeColor = $textWhite
    $pnlPath.Controls.Add($lblPath)
    
    $txtPath = [System.Windows.Forms.TextBox]::new()
    $txtPath.Location = [System.Drawing.Point]::new(50, 12)
    $txtPath.Size = [System.Drawing.Size]::new(750, 25)
    $txtPath.BackColor = $bgLight
    $txtPath.ForeColor = $textWhite
    $txtPath.BorderStyle = 'FixedSingle'
    $pnlPath.Controls.Add($txtPath)
    
    $btnBrowse = [System.Windows.Forms.Button]::new()
    $btnBrowse.Text = 'Browse...'
    $btnBrowse.Location = [System.Drawing.Point]::new(770, 10)
    $btnBrowse.Size = [System.Drawing.Size]::new(80, 28)
    $btnBrowse.BackColor = $bgLight
    $btnBrowse.ForeColor = $textWhite
    $btnBrowse.FlatStyle = 'Flat'
    $pnlPath.Controls.Add($btnBrowse)
    
    $chkRecurse = [System.Windows.Forms.CheckBox]::new()
    $chkRecurse.Text = 'Recurse'
    $chkRecurse.Location = [System.Drawing.Point]::new(860, 14)
    $chkRecurse.AutoSize = $true
    $chkRecurse.ForeColor = $textWhite
    $chkRecurse.Checked = $true
    $pnlPath.Controls.Add($chkRecurse)
    
    $btnScan = [System.Windows.Forms.Button]::new()
    $btnScan.Text = 'Scan'
    $btnScan.Location = [System.Drawing.Point]::new(950, 10)
    $btnScan.Size = [System.Drawing.Size]::new(80, 28)
    $btnScan.BackColor = $accentGreen
    $btnScan.ForeColor = $textWhite
    $btnScan.FlatStyle = 'Flat'
    $pnlPath.Controls.Add($btnScan)
    
    $btnFix = [System.Windows.Forms.Button]::new()
    $btnFix.Text = 'Auto-Fix'
    $btnFix.Location = [System.Drawing.Point]::new(1040, 10)
    $btnFix.Size = [System.Drawing.Size]::new(80, 28)
    $btnFix.BackColor = $accent
    $btnFix.ForeColor = $textWhite
    $btnFix.FlatStyle = 'Flat'
    $pnlPath.Controls.Add($btnFix)
    
    $btnFormat = [System.Windows.Forms.Button]::new()
    $btnFormat.Text = 'Format'
    $btnFormat.Location = [System.Drawing.Point]::new(1130, 10)
    $btnFormat.Size = [System.Drawing.Size]::new(80, 28)
    $btnFormat.BackColor = [System.Drawing.Color]::FromArgb(140, 100, 200)
    $btnFormat.ForeColor = $textWhite
    $btnFormat.FlatStyle = 'Flat'
    $pnlPath.Controls.Add($btnFormat)
    
    $btnExport = [System.Windows.Forms.Button]::new()
    $btnExport.Text = 'Export Log'
    $btnExport.Location = [System.Drawing.Point]::new(1220, 10)
    $btnExport.Size = [System.Drawing.Size]::new(90, 28)
    $btnExport.BackColor = [System.Drawing.Color]::FromArgb(100, 140, 100)
    $btnExport.ForeColor = $textWhite
    $btnExport.FlatStyle = 'Flat'
    $pnlPath.Controls.Add($btnExport)
    
    # Export log button handler
    $btnExport.Add_Click({
        $saveDialog = [System.Windows.Forms.SaveFileDialog]::new()
        $saveDialog.Filter = 'Text Files (*.txt)|*.txt|All Files (*.*)|*.*'
        $saveDialog.FileName = "ScanResults_$(Get-Date -Format 'yyyyMMdd_HHmmss').txt"
        $saveDialog.Title = 'Export Scan Results Log'
        
        if ($saveDialog.ShowDialog() -eq 'OK') {
            try {
                $rtbLog.SaveFile($saveDialog.FileName, [System.Windows.Forms.RichTextBoxStreamType]::PlainText)
                [System.Windows.Forms.MessageBox]::Show("Log exported successfully to:`n$($saveDialog.FileName)", 'Export Complete', 'OK', 'Information')
            }
            catch {
                [System.Windows.Forms.MessageBox]::Show("Error exporting log: $_", 'Export Error', 'OK', 'Error')
            }
        }
    })
    
    # Split container for grid and log
    $splitContainer = [System.Windows.Forms.SplitContainer]::new()
    $splitContainer.Dock = 'Fill'
    $splitContainer.Orientation = 'Horizontal'
    $splitContainer.SplitterDistance = 400
    $splitContainer.BackColor = $bgDark
    $tabChecker.Controls.Add($splitContainer)
    
    # Results grid (top panel)
    $grid = [System.Windows.Forms.DataGridView]::new()
    $grid.Dock = 'Fill'
    $grid.BackgroundColor = $bgDark
    $grid.ForeColor = $textWhite
    $grid.GridColor = $bgLight
    $grid.BorderStyle = 'None'
    $grid.RowHeadersVisible = $false
    $grid.AllowUserToAddRows = $false
    $grid.AllowUserToDeleteRows = $false
    $grid.ReadOnly = $true
    $grid.SelectionMode = 'FullRowSelect'
    $grid.AutoSizeColumnsMode = 'Fill'
    $grid.DefaultCellStyle.BackColor = $bgDark
    $grid.DefaultCellStyle.ForeColor = $textWhite
    $grid.DefaultCellStyle.SelectionBackColor = $accent
    $grid.ColumnHeadersDefaultCellStyle.BackColor = $bgMedium
    $grid.ColumnHeadersDefaultCellStyle.ForeColor = $textWhite
    $grid.EnableHeadersVisualStyles = $false
    
    $grid.Columns.Add('Severity', 'Severity') | Out-Null
    $grid.Columns.Add('Code', 'Code') | Out-Null
    $grid.Columns.Add('Line', 'Line') | Out-Null
    $grid.Columns.Add('Message', 'Message') | Out-Null
    $grid.Columns.Add('File', 'File') | Out-Null
    $grid.Columns['Severity'].Width = 70
    $grid.Columns['Code'].Width = 150
    $grid.Columns['Line'].Width = 50
    $grid.Columns['Message'].Width = 400
    $grid.Columns['File'].Width = 400
    
    $splitContainer.Panel1.Controls.Add($grid)
    
    # Results log (bottom panel)
    $rtbLog = [System.Windows.Forms.RichTextBox]::new()
    $rtbLog.Dock = 'Fill'
    $rtbLog.BackColor = $bgLight
    $rtbLog.ForeColor = $textWhite
    $rtbLog.Font = [System.Drawing.Font]::new('Consolas', 9)
    $rtbLog.ReadOnly = $true
    $rtbLog.BorderStyle = 'None'
    $splitContainer.Panel2.Controls.Add($rtbLog)
    
    # Log label
    $lblLog = [System.Windows.Forms.Label]::new()
    $lblLog.Text = 'Scan Results Log:'
    $lblLog.Dock = 'Top'
    $lblLog.Height = 20
    $lblLog.BackColor = $bgMedium
    $lblLog.ForeColor = $textWhite
    $lblLog.Padding = [System.Windows.Forms.Padding]::new(5, 2, 0, 0)
    $splitContainer.Panel2.Controls.Add($lblLog)
    $splitContainer.Panel2.Controls.SetChildIndex($lblLog, 0)
    
    # Status bar
    $lblStatus = [System.Windows.Forms.Label]::new()
    $lblStatus.Dock = 'Bottom'
    $lblStatus.Height = 25
    $lblStatus.BackColor = $bgMedium
    $lblStatus.ForeColor = $textGray
    $lblStatus.Text = 'Ready'
    $lblStatus.TextAlign = 'MiddleLeft'
    $lblStatus.Padding = [System.Windows.Forms.Padding]::new(5, 0, 0, 0)
    $tabChecker.Controls.Add($lblStatus)
    
    # ============================================================
    # TAB 2: ERROR HELPER
    # ============================================================
    $tabHelper = [System.Windows.Forms.TabPage]::new()
    $tabHelper.Text = '  Error Helper  '
    $tabHelper.BackColor = $bgDark
    $tabHelper.Padding = [System.Windows.Forms.Padding]::new(10)
    $tabs.TabPages.Add($tabHelper)
    
    $lblInput = [System.Windows.Forms.Label]::new()
    $lblInput.Text = 'Paste your Transcendence error message:'
    $lblInput.Location = [System.Drawing.Point]::new(10, 10)
    $lblInput.AutoSize = $true
    $lblInput.ForeColor = $textWhite
    $tabHelper.Controls.Add($lblInput)
    
    $txtError = [System.Windows.Forms.TextBox]::new()
    $txtError.Location = [System.Drawing.Point]::new(10, 35)
    $txtError.Size = [System.Drawing.Size]::new(1140, 120)
    $txtError.Multiline = $true
    $txtError.ScrollBars = 'Vertical'
    $txtError.BackColor = $bgLight
    $txtError.ForeColor = $textWhite
    $txtError.Font = [System.Drawing.Font]::new('Consolas', 10)
    $tabHelper.Controls.Add($txtError)
    
    $btnAnalyze = [System.Windows.Forms.Button]::new()
    $btnAnalyze.Text = 'Analyze Error'
    $btnAnalyze.Location = [System.Drawing.Point]::new(10, 165)
    $btnAnalyze.Size = [System.Drawing.Size]::new(120, 30)
    $btnAnalyze.BackColor = $accentGreen
    $btnAnalyze.ForeColor = $textWhite
    $btnAnalyze.FlatStyle = 'Flat'
    $tabHelper.Controls.Add($btnAnalyze)
    
    $btnClear = [System.Windows.Forms.Button]::new()
    $btnClear.Text = 'Clear'
    $btnClear.Location = [System.Drawing.Point]::new(140, 165)
    $btnClear.Size = [System.Drawing.Size]::new(80, 30)
    $btnClear.BackColor = $bgLight
    $btnClear.ForeColor = $textWhite
    $btnClear.FlatStyle = 'Flat'
    $tabHelper.Controls.Add($btnClear)
    
    $lblOutput = [System.Windows.Forms.Label]::new()
    $lblOutput.Text = 'Analysis:'
    $lblOutput.Location = [System.Drawing.Point]::new(10, 210)
    $lblOutput.AutoSize = $true
    $lblOutput.ForeColor = $textWhite
    $tabHelper.Controls.Add($lblOutput)
    
    $txtResult = [System.Windows.Forms.RichTextBox]::new()
    $txtResult.Location = [System.Drawing.Point]::new(10, 235)
    $txtResult.Size = [System.Drawing.Size]::new(1140, 450)
    $txtResult.BackColor = $bgDark
    $txtResult.ForeColor = $textWhite
    $txtResult.Font = [System.Drawing.Font]::new('Consolas', 10)
    $txtResult.ReadOnly = $true
    $txtResult.BorderStyle = 'None'
    $tabHelper.Controls.Add($txtResult)
    
    # ============================================================
    # TAB 3: PROJECT HEALTH
    # ============================================================
    $tabHealth = [System.Windows.Forms.TabPage]::new()
    $tabHealth.Text = '  Project Health  '
    $tabHealth.BackColor = $bgDark
    $tabHealth.Padding = [System.Windows.Forms.Padding]::new(10)
    $tabs.TabPages.Add($tabHealth)
    
    $lblHealthPath = [System.Windows.Forms.Label]::new()
    $lblHealthPath.Text = 'Project Path:'
    $lblHealthPath.Location = [System.Drawing.Point]::new(10, 10)
    $lblHealthPath.AutoSize = $true
    $lblHealthPath.ForeColor = $textWhite
    $tabHealth.Controls.Add($lblHealthPath)
    
    $txtHealthPath = [System.Windows.Forms.TextBox]::new()
    $txtHealthPath.Location = [System.Drawing.Point]::new(100, 8)
    $txtHealthPath.Size = [System.Drawing.Size]::new(800, 25)
    $txtHealthPath.BackColor = $bgLight
    $txtHealthPath.ForeColor = $textWhite
    $txtHealthPath.BorderStyle = 'FixedSingle'
    $tabHealth.Controls.Add($txtHealthPath)
    
    $btnHealthBrowse = [System.Windows.Forms.Button]::new()
    $btnHealthBrowse.Text = 'Browse...'
    $btnHealthBrowse.Location = [System.Drawing.Point]::new(910, 6)
    $btnHealthBrowse.Size = [System.Drawing.Size]::new(80, 28)
    $btnHealthBrowse.BackColor = $bgLight
    $btnHealthBrowse.ForeColor = $textWhite
    $btnHealthBrowse.FlatStyle = 'Flat'
    $tabHealth.Controls.Add($btnHealthBrowse)
    
    $btnHealthScan = [System.Windows.Forms.Button]::new()
    $btnHealthScan.Text = 'Generate Report'
    $btnHealthScan.Location = [System.Drawing.Point]::new(1000, 6)
    $btnHealthScan.Size = [System.Drawing.Size]::new(120, 28)
    $btnHealthScan.BackColor = $accentGreen
    $btnHealthScan.ForeColor = $textWhite
    $btnHealthScan.FlatStyle = 'Flat'
    $tabHealth.Controls.Add($btnHealthScan)
    
    $btnResourceCheck = [System.Windows.Forms.Button]::new()
    $btnResourceCheck.Text = 'Resource Integrity'
    $btnResourceCheck.Location = [System.Drawing.Point]::new(1130, 6)
    $btnResourceCheck.Size = [System.Drawing.Size]::new(140, 28)
    $btnResourceCheck.BackColor = $accent
    $btnResourceCheck.ForeColor = $textWhite
    $btnResourceCheck.FlatStyle = 'Flat'
    $tabHealth.Controls.Add($btnResourceCheck)
    
    $txtHealthReport = [System.Windows.Forms.RichTextBox]::new()
    $txtHealthReport.Location = [System.Drawing.Point]::new(10, 45)
    $txtHealthReport.Size = [System.Drawing.Size]::new(1140, 640)
    $txtHealthReport.BackColor = $bgDark
    $txtHealthReport.ForeColor = $textWhite
    $txtHealthReport.Font = [System.Drawing.Font]::new('Consolas', 9)
    $txtHealthReport.ReadOnly = $true
    $txtHealthReport.BorderStyle = 'None'
    $tabHealth.Controls.Add($txtHealthReport)
    
    # ============================================================
    # TAB 4: UNID MANAGER
    # ============================================================
    $tabUnid = [System.Windows.Forms.TabPage]::new()
    $tabUnid.Text = '  UNID Manager  '
    $tabUnid.BackColor = $bgDark
    $tabUnid.Padding = [System.Windows.Forms.Padding]::new(10)
    $tabs.TabPages.Add($tabUnid)
    
    $lblUnidPath = [System.Windows.Forms.Label]::new()
    $lblUnidPath.Text = 'Mod Path:'
    $lblUnidPath.Location = [System.Drawing.Point]::new(10, 10)
    $lblUnidPath.AutoSize = $true
    $lblUnidPath.ForeColor = $textWhite
    $tabUnid.Controls.Add($lblUnidPath)
    
    $txtUnidPath = [System.Windows.Forms.TextBox]::new()
    $txtUnidPath.Location = [System.Drawing.Point]::new(80, 8)
    $txtUnidPath.Size = [System.Drawing.Size]::new(700, 25)
    $txtUnidPath.BackColor = $bgLight
    $txtUnidPath.ForeColor = $textWhite
    $txtUnidPath.BorderStyle = 'FixedSingle'
    $tabUnid.Controls.Add($txtUnidPath)
    
    $btnUnidBrowse = [System.Windows.Forms.Button]::new()
    $btnUnidBrowse.Text = 'Browse...'
    $btnUnidBrowse.Location = [System.Drawing.Point]::new(790, 6)
    $btnUnidBrowse.Size = [System.Drawing.Size]::new(80, 28)
    $btnUnidBrowse.BackColor = $bgLight
    $btnUnidBrowse.ForeColor = $textWhite
    $btnUnidBrowse.FlatStyle = 'Flat'
    $tabUnid.Controls.Add($btnUnidBrowse)
    
    $btnUnidScan = [System.Windows.Forms.Button]::new()
    $btnUnidScan.Text = 'Scan UNIDs'
    $btnUnidScan.Location = [System.Drawing.Point]::new(880, 6)
    $btnUnidScan.Size = [System.Drawing.Size]::new(100, 28)
    $btnUnidScan.BackColor = $accentGreen
    $btnUnidScan.ForeColor = $textWhite
    $btnUnidScan.FlatStyle = 'Flat'
    $tabUnid.Controls.Add($btnUnidScan)
    
    $btnUnidIntelligence = [System.Windows.Forms.Button]::new()
    $btnUnidIntelligence.Text = 'Intelligence'
    $btnUnidIntelligence.Location = [System.Drawing.Point]::new(990, 6)
    $btnUnidIntelligence.Size = [System.Drawing.Size]::new(100, 28)
    $btnUnidIntelligence.BackColor = $accent
    $btnUnidIntelligence.ForeColor = $textWhite
    $btnUnidIntelligence.FlatStyle = 'Flat'
    $tabUnid.Controls.Add($btnUnidIntelligence)
    
    $btnUnidGenerate = [System.Windows.Forms.Button]::new()
    $btnUnidGenerate.Text = 'Generate'
    $btnUnidGenerate.Location = [System.Drawing.Point]::new(1100, 6)
    $btnUnidGenerate.Size = [System.Drawing.Size]::new(80, 28)
    $btnUnidGenerate.BackColor = $accent
    $btnUnidGenerate.ForeColor = $textWhite
    $btnUnidGenerate.FlatStyle = 'Flat'
    $tabUnid.Controls.Add($btnUnidGenerate)
    
    $gridUnid = [System.Windows.Forms.DataGridView]::new()
    $gridUnid.Location = [System.Drawing.Point]::new(10, 45)
    $gridUnid.Size = [System.Drawing.Size]::new(1160, 500)
    $gridUnid.BackgroundColor = $bgDark
    $gridUnid.ForeColor = $textWhite
    $gridUnid.GridColor = $bgLight
    $gridUnid.BorderStyle = 'None'
    $gridUnid.RowHeadersVisible = $false
    $gridUnid.AllowUserToAddRows = $false
    $gridUnid.ReadOnly = $true
    $gridUnid.SelectionMode = 'FullRowSelect'
    $gridUnid.AutoSizeColumnsMode = 'Fill'
    $gridUnid.DefaultCellStyle.BackColor = $bgDark
    $gridUnid.DefaultCellStyle.ForeColor = $textWhite
    $gridUnid.DefaultCellStyle.SelectionBackColor = $accent
    $gridUnid.ColumnHeadersDefaultCellStyle.BackColor = $bgMedium
    $gridUnid.ColumnHeadersDefaultCellStyle.ForeColor = $textWhite
    $gridUnid.EnableHeadersVisualStyles = $false
    
    $gridUnid.Columns.Add('UNID', 'UNID') | Out-Null
    $gridUnid.Columns.Add('Entity', 'Entity Name') | Out-Null
    $gridUnid.Columns.Add('References', 'References') | Out-Null
    $gridUnid.Columns.Add('Range', 'Range') | Out-Null
    $gridUnid.Columns.Add('File', 'File') | Out-Null
    $gridUnid.Columns['UNID'].Width = 120
    $gridUnid.Columns['Entity'].Width = 200
    $gridUnid.Columns['References'].Width = 100
    $gridUnid.Columns['Range'].Width = 150
    $gridUnid.Columns['File'].Width = 390
    
    $tabUnid.Controls.Add($gridUnid)
    
    $lblUnidStatus = [System.Windows.Forms.Label]::new()
    $lblUnidStatus.Location = [System.Drawing.Point]::new(10, 555)
    $lblUnidStatus.Size = [System.Drawing.Size]::new(1160, 25)
    $lblUnidStatus.BackColor = $bgMedium
    $lblUnidStatus.ForeColor = $textGray
    $lblUnidStatus.Text = 'Ready'
    $lblUnidStatus.TextAlign = 'MiddleLeft'
    $lblUnidStatus.Padding = [System.Windows.Forms.Padding]::new(5, 0, 0, 0)
    $tabUnid.Controls.Add($lblUnidStatus)
    
    # ============================================================
    # TAB 5: CROSS-MOD COMPATIBILITY
    # ============================================================
    $tabCompat = [System.Windows.Forms.TabPage]::new()
    $tabCompat.Text = '  Cross-Mod Check  '
    $tabCompat.BackColor = $bgDark
    $tabCompat.Padding = [System.Windows.Forms.Padding]::new(10)
    $tabs.TabPages.Add($tabCompat)
    
    $lblCompatPath = [System.Windows.Forms.Label]::new()
    $lblCompatPath.Text = 'Extensions Folder:'
    $lblCompatPath.Location = [System.Drawing.Point]::new(10, 10)
    $lblCompatPath.AutoSize = $true
    $lblCompatPath.ForeColor = $textWhite
    $tabCompat.Controls.Add($lblCompatPath)
    
    $txtCompatPath = [System.Windows.Forms.TextBox]::new()
    $txtCompatPath.Location = [System.Drawing.Point]::new(120, 8)
    $txtCompatPath.Size = [System.Drawing.Size]::new(800, 25)
    $txtCompatPath.BackColor = $bgLight
    $txtCompatPath.ForeColor = $textWhite
    $txtCompatPath.BorderStyle = 'FixedSingle'
    $tabCompat.Controls.Add($txtCompatPath)
    
    $btnCompatBrowse = [System.Windows.Forms.Button]::new()
    $btnCompatBrowse.Text = 'Browse...'
    $btnCompatBrowse.Location = [System.Drawing.Point]::new(930, 6)
    $btnCompatBrowse.Size = [System.Drawing.Size]::new(80, 28)
    $btnCompatBrowse.BackColor = $bgLight
    $btnCompatBrowse.ForeColor = $textWhite
    $btnCompatBrowse.FlatStyle = 'Flat'
    $tabCompat.Controls.Add($btnCompatBrowse)
    
    $btnCompatScan = [System.Windows.Forms.Button]::new()
    $btnCompatScan.Text = 'Check Compatibility'
    $btnCompatScan.Location = [System.Drawing.Point]::new(1020, 6)
    $btnCompatScan.Size = [System.Drawing.Size]::new(150, 28)
    $btnCompatScan.BackColor = $accentGreen
    $btnCompatScan.ForeColor = $textWhite
    $btnCompatScan.FlatStyle = 'Flat'
    $tabCompat.Controls.Add($btnCompatScan)
    
    $txtCompatReport = [System.Windows.Forms.RichTextBox]::new()
    $txtCompatReport.Location = [System.Drawing.Point]::new(10, 45)
    $txtCompatReport.Size = [System.Drawing.Size]::new(1160, 640)
    $txtCompatReport.BackColor = $bgDark
    $txtCompatReport.ForeColor = $textWhite
    $txtCompatReport.Font = [System.Drawing.Font]::new('Consolas', 9)
    $txtCompatReport.ReadOnly = $true
    $txtCompatReport.BorderStyle = 'None'
    $tabCompat.Controls.Add($txtCompatReport)
    
    # ============================================================
    # TAB 6: DEPENDENCY GRAPH
    # ============================================================
    $tabDependency = [System.Windows.Forms.TabPage]::new()
    $tabDependency.Text = '  Dependency Graph  '
    $tabDependency.BackColor = $bgDark
    $tabDependency.Padding = [System.Windows.Forms.Padding]::new(10)
    $tabs.TabPages.Add($tabDependency)
    
    $lblDepPath = [System.Windows.Forms.Label]::new()
    $lblDepPath.Text = 'Mod Path:'
    $lblDepPath.Location = [System.Drawing.Point]::new(10, 10)
    $lblDepPath.AutoSize = $true
    $lblDepPath.ForeColor = $textWhite
    $tabDependency.Controls.Add($lblDepPath)
    
    $txtDepPath = [System.Windows.Forms.TextBox]::new()
    $txtDepPath.Location = [System.Drawing.Point]::new(80, 8)
    $txtDepPath.Size = [System.Drawing.Size]::new(800, 25)
    $txtDepPath.BackColor = $bgLight
    $txtDepPath.ForeColor = $textWhite
    $txtDepPath.BorderStyle = 'FixedSingle'
    $tabDependency.Controls.Add($txtDepPath)
    
    $btnDepBrowse = [System.Windows.Forms.Button]::new()
    $btnDepBrowse.Text = 'Browse...'
    $btnDepBrowse.Location = [System.Drawing.Point]::new(890, 6)
    $btnDepBrowse.Size = [System.Drawing.Size]::new(80, 28)
    $btnDepBrowse.BackColor = $bgLight
    $btnDepBrowse.ForeColor = $textWhite
    $btnDepBrowse.FlatStyle = 'Flat'
    $tabDependency.Controls.Add($btnDepBrowse)
    
    $btnDepGenerate = [System.Windows.Forms.Button]::new()
    $btnDepGenerate.Text = 'Generate Graph'
    $btnDepGenerate.Location = [System.Drawing.Point]::new(980, 6)
    $btnDepGenerate.Size = [System.Drawing.Size]::new(120, 28)
    $btnDepGenerate.BackColor = $accentGreen
    $btnDepGenerate.ForeColor = $textWhite
    $btnDepGenerate.FlatStyle = 'Flat'
    $tabDependency.Controls.Add($btnDepGenerate)
    
    $btnDepExport = [System.Windows.Forms.Button]::new()
    $btnDepExport.Text = 'Export'
    $btnDepExport.Location = [System.Drawing.Point]::new(1110, 6)
    $btnDepExport.Size = [System.Drawing.Size]::new(80, 28)
    $btnDepExport.BackColor = $accent
    $btnDepExport.ForeColor = $textWhite
    $btnDepExport.FlatStyle = 'Flat'
    $tabDependency.Controls.Add($btnDepExport)
    
    $txtDepGraph = [System.Windows.Forms.RichTextBox]::new()
    $txtDepGraph.Location = [System.Drawing.Point]::new(10, 45)
    $txtDepGraph.Size = [System.Drawing.Size]::new(1160, 640)
    $txtDepGraph.BackColor = $bgDark
    $txtDepGraph.ForeColor = $textWhite
    $txtDepGraph.Font = [System.Drawing.Font]::new('Consolas', 9)
    $txtDepGraph.ReadOnly = $true
    $txtDepGraph.BorderStyle = 'None'
    $tabDependency.Controls.Add($txtDepGraph)
    
    # ============================================================
    # TAB 7: DIFF MODE
    # ============================================================
    $tabDiff = [System.Windows.Forms.TabPage]::new()
    $tabDiff.Text = '  Diff Mode  '
    $tabDiff.BackColor = $bgDark
    $tabDiff.Padding = [System.Windows.Forms.Padding]::new(10)
    $tabs.TabPages.Add($tabDiff)
    
    $lblDiffOld = [System.Windows.Forms.Label]::new()
    $lblDiffOld.Text = 'Old Version:'
    $lblDiffOld.Location = [System.Drawing.Point]::new(10, 10)
    $lblDiffOld.AutoSize = $true
    $lblDiffOld.ForeColor = $textWhite
    $tabDiff.Controls.Add($lblDiffOld)
    
    $txtDiffOld = [System.Windows.Forms.TextBox]::new()
    $txtDiffOld.Location = [System.Drawing.Point]::new(100, 8)
    $txtDiffOld.Size = [System.Drawing.Size]::new(800, 25)
    $txtDiffOld.BackColor = $bgLight
    $txtDiffOld.ForeColor = $textWhite
    $txtDiffOld.BorderStyle = 'FixedSingle'
    $tabDiff.Controls.Add($txtDiffOld)
    
    $btnDiffOldBrowse = [System.Windows.Forms.Button]::new()
    $btnDiffOldBrowse.Text = 'Browse...'
    $btnDiffOldBrowse.Location = [System.Drawing.Point]::new(910, 6)
    $btnDiffOldBrowse.Size = [System.Drawing.Size]::new(80, 28)
    $btnDiffOldBrowse.BackColor = $bgLight
    $btnDiffOldBrowse.ForeColor = $textWhite
    $btnDiffOldBrowse.FlatStyle = 'Flat'
    $tabDiff.Controls.Add($btnDiffOldBrowse)
    
    $lblDiffNew = [System.Windows.Forms.Label]::new()
    $lblDiffNew.Text = 'New Version:'
    $lblDiffNew.Location = [System.Drawing.Point]::new(10, 45)
    $lblDiffNew.AutoSize = $true
    $lblDiffNew.ForeColor = $textWhite
    $tabDiff.Controls.Add($lblDiffNew)
    
    $txtDiffNew = [System.Windows.Forms.TextBox]::new()
    $txtDiffNew.Location = [System.Drawing.Point]::new(100, 43)
    $txtDiffNew.Size = [System.Drawing.Size]::new(800, 25)
    $txtDiffNew.BackColor = $bgLight
    $txtDiffNew.ForeColor = $textWhite
    $txtDiffNew.BorderStyle = 'FixedSingle'
    $tabDiff.Controls.Add($txtDiffNew)
    
    $btnDiffNewBrowse = [System.Windows.Forms.Button]::new()
    $btnDiffNewBrowse.Text = 'Browse...'
    $btnDiffNewBrowse.Location = [System.Drawing.Point]::new(910, 41)
    $btnDiffNewBrowse.Size = [System.Drawing.Size]::new(80, 28)
    $btnDiffNewBrowse.BackColor = $bgLight
    $btnDiffNewBrowse.ForeColor = $textWhite
    $btnDiffNewBrowse.FlatStyle = 'Flat'
    $tabDiff.Controls.Add($btnDiffNewBrowse)
    
    $btnDiffCompare = [System.Windows.Forms.Button]::new()
    $btnDiffCompare.Text = 'Compare Versions'
    $btnDiffCompare.Location = [System.Drawing.Point]::new(1000, 6)
    $btnDiffCompare.Size = [System.Drawing.Size]::new(120, 63)
    $btnDiffCompare.BackColor = $accentGreen
    $btnDiffCompare.ForeColor = $textWhite
    $btnDiffCompare.FlatStyle = 'Flat'
    $tabDiff.Controls.Add($btnDiffCompare)
    
    $txtDiffReport = [System.Windows.Forms.RichTextBox]::new()
    $txtDiffReport.Location = [System.Drawing.Point]::new(10, 80)
    $txtDiffReport.Size = [System.Drawing.Size]::new(1160, 605)
    $txtDiffReport.BackColor = $bgDark
    $txtDiffReport.ForeColor = $textWhite
    $txtDiffReport.Font = [System.Drawing.Font]::new('Consolas', 9)
    $txtDiffReport.ReadOnly = $true
    $txtDiffReport.BorderStyle = 'None'
    $tabDiff.Controls.Add($txtDiffReport)
    
    # ============================================================
    # TAB 8: SEMANTIC VALIDATION
    # ============================================================
    $tabSemantic = [System.Windows.Forms.TabPage]::new()
    $tabSemantic.Text = '  Semantic Validation  '
    $tabSemantic.BackColor = $bgDark
    $tabSemantic.Padding = [System.Windows.Forms.Padding]::new(10)
    $tabs.TabPages.Add($tabSemantic)
    
    $lblSemPath = [System.Windows.Forms.Label]::new()
    $lblSemPath.Text = 'Mod Path:'
    $lblSemPath.Location = [System.Drawing.Point]::new(10, 10)
    $lblSemPath.AutoSize = $true
    $lblSemPath.ForeColor = $textWhite
    $tabSemantic.Controls.Add($lblSemPath)
    
    $txtSemPath = [System.Windows.Forms.TextBox]::new()
    $txtSemPath.Location = [System.Drawing.Point]::new(80, 8)
    $txtSemPath.Size = [System.Drawing.Size]::new(600, 25)
    $txtSemPath.BackColor = $bgLight
    $txtSemPath.ForeColor = $textWhite
    $txtSemPath.BorderStyle = 'FixedSingle'
    $tabSemantic.Controls.Add($txtSemPath)
    
    $btnSemBrowse = [System.Windows.Forms.Button]::new()
    $btnSemBrowse.Text = 'Browse...'
    $btnSemBrowse.Location = [System.Drawing.Point]::new(690, 6)
    $btnSemBrowse.Size = [System.Drawing.Size]::new(80, 28)
    $btnSemBrowse.BackColor = $bgLight
    $btnSemBrowse.ForeColor = $textWhite
    $btnSemBrowse.FlatStyle = 'Flat'
    $tabSemantic.Controls.Add($btnSemBrowse)
    
    $btnSemValidate = [System.Windows.Forms.Button]::new()
    $btnSemValidate.Text = 'Validate'
    $btnSemValidate.Location = [System.Drawing.Point]::new(780, 6)
    $btnSemValidate.Size = [System.Drawing.Size]::new(100, 28)
    $btnSemValidate.BackColor = $accentGreen
    $btnSemValidate.ForeColor = $textWhite
    $btnSemValidate.FlatStyle = 'Flat'
    $tabSemantic.Controls.Add($btnSemValidate)
    
    $btnSemInheritance = [System.Windows.Forms.Button]::new()
    $btnSemInheritance.Text = 'Inheritance Tree'
    $btnSemInheritance.Location = [System.Drawing.Point]::new(890, 6)
    $btnSemInheritance.Size = [System.Drawing.Size]::new(120, 28)
    $btnSemInheritance.BackColor = $accent
    $btnSemInheritance.ForeColor = $textWhite
    $btnSemInheritance.FlatStyle = 'Flat'
    $tabSemantic.Controls.Add($btnSemInheritance)
    
    $btnSemEvents = [System.Windows.Forms.Button]::new()
    $btnSemEvents.Text = 'Event Flow'
    $btnSemEvents.Location = [System.Drawing.Point]::new(1020, 6)
    $btnSemEvents.Size = [System.Drawing.Size]::new(100, 28)
    $btnSemEvents.BackColor = $accent
    $btnSemEvents.ForeColor = $textWhite
    $btnSemEvents.FlatStyle = 'Flat'
    $tabSemantic.Controls.Add($btnSemEvents)
    
    $btnSemTML = [System.Windows.Forms.Button]::new()
    $btnSemTML.Text = 'TML Analysis'
    $btnSemTML.Location = [System.Drawing.Point]::new(1330, 6)
    $btnSemTML.Size = [System.Drawing.Size]::new(100, 28)
    $btnSemTML.BackColor = $accent
    $btnSemTML.ForeColor = $textWhite
    $btnSemTML.FlatStyle = 'Flat'
    $tabSemantic.Controls.Add($btnSemTML)
    
    $gridSemantic = [System.Windows.Forms.DataGridView]::new()
    $gridSemantic.Location = [System.Drawing.Point]::new(10, 45)
    $gridSemantic.Size = [System.Drawing.Size]::new(1360, 640)
    $gridSemantic.BackgroundColor = $bgDark
    $gridSemantic.ForeColor = $textWhite
    $gridSemantic.DefaultCellStyle.BackColor = $bgDark
    $gridSemantic.DefaultCellStyle.ForeColor = $textWhite
    $gridSemantic.DefaultCellStyle.SelectionBackColor = $accent
    $gridSemantic.DefaultCellStyle.SelectionForeColor = $textWhite
    $gridSemantic.ColumnHeadersDefaultCellStyle.BackColor = $bgLight
    $gridSemantic.ColumnHeadersDefaultCellStyle.ForeColor = $textWhite
    $gridSemantic.BorderStyle = 'None'
    $gridSemantic.ReadOnly = $true
    $gridSemantic.SelectionMode = 'FullRowSelect'
    $gridSemantic.MultiSelect = $false
    $gridSemantic.AutoSizeColumnsMode = 'Fill'
    $gridSemantic.Columns.Add('File', 'File') | Out-Null
    $gridSemantic.Columns.Add('Line', 'Line') | Out-Null
    $gridSemantic.Columns.Add('Severity', 'Severity') | Out-Null
    $gridSemantic.Columns.Add('Code', 'Code') | Out-Null
    $gridSemantic.Columns.Add('Message', 'Message') | Out-Null
    $gridSemantic.Columns['File'].Width = 300
    $gridSemantic.Columns['Line'].Width = 60
    $gridSemantic.Columns['Severity'].Width = 80
    $gridSemantic.Columns['Code'].Width = 200
    $gridSemantic.Columns['Message'].Width = 520
    $tabSemantic.Controls.Add($gridSemantic)
    
    # ============================================================
    # TAB 9: LIVE PREVIEW
    # ============================================================
    $tabLivePreview = [System.Windows.Forms.TabPage]::new()
    $tabLivePreview.Text = '  Live Preview  '
    $tabLivePreview.BackColor = $bgDark
    $tabLivePreview.Padding = [System.Windows.Forms.Padding]::new(10)
    $tabs.TabPages.Add($tabLivePreview)
    
    $lblLivePath = [System.Windows.Forms.Label]::new()
    $lblLivePath.Text = 'Mod Path:'
    $lblLivePath.Location = [System.Drawing.Point]::new(10, 10)
    $lblLivePath.AutoSize = $true
    $lblLivePath.ForeColor = $textWhite
    $tabLivePreview.Controls.Add($lblLivePath)
    
    $txtLivePath = [System.Windows.Forms.TextBox]::new()
    $txtLivePath.Location = [System.Drawing.Point]::new(80, 8)
    $txtLivePath.Size = [System.Drawing.Size]::new(600, 25)
    $txtLivePath.BackColor = $bgLight
    $txtLivePath.ForeColor = $textWhite
    $txtLivePath.BorderStyle = 'FixedSingle'
    $tabLivePreview.Controls.Add($txtLivePath)
    
    $btnLiveBrowse = [System.Windows.Forms.Button]::new()
    $btnLiveBrowse.Text = 'Browse...'
    $btnLiveBrowse.Location = [System.Drawing.Point]::new(690, 6)
    $btnLiveBrowse.Size = [System.Drawing.Size]::new(80, 28)
    $btnLiveBrowse.BackColor = $bgLight
    $btnLiveBrowse.ForeColor = $textWhite
    $btnLiveBrowse.FlatStyle = 'Flat'
    $tabLivePreview.Controls.Add($btnLiveBrowse)
    
    $btnLiveLoad = [System.Windows.Forms.Button]::new()
    $btnLiveLoad.Text = 'Load Types'
    $btnLiveLoad.Location = [System.Drawing.Point]::new(780, 6)
    $btnLiveLoad.Size = [System.Drawing.Size]::new(100, 28)
    $btnLiveLoad.BackColor = $accentGreen
    $btnLiveLoad.ForeColor = $textWhite
    $btnLiveLoad.FlatStyle = 'Flat'
    $tabLivePreview.Controls.Add($btnLiveLoad)
    
    $lblLiveType = [System.Windows.Forms.Label]::new()
    $lblLiveType.Text = 'Select Type:'
    $lblLiveType.Location = [System.Drawing.Point]::new(10, 45)
    $lblLiveType.AutoSize = $true
    $lblLiveType.ForeColor = $textWhite
    $tabLivePreview.Controls.Add($lblLiveType)
    
    $cmbLiveType = [System.Windows.Forms.ComboBox]::new()
    $cmbLiveType.Location = [System.Drawing.Point]::new(90, 43)
    $cmbLiveType.Size = [System.Drawing.Size]::new(500, 25)
    $cmbLiveType.BackColor = $bgLight
    $cmbLiveType.ForeColor = $textWhite
    $cmbLiveType.DropDownStyle = 'DropDownList'
    $cmbLiveType.DisplayMember = 'Name'
    $cmbLiveType.ValueMember = 'UNID'
    $tabLivePreview.Controls.Add($cmbLiveType)
    
    $btnLivePreview = [System.Windows.Forms.Button]::new()
    $btnLivePreview.Text = 'Preview'
    $btnLivePreview.Location = [System.Drawing.Point]::new(600, 41)
    $btnLivePreview.Size = [System.Drawing.Size]::new(100, 28)
    $btnLivePreview.BackColor = $accentGreen
    $btnLivePreview.ForeColor = $textWhite
    $btnLivePreview.FlatStyle = 'Flat'
    $tabLivePreview.Controls.Add($btnLivePreview)
    
    $txtLivePreview = [System.Windows.Forms.RichTextBox]::new()
    $txtLivePreview.Location = [System.Drawing.Point]::new(10, 80)
    $txtLivePreview.Size = [System.Drawing.Size]::new(1160, 605)
    $txtLivePreview.BackColor = $bgDark
    $txtLivePreview.ForeColor = $textWhite
    $txtLivePreview.Font = [System.Drawing.Font]::new('Consolas', 9)
    $txtLivePreview.ReadOnly = $true
    $txtLivePreview.BorderStyle = 'None'
    $tabLivePreview.Controls.Add($txtLivePreview)
    
    # ============================================================
    # TAB: MIGRATION SAFETY
    # ============================================================
    $tabMigration = [System.Windows.Forms.TabPage]::new()
    $tabMigration.Text = '  Migration Safety  '
    $tabMigration.BackColor = $bgDark
    $tabMigration.Padding = [System.Windows.Forms.Padding]::new(10)
    $tabs.TabPages.Add($tabMigration)
    
    # Load migration safety modules
    $migrationModule = Join-Path $PSScriptRoot 'TranscendenceModTools_MigrationSafety.ps1'
    $testRunnerModule = Join-Path $PSScriptRoot 'TranscendenceModTools_TestRunner.ps1'
    if (Test-Path $migrationModule) {
        try {
            . $migrationModule
        }
        catch {
            Write-Warning "Failed to load migration safety module: $_"
        }
    }
    if (Test-Path $testRunnerModule) {
        try {
            . $testRunnerModule
        }
        catch {
            Write-Warning "Failed to load test runner module: $_"
        }
    }
    
    # Split container for different panels
    $splitMigration = [System.Windows.Forms.SplitContainer]::new()
    $splitMigration.Dock = 'Fill'
    $splitMigration.Orientation = 'Vertical'
    $splitMigration.SplitterDistance = 600
    $splitMigration.BackColor = $bgDark
    $tabMigration.Controls.Add($splitMigration)
    
    # Left panel: Diff & Verification
    $pnlLeft = [System.Windows.Forms.Panel]::new()
    $pnlLeft.Dock = 'Fill'
    $pnlLeft.BackColor = $bgDark
    $splitMigration.Panel1.Controls.Add($pnlLeft)
    
    # Tab control for left panel sections
    $tabLeft = [System.Windows.Forms.TabControl]::new()
    $tabLeft.Dock = 'Fill'
    $tabLeft.BackColor = $bgDark
    $pnlLeft.Controls.Add($tabLeft)
    
    # Sub-tab 1: Diff Viewer
    $subTabDiff = [System.Windows.Forms.TabPage]::new()
    $subTabDiff.Text = 'Diff Viewer'
    $subTabDiff.BackColor = $bgDark
    $tabLeft.TabPages.Add($subTabDiff)
    
    $lblOriginal = [System.Windows.Forms.Label]::new()
    $lblOriginal.Text = 'Original Path:'
    $lblOriginal.Location = [System.Drawing.Point]::new(10, 10)
    $lblOriginal.AutoSize = $true
    $lblOriginal.ForeColor = $textWhite
    $subTabDiff.Controls.Add($lblOriginal)
    
    $txtOriginal = [System.Windows.Forms.TextBox]::new()
    $txtOriginal.Location = [System.Drawing.Point]::new(100, 8)
    $txtOriginal.Size = [System.Drawing.Size]::new(400, 25)
    $txtOriginal.BackColor = $bgLight
    $txtOriginal.ForeColor = $textWhite
    $subTabDiff.Controls.Add($txtOriginal)
    
    $lblManual = [System.Windows.Forms.Label]::new()
    $lblManual.Text = 'Manual Path:'
    $lblManual.Location = [System.Drawing.Point]::new(10, 40)
    $lblManual.AutoSize = $true
    $lblManual.ForeColor = $textWhite
    $subTabDiff.Controls.Add($lblManual)
    
    $txtManual = [System.Windows.Forms.TextBox]::new()
    $txtManual.Location = [System.Drawing.Point]::new(100, 38)
    $txtManual.Size = [System.Drawing.Size]::new(400, 25)
    $txtManual.BackColor = $bgLight
    $txtManual.ForeColor = $textWhite
    $subTabDiff.Controls.Add($txtManual)
    
    $lblAi = [System.Windows.Forms.Label]::new()
    $lblAi.Text = 'AI Path:'
    $lblAi.Location = [System.Drawing.Point]::new(10, 70)
    $lblAi.AutoSize = $true
    $lblAi.ForeColor = $textWhite
    $subTabDiff.Controls.Add($lblAi)
    
    $txtAi = [System.Windows.Forms.TextBox]::new()
    $txtAi.Location = [System.Drawing.Point]::new(100, 68)
    $txtAi.Size = [System.Drawing.Size]::new(400, 25)
    $txtAi.BackColor = $bgLight
    $txtAi.ForeColor = $textWhite
    $subTabDiff.Controls.Add($txtAi)
    
    $btnDiff = [System.Windows.Forms.Button]::new()
    $btnDiff.Text = 'Run Diff'
    $btnDiff.Location = [System.Drawing.Point]::new(510, 35)
    $btnDiff.Size = [System.Drawing.Size]::new(100, 30)
    $btnDiff.BackColor = $accentGreen
    $btnDiff.ForeColor = $textWhite
    $btnDiff.FlatStyle = 'Flat'
    $subTabDiff.Controls.Add($btnDiff)
    
    $gridDiff = [System.Windows.Forms.DataGridView]::new()
    $gridDiff.Location = [System.Drawing.Point]::new(10, 100)
    $gridDiff.Size = [System.Drawing.Size]::new(600, 400)
    $gridDiff.BackgroundColor = $bgDark
    $gridDiff.ForeColor = $textWhite
    $gridDiff.GridColor = $bgLight
    $gridDiff.RowHeadersVisible = $false
    $gridDiff.AllowUserToAddRows = $false
    $gridDiff.ReadOnly = $true
    $gridDiff.SelectionMode = 'FullRowSelect'
    $gridDiff.AutoSizeColumnsMode = 'Fill'
    $gridDiff.DefaultCellStyle.BackColor = $bgDark
    $gridDiff.DefaultCellStyle.ForeColor = $textWhite
    $gridDiff.DefaultCellStyle.SelectionBackColor = $accent
    $gridDiff.ColumnHeadersDefaultCellStyle.BackColor = $bgMedium
    $gridDiff.ColumnHeadersDefaultCellStyle.ForeColor = $textWhite
    $gridDiff.EnableHeadersVisualStyles = $false
    $gridDiff.Anchor = 'Top,Left,Right,Bottom'
    $subTabDiff.Controls.Add($gridDiff)
    
    $gridDiff.Columns.Add('FileName', 'File') | Out-Null
    $gridDiff.Columns.Add('Status', 'Status') | Out-Null
    $gridDiff.Columns.Add('RiskScore', 'Risk') | Out-Null
    $gridDiff.Columns.Add('Conflicts', 'Conflicts') | Out-Null
    $gridDiff.Columns['RiskScore'].Width = 60
    
    # Store diff result for risk report
    $script:migrationDiff = $null
    
    $btnDiff.Add_Click({
        $original = $txtOriginal.Text
        $manual = $txtManual.Text
        $ai = $txtAi.Text
        
        if ([string]::IsNullOrWhiteSpace($original) -or [string]::IsNullOrWhiteSpace($manual) -or [string]::IsNullOrWhiteSpace($ai)) {
            [System.Windows.Forms.MessageBox]::Show('Please provide all three paths (Original, Manual, AI)', 'Missing Paths', 'OK', 'Warning')
            return
        }
        
        try {
            $outputPath = Join-Path $PSScriptRoot "migration_diff_$(Get-Date -Format 'yyyyMMdd_HHmmss').txt"
            $script:migrationDiff = Get-MigrationDiff -OriginalPath $original -ManualPath $manual -AiPath $ai -OutputPath $outputPath
            
            $gridDiff.Rows.Clear()
            foreach ($file in $script:migrationDiff.Files | Sort-Object RiskScore -Descending) {
                $row = $gridDiff.Rows.Add($file.FileName, $file.Status, $file.RiskScore, $file.Conflicts.Count)
                $gridDiff.Rows[$row].Tag = $file
                
                # Color by risk
                if ($file.RiskScore -ge 50) {
                    $gridDiff.Rows[$row].DefaultCellStyle.BackColor = [System.Drawing.Color]::FromArgb(80, 40, 40)
                }
                elseif ($file.RiskScore -ge 20) {
                    $gridDiff.Rows[$row].DefaultCellStyle.BackColor = [System.Drawing.Color]::FromArgb(80, 70, 40)
                }
            }
            
            # Update risk report
            if ($script:migrationDiff) {
                $riskReport = Get-MigrationRiskReport -Diff $script:migrationDiff
                $txtRiskReport.Clear()
                $txtRiskReport.AppendText("Migration Risk Report`n")
                $txtRiskReport.AppendText("===================`n`n")
                $txtRiskReport.AppendText("High Risk Files ($($riskReport.HighRiskCount)):`n")
                foreach ($file in $riskReport.HighRisk) {
                    $txtRiskReport.AppendText("  - $($file.FileName) (Score: $($file.RiskScore))`n")
                }
                $txtRiskReport.AppendText("`nMedium Risk Files ($($riskReport.MediumRiskCount)):`n")
                foreach ($file in $riskReport.MediumRisk) {
                    $txtRiskReport.AppendText("  - $($file.FileName) (Score: $($file.RiskScore))`n")
                }
                $txtRiskReport.AppendText("`nLow Risk Files ($($riskReport.LowRiskCount)):`n")
                foreach ($file in $riskReport.LowRisk) {
                    $txtRiskReport.AppendText("  - $($file.FileName) (Score: $($file.RiskScore))`n")
                }
            }
            
            [System.Windows.Forms.MessageBox]::Show("Diff complete. Found $($script:migrationDiff.Summary.Conflicts) conflicts.`nReport saved to:`n$outputPath", 'Diff Complete', 'OK', 'Information')
        }
        catch {
            [System.Windows.Forms.MessageBox]::Show("Error running diff: $_", 'Error', 'OK', 'Error')
        }
    })
    
    # Sub-tab 2: Verification
    $subTabVerify = [System.Windows.Forms.TabPage]::new()
    $subTabVerify.Text = 'Verification'
    $subTabVerify.BackColor = $bgDark
    $tabLeft.TabPages.Add($subTabVerify)
    
    $lblVerifyPath = [System.Windows.Forms.Label]::new()
    $lblVerifyPath.Text = 'Mod Path:'
    $lblVerifyPath.Location = [System.Drawing.Point]::new(10, 10)
    $lblVerifyPath.AutoSize = $true
    $lblVerifyPath.ForeColor = $textWhite
    $subTabVerify.Controls.Add($lblVerifyPath)
    
    $txtVerifyPath = [System.Windows.Forms.TextBox]::new()
    $txtVerifyPath.Location = [System.Drawing.Point]::new(80, 8)
    $txtVerifyPath.Size = [System.Drawing.Size]::new(500, 25)
    $txtVerifyPath.BackColor = $bgLight
    $txtVerifyPath.ForeColor = $textWhite
    $subTabVerify.Controls.Add($txtVerifyPath)
    
    $chkSchema = [System.Windows.Forms.CheckBox]::new()
    $chkSchema.Text = 'Schema'
    $chkSchema.Location = [System.Drawing.Point]::new(10, 40)
    $chkSchema.AutoSize = $true
    $chkSchema.ForeColor = $textWhite
    $chkSchema.Checked = $true
    $subTabVerify.Controls.Add($chkSchema)
    
    $chkSemantic = [System.Windows.Forms.CheckBox]::new()
    $chkSemantic.Text = 'Semantic'
    $chkSemantic.Location = [System.Drawing.Point]::new(80, 40)
    $chkSemantic.AutoSize = $true
    $chkSemantic.ForeColor = $textWhite
    $chkSemantic.Checked = $true
    $subTabVerify.Controls.Add($chkSemantic)
    
    $chkApi = [System.Windows.Forms.CheckBox]::new()
    $chkApi.Text = 'API Deprecation'
    $chkApi.Location = [System.Drawing.Point]::new(160, 40)
    $chkApi.AutoSize = $true
    $chkApi.ForeColor = $textWhite
    $chkApi.Checked = $true
    $subTabVerify.Controls.Add($chkApi)
    
    $btnVerify = [System.Windows.Forms.Button]::new()
    $btnVerify.Text = 'Run Verification'
    $btnVerify.Location = [System.Drawing.Point]::new(590, 35)
    $btnVerify.Size = [System.Drawing.Size]::new(120, 30)
    $btnVerify.BackColor = $accentGreen
    $btnVerify.ForeColor = $textWhite
    $btnVerify.FlatStyle = 'Flat'
    $subTabVerify.Controls.Add($btnVerify)
    
    $txtVerifyResults = [System.Windows.Forms.RichTextBox]::new()
    $txtVerifyResults.Location = [System.Drawing.Point]::new(10, 75)
    $txtVerifyResults.Size = [System.Drawing.Size]::new(700, 425)
    $txtVerifyResults.BackColor = $bgLight
    $txtVerifyResults.ForeColor = $textWhite
    $txtVerifyResults.Font = [System.Drawing.Font]::new('Consolas', 9)
    $txtVerifyResults.ReadOnly = $true
    $txtVerifyResults.Anchor = 'Top,Left,Right,Bottom'
    $subTabVerify.Controls.Add($txtVerifyResults)
    
    $btnVerify.Add_Click({
        $modPath = $txtVerifyPath.Text
        if ([string]::IsNullOrWhiteSpace($modPath)) {
            return
        }
        
        try {
            $txtVerifyResults.Clear()
            $txtVerifyResults.AppendText("Running verification...`n`n")
            
            $results = Invoke-MigrationVerification -ModPath $modPath -SchemaCheck:$chkSchema.Checked -SemanticCheck:$chkSemantic.Checked -ApiDeprecationCheck:$chkApi.Checked
            
            $txtVerifyResults.AppendText("Verification Results`n")
            $txtVerifyResults.AppendText("==================`n`n")
            $txtVerifyResults.AppendText("Overall: $($results.Overall)`n`n")
            
            if ($results.Schema) {
                $txtVerifyResults.AppendText("Schema Check:`n")
                $txtVerifyResults.AppendText("  Passed: $($results.Schema.Passed)`n")
                $txtVerifyResults.AppendText("  Well-formed Errors: $($results.Schema.WellformedErrors)`n")
                $txtVerifyResults.AppendText("  BOM Errors: $($results.Schema.BomErrors)`n")
                $txtVerifyResults.AppendText("  Total Issues: $($results.Schema.TotalIssues)`n`n")
            }
            
            if ($results.Semantic) {
                $txtVerifyResults.AppendText("Semantic Check:`n")
                $txtVerifyResults.AppendText("  Passed: $($results.Semantic.Passed)`n")
                $txtVerifyResults.AppendText("  UNID Issues: $($results.Semantic.UnidIssues)`n")
                $txtVerifyResults.AppendText("  Resource Issues: $($results.Semantic.ResourceIssues)`n`n")
            }
            
            if ($results.ApiDeprecation) {
                $txtVerifyResults.AppendText("API Deprecation:`n")
                $txtVerifyResults.AppendText("  Passed: $($results.ApiDeprecation.Passed)`n")
                $txtVerifyResults.AppendText("  Deprecations Found: $($results.ApiDeprecation.Count)`n`n")
            }
        }
        catch {
            $txtVerifyResults.AppendText("Error: $_`n")
        }
    })
    
    # Right panel: Test Runner & Risk Report
    $pnlRight = [System.Windows.Forms.Panel]::new()
    $pnlRight.Dock = 'Fill'
    $pnlRight.BackColor = $bgDark
    $splitMigration.Panel2.Controls.Add($pnlRight)
    
    $tabRight = [System.Windows.Forms.TabControl]::new()
    $tabRight.Dock = 'Fill'
    $tabRight.BackColor = $bgDark
    $pnlRight.Controls.Add($tabRight)
    
    # Sub-tab 3: Test Runner
    $subTabTest = [System.Windows.Forms.TabPage]::new()
    $subTabTest.Text = 'Test Runner'
    $subTabTest.BackColor = $bgDark
    $tabRight.TabPages.Add($subTabTest)
    
    $lblTestPath = [System.Windows.Forms.Label]::new()
    $lblTestPath.Text = 'Mod Path:'
    $lblTestPath.Location = [System.Drawing.Point]::new(10, 10)
    $lblTestPath.AutoSize = $true
    $lblTestPath.ForeColor = $textWhite
    $subTabTest.Controls.Add($lblTestPath)
    
    $txtTestPath = [System.Windows.Forms.TextBox]::new()
    $txtTestPath.Location = [System.Drawing.Point]::new(80, 8)
    $txtTestPath.Size = [System.Drawing.Size]::new(400, 25)
    $txtTestPath.BackColor = $bgLight
    $txtTestPath.ForeColor = $textWhite
    $subTabTest.Controls.Add($txtTestPath)
    
    $btnRunTests = [System.Windows.Forms.Button]::new()
    $btnRunTests.Text = 'Run Tests'
    $btnRunTests.Location = [System.Drawing.Point]::new(490, 6)
    $btnRunTests.Size = [System.Drawing.Size]::new(100, 30)
    $btnRunTests.BackColor = $accentGreen
    $btnRunTests.ForeColor = $textWhite
    $btnRunTests.FlatStyle = 'Flat'
    $subTabTest.Controls.Add($btnRunTests)
    
    $listTests = [System.Windows.Forms.ListView]::new()
    $listTests.Location = [System.Drawing.Point]::new(10, 45)
    $listTests.Size = [System.Drawing.Size]::new(580, 455)
    $listTests.BackColor = $bgLight
    $listTests.ForeColor = $textWhite
    $listTests.View = 'Details'
    $listTests.FullRowSelect = $true
    $listTests.Anchor = 'Top,Left,Right,Bottom'
    $subTabTest.Controls.Add($listTests)
    
    $listTests.Columns.Add('Test', 200) | Out-Null
    $listTests.Columns.Add('Status', 100) | Out-Null
    $listTests.Columns.Add('Risk', 80) | Out-Null
    
    $btnRunTests.Add_Click({
        $modPath = $txtTestPath.Text
        if ([string]::IsNullOrWhiteSpace($modPath)) {
            return
        }
        
        $listTests.Items.Clear()
        
        $checklist = Get-PlaytestChecklist
        foreach ($item in $checklist) {
            $listItem = [System.Windows.Forms.ListViewItem]::new($item.Item)
            $listItem.SubItems.Add('Pending')
            $listItem.SubItems.Add($item.Priority)
            $listItem.Tag = $item
            $listTests.Items.Add($listItem)
        }
        
        [System.Windows.Forms.MessageBox]::Show('Test runner requires game integration. Tests are defined but need game API to execute.', 'Test Runner', 'OK', 'Information')
    })
    
    # Sub-tab 4: Risk Report
    $subTabRisk = [System.Windows.Forms.TabPage]::new()
    $subTabRisk.Text = 'Risk Report'
    $subTabRisk.BackColor = $bgDark
    $tabRight.TabPages.Add($subTabRisk)
    
    $txtRiskReport = [System.Windows.Forms.RichTextBox]::new()
    $txtRiskReport.Dock = 'Fill'
    $txtRiskReport.BackColor = $bgLight
    $txtRiskReport.ForeColor = $textWhite
    $txtRiskReport.Font = [System.Drawing.Font]::new('Consolas', 9)
    $txtRiskReport.ReadOnly = $true
    $subTabRisk.Controls.Add($txtRiskReport)
    
    # Sub-tab 5: Migration Preview
    $subTabPreview = [System.Windows.Forms.TabPage]::new()
    $subTabPreview.Text = 'Type Preview'
    $subTabPreview.BackColor = $bgDark
    $tabRight.TabPages.Add($subTabPreview)
    
    # Load migration preview module
    $previewModule = Join-Path $PSScriptRoot 'TranscendenceModTools_MigrationPreview.ps1'
    if (Test-Path $previewModule) {
        try {
            . $previewModule
        }
        catch {
            Write-Warning "Failed to load migration preview module: $_"
        }
    }
    
    $lblPreviewPath = [System.Windows.Forms.Label]::new()
    $lblPreviewPath.Text = 'Mod Path:'
    $lblPreviewPath.Location = [System.Drawing.Point]::new(10, 10)
    $lblPreviewPath.AutoSize = $true
    $lblPreviewPath.ForeColor = $textWhite
    $subTabPreview.Controls.Add($lblPreviewPath)
    
    $txtPreviewPath = [System.Windows.Forms.TextBox]::new()
    $txtPreviewPath.Location = [System.Drawing.Point]::new(80, 8)
    $txtPreviewPath.Size = [System.Drawing.Size]::new(300, 25)
    $txtPreviewPath.BackColor = $bgLight
    $txtPreviewPath.ForeColor = $textWhite
    $subTabPreview.Controls.Add($txtPreviewPath)
    
    $lblPreviewUNID = [System.Windows.Forms.Label]::new()
    $lblPreviewUNID.Text = 'Type UNID:'
    $lblPreviewUNID.Location = [System.Drawing.Point]::new(10, 40)
    $lblPreviewUNID.AutoSize = $true
    $lblPreviewUNID.ForeColor = $textWhite
    $subTabPreview.Controls.Add($lblPreviewUNID)
    
    $txtPreviewUNID = [System.Windows.Forms.TextBox]::new()
    $txtPreviewUNID.Location = [System.Drawing.Point]::new(80, 38)
    $txtPreviewUNID.Size = [System.Drawing.Size]::new(200, 25)
    $txtPreviewUNID.BackColor = $bgLight
    $txtPreviewUNID.ForeColor = $textWhite
    $subTabPreview.Controls.Add($txtPreviewUNID)
    
    $cmbPreviewVersion = [System.Windows.Forms.ComboBox]::new()
    $cmbPreviewVersion.Location = [System.Drawing.Point]::new(290, 38)
    $cmbPreviewVersion.Size = [System.Drawing.Size]::new(90, 25)
    $cmbPreviewVersion.BackColor = $bgLight
    $cmbPreviewVersion.ForeColor = $textWhite
    $cmbPreviewVersion.DropDownStyle = 'DropDownList'
    $cmbPreviewVersion.Items.AddRange(@('Original', 'Manual', 'AI'))
    $cmbPreviewVersion.SelectedIndex = 2  # Default to AI
    $subTabPreview.Controls.Add($cmbPreviewVersion)
    
    $btnPreview = [System.Windows.Forms.Button]::new()
    $btnPreview.Text = 'Preview Type'
    $btnPreview.Location = [System.Drawing.Point]::new(390, 36)
    $btnPreview.Size = [System.Drawing.Size]::new(100, 30)
    $btnPreview.BackColor = $accentGreen
    $btnPreview.ForeColor = $textWhite
    $btnPreview.FlatStyle = 'Flat'
    $subTabPreview.Controls.Add($btnPreview)
    
    $txtPreview = [System.Windows.Forms.RichTextBox]::new()
    $txtPreview.Location = [System.Drawing.Point]::new(10, 75)
    $txtPreview.Size = [System.Drawing.Size]::new(580, 425)
    $txtPreview.BackColor = $bgLight
    $txtPreview.ForeColor = $textWhite
    $txtPreview.Font = [System.Drawing.Font]::new('Consolas', 9)
    $txtPreview.ReadOnly = $true
    $txtPreview.Anchor = 'Top,Left,Right,Bottom'
    $subTabPreview.Controls.Add($txtPreview)
    
    $btnPreview.Add_Click({
        $modPath = $txtPreviewPath.Text
        $unid = $txtPreviewUNID.Text
        $version = $cmbPreviewVersion.SelectedItem
        
        if ([string]::IsNullOrWhiteSpace($modPath) -or [string]::IsNullOrWhiteSpace($unid)) {
            [System.Windows.Forms.MessageBox]::Show('Please provide mod path and type UNID', 'Missing Information', 'OK', 'Warning')
            return
        }
        
        try {
            $txtPreview.Clear()
            $txtPreview.AppendText("Loading preview for UNID: $unid`n")
            $txtPreview.AppendText("Version: $version`n")
            $txtPreview.AppendText("=" * 60 + "`n`n")
            
            $preview = Get-MigrationPreview -ModPath $modPath -TypeUNID $unid -Version $version
            
            if ($preview.Found) {
                $formatted = Format-MigrationPreview -Preview $preview
                $txtPreview.AppendText($formatted)
            }
            else {
                $txtPreview.AppendText("Type not found: $($preview.Message)`n")
            }
        }
        catch {
            $txtPreview.AppendText("Error: $_`n")
        }
    })
    
    # Double-click on diff grid to preview type
    $gridDiff.Add_CellDoubleClick({
        $row = $gridDiff.CurrentRow
        if ($row -and $row.Tag) {
            $file = $row.Tag
            
            # Try to extract UNID from file name or content
            # For now, just show a message
            [System.Windows.Forms.MessageBox]::Show("Double-click on a file to preview types.`n`nTo preview a specific type, enter its UNID in the Type Preview tab.", 'Preview Type', 'OK', 'Information')
        }
    })
    
    # ============================================================
    # EVENT HANDLERS
    # ============================================================
    
    $script:issues = @()
    
    # ============================================================
    # DRAG AND DROP HANDLERS
    # ============================================================
    
    $form.Add_DragEnter({
        if ($_.Data.GetDataPresent([System.Windows.Forms.DataFormats]::FileDrop)) {
            $_.Effect = 'Copy'
        }
        else {
            $_.Effect = 'None'
        }
    })
    
    $form.Add_DragDrop({
        $droppedPaths = $_.Data.GetData([System.Windows.Forms.DataFormats]::FileDrop)
        
        if ($droppedPaths.Count -eq 0) { return }
        
        # Load smart detection module
        $smartModule = Join-Path $PSScriptRoot 'TranscendenceModTools_SmartDetect.ps1'
        if (Test-Path $smartModule) {
            try {
                . $smartModule
            }
            catch {
                # Module load failed, fall back to normal behavior
                $txtPath.Text = $droppedPaths[0]
                return
            }
        }
        else {
            # No smart module, just set path
            $txtPath.Text = $droppedPaths[0]
            return
        }
        
        # Run smart detection
        $detection = Invoke-SmartDetection -Paths $droppedPaths
        
        # Show smart detection dialog
        $dialogResult = Show-SmartDetectionDialog -Result $detection -ParentForm $form
        
        # Handle selected action
        if ($dialogResult.DialogResult -eq 'OK' -and $dialogResult.SelectedAction) {
            $action = $dialogResult.SelectedAction
            $path = $droppedPaths[0]
            
            switch ($action.Tab) {
                'XML Checker' {
                    $tabs.SelectedIndex = 0
                    $txtPath.Text = $path
                    if ($action.Name -eq 'Quick Validate' -or $action.Name -eq 'Fix Errors') {
                        $btnScan.PerformClick()
                    }
                }
                'Project Health' {
                    $tabs.SelectedIndex = 3
                    $txtHealthPath.Text = $path
                    $btnHealthScan.PerformClick()
                }
                'Cross-Mod Compatibility' {
                    $tabs.SelectedIndex = 4
                    $txtCompatPath.Text = $path
                }
                'Dependency Graph' {
                    $tabs.SelectedIndex = 5
                    $txtDepPath.Text = $path
                    $btnDepGenerate.PerformClick()
                }
                'Semantic Validation' {
                    $tabs.SelectedIndex = 7
                    $txtSemPath.Text = $path
                    $btnSemValidate.PerformClick()
                }
                'Live Preview' {
                    $tabs.SelectedIndex = 8
                    $txtLivePath.Text = $path
                    $btnLiveLoad.PerformClick()
                }
                default {
                    # Default to XML Checker
                    $tabs.SelectedIndex = 0
                    $txtPath.Text = $path
                }
            }
        }
        else {
            # User cancelled, just set path in XML Checker
            $tabs.SelectedIndex = 0
            $txtPath.Text = $droppedPaths[0]
        }
    })
    
    $btnBrowse.Add_Click({
        # Try folder browser first
        $folderDialog = [System.Windows.Forms.FolderBrowserDialog]::new()
        $folderDialog.Description = 'Select mod folder or file to scan'
        
        # Also allow file selection
        $fileDialog = [System.Windows.Forms.OpenFileDialog]::new()
        $fileDialog.Filter = 'XML files (*.xml)|*.xml|All files (*.*)|*.*'
        $fileDialog.Title = 'Select XML file to scan'
        
        # Show folder dialog
        if ($folderDialog.ShowDialog() -eq 'OK') {
            $txtPath.Text = $folderDialog.SelectedPath
        }
        # If cancelled, try file dialog
        elseif ($fileDialog.ShowDialog() -eq 'OK') {
            $txtPath.Text = $fileDialog.FileName
        }
    })
    
    $btnScan.Add_Click({
        $grid.Rows.Clear()
        $script:issues = @()
        
        $path = $txtPath.Text
        if ([string]::IsNullOrWhiteSpace($path)) {
            $lblStatus.Text = 'Please enter a path'
            return
        }
        
        if (-not (Test-Path $path)) {
            $lblStatus.Text = 'Path not found'
            return
        }
        
        $lblStatus.Text = 'Scanning...'
        $form.Refresh()
        
        # Get files (XML and TDB)
        $fileResult = Get-XmlAndTdbFiles -Path $path -Recurse:$chkRecurse.Checked
        $files = $fileResult.XmlFiles
        $tdbFiles = $fileResult.TdbFiles
        $tdbWarnings = $fileResult.TdbWarnings
        
        # Show TDB warnings in log
        if ($tdbWarnings.Count -gt 0) {
            $rtbLog.SelectionColor = [System.Drawing.Color]::Yellow
            foreach ($warning in $tdbWarnings) {
                $rtbLog.AppendText("WARNING: $warning`n")
            }
            $rtbLog.SelectionColor = $textWhite
        }
        
        if ($files.Count -eq 0 -and $tdbFiles.Count -eq 0) {
            $lblStatus.Text = 'No XML or TDB files found'
            return
        }
        
        # Load TDB parser if we have TDB files
        $tdbModule = Join-Path $PSScriptRoot 'TranscendenceModTools_TDBParser.ps1'
        $tdbParserLoaded = $false
        if ($tdbFiles.Count -gt 0 -and (Test-Path $tdbModule)) {
            try {
                . $tdbModule
                $tdbParserLoaded = $true
                $rtbLog.AppendText("TDB Parser loaded - will parse $($tdbFiles.Count) TDB file(s)`n")
            }
            catch {
                $rtbLog.SelectionColor = [System.Drawing.Color]::Yellow
                $rtbLog.AppendText("WARNING: TDB parser failed to load: $_`n")
                $rtbLog.SelectionColor = $textWhite
            }
        }
        
        # Load advanced features
        $advancedModule = Join-Path $PSScriptRoot 'TranscendenceModTools_Advanced.ps1'
        $advancedLoaded = $false
        if (Test-Path $advancedModule) {
            try {
                . $advancedModule
                $advancedLoaded = $true
            }
            catch {
                $lblStatus.Text = "Warning: Advanced features failed to load: $_"
            }
        }
        
        # Pre-populate UNID registry from Extensions, Collection, and Transcendence.tdb
        # Priority is based on UNID range AND file type:
        # 1=Game/DLC (0x0000-0x9FFF + official DLC TDBs), 2=Dynamic (0xF000-0xFFFF) + Official Mods,
        # 3=Registered Extensions (0xA000-0xCFFF), 4=User UNIDs (0xD000-0xEFFF), 
        # 5=Unknown/Unregistered (Extensions and third-party Collection mods are same priority)
        $allUnids = @{}
        $transcendenceRoot = Find-TranscendenceRoot -StartPath $PSScriptRoot
        if (-not $transcendenceRoot) {
            $rtbLog.AppendText("WARNING: Transcendence installation not detected.`n")
            $rtbLog.AppendText("  UNID scanning features require Extensions/Collection folders.`n")
            $rtbLog.AppendText("  Most other features (XML checking, error diagnosis) work without it.`n")
            $rtbLog.SelectionColor = $textYellow
            return
        }
        $extensionsPath = Join-Path $transcendenceRoot "Extensions"
        $collectionPath = Join-Path $transcendenceRoot "Collection"
        
        # Official DLC TDB files (have priority 1, same as game)
        $officialDlcTdbs = @(
            'CorporateCommand.tdb',
            'CorporateHierarchyVol01.tdb',
            'CorporateHierarchyVol1UNIDs.tdb',
            'DebugPart1.tdb',
            'EternityPort.tdb',
            'StarsOfThePilgrimHD.tdb',
            'StarsOfThePilgrimSoundtrack.tdb'
        )
        
        # Official mods (have higher priority than third-party mods)
        $officialMods = @(
            'VaultOfTheGalaxy',
            'Vault of the Galaxy'
        )
        
        # Function to check if a TDB file is official DLC
        function Test-IsOfficialDlcTdb {
            param([string]$FilePath)
            $fileName = Split-Path -Leaf $FilePath
            return $officialDlcTdbs -contains $fileName
        }
        
        # Function to check if a mod is official
        function Test-IsOfficialMod {
            param([string]$ModName)
            return $officialMods -contains $ModName
        }
        
        # Function to determine UNID range priority based on wiki.kronosaur.com/modding/unid_database
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
        
        # Function to scan UNIDs from a folder (XML and TDB files)
        # Collection contains official DLC TDBs (priority 1) and third-party mods (priority 5, same as Extensions)
        function Get-UnidsFromFolder {
            param([string]$FolderPath, [string]$SourceName, [bool]$IsCollection = $false)
            $unids = @{}
            if (Test-Path $FolderPath) {
                # Scan XML files
                $xmlFiles = Get-ChildItem -LiteralPath $FolderPath -Filter '*.xml' -Recurse -ErrorAction SilentlyContinue
                foreach ($xmlFile in $xmlFiles) {
                    try {
                        $text = [System.IO.File]::ReadAllText($xmlFile.FullName, [System.Text.Encoding]::UTF8)
                        $unidDefPattern = '<!ENTITY\s+(\w+)\s+"(0x[0-9A-Fa-f]+)"'
                        $matches = [regex]::Matches($text, $unidDefPattern, 'IgnoreCase')
                        foreach ($m in $matches) {
                            $unidValue = $m.Groups[2].Value
                            # Priority is based on UNID range
                            $rangePriority = Get-UnidRangePriority -UnidValue $unidValue
                            $finalPriority = if ($rangePriority -lt 99) { $rangePriority } else { 5 }  # Default to 5 for unregistered
                            $rangeDesc = Get-UnidRangeDescription -UnidValue $unidValue
                            
                            # Check if this is an official mod in Collection
                            if ($IsCollection) {
                                $modFolder = Split-Path (Split-Path $xmlFile.FullName -Parent) -Leaf
                                if (Test-IsOfficialMod -ModName $modFolder) {
                                    # Official mods get priority 2 (higher than third-party mods)
                                    if ($finalPriority -gt 2) { $finalPriority = 2 }
                                }
                            }
                            
                            if (-not $unids.ContainsKey($unidValue)) {
                                $unids[$unidValue] = [PSCustomObject]@{
                                    File = $xmlFile.FullName
                                    Priority = $finalPriority
                                    Source = $SourceName
                                    Range = $rangeDesc
                                    UnidValue = $unidValue
                                }
                            }
                        }
                    } catch { }
                }
                
                # Scan TDB files
                # Official DLC TDBs get priority 1 (same as game), third-party TDBs get priority based on UNID range
                $tdbFiles = Get-ChildItem -LiteralPath $FolderPath -Filter '*.tdb' -Recurse -ErrorAction SilentlyContinue
                foreach ($tdbFile in $tdbFiles) {
                    $isOfficialDlc = Test-IsOfficialDlcTdb -FilePath $tdbFile.FullName
                    $tdbUnids = Get-UnidsFromTdb -TdbPath $tdbFile.FullName
                    foreach ($unid in $tdbUnids.Keys) {
                        if (-not $unids.ContainsKey($unid)) {
                            # Official DLC TDBs get priority 1 (same as game), regardless of UNID range
                            if ($isOfficialDlc) {
                                $finalPriority = 1
                                $rangeDesc = "Official DLC"
                            }
                            else {
                                # Third-party TDBs: priority based on UNID range
                                $rangePriority = Get-UnidRangePriority -UnidValue $unid
                                $finalPriority = if ($rangePriority -lt 99) { $rangePriority } else { 5 }
                                $rangeDesc = Get-UnidRangeDescription -UnidValue $unid
                            }
                            
                            $unids[$unid] = [PSCustomObject]@{
                                File = $tdbFile.FullName
                                Priority = $finalPriority
                                Source = if ($isOfficialDlc) { "Official DLC" } else { $SourceName }
                                Range = $rangeDesc
                                UnidValue = $unid
                            }
                        }
                    }
                }
            }
            return $unids
        }
        
        # Function to extract UNIDs from TDB file
        function Get-UnidsFromTdb {
            param([string]$TdbPath)
            $unids = @{}
            if (Test-Path $TdbPath) {
                try {
                    # Load TDB parser if available
                    $tdbModule = Join-Path $PSScriptRoot 'TranscendenceModTools_TDBParser.ps1'
                    if (Test-Path $tdbModule) {
                        . $tdbModule
                        $tdbPreview = Get-TdbPreview -Path $TdbPath
                        if ($tdbPreview -and $tdbPreview.Parsed -and $tdbPreview.Parsed.Unids) {
                            foreach ($unid in $tdbPreview.Parsed.Unids) {
                                if (-not $unids.ContainsKey($unid)) {
                                    $unids[$unid] = $TdbPath
                                }
                            }
                        }
                        elseif ($tdbPreview -and $tdbPreview.Extracted -and $tdbPreview.Extracted.Unids) {
                            foreach ($unid in $tdbPreview.Extracted.Unids) {
                                if (-not $unids.ContainsKey($unid)) {
                                    $unids[$unid] = $TdbPath
                                }
                            }
                        }
                    }
                } catch { }
            }
            return $unids
        }
        
        # Populate from Transcendence.tdb in game root (Priority 1 - highest)
        $transcendenceTdb = Join-Path $transcendenceRoot "Transcendence.tdb"
        $tdbUnids = Get-UnidsFromTdb -TdbPath $transcendenceTdb
        foreach ($unid in $tdbUnids.Keys) {
            # Use range-based priority (game UNIDs should be in 0x0000-0x9FFF range)
            $rangePriority = Get-UnidRangePriority -UnidValue $unid
            $finalPriority = if ($rangePriority -lt 99) { $rangePriority } else { 1 }
            $rangeDesc = Get-UnidRangeDescription -UnidValue $unid
            
            $allUnids[$unid] = [PSCustomObject]@{
                File = $tdbUnids[$unid]
                Priority = $finalPriority
                Source = 'Game'
                Range = $rangeDesc
                UnidValue = $unid
            }
        }
        
        # Populate from Collection
        # Collection contains official DLC TDBs (priority 1), official mods (priority 2), and third-party mods (priority 5)
        $collUnids = Get-UnidsFromFolder -FolderPath $collectionPath -SourceName "Collection" -IsCollection $true
        foreach ($unid in $collUnids.Keys) {
            if (-not $allUnids.ContainsKey($unid)) {
                $allUnids[$unid] = $collUnids[$unid]
            }
            else {
                # Conflict: Check if existing has higher priority (based on UNID range)
                $existingPriority = if ($allUnids[$unid].Priority) { $allUnids[$unid].Priority } else { 5 }
                $newPriority = $collUnids[$unid].Priority
                if ($newPriority -lt $existingPriority) {
                    # New UNID has higher priority, replace
                    $allUnids[$unid] = $collUnids[$unid]
                }
                elseif ($newPriority -eq $existingPriority) {
                    # Same priority - track as conflict
                    if ($allUnids[$unid] -is [PSCustomObject]) {
                        $allUnids[$unid] = @($allUnids[$unid], $collUnids[$unid])
                    }
                    else {
                        $allUnids[$unid] = @($allUnids[$unid]) + @($collUnids[$unid])
                    }
                }
                # If existing has higher priority, keep it (don't add new one)
            }
        }
        
        # Populate from Extensions (same priority as Collection - based on UNID range only)
        $extUnids = Get-UnidsFromFolder -FolderPath $extensionsPath -SourceName "Extensions"
        foreach ($unid in $extUnids.Keys) {
            if (-not $allUnids.ContainsKey($unid)) {
                $allUnids[$unid] = $extUnids[$unid]
            }
            else {
                # Conflict: Check if existing has higher priority (based on UNID range)
                $existingPriority = if ($allUnids[$unid].Priority) { $allUnids[$unid].Priority } else { 5 }
                $newPriority = $extUnids[$unid].Priority
                if ($newPriority -lt $existingPriority) {
                    # New UNID has higher priority, replace
                    $allUnids[$unid] = $extUnids[$unid]
                }
                elseif ($newPriority -eq $existingPriority) {
                    # Same priority - track as conflict
                    if ($allUnids[$unid] -is [PSCustomObject]) {
                        $allUnids[$unid] = @($allUnids[$unid], $extUnids[$unid])
                    }
                    else {
                        $allUnids[$unid] = @($allUnids[$unid]) + @($extUnids[$unid])
                    }
                }
                # If existing has higher priority, keep it (don't add new one)
            }
        }
        
        $sources = @()
        if ($extUnids.Count -gt 0) { $sources += "Extensions ($($extUnids.Count))" }
        if ($collUnids.Count -gt 0) { $sources += "Collection ($($collUnids.Count))" }
        if ($tdbUnids.Count -gt 0) { $sources += "Transcendence.tdb ($($tdbUnids.Count))" }
        $rtbLog.AppendText("Pre-loaded $($allUnids.Count) UNID(s) from $($sources -join ', ')`n")
        $form.Refresh()
        
        # Scan XML files with all checks
        $fileCount = 0
        $totalFiles = $files.Count + $tdbFiles.Count
        foreach ($f in $files) {
            $fileCount++
            $fileName = Split-Path -Leaf $f
            $rtbLog.AppendText("[$fileCount/$totalFiles] Scanning XML: $fileName`n")
            $form.Refresh()
            $fileIssues = @()
            try {
                $fileIssues += Get-XmlIssues -FilePath $f
                $hasWellformedError = @($fileIssues | Where-Object { $_.Code -eq 'XML_WELLFORMED_ERROR' }).Count -gt 0
                $hasUndeclaredEntity = @($fileIssues | Where-Object { $_.Code -eq 'ENTITY_UNDECLARED' -or ($_.Code -eq 'XML_WELLFORMED_ERROR' -and $_.Message -match 'undeclared entity') }).Count -gt 0
                
                # Advanced checks if module loaded
                if ($advancedLoaded) {
                    # Only run structure heuristics if XML parsing failed (XmlReader is authoritative).
                    if ($hasWellformedError) {
                        try { 
                            $structureIssues = Get-XmlStructureIssues -FilePath $f
                            # Mark structural issues as potentially cascading if caused by undeclared entities
                            if ($hasUndeclaredEntity) {
                                foreach ($issue in $structureIssues) {
                                    if ($issue.Code -match 'TAG_MISMATCH|UNEXPECTED_CLOSE_TAG|UNCLOSED_TAG') {
                                        $issue.Message = $issue.Message + " [POTENTIALLY CASCADING - fix undeclared entities first]"
                                        $issue.IsCascading = $true
                                    }
                                }
                            }
                            $fileIssues += $structureIssues
                        } catch { }
                    }
                    try {
                        $fileIssues += Get-TlispExpressionIssues -FilePath $f
                    } catch { }
                    try {
                        $fileIssues += Get-UnidReferenceIssues -FilePath $f -AllUnids $allUnids
                    } catch { }
                    try {
                        $fileIssues += Get-ResourcePathIssues -FilePath $f
                    } catch { }
                    try {
                        $fileIssues += Get-DeprecatedAttributeIssues -FilePath $f
                    } catch { }
                    try {
                        $indentIssues = Get-IndentationIssues -FilePath $f
                        if ($indentIssues) { $fileIssues += $indentIssues }
                    } catch { }
                }
            }
            catch {
                $fileIssues += [PSCustomObject]@{
                    File = $f
                    Line = 0
                    Code = 'SCAN_ERROR'
                    Severity = 'Error'
                    Message = "Error scanning file: $_"
                    CanFix = $false
                }
            }
            
            if ($fileIssues.Count -gt 0) {
                $rtbLog.SelectionColor = [System.Drawing.Color]::Yellow
                $rtbLog.AppendText("  Found $($fileIssues.Count) issue(s)`n")
                $rtbLog.SelectionColor = $textWhite
            }
            
            foreach ($issue in $fileIssues) {
                $script:issues += $issue
                $rowIndex = $grid.Rows.Add($issue.Severity, $issue.Code, $issue.Line, $issue.Message, $issue.File)
                
                # Add to log with color coding
                $logLine = "  [$($issue.Severity)] Line $($issue.Line): $($issue.Code) - $($issue.Message)`n"
                switch ($issue.Severity) {
                    'Error' { $rtbLog.SelectionColor = [System.Drawing.Color]::FromArgb(255, 100, 100) }
                    'Warning' { $rtbLog.SelectionColor = [System.Drawing.Color]::FromArgb(255, 200, 100) }
                    'Info' { $rtbLog.SelectionColor = [System.Drawing.Color]::FromArgb(150, 200, 255) }
                    default { $rtbLog.SelectionColor = $textWhite }
                }
                $rtbLog.AppendText($logLine)
                $rtbLog.SelectionColor = $textWhite
                
                # Color by severity
                $row = $grid.Rows[$rowIndex]
                switch ($issue.Severity) {
                    'Error' { $row.DefaultCellStyle.ForeColor = $accentRed }
                    'Warning' { $row.DefaultCellStyle.ForeColor = $accentYellow }
                }
            }
        }
        
        # Scan TDB files if parser is loaded
        if ($tdbParserLoaded -and $tdbFiles.Count -gt 0) {
            foreach ($tdb in $tdbFiles) {
                $fileCount++
                $fileName = Split-Path -Leaf $tdb
                $rtbLog.AppendText("[$fileCount/$totalFiles] Scanning TDB: $fileName`n")
                $form.Refresh()
                $fileIssues = @()
                try {
                    $tdbPreview = Get-TdbPreview -Path $tdb
                    if ($tdbPreview.SemanticIssues) {
                        foreach ($issue in $tdbPreview.SemanticIssues) {
                            $fileIssues += [PSCustomObject]@{
                                File = $tdb
                                Line = 0
                                Code = $issue.Type
                                Severity = $issue.Severity
                                Message = $issue.Message
                                CanFix = $false
                            }
                        }
                    }
                    
                    # Check for deprecations
                    $deprecations = Test-TdbDeprecation -TdbData $tdbPreview
                    foreach ($dep in $deprecations) {
                        $fileIssues += [PSCustomObject]@{
                            File = $tdb
                            Line = 0
                            Code = 'TDB_DEPRECATED'
                            Severity = $dep.Severity
                            Message = "$($dep.Type): $($dep.Suggestion)"
                            CanFix = $false
                        }
                    }
                }
                catch {
                    $fileIssues += [PSCustomObject]@{
                        File = $tdb
                        Line = 0
                        Code = 'TDB_SCAN_ERROR'
                        Severity = 'Error'
                        Message = "Error scanning TDB file: $_"
                        CanFix = $false
                    }
                }
                
                if ($fileIssues.Count -gt 0) {
                    $rtbLog.SelectionColor = [System.Drawing.Color]::Yellow
                    $rtbLog.AppendText("  Found $($fileIssues.Count) issue(s)`n")
                    $rtbLog.SelectionColor = $textWhite
                }
                else {
                    $rtbLog.SelectionColor = [System.Drawing.Color]::FromArgb(100, 255, 100)
                    $rtbLog.AppendText("  No issues found`n")
                    $rtbLog.SelectionColor = $textWhite
                }
                
                foreach ($issue in $fileIssues) {
                    $script:issues += $issue
                    $rowIndex = $grid.Rows.Add($issue.Severity, $issue.Code, $issue.Line, $issue.Message, $issue.File)
                    
                    # Add to log with color coding
                    $logLine = "  [$($issue.Severity)] $($issue.Code) - $($issue.Message)`n"
                    switch ($issue.Severity) {
                        'Error' { $rtbLog.SelectionColor = [System.Drawing.Color]::FromArgb(255, 100, 100) }
                        'Warning' { $rtbLog.SelectionColor = [System.Drawing.Color]::FromArgb(255, 200, 100) }
                        'Info' { $rtbLog.SelectionColor = [System.Drawing.Color]::FromArgb(150, 200, 255) }
                        default { $rtbLog.SelectionColor = $textWhite }
                    }
                    $rtbLog.AppendText($logLine)
                    $rtbLog.SelectionColor = $textWhite
                    
                    # Color by severity
                    $row = $grid.Rows[$rowIndex]
                    switch ($issue.Severity) {
                        'Error' { $row.DefaultCellStyle.ForeColor = $accentRed }
                        'Warning' { $row.DefaultCellStyle.ForeColor = $accentYellow }
                    }
                }
            }
        }
        
        $errorCount = @($script:issues | Where-Object { $_.Severity -eq 'Error' }).Count
        $warnCount = @($script:issues | Where-Object { $_.Severity -eq 'Warning' }).Count
        $fixable = @($script:issues | Where-Object { $_.CanFix }).Count
        
        $totalScanned = $files.Count + $tdbFiles.Count
        $summary = "Scanned $totalScanned file(s) ($($files.Count) XML, $($tdbFiles.Count) TDB): $errorCount error(s), $warnCount warning(s), $fixable fixable"
        $lblStatus.Text = $summary
        
        # Add summary to log
        $rtbLog.AppendText("`n=== Scan Complete ===`n")
        $rtbLog.SelectionColor = [System.Drawing.Color]::FromArgb(100, 255, 100)
        $rtbLog.AppendText($summary + "`n")
        $rtbLog.SelectionColor = $textWhite
        $rtbLog.AppendText("Completed at $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')`n")
        $rtbLog.ScrollToCaret()
    })
    
    $btnFix.Add_Click({
        $fixableIssues = @($script:issues | Where-Object { $_.CanFix })
        if ($fixableIssues.Count -eq 0) {
            [System.Windows.Forms.MessageBox]::Show('No fixable issues found.', 'Auto-Fix', 'OK', 'Information')
            return
        }
        
        $result = [System.Windows.Forms.MessageBox]::Show(
            "Found $($fixableIssues.Count) fixable issue(s). Create backups and fix?",
            'Auto-Fix',
            'YesNo',
            'Question'
        )
        
        if ($result -ne 'Yes') { return }
        
        $fixedFiles = @{}
        foreach ($issue in $fixableIssues) {
            if (-not $fixedFiles.ContainsKey($issue.File)) {
                # Create backup
                $backupPath = $issue.File + '.bak'
                Copy-Item -LiteralPath $issue.File -Destination $backupPath -Force
                
                $text = [System.IO.File]::ReadAllText($issue.File, [System.Text.Encoding]::UTF8)
                $fixedFiles[$issue.File] = $text
            }
        }
        
        # Apply fixes
        $fixCount = 0
        foreach ($file in $fixedFiles.Keys) {
            $text = $fixedFiles[$file]
            $modified = $false
            
            # Get issues for this file
            $fileIssues = @($fixableIssues | Where-Object { $_.File -eq $file })
            
            # Fix BOM
            $bytes = [System.IO.File]::ReadAllBytes($file)
            if ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) {
                $bytes = $bytes[3..($bytes.Length - 1)]
                [System.IO.File]::WriteAllBytes($file, $bytes)
                $text = [System.Text.Encoding]::UTF8.GetString($bytes)
                $modified = $true
                $fixCount++
            }
            
            # Fix invalid symbol syntax 'symbol' -> 'symbol
            foreach ($issue in $fileIssues) {
                if ($issue.Code -eq 'INVALID_SYMBOL_SYNTAX') {
                    $pattern = "'([a-zA-Z_][a-zA-Z0-9_]*)'"
                    $text = [regex]::Replace($text, $pattern, { param($m) "'$($m.Groups[1].Value)" })
                    $modified = $true
                    $fixCount++
                }
            }
            
            # Fix raw > in content (outside tags/comments) - careful replacement
            foreach ($issue in $fileIssues) {
                if ($issue.Code -eq 'RAW_GT_IN_CONTENT') {
                    # This is complex - we need to avoid replacing > inside tags
                    # For now, do a simple replacement but warn user to verify
                    # Better approach: line-by-line with context awareness
                    $lines = $text -split "`n"
                    $newLines = @()
                    foreach ($line in $lines) {
                        # Simple heuristic: if line has > and no <, likely raw > in content
                        if ($line -match '>' -and $line -notmatch '<') {
                            $line = $line -replace '>', '&gt;'
                            $modified = $true
                            $fixCount++
                        }
                        $newLines += $line
                    }
                    $text = $newLines -join "`n"
                }
            }
            
            # Fix xmlCreate with raw XML
            foreach ($issue in $fileIssues) {
                if ($issue.Code -eq 'XMLCREATE_RAW_XML') {
                    # Find xmlCreate "..." patterns and escape < and > inside
                    $pattern = '(xmlCreate\s*\(?\s*")([^"]*<[^"]*>)'
                    $text = [regex]::Replace($text, $pattern, {
                        param($m)
                        $prefix = $m.Groups[1].Value
                        $content = $m.Groups[2].Value
                        $content = $content -replace '<', '&lt;' -replace '>', '&gt;'
                        "$prefix$content"
                    }, [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
                    $modified = $true
                    $fixCount++
                }
            }
            
            if ($modified) {
                $utf8NoBom = [System.Text.UTF8Encoding]::new($false)
                [System.IO.File]::WriteAllText($file, $text, $utf8NoBom)
            }
        }
        
        [System.Windows.Forms.MessageBox]::Show(
            "Fixed $fixCount issue(s) in $($fixedFiles.Count) file(s).`nBackups created with .bak extension.`n`nPlease verify the changes and rescan.",
            'Auto-Fix Complete',
            'OK',
            'Information'
        )
        
        # Rescan
        $btnScan.PerformClick()
    })
    
    $btnFormat.Add_Click({
        $path = $txtPath.Text
        if ([string]::IsNullOrWhiteSpace($path)) {
            $lblStatus.Text = 'Please enter a path'
            return
        }
        
        if (-not (Test-Path $path)) {
            $lblStatus.Text = 'Path not found'
            return
        }
        
        # Load formatting module
        $formatModule = Join-Path $PSScriptRoot 'TranscendenceModTools_Formatting.ps1'
        if (-not (Test-Path $formatModule)) {
            [System.Windows.Forms.MessageBox]::Show('Formatting module not found.', 'Format', 'OK', 'Warning')
            return
        }
        
        try {
            . $formatModule
        }
        catch {
            [System.Windows.Forms.MessageBox]::Show("Failed to load formatting module: $_", 'Format', 'OK', 'Error')
            return
        }
        
        # Get files
        $files = @()
        if (Test-Path $path -PathType Leaf) {
            if ($path.EndsWith('.xml')) { $files = @($path) }
        }
        else {
            $opts = @{ Filter = '*.xml' }
            if ($chkRecurse.Checked) { $opts.Recurse = $true }
            $files = @(Get-ChildItem -LiteralPath $path @opts | ForEach-Object { $_.FullName })
        }
        
        if ($files.Count -eq 0) {
            $lblStatus.Text = 'No XML files found'
            return
        }
        
        $result = [System.Windows.Forms.MessageBox]::Show(
            "Format $($files.Count) file(s)? Backups will be created with .bak extension.",
            'Format XML',
            'YesNo',
            'Question'
        )
        
        if ($result -ne 'Yes') { return }
        
        $formatted = 0
        foreach ($f in $files) {
            try {
                if (Format-XmlFile -FilePath $f -IndentChar "`t" -AlignAttributes -BreakLongLines) {
                    $formatted++
                }
            }
            catch {
                # Continue with other files
            }
        }
        
        [System.Windows.Forms.MessageBox]::Show(
            "Formatted $formatted of $($files.Count) file(s). Backups created with .bak extension.",
            'Format Complete',
            'OK',
            'Information'
        )
        
        $lblStatus.Text = "Formatted $formatted file(s)"
    })
    
    $btnAnalyze.Add_Click({
        $errorText = $txtError.Text
        if ([string]::IsNullOrWhiteSpace($errorText)) {
            $txtResult.Text = 'Please paste an error message to analyze.'
            return
        }
        
        $results = Parse-ErrorMessage -ErrorText $errorText
        
        $output = [System.Text.StringBuilder]::new()
        [void]$output.AppendLine('═══════════════════════════════════════════════════════════')
        [void]$output.AppendLine('                    ERROR ANALYSIS')
        [void]$output.AppendLine('═══════════════════════════════════════════════════════════')
        
        foreach ($r in $results) {
            [void]$output.AppendLine('')
            [void]$output.AppendLine("[$($r.Code)]")
            if ($r.File) { [void]$output.AppendLine("  File: $($r.File)") }
            if ($r.Line -gt 0) { [void]$output.AppendLine("  Line: $($r.Line)") }
            [void]$output.AppendLine('')
            [void]$output.AppendLine('CAUSE:')
            [void]$output.AppendLine("  $($r.Cause)")
            [void]$output.AppendLine('')
            [void]$output.AppendLine('SOLUTION:')
            [void]$output.AppendLine("  $($r.Solution)")
            if ($r.CanFix) {
                [void]$output.AppendLine('')
                [void]$output.AppendLine('[✓ This issue can be auto-fixed by the XML Checker]')
            }
        }
        
        [void]$output.AppendLine('')
        [void]$output.AppendLine('═══════════════════════════════════════════════════════════')
        
        $txtResult.Text = $output.ToString()
    })
    
    $btnClear.Add_Click({
        $txtError.Text = ''
        $txtResult.Text = ''
    })
    
    # Double-click to open file
    $grid.Add_CellDoubleClick({
        param($sender, $e)
        if ($e.RowIndex -ge 0) {
            $file = $grid.Rows[$e.RowIndex].Cells['File'].Value
            $line = $grid.Rows[$e.RowIndex].Cells['Line'].Value
            if ($file -and (Test-Path $file)) {
                # Try to open in VS Code at line
                $codeCmd = Get-Command 'code' -ErrorAction SilentlyContinue
                if ($codeCmd) {
                    & code --goto "${file}:${line}"
                }
                else {
                    Start-Process $file
                }
            }
        }
    })
    
    # Project Health event handlers
    $btnHealthBrowse.Add_Click({
        $folderDialog = [System.Windows.Forms.FolderBrowserDialog]::new()
        $folderDialog.Description = 'Select mod project folder'
        if ($folderDialog.ShowDialog() -eq 'OK') {
            $txtHealthPath.Text = $folderDialog.SelectedPath
        }
    })
    
    $btnHealthScan.Add_Click({
        $projectPath = $txtHealthPath.Text
        if ([string]::IsNullOrWhiteSpace($projectPath)) {
            $txtHealthReport.Text = 'Please enter a project path'
            return
        }
        
        if (-not (Test-Path $projectPath)) {
            $txtHealthReport.Text = 'Path not found'
            return
        }
        
        $txtHealthReport.Text = 'Scanning project...'
        $form.Refresh()
        
        # Load advanced features
        $advancedModule = Join-Path $PSScriptRoot 'TranscendenceModTools_Advanced.ps1'
        if (Test-Path $advancedModule) {
            try {
                . $advancedModule
            }
            catch {
                $txtHealthReport.Text = "Warning: Advanced features failed to load: $_"
                return
            }
        }
        
        # Get all files
        $files = @(Get-ChildItem -LiteralPath $projectPath -Filter '*.xml' -Recurse | ForEach-Object { $_.FullName })
        
        if ($files.Count -eq 0) {
            $txtHealthReport.Text = 'No XML files found in project'
            return
        }
        
        # Generate health report
        $report = Get-ProjectHealthReport -Files $files -GetXmlIssuesFunc ${function:Get-XmlIssues}
        
        # Format report
        $output = [System.Text.StringBuilder]::new()
        [void]$output.AppendLine('═══════════════════════════════════════════════════════════')
        [void]$output.AppendLine('                  PROJECT HEALTH REPORT')
        [void]$output.AppendLine('═══════════════════════════════════════════════════════════')
        [void]$output.AppendLine('')
        [void]$output.AppendLine("Total Files Scanned: $($report.TotalFiles)")
        [void]$output.AppendLine("Files with Errors: $($report.FilesWithErrors)")
        [void]$output.AppendLine("Files with Warnings: $($report.FilesWithWarnings)")
        [void]$output.AppendLine('')
        [void]$output.AppendLine('═══════════════════════════════════════════════════════════')
        [void]$output.AppendLine('                    DETAILED STATISTICS')
        [void]$output.AppendLine('═══════════════════════════════════════════════════════════')
        [void]$output.AppendLine('')
        
        # Format statistics in requested format
        $xmlErrorsColor = if ($report.XmlErrors -eq 0) { '✓' } else { '❌' }
        $missingResColor = if ($report.MissingResources -eq 0) { '✓' } else { '⚠' }
        $unusedUnidColor = if ($report.UnusedUnids -eq 0) { '✓' } else { '⚠' }
        $deprecatedColor = if ($report.DeprecatedAttributes -eq 0) { '✓' } else { '⚠' }
        $indentColor = if ($report.InconsistentIndentation -eq 0) { '✓' } else { '⚠' }
        
        [void]$output.AppendLine("$xmlErrorsColor XML errors:                    $($report.XmlErrors)")
        [void]$output.AppendLine("$missingResColor Missing resources:             $($report.MissingResources)")
        [void]$output.AppendLine("$unusedUnidColor Unused UNIDs:                  $($report.UnusedUnids)")
        [void]$output.AppendLine("$deprecatedColor Deprecated attributes:        $($report.DeprecatedAttributes)")
        [void]$output.AppendLine("$indentColor Files with inconsistent indentation: $($report.InconsistentIndentation)")
        [void]$output.AppendLine('')
        [void]$output.AppendLine('═══════════════════════════════════════════════════════════')
        [void]$output.AppendLine('                    ADDITIONAL METRICS')
        [void]$output.AppendLine('═══════════════════════════════════════════════════════════')
        [void]$output.AppendLine('')
        [void]$output.AppendLine("Total Errors:                  $($report.TotalErrors)")
        [void]$output.AppendLine("Total Warnings:                 $($report.TotalWarnings)")
        [void]$output.AppendLine("UNID Duplicates:                $($report.UnidDuplicates)")
        [void]$output.AppendLine('')
        [void]$output.AppendLine('═══════════════════════════════════════════════════════════')
        [void]$output.AppendLine('                    FILE STATUS')
        [void]$output.AppendLine('═══════════════════════════════════════════════════════════')
        [void]$output.AppendLine('')
        
        foreach ($file in $report.FileStatus.Keys | Sort-Object) {
            $status = $report.FileStatus[$file]
            $fileName = Split-Path -Leaf $file
            $relPath = $file.Replace($projectPath, '.').TrimStart('\', '/')
            
            if ($status.Errors -gt 0) {
                [void]$output.AppendLine("  ❌ $relPath")
                [void]$output.AppendLine("     Errors: $($status.Errors), Warnings: $($status.Warnings)")
            }
            elseif ($status.Warnings -gt 0) {
                [void]$output.AppendLine("  ⚠ $relPath")
                [void]$output.AppendLine("     Warnings: $($status.Warnings)")
            }
            else {
                [void]$output.AppendLine("  ✓ $relPath")
            }
        }
        
        [void]$output.AppendLine('')
        [void]$output.AppendLine('═══════════════════════════════════════════════════════════')
        
        $txtHealthReport.Text = $output.ToString()
    })
    
    $btnResourceCheck.Add_Click({
        $modPath = $txtHealthPath.Text
        if ([string]::IsNullOrWhiteSpace($modPath)) {
            $txtHealthReport.Text = 'Please enter a mod path'
            return
        }
        
        if (-not (Test-Path $modPath)) {
            $txtHealthReport.Text = 'Path not found'
            return
        }
        
        $txtHealthReport.Text = 'Checking resource integrity...'
        $form.Refresh()
        
        # Load resource integrity module
        $resourceModule = Join-Path $PSScriptRoot 'TranscendenceModTools_ResourceIntegrity.ps1'
        if (Test-Path $resourceModule) {
            try {
                . $resourceModule
            }
            catch {
                $txtHealthReport.Text = "Failed to load resource integrity module: $_"
                return
            }
        }
        else {
            $txtHealthReport.Text = 'Resource integrity module not found'
            return
        }
        
        # Get all XML files
        $files = @(Get-ChildItem -LiteralPath $modPath -Filter '*.xml' -Recurse | ForEach-Object { $_.FullName })
        
        if ($files.Count -eq 0) {
            $txtHealthReport.Text = 'No XML files found'
            return
        }
        
        # Run resource integrity check
        $issues = Get-ResourceIntegrityIssues -Files $files
        
        # Format report
        $output = [System.Text.StringBuilder]::new()
        [void]$output.AppendLine('═══════════════════════════════════════════════════════════')
        [void]$output.AppendLine('              RESOURCE INTEGRITY REPORT')
        [void]$output.AppendLine('═══════════════════════════════════════════════════════════')
        [void]$output.AppendLine('')
        [void]$output.AppendLine("Files Scanned: $($files.Count)")
        [void]$output.AppendLine("Issues Found: $($issues.Count)")
        [void]$output.AppendLine('')
        
        # Group by severity
        $errors = @($issues | Where-Object { $_.Severity -eq 'Error' })
        $warnings = @($issues | Where-Object { $_.Severity -eq 'Warning' })
        
        [void]$output.AppendLine("Errors: $($errors.Count)")
        [void]$output.AppendLine("Warnings: $($warnings.Count)")
        [void]$output.AppendLine('')
        
        # Group by type
        $byType = $issues | Group-Object ResourceType
        
        foreach ($group in $byType | Sort-Object Name) {
            [void]$output.AppendLine('═══════════════════════════════════════════════════════════')
            [void]$output.AppendLine("$($group.Name) Issues ($($group.Count))")
            [void]$output.AppendLine('═══════════════════════════════════════════════════════════')
            [void]$output.AppendLine('')
            
            foreach ($issue in $group.Group | Sort-Object File, Line) {
                $severity = if ($issue.Severity -eq 'Error') { '❌' } else { '⚠' }
                $fileName = Split-Path -Leaf $issue.File
                $lineNum = $issue.Line
                [void]$output.AppendLine("$severity $fileName`:$lineNum")
                [void]$output.AppendLine("   $($issue.Message)")
                [void]$output.AppendLine("   Resource: $($issue.ResourcePath)")
                [void]$output.AppendLine('')
            }
        }
        
        [void]$output.AppendLine('═══════════════════════════════════════════════════════════')
        
        $txtHealthReport.Text = $output.ToString()
    })
    
    # Menu handlers
    $exportItem.Add_Click({
        if ($script:issues.Count -eq 0) {
            [System.Windows.Forms.MessageBox]::Show('No issues to export. Please scan first.', 'Export', 'OK', 'Information')
            return
        }
        
        $saveDialog = [System.Windows.Forms.SaveFileDialog]::new()
        $saveDialog.Filter = 'CSV files (*.csv)|*.csv|Text files (*.txt)|*.txt|All files (*.*)|*.*'
        $saveDialog.Title = 'Export Report'
        $saveDialog.FileName = 'TranscendenceModReport.csv'
        
        if ($saveDialog.ShowDialog() -eq 'OK') {
            $ext = [System.IO.Path]::GetExtension($saveDialog.FileName).ToLower()
            
            if ($ext -eq '.csv') {
                $script:issues | Select-Object Severity, Code, Line, Message, File, @{Name='CanFix';Expression={$_.CanFix}} |
                    Export-Csv -Path $saveDialog.FileName -NoTypeInformation -Encoding UTF8
            }
            else {
                $lines = @()
                $lines += 'Transcendence Mod Tools - Issue Report'
                $lines += "Generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
                $lines += "Total Issues: $($script:issues.Count)"
                $lines += ''
                $lines += '═══════════════════════════════════════════════════════════'
                $lines += ''
                
                $byFile = $script:issues | Group-Object File
                foreach ($fileGroup in $byFile | Sort-Object Name) {
                    $lines += "[$($fileGroup.Name)]"
                    foreach ($issue in $fileGroup.Group | Sort-Object Line) {
                        $lines += "  [$($issue.Severity)] L$($issue.Line): $($issue.Code) - $($issue.Message)"
                    }
                    $lines += ''
                }
                
                [System.IO.File]::WriteAllLines($saveDialog.FileName, $lines)
            }
            
            [System.Windows.Forms.MessageBox]::Show("Report exported to:`n$($saveDialog.FileName)", 'Export Complete', 'OK', 'Information')
        }
    })
    
    $exitItem.Add_Click({
        $form.Close()
    })
    
    $aboutItem.Add_Click({
        $aboutText = @"
Transcendence Mod Tools
Version 2.0

A comprehensive tool for Transcendence mod development:
• XML Structure Validation
• TLisp Expression Checking
• UNID Reference Validation
• Error Message Diagnosis
• Project Health Reports
• Auto-Fix Capabilities

Features:
✓ XML well-formedness checking
✓ Tag matching and validation
✓ Parentheses balance checking
✓ UNID duplicate detection
✓ Error pattern recognition
✓ Multi-file project support

Created for the Transcendence modding community.

See FEATURES.md and QUICK_REFERENCE.md for more information.
"@
        [System.Windows.Forms.MessageBox]::Show($aboutText, 'About Transcendence Mod Tools', 'OK', 'Information')
    })
    
    $quickRefItem.Add_Click({
        $refPath = Join-Path $PSScriptRoot 'QUICK_REFERENCE.md'
        if (Test-Path $refPath) {
            Start-Process $refPath
        }
        else {
            [System.Windows.Forms.MessageBox]::Show('Quick Reference guide not found.', 'Help', 'OK', 'Warning')
        }
    })
    
    # UNID Manager handlers
    $btnUnidBrowse.Add_Click({
        $folderDialog = [System.Windows.Forms.FolderBrowserDialog]::new()
        $folderDialog.Description = 'Select mod folder'
        if ($folderDialog.ShowDialog() -eq 'OK') {
            $txtUnidPath.Text = $folderDialog.SelectedPath
        }
    })
    
    $btnUnidIntelligence.Add_Click({
        $modPath = $txtUnidPath.Text
        if ([string]::IsNullOrWhiteSpace($modPath)) {
            return
        }
        
        if (-not (Test-Path $modPath)) {
            return
        }
        
        # Load UNID intelligence module
        $unidModule = Join-Path $PSScriptRoot 'TranscendenceModTools_UNIDIntelligence.ps1'
        if (Test-Path $unidModule) {
            try {
                . $unidModule
            }
            catch {
                [System.Windows.Forms.MessageBox]::Show("Failed to load UNID intelligence module: $_", 'Error', 'OK', 'Error')
                return
            }
        }
        
        # Get all XML files
        $files = @(Get-ChildItem -LiteralPath $modPath -Filter '*.xml' -Recurse | ForEach-Object { $_.FullName })
        
        if ($files.Count -eq 0) {
            return
        }
        
        # Get all mod paths for override detection
        $extensionsPath = Split-Path -Parent $modPath
        $allModPaths = @()
        if (Test-Path $extensionsPath) {
            $allModPaths = @(Get-ChildItem -LiteralPath $extensionsPath -Directory | ForEach-Object { $_.FullName })
        }
        
        # Run intelligence analysis
        $intelligence = Get-UnidIntelligence -Files $files -AllModPaths $allModPaths
        
        # Create intelligence dialog
        $intelForm = [System.Windows.Forms.Form]::new()
        $intelForm.Text = 'UNID Intelligence Report'
        $intelForm.Size = [System.Drawing.Size]::new(1200, 800)
        $intelForm.StartPosition = 'CenterParent'
        $intelForm.BackColor = $bgDark
        $intelForm.ForeColor = $textWhite
        
        # Tab control for different views
        $intelTabs = [System.Windows.Forms.TabControl]::new()
        $intelTabs.Dock = 'Fill'
        $intelTabs.BackColor = $bgDark
        $intelForm.Controls.Add($intelTabs)
        
        # Tab 1: All UNIDs with References
        $tabAll = [System.Windows.Forms.TabPage]::new()
        $tabAll.Text = 'All UNIDs'
        $tabAll.BackColor = $bgDark
        $intelTabs.TabPages.Add($tabAll)
        
        $gridAll = [System.Windows.Forms.DataGridView]::new()
        $gridAll.Dock = 'Fill'
        $gridAll.BackgroundColor = $bgDark
        $gridAll.ForeColor = $textWhite
        $gridAll.DefaultCellStyle.BackColor = $bgDark
        $gridAll.DefaultCellStyle.ForeColor = $textWhite
        $gridAll.ColumnHeadersDefaultCellStyle.BackColor = $bgLight
        $gridAll.ColumnHeadersDefaultCellStyle.ForeColor = $textWhite
        $gridAll.ReadOnly = $true
        $gridAll.SelectionMode = 'FullRowSelect'
        $gridAll.Columns.Add('UNID', 'UNID') | Out-Null
        $gridAll.Columns.Add('Entity', 'Entity Name') | Out-Null
        $gridAll.Columns.Add('References', 'Refs') | Out-Null
        $gridAll.Columns.Add('Range', 'Range') | Out-Null
        $gridAll.Columns.Add('File', 'File') | Out-Null
        $tabAll.Controls.Add($gridAll)
        
        foreach ($unid in $intelligence.Unids.Keys | Sort-Object) {
            $info = $intelligence.Unids[$unid]
            $row = $gridAll.Rows.Add()
            $gridAll.Rows[$row].Cells['UNID'].Value = $unid
            $gridAll.Rows[$row].Cells['Entity'].Value = $info.EntityName
            $gridAll.Rows[$row].Cells['References'].Value = $info.ReferenceCount
            $gridAll.Rows[$row].Cells['Range'].Value = $info.Range
            $gridAll.Rows[$row].Cells['File'].Value = Split-Path -Leaf $info.DefinedIn
            
            if ($info.IsDangling) {
                $gridAll.Rows[$row].DefaultCellStyle.ForeColor = [System.Drawing.Color]::FromArgb(255, 200, 100)
            }
            
            $gridAll.Rows[$row].Tag = $info
        }
        
        # Tab 2: Dangling UNIDs
        $tabDangling = [System.Windows.Forms.TabPage]::new()
        $tabDangling.Text = 'Dangling UNIDs'
        $tabDangling.BackColor = $bgDark
        $intelTabs.TabPages.Add($tabDangling)
        
        $gridDangling = [System.Windows.Forms.DataGridView]::new()
        $gridDangling.Dock = 'Fill'
        $gridDangling.BackgroundColor = $bgDark
        $gridDangling.ForeColor = $textWhite
        $gridDangling.DefaultCellStyle.BackColor = $bgDark
        $gridDangling.DefaultCellStyle.ForeColor = [System.Drawing.Color]::FromArgb(255, 200, 100)
        $gridDangling.ColumnHeadersDefaultCellStyle.BackColor = $bgLight
        $gridDangling.ColumnHeadersDefaultCellStyle.ForeColor = $textWhite
        $gridDangling.ReadOnly = $true
        $gridDangling.SelectionMode = 'FullRowSelect'
        $gridDangling.Columns.Add('UNID', 'UNID') | Out-Null
        $gridDangling.Columns.Add('Entity', 'Entity Name') | Out-Null
        $gridDangling.Columns.Add('File', 'File') | Out-Null
        $gridDangling.Columns.Add('Line', 'Line') | Out-Null
        $tabDangling.Controls.Add($gridDangling)
        
        foreach ($dangling in $intelligence.DanglingUnids) {
            $row = $gridDangling.Rows.Add()
            $gridDangling.Rows[$row].Cells['UNID'].Value = $dangling.UNID
            $gridDangling.Rows[$row].Cells['Entity'].Value = $dangling.EntityName
            $gridDangling.Rows[$row].Cells['File'].Value = Split-Path -Leaf $dangling.File
            $gridDangling.Rows[$row].Cells['Line'].Value = $dangling.Line
            $gridDangling.Rows[$row].Tag = $dangling
        }
        
        # Tab 3: Override Conflicts
        if ($intelligence.OverrideConflicts.Count -gt 0) {
            $tabConflicts = [System.Windows.Forms.TabPage]::new()
            $tabConflicts.Text = "Override Conflicts ($($intelligence.OverrideConflicts.Count))"
            $tabConflicts.BackColor = $bgDark
            $intelTabs.TabPages.Add($tabConflicts)
            
            $gridConflicts = [System.Windows.Forms.DataGridView]::new()
            $gridConflicts.Dock = 'Fill'
            $gridConflicts.BackgroundColor = $bgDark
            $gridConflicts.ForeColor = $textWhite
            $gridConflicts.DefaultCellStyle.BackColor = $bgDark
            $gridConflicts.DefaultCellStyle.ForeColor = [System.Drawing.Color]::FromArgb(255, 100, 100)
            $gridConflicts.ColumnHeadersDefaultCellStyle.BackColor = $bgLight
            $gridConflicts.ColumnHeadersDefaultCellStyle.ForeColor = $textWhite
            $gridConflicts.ReadOnly = $true
            $gridConflicts.SelectionMode = 'FullRowSelect'
            $gridConflicts.Columns.Add('UNID', 'UNID') | Out-Null
            $gridConflicts.Columns.Add('Mods', 'Mods') | Out-Null
            $gridConflicts.Columns.Add('Count', 'Count') | Out-Null
            $tabConflicts.Controls.Add($gridConflicts)
            
            foreach ($conflict in $intelligence.OverrideConflicts) {
                $row = $gridConflicts.Rows.Add()
                $gridConflicts.Rows[$row].Cells['UNID'].Value = $conflict.UNID
                $gridConflicts.Rows[$row].Cells['Mods'].Value = ($conflict.Mods -join ', ')
                $gridConflicts.Rows[$row].Cells['Count'].Value = $conflict.ConflictCount
            }
        }
        
        # Tab 4: Unused Ranges
        $tabRanges = [System.Windows.Forms.TabPage]::new()
        $tabRanges.Text = 'Unused Ranges'
        $tabRanges.BackColor = $bgDark
        $intelTabs.TabPages.Add($tabRanges)
        
        $gridRanges = [System.Windows.Forms.DataGridView]::new()
        $gridRanges.Dock = 'Fill'
        $gridRanges.BackgroundColor = $bgDark
        $gridRanges.ForeColor = $textWhite
        $gridRanges.DefaultCellStyle.BackColor = $bgDark
        $gridRanges.DefaultCellStyle.ForeColor = $textWhite
        $gridRanges.ColumnHeadersDefaultCellStyle.BackColor = $bgLight
        $gridRanges.ColumnHeadersDefaultCellStyle.ForeColor = $textWhite
        $gridRanges.ReadOnly = $true
        $gridRanges.SelectionMode = 'FullRowSelect'
        $gridRanges.Columns.Add('Start', 'Start') | Out-Null
        $gridRanges.Columns.Add('End', 'End') | Out-Null
        $gridRanges.Columns.Add('Size', 'Size') | Out-Null
        $gridRanges.Columns.Add('Description', 'Description') | Out-Null
        $tabRanges.Controls.Add($gridRanges)
        
        foreach ($range in $intelligence.UnusedRanges) {
            $row = $gridRanges.Rows.Add()
            $gridRanges.Rows[$row].Cells['Start'].Value = $range.Start
            $gridRanges.Rows[$row].Cells['End'].Value = $range.End
            $gridRanges.Rows[$row].Cells['Size'].Value = $range.Size
            $gridRanges.Rows[$row].Cells['Description'].Value = $range.Description
        }
        
        # Double-click to show references
        $gridAll.Add_CellDoubleClick({
            $row = $gridAll.CurrentRow
            if ($row -and $row.Tag) {
                $info = $row.Tag
                $refText = [System.Text.StringBuilder]::new()
                [void]$refText.AppendLine("UNID: $($info.UNID)")
                [void]$refText.AppendLine("Entity: $($info.EntityName)")
                [void]$refText.AppendLine("References: $($info.ReferenceCount)")
                [void]$refText.AppendLine('')
                [void]$refText.AppendLine('Reference Locations:')
                [void]$refText.AppendLine('')
                
                foreach ($ref in $info.References) {
                    [void]$refText.AppendLine("$($ref.File):$($ref.Line)")
                    [void]$refText.AppendLine("  $($ref.Context)")
                    [void]$refText.AppendLine('')
                }
                
                $refForm = [System.Windows.Forms.Form]::new()
                $refForm.Text = "UNID References: $($info.UNID)"
                $refForm.Size = [System.Drawing.Size]::new(800, 600)
                $refForm.StartPosition = 'CenterParent'
                $refForm.BackColor = $bgDark
                $refForm.ForeColor = $textWhite
                
                $refTextbox = [System.Windows.Forms.RichTextBox]::new()
                $refTextbox.Dock = 'Fill'
                $refTextbox.BackColor = $bgDark
                $refTextbox.ForeColor = $textWhite
                $refTextbox.Font = [System.Drawing.Font]::new('Consolas', 9)
                $refTextbox.ReadOnly = $true
                $refTextbox.Text = $refText.ToString()
                $refForm.Controls.Add($refTextbox)
                
                $refForm.ShowDialog() | Out-Null
            }
        })
        
        $intelForm.ShowDialog() | Out-Null
    })
    
    $btnUnidScan.Add_Click({
        $gridUnid.Rows.Clear()
        $path = $txtUnidPath.Text
        if ([string]::IsNullOrWhiteSpace($path)) {
            $lblUnidStatus.Text = 'Please enter a path'
            return
        }
        
        if (-not (Test-Path $path)) {
            $lblUnidStatus.Text = 'Path not found'
            return
        }
        
        $lblUnidStatus.Text = 'Scanning...'
        $form.Refresh()
        
        # Load advanced features
        $advancedModule = Join-Path $PSScriptRoot 'TranscendenceModTools_Advanced.ps1'
        if (Test-Path $advancedModule) {
            try {
                . $advancedModule
            }
            catch { }
        }
        
        $files = @(Get-ChildItem -LiteralPath $path -Filter '*.xml' -Recurse | ForEach-Object { $_.FullName })
        
        # Pre-populate UNID registry from Extensions and Collection folders
        $allUnids = @{}
        $transcendenceRoot = Find-TranscendenceRoot -StartPath $PSScriptRoot
        if (-not $transcendenceRoot) {
            $rtbLog.AppendText("WARNING: Transcendence installation not detected.`n")
            $rtbLog.AppendText("  UNID scanning features require Extensions/Collection folders.`n")
            $rtbLog.AppendText("  Most other features (XML checking, error diagnosis) work without it.`n")
            $rtbLog.SelectionColor = $textYellow
            return
        }
        $extensionsPath = Join-Path $transcendenceRoot "Extensions"
        $collectionPath = Join-Path $transcendenceRoot "Collection"
        
        # Function to scan UNIDs from a folder
        function Get-UnidsFromFolder {
            param([string]$FolderPath)
            $unids = @{}
            if (Test-Path $FolderPath) {
                $xmlFiles = Get-ChildItem -LiteralPath $FolderPath -Filter '*.xml' -Recurse -ErrorAction SilentlyContinue
                foreach ($xmlFile in $xmlFiles) {
                    try {
                        $text = [System.IO.File]::ReadAllText($xmlFile.FullName, [System.Text.Encoding]::UTF8)
                        $unidDefPattern = '<!ENTITY\s+(\w+)\s+"(0x[0-9A-Fa-f]+)"'
                        $matches = [regex]::Matches($text, $unidDefPattern, 'IgnoreCase')
                        foreach ($m in $matches) {
                            $unidValue = $m.Groups[2].Value
                            if (-not $unids.ContainsKey($unidValue)) {
                                $unids[$unidValue] = $xmlFile.FullName
                            }
                        }
                    } catch { }
                }
            }
            return $unids
        }
        
        # Function to extract UNIDs from TDB file
        function Get-UnidsFromTdb {
            param([string]$TdbPath)
            $unids = @{}
            if (Test-Path $TdbPath) {
                try {
                    # Load TDB parser if available
                    $tdbModule = Join-Path $PSScriptRoot 'TranscendenceModTools_TDBParser.ps1'
                    if (Test-Path $tdbModule) {
                        . $tdbModule
                        $tdbPreview = Get-TdbPreview -Path $TdbPath
                        if ($tdbPreview -and $tdbPreview.Parsed -and $tdbPreview.Parsed.Unids) {
                            foreach ($unid in $tdbPreview.Parsed.Unids) {
                                if (-not $unids.ContainsKey($unid)) {
                                    $unids[$unid] = $TdbPath
                                }
                            }
                        }
                        elseif ($tdbPreview -and $tdbPreview.Extracted -and $tdbPreview.Extracted.Unids) {
                            foreach ($unid in $tdbPreview.Extracted.Unids) {
                                if (-not $unids.ContainsKey($unid)) {
                                    $unids[$unid] = $TdbPath
                                }
                            }
                        }
                    }
                } catch { }
            }
            return $unids
        }
        
        # Populate from Extensions
        $extUnids = Get-UnidsFromFolder -FolderPath $extensionsPath
        foreach ($unid in $extUnids.Keys) {
            $allUnids[$unid] = @($extUnids[$unid])
        }
        
        # Populate from Collection
        $collUnids = Get-UnidsFromFolder -FolderPath $collectionPath
        foreach ($unid in $collUnids.Keys) {
            if (-not $allUnids.ContainsKey($unid)) {
                $allUnids[$unid] = @($collUnids[$unid])
            } else {
                $allUnids[$unid] += $collUnids[$unid]
            }
        }
        
        # Populate from Transcendence.tdb in game root
        $transcendenceTdb = Join-Path $transcendenceRoot "Transcendence.tdb"
        $tdbUnids = Get-UnidsFromTdb -TdbPath $transcendenceTdb
        foreach ($unid in $tdbUnids.Keys) {
            if (-not $allUnids.ContainsKey($unid)) {
                $allUnids[$unid] = @($tdbUnids[$unid])
            } else {
                $allUnids[$unid] += $tdbUnids[$unid]
            }
        }
        
        $unidList = @()
        
        foreach ($f in $files) {
            $text = [System.IO.File]::ReadAllText($f, [System.Text.Encoding]::UTF8)
            
            # Extract UNID definitions
            $unidPattern = '<!ENTITY\s+(\w+)\s+"(0x[0-9A-Fa-f]+)"'
            $matches = [regex]::Matches($text, $unidPattern, 'IgnoreCase')
            foreach ($m in $matches) {
                $entityName = $m.Groups[1].Value
                $unidValue = $m.Groups[2].Value
                
                # Determine type from entity name
                $type = 'Unknown'
                if ($entityName.StartsWith('it')) { $type = 'Item' }
                elseif ($entityName.StartsWith('sc')) { $type = 'Ship' }
                elseif ($entityName.StartsWith('st')) { $type = 'Station' }
                elseif ($entityName.StartsWith('rs')) { $type = 'Image' }
                elseif ($entityName.StartsWith('sv')) { $type = 'Sovereign' }
                elseif ($entityName.StartsWith('ds')) { $type = 'Dockscreen' }
                elseif ($entityName.StartsWith('unid')) { $type = 'Extension' }
                
                $unidList += [PSCustomObject]@{
                    UNID = $unidValue
                    Entity = $entityName
                    Type = $type
                    File = $f
                }
                
                if ($allUnids.ContainsKey($unidValue)) {
                    $allUnids[$unidValue] += $f
                }
                else {
                    $allUnids[$unidValue] = @($f)
                }
            }
        }
        
        # Load UNID intelligence for reference counts
        $unidModule = Join-Path $PSScriptRoot 'TranscendenceModTools_UNIDIntelligence.ps1'
        $intelligence = $null
        if (Test-Path $unidModule) {
            try {
                . $unidModule
                $intelligence = Get-UnidIntelligence -Files $files
            }
            catch { }
        }
        
        # Add to grid
        foreach ($u in $unidList | Sort-Object UNID) {
            $refCount = 0
            $range = 'Unknown'
            if ($intelligence -and $intelligence.Unids.ContainsKey($u.UNID)) {
                $refCount = $intelligence.Unids[$u.UNID].ReferenceCount
                $range = $intelligence.Unids[$u.UNID].Range
            }
            
            $rowIndex = $gridUnid.Rows.Add($u.UNID, $u.Entity, $refCount, $range, $u.File)
            
            # Highlight duplicates (check if it's an array = conflict)
            $unidEntry = $allUnids[$u.UNID]
            $isConflict = $false
            if ($unidEntry -is [Array]) {
                $isConflict = $true
            }
            elseif ($unidEntry -is [PSCustomObject] -and $u.File -like "*Extensions*" -and $unidEntry.Priority -lt 3) {
                # Extension UNID conflicts with higher-priority source
                $isConflict = $true
            }
            
            if ($isConflict) {
                $gridUnid.Rows[$rowIndex].DefaultCellStyle.ForeColor = $accentRed
            }
            # Highlight dangling UNIDs
            elseif ($refCount -eq 0) {
                $gridUnid.Rows[$rowIndex].DefaultCellStyle.ForeColor = [System.Drawing.Color]::FromArgb(255, 200, 100)
            }
        }
        
        # Count conflicts (only lower-priority conflicts with higher-priority sources)
        $duplicateCount = @($unidList | Where-Object {
            $entry = $allUnids[$_.UNID]
            if ($entry -is [Array]) { return $true }
            if ($entry -is [PSCustomObject] -and $_.File -like "*Extensions*" -and $entry.Priority -lt 3) { return $true }
            return $false
        }).Count
        $danglingCount = if ($intelligence) { $intelligence.DanglingUnids.Count } else { 0 }
        $lblUnidStatus.Text = "Found $($unidList.Count) UNID(s), $duplicateCount duplicate(s), $danglingCount dangling"
    })
    
    $btnUnidGenerate.Add_Click({
        # Generate a new UNID
        $baseUnid = 0xE1270000
        $random = Get-Random -Minimum 0x0000 -Maximum 0xFFFF
        $newUnid = "0x{0:X8}" -f ($baseUnid + $random)
        
        [System.Windows.Forms.MessageBox]::Show(
            "Generated UNID:`n$newUnid`n`nCopy this to your clipboard?",
            'Generated UNID',
            'YesNo',
            'Question'
        ) | Out-Null
        
        Set-Clipboard -Value $newUnid
    })
    
    # Cross-Mod Compatibility handlers
    $btnCompatBrowse.Add_Click({
        $folderDialog = [System.Windows.Forms.FolderBrowserDialog]::new()
        $folderDialog.Description = 'Select Extensions folder'
        if ($folderDialog.ShowDialog() -eq 'OK') {
            $txtCompatPath.Text = $folderDialog.SelectedPath
        }
    })
    
    $btnCompatScan.Add_Click({
        $extensionsPath = $txtCompatPath.Text
        if ([string]::IsNullOrWhiteSpace($extensionsPath)) {
            $txtCompatReport.Text = 'Please enter Extensions folder path'
            return
        }
        
        if (-not (Test-Path $extensionsPath)) {
            $txtCompatReport.Text = 'Path not found'
            return
        }
        
        $txtCompatReport.Text = 'Scanning all mods for compatibility issues...'
        $form.Refresh()
        
        # Load advanced features
        $advancedModule = Join-Path $PSScriptRoot 'TranscendenceModTools_Advanced.ps1'
        if (Test-Path $advancedModule) {
            try {
                . $advancedModule
            }
            catch { }
        }
        
        # Get all mod folders
        $modFolders = @(Get-ChildItem -LiteralPath $extensionsPath -Directory | Where-Object { 
            $_.GetFiles('*.xml', 'TopDirectoryOnly').Count -gt 0 
        })
        
        # Pre-load game/DLC UNIDs for priority checking
        $gameUnids = @{}
        $transcendenceRoot = Find-TranscendenceRoot -StartPath $PSScriptRoot
        if (-not $transcendenceRoot) {
            $txtCompatReport.Text = "Transcendence installation not detected.`n`nCompatibility checking requires access to Extensions/Collection folders.`n`nMost other features work without Transcendence."
            return
        }
        $collectionPath = Join-Path $transcendenceRoot "Collection"
        $transcendenceTdb = Join-Path $transcendenceRoot "Transcendence.tdb"
        
        # Official DLC TDB files (have priority 1, same as game)
        $officialDlcTdbs = @(
            'CorporateCommand.tdb',
            'CorporateHierarchyVol01.tdb',
            'CorporateHierarchyVol1UNIDs.tdb',
            'DebugPart1.tdb',
            'EternityPort.tdb',
            'StarsOfThePilgrimHD.tdb',
            'StarsOfThePilgrimSoundtrack.tdb'
        )
        
        function Test-IsOfficialDlcTdb {
            param([string]$FilePath)
            $fileName = Split-Path -Leaf $FilePath
            return $officialDlcTdbs -contains $fileName
        }
        
        # Load TDB parser if available
        $tdbModule = Join-Path $PSScriptRoot 'TranscendenceModTools_TDBParser.ps1'
        if (Test-Path $tdbModule) {
            try {
                . $tdbModule
                
                # Load from Transcendence.tdb (Priority 1)
                if (Test-Path $transcendenceTdb) {
                    $tdbUnids = Get-UnidsFromTdb -TdbPath $transcendenceTdb
                    foreach ($unid in $tdbUnids.Keys) {
                        $gameUnids[$unid] = [PSCustomObject]@{
                            Source = 'Game (Transcendence.tdb)'
                            Priority = 1
                            File = $transcendenceTdb
                            Range = 'Game/DLC (0x0000-0x9FFF)'
                        }
                    }
                }
                
                # Load from Collection TDBs
                # Official DLC TDBs get Priority 1, third-party TDBs get Priority 5
                if (Test-Path $collectionPath) {
                    $tdbFiles = Get-ChildItem -LiteralPath $collectionPath -Filter '*.tdb' -Recurse -ErrorAction SilentlyContinue
                    foreach ($tdbFile in $tdbFiles) {
                        $isOfficialDlc = Test-IsOfficialDlcTdb -FilePath $tdbFile.FullName
                        $tdbUnids = Get-UnidsFromTdb -TdbPath $tdbFile.FullName
                        foreach ($unid in $tdbUnids.Keys) {
                            if (-not $gameUnids.ContainsKey($unid)) {
                                if ($isOfficialDlc) {
                                    $gameUnids[$unid] = [PSCustomObject]@{
                                        Source = "Official DLC ($($tdbFile.Name))"
                                        Priority = 1
                                        File = $tdbFile.FullName
                                        Range = 'Official DLC'
                                    }
                                }
                                else {
                                    # Third-party TDBs - only track if they conflict (priority 5)
                                    # We'll check these during conflict detection
                                }
                            }
                        }
                    }
                }
            } catch { }
        }
        
        $allUnids = @{}
        $modUnids = @{}
        $conflicts = @()
        $gameConflicts = @()
        
        foreach ($modFolder in $modFolders) {
            $modName = $modFolder.Name
            $modUnids[$modName] = @{}
            
            $files = @(Get-ChildItem -LiteralPath $modFolder.FullName -Filter '*.xml' -Recurse)
            foreach ($f in $files) {
                $text = [System.IO.File]::ReadAllText($f.FullName, [System.Text.Encoding]::UTF8)
                $unidPattern = '<!ENTITY\s+(\w+)\s+"(0x[0-9A-Fa-f]+)"'
                $matches = [regex]::Matches($text, $unidPattern, 'IgnoreCase')
                
                foreach ($m in $matches) {
                    $unidValue = $m.Groups[2].Value
                    $entityName = $m.Groups[1].Value
                    
                    # Check for conflict with game/DLC (higher priority)
                    if ($gameUnids.ContainsKey($unidValue)) {
                        $gameConflicts += [PSCustomObject]@{
                            UNID = $unidValue
                            Entity = $entityName
                            Mod = $modName
                            ModFile = $f.FullName
                            GameSource = $gameUnids[$unidValue]
                        }
                    }
                    
                    # Track mod-to-mod conflicts
                    if (-not $allUnids.ContainsKey($unidValue)) {
                        $allUnids[$unidValue] = @()
                    }
                    $allUnids[$unidValue] += [PSCustomObject]@{
                        Mod = $modName
                        Entity = $entityName
                        File = $f.FullName
                    }
                    
                    $modUnids[$modName][$unidValue] = $entityName
                }
            }
        }
        
        # Find mod-to-mod conflicts
        foreach ($unid in $allUnids.Keys) {
            if ($allUnids[$unid].Count -gt 1) {
                $conflicts += [PSCustomObject]@{
                    UNID = $unid
                    Mods = $allUnids[$unid]
                }
            }
        }
        
        # Generate report
        $output = [System.Text.StringBuilder]::new()
        [void]$output.AppendLine('═══════════════════════════════════════════════════════════')
        [void]$output.AppendLine('              CROSS-MOD COMPATIBILITY REPORT')
        [void]$output.AppendLine('═══════════════════════════════════════════════════════════')
        [void]$output.AppendLine('')
        [void]$output.AppendLine("Scanned $($modFolders.Count) mod(s)")
        [void]$output.AppendLine("Total UNIDs found: $($allUnids.Count)")
        [void]$output.AppendLine("Mod-to-mod conflicts: $($conflicts.Count)")
        [void]$output.AppendLine("Game/DLC conflicts: $($gameConflicts.Count)")
        [void]$output.AppendLine('')
        
        # Game/DLC conflicts (highest priority - must be fixed)
        if ($gameConflicts.Count -gt 0) {
            [void]$output.AppendLine('⚠ GAME/DLC CONFLICTS (HIGH PRIORITY - MUST FIX):')
            [void]$output.AppendLine('   Game and DLC UNIDs take priority. Mod UNIDs must be changed.')
            [void]$output.AppendLine('   Reference: https://wiki.kronosaur.com/doku.php/modding/unid_database')
            [void]$output.AppendLine('')
            foreach ($conflict in $gameConflicts) {
                $gameRange = if ($conflict.GameSource.Range) { " ($($conflict.GameSource.Range))" } else { "" }
                [void]$output.AppendLine("UNID: $($conflict.UNID)")
                [void]$output.AppendLine("  Game/DLC: $($conflict.GameSource.Source)$gameRange (Priority $($conflict.GameSource.Priority))")
                [void]$output.AppendLine("  Conflict: $($conflict.Mod) - $($conflict.Entity)")
                [void]$output.AppendLine("    File: $($conflict.ModFile)")
                [void]$output.AppendLine('')
            }
        }
        
        # Mod-to-mod conflicts
        if ($conflicts.Count -gt 0) {
            [void]$output.AppendLine('MOD-TO-MOD CONFLICTS:')
            [void]$output.AppendLine('')
            foreach ($conflict in $conflicts) {
                [void]$output.AppendLine("UNID: $($conflict.UNID)")
                foreach ($mod in $conflict.Mods) {
                    [void]$output.AppendLine("  - $($mod.Mod): $($mod.Entity) ($($mod.File))")
                }
                [void]$output.AppendLine('')
            }
        }
        
        if ($conflicts.Count -eq 0 -and $gameConflicts.Count -eq 0) {
            [void]$output.AppendLine('✓ No UNID conflicts found!')
        }
        
        [void]$output.AppendLine('')
        [void]$output.AppendLine('═══════════════════════════════════════════════════════════')
        
        $txtCompatReport.Text = $output.ToString()
    })
    
    # Dependency Graph handlers
    $btnDepBrowse.Add_Click({
        $folderDialog = [System.Windows.Forms.FolderBrowserDialog]::new()
        $folderDialog.Description = 'Select mod folder'
        if ($folderDialog.ShowDialog() -eq 'OK') {
            $txtDepPath.Text = $folderDialog.SelectedPath
        }
    })
    
    $btnDepGenerate.Add_Click({
        $modPath = $txtDepPath.Text
        if ([string]::IsNullOrWhiteSpace($modPath)) {
            $txtDepGraph.Text = 'Please enter a mod path'
            return
        }
        
        if (-not (Test-Path $modPath)) {
            $txtDepGraph.Text = 'Path not found'
            return
        }
        
        $txtDepGraph.Text = 'Analyzing dependencies...'
        $form.Refresh()
        
        # Load dependency graph module
        $depModule = Join-Path $PSScriptRoot 'TranscendenceModTools_DependencyGraph.ps1'
        if (Test-Path $depModule) {
            try {
                . $depModule
            }
            catch {
                $txtDepGraph.Text = "Failed to load dependency graph module: $_"
                return
            }
        }
        else {
            $txtDepGraph.Text = 'Dependency graph module not found'
            return
        }
        
        # Get all XML files
        $files = @(Get-ChildItem -LiteralPath $modPath -Filter '*.xml' -Recurse | ForEach-Object { $_.FullName })
        
        if ($files.Count -eq 0) {
            $txtDepGraph.Text = 'No XML files found'
            return
        }
        
        # Generate dependency graph
        $graph = Get-DependencyGraph -Files $files
        $formatted = Format-DependencyGraph -Graph $graph
        $summary = Get-DependencyGraphSummary -Graph $graph
        
        # Add summary at top
        $fullOutput = [System.Text.StringBuilder]::new()
        [void]$fullOutput.AppendLine('═══════════════════════════════════════════════════════════')
        [void]$fullOutput.AppendLine('                    GRAPH SUMMARY')
        [void]$fullOutput.AppendLine('═══════════════════════════════════════════════════════════')
        [void]$fullOutput.AppendLine('')
        [void]$fullOutput.AppendLine("Total Nodes: $($summary.TotalNodes)")
        [void]$fullOutput.AppendLine("Total Relationships: $($summary.TotalRelationships)")
        [void]$fullOutput.AppendLine('')
        [void]$fullOutput.AppendLine('Relationship Types:')
        foreach ($relType in $summary.RelationshipTypes.Keys | Sort-Object) {
            [void]$fullOutput.AppendLine("  $relType`: $($summary.RelationshipTypes[$relType])")
        }
        [void]$fullOutput.AppendLine('')
        [void]$fullOutput.AppendLine($formatted)
        
        $txtDepGraph.Text = $fullOutput.ToString()
    })
    
    $btnDepExport.Add_Click({
        if ([string]::IsNullOrWhiteSpace($txtDepGraph.Text) -or $txtDepGraph.Text -match 'Please enter|not found|Analyzing|No XML') {
            [System.Windows.Forms.MessageBox]::Show('Please generate the graph first.', 'Export', 'OK', 'Information')
            return
        }
        
        $saveDialog = [System.Windows.Forms.SaveFileDialog]::new()
        $saveDialog.Filter = 'Text files (*.txt)|*.txt|All files (*.*)|*.*'
        $saveDialog.Title = 'Export Dependency Graph'
        $saveDialog.FileName = 'DependencyGraph.txt'
        
        if ($saveDialog.ShowDialog() -eq 'OK') {
            [System.IO.File]::WriteAllText($saveDialog.FileName, $txtDepGraph.Text, [System.Text.Encoding]::UTF8)
            [System.Windows.Forms.MessageBox]::Show("Graph exported to:`n$($saveDialog.FileName)", 'Export Complete', 'OK', 'Information')
        }
    })
    
    # Diff Mode handlers
    $btnDiffOldBrowse.Add_Click({
        $folderDialog = [System.Windows.Forms.FolderBrowserDialog]::new()
        $folderDialog.Description = 'Select old version folder'
        if ($folderDialog.ShowDialog() -eq 'OK') {
            $txtDiffOld.Text = $folderDialog.SelectedPath
        }
    })
    
    $btnDiffNewBrowse.Add_Click({
        $folderDialog = [System.Windows.Forms.FolderBrowserDialog]::new()
        $folderDialog.Description = 'Select new version folder'
        if ($folderDialog.ShowDialog() -eq 'OK') {
            $txtDiffNew.Text = $folderDialog.SelectedPath
        }
    })
    
    $btnDiffCompare.Add_Click({
        $oldPath = $txtDiffOld.Text
        $newPath = $txtDiffNew.Text
        
        if ([string]::IsNullOrWhiteSpace($oldPath) -or [string]::IsNullOrWhiteSpace($newPath)) {
            $txtDiffReport.Text = 'Please select both old and new version paths'
            return
        }
        
        if (-not (Test-Path $oldPath)) {
            $txtDiffReport.Text = 'Old version path not found'
            return
        }
        
        if (-not (Test-Path $newPath)) {
            $txtDiffReport.Text = 'New version path not found'
            return
        }
        
        $txtDiffReport.Text = 'Comparing versions...'
        $form.Refresh()
        
        # Load diff mode module
        $diffModule = Join-Path $PSScriptRoot 'TranscendenceModTools_DiffMode.ps1'
        if (Test-Path $diffModule) {
            try {
                . $diffModule
            }
            catch {
                $txtDiffReport.Text = "Failed to load diff mode module: $_"
                return
            }
        }
        else {
            $txtDiffReport.Text = 'Diff mode module not found'
            return
        }
        
        # Get all XML files from both versions
        $oldFiles = @(Get-ChildItem -LiteralPath $oldPath -Filter '*.xml' -Recurse | ForEach-Object { $_.FullName })
        $newFiles = @(Get-ChildItem -LiteralPath $newPath -Filter '*.xml' -Recurse | ForEach-Object { $_.FullName })
        
        if ($oldFiles.Count -eq 0) {
            $txtDiffReport.Text = 'No XML files found in old version'
            return
        }
        
        if ($newFiles.Count -eq 0) {
            $txtDiffReport.Text = 'No XML files found in new version'
            return
        }
        
        # Store events for comparison
        $oldEvents = Get-AllEvents -Files $oldFiles
        $newEvents = Get-AllEvents -Files $newFiles
        
        # Generate diff
        $diff = Get-ModDiff -OldFiles $oldFiles -NewFiles $newFiles -OldEvents $oldEvents -NewEvents $newEvents
        $formatted = Format-DiffReport -Diff $diff
        
        $txtDiffReport.Text = $formatted
    })
    
    # Live Preview handlers
    $script:livePreviewFiles = @()
    $script:livePreviewTypes = @()
    
    $btnLiveBrowse.Add_Click({
        $folderDialog = [System.Windows.Forms.FolderBrowserDialog]::new()
        $folderDialog.Description = 'Select mod folder'
        if ($folderDialog.ShowDialog() -eq 'OK') {
            $txtLivePath.Text = $folderDialog.SelectedPath
        }
    })
    
    $btnLiveLoad.Add_Click({
        $modPath = $txtLivePath.Text
        if ([string]::IsNullOrWhiteSpace($modPath)) {
            $txtLivePreview.Text = 'Please enter a mod path'
            return
        }
        
        if (-not (Test-Path $modPath)) {
            $txtLivePreview.Text = 'Path not found'
            return
        }
        
        $txtLivePreview.Text = 'Loading types...'
        $form.Refresh()
        
        # Load live preview module
        $liveModule = Join-Path $PSScriptRoot 'TranscendenceModTools_LivePreview.ps1'
        if (Test-Path $liveModule) {
            try {
                . $liveModule
            }
            catch {
                $txtLivePreview.Text = "Failed to load live preview module: $_"
                return
            }
        }
        else {
            $txtLivePreview.Text = 'Live preview module not found'
            return
        }
        
        # Get all XML files
        $files = @(Get-ChildItem -LiteralPath $modPath -Filter '*.xml' -Recurse | ForEach-Object { $_.FullName })
        
        if ($files.Count -eq 0) {
            $txtLivePreview.Text = 'No XML files found'
            return
        }
        
        $script:livePreviewFiles = $files
        
        # Get all types
        $types = Get-AllTypes -Files $files
        $script:livePreviewTypes = $types
        
        # Populate combo box
        $cmbLiveType.Items.Clear()
        foreach ($type in ($types | Sort-Object Type, Name)) {
            $display = "$($type.Name) [$($type.Type)]"
            $cmbLiveType.Items.Add($type) | Out-Null
        }
        
        if ($cmbLiveType.Items.Count -gt 0) {
            $cmbLiveType.SelectedIndex = 0
        }
        
        $txtLivePreview.Text = "Loaded $($types.Count) types. Select a type and click Preview."
    })
    
    $btnLivePreview.Add_Click({
        if ($cmbLiveType.SelectedItem -eq $null) {
            $txtLivePreview.Text = 'Please select a type'
            return
        }
        
        if ($script:livePreviewFiles.Count -eq 0) {
            $txtLivePreview.Text = 'Please load types first'
            return
        }
        
        $selectedType = $cmbLiveType.SelectedItem
        $unid = $selectedType.UNID
        
        $txtLivePreview.Text = 'Generating preview...'
        $form.Refresh()
        
        # Load live preview module if not already loaded
        $liveModule = Join-Path $PSScriptRoot 'TranscendenceModTools_LivePreview.ps1'
        if (Test-Path $liveModule) {
            try {
                . $liveModule
            }
            catch {
                # Already loaded, continue
            }
        }
        
        # Generate preview
        $preview = Get-LivePreview -Unid $unid -Files $script:livePreviewFiles
        $formatted = Format-LivePreview -Preview $preview
        
        $txtLivePreview.Text = $formatted
    })
    
    # Semantic Validation handlers
    $btnSemBrowse.Add_Click({
        $folderDialog = [System.Windows.Forms.FolderBrowserDialog]::new()
        $folderDialog.Description = 'Select mod folder'
        if ($folderDialog.ShowDialog() -eq 'OK') {
            $txtSemPath.Text = $folderDialog.SelectedPath
        }
    })
    
    $btnSemValidate.Add_Click({
        $modPath = $txtSemPath.Text
        if ([string]::IsNullOrWhiteSpace($modPath)) {
            $gridSemantic.Rows.Clear()
            return
        }
        
        if (-not (Test-Path $modPath)) {
            $gridSemantic.Rows.Clear()
            return
        }
        
        # Load semantic module
        $semModule = Join-Path $PSScriptRoot 'TranscendenceModTools_Semantic.ps1'
        if (Test-Path $semModule) {
            try {
                . $semModule
            }
            catch {
                [System.Windows.Forms.MessageBox]::Show("Failed to load semantic module: $_", 'Error', 'OK', 'Error')
                return
            }
        }
        
        # Get all XML files
        $files = @(Get-ChildItem -LiteralPath $modPath -Filter '*.xml' -Recurse | ForEach-Object { $_.FullName })
        
        if ($files.Count -eq 0) {
            $gridSemantic.Rows.Clear()
            return
        }
        
        # Run semantic validation
        $issues = Get-SemanticIssues -Files $files
        
        # Also check for override conflicts
        $tree = Get-InheritanceTree -Files $files
        $overrideConflicts = Get-OverrideConflicts -InheritanceTree $tree -Files $files
        $issues += $overrideConflicts
        
        # Also run TML static analysis
        $tmlModule = Join-Path $PSScriptRoot 'TranscendenceModTools_TMLStaticAnalysis.ps1'
        if (Test-Path $tmlModule) {
            try {
                . $tmlModule
                $tmlIssues = Get-TMLStaticAnalysis -Files $files
                $issues += $tmlIssues
            }
            catch { }
        }
        
        $gridSemantic.Rows.Clear()
        foreach ($issue in $issues) {
            $row = $gridSemantic.Rows.Add()
            $gridSemantic.Rows[$row].Cells['File'].Value = Split-Path -Leaf $issue.File
            $gridSemantic.Rows[$row].Cells['Line'].Value = $issue.Line
            $gridSemantic.Rows[$row].Cells['Severity'].Value = $issue.Severity
            $gridSemantic.Rows[$row].Cells['Code'].Value = $issue.Code
            $gridSemantic.Rows[$row].Cells['Message'].Value = $issue.Message
            
            # Color code by severity
            if ($issue.Severity -eq 'Error') {
                $gridSemantic.Rows[$row].DefaultCellStyle.ForeColor = [System.Drawing.Color]::FromArgb(255, 100, 100)
            }
            elseif ($issue.Severity -eq 'Warning') {
                $gridSemantic.Rows[$row].DefaultCellStyle.ForeColor = [System.Drawing.Color]::FromArgb(255, 200, 100)
            }
            
            # Store full path for double-click
            $gridSemantic.Rows[$row].Tag = $issue
        }
    })
    
    $btnSemInheritance.Add_Click({
        $modPath = $txtSemPath.Text
        if ([string]::IsNullOrWhiteSpace($modPath)) {
            return
        }
        
        if (-not (Test-Path $modPath)) {
            return
        }
        
        # Load semantic module
        $semModule = Join-Path $PSScriptRoot 'TranscendenceModTools_Semantic.ps1'
        if (Test-Path $semModule) {
            try {
                . $semModule
            }
            catch {
                [System.Windows.Forms.MessageBox]::Show("Failed to load semantic module: $_", 'Error', 'OK', 'Error')
                return
            }
        }
        
        # Get all XML files
        $files = @(Get-ChildItem -LiteralPath $modPath -Filter '*.xml' -Recurse | ForEach-Object { $_.FullName })
        
        if ($files.Count -eq 0) {
            return
        }
        
        # Build inheritance tree
        $tree = Get-InheritanceTree -Files $files
        
        # Create dialog with type selector and resolved view
        $treeForm = [System.Windows.Forms.Form]::new()
        $treeForm.Text = 'Inheritance & Override Resolution'
        $treeForm.Size = [System.Drawing.Size]::new(1000, 700)
        $treeForm.StartPosition = 'CenterParent'
        $treeForm.BackColor = $bgDark
        $treeForm.ForeColor = $textWhite
        
        # Type selector
        $lblTypeSelect = [System.Windows.Forms.Label]::new()
        $lblTypeSelect.Text = 'Select Type:'
        $lblTypeSelect.Location = [System.Drawing.Point]::new(10, 10)
        $lblTypeSelect.AutoSize = $true
        $lblTypeSelect.ForeColor = $textWhite
        $treeForm.Controls.Add($lblTypeSelect)
        
        $comboType = [System.Windows.Forms.ComboBox]::new()
        $comboType.Location = [System.Drawing.Point]::new(80, 8)
        $comboType.Size = [System.Drawing.Size]::new(300, 25)
        $comboType.DropDownStyle = 'DropDownList'
        $comboType.BackColor = $bgLight
        $comboType.ForeColor = $textWhite
        $treeForm.Controls.Add($comboType)
        
        # Store UNID mapping
        $typeUnidMap = @{}
        
        # Populate combo
        foreach ($unid in $tree.Keys | Sort-Object) {
            $node = $tree[$unid]
            $type = $node.Type
            $display = "$($type.Name) ($($type.Type))"
            $comboType.Items.Add($display) | Out-Null
            $typeUnidMap[$display] = $unid
        }
        
        if ($comboType.Items.Count -gt 0) {
            $comboType.SelectedIndex = 0
        }
        
        # Resolved type display
        $treeText = [System.Windows.Forms.RichTextBox]::new()
        $treeText.Location = [System.Drawing.Point]::new(10, 40)
        $treeText.Size = [System.Drawing.Size]::new(970, 620)
        $treeText.BackColor = $bgDark
        $treeText.ForeColor = $textWhite
        $treeText.Font = [System.Drawing.Font]::new('Consolas', 9)
        $treeText.ReadOnly = $true
        $treeForm.Controls.Add($treeText)
        
        function Update-ResolvedView {
            $selected = $comboType.SelectedItem
            if (-not $selected) { return }
            
            $unid = $typeUnidMap[$selected]
            $resolved = Get-ResolvedType -Unid $unid -InheritanceTree $tree -TypeRegistry @{} -Files $files
            
            if (-not $resolved) {
                $treeText.Text = 'Type not found or has no inheritance'
                return
            }
            
            $output = [System.Text.StringBuilder]::new()
            [void]$output.AppendLine('═══════════════════════════════════════════════════════════')
            [void]$output.AppendLine('              FULLY RESOLVED TYPE')
            [void]$output.AppendLine('═══════════════════════════════════════════════════════════')
            [void]$output.AppendLine('')
            [void]$output.AppendLine("Type: $($resolved.Name) ($($resolved.Type))")
            [void]$output.AppendLine("UNID: $($resolved.UNID)")
            [void]$output.AppendLine("File: $(Split-Path -Leaf $resolved.File)")
            [void]$output.AppendLine('')
            
            if ($resolved.InheritChain.Count -gt 0) {
                [void]$output.AppendLine('Inheritance Chain:')
                $chain = @($resolved.Name)
                foreach ($parentUnid in $resolved.InheritChain) {
                    if ($tree.ContainsKey($parentUnid)) {
                        $chain += $tree[$parentUnid].Type.Name
                    }
                }
                [void]$output.AppendLine("  $($chain -join ' → ')")
                [void]$output.AppendLine('')
            }
            
            [void]$output.AppendLine('═══════════════════════════════════════════════════════════')
            [void]$output.AppendLine('                    ATTRIBUTES')
            [void]$output.AppendLine('═══════════════════════════════════════════════════════════')
            [void]$output.AppendLine('')
            
            foreach ($attr in $resolved.Attributes.Keys | Sort-Object) {
                $value = $resolved.Attributes[$attr]
                $source = $resolved.AttributeSources[$attr]
                [void]$output.AppendLine("$attr = `"$value`"")
                [void]$output.AppendLine("  Source: $source")
                [void]$output.AppendLine('')
            }
            
            if ($resolved.Conflicts.Count -gt 0) {
                [void]$output.AppendLine('═══════════════════════════════════════════════════════════')
                [void]$output.AppendLine('                    OVERRIDE CONFLICTS')
                [void]$output.AppendLine('═══════════════════════════════════════════════════════════')
                [void]$output.AppendLine('')
                
                foreach ($conflict in $resolved.Conflicts) {
                    [void]$output.AppendLine("⚠ Attribute: $($conflict.Attribute)")
                    [void]$output.AppendLine("  Parent value: $($conflict.ParentValue)")
                    [void]$output.AppendLine("  Child value:  $($conflict.ChildValue)")
                    [void]$output.AppendLine("  Source: $($conflict.Source)")
                    [void]$output.AppendLine('')
                }
            }
            
            if ($resolved.Events.Count -gt 0) {
                [void]$output.AppendLine('═══════════════════════════════════════════════════════════')
                [void]$output.AppendLine('                    EVENTS')
                [void]$output.AppendLine('═══════════════════════════════════════════════════════════')
                [void]$output.AppendLine('')
                
                foreach ($event in $resolved.Events | Sort-Object) {
                    $source = $resolved.EventSources[$event]
                    [void]$output.AppendLine("$event")
                    [void]$output.AppendLine("  Source: $source")
                    [void]$output.AppendLine('')
                }
            }
            
            $treeText.Text = $output.ToString()
        }
        
        $comboType.Add_SelectedIndexChanged({ Update-ResolvedView })
        Update-ResolvedView
        
        $treeForm.ShowDialog() | Out-Null
    })
    
    $btnSemEvents.Add_Click({
        $modPath = $txtSemPath.Text
        if ([string]::IsNullOrWhiteSpace($modPath)) {
            return
        }
        
        if (-not (Test-Path $modPath)) {
            return
        }
        
        # Load semantic module
        $semModule = Join-Path $PSScriptRoot 'TranscendenceModTools_Semantic.ps1'
        if (Test-Path $semModule) {
            try {
                . $semModule
            }
            catch {
                [System.Windows.Forms.MessageBox]::Show("Failed to load semantic module: $_", 'Error', 'OK', 'Error')
                return
            }
        }
        
        # Get all XML files
        $files = @(Get-ChildItem -LiteralPath $modPath -Filter '*.xml' -Recurse | ForEach-Object { $_.FullName })
        
        if ($files.Count -eq 0) {
            return
        }
        
        # Build event flow
        $eventFlow = Get-EventFlow -Files $files
        $report = Get-EventFlowReport -EventFlow $eventFlow
        
        # Create dialog
        $eventForm = [System.Windows.Forms.Form]::new()
        $eventForm.Text = 'Event Flow Analyzer'
        $eventForm.Size = [System.Drawing.Size]::new(1000, 700)
        $eventForm.StartPosition = 'CenterParent'
        $eventForm.BackColor = $bgDark
        $eventForm.ForeColor = $textWhite
        
        # Filter controls
        $lblFilter = [System.Windows.Forms.Label]::new()
        $lblFilter.Text = 'Filter:'
        $lblFilter.Location = [System.Drawing.Point]::new(10, 10)
        $lblFilter.AutoSize = $true
        $lblFilter.ForeColor = $textWhite
        $eventForm.Controls.Add($lblFilter)
        
        $comboFilter = [System.Windows.Forms.ComboBox]::new()
        $comboFilter.Location = [System.Drawing.Point]::new(60, 8)
        $comboFilter.Size = [System.Drawing.Size]::new(200, 25)
        $comboFilter.DropDownStyle = 'DropDownList'
        $comboFilter.BackColor = $bgLight
        $comboFilter.ForeColor = $textWhite
        $comboFilter.Items.AddRange(@('All', 'Implemented', 'Inherited', 'Duplicate', 'Unused', 'Summary'))
        $comboFilter.SelectedIndex = 0
        $eventForm.Controls.Add($comboFilter)
        
        # Type selector
        $lblType = [System.Windows.Forms.Label]::new()
        $lblType.Text = 'Type:'
        $lblType.Location = [System.Drawing.Point]::new(270, 10)
        $lblType.AutoSize = $true
        $lblType.ForeColor = $textWhite
        $eventForm.Controls.Add($lblType)
        
        $comboType = [System.Windows.Forms.ComboBox]::new()
        $comboType.Location = [System.Drawing.Point]::new(310, 8)
        $comboType.Size = [System.Drawing.Size]::new(300, 25)
        $comboType.DropDownStyle = 'DropDownList'
        $comboType.BackColor = $bgLight
        $comboType.ForeColor = $textWhite
        $comboType.Items.Add('All Types')
        foreach ($unid in $eventFlow.Keys | Sort-Object) {
            $comboType.Items.Add($eventFlow[$unid].Name) | Out-Null
        }
        $comboType.SelectedIndex = 0
        $eventForm.Controls.Add($comboType)
        
        # Grid
        $gridEvents = [System.Windows.Forms.DataGridView]::new()
        $gridEvents.Location = [System.Drawing.Point]::new(10, 40)
        $gridEvents.Size = [System.Drawing.Size]::new(970, 620)
        $gridEvents.BackgroundColor = $bgDark
        $gridEvents.ForeColor = $textWhite
        $gridEvents.DefaultCellStyle.BackColor = $bgDark
        $gridEvents.DefaultCellStyle.ForeColor = $textWhite
        $gridEvents.DefaultCellStyle.SelectionBackColor = $accent
        $gridEvents.DefaultCellStyle.SelectionForeColor = $textWhite
        $gridEvents.ColumnHeadersDefaultCellStyle.BackColor = $bgLight
        $gridEvents.ColumnHeadersDefaultCellStyle.ForeColor = $textWhite
        $gridEvents.BorderStyle = 'None'
        $gridEvents.ReadOnly = $true
        $gridEvents.SelectionMode = 'FullRowSelect'
        $gridEvents.MultiSelect = $false
        $gridEvents.AutoSizeColumnsMode = 'Fill'
        $gridEvents.Columns.Add('Type', 'Type') | Out-Null
        $gridEvents.Columns.Add('TypeName', 'Type Name') | Out-Null
        $gridEvents.Columns.Add('Event', 'Event') | Out-Null
        $gridEvents.Columns.Add('Status', 'Status') | Out-Null
        $gridEvents.Columns.Add('Line', 'Line') | Out-Null
        $gridEvents.Columns.Add('Details', 'Details') | Out-Null
        $gridEvents.Columns['Type'].Width = 100
        $gridEvents.Columns['TypeName'].Width = 150
        $gridEvents.Columns['Event'].Width = 150
        $gridEvents.Columns['Status'].Width = 150
        $gridEvents.Columns['Line'].Width = 60
        $gridEvents.Columns['Details'].Width = 360
        $eventForm.Controls.Add($gridEvents)
        
        function Update-EventGrid {
            $filter = $comboFilter.SelectedItem
            $typeFilter = $comboType.SelectedItem
            
            $gridEvents.Rows.Clear()
            
            $filtered = $report | Where-Object {
                ($filter -eq 'All' -or $_.Type -eq $filter) -and
                ($typeFilter -eq 'All Types' -or $_.TypeName -eq $typeFilter)
            }
            
            foreach ($item in $filtered) {
                $row = $gridEvents.Rows.Add()
                $gridEvents.Rows[$row].Cells['Type'].Value = $item.Type
                $gridEvents.Rows[$row].Cells['TypeName'].Value = $item.TypeName
                $gridEvents.Rows[$row].Cells['Event'].Value = $item.Event
                $gridEvents.Rows[$row].Cells['Status'].Value = $item.Status
                $gridEvents.Rows[$row].Cells['Line'].Value = if ($item.Line -gt 0) { $item.Line } else { '' }
                $gridEvents.Rows[$row].Cells['Details'].Value = $item.Details
                
                # Color code
                if ($item.Type -eq 'Duplicate' -or $item.Type -eq 'Unused') {
                    $gridEvents.Rows[$row].DefaultCellStyle.ForeColor = [System.Drawing.Color]::FromArgb(255, 200, 100)
                }
                elseif ($item.Status -like '✓*') {
                    $gridEvents.Rows[$row].DefaultCellStyle.ForeColor = [System.Drawing.Color]::FromArgb(100, 255, 100)
                }
                
                $gridEvents.Rows[$row].Tag = $item
            }
        }
        
        $comboFilter.Add_SelectedIndexChanged({ Update-EventGrid })
        $comboType.Add_SelectedIndexChanged({ Update-EventGrid })
        Update-EventGrid
        
        $eventForm.ShowDialog() | Out-Null
    })
    
    $gridSemantic.Add_CellDoubleClick({
        $row = $gridSemantic.CurrentRow
        if ($row -and $row.Tag) {
            $issue = $row.Tag
            $line = $issue.Line
            $file = $issue.File
            
            if (Test-Path $file) {
                $vscode = Get-Command code -ErrorAction SilentlyContinue
                if ($vscode) {
                    Start-Process code -ArgumentList "--goto", "$file`:$line"
                }
                else {
                    Start-Process notepad.exe -ArgumentList $file
                }
            }
        }
    })
    
    # Pre-fill paths if provided (check both $Path parameter and $script:InitialPath)
    $pathToUse = if ($Path) { $Path } elseif ($script:InitialPath) { $script:InitialPath } else { $null }
    
    # Debug logging (can be removed later)
    $logFile = Join-Path $PSScriptRoot "tool_debug.log"
    $logMsg = @"
[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] Path parameter check:
  - `$Path = '$Path'
  - `$script:InitialPath = '$script:InitialPath'
  - `$pathToUse = '$pathToUse'
"@
    Add-Content -Path $logFile -Value $logMsg -ErrorAction SilentlyContinue
    
    if ($pathToUse) { 
        # Resolve relative paths and validate
        try {
            # If path is relative, resolve it relative to the Extensions directory (sibling of Tools)
            $extensionsDir = Join-Path $PSScriptRoot '..'
            if (-not ([System.IO.Path]::IsPathRooted($pathToUse))) {
                # Relative path - resolve relative to Extensions directory
                $fullPath = Join-Path $extensionsDir $pathToUse
            }
            else {
                # Absolute path
                $fullPath = $pathToUse
            }
            
            # Resolve the path (handles .. and .)
            # Use SilentlyContinue to avoid hanging on network drives or invalid paths
            $resolvedPathInfo = Resolve-Path $fullPath -ErrorAction SilentlyContinue
            if ($resolvedPathInfo) {
                $resolvedPath = $resolvedPathInfo.Path  # Get string path from PathInfo object
            } else {
                # If resolution fails, use the original path
                $resolvedPath = $fullPath
            }
            
            if (Test-Path $resolvedPath -PathType Container) {
                # It's a folder
                $txtPath.Text = $resolvedPath
                $txtHealthPath.Text = $resolvedPath
                $txtUnidPath.Text = $resolvedPath
                $txtDepPath.Text = $resolvedPath
                $txtSemPath.Text = $resolvedPath
                $txtLivePath.Text = $resolvedPath
                Add-Content -Path $logFile -Value "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] Path set successfully: $resolvedPath" -ErrorAction SilentlyContinue
            }
            elseif (Test-Path $resolvedPath -PathType Leaf) {
                # It's a file - use parent directory
                $parentDir = Split-Path $resolvedPath -Parent
                $txtPath.Text = $resolvedPath
                $txtHealthPath.Text = $parentDir
                $txtUnidPath.Text = $parentDir
                $txtDepPath.Text = $parentDir
                $txtSemPath.Text = $parentDir
                $txtLivePath.Text = $parentDir
            }
            else {
                # Path doesn't exist - set as-is and let user fix
                $txtPath.Text = $resolvedPath
                $txtHealthPath.Text = $resolvedPath
                $txtUnidPath.Text = $resolvedPath
                $txtDepPath.Text = $resolvedPath
                $txtSemPath.Text = $resolvedPath
                $txtLivePath.Text = $resolvedPath
            }
        }
        catch {
            # Path doesn't exist or can't be resolved - set as-is and let user fix
            $txtPath.Text = $pathToUse
            $txtHealthPath.Text = $pathToUse
            $txtUnidPath.Text = $pathToUse
            $txtDepPath.Text = $pathToUse
            $txtSemPath.Text = $pathToUse
            $txtLivePath.Text = $pathToUse
            Add-Content -Path $logFile -Value "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] Error resolving path: $_" -ErrorAction SilentlyContinue
        }
    }
    else {
        Add-Content -Path $logFile -Value "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] No path provided - pathToUse is null" -ErrorAction SilentlyContinue
    }
    
    # Try to auto-detect Extensions folder
    $possibleExtensions = @(
        (Join-Path $PSScriptRoot '..'),
        (Join-Path $PSScriptRoot '..\..'),
        'D:\games\Steam\steamapps\common\Transcendence\Extensions'
    )
    foreach ($possible in $possibleExtensions) {
        if (Test-Path $possible) {
            $txtCompatPath.Text = $possible
            break
        }
    }

# ============================================================
# TAB: MIGRATION SAFETY
# ============================================================
$tabMigration = [System.Windows.Forms.TabPage]::new()
$tabMigration.Text = '  Migration Safety  '
$tabMigration.BackColor = $bgDark
$tabMigration.Padding = [System.Windows.Forms.Padding]::new(10)
$tabs.TabPages.Add($tabMigration)

# Load migration safety modules
$migrationModule = Join-Path $PSScriptRoot 'TranscendenceModTools_MigrationSafety.ps1'
$testRunnerModule = Join-Path $PSScriptRoot 'TranscendenceModTools_TestRunner.ps1'
if (Test-Path $migrationModule) {
    try {
        . $migrationModule
    }
    catch {
        Write-Warning "Failed to load migration safety module: $_"
    }
}
if (Test-Path $testRunnerModule) {
    try {
        . $testRunnerModule
    }
    catch {
        Write-Warning "Failed to load test runner module: $_"
    }
}

# Split container for different panels
$splitMigration = [System.Windows.Forms.SplitContainer]::new()
$splitMigration.Dock = 'Fill'
$splitMigration.Orientation = 'Vertical'
$splitMigration.SplitterDistance = 600
$splitMigration.BackColor = $bgDark
$tabMigration.Controls.Add($splitMigration)

# Left panel: Diff & Verification
$pnlLeft = [System.Windows.Forms.Panel]::new()
$pnlLeft.Dock = 'Fill'
$pnlLeft.BackColor = $bgDark
$splitMigration.Panel1.Controls.Add($pnlLeft)

# Tab control for left panel sections
$tabLeft = [System.Windows.Forms.TabControl]::new()
$tabLeft.Dock = 'Fill'
$tabLeft.BackColor = $bgDark
$pnlLeft.Controls.Add($tabLeft)

# Sub-tab 1: Diff Viewer
$subTabDiff = [System.Windows.Forms.TabPage]::new()
$subTabDiff.Text = 'Diff Viewer'
$subTabDiff.BackColor = $bgDark
$tabLeft.TabPages.Add($subTabDiff)

$lblOriginal = [System.Windows.Forms.Label]::new()
$lblOriginal.Text = 'Original Path:'
$lblOriginal.Location = [System.Drawing.Point]::new(10, 10)
$lblOriginal.AutoSize = $true
$lblOriginal.ForeColor = $textWhite
$subTabDiff.Controls.Add($lblOriginal)

$txtOriginal = [System.Windows.Forms.TextBox]::new()
$txtOriginal.Location = [System.Drawing.Point]::new(100, 8)
$txtOriginal.Size = [System.Drawing.Size]::new(400, 25)
$txtOriginal.BackColor = $bgLight
$txtOriginal.ForeColor = $textWhite
$subTabDiff.Controls.Add($txtOriginal)

$lblManual = [System.Windows.Forms.Label]::new()
$lblManual.Text = 'Manual Path:'
$lblManual.Location = [System.Drawing.Point]::new(10, 40)
$lblManual.AutoSize = $true
$lblManual.ForeColor = $textWhite
$subTabDiff.Controls.Add($lblManual)

$txtManual = [System.Windows.Forms.TextBox]::new()
$txtManual.Location = [System.Drawing.Point]::new(100, 38)
$txtManual.Size = [System.Drawing.Size]::new(400, 25)
$txtManual.BackColor = $bgLight
$txtManual.ForeColor = $textWhite
$subTabDiff.Controls.Add($txtManual)

$lblAi = [System.Windows.Forms.Label]::new()
$lblAi.Text = 'AI Path:'
$lblAi.Location = [System.Drawing.Point]::new(10, 70)
$lblAi.AutoSize = $true
$lblAi.ForeColor = $textWhite
$subTabDiff.Controls.Add($lblAi)

$txtAi = [System.Windows.Forms.TextBox]::new()
$txtAi.Location = [System.Drawing.Point]::new(100, 68)
$txtAi.Size = [System.Drawing.Size]::new(400, 25)
$txtAi.BackColor = $bgLight
$txtAi.ForeColor = $textWhite
$subTabDiff.Controls.Add($txtAi)

$btnDiff = [System.Windows.Forms.Button]::new()
$btnDiff.Text = 'Run Diff'
$btnDiff.Location = [System.Drawing.Point]::new(510, 35)
$btnDiff.Size = [System.Drawing.Size]::new(100, 30)
$btnDiff.BackColor = $accentGreen
$btnDiff.ForeColor = $textWhite
$btnDiff.FlatStyle = 'Flat'
$subTabDiff.Controls.Add($btnDiff)

$gridDiff = [System.Windows.Forms.DataGridView]::new()
$gridDiff.Location = [System.Drawing.Point]::new(10, 100)
$gridDiff.Size = [System.Drawing.Size]::new(600, 400)
$gridDiff.BackgroundColor = $bgDark
$gridDiff.ForeColor = $textWhite
$gridDiff.GridColor = $bgLight
$gridDiff.RowHeadersVisible = $false
$gridDiff.AllowUserToAddRows = $false
$gridDiff.ReadOnly = $true
$gridDiff.SelectionMode = 'FullRowSelect'
$gridDiff.AutoSizeColumnsMode = 'Fill'
$gridDiff.DefaultCellStyle.BackColor = $bgDark
$gridDiff.DefaultCellStyle.ForeColor = $textWhite
$gridDiff.DefaultCellStyle.SelectionBackColor = $accent
$gridDiff.ColumnHeadersDefaultCellStyle.BackColor = $bgMedium
$gridDiff.ColumnHeadersDefaultCellStyle.ForeColor = $textWhite
$gridDiff.EnableHeadersVisualStyles = $false
$gridDiff.Anchor = 'Top,Left,Right,Bottom'
$subTabDiff.Controls.Add($gridDiff)

$gridDiff.Columns.Add('FileName', 'File') | Out-Null
$gridDiff.Columns.Add('Status', 'Status') | Out-Null
$gridDiff.Columns.Add('RiskScore', 'Risk') | Out-Null
$gridDiff.Columns.Add('Conflicts', 'Conflicts') | Out-Null
$gridDiff.Columns['RiskScore'].Width = 60

$btnDiff.Add_Click({
    $original = $txtOriginal.Text
    $manual = $txtManual.Text
    $ai = $txtAi.Text
    
    if ([string]::IsNullOrWhiteSpace($original) -or [string]::IsNullOrWhiteSpace($manual) -or [string]::IsNullOrWhiteSpace($ai)) {
        [System.Windows.Forms.MessageBox]::Show('Please provide all three paths (Original, Manual, AI)', 'Missing Paths', 'OK', 'Warning')
        return
    }
    
    try {
        $outputPath = Join-Path $PSScriptRoot "migration_diff_$(Get-Date -Format 'yyyyMMdd_HHmmss').txt"
        $diff = Get-MigrationDiff -OriginalPath $original -ManualPath $manual -AiPath $ai -OutputPath $outputPath
        
        $gridDiff.Rows.Clear()
        foreach ($file in $diff.Files | Sort-Object RiskScore -Descending) {
            $row = $gridDiff.Rows.Add($file.FileName, $file.Status, $file.RiskScore, $file.Conflicts.Count)
            $gridDiff.Rows[$row].Tag = $file
            
            # Color by risk
            if ($file.RiskScore -ge 50) {
                $gridDiff.Rows[$row].DefaultCellStyle.BackColor = [System.Drawing.Color]::FromArgb(80, 40, 40)
            }
            elseif ($file.RiskScore -ge 20) {
                $gridDiff.Rows[$row].DefaultCellStyle.BackColor = [System.Drawing.Color]::FromArgb(80, 70, 40)
            }
        }
        
        [System.Windows.Forms.MessageBox]::Show("Diff complete. Found $($diff.Summary.Conflicts) conflicts.`nReport saved to:`n$outputPath", 'Diff Complete', 'OK', 'Information')
    }
    catch {
        [System.Windows.Forms.MessageBox]::Show("Error running diff: $_", 'Error', 'OK', 'Error')
    }
})

# Sub-tab 2: Verification
$subTabVerify = [System.Windows.Forms.TabPage]::new()
$subTabVerify.Text = 'Verification'
$subTabVerify.BackColor = $bgDark
$tabLeft.TabPages.Add($subTabVerify)

$lblVerifyPath = [System.Windows.Forms.Label]::new()
$lblVerifyPath.Text = 'Mod Path:'
$lblVerifyPath.Location = [System.Drawing.Point]::new(10, 10)
$lblVerifyPath.AutoSize = $true
$lblVerifyPath.ForeColor = $textWhite
$subTabVerify.Controls.Add($lblVerifyPath)

$txtVerifyPath = [System.Windows.Forms.TextBox]::new()
$txtVerifyPath.Location = [System.Drawing.Point]::new(80, 8)
$txtVerifyPath.Size = [System.Drawing.Size]::new(500, 25)
$txtVerifyPath.BackColor = $bgLight
$txtVerifyPath.ForeColor = $textWhite
$subTabVerify.Controls.Add($txtVerifyPath)

$chkSchema = [System.Windows.Forms.CheckBox]::new()
$chkSchema.Text = 'Schema'
$chkSchema.Location = [System.Drawing.Point]::new(10, 40)
$chkSchema.AutoSize = $true
$chkSchema.ForeColor = $textWhite
$chkSchema.Checked = $true
$subTabVerify.Controls.Add($chkSchema)

$chkSemantic = [System.Windows.Forms.CheckBox]::new()
$chkSemantic.Text = 'Semantic'
$chkSemantic.Location = [System.Drawing.Point]::new(80, 40)
$chkSemantic.AutoSize = $true
$chkSemantic.ForeColor = $textWhite
$chkSemantic.Checked = $true
$subTabVerify.Controls.Add($chkSemantic)

$chkApi = [System.Windows.Forms.CheckBox]::new()
$chkApi.Text = 'API Deprecation'
$chkApi.Location = [System.Drawing.Point]::new(160, 40)
$chkApi.AutoSize = $true
$chkApi.ForeColor = $textWhite
$chkApi.Checked = $true
$subTabVerify.Controls.Add($chkApi)

$btnVerify = [System.Windows.Forms.Button]::new()
$btnVerify.Text = 'Run Verification'
$btnVerify.Location = [System.Drawing.Point]::new(590, 35)
$btnVerify.Size = [System.Drawing.Size]::new(120, 30)
$btnVerify.BackColor = $accentGreen
$btnVerify.ForeColor = $textWhite
$btnVerify.FlatStyle = 'Flat'
$subTabVerify.Controls.Add($btnVerify)

$txtVerifyResults = [System.Windows.Forms.RichTextBox]::new()
$txtVerifyResults.Location = [System.Drawing.Point]::new(10, 75)
$txtVerifyResults.Size = [System.Drawing.Size]::new(700, 425)
$txtVerifyResults.BackColor = $bgLight
$txtVerifyResults.ForeColor = $textWhite
$txtVerifyResults.Font = [System.Drawing.Font]::new('Consolas', 9)
$txtVerifyResults.ReadOnly = $true
$txtVerifyResults.Anchor = 'Top,Left,Right,Bottom'
$subTabVerify.Controls.Add($txtVerifyResults)

$btnVerify.Add_Click({
    $modPath = $txtVerifyPath.Text
    if ([string]::IsNullOrWhiteSpace($modPath)) {
        return
    }
    
    try {
        $txtVerifyResults.Clear()
        $txtVerifyResults.AppendText("Running verification...`n`n")
        
        $results = Invoke-MigrationVerification -ModPath $modPath -SchemaCheck:$chkSchema.Checked -SemanticCheck:$chkSemantic.Checked -ApiDeprecationCheck:$chkApi.Checked
        
        $txtVerifyResults.AppendText("Verification Results`n")
        $txtVerifyResults.AppendText("==================`n`n")
        $txtVerifyResults.AppendText("Overall: $($results.Overall)`n`n")
        
        if ($results.Schema) {
            $txtVerifyResults.AppendText("Schema Check:`n")
            $txtVerifyResults.AppendText("  Passed: $($results.Schema.Passed)`n")
            $txtVerifyResults.AppendText("  Well-formed Errors: $($results.Schema.WellformedErrors)`n")
            $txtVerifyResults.AppendText("  BOM Errors: $($results.Schema.BomErrors)`n")
            $txtVerifyResults.AppendText("  Total Issues: $($results.Schema.TotalIssues)`n`n")
        }
        
        if ($results.Semantic) {
            $txtVerifyResults.AppendText("Semantic Check:`n")
            $txtVerifyResults.AppendText("  Passed: $($results.Semantic.Passed)`n")
            $txtVerifyResults.AppendText("  UNID Issues: $($results.Semantic.UnidIssues)`n")
            $txtVerifyResults.AppendText("  Resource Issues: $($results.Semantic.ResourceIssues)`n`n")
        }
        
        if ($results.ApiDeprecation) {
            $txtVerifyResults.AppendText("API Deprecation:`n")
            $txtVerifyResults.AppendText("  Passed: $($results.ApiDeprecation.Passed)`n")
            $txtVerifyResults.AppendText("  Deprecations Found: $($results.ApiDeprecation.Count)`n`n")
        }
    }
    catch {
        $txtVerifyResults.AppendText("Error: $_`n")
    }
})

# Right panel: Test Runner & Risk Report
$pnlRight = [System.Windows.Forms.Panel]::new()
$pnlRight.Dock = 'Fill'
$pnlRight.BackColor = $bgDark
$splitMigration.Panel2.Controls.Add($pnlRight)

$tabRight = [System.Windows.Forms.TabControl]::new()
$tabRight.Dock = 'Fill'
$tabRight.BackColor = $bgDark
$pnlRight.Controls.Add($tabRight)

# Sub-tab 3: Test Runner
$subTabTest = [System.Windows.Forms.TabPage]::new()
$subTabTest.Text = 'Test Runner'
$subTabTest.BackColor = $bgDark
$tabRight.TabPages.Add($subTabTest)

$lblTestPath = [System.Windows.Forms.Label]::new()
$lblTestPath.Text = 'Mod Path:'
$lblTestPath.Location = [System.Drawing.Point]::new(10, 10)
$lblTestPath.AutoSize = $true
$lblTestPath.ForeColor = $textWhite
$subTabTest.Controls.Add($lblTestPath)

$txtTestPath = [System.Windows.Forms.TextBox]::new()
$txtTestPath.Location = [System.Drawing.Point]::new(80, 8)
$txtTestPath.Size = [System.Drawing.Size]::new(400, 25)
$txtTestPath.BackColor = $bgLight
$txtTestPath.ForeColor = $textWhite
$subTabTest.Controls.Add($txtTestPath)

$btnRunTests = [System.Windows.Forms.Button]::new()
$btnRunTests.Text = 'Run Tests'
$btnRunTests.Location = [System.Drawing.Point]::new(490, 6)
$btnRunTests.Size = [System.Drawing.Size]::new(100, 30)
$btnRunTests.BackColor = $accentGreen
$btnRunTests.ForeColor = $textWhite
$btnRunTests.FlatStyle = 'Flat'
$subTabTest.Controls.Add($btnRunTests)

$listTests = [System.Windows.Forms.ListView]::new()
$listTests.Location = [System.Drawing.Point]::new(10, 45)
$listTests.Size = [System.Drawing.Size]::new(580, 455)
$listTests.BackColor = $bgLight
$listTests.ForeColor = $textWhite
$listTests.View = 'Details'
$listTests.FullRowSelect = $true
$listTests.Anchor = 'Top,Left,Right,Bottom'
$subTabTest.Controls.Add($listTests)

$listTests.Columns.Add('Test', 200) | Out-Null
$listTests.Columns.Add('Status', 100) | Out-Null
$listTests.Columns.Add('Risk', 80) | Out-Null

$btnRunTests.Add_Click({
    $modPath = $txtTestPath.Text
    if ([string]::IsNullOrWhiteSpace($modPath)) {
        return
    }
    
    $listTests.Items.Clear()
    
    $checklist = Get-PlaytestChecklist
    foreach ($item in $checklist) {
        $listItem = [System.Windows.Forms.ListViewItem]::new($item.Item)
        $listItem.SubItems.Add('Pending')
        $listItem.SubItems.Add($item.Priority)
        $listItem.Tag = $item
        $listTests.Items.Add($listItem)
    }
    
    [System.Windows.Forms.MessageBox]::Show('Test runner requires game integration. Tests are defined but need game API to execute.', 'Test Runner', 'OK', 'Information')
})

# Sub-tab 4: Risk Report
$subTabRisk = [System.Windows.Forms.TabPage]::new()
$subTabRisk.Text = 'Risk Report'
$subTabRisk.BackColor = $bgDark
$tabRight.TabPages.Add($subTabRisk)

$txtRiskReport = [System.Windows.Forms.RichTextBox]::new()
$txtRiskReport.Dock = 'Fill'
$txtRiskReport.BackColor = $bgLight
$txtRiskReport.ForeColor = $textWhite
$txtRiskReport.Font = [System.Drawing.Font]::new('Consolas', 9)
$txtRiskReport.ReadOnly = $true
$subTabRisk.Controls.Add($txtRiskReport)

# Update risk report when diff is run
$script:UpdateRiskReport = {
    param($diff)
    
    if ($diff) {
        $riskReport = Get-MigrationRiskReport -Diff $diff
        
        $txtRiskReport.Clear()
        $txtRiskReport.AppendText("Migration Risk Report`n")
        $txtRiskReport.AppendText("===================`n`n")
        $txtRiskReport.AppendText("High Risk Files ($($riskReport.HighRiskCount)):`n")
        foreach ($file in $riskReport.HighRisk) {
            $txtRiskReport.AppendText("  - $($file.FileName) (Score: $($file.RiskScore))`n")
        }
        $txtRiskReport.AppendText("`nMedium Risk Files ($($riskReport.MediumRiskCount)):`n")
        foreach ($file in $riskReport.MediumRisk) {
            $txtRiskReport.AppendText("  - $($file.FileName) (Score: $($file.RiskScore))`n")
        }
        $txtRiskReport.AppendText("`nLow Risk Files ($($riskReport.LowRiskCount)):`n")
        foreach ($file in $riskReport.LowRisk) {
            $txtRiskReport.AppendText("  - $($file.FileName) (Score: $($file.RiskScore))`n")
        }
    }
}

# Update risk report when diff completes
$btnDiff.Add_Click({
    # ... existing diff code ...
    if ($diff) {
        & $script:UpdateRiskReport $diff
    }
})

[void]$form.ShowDialog()
}

# ============================================================
# MAIN
# ============================================================

# Auto-scan mode: scan and exit without GUI
if ($AutoScan -or $ScanAndExit) {
    if (-not $Path) {
        Write-Host 'ERROR: -AutoScan or -ScanAndExit requires -Path parameter' -ForegroundColor Red
        Write-Host ''
        Write-Host 'Usage:'
        Write-Host '  pwsh -File TranscendenceModTools.ps1 -AutoScan -Path "path\to\mod"'
        Write-Host '  pwsh -File TranscendenceModTools.ps1 -ScanAndExit -Path "path\to\mod"'
        exit 1
    }
    
    Write-Host 'Transcendence Mod Tools - Auto-Scan Mode' -ForegroundColor Cyan
    Write-Host '========================================' -ForegroundColor Cyan
    Write-Host ''
    
    # Resolve path (use -LiteralPath to handle square brackets and other special characters)
    # Use SilentlyContinue to avoid hanging on network drives or invalid paths
    try {
        if ([System.IO.Path]::IsPathRooted($Path)) {
            if (Test-Path -LiteralPath $Path) {
                $resolvedPathInfo = Resolve-Path -LiteralPath $Path -ErrorAction SilentlyContinue
                if ($resolvedPathInfo) {
                    $resolvedPath = $resolvedPathInfo.Path
                } else {
                    $resolvedPath = $Path  # Use original if resolution fails
                }
            }
            else {
                Write-Host "ERROR: Path does not exist: $Path" -ForegroundColor Red
                exit 1
            }
        }
        else {
            # Try relative to Extensions folder first
            $extensionsDir = Join-Path (Split-Path $PSScriptRoot -Parent) "Extensions"
            $fullPath = Join-Path $extensionsDir $Path
            if (Test-Path -LiteralPath $fullPath) {
                $resolvedPathInfo = Resolve-Path -LiteralPath $fullPath -ErrorAction SilentlyContinue
                if ($resolvedPathInfo) {
                    $resolvedPath = $resolvedPathInfo.Path
                } else {
                    $resolvedPath = $fullPath  # Use original if resolution fails
                }
            }
            elseif (Test-Path -LiteralPath $Path) {
                # Try relative to current directory
                $resolvedPathInfo = Resolve-Path -LiteralPath $Path -ErrorAction SilentlyContinue
                if ($resolvedPathInfo) {
                    $resolvedPath = $resolvedPathInfo.Path
                } else {
                    $resolvedPath = $Path  # Use original if resolution fails
                }
            }
            else {
                Write-Host "ERROR: Path does not exist: $Path" -ForegroundColor Red
                exit 1
            }
        }
    }
    catch {
        Write-Host "ERROR: Cannot resolve path: $Path" -ForegroundColor Red
        Write-Host "Error: $_" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "Scanning: $resolvedPath" -ForegroundColor Yellow
    Write-Host ''
    
    # Get files (XML and TDB) - recursion is default, so all files in subdirectories are scanned
    $fileResult = Get-XmlAndTdbFiles -Path $resolvedPath -Recurse $true
    $files = $fileResult.XmlFiles
    $tdbFiles = $fileResult.TdbFiles
    $tdbWarnings = $fileResult.TdbWarnings
    
    # Show TDB warnings
    if ($tdbWarnings.Count -gt 0) {
        Write-Host "TDB Warnings:" -ForegroundColor Yellow
        foreach ($warning in $tdbWarnings) {
            Write-Host "  $warning" -ForegroundColor Yellow
        }
        Write-Host ''
    }
    
    if ($files.Count -eq 0 -and $tdbFiles.Count -eq 0) {
        Write-Host 'No XML or TDB files found' -ForegroundColor Red
        exit 1
    }
    
    Write-Host "Found $($files.Count) XML file(s), $($tdbFiles.Count) TDB file(s)" -ForegroundColor Green
    Write-Host ''
    
    # Load TDB parser if we have TDB files
    $tdbModule = Join-Path $PSScriptRoot 'TranscendenceModTools_TDBParser.ps1'
    $tdbParserLoaded = $false
    if ($tdbFiles.Count -gt 0 -and (Test-Path $tdbModule)) {
        try {
            . $tdbModule
            $tdbParserLoaded = $true
            Write-Host "TDB Parser loaded" -ForegroundColor Green
        }
        catch {
            Write-Host "Warning: TDB parser failed to load: $_" -ForegroundColor Yellow
        }
    }
    
    # Load advanced features
    $advancedModule = Join-Path $PSScriptRoot 'TranscendenceModTools_Advanced.ps1'
    $advancedLoaded = $false
    if (Test-Path $advancedModule) {
        try {
            . $advancedModule
            $advancedLoaded = $true
        }
        catch {
            Write-Host "Warning: Advanced features failed to load: $_" -ForegroundColor Yellow
        }
    }
    
    # Load API rules for deprecation checks (auto-update if needed)
    $apiRulesModule = Join-Path $PSScriptRoot 'TranscendenceModTools_ApiRules.ps1'
    $apiRulesLoaded = $false
    $apiRules = $null
    if (Test-Path $apiRulesModule) {
        try {
            . $apiRulesModule
            
            # Auto-update if source files are newer
            $apiRules = Update-ApiRulesIfNeeded -ApiVersion $script:DefaultApiVersion -Quiet
            
            if ($apiRules) {
                $apiRulesLoaded = $true
                Write-Host "API Rules loaded (v$($apiRules.ApiVersion), $($apiRules.Stats.TotalTags) tags, $($apiRules.Stats.TotalFunctions) functions)" -ForegroundColor Green
            }
        }
        catch {
            Write-Host "Warning: API rules failed to load: $_" -ForegroundColor Yellow
        }
    }
    
    # Pre-populate UNID registry from Extensions, Collection, and Transcendence.tdb
    # Priority is based on UNID range AND file type:
    # 1=Game/DLC (0x0000-0x9FFF + official DLC TDBs), 2=Dynamic (0xF000-0xFFFF), 
    # 3=Registered Extensions (0xA000-0xCFFF), 4=User UNIDs (0xD000-0xEFFF), 
    # 5=Unknown/Unregistered (Extensions and third-party Collection mods are same priority)
    Write-Host "Pre-loading UNIDs from game, DLC, and mods..." -ForegroundColor Yellow
    $allUnids = @{}
    $transcendenceRoot = Find-TranscendenceRoot -StartPath $PSScriptRoot
    if (-not $transcendenceRoot) {
        Write-Host "WARNING: Transcendence installation not detected." -ForegroundColor Yellow
        Write-Host "  UNID scanning requires Extensions/Collection folders." -ForegroundColor Gray
        Write-Host "  Most other features (XML checking, error diagnosis) work without it." -ForegroundColor Gray
        return @{}
    }
    $extensionsPath = Join-Path $transcendenceRoot "Extensions"
    $collectionPath = Join-Path $transcendenceRoot "Collection"
    
    # Official DLC TDB files (have priority 1, same as game)
    $officialDlcTdbs = @(
        'CorporateCommand.tdb',
        'CorporateHierarchyVol01.tdb',
        'CorporateHierarchyVol1UNIDs.tdb',
        'DebugPart1.tdb',
        'EternityPort.tdb',
        'StarsOfThePilgrimHD.tdb',
        'StarsOfThePilgrimSoundtrack.tdb'
    )
    
    # Official mods (have higher priority than third-party mods)
    $officialMods = @(
        'VaultOfTheGalaxy',
        'Vault of the Galaxy'
    )
    
    # Function to check if a TDB file is official DLC
    function Test-IsOfficialDlcTdb {
        param([string]$FilePath)
        $fileName = Split-Path -Leaf $FilePath
        return $officialDlcTdbs -contains $fileName
    }
    
    # Function to check if a mod is official
    function Test-IsOfficialMod {
        param([string]$ModName)
        return $officialMods -contains $ModName
    }
    
    # Function to determine UNID range priority based on wiki.kronosaur.com/modding/unid_database
    # Reference: https://wiki.kronosaur.com/doku.php/modding/unid_database
    function Get-UnidRangePriority {
        param([string]$UnidValue)
        
        # Parse UNID to integer (remove 0x prefix if present)
        $unidStr = $UnidValue -replace '^0x', ''
        try {
            $unidInt = [Convert]::ToUInt32($unidStr, 16)
        } catch {
            return 99  # Unknown/invalid - lowest priority
        }
        
        # Extract high 16 bits for range checking
        $high16 = ($unidInt -shr 16) -band 0xFFFF
        $low16 = $unidInt -band 0xFFFF
        
        # Priority 1: Game/DLC ranges (0x0000-0x9FFF)
        if ($high16 -ge 0x0000 -and $high16 -le 0x9FFF) {
            return 1
        }
        
        # Priority 2: Registered Extensions (0xA000-0xCFFF)
        # These are officially registered modder ranges
        if ($high16 -ge 0xA000 -and $high16 -le 0xCFFF) {
            return 3  # Registered extensions have priority over user UNIDs
        }
        
        # Priority 3: User UNIDs (0xD000-0xEFFF)
        # These are assigned to specific modders on the wiki
        if ($high16 -ge 0xD000 -and $high16 -le 0xEFFF) {
            return 4
        }
        
        # Priority 4: Dynamic UNIDs (0xF000-0xFFFF) - reserved for typCreate
        if ($high16 -ge 0xF000 -and $high16 -le 0xFFFF) {
            return 2  # Dynamic UNIDs are game-generated, high priority
        }
        
        # Unknown range - lowest priority
        return 99
    }
    
    # Function to get UNID range description
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
    
    # Function to get source priority (lower number = higher priority)
    # Priority is based ONLY on UNID range, not folder location
    # Collection and Extensions have the same priority (both default to 5, upgraded by UNID range)
    function Get-SourcePriority {
        param([string]$FilePath, [string]$UnidValue = "")
        
        # Always use range-based priority if UNID is provided
        if (-not [string]::IsNullOrWhiteSpace($UnidValue)) {
            $rangePriority = Get-UnidRangePriority -UnidValue $UnidValue
            if ($rangePriority -lt 99) {
                return $rangePriority
            }
        }
        
        # Fallback: only Transcendence.tdb gets priority 1 (game files)
        # Collection and Extensions are treated the same (priority 5)
        if ($FilePath -like "*Transcendence.tdb") { return 1 }
        return 5  # Collection and Extensions - same priority
    }
    
    # Function to scan UNIDs from a folder (XML and TDB files)
    # Collection contains official DLC TDBs (priority 1) and third-party mods (priority 5, same as Extensions)
    function Get-UnidsFromFolder {
        param([string]$FolderPath, [string]$SourceName, [bool]$IsCollection = $false)
        $unids = @{}
        if (Test-Path $FolderPath) {
            # Scan XML files
            $xmlFiles = Get-ChildItem -LiteralPath $FolderPath -Filter '*.xml' -Recurse -ErrorAction SilentlyContinue
            foreach ($xmlFile in $xmlFiles) {
                try {
                    $text = [System.IO.File]::ReadAllText($xmlFile.FullName, [System.Text.Encoding]::UTF8)
                    $unidDefPattern = '<!ENTITY\s+(\w+)\s+"(0x[0-9A-Fa-f]+)"'
                    $matches = [regex]::Matches($text, $unidDefPattern, 'IgnoreCase')
                    foreach ($m in $matches) {
                        $unidValue = $m.Groups[2].Value
                        # Priority is based on UNID range
                        $rangePriority = Get-UnidRangePriority -UnidValue $unidValue
                        $finalPriority = if ($rangePriority -lt 99) { $rangePriority } else { 5 }  # Default to 5 for unregistered
                        $rangeDesc = Get-UnidRangeDescription -UnidValue $unidValue
                        
                        # Check if this is an official mod in Collection
                        if ($IsCollection) {
                            $modFolder = Split-Path (Split-Path $xmlFile.FullName -Parent) -Leaf
                            if (Test-IsOfficialMod -ModName $modFolder) {
                                # Official mods get priority 2 (higher than third-party mods)
                                if ($finalPriority -gt 2) { $finalPriority = 2 }
                            }
                        }
                        
                        if (-not $unids.ContainsKey($unidValue)) {
                            $unids[$unidValue] = [PSCustomObject]@{
                                File = $xmlFile.FullName
                                Priority = $finalPriority
                                Source = $SourceName
                                Range = $rangeDesc
                                UnidValue = $unidValue
                            }
                        }
                    }
                } catch { }
            }
            
            # Scan TDB files in parallel for faster loading
            # Official DLC TDBs get priority 1 (same as game), third-party TDBs get priority based on UNID range
            $tdbFiles = @(Get-ChildItem -LiteralPath $FolderPath -Filter '*.tdb' -Recurse -ErrorAction SilentlyContinue)
            
            if ($tdbFiles.Count -gt 0) {
                # Use parallel processing for TDB files (PowerShell 7+)
                $tdbResults = $tdbFiles | ForEach-Object -Parallel {
                    $tdbFile = $_
                    $tdbPath = $tdbFile.FullName
                    $result = @{ TdbPath = $tdbPath; Unids = @{} }
                    
                    try {
                        # Fast method: read raw bytes and search for UNID patterns
                        $bytes = [System.IO.File]::ReadAllBytes($tdbPath)
                        $text = [System.Text.Encoding]::UTF8.GetString($bytes)
                        
                        # Search for UNID entity definitions
                        $unidDefPattern = '<!ENTITY\s+(\w+)\s+"(0x[0-9A-Fa-f]+)"'
                        $matches = [regex]::Matches($text, $unidDefPattern, 'IgnoreCase')
                        foreach ($m in $matches) {
                            $unidValue = $m.Groups[2].Value
                            if (-not $result.Unids.ContainsKey($unidValue)) {
                                $result.Unids[$unidValue] = $tdbPath
                            }
                        }
                        
                        # Also search for UNID= attributes
                        $unidAttrPattern = 'UNID\s*=\s*"(0x[0-9A-Fa-f]+)"'
                        $attrMatches = [regex]::Matches($text, $unidAttrPattern, 'IgnoreCase')
                        foreach ($m in $attrMatches) {
                            $unidValue = $m.Groups[1].Value
                            if (-not $result.Unids.ContainsKey($unidValue)) {
                                $result.Unids[$unidValue] = $tdbPath
                            }
                        }
                    } catch { }
                    
                    $result
                } -ThrottleLimit 8
                
                # Merge parallel results
                foreach ($tdbResult in $tdbResults) {
                    $tdbPath = $tdbResult.TdbPath
                    $isOfficialDlc = $officialDlcTdbs -contains (Split-Path -Leaf $tdbPath)
                    
                    foreach ($unid in $tdbResult.Unids.Keys) {
                        if (-not $unids.ContainsKey($unid)) {
                            # Official DLC TDBs get priority 1 (same as game), regardless of UNID range
                            if ($isOfficialDlc) {
                                $finalPriority = 1
                                $rangeDesc = "Official DLC"
                            }
                            else {
                                # Third-party TDBs: priority based on UNID range
                                $rangePriority = Get-UnidRangePriority -UnidValue $unid
                                $finalPriority = if ($rangePriority -lt 99) { $rangePriority } else { 5 }
                                $rangeDesc = Get-UnidRangeDescription -UnidValue $unid
                            }
                            
                            $unids[$unid] = [PSCustomObject]@{
                                File = $tdbPath
                                Priority = $finalPriority
                                Source = if ($isOfficialDlc) { "Official DLC" } else { $SourceName }
                                Range = $rangeDesc
                                UnidValue = $unid
                            }
                        }
                    }
                }
            }
        }
        return $unids
    }
    
    # Function to extract UNIDs from TDB file (fast regex-based extraction, no full parsing)
    function Get-UnidsFromTdb {
        param([string]$TdbPath)
        $unids = @{}
        if (Test-Path -LiteralPath $TdbPath) {
            try {
                # Fast method: read raw bytes and search for UNID patterns
                # TDB files contain XML text, so we can search for UNID definitions
                $bytes = [System.IO.File]::ReadAllBytes($TdbPath)
                $text = [System.Text.Encoding]::UTF8.GetString($bytes)
                
                # Search for UNID entity definitions
                $unidDefPattern = '<!ENTITY\s+(\w+)\s+"(0x[0-9A-Fa-f]+)"'
                $matches = [regex]::Matches($text, $unidDefPattern, 'IgnoreCase')
                foreach ($m in $matches) {
                    $unidValue = $m.Groups[2].Value
                    if (-not $unids.ContainsKey($unidValue)) {
                        $unids[$unidValue] = $TdbPath
                    }
                }
                
                # Also search for UNID= attributes
                $unidAttrPattern = 'UNID\s*=\s*"(0x[0-9A-Fa-f]+)"'
                $attrMatches = [regex]::Matches($text, $unidAttrPattern, 'IgnoreCase')
                foreach ($m in $attrMatches) {
                    $unidValue = $m.Groups[1].Value
                    if (-not $unids.ContainsKey($unidValue)) {
                        $unids[$unidValue] = $TdbPath
                    }
                }
            } catch { }
        }
        return $unids
    }
    
    # Populate from Transcendence.tdb in game root (Priority 1 - highest)
    Write-Host "  Loading from Transcendence.tdb..." -ForegroundColor Gray
    $transcendenceTdb = Join-Path $transcendenceRoot "Transcendence.tdb"
    $tdbUnids = Get-UnidsFromTdb -TdbPath $transcendenceTdb
    foreach ($unid in $tdbUnids.Keys) {
        # Use range-based priority (game UNIDs should be in 0x0000-0x9FFF range)
        $rangePriority = Get-UnidRangePriority -UnidValue $unid
        $finalPriority = if ($rangePriority -lt 99) { $rangePriority } else { 1 }
        $rangeDesc = Get-UnidRangeDescription -UnidValue $unid
        
        $allUnids[$unid] = [PSCustomObject]@{
            File = $tdbUnids[$unid]
            Priority = $finalPriority
            Source = 'Game'
            Range = $rangeDesc
            UnidValue = $unid
        }
    }
    
    # Populate from Collection
    # Collection contains official DLC TDBs (priority 1), official mods (priority 2), and third-party mods (priority 5)
    Write-Host "  Loading from Collection folder..." -ForegroundColor Gray
    $collUnids = Get-UnidsFromFolder -FolderPath $collectionPath -SourceName "Collection" -IsCollection $true
    foreach ($unid in $collUnids.Keys) {
        if (-not $allUnids.ContainsKey($unid)) {
            $allUnids[$unid] = $collUnids[$unid]
        }
        else {
            # Conflict: Check if existing has higher priority (based on UNID range)
            $existingPriority = if ($allUnids[$unid].Priority) { $allUnids[$unid].Priority } else { 5 }
            $newPriority = $collUnids[$unid].Priority
            if ($newPriority -lt $existingPriority) {
                # New UNID has higher priority, replace
                $allUnids[$unid] = $collUnids[$unid]
            }
            elseif ($newPriority -eq $existingPriority) {
                # Same priority - track as conflict
                if ($allUnids[$unid] -is [PSCustomObject]) {
                    $allUnids[$unid] = @($allUnids[$unid], $collUnids[$unid])
                }
                else {
                    $allUnids[$unid] = @($allUnids[$unid]) + @($collUnids[$unid])
                }
            }
            # If existing has higher priority, keep it (don't add new one)
        }
    }
    
    # Populate from Extensions (same priority as Collection - based on UNID range only)
    Write-Host "  Loading from Extensions folder..." -ForegroundColor Gray
    $extUnids = Get-UnidsFromFolder -FolderPath $extensionsPath -SourceName "Extensions"
    foreach ($unid in $extUnids.Keys) {
        if (-not $allUnids.ContainsKey($unid)) {
            $allUnids[$unid] = $extUnids[$unid]
        }
        else {
            # Conflict: Check if existing has higher priority (based on UNID range)
            $existingPriority = if ($allUnids[$unid].Priority) { $allUnids[$unid].Priority } else { 5 }
            $newPriority = $extUnids[$unid].Priority
            if ($newPriority -lt $existingPriority) {
                # New UNID has higher priority, replace
                $allUnids[$unid] = $extUnids[$unid]
            }
            elseif ($newPriority -eq $existingPriority) {
                # Same priority - track as conflict
                if ($allUnids[$unid] -is [PSCustomObject]) {
                    $allUnids[$unid] = @($allUnids[$unid], $extUnids[$unid])
                }
                else {
                    $allUnids[$unid] = @($allUnids[$unid]) + @($extUnids[$unid])
                }
            }
            # If existing has higher priority, keep it (don't add new one)
        }
    }
    
    $sources = @()
    if ($extUnids.Count -gt 0) { $sources += "Extensions ($($extUnids.Count))" }
    if ($collUnids.Count -gt 0) { $sources += "Collection ($($collUnids.Count))" }
    if ($tdbUnids.Count -gt 0) { $sources += "Transcendence.tdb ($($tdbUnids.Count))" }
    Write-Host "Pre-loaded $($allUnids.Count) UNID(s) from $($sources -join ', ')" -ForegroundColor Gray
    Write-Host ''
    
    # Scan XML files
    Write-Host "Scanning $($files.Count) XML file(s)..." -ForegroundColor Yellow
    $allIssues = @()
    $fileCount = 0
    $totalFiles = $files.Count + $tdbFiles.Count
    
    foreach ($f in $files) {
        $fileCount++
        $fileName = Split-Path -Leaf $f
        Write-Host "[$fileCount/$totalFiles] Scanning: $fileName" -NoNewline
        
        $fileIssues = @()
        try {
            $fileIssues += Get-XmlIssues -FilePath $f
            $hasWellformedError = @($fileIssues | Where-Object { $_.Code -eq 'XML_WELLFORMED_ERROR' }).Count -gt 0
            $hasUndeclaredEntity = @($fileIssues | Where-Object { $_.Code -eq 'ENTITY_UNDECLARED' -or ($_.Code -eq 'XML_WELLFORMED_ERROR' -and $_.Message -match 'undeclared entity') }).Count -gt 0
            
            if ($advancedLoaded) {
                # Only run structure heuristics if XML parsing failed (XmlReader is authoritative).
                if ($hasWellformedError) {
                    try { 
                        $structureIssues = Get-XmlStructureIssues -FilePath $f
                        # Mark structural issues as potentially cascading if caused by undeclared entities
                        if ($hasUndeclaredEntity) {
                            foreach ($issue in $structureIssues) {
                                if ($issue.Code -match 'TAG_MISMATCH|UNEXPECTED_CLOSE_TAG|UNCLOSED_TAG') {
                                    $issue.Message = $issue.Message + " [POTENTIALLY CASCADING - fix undeclared entities first]"
                                    $issue.IsCascading = $true
                                }
                            }
                        }
                        $fileIssues += $structureIssues
                    } catch { }
                }
                try { $fileIssues += Get-TlispExpressionIssues -FilePath $f } catch { }
                try { $fileIssues += Get-UnidReferenceIssues -FilePath $f -AllUnids $allUnids } catch { }
                try { $fileIssues += Get-ResourcePathIssues -FilePath $f } catch { }
                try { $fileIssues += Get-DeprecatedAttributeIssues -FilePath $f } catch { }
                try {
                    $indentIssues = Get-IndentationIssues -FilePath $f
                    if ($indentIssues) { $fileIssues += $indentIssues }
                } catch { }
            }
            
            # Validate against API rules (deprecated tags/functions)
            if ($apiRulesLoaded -and $apiRules) {
                try {
                    $apiIssues = Test-ModAgainstApiRules -ModPath $f -Rules $apiRules
                    if ($apiIssues) {
                        foreach ($apiIssue in $apiIssues) {
                            $fileIssues += [PSCustomObject]@{
                                File = $f
                                Line = 0
                                Code = "API_$($apiIssue.Type.ToUpper())"
                                Severity = $apiIssue.Severity
                                Message = $apiIssue.Message
                                CanFix = $false
                            }
                        }
                    }
                } catch { }
            }
        }
        catch {
            $fileIssues += [PSCustomObject]@{
                File = $f
                Line = 0
                Code = 'SCAN_ERROR'
                Severity = 'Error'
                Message = "Error scanning file: $_"
                CanFix = $false
            }
        }
        
        if ($fileIssues.Count -gt 0) {
            Write-Host " - Found $($fileIssues.Count) issue(s)" -ForegroundColor Yellow
            $allIssues += $fileIssues
        }
        else {
            Write-Host " - OK" -ForegroundColor Green
        }
    }
    
    # Scan TDB files if parser is loaded
    if ($tdbParserLoaded -and $tdbFiles.Count -gt 0) {
        foreach ($tdb in $tdbFiles) {
            $fileCount++
            $fileName = Split-Path -Leaf $tdb
            Write-Host "[$fileCount/$totalFiles] Scanning TDB: $fileName" -NoNewline
            
            $fileIssues = @()
            try {
                $tdbPreview = Get-TdbPreview -Path $tdb
                if ($tdbPreview.SemanticIssues) {
                    foreach ($issue in $tdbPreview.SemanticIssues) {
                        $fileIssues += [PSCustomObject]@{
                            File = $tdb
                            Line = 0
                            Code = $issue.Type
                            Severity = $issue.Severity
                            Message = $issue.Message
                            CanFix = $false
                        }
                    }
                }
                
                # Check for deprecations
                $deprecations = Test-TdbDeprecation -TdbData $tdbPreview
                foreach ($dep in $deprecations) {
                    $fileIssues += [PSCustomObject]@{
                        File = $tdb
                        Line = 0
                        Code = 'TDB_DEPRECATED'
                        Severity = $dep.Severity
                        Message = "$($dep.Type): $($dep.Suggestion)"
                        CanFix = $false
                    }
                }
            }
            catch {
                $fileIssues += [PSCustomObject]@{
                    File = $tdb
                    Line = 0
                    Code = 'TDB_SCAN_ERROR'
                    Severity = 'Error'
                    Message = "Error scanning TDB file: $_"
                    CanFix = $false
                }
            }
            
            if ($fileIssues.Count -gt 0) {
                Write-Host " - Found $($fileIssues.Count) issue(s)" -ForegroundColor Yellow
                $allIssues += $fileIssues
            }
            else {
                Write-Host " - OK" -ForegroundColor Green
            }
        }
    }
    
    Write-Host ''
    Write-Host '========================================' -ForegroundColor Cyan
    Write-Host 'SCAN RESULTS' -ForegroundColor Cyan
    Write-Host '========================================' -ForegroundColor Cyan
    Write-Host ''
    
    $errorCount = @($allIssues | Where-Object { $_.Severity -eq 'Error' }).Count
    $warnCount = @($allIssues | Where-Object { $_.Severity -eq 'Warning' }).Count
    $infoCount = @($allIssues | Where-Object { $_.Severity -eq 'Info' }).Count
    $fixable = @($allIssues | Where-Object { $_.CanFix }).Count
    
    $totalScanned = $files.Count + $tdbFiles.Count
    Write-Host "Files Scanned: $totalScanned ($($files.Count) XML, $($tdbFiles.Count) TDB)" -ForegroundColor White
    Write-Host "Total Issues: $($allIssues.Count)" -ForegroundColor White
    Write-Host "  Errors: $errorCount" -ForegroundColor $(if ($errorCount -gt 0) { 'Red' } else { 'Green' })
    Write-Host "  Warnings: $warnCount" -ForegroundColor $(if ($warnCount -gt 0) { 'Yellow' } else { 'Green' })
    Write-Host "  Info: $infoCount" -ForegroundColor $(if ($infoCount -gt 0) { 'Cyan' } else { 'Green' })
    Write-Host "  Fixable: $fixable" -ForegroundColor $(if ($fixable -gt 0) { 'Yellow' } else { 'Gray' })
    Write-Host ''
    
    # Group by file
    $byFile = $allIssues | Group-Object File
    if ($byFile.Count -gt 0) {
        Write-Host 'Issues by File:' -ForegroundColor Cyan
        Write-Host ''
        foreach ($fileGroup in $byFile | Sort-Object Count -Descending) {
            $fileName = Split-Path -Leaf $fileGroup.Name
            $fileErrors = @($fileGroup.Group | Where-Object { $_.Severity -eq 'Error' }).Count
            $fileWarnings = @($fileGroup.Group | Where-Object { $_.Severity -eq 'Warning' }).Count
            Write-Host "  $fileName" -ForegroundColor White
            Write-Host "    Total: $($fileGroup.Count) (Errors: $fileErrors, Warnings: $fileWarnings)" -ForegroundColor Gray
        }
        Write-Host ''
    }
    
    # Save log file
    $logFile = Join-Path $PSScriptRoot "scan_results_$(Get-Date -Format 'yyyyMMdd_HHmmss').txt"
    $logContent = @"
Transcendence Mod Tools - Scan Results
========================================
Scan Date: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
Path: $resolvedPath
Files Scanned: $($files.Count)

SUMMARY
-------
Total Issues: $($allIssues.Count)
  Errors: $errorCount
  Warnings: $warnCount
  Info: $infoCount
  Fixable: $fixable

DETAILED RESULTS
----------------
"@
    
    foreach ($issue in $allIssues) {
        $fileName = Split-Path -Leaf $issue.File
        $colInfo = if ($issue.Column) { ", Col $($issue.Column)" } else { "" }
        $logContent += "`n[$($issue.Severity)] $fileName (Line $($issue.Line)$colInfo)`n"
        $logContent += "  Code: $($issue.Code)`n"
        $logContent += "  Message: $($issue.Message)`n"
        # Include Context and Fix for precision errors
        if ($issue.Context) {
            $logContent += "  Context: $($issue.Context)`n"
        }
        if ($issue.Fix) {
            $logContent += "  Fix: $($issue.Fix)`n"
        }
        if ($issue.CanFix) {
            $logContent += "  [AUTO-FIXABLE]`n"
        }
    }
    
    [System.IO.File]::WriteAllText($logFile, $logContent, [System.Text.Encoding]::UTF8)
    Write-Host "Results saved to: $logFile" -ForegroundColor Green
    Write-Host ''
    
    # Exit with appropriate code
    if ($errorCount -gt 0) {
        Write-Host 'Scan completed with errors.' -ForegroundColor Red
        exit 1
    }
    elseif ($warnCount -gt 0) {
        Write-Host 'Scan completed with warnings.' -ForegroundColor Yellow
        exit 0
    }
    else {
        Write-Host 'Scan completed successfully - no issues found!' -ForegroundColor Green
        exit 0
    }
}
elseif ($DiagnoseLog) {
    # Diagnose game errors from Debug.log
    Write-Host '============================================================' -ForegroundColor Cyan
    Write-Host '  Transcendence Debug.log Error Diagnostics' -ForegroundColor Cyan
    Write-Host '============================================================' -ForegroundColor Cyan
    Write-Host ''
    
    $diagResult = Get-DebugLogDiagnostics -MaxRecent $MaxErrors
    
    if (-not $diagResult.Success) {
        Write-Host "ERROR: $($diagResult.Error)" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "Scanned: $($diagResult.LogPath)" -ForegroundColor Gray
    Write-Host "Entity database: $($diagResult.EntityDatabaseSize) known entities" -ForegroundColor Gray
    Write-Host "Found: $($diagResult.TotalErrors) error(s)" -ForegroundColor $(if ($diagResult.TotalErrors -gt 0) { 'Yellow' } else { 'Green' })
    Write-Host ''
    
    if ($diagResult.Diagnostics.Count -eq 0) {
        Write-Host 'No errors found in Debug.log!' -ForegroundColor Green
        exit 0
    }
    
    foreach ($diag in $diagResult.Diagnostics) {
        $errEntry = $diag.Error
        
        Write-Host '------------------------------------------------------------' -ForegroundColor DarkGray
        Write-Host "[$($errEntry.Type)]" -ForegroundColor Red -NoNewline
        if ($errEntry.Timestamp) {
            Write-Host " @ $($errEntry.Timestamp)" -ForegroundColor DarkGray
        }
        else {
            Write-Host ''
        }
        
        if ($errEntry.Type -eq 'INVALID_ENTITY') {
            $d = $errEntry.Details
            Write-Host "  File: $($d.FilePath)" -ForegroundColor White
            Write-Host "  Line: $($d.Line)" -ForegroundColor White
            Write-Host "  Entity: &$($d.EntityName);" -ForegroundColor Yellow
            
            if ($diag.Diagnosis) {
                $dx = $diag.Diagnosis
                Write-Host ''
                Write-Host "  Entity Type: $($dx.EntityTypeDescription)" -ForegroundColor Cyan
                
                if ($dx.Suggestions.Count -gt 0) {
                    Write-Host ''
                    Write-Host '  Did you mean:' -ForegroundColor Green
                    foreach ($suggestion in $dx.Suggestions) {
                        $distance = if ($suggestion.Distance -le 1) { '(very similar)' } 
                                    elseif ($suggestion.Distance -le 2) { '(similar)' } 
                                    else { '' }
                        Write-Host "    - &$($suggestion.EntityName); $distance" -ForegroundColor White
                        Write-Host "      From: $(Split-Path -Leaf $suggestion.File)" -ForegroundColor DarkGray
                    }
                }
                
                Write-Host ''
                Write-Host '  How to fix:' -ForegroundColor Magenta
                foreach ($step in $dx.FixSteps) {
                    Write-Host "    $step" -ForegroundColor White
                }
            }
        }
        elseif ($errEntry.Type -eq 'PARSE_ERROR') {
            $d = $errEntry.Details
            Write-Host "  File: $($d.FilePath)" -ForegroundColor White
            Write-Host "  Line: $($d.Line)" -ForegroundColor White
            Write-Host "  Error: $($d.Message)" -ForegroundColor Yellow
            
            # Try to match against known error patterns
            $parsed = Parse-ErrorMessage -ErrorText $d.Message
            if ($parsed.Count -gt 0 -and $parsed[0].Code -ne 'UNKNOWN') {
                Write-Host ''
                Write-Host "  Cause: $($parsed[0].Cause)" -ForegroundColor Cyan
                Write-Host "  Solution: $($parsed[0].Solution)" -ForegroundColor Green
            }
        }
        elseif ($errEntry.Type -eq 'EXTENSION_LOAD_FAILED') {
            Write-Host "  Extension: $($errEntry.Details.ExtensionPath)" -ForegroundColor Yellow
            Write-Host "  This extension failed to load. Check the errors above for details." -ForegroundColor Gray
        }
        
        Write-Host ''
    }
    
    Write-Host '============================================================' -ForegroundColor Cyan
    Write-Host "Total: $($diagResult.TotalErrors) error(s) diagnosed" -ForegroundColor $(if ($diagResult.TotalErrors -gt 0) { 'Yellow' } else { 'Green' })
    Write-Host ''
    Write-Host 'Tips:' -ForegroundColor Gray
    Write-Host '  - "Invalid entity" means the entity is used but not defined in DOCTYPE' -ForegroundColor Gray
    Write-Host '  - Add missing entities to your DOCTYPE section' -ForegroundColor Gray
    Write-Host '  - Check spelling of entity names carefully' -ForegroundColor Gray
    Write-Host '  - Common prefixes: it=item, sc=ship, st=station, rs=resource' -ForegroundColor Gray
    
    exit 0
}
elseif ($NoGui) {
    Write-Host 'Transcendence Mod Tools - CLI Mode'
    Write-Host 'Use GUI mode for full functionality: pwsh -File TranscendenceModTools.ps1'
    Write-Host ''
    Write-Host 'For auto-scan mode:'
    Write-Host '  pwsh -File TranscendenceModTools.ps1 -AutoScan -Path "path\to\mod"'
    Write-Host ''
    Write-Host 'For Debug.log diagnostics:'
    Write-Host '  pwsh -File TranscendenceModTools.ps1 -DiagnoseLog [-MaxErrors 20]'
}
else {
    Show-MainGui
}


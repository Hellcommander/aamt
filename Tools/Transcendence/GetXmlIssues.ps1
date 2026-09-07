# Standalone Get-XmlIssues function
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
    
    # Stricter validation based on Transcendence's Parser.cpp
    # Key insight: ParsePrologue checks if first char is '<' (line 535-539)
    # "We don't allow any whitespace at the beginning"
    
    # Check 1: File must start with '<' (no BOM check already done above)
    $firstChar = if ($text.Length -gt 0) { $text[0] } else { '' }
    if ($firstChar -ne '<') {
        [void]$issues.Add([PSCustomObject]@{
            File = $FilePath
            Line = 1
            Code = 'FILE_NOT_START_WITH_LT'
            Severity = 'Error'
            Message = "File must start with '<'. Game parser requires '<?XML prologue expected'. Found: '$firstChar'"
            CanFix = $false
        })
    }
    
    # Check 2: Comments/content between XML declaration and DOCTYPE
    # Game parser (line 655-744) expects DOCTYPE after PI close, handles it specially
    $xmlDeclEnd = $text.IndexOf('?>')
    if ($xmlDeclEnd -gt 0) {
        $doctypeStart = $text.IndexOf('<!DOCTYPE', [System.StringComparison]::OrdinalIgnoreCase)
        if ($doctypeStart -gt $xmlDeclEnd) {
            $between = $text.Substring($xmlDeclEnd + 2, $doctypeStart - $xmlDeclEnd - 2).Trim()
            # Remove comments (including multiline) to check for actual content
            $betweenNoComments = $between -replace '(?s)<!--.*?-->', '' -replace '\s', ''
            
            if ($betweenNoComments.Length -gt 0) {
                $lineNum = ($text.Substring(0, $xmlDeclEnd + 2) -split "`n").Count
                [void]$issues.Add([PSCustomObject]@{
                    File = $FilePath
                    Line = $lineNum
                    Code = 'CONTENT_BETWEEN_XML_DECL_AND_DOCTYPE'
                    Severity = 'Error'
                    Message = "Non-whitespace content between XML declaration and DOCTYPE causes 'Expected element open tag' error"
                    CanFix = $false
                })
            }
            elseif ($between -match '<!--') {
                # Comments between <?xml?> and <!DOCTYPE> - game parser may not handle correctly
                $lineNum = ($text.Substring(0, $xmlDeclEnd + 2) -split "`n").Count
                [void]$issues.Add([PSCustomObject]@{
                    File = $FilePath
                    Line = $lineNum
                    Code = 'COMMENT_BETWEEN_XML_DECL_AND_DOCTYPE'
                    Severity = 'Error'
                    Message = "Comment between XML declaration and DOCTYPE causes 'Expected element open tag' error. Move comment inside root element or after DOCTYPE."
                    CanFix = $false
                })
            }
        }
    }
    
    # Check for text/content before root element (after DOCTYPE)
    $doctypeEnd = $text.IndexOf(']>')
    if ($doctypeEnd -gt 0) {
        $afterDoctype = $text.Substring($doctypeEnd + 2).TrimStart()
        # Check if there's non-whitespace before root element
        $rootElementPattern = '<(TranscendenceExtension|TranscendenceAdventure|TranscendenceModule|TranscendenceLibrary|TranscendenceUniverse)'
        $rootMatch = [regex]::Match($afterDoctype, $rootElementPattern)
        
        if ($rootMatch.Success) {
            $beforeRoot = $afterDoctype.Substring(0, $rootMatch.Index).Trim()
            # Check for non-comment content before root
            $beforeRootNoComments = $beforeRoot
            $beforeRootNoComments = $beforeRootNoComments -replace '(?s)<!--.*?-->', ''
            $beforeRootNoComments = $beforeRootNoComments.Trim()
            
            if ($beforeRootNoComments.Length -gt 0) {
                $lineNum = ($text.Substring(0, $doctypeEnd + 2 + $rootMatch.Index) -split "`n").Count
                [void]$issues.Add([PSCustomObject]@{
                    File = $FilePath
                    Line = $lineNum
                    Code = 'CONTENT_BEFORE_ROOT'
                    Severity = 'Error'
                    Message = "Content before root element: '$($beforeRootNoComments.Substring(0, [Math]::Min(50, $beforeRootNoComments.Length)))' - may cause 'Expected element open tag' error"
                    CanFix = $false
                })
            }
        }
        else {
            # No root element found after DOCTYPE
            $lineNum = ($text.Substring(0, $doctypeEnd + 2) -split "`n").Count
            [void]$issues.Add([PSCustomObject]@{
                File = $FilePath
                Line = $lineNum
                Code = 'MISSING_ROOT_ELEMENT'
                Severity = 'Error'
                Message = "No root element found after DOCTYPE - may cause 'Expected element open tag' error"
                CanFix = $false
            })
        }
    }
    
    # Check for root element structure issues
    $rootElementPattern = '<(TranscendenceExtension|TranscendenceAdventure|TranscendenceModule|TranscendenceLibrary|TranscendenceUniverse)(\s[^>]*)?>'
    $rootMatches = [regex]::Matches($text, $rootElementPattern)
    if ($rootMatches.Count -eq 0) {
        [void]$issues.Add([PSCustomObject]@{
            File = $FilePath
            Line = 0
            Code = 'NO_ROOT_ELEMENT'
            Severity = 'Error'
            Message = "No root element found - file must have TranscendenceExtension, TranscendenceAdventure, TranscendenceModule, TranscendenceLibrary, or TranscendenceUniverse"
            CanFix = $false
        })
    }
    elseif ($rootMatches.Count -gt 1) {
        $lineNum = ($text.Substring(0, $rootMatches[1].Index) -split "`n").Count
        [void]$issues.Add([PSCustomObject]@{
            File = $FilePath
            Line = $lineNum
            Code = 'MULTIPLE_ROOT_ELEMENTS'
            Severity = 'Error'
            Message = "Multiple root elements found - XML must have exactly one root element"
            CanFix = $false
        })
    }
    
    # PRE-PARSE: Extract declared entities and check for undeclared entity references
    # This prevents cascading errors when XML parser fails on undeclared entities
    $declaredEntities = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
    $undeclaredEntities = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
    $entityRefsByLine = @{}
    
    # Extract declared entities from DOCTYPE
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
    
    # Extract all entity references from the file
    $entityRefPattern = '&(\w+);'
    $entityRefMatches = [regex]::Matches($text, $entityRefPattern)
    foreach ($match in $entityRefMatches) {
        $entityName = $match.Groups[1].Value
        $lineNum = ($text.Substring(0, $match.Index) -split "`n").Count
        
        if (-not $declaredEntities.Contains($entityName)) {
            [void]$undeclaredEntities.Add($entityName)
            if (-not $entityRefsByLine.ContainsKey($lineNum)) {
                $entityRefsByLine[$lineNum] = [System.Collections.ArrayList]::new()
            }
            [void]$entityRefsByLine[$lineNum].Add($entityName)
        }
    }
    
    # Report undeclared entities BEFORE attempting XML parsing
    # This helps identify the root cause before cascading errors occur
    if ($undeclaredEntities.Count -gt 0) {
        foreach ($lineNum in ($entityRefsByLine.Keys | Sort-Object)) {
            $entitiesOnLine = $entityRefsByLine[$lineNum] | Select-Object -Unique
            foreach ($entityName in $entitiesOnLine) {
                [void]$issues.Add([PSCustomObject]@{
                    File = $FilePath
                    Line = $lineNum
                    Code = 'ENTITY_UNDECLARED'
                    Severity = 'Error'
                    Message = "Entity '&$entityName;' is not declared in DOCTYPE (may be from base game or another mod)"
                    CanFix = $false
                    IsCascadingCause = $true
                })
            }
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
        
        # Check if this error is caused by an undeclared entity
        $isUndeclaredEntityError = $errorMsg -match "undeclared entity|Reference to undeclared entity"
        $isCascading = $isUndeclaredEntityError -and $undeclaredEntities.Count -gt 0
        
        [void]$issues.Add([PSCustomObject]@{
            File = $FilePath
            Line = $lineNum
            Code = 'XML_WELLFORMED_ERROR'
            Severity = 'Error'
            Message = "XML parsing error: $errorMsg" + $(if ($isCascading) { " [CAUSED BY UNDECLARED ENTITY - fix entities first to see real structural errors]" } else { "" })
            CanFix = $false
            IsCascadingCause = $isCascading
        })
    }
    
    # If we had undeclared entities and XML parsing failed, mark subsequent structural checks as potentially cascading
    if ($undeclaredEntities.Count -gt 0) {
        # Find the first XML_WELLFORMED_ERROR
        $hasParsingError = $issues | Where-Object { $_.Code -eq 'XML_WELLFORMED_ERROR' } | Select-Object -First 1
        if ($hasParsingError) {
            # Mark that subsequent errors may be cascading
            $script:HasUndeclaredEntities = $true
            $script:UndeclaredEntityErrorLine = $hasParsingError.Line
        }
    }
    
    return $issues
}


<#
.SYNOPSIS
  Transcendence TLisp/XML Checker (GUI + CLI).

.DESCRIPTION
  Transcendence uses a custom XML parser (XMLUtil). It has a few non-standard behaviors that
  make some perfectly-valid XML files fail to load in-game, especially when embedding CodeChain
  (TLisp) scripts inside XML.

  This tool scans one XML file or a folder of XML files and reports:
    - Standard XML well-formedness errors (mismatched tags, etc.) via .NET XmlReader
    - Transcendence XMLUtil quirks (from TranscendenceDev-integration-API57/Alchemy/XMLUtil/Parser.cpp):
        * Any literal '>' in element content will be tokenized as tkTagClose and cause
          "content expected" at runtime. Fix: replace with '&gt;'.
        * UTF-8 BOM or leading whitespace before the first '<' can cause "prologue expected".
    - DOCTYPE internal subset mistakes:
        * Lines starting with ';' inside the <!DOCTYPE ... [ ... ]> block (these are TLisp comments,
          not valid DTD syntax).
    - Suspicious TLisp patterns that frequently create accidental nested XML:
        * (xmlCreate "<Tag>...</Tag>")  (raw '<'/'>' inside a string literal)

  Optional "safe auto-fix" (with .bak backups):
    - Remove UTF-8 BOM and trim leading whitespace before first '<'
    - Escape raw '>' in element content to '&gt;'
    - Escape '<' and '>' inside xmlCreate string literals to '&lt;' and '&gt;'

.NOTES
  Designed for Windows + PowerShell 7+. Uses WinForms for a minimal GUI.
  CLI mode is available with -NoGui.

.EXAMPLE
  # GUI
  pwsh -NoProfile -ExecutionPolicy Bypass -File .\Tools\TranscendenceTlispXmlChecker.ps1

.EXAMPLE
  # CLI scan a folder recursively
  pwsh -NoProfile -ExecutionPolicy Bypass -File .\Tools\TranscendenceTlispXmlChecker.ps1 -NoGui -Path . -Recurse
#>

[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [string]$Path,

    [switch]$Recurse,

    [switch]$NoGui,

    # Filter by severity: All, Error, Warning, Info
    [ValidateSet('All', 'Error', 'Warning', 'Info')]
    [string]$Severity = 'All',

    # Export report to file (CSV or TXT)
    [string]$ExportPath,

    # Detailed output (show all checked files and fix hints)
    [switch]$Detailed,

    # Skip specific check codes (comma-separated)
    [string]$SkipCodes,

    # Only run specific check codes (comma-separated)
    [string]$OnlyCodes,

    # API version to use (auto-detected if not specified)
    [int]$ApiVersion = 0
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# ============================================================
# API VERSION DETECTION AND RULES LOADING
# ============================================================

$script:ToolsRoot = $PSScriptRoot
$script:ApiRules = $null
$script:DetectedApiVersion = 0

function Get-ApiVersionFromMod {
    <#
    .SYNOPSIS
      Detects API version from mod XML files, .tdb files, or mod folders
    #>
    param([Parameter(Mandatory)][string]$ModPath)

    $apiVersions = @()
    
    # Check if it's a file or directory
    if (Test-Path $ModPath -PathType Leaf) {
        $item = Get-Item $ModPath
        $extension = $item.Extension.ToLowerInvariant()
        
        # Handle .tdb files (compiled Transcendence extensions)
        if ($extension -eq '.tdb') {
            # TDB files are binary, but we can try to extract metadata
            # Some TDB files may have XML-like headers or metadata
            try {
                $bytes = [System.IO.File]::ReadAllBytes($ModPath)
                $text = [System.Text.Encoding]::UTF8.GetString($bytes)
                
                # Look for apiVersion in the binary data (might be stored as text)
                if ($text -match 'apiVersion["\s=]+(\d+)') {
                    $version = [int]$matches[1]
                    if ($version -gt 0) {
                        $apiVersions += $version
                    }
                }
                
                # Also check for ASCII strings that might contain version info
                # TDB files sometimes have readable metadata sections
                if ($text -match 'TranscendenceExtension[^>]*apiVersion["\s=]+(\d+)') {
                    $version = [int]$matches[1]
                    if ($version -gt 0) {
                        $apiVersions += $version
                    }
                }
            }
            catch {
                # TDB is binary, can't read as text - that's okay
            }
            
            # If TDB file, also check for associated XML source files in same directory
            $tdbDir = $item.DirectoryName
            $baseName = [System.IO.Path]::GetFileNameWithoutExtension($item.Name)
            $xmlFiles = @(
                Join-Path $tdbDir "$baseName.xml",
                Join-Path $tdbDir "*.xml"
            )
            
            foreach ($xmlPattern in $xmlFiles) {
                $found = Get-ChildItem -LiteralPath $xmlPattern -ErrorAction SilentlyContinue | Select-Object -First 5
                foreach ($xmlFile in $found) {
                    try {
                        $content = Get-Content $xmlFile.FullName -Raw -ErrorAction SilentlyContinue
                        if ($content -match 'apiVersion\s*=\s*["\x27](\d+)["\x27]') {
                            $version = [int]$matches[1]
                            if ($version -gt 0) {
                                $apiVersions += $version
                            }
                        }
                    }
                    catch { }
                }
            }
        }
        else {
            # Regular XML file
            $files = @($ModPath)
        }
    }
    else {
        # Directory - search for XML files
        $searchDir = $ModPath
        $files = Get-ChildItem -LiteralPath $ModPath -Filter *.xml -Recurse -ErrorAction SilentlyContinue | Select-Object -First 100 -ExpandProperty FullName
        
        # Also check for .tdb files in the directory
        $tdbFiles = Get-ChildItem -LiteralPath $ModPath -Filter *.tdb -Recurse -ErrorAction SilentlyContinue | Select-Object -First 10
        foreach ($tdbFile in $tdbFiles) {
            try {
                $bytes = [System.IO.File]::ReadAllBytes($tdbFile.FullName)
                $text = [System.Text.Encoding]::UTF8.GetString($bytes)
                if ($text -match 'apiVersion["\s=]+(\d+)') {
                    $version = [int]$matches[1]
                    if ($version -gt 0) {
                        $apiVersions += $version
                    }
                }
            }
            catch { }
        }
    }

    # Process XML files
    if ($files) {
        foreach ($file in $files) {
            if (-not (Test-Path $file)) { continue }
            
            try {
                $content = Get-Content $file -Raw -ErrorAction SilentlyContinue
                if (-not $content) { continue }
                
                # Look for apiVersion attribute in TranscendenceExtension, TranscendenceLibrary, or TranscendenceModule
                if ($content -match 'apiVersion\s*=\s*["\x27](\d+)["\x27]') {
                    $version = [int]$matches[1]
                    if ($version -gt 0) {
                        $apiVersions += $version
                    }
                }
            }
            catch {
                # Skip files that can't be read
                continue
            }
        }
    }

    if ($apiVersions.Count -gt 0) {
        # Return the most common version (or highest if tie)
        $grouped = $apiVersions | Group-Object | Sort-Object Count -Descending
        return [int]$grouped[0].Name
    }

    return 0
}

function Load-ApiRules {
    <#
    .SYNOPSIS
      Loads API rules for the specified version
    #>
    param([int]$Version)

    if ($Version -eq 0) { return $null }

    $rulesPath = Join-Path $script:ToolsRoot "api_rules_$Version.json"
    if (-not (Test-Path $rulesPath)) {
        $rulesPath = Join-Path $script:ToolsRoot "api_rules.json"
    }

    if (-not (Test-Path $rulesPath)) {
        Write-Warning "API rules file not found for version $Version. Run GenerateApiRules.ps1 first."
        return $null
    }

    try {
        $rules = Get-Content $rulesPath -Raw | ConvertFrom-Json
        return $rules
    }
    catch {
        Write-Warning "Failed to load API rules: $_"
        return $null
    }
}

# Detect API version from path if provided and not explicitly set
if ($Path -and $ApiVersion -eq 0) {
    $detected = Get-ApiVersionFromMod -ModPath $Path
    if ($detected -gt 0) {
        $script:DetectedApiVersion = $detected
        $script:ApiRules = Load-ApiRules -Version $detected
        if ($script:ApiRules) {
            Write-Host "Detected API version: $detected" -ForegroundColor Cyan
            Write-Host "Loaded API rules: $($script:ApiRules.Functions.PSObject.Properties.Count) functions, $($script:ApiRules.Tags.PSObject.Properties.Count) tags" -ForegroundColor Gray
        }
    }
}
elseif ($ApiVersion -gt 0) {
    $script:DetectedApiVersion = $ApiVersion
    $script:ApiRules = Load-ApiRules -Version $ApiVersion
    if ($script:ApiRules) {
        Write-Host "Using API version: $ApiVersion" -ForegroundColor Cyan
    }
}

function New-Issue {
    param(
        [Parameter(Mandatory)] [string]$File,
        [Parameter(Mandatory)] [ValidateSet('Error','Warning','Info')] [string]$Severity,
        [Parameter(Mandatory)] [string]$Code,
        [Parameter(Mandatory)] [string]$Message,
        [int]$Line = 0,
        [int]$Column = 0,
        [string]$Context = '',
        [bool]$Fixable = $false,
        [string]$FixHint = ''
    )

    [pscustomobject]@{
        File     = $File
        Severity = $Severity
        Code     = $Code
        Line     = $Line
        Column   = $Column
        Message  = $Message
        Context  = $Context
        Fixable  = $Fixable
        FixHint  = $FixHint
    }
}

function Get-XmlReaderSettings {
    $settings = [System.Xml.XmlReaderSettings]::new()
    $settings.DtdProcessing = [System.Xml.DtdProcessing]::Parse
    $settings.XmlResolver = [System.Xml.XmlUrlResolver]::new()
    $settings.IgnoreComments = $false
    $settings.IgnoreWhitespace = $false
    return $settings
}

function Get-XmlWellFormedIssues {
    param([Parameter(Mandatory)][string]$FilePath)

    $issues = @()
    try {
        $settings = Get-XmlReaderSettings
        $reader = [System.Xml.XmlReader]::Create($FilePath, $settings)
        try {
            while ($reader.Read()) { }
        }
        finally {
            $reader.Dispose()
        }
    }
    catch [System.Xml.XmlException] {
        $issues += New-Issue -File $FilePath -Severity Error -Code 'XML_WELLFORMED' `
            -Line $_.Exception.LineNumber -Column $_.Exception.LinePosition `
            -Message $_.Exception.Message -Fixable $false
    }
    catch {
        $issues += New-Issue -File $FilePath -Severity Error -Code 'XML_READ' `
            -Message $_.Exception.Message -Fixable $false
    }

    return $issues
}

function Get-FileEncodingIssues {
    param([Parameter(Mandatory)][string]$FilePath)

    $issues = @()
    $bytes = [System.IO.File]::ReadAllBytes($FilePath)
    if ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) {
        $issues += New-Issue -File $FilePath -Severity Error -Code 'ENGINE_UTF8_BOM' `
            -Message 'UTF-8 BOM detected. Transcendence XMLUtil may treat the BOM as a non-< leading character and fail parsing.' `
            -Fixable $true -FixHint 'Remove BOM (write UTF-8 without BOM).'
    }
    elseif ($bytes.Length -ge 2 -and (($bytes[0] -eq 0xFF -and $bytes[1] -eq 0xFE) -or ($bytes[0] -eq 0xFE -and $bytes[1] -eq 0xFF))) {
        $issues += New-Issue -File $FilePath -Severity Warning -Code 'ENGINE_UTF16_BOM' `
            -Message 'UTF-16 BOM detected. Most Transcendence extensions are expected to be UTF-8 (matching the XML header).' `
            -Fixable $false
    }

    # Leading whitespace before first '<'
    $i = 0
    while ($i -lt $bytes.Length) {
        $b = $bytes[$i]
        # ASCII whitespace only for this heuristic
        if ($b -eq 0x20 -or $b -eq 0x09 -or $b -eq 0x0D -or $b -eq 0x0A) { $i++; continue }
        break
    }
    if ($i -lt $bytes.Length -and $bytes[$i] -ne [byte][char]'<' ) {
        $issues += New-Issue -File $FilePath -Severity Error -Code 'ENGINE_LEADING_NON_LT' `
            -Message 'Leading characters before the first "<". Transcendence XMLUtil ParsePrologue expects the first character to be "<".' `
            -Fixable $true -FixHint 'Remove leading whitespace/BOM before the XML prologue.'
    }

    return $issues
}

function Get-DoctypeSemicolonCommentIssues {
    param([Parameter(Mandatory)][string]$FilePath)

    $issues = @()
    $lines = [System.IO.File]::ReadAllLines($FilePath)
    $inDoctype = $false
    $inXmlComment = $false
    for ($i = 0; $i -lt $lines.Length; $i++) {
        $line = $lines[$i]
        if (-not $inDoctype) {
            if ($line -match '<!DOCTYPE') { $inDoctype = $true; $inXmlComment = $false }
        }
        else {
            # Track XML comments inside DOCTYPE (these are valid)
            if ($line -match '<!--') { $inXmlComment = $true }
            if ($inXmlComment -and $line -match '-->') { $inXmlComment = $false; continue }
            
            if ($line -match ']>') { $inDoctype = $false; $inXmlComment = $false; continue }
            
            # Only flag semicolon comments if NOT inside an XML comment
            if (-not $inXmlComment -and $line -match '^\s*;') {
                $issues += New-Issue -File $FilePath -Severity Error -Code 'DTD_TLISP_COMMENT' `
                    -Line ($i + 1) -Column 1 `
                    -Message 'Found a TLisp-style semicolon comment inside the DOCTYPE internal subset. This is not valid DTD syntax. Use XML comments (<!-- -->) instead.' `
                    -Context $line.Trim() -Fixable $false
            }
        }
    }
    return $issues
}

function Get-LineSnippetAtIndex {
    param(
        [Parameter(Mandatory)][string]$Text,
        [Parameter(Mandatory)][int]$Index
    )
    if ($Index -lt 0) { return '' }
    if ($Index -ge $Text.Length) { return '' }

    $start = $Index
    while ($start -gt 0 -and $Text[$start - 1] -ne "`n") { $start-- }
    $end = $Index
    while ($end -lt $Text.Length -and $Text[$end] -ne "`n") { $end++ }

    $line = $Text.Substring($start, $end - $start)
    return $line.TrimEnd("`r")
}

function Get-EngineRawGreaterThanIssues {
    <#
    Detects literal '>' in element content (outside tags/comments/CDATA/DOCTYPE).
    This is invalid for Transcendence XMLUtil because ContentState treats '>' as tkTagClose.
    #>
    param([Parameter(Mandatory)][string]$FilePath)

    $issues = @()
    $text = [System.IO.File]::ReadAllText($FilePath, [System.Text.Encoding]::UTF8)

    $state = 'Outside'  # Outside, Tag, Comment, CData, PI, Doctype
    $tagQuote = [char]0
    $doctypeQuote = [char]0
    $doctypeBracketDepth = 0

    $line = 1
    $col = 0

    $i = 0
    while ($i -lt $text.Length) {
        $ch = $text[$i]

        if ($ch -eq "`n") { $line++; $col = 0 } else { $col++ }

        switch ($state) {
            'Outside' {
                if ($ch -eq '<') {
                    if ($i + 3 -lt $text.Length -and $text.Substring($i, 4) -eq '<!--') {
                        $state = 'Comment'
                        $i += 3
                        $col += 3
                    }
                    elseif ($i + 8 -lt $text.Length -and $text.Substring($i, 9) -eq '<![CDATA[') {
                        $state = 'CData'
                        $i += 8
                        $col += 8
                    }
                    elseif ($i + 1 -lt $text.Length -and $text.Substring($i, 2) -eq '<?') {
                        $state = 'PI'
                        $i += 1
                        $col += 1
                    }
                    elseif ($i + 8 -lt $text.Length -and $text.Substring($i, 9).ToUpperInvariant() -eq '<!DOCTYPE') {
                        $state = 'Doctype'
                        $doctypeBracketDepth = 0
                        $doctypeQuote = [char]0
                        $i += 8
                        $col += 8
                    }
                    else {
                        $state = 'Tag'
                        $tagQuote = [char]0
                    }
                }
                elseif ($ch -eq '>') {
                    $issues += New-Issue -File $FilePath -Severity Error -Code 'ENGINE_RAW_GT' `
                        -Line $line -Column $col `
                        -Message "Literal '>' in element content. Transcendence XMLUtil will throw 'content expected'." `
                        -Context (Get-LineSnippetAtIndex -Text $text -Index $i) `
                        -Fixable $true -FixHint "Replace with '&gt;' (or avoid '>' in TLisp comments/strings)."
                }
            }

            'Tag' {
                if ($tagQuote -ne [char]0) {
                    if ($ch -eq $tagQuote) { $tagQuote = [char]0 }
                }
                else {
                    if ($ch -eq '"' -or $ch -eq "'") { $tagQuote = $ch }
                    elseif ($ch -eq '>') { $state = 'Outside' }
                }
            }

            'Comment' {
                if ($ch -eq '>' -and $i -ge 2 -and $text.Substring($i - 2, 3) -eq '-->') {
                    $state = 'Outside'
                }
            }

            'CData' {
                if ($ch -eq '>' -and $i -ge 2 -and $text.Substring($i - 2, 3) -eq ']]>') {
                    $state = 'Outside'
                }
            }

            'PI' {
                if ($ch -eq '>' -and $i -ge 1 -and $text.Substring($i - 1, 2) -eq '?>') {
                    $state = 'Outside'
                }
            }

            'Doctype' {
                if ($doctypeQuote -ne [char]0) {
                    if ($ch -eq $doctypeQuote) { $doctypeQuote = [char]0 }
                }
                else {
                    if ($ch -eq '"' -or $ch -eq "'") { $doctypeQuote = $ch }
                    elseif ($ch -eq '[') { $doctypeBracketDepth++ }
                    elseif ($ch -eq ']') { if ($doctypeBracketDepth -gt 0) { $doctypeBracketDepth-- } }
                    elseif ($ch -eq '>' -and $doctypeBracketDepth -eq 0) { $state = 'Outside' }
                }
            }
        }

        $i++
    }

    return $issues
}

function Get-XmlCreateRawTagInStringIssues {
    param([Parameter(Mandatory)][string]$FilePath)

    $issues = @()
    $text = [System.IO.File]::ReadAllText($FilePath, [System.Text.Encoding]::UTF8)

    # NOTE: PowerShell single-quoted strings do not treat backslash as an escape, so we use
    # normal .NET regex syntax (\s, \(, etc.) with single backslashes.
    $re = [regex]::new('xmlCreate\s*\(?\s*"<', [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
    $matches = $re.Matches($text)
    foreach ($m in $matches) {
        $idx = $m.Index
        $before = $text.Substring(0, $idx)
        $line = ([regex]::Matches($before, "\n")).Count + 1
        $lastNl = $before.LastIndexOf("`n")
        $col = $idx - $lastNl
        if ($lastNl -lt 0) { $col = $idx + 1 }

        $issues += New-Issue -File $FilePath -Severity Warning -Code 'TLISP_XMLCREATE_RAW_TAG' `
            -Line $line -Column $col `
            -Message 'xmlCreate string literal begins with "<". This will create nested XML unless you escape it as &lt;...&gt;.' `
            -Context (Get-LineSnippetAtIndex -Text $text -Index $idx) `
            -Fixable $true -FixHint 'Escape < and > inside the string: &lt;Tag&gt;...&lt;/Tag&gt;'
    }

    return $issues
}

function Get-TlispSyntaxIssues {
    param([Parameter(Mandatory)][string]$FilePath)

    $issues = @()
    $text = [System.IO.File]::ReadAllText($FilePath, [System.Text.Encoding]::UTF8)
    $lines = [System.IO.File]::ReadAllLines($FilePath)

    # Check for invalid symbol literal syntax: 'symbol' (trailing quote)
    # Valid: 'symbol, Invalid: 'symbol'
    $re = [regex]::new("'([a-zA-Z_][a-zA-Z0-9_]*)'", [System.Text.RegularExpressions.RegexOptions]::None)
    $matches = $re.Matches($text)
    foreach ($m in $matches) {
        $idx = $m.Index
        $before = $text.Substring(0, $idx)
        $line = ([regex]::Matches($before, "`n")).Count + 1
        $lastNl = $before.LastIndexOf("`n")
        $col = if ($lastNl -lt 0) { $idx + 1 } else { $idx - $lastNl }

        # Skip if inside a string literal or comment
        $context = Get-LineSnippetAtIndex -Text $text -Index $idx
        if ($context -match '"[^"]*' -or $context -match ";[^`n]*") { continue }

        $issues += New-Issue -File $FilePath -Severity Error -Code 'TLISP_INVALID_SYMBOL_LITERAL' `
            -Line $line -Column $col `
            -Message "Invalid TLisp symbol literal syntax: '$($m.Groups[1].Value)'. Symbol literals use a leading quote only (e.g., 'symbol, not 'symbol')." `
            -Context $context `
            -Fixable $true -FixHint "Remove trailing quote: '$($m.Groups[1].Value)' -> '$($m.Groups[1].Value)"
    }

    return $issues
}

function Get-ParenthesesBalanceIssues {
    param([Parameter(Mandatory)][string]$FilePath)

    $issues = @()
    $text = [System.IO.File]::ReadAllText($FilePath, [System.Text.Encoding]::UTF8)
    $lines = [System.IO.File]::ReadAllLines($FilePath)

    # Only check inside <Globals>, <Events>, <OnCreate>, etc. (TLisp code blocks)
    # Use a simpler pattern: any tag starting with On or Globals/Events
    $inTlispBlock = $false
    $blockStartLine = 0
    $blockName = ''
    $openCount = 0
    $closeCount = 0
    $lineNum = 0

    foreach ($line in $lines) {
        $lineNum++
        
        # Detect TLisp code blocks (simplified: On* events, Globals, Events)
        if ($line -match '<(Globals|Events|On\w+)') {
            $inTlispBlock = $true
            $blockStartLine = $lineNum
            $blockName = $matches[1]
            $openCount = 0
            $closeCount = 0
        }
        elseif ($inTlispBlock) {
            if ($line -match "</$blockName>") {
                $inTlispBlock = $false
                $diff = $openCount - $closeCount
                if ($diff -ne 0) {
                    $issues += New-Issue -File $FilePath -Severity Error -Code 'TLISP_PARENS_UNBALANCED' `
                        -Line $blockStartLine -Column 1 `
                        -Message "Unbalanced parentheses in <$blockName> block: $diff more opening '(' than closing ')'." `
                        -Context "<$blockName>...</$blockName>" `
                        -Fixable $false
                }
            }
            else {
                # Count parentheses (simple count, doesn't handle strings perfectly but good enough)
                $openCount += ([regex]::Matches($line, '\(')).Count
                $closeCount += ([regex]::Matches($line, '\)')).Count
            }
        }
    }

    return $issues
}

function Get-UnidIssues {
    <#
    Checks for UNID-related issues:
    - Invalid UNID format (should be 0x followed by 8 hex digits)
    - Duplicate UNID definitions within the same file
    - Reserved UNID ranges being used
    #>
    param([Parameter(Mandatory)][string]$FilePath)

    $issues = @()
    $text = [System.IO.File]::ReadAllText($FilePath, [System.Text.Encoding]::UTF8)
    $lines = [System.IO.File]::ReadAllLines($FilePath)

    # Find all UNID definitions in DOCTYPE entities
    $unidDefs = @{}
    $entityRe = [regex]::new('<!ENTITY\s+(\w+)\s+"(0x[0-9A-Fa-f]+)"', [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
    $matches = $entityRe.Matches($text)
    
    foreach ($m in $matches) {
        $entityName = $m.Groups[1].Value
        $unidValue = $m.Groups[2].Value
        $idx = $m.Index
        $before = $text.Substring(0, $idx)
        $line = ([regex]::Matches($before, "`n")).Count + 1

        # Check UNID format (should be 0x + 8 hex digits)
        if ($unidValue -notmatch '^0x[0-9A-Fa-f]{8}$') {
            $issues += New-Issue -File $FilePath -Severity Warning -Code 'UNID_FORMAT' `
                -Line $line -Column 1 `
                -Message "UNID '$unidValue' for entity '$entityName' may be malformed. Standard format is 0x followed by 8 hex digits." `
                -Context $m.Value `
                -Fixable $false
        }

        # Check for duplicates
        $unidLower = $unidValue.ToLowerInvariant()
        if ($unidDefs.ContainsKey($unidLower)) {
            $issues += New-Issue -File $FilePath -Severity Error -Code 'UNID_DUPLICATE' `
                -Line $line -Column 1 `
                -Message "Duplicate UNID '$unidValue' defined for entity '$entityName'. Previously defined for '$($unidDefs[$unidLower])'." `
                -Context $m.Value `
                -Fixable $false
        }
        else {
            $unidDefs[$unidLower] = $entityName
        }

        # Check for reserved ranges
        # Base game uses 0x00000001-0x000FFFFF (reserved range)
        # Mods should use 0xD0000000-0xEFFFFFFF (user UNID range)
        # If UNID is in reserved range (0x00000001-0x000FFFFF), it's either:
        #   1. A base game entity reference (correct - must use actual UNID from base game source)
        #   2. A mod incorrectly using reserved range (mod author's responsibility)
        # We don't warn about reserved range UNIDs - they're either correct base game references
        # or the mod author's issue. The base game source files contain the actual UNID values.
        # Only check if mod UNIDs (0xD0000000-0xEFFFFFFF) are being used correctly
        $unidNum = [Convert]::ToUInt32($unidValue, 16)
        $high16Bits = ($unidNum -shr 16) -band 0xFFFF
        
        # Mods should use 0xD000-0xEFFF range. If they're using reserved range, that's their issue.
        # We don't warn because base game entities MUST use their actual UNIDs from the reserved range.
        # No warning needed - reserved range UNIDs are either correct (base game) or mod author's responsibility.
    }

    return $issues
}

function Get-DeprecatedApiFunctionIssues {
    <#
    Checks for deprecated or changed API functions (especially for API 57 migration).
    Uses API rules if available for version-specific deprecations.
    #>
    param([Parameter(Mandatory)][string]$FilePath)

    $issues = @()
    $text = [System.IO.File]::ReadAllText($FilePath, [System.Text.Encoding]::UTF8)

    # Base deprecated/changed functions (API 57+)
    # Note: objGetItems is NOT deprecated in API 57 - it's still the correct function to use
    $deprecatedFunctions = @{
        'objGetArmorType' = @{ replacement = 'objGetProperty ... ''armorClass'; severity = 'Warning' }
        'objSetItemProperty' = @{ replacement = 'itmSetProperty'; severity = 'Warning' }
        'shpGetDirection' = @{ replacement = 'objGetProperty ... ''rotation'; severity = 'Warning' }
        'shpSetController' = @{ replacement = 'objSetProperty ... ''controller'; severity = 'Warning' }
        'sysGetNodes' = @{ replacement = 'unvGetTopologyNodes'; severity = 'Warning' }
        'staGetDockedShips' = @{ replacement = 'objGetProperty ... ''dockedShips'; severity = 'Warning' }
        'objGetObjRefData' = @{ replacement = 'objGetData with proper type handling'; severity = 'Info' }
        'objSetObjRefData' = @{ replacement = 'objSetData with proper type handling'; severity = 'Info' }
        'itmGetData' = @{ replacement = 'itmGetStaticData or itmGetProperty'; severity = 'Info' }
        'itmSetData' = @{ replacement = 'itmSetStaticData'; severity = 'Info' }
        'typGetData' = @{ replacement = 'typGetStaticData'; severity = 'Info' }
        'typSetData' = @{ replacement = 'typSetStaticData (if appropriate)'; severity = 'Info' }
    }

    # Enhance with deprecated functions from API rules if available
    if ($script:ApiRules -and $script:ApiRules.Deprecated -and $script:ApiRules.Deprecated.Functions) {
        foreach ($depFunc in $script:ApiRules.Deprecated.Functions) {
            if (-not $deprecatedFunctions.ContainsKey($depFunc)) {
                # Add to deprecated list with generic replacement
                $deprecatedFunctions[$depFunc] = @{ 
                    replacement = 'See API documentation for replacement'; 
                    severity = 'Warning' 
                }
            }
        }
    }

    foreach ($func in $deprecatedFunctions.Keys) {
        $pattern = "\($func\s"
        $re = [regex]::new($pattern, [System.Text.RegularExpressions.RegexOptions]::None)
        $matches = $re.Matches($text)
        
        foreach ($m in $matches) {
            $idx = $m.Index
            $before = $text.Substring(0, $idx)
            $line = ([regex]::Matches($before, "`n")).Count + 1
            $lastNl = $before.LastIndexOf("`n")
            $col = if ($lastNl -lt 0) { $idx + 1 } else { $idx - $lastNl }

            $info = $deprecatedFunctions[$func]
            $issues += New-Issue -File $FilePath -Severity $info.severity -Code 'API_DEPRECATED' `
                -Line $line -Column $col `
                -Message "Function '$func' may be deprecated or changed in API 57. Consider using: $($info.replacement)" `
                -Context (Get-LineSnippetAtIndex -Text $text -Index $idx) `
                -Fixable $false
        }
    }

    return $issues
}

function Get-CommonTlispTypoIssues {
    <#
    Checks for common TLisp function name typos.
    #>
    param([Parameter(Mandatory)][string]$FilePath)

    $issues = @()
    $text = [System.IO.File]::ReadAllText($FilePath, [System.Text.Encoding]::UTF8)

    # Common typos and their corrections (case-sensitive matching)
    # Using an array of tuples since PowerShell hashtables are case-insensitive
    $typos = @(
        @('objGetPropert', 'objGetProperty'),
        @('objSetPropert', 'objSetProperty'),
        @('itmGetPropert', 'itmGetProperty'),
        @('itmSetPropert', 'itmSetProperty'),
        @('typGetPropert', 'typGetProperty'),
        @('typSetPropert', 'typSetProperty'),
        @('sysFindobject', 'sysFindObject'),
        @('objFireevent', 'objFireEvent'),
        @('typFireevent', 'typFireEvent'),
        @('objGetdata', 'objGetData'),
        @('objSetdata', 'objSetData'),
        @('objGetname', 'objGetName'),
        @('objSetname', 'objSetName'),
        @('shpgetOrder', 'shpGetOrder'),
        @('shpsetOrder', 'shpOrder'),
        @('greter', 'gr'),
        @('lees', 'ls'),
        @('equall', 'eq'),
        @('substract', 'subtract'),
        @('devide', 'divide'),
        @('multipley', 'multiply'),
        @('concatinate', 'cat'),
        @('lenght', 'count')
    )

    foreach ($typoPair in $typos) {
        $typo = $typoPair[0]
        $correction = $typoPair[1]
        
        $pattern = "\($typo\s"
        $re = [regex]::new($pattern, [System.Text.RegularExpressions.RegexOptions]::None)
        $matches = $re.Matches($text)
        
        foreach ($m in $matches) {
            $idx = $m.Index
            $before = $text.Substring(0, $idx)
            $line = ([regex]::Matches($before, "`n")).Count + 1
            $lastNl = $before.LastIndexOf("`n")
            $col = if ($lastNl -lt 0) { $idx + 1 } else { $idx - $lastNl }

            $issues += New-Issue -File $FilePath -Severity Error -Code 'TLISP_TYPO' `
                -Line $line -Column $col `
                -Message "Possible typo: '$typo' should be '$correction'" `
                -Context (Get-LineSnippetAtIndex -Text $text -Index $idx) `
                -Fixable $true -FixHint "Replace '$typo' with '$correction'"
        }
    }

    return $issues
}

function Get-VanillaDesignTypeMap {
    <#
    Official current UNIDs + old→new type remaps from Remap-VanillaDesignTypes.py.
    #>
    $jsonPath = Join-Path $PSScriptRoot 'VanillaDesignTypeMap.json'
    if (-not (Test-Path -LiteralPath $jsonPath)) {
        return $null
    }
    try {
        return Get-Content -LiteralPath $jsonPath -Raw -Encoding UTF8 | ConvertFrom-Json
    }
    catch {
        return $null
    }
}

function Get-CommonGameEntities {
    <#
    Current official entity UNIDs. Old names (dsLoot, itSolarArmor, …) are rewritten
    to the replacement type's UNID so auto-fix does not re-inject 1.0 design types.
    #>
    $entities = @{}
    $remaps = @{}
    $map = Get-VanillaDesignTypeMap
    if ($null -ne $map -and $null -ne $map.unids) {
        foreach ($prop in $map.unids.PSObject.Properties) {
            $entities[$prop.Name] = [string]$prop.Value
        }
        if ($null -ne $map.nameRemaps) {
            foreach ($prop in $map.nameRemaps.PSObject.Properties) {
                $oldName = $prop.Name
                $newName = [string]$prop.Value
                $remaps[$oldName] = $newName
                if ($entities.ContainsKey($newName)) {
                    $entities[$oldName] = $entities[$newName]
                }
            }
        }
    }

    # Mod-local types that are not in vanilla. Keep as extras only.
    $entities['evD789StorageEvents'] = '0xD78912B6'
    $entities['dsD789StorageRefuseContam'] = '0xD78912B8'
    $entities['dsD789StorageRetrieve'] = '0xD78912B9'
    $entities['dsD789StorageStorage'] = '0xD78912BA'
    $entities['dsD789StorageTransfer'] = '0xD78912BB'
    $entities['dsD789StorageTransferItems'] = '0xD78912BC'

    return @{ Entities = $entities; Remaps = $remaps }
}

function Get-UndefinedEntityIssues {
    <#
    Checks for entity references that are not defined in the DOCTYPE.
    Improved to detect common game entities and suggest fixes.
    Uses API rules if available for better detection.
    #>
    param([Parameter(Mandatory)][string]$FilePath)

    $issues = @()
    $text = [System.IO.File]::ReadAllText($FilePath, [System.Text.Encoding]::UTF8)

    $mapBundle = Get-CommonGameEntities
    $commonEntities = $mapBundle.Entities
    $typeRemaps = $mapBundle.Remaps

    # Collect all defined entities
    $definedEntities = @{}
    $entityDefRe = [regex]::new('<!ENTITY\s+(\w+)\s+', [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
    $defMatches = $entityDefRe.Matches($text)
    foreach ($m in $defMatches) {
        $definedEntities[$m.Groups[1].Value] = $true
    }

    # Standard XML entities
    $standardEntities = @('lt', 'gt', 'amp', 'quot', 'apos')
    foreach ($e in $standardEntities) { $definedEntities[$e] = $true }

    # Check if file references HumanSpaceLibrary (entities might come from there)
    $hasLibrary = $text -match '<Library[^>]*unid="&unidHumanSpaceLibrary;' -or 
                  $text -match '<Library[^>]*unid="0x00100000' -or
                  $text -match 'unidHumanSpaceLibrary'

    # Find all entity references (but not in DOCTYPE section)
    # Also skip entity references within entity definitions themselves
    $doctypeStart = $text.IndexOf('<!DOCTYPE')
    $doctypeEnd = $text.IndexOf(']>')
    if ($doctypeEnd -lt 0) { $doctypeEnd = 0 } else { $doctypeEnd += 2 }
    if ($doctypeStart -lt 0) { $doctypeStart = 0 }

    $contentText = $text.Substring($doctypeEnd)
    $contentOffset = $doctypeEnd

    # Find entity references in content (including attribute values)
    # This regex will match &entityName; anywhere in the content
    $entityRefRe = [regex]::new('&(\w+);', [System.Text.RegularExpressions.RegexOptions]::None)
    $refMatches = $entityRefRe.Matches($contentText)

    $reportedEntities = @{}
    foreach ($m in $refMatches) {
        $entityName = $m.Groups[1].Value
        
        # Skip if already defined or already reported
        if ($definedEntities.ContainsKey($entityName)) { continue }
        if ($reportedEntities.ContainsKey($entityName)) { continue }
        $reportedEntities[$entityName] = $true

        $idx = $m.Index + $contentOffset
        $before = $text.Substring(0, $idx)
        $line = ([regex]::Matches($before, "`n")).Count + 1
        $lastNl = $before.LastIndexOf("`n")
        $col = if ($lastNl -lt 0) { $idx + 1 } else { $idx - $lastNl }

        # Determine severity and message
        $severity = 'Warning'
        $message = "Entity '&$entityName;' is referenced but not defined in this file's DOCTYPE."
        $fixHint = ''
        $fixable = $false

        if ($commonEntities.ContainsKey($entityName)) {
            $unid = $commonEntities[$entityName]
            $severity = 'Error'
            if ($typeRemaps.ContainsKey($entityName)) {
                $newName = $typeRemaps[$entityName]
                $newUnid = if ($commonEntities.ContainsKey($newName)) { $commonEntities[$newName] } else { $unid }
                $message = "Entity '&$entityName;' is an obsolete design type. Use '&$newName;' (UNID: $newUnid)."
                $fixHint = "Replace &$entityName; with &$newName; and add: <!ENTITY $newName `"$newUnid`">"
            }
            else {
                $message = "Entity '&$entityName;' is referenced but not defined. This is a common game entity (UNID: $unid)."
                $fixHint = "Add to DOCTYPE: <!ENTITY $entityName `"$unid`">"
            }
            $fixable = $true
        }
        elseif (-not $hasLibrary) {
            $severity = 'Error'
            $message = "Entity '&$entityName;' is referenced but not defined in this file's DOCTYPE. No library reference found."
            # Check for common typos in entity names
            $possibleTypo = $null
            foreach ($knownEntity in $commonEntities.Keys) {
                # Check if entity name is similar to a known entity (Levenshtein-like, simple check)
                if ($entityName.Length -eq $knownEntity.Length) {
                    $diff = 0
                    for ($i = 0; $i -lt $entityName.Length; $i++) {
                        if ($entityName[$i] -ne $knownEntity[$i]) { $diff++ }
                    }
                    if ($diff -eq 1) {
                        $possibleTypo = $knownEntity
                        break
                    }
                }
            }
            if ($possibleTypo) {
                $unid = $commonEntities[$possibleTypo]
                $fixHint = "Possible typo? Did you mean '$possibleTypo'? If so, add: <!ENTITY $possibleTypo `"$unid`">"
                $message += " Possible typo: did you mean '$possibleTypo'?"
            }
        }
        else {
            $message += " It may be defined in an external file or library."
        }

        $issues += New-Issue -File $FilePath -Severity $severity -Code 'ENTITY_UNDEFINED' `
            -Line $line -Column $col `
            -Message $message `
            -Context (Get-LineSnippetAtIndex -Text $text -Index $idx) `
            -Fixable $fixable -FixHint $fixHint
    }

    return $issues
}

function Get-MismatchedTagIssues {
    <#
    Additional check for mismatched XML tags that may be more specific than XmlReader errors.
    #>
    param([Parameter(Mandatory)][string]$FilePath)

    $issues = @()
    $lines = [System.IO.File]::ReadAllLines($FilePath)

    # Simple tag matching for common Transcendence elements
    $tagStack = [System.Collections.Stack]::new()
    $lineNum = 0

    foreach ($line in $lines) {
        $lineNum++
        
        # Skip DOCTYPE lines
        if ($line -match '<!DOCTYPE' -or $line -match '<!ENTITY' -or $line -match ']>') { continue }

        # Find opening tags (not self-closing)
        $openTagRe = [regex]::new('<(\w+)(?:\s[^>]*)?>(?!.*/>)', [System.Text.RegularExpressions.RegexOptions]::None)
        $openMatches = $openTagRe.Matches($line)
        foreach ($m in $openMatches) {
            if ($line.Contains("</$($m.Groups[1].Value)>")) { continue }  # Same line close
            if ($m.Value.EndsWith('/>')) { continue }  # Self-closing
            $tagStack.Push(@{ Name = $m.Groups[1].Value; Line = $lineNum })
        }

        # Find closing tags
        $closeTagRe = [regex]::new('</(\w+)>', [System.Text.RegularExpressions.RegexOptions]::None)
        $closeMatches = $closeTagRe.Matches($line)
        foreach ($m in $closeMatches) {
            $closeName = $m.Groups[1].Value
            if ($tagStack.Count -eq 0) {
                $issues += New-Issue -File $FilePath -Severity Error -Code 'TAG_UNEXPECTED_CLOSE' `
                    -Line $lineNum -Column 1 `
                    -Message "Unexpected closing tag '</$closeName>' with no matching open tag." `
                    -Context $line.Trim() `
                    -Fixable $false
            }
            else {
                $top = $tagStack.Pop()
                if ($top.Name -ne $closeName) {
                    $issues += New-Issue -File $FilePath -Severity Error -Code 'TAG_MISMATCH' `
                        -Line $lineNum -Column 1 `
                        -Message "Closing tag '</$closeName>' does not match open tag '<$($top.Name)>' from line $($top.Line)." `
                        -Context $line.Trim() `
                        -Fixable $false
                    # Put it back and try to continue
                    $tagStack.Push($top)
                }
            }
        }
    }

    return $issues
}

function Get-IssuesForFile {
    param([Parameter(Mandatory)][string]$FilePath)

    $all = [System.Collections.ArrayList]::new()

    try {
        $result = Get-FileEncodingIssues -FilePath $FilePath
        if ($result) { [void]$all.AddRange(@($result)) }
    } catch { }

    try {
        $result = Get-XmlWellFormedIssues -FilePath $FilePath
        if ($result) { [void]$all.AddRange(@($result)) }
    } catch { }

    try {
        $result = Get-DoctypeSemicolonCommentIssues -FilePath $FilePath
        if ($result) { [void]$all.AddRange(@($result)) }
    } catch { }

    # Engine quirk checks (only if we can read as UTF-8)
    try {
        $result = Get-EngineRawGreaterThanIssues -FilePath $FilePath
        if ($result) { [void]$all.AddRange(@($result)) }
    } catch { }

    try {
        $result = Get-XmlCreateRawTagInStringIssues -FilePath $FilePath
        if ($result) { [void]$all.AddRange(@($result)) }
    } catch { }

    # TLisp-specific checks
    try {
        $result = Get-TlispSyntaxIssues -FilePath $FilePath
        if ($result) { [void]$all.AddRange(@($result)) }
    } catch { }

    try {
        $result = Get-ParenthesesBalanceIssues -FilePath $FilePath
        if ($result) { [void]$all.AddRange(@($result)) }
    } catch { }

    # UNID validation
    try {
        $result = Get-UnidIssues -FilePath $FilePath
        if ($result) { [void]$all.AddRange(@($result)) }
    } catch { }

    # API and typo checks
    try {
        $result = Get-DeprecatedApiFunctionIssues -FilePath $FilePath
        if ($result) { [void]$all.AddRange(@($result)) }
    } catch { }

    try {
        $result = Get-CommonTlispTypoIssues -FilePath $FilePath
        if ($result) { [void]$all.AddRange(@($result)) }
    } catch { }

    # Entity reference checks (warning level - may be defined externally)
    try {
        $result = Get-UndefinedEntityIssues -FilePath $FilePath
        if ($result) { [void]$all.AddRange(@($result)) }
    } catch { }

    return @($all)
}

function Get-XmlFilesFromPath {
    param(
        [Parameter(Mandatory)][string]$InputPath,
        [switch]$Recurse
    )

    if ([string]::IsNullOrWhiteSpace($InputPath)) { return @() }

    try {
        $resolved = Resolve-Path -LiteralPath $InputPath -ErrorAction Stop
        $p = if ($resolved -is [System.Array]) { $resolved[0].Path } else { $resolved.Path }
    }
    catch {
        return @()
    }

    if (Test-Path -LiteralPath $p -PathType Leaf) {
        if ($p.ToLowerInvariant().EndsWith('.xml')) { return @($p) }
        return @()
    }

    if (Test-Path -LiteralPath $p -PathType Container) {
        $opts = @{}
        if ($Recurse) { $opts.Recurse = $true }
        $files = Get-ChildItem -LiteralPath $p -Filter *.xml @opts | ForEach-Object { $_.FullName }
        # Ensure we always return an array, even if only one file
        if ($null -eq $files) { return @() }
        return @($files)
    }

    return @()
}

function Escape-RawGreaterThanInContent {
    param([Parameter(Mandatory)][string]$Text)

    $sb = [System.Text.StringBuilder]::new($Text.Length + 128)
    $state = 'Outside'  # Outside, Tag, Comment, CData, PI, Doctype
    $tagQuote = [char]0
    $doctypeQuote = [char]0
    $doctypeBracketDepth = 0

    $i = 0
    while ($i -lt $Text.Length) {
        $ch = $Text[$i]

        switch ($state) {
            'Outside' {
                if ($ch -eq '<') {
                    if ($i + 3 -lt $Text.Length -and $Text.Substring($i, 4) -eq '<!--') {
                        [void]$sb.Append('<!--')
                        $state = 'Comment'
                        $i += 4
                        continue
                    }
                    elseif ($i + 8 -lt $Text.Length -and $Text.Substring($i, 9) -eq '<![CDATA[') {
                        [void]$sb.Append('<![CDATA[')
                        $state = 'CData'
                        $i += 9
                        continue
                    }
                    elseif ($i + 1 -lt $Text.Length -and $Text.Substring($i, 2) -eq '<?') {
                        [void]$sb.Append('<?')
                        $state = 'PI'
                        $i += 2
                        continue
                    }
                    elseif ($i + 8 -lt $Text.Length -and $Text.Substring($i, 9).ToUpperInvariant() -eq '<!DOCTYPE') {
                        [void]$sb.Append($Text.Substring($i, 9))
                        $state = 'Doctype'
                        $doctypeBracketDepth = 0
                        $doctypeQuote = [char]0
                        $i += 9
                        continue
                    }
                    else {
                        [void]$sb.Append('<')
                        $state = 'Tag'
                        $tagQuote = [char]0
                        $i++
                        continue
                    }
                }
                elseif ($ch -eq '>') {
                    [void]$sb.Append('&gt;')
                    $i++
                    continue
                }
                else {
                    [void]$sb.Append($ch)
                    $i++
                    continue
                }
            }

            'Tag' {
                [void]$sb.Append($ch)
                if ($tagQuote -ne [char]0) {
                    if ($ch -eq $tagQuote) { $tagQuote = [char]0 }
                }
                else {
                    if ($ch -eq '"' -or $ch -eq "'") { $tagQuote = $ch }
                    elseif ($ch -eq '>') { $state = 'Outside' }
                }
                $i++
                continue
            }

            'Comment' {
                [void]$sb.Append($ch)
                if ($ch -eq '>' -and $i -ge 2 -and $Text.Substring($i - 2, 3) -eq '-->') {
                    $state = 'Outside'
                }
                $i++
                continue
            }

            'CData' {
                [void]$sb.Append($ch)
                if ($ch -eq '>' -and $i -ge 2 -and $Text.Substring($i - 2, 3) -eq ']]>') {
                    $state = 'Outside'
                }
                $i++
                continue
            }

            'PI' {
                [void]$sb.Append($ch)
                if ($ch -eq '>' -and $i -ge 1 -and $Text.Substring($i - 1, 2) -eq '?>') {
                    $state = 'Outside'
                }
                $i++
                continue
            }

            'Doctype' {
                [void]$sb.Append($ch)
                if ($doctypeQuote -ne [char]0) {
                    if ($ch -eq $doctypeQuote) { $doctypeQuote = [char]0 }
                }
                else {
                    if ($ch -eq '"' -or $ch -eq "'") { $doctypeQuote = $ch }
                    elseif ($ch -eq '[') { $doctypeBracketDepth++ }
                    elseif ($ch -eq ']') { if ($doctypeBracketDepth -gt 0) { $doctypeBracketDepth-- } }
                    elseif ($ch -eq '>' -and $doctypeBracketDepth -eq 0) { $state = 'Outside' }
                }
                $i++
                continue
            }
        }
    }

    return $sb.ToString()
}

function Escape-XmlCreateStringLiterals {
    param([Parameter(Mandatory)][string]$Text)

    # Finds: xmlCreate  (optional '(')  " ... "
    # Escapes < and > inside that string literal.
    $re = [regex]::new('xmlCreate\s*\(?\s*"', [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
    $sb = [System.Text.StringBuilder]::new($Text.Length + 128)

    $pos = 0
    $matches = $re.Matches($Text)
    foreach ($m in $matches) {
        $start = $m.Index

        # Append everything before match.
        if ($start -gt $pos) { [void]$sb.Append($Text.Substring($pos, $start - $pos)) }

        # Append the match prefix up to and including the opening quote.
        $prefixLen = $m.Length
        [void]$sb.Append($Text.Substring($start, $prefixLen))

        $i = $start + $prefixLen
        $stringStart = $i

        # Find end quote (naive: \" escapes).
        $escaped = $false
        while ($i -lt $Text.Length) {
            $c = $Text[$i]
            if ($escaped) { $escaped = $false; $i++; continue }
            if ($c -eq '\') { $escaped = $true; $i++; continue }
            if ($c -eq '"') { break }
            $i++
        }

        if ($i -ge $Text.Length) {
            # No closing quote found; append the rest and bail.
            [void]$sb.Append($Text.Substring($stringStart))
            $pos = $Text.Length
            break
        }

        $literal = $Text.Substring($stringStart, $i - $stringStart)
        $literal = $literal.Replace('<','&lt;').Replace('>','&gt;')
        [void]$sb.Append($literal)

        # Append closing quote.
        [void]$sb.Append('"')

        $pos = $i + 1
    }

    if ($pos -lt $Text.Length) {
        [void]$sb.Append($Text.Substring($pos))
    }

    return $sb.ToString()
}

function Remove-Utf8BomAndLeadingWhitespace {
    param(
        [Parameter(Mandatory)][byte[]]$Bytes
    )

    $start = 0
    if ($Bytes.Length -ge 3 -and $Bytes[0] -eq 0xEF -and $Bytes[1] -eq 0xBB -and $Bytes[2] -eq 0xBF) {
        $start = 3
    }

    # Only trim ASCII whitespace before first '<' (matches engine prologue rule).
    while ($start -lt $Bytes.Length) {
        $b = $Bytes[$start]
        if ($b -eq 0x20 -or $b -eq 0x09 -or $b -eq 0x0D -or $b -eq 0x0A) { $start++; continue }
        break
    }

    if ($start -eq 0) { return $Bytes }
    if ($start -ge $Bytes.Length) { return @() }
    return $Bytes[$start..($Bytes.Length - 1)]
}

function Fix-FileSafe {
    param(
        [Parameter(Mandatory)][string]$FilePath,
        [switch]$Backup,
        [switch]$FixBomAndLeadingWhitespace,
        [switch]$FixRawGreaterThan,
        [switch]$FixXmlCreateStrings
    )

    if ($Backup) {
        $bak = "$FilePath.bak"
        if (-not (Test-Path -LiteralPath $bak)) {
            Copy-Item -LiteralPath $FilePath -Destination $bak -Force
        }
    }

    $bytes = [System.IO.File]::ReadAllBytes($FilePath)
    if ($FixBomAndLeadingWhitespace) {
        $bytes = Remove-Utf8BomAndLeadingWhitespace -Bytes $bytes
    }

    $text = [System.Text.Encoding]::UTF8.GetString($bytes)

    if ($FixXmlCreateStrings) {
        $text = Escape-XmlCreateStringLiterals -Text $text
    }
    if ($FixRawGreaterThan) {
        $text = Escape-RawGreaterThanInContent -Text $text
    }

    $utf8NoBom = [System.Text.UTF8Encoding]::new($false)
    [System.IO.File]::WriteAllText($FilePath, $text, $utf8NoBom)
}

function Run-Cli {
    param(
        [Parameter(Mandatory)][string]$InputPath,
        [switch]$Recurse,
        [string]$SeverityFilter = 'All',
        [string]$ExportPath = '',
        [switch]$VerboseOutput,
        [string]$SkipCodes = '',
        [string]$OnlyCodes = ''
    )

    # Parse skip/only codes - ensure they're always arrays
    $skipCodeList = @()
    if ($SkipCodes) {
        $splitCodes = $SkipCodes -split ','
        foreach ($code in $splitCodes) {
            $trimmed = $code.Trim()
            if ($trimmed) { $skipCodeList += $trimmed }
        }
    }
    $onlyCodeList = @()
    if ($OnlyCodes) {
        $splitCodes = $OnlyCodes -split ','
        foreach ($code in $splitCodes) {
            $trimmed = $code.Trim()
            if ($trimmed) { $onlyCodeList += $trimmed }
        }
    }

    # Ensure we always get an array (PowerShell will otherwise "unwrap" single results).
    $files = @(Get-XmlFilesFromPath -InputPath $InputPath -Recurse:$Recurse)
    # Double-check: ensure $files is always an array
    if ($null -eq $files) { $files = @() }
    if (-not ($files -is [System.Array])) { $files = @($files) }
    if ($files.Count -eq 0) {
        Write-Host "No .xml files found at path: $InputPath" -ForegroundColor Yellow
        return
    }

    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host "Transcendence TLisp/XML Checker" -ForegroundColor Cyan
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host "Scanning $($files.Count) file(s)..." -ForegroundColor White
    if ($SeverityFilter -ne 'All') { Write-Host "Severity filter: $SeverityFilter" -ForegroundColor Gray }
    if ($skipCodeList.Count -gt 0) { Write-Host "Skipping codes: $($skipCodeList -join ', ')" -ForegroundColor Gray }
    if ($onlyCodeList.Count -gt 0) { Write-Host "Only codes: $($onlyCodeList -join ', ')" -ForegroundColor Gray }
    Write-Host ""

    $allIssues = @()
    $fileCount = 0
    $filesWithIssues = 0
    foreach ($f in $files) {
        $fileCount++
        Write-Progress -Activity "Scanning files" -Status "File $fileCount of $($files.Count): $(Split-Path -Leaf $f)" -PercentComplete (($fileCount / $files.Count) * 100)
        
        $fileIssues = @(Get-IssuesForFile -FilePath $f)
        
        if ($VerboseOutput -and $fileIssues.Count -eq 0) {
            Write-Host "  ✓ $(Split-Path -Leaf $f)" -ForegroundColor DarkGray
        }
        
        if ($fileIssues.Count -gt 0) { $filesWithIssues++ }
        $allIssues += $fileIssues
    }
    Write-Progress -Activity "Scanning files" -Completed

    # Apply filters
    $filteredIssues = @($allIssues)
    
    # Severity filter
    if ($SeverityFilter -ne 'All') {
        $filteredIssues = @($filteredIssues | Where-Object { $_.Severity -eq $SeverityFilter })
    }
    
    # Skip codes filter
    if ($skipCodeList.Count -gt 0) {
        $filteredIssues = @($filteredIssues | Where-Object { $_.Code -notin $skipCodeList })
    }
    
    # Only codes filter
    if ($onlyCodeList.Count -gt 0) {
        $filteredIssues = @($filteredIssues | Where-Object { $_.Code -in $onlyCodeList })
    }

    # Export to file if requested
    if ($ExportPath) {
        $exportDir = Split-Path -Parent $ExportPath
        if ($exportDir -and -not (Test-Path $exportDir)) {
            New-Item -ItemType Directory -Path $exportDir -Force | Out-Null
        }
        
        if ($ExportPath.EndsWith('.csv')) {
            $filteredIssues | Select-Object Severity, Code, Line, Column, Message, File, Context, Fixable, FixHint |
                Export-Csv -Path $ExportPath -NoTypeInformation -Encoding UTF8
            Write-Host "Report exported to: $ExportPath" -ForegroundColor Green
        }
        else {
            $lines = @()
            $lines += "Transcendence TLisp/XML Checker Report"
            $lines += "Generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
            $lines += "Path: $InputPath"
            $lines += "Files scanned: $($files.Count)"
            $lines += "============================================================"
            $lines += ""
            
            $byFileExport = @($filteredIssues | Group-Object File)
            foreach ($fileGroup in $byFileExport | Sort-Object Name) {
                $lines += "[$($fileGroup.Name)]"
                foreach ($issue in @($fileGroup.Group) | Sort-Object Line) {
                    $lines += "  [$($issue.Severity)] $($issue.Code) L$($issue.Line):$($issue.Column) $($issue.Message)"
                }
                $lines += ""
            }
            
            $lines += "============================================================"
            $errCnt = @($filteredIssues | Where-Object { $_.Severity -eq 'Error' }).Count
            $warnCnt = @($filteredIssues | Where-Object { $_.Severity -eq 'Warning' }).Count
            $lines += "Summary: $errCnt error(s), $warnCnt warning(s)"
            
            [System.IO.File]::WriteAllLines($ExportPath, $lines)
            Write-Host "Report exported to: $ExportPath" -ForegroundColor Green
        }
    }

    if ($filteredIssues.Count -eq 0) {
        Write-Host "`n✓ No issues found in $($files.Count) file(s)." -ForegroundColor Green
        return
    }

    # Group by file for better readability
    $byFile = @($filteredIssues | Group-Object File)
    $errorCount = @($filteredIssues | Where-Object { $_.Severity -eq 'Error' }).Count
    $warningCount = @($filteredIssues | Where-Object { $_.Severity -eq 'Warning' }).Count
    $infoCount = @($filteredIssues | Where-Object { $_.Severity -eq 'Info' }).Count

    Write-Host "`nFound $($filteredIssues.Count) issue(s) in $($byFile.Count) file(s):" -ForegroundColor Yellow
    Write-Host "  Errors:   $errorCount" -ForegroundColor $(if ($errorCount -gt 0) { 'Red' } else { 'Green' })
    Write-Host "  Warnings: $warningCount" -ForegroundColor $(if ($warningCount -gt 0) { 'Yellow' } else { 'Green' })
    Write-Host "  Info:     $infoCount" -ForegroundColor $(if ($infoCount -gt 0) { 'Cyan' } else { 'Green' })
    Write-Host ""

    # Group by code for summary
    $byCode = @($filteredIssues | Group-Object Code | Sort-Object Count -Descending)
    if ($byCode.Count -gt 0) {
        Write-Host "Issues by type:" -ForegroundColor Gray
        foreach ($codeGroup in $byCode) {
            Write-Host "  $($codeGroup.Count.ToString().PadLeft(4)) x $($codeGroup.Name)" -ForegroundColor Gray
        }
        Write-Host ""
    }

    foreach ($fileGroup in @($byFile | Sort-Object Name)) {
        $fileName = $fileGroup.Name
        $relativePath = if ($fileName -and $fileName.StartsWith($InputPath)) { 
            $fileName.Substring($InputPath.Length).TrimStart('\', '/') 
        } else { 
            $fileName 
        }
        Write-Host "`n[$relativePath]" -ForegroundColor Cyan
        @($fileGroup.Group) | Sort-Object Line, Column | ForEach-Object {
            $severityColor = switch ($_.Severity) {
                'Error' { 'Red' }
                'Warning' { 'Yellow' }
                'Info' { 'Cyan' }
                default { 'White' }
            }
            $lineInfo = "L$($_.Line):$($_.Column)"
            Write-Host "  [$($_.Severity.PadRight(7))] " -NoNewline -ForegroundColor $severityColor
            Write-Host "$($_.Code.PadRight(25)) " -NoNewline -ForegroundColor DarkGray
            Write-Host "$($lineInfo.PadRight(10)) " -NoNewline -ForegroundColor Gray
            Write-Host $_.Message -ForegroundColor White
            if ($_.FixHint -and $VerboseOutput) {
                Write-Host "           Fix: $($_.FixHint)" -ForegroundColor DarkGreen
            }
        }
    }

    Write-Host "`n============================================================" -ForegroundColor Gray
    Write-Host "Summary: $errorCount error(s), $warningCount warning(s), $infoCount info across $($byFile.Count) file(s)" -ForegroundColor $(if ($errorCount -gt 0) { 'Red' } elseif ($warningCount -gt 0) { 'Yellow' } else { 'Green' })
    
    $fixableIssues = @($filteredIssues | Where-Object { $_.Fixable })
    if ($fixableIssues.Count -gt 0) {
        Write-Host "$($fixableIssues.Count) issue(s) can be auto-fixed. Run with GUI mode for auto-fix options." -ForegroundColor Cyan
    }
}

function Run-Gui {
    Add-Type -AssemblyName System.Windows.Forms
    Add-Type -AssemblyName System.Drawing

    [System.Windows.Forms.Application]::EnableVisualStyles()

    $form = [System.Windows.Forms.Form]::new()
    $form.Text = 'Transcendence TLisp/XML Checker'
    $form.Width = 1100
    $form.Height = 720
    $form.StartPosition = 'CenterScreen'

    $lblPath = [System.Windows.Forms.Label]::new()
    $lblPath.Text = 'Path:'
    $lblPath.AutoSize = $true
    $lblPath.Location = [System.Drawing.Point]::new(10, 15)
    $form.Controls.Add($lblPath)

    $txtPath = [System.Windows.Forms.TextBox]::new()
    $txtPath.Width = 720
    $txtPath.Location = [System.Drawing.Point]::new(55, 12)
    $form.Controls.Add($txtPath)

    $btnBrowseFile = [System.Windows.Forms.Button]::new()
    $btnBrowseFile.Text = 'Browse File…'
    $btnBrowseFile.Location = [System.Drawing.Point]::new(785, 10)
    $btnBrowseFile.Width = 95
    $form.Controls.Add($btnBrowseFile)

    $btnBrowseFolder = [System.Windows.Forms.Button]::new()
    $btnBrowseFolder.Text = 'Browse Folder…'
    $btnBrowseFolder.Location = [System.Drawing.Point]::new(885, 10)
    $btnBrowseFolder.Width = 110
    $form.Controls.Add($btnBrowseFolder)

    $chkRecurse = [System.Windows.Forms.CheckBox]::new()
    $chkRecurse.Text = 'Recurse'
    $chkRecurse.AutoSize = $true
    $chkRecurse.Location = [System.Drawing.Point]::new(1000, 13)
    $form.Controls.Add($chkRecurse)

    $grpFix = [System.Windows.Forms.GroupBox]::new()
    $grpFix.Text = 'Safe Auto-Fix Options'
    $grpFix.Location = [System.Drawing.Point]::new(10, 42)
    $grpFix.Width = 1070
    $grpFix.Height = 70
    $form.Controls.Add($grpFix)

    $chkBackup = [System.Windows.Forms.CheckBox]::new()
    $chkBackup.Text = 'Create .bak backups'
    $chkBackup.AutoSize = $true
    $chkBackup.Checked = $true
    $chkBackup.Location = [System.Drawing.Point]::new(12, 28)
    $grpFix.Controls.Add($chkBackup)

    $chkFixBom = [System.Windows.Forms.CheckBox]::new()
    $chkFixBom.Text = 'Remove BOM + trim leading whitespace'
    $chkFixBom.AutoSize = $true
    $chkFixBom.Checked = $true
    $chkFixBom.Location = [System.Drawing.Point]::new(170, 28)
    $grpFix.Controls.Add($chkFixBom)

    $chkFixGt = [System.Windows.Forms.CheckBox]::new()
    $chkFixGt.Text = "Escape raw '>' in element content (&gt;)"
    $chkFixGt.AutoSize = $true
    $chkFixGt.Checked = $true
    $chkFixGt.Location = [System.Drawing.Point]::new(440, 28)
    $grpFix.Controls.Add($chkFixGt)

    $chkFixXmlCreate = [System.Windows.Forms.CheckBox]::new()
    $chkFixXmlCreate.Text = 'Escape < > inside xmlCreate string literals'
    $chkFixXmlCreate.AutoSize = $true
    $chkFixXmlCreate.Checked = $true
    $chkFixXmlCreate.Location = [System.Drawing.Point]::new(740, 28)
    $grpFix.Controls.Add($chkFixXmlCreate)

    $btnScan = [System.Windows.Forms.Button]::new()
    $btnScan.Text = 'Scan'
    $btnScan.Location = [System.Drawing.Point]::new(10, 118)
    $btnScan.Width = 80
    $form.Controls.Add($btnScan)

    $btnFix = [System.Windows.Forms.Button]::new()
    $btnFix.Text = 'Fix (Safe)'
    $btnFix.Location = [System.Drawing.Point]::new(100, 118)
    $btnFix.Width = 100
    $form.Controls.Add($btnFix)

    $btnOpen = [System.Windows.Forms.Button]::new()
    $btnOpen.Text = 'Open File'
    $btnOpen.Location = [System.Drawing.Point]::new(210, 118)
    $btnOpen.Width = 90
    $form.Controls.Add($btnOpen)

    $btnCopy = [System.Windows.Forms.Button]::new()
    $btnCopy.Text = 'Copy Issues'
    $btnCopy.Location = [System.Drawing.Point]::new(310, 118)
    $btnCopy.Width = 95
    $form.Controls.Add($btnCopy)

    $grid = [System.Windows.Forms.DataGridView]::new()
    $grid.Location = [System.Drawing.Point]::new(10, 150)
    $grid.Width = 1070
    $grid.Height = 500
    $grid.ReadOnly = $true
    $grid.AllowUserToAddRows = $false
    $grid.AllowUserToDeleteRows = $false
    $grid.SelectionMode = 'FullRowSelect'
    $grid.MultiSelect = $true
    $grid.AutoSizeColumnsMode = 'Fill'
    $grid.RowHeadersVisible = $false
    
    # Add cell formatting to highlight fixable issues
    $grid.CellFormatting.Add({
        param($sender, $e)
        if ($e.ColumnIndex -ge 0 -and $e.RowIndex -ge 0) {
            $row = $grid.Rows[$e.RowIndex]
            $fixable = $row.Cells['Fixable'].Value
            if ($fixable -eq $true) {
                $row.DefaultCellStyle.BackColor = [System.Drawing.Color]::FromArgb(240, 255, 240)  # Light green
            } else {
                $row.DefaultCellStyle.BackColor = [System.Drawing.Color]::White
            }
        }
    })
    
    $form.Controls.Add($grid)

    $status = [System.Windows.Forms.StatusStrip]::new()
    $statusLabel = [System.Windows.Forms.ToolStripStatusLabel]::new()
    $statusLabel.Text = 'Ready.'
    $progress = [System.Windows.Forms.ToolStripProgressBar]::new()
    $progress.Width = 200
    $progress.Minimum = 0
    $progress.Maximum = 100
    $progress.Value = 0
    [void]$status.Items.Add($statusLabel)
    [void]$status.Items.Add($progress)
    $form.Controls.Add($status)

    $issues = New-Object System.Collections.ArrayList

    $refreshGrid = {
        $grid.DataSource = $null
        $grid.DataSource = $issues
    }

    $doScan = {
        $issues.Clear() | Out-Null
        $grid.DataSource = $null

        $p = $txtPath.Text
        if ([string]::IsNullOrWhiteSpace($p)) {
            [System.Windows.Forms.MessageBox]::Show('Pick a file or folder first.')
            return
        }

        $files = @()
        try {
            # Ensure we always get an array (PowerShell will otherwise "unwrap" single results).
            $files = @(Get-XmlFilesFromPath -InputPath $p -Recurse:$($chkRecurse.Checked))
        }
        catch {
            [System.Windows.Forms.MessageBox]::Show($_.Exception.Message, 'Error')
            return
        }

        if ($files.Count -eq 0) {
            $statusLabel.Text = 'No XML files found.'
            $progress.Value = 0
            return
        }

        $statusLabel.Text = "Scanning $($files.Count) file(s)…"
        $progress.Value = 0

        for ($i = 0; $i -lt $files.Count; $i++) {
            $f = $files[$i]
            $statusLabel.Text = "Scanning: $([System.IO.Path]::GetFileName($f)) ($($i+1)/$($files.Count))"
            $progress.Value = [Math]::Min(100, [Math]::Floor((($i+1) * 100.0) / $files.Count))
            [System.Windows.Forms.Application]::DoEvents()

            foreach ($iss in (Get-IssuesForFile -FilePath $f)) {
                [void]$issues.Add($iss)
            }
        }

        & $refreshGrid
        
        $fixableCount = @($issues | Where-Object { $_.Fixable }).Count
        if ($fixableCount -gt 0) {
            $statusLabel.Text = "Done. $($issues.Count) issue(s) found ($fixableCount fixable)."
        } else {
            $statusLabel.Text = "Done. $($issues.Count) issue(s) found (none auto-fixable)."
        }
    }

    $doFix = {
        # Get all files that have fixable issues
        $targets = New-Object System.Collections.Generic.HashSet[string]
        
        if ($grid.SelectedRows.Count -gt 0) {
            # If rows are selected, only fix those files
            foreach ($row in $grid.SelectedRows) {
                $file = $row.Cells['File'].Value
                $fixable = $row.Cells['Fixable'].Value
                if ($file -and $fixable) { 
                    [void]$targets.Add([string]$file) 
                }
            }
        } else {
            # If no rows selected, fix all files with fixable issues
            foreach ($iss in $issues) {
                if ($iss.Fixable) {
                    [void]$targets.Add($iss.File)
                }
            }
        }

        if ($targets.Count -eq 0) {
            [System.Windows.Forms.MessageBox]::Show(
                'No fixable issues found. Either:' + [Environment]::NewLine +
                '1. Select rows with fixable issues (Fixable = True), or' + [Environment]::NewLine +
                '2. The issues found are not auto-fixable (require manual editing).',
                'No Fixable Issues',
                [System.Windows.Forms.MessageBoxButtons]::OK,
                [System.Windows.Forms.MessageBoxIcon]::Information
            )
            return
        }

        $result = [System.Windows.Forms.MessageBox]::Show(
            "Fix $($targets.Count) file(s) with safe auto-fixes?`n`n" +
            "This will:" + [Environment]::NewLine +
            $(if ($chkBackup.Checked) { "  • Create .bak backups" } else { "" }) +
            $(if ($chkFixBom.Checked) { "  • Remove BOM and trim leading whitespace" } else { "" }) +
            $(if ($chkFixGt.Checked) { "  • Escape raw '>' in element content" } else { "" }) +
            $(if ($chkFixXmlCreate.Checked) { "  • Escape < > inside xmlCreate strings" } else { "" }),
            'Confirm Fix',
            [System.Windows.Forms.MessageBoxButtons]::YesNo,
            [System.Windows.Forms.MessageBoxIcon]::Question
        )
        
        if ($result -ne 'Yes') { return }

        $statusLabel.Text = "Fixing $($targets.Count) file(s)…"
        $progress.Value = 0

        $fixedCount = 0
        $errorCount = 0
        $idx = 0
        foreach ($f in $targets) {
            $idx++
            $statusLabel.Text = "Fixing: $([System.IO.Path]::GetFileName($f)) ($idx/$($targets.Count))"
            $progress.Value = [Math]::Min(100, [Math]::Floor(($idx * 100.0) / $targets.Count))
            [System.Windows.Forms.Application]::DoEvents()

            try {
                Fix-FileSafe -FilePath $f `
                    -Backup:$($chkBackup.Checked) `
                    -FixBomAndLeadingWhitespace:$($chkFixBom.Checked) `
                    -FixRawGreaterThan:$($chkFixGt.Checked) `
                    -FixXmlCreateStrings:$($chkFixXmlCreate.Checked)
                $fixedCount++
            }
            catch {
                $errorCount++
                [System.Windows.Forms.MessageBox]::Show("Failed to fix $f`n`n$($_.Exception.Message)", 'Fix Error', [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Error)
            }
        }

        $statusLabel.Text = "Fixed $fixedCount file(s). Re-scanning…"
        $progress.Value = 0
        [System.Windows.Forms.Application]::DoEvents()

        # Re-scan to show updated results
        & $doScan
        
        if ($fixedCount -gt 0) {
            $statusLabel.Text = "Fixed $fixedCount file(s). $($issues.Count) issue(s) remaining."
        }
    }

    $btnBrowseFile.Add_Click({
        $dlg = [System.Windows.Forms.OpenFileDialog]::new()
        $dlg.Filter = 'XML files (*.xml)|*.xml|All files (*.*)|*.*'
        $dlg.Title = 'Select an XML file'
        if ($dlg.ShowDialog() -eq 'OK') { $txtPath.Text = $dlg.FileName }
    })

    $btnBrowseFolder.Add_Click({
        $dlg = [System.Windows.Forms.FolderBrowserDialog]::new()
        $dlg.Description = 'Select a folder to scan'
        if ($dlg.ShowDialog() -eq 'OK') { $txtPath.Text = $dlg.SelectedPath }
    })

    $btnScan.Add_Click({ & $doScan })
    $btnFix.Add_Click({ & $doFix })

    $btnOpen.Add_Click({
        if ($grid.SelectedRows.Count -lt 1) { return }
        $file = $grid.SelectedRows[0].Cells['File'].Value
        if ($file -and (Test-Path -LiteralPath $file)) {
            Start-Process -FilePath $file
        }
    })

    $btnCopy.Add_Click({
        if ($issues.Count -eq 0) { return }
        $lines = @()
        foreach ($iss in $issues) {
            $lines += ("{0}`t{1}`tL{2}:{3}`t{4}`t{5}" -f $iss.Severity, $iss.Code, $iss.Line, $iss.Column, $iss.Message, $iss.File)
        }
        [System.Windows.Forms.Clipboard]::SetText(($lines -join "`r`n"))
        $statusLabel.Text = 'Copied issues to clipboard.'
    })

    if (-not [string]::IsNullOrWhiteSpace($Path)) { $txtPath.Text = $Path }
    $chkRecurse.Checked = $Recurse.IsPresent

    # First scan if a path is provided.
    if (-not [string]::IsNullOrWhiteSpace($txtPath.Text)) {
        $form.Shown.Add({ & $doScan })
    }

    [void]$form.ShowDialog()
}

if ($NoGui) {
    if ([string]::IsNullOrWhiteSpace($Path)) { $Path = '.' }
    Run-Cli -InputPath $Path -Recurse:$Recurse -SeverityFilter $Severity -ExportPath $ExportPath -VerboseOutput:$Detailed -SkipCodes $SkipCodes -OnlyCodes $OnlyCodes
}
else {
    Run-Gui
}



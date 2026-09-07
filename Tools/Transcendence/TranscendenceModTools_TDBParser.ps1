<#
.SYNOPSIS
  TDB File Parser and Validator
  
.DESCRIPTION
  Supports both text and binary TDB files:
  - Text mode: Parse key/value, sectioned, or XML-like variants
  - Binary mode: Extract embedded strings and metadata
  - Semantic validation: UNIDs, resources, API usage
  - Preview and extraction capabilities

# Load shared asset generation settings
$settingsPath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "..\\AssetGenerationSettings.ps1"
if (Test-Path $settingsPath) {
    . $settingsPath
}
#>

# ============================================================
# TDB FILE DETECTION
# ============================================================

function Test-IsTextFile {
    param([string]$Path)
    
    try {
        $fs = [System.IO.File]::OpenRead($Path)
        $bytes = New-Object byte[] 1024
        $read = $fs.Read($bytes, 0, $bytes.Length)
        $fs.Close()
        
        for ($i = 0; $i -lt $read; $i++) {
            # Check for non-text characters (control chars except common ones)
            if ($bytes[$i] -lt 9 -or ($bytes[$i] -gt 13 -and $bytes[$i] -lt 32 -and $bytes[$i] -ne 0)) {
                return $false
            }
        }
        return $true
    }
    catch {
        return $false
    }
}

function Get-TdbFileType {
    param([string]$Path)
    
    $extension = [System.IO.Path]::GetExtension($Path)
    if ($extension -notmatch '\.(tdb|TDB)$') {
        return [PSCustomObject]@{ Type = 'Unknown'; Confidence = 0 }
    }
    
    # Check magic bytes/signature
    try {
        $bytes = [System.IO.File]::ReadAllBytes($Path)
        if ($bytes.Length -lt 4) {
            return [PSCustomObject]@{ Type = 'Unknown'; Confidence = 0 }
        }
        
        # Check for XML signature
        $header = [System.Text.Encoding]::ASCII.GetString($bytes, 0, [Math]::Min(100, $bytes.Length))
        if ($header -match '^\s*<\?xml') {
            return [PSCustomObject]@{ Type = 'XML'; Confidence = 100 }
        }
        
        # Check if text file
        if (Test-IsTextFile $Path) {
            # Try to detect format
            $text = [System.IO.File]::ReadAllText($Path, [System.Text.Encoding]::UTF8)
            if ($text -match '^\s*\[.*\]\s*$' -or $text -match '^\s*\w+\s*=') {
                return [PSCustomObject]@{ Type = 'Text'; Format = 'KeyValue'; Confidence = 90 }
            }
            elseif ($text -match '<\w+') {
                return [PSCustomObject]@{ Type = 'Text'; Format = 'XML'; Confidence = 95 }
            }
            else {
                return [PSCustomObject]@{ Type = 'Text'; Format = 'Unknown'; Confidence = 70 }
            }
        }
        else {
            return [PSCustomObject]@{ Type = 'Binary'; Confidence = 85 }
        }
    }
    catch {
        return [PSCustomObject]@{ Type = 'Unknown'; Confidence = 0; Error = $_.Exception.Message }
    }
}

# ============================================================
# TEXT TDB PARSER
# ============================================================

function Parse-TdbText {
    param(
        [string]$Path,
        [int]$MaxLines = 1000
    )
    
    $result = [PSCustomObject]@{
        Path = $Path
        Type = 'Text'
        Entries = @()
        Sections = @()
        KeyValuePairs = @{}
        Preview = ""
        LineCount = 0
        Unids = @()
        Resources = @()
    }
    
    try {
        $lines = Get-Content -Path $Path -ErrorAction SilentlyContinue
        if (-not $lines) {
            return $result
        }
        
        $result.LineCount = $lines.Count
        $currentSection = ""
        $entryCount = 0
        
        foreach ($line in $lines) {
            if ($entryCount -ge $MaxLines) { break }
            
            $trim = $line.Trim()
            if ($trim -eq "" -or $trim.StartsWith(';') -or $trim.StartsWith('#')) {
                continue
            }
            
            # Section header: [SectionName]
            if ($trim -match '^\s*\[(.+)\]\s*$') {
                $currentSection = $matches[1]
                $result.Sections += $currentSection
                $result.Entries += [PSCustomObject]@{
                    Type = 'Section'
                    Section = $currentSection
                    Line = $entryCount + 1
                    Value = $trim
                }
            }
            # Key=Value pair
            elseif ($trim -match '^([^=]+)=(.*)$') {
                $key = $matches[1].Trim()
                $value = $matches[2].Trim()
                
                $result.Entries += [PSCustomObject]@{
                    Type = 'KeyValue'
                    Section = $currentSection
                    Key = $key
                    Value = $value
                    Line = $entryCount + 1
                }
                
                if ($currentSection) {
                    if (-not $result.KeyValuePairs.ContainsKey($currentSection)) {
                        $result.KeyValuePairs[$currentSection] = @{}
                    }
                    $result.KeyValuePairs[$currentSection][$key] = $value
                }
                else {
                    $result.KeyValuePairs[$key] = $value
                }
                
                # Extract UNIDs
                if ($value -match '0x[0-9A-Fa-f]{8}') {
                    $unidMatches = [regex]::Matches($value, '0x[0-9A-Fa-f]{8}')
                    foreach ($match in $unidMatches) {
                        if ($result.Unids -notcontains $match.Value) {
                            $result.Unids += $match.Value
                        }
                    }
                }
                
                # Extract resource references
                if ($key -match 'image|sound|resource|bitmap' -or $value -match '\.(jpg|png|bmp|wav|mp3)') {
                    $result.Resources += [PSCustomObject]@{
                        Key = $key
                        Value = $value
                        Line = $entryCount + 1
                    }
                }
            }
            # Plain line
            else {
                $result.Entries += [PSCustomObject]@{
                    Type = 'Line'
                    Section = $currentSection
                    Value = $trim
                    Line = $entryCount + 1
                }
            }
            
            $entryCount++
        }
        
        # Generate preview
        $previewLines = $result.Entries | Select-Object -First 20 | ForEach-Object {
            if ($_.Type -eq "Section") {
                "[$($_.Section)]"
            }
            elseif ($_.Type -eq "KeyValue") {
                "$($_.Key)=$($_.Value)"
            }
            else {
                $_.Value
            }
        }
        $result.Preview = $previewLines -join "`n"
    }
    catch {
        $result.Error = $_.Exception.Message
    }
    
    return $result
}

# ============================================================
# BINARY TDB PARSER
# ============================================================

function Extract-StringsFromBinary {
    param(
        [string]$Path,
        [int]$MinLength = 4,
        [int]$MaxStrings = 500
    )
    
    $result = [PSCustomObject]@{
        Path = $Path
        Type = 'Binary'
        Strings = @()
        Unids = @()
        Resources = @()
        Preview = ""
    }
    
    try {
        $bytes = [System.IO.File]::ReadAllBytes($Path)
        $sb = New-Object System.Text.StringBuilder
        $strings = @()
        
        foreach ($b in $bytes) {
            # Printable ASCII range
            if ($b -ge 32 -and $b -le 126) {
                [void]$sb.Append([char]$b)
            }
            else {
                if ($sb.Length -ge $MinLength) {
                    $str = $sb.ToString()
                    if ($strings.Count -lt $MaxStrings) {
                        $strings += $str
                    }
                }
                $sb.Clear() | Out-Null
            }
        }
        
        if ($sb.Length -ge $MinLength) {
            $strings += $sb.ToString()
        }
        
        $result.Strings = $strings
        
        # Extract UNIDs from strings
        foreach ($str in $strings) {
            if ($str -match '0x[0-9A-Fa-f]{8}') {
                $unidMatches = [regex]::Matches($str, '0x[0-9A-Fa-f]{8}')
                foreach ($match in $unidMatches) {
                    if ($result.Unids -notcontains $match.Value) {
                        $result.Unids += $match.Value
                    }
                }
            }
            
            # Extract resource references
            if ($str -match '\.(jpg|png|bmp|wav|mp3|xml)', 'IgnoreCase') {
                $result.Resources += $str
            }
        }
        
        # Generate preview
        $result.Preview = ($strings | Select-Object -First 30) -join "`n"
    }
    catch {
        $result.Error = $_.Exception.Message
    }
    
    return $result
}

# ============================================================
# TDB SEMANTIC VALIDATION
# ============================================================

function Test-TdbSemantic {
    param(
        [PSCustomObject]$TdbData,
        [string[]]$AllFiles = @()
    )
    
    $issues = [System.Collections.ArrayList]::new()
    
    # Validate UNIDs
    foreach ($unid in $TdbData.Unids) {
        # Check if UNID is in valid range
        try {
            $unidValue = [Convert]::ToUInt32($unid, 16)
            
            # Reserved ranges
            if ($unidValue -ge 0x0000 -and $unidValue -le 0x9FFF) {
                [void]$issues.Add([PSCustomObject]@{
                    Type = 'UNID_Reserved'
                    Severity = 'Warning'
                    Message = "UNID $unid is in reserved Kronosaur range"
                    UNID = $unid
                })
            }
        }
        catch {
            [void]$issues.Add([PSCustomObject]@{
                Type = 'UNID_Invalid'
                Severity = 'Error'
                Message = "Invalid UNID format: $unid"
                UNID = $unid
            })
        }
    }
    
    # Validate resource references
    foreach ($resource in $TdbData.Resources) {
        $resourcePath = if ($resource.Value) { $resource.Value } else { $resource }
        
        # Check if resource file exists (if path is relative)
        if ($resourcePath -match '\.(jpg|png|bmp|wav|mp3)', 'IgnoreCase') {
            $resourceFile = $resourcePath
            if (-not ([System.IO.Path]::IsPathRooted($resourceFile))) {
                # Try to find relative to TDB file
                $tdbDir = [System.IO.Path]::GetDirectoryName($TdbData.Path)
                $resourceFile = Join-Path $tdbDir $resourcePath
            }
            
            if (-not (Test-Path $resourceFile)) {
                [void]$issues.Add([PSCustomObject]@{
                    Type = 'Resource_Missing'
                    Severity = 'Warning'
                    Message = "Resource file not found: $resourcePath"
                    Resource = $resourcePath
                })
            }
        }
    }
    
    return $issues
}

# ============================================================
# TDB PREVIEW GENERATOR
# ============================================================

function Get-TdbPreview {
    param([string]$Path)
    
    $fileType = Get-TdbFileType -Path $Path
    
    if ($fileType.Type -eq 'Text') {
        $parsed = Parse-TdbText -Path $Path -MaxLines 200
        $semantic = Test-TdbSemantic -TdbData $parsed
        
        return [PSCustomObject]@{
            Path = $Path
            FileType = $fileType
            Parsed = $parsed
            SemanticIssues = $semantic
            Summary = [PSCustomObject]@{
                Entries = $parsed.Entries.Count
                Sections = $parsed.Sections.Count
                Unids = $parsed.Unids.Count
                Resources = $parsed.Resources.Count
                Issues = $semantic.Count
            }
        }
    }
    elseif ($fileType.Type -eq 'Binary') {
        $extracted = Extract-StringsFromBinary -Path $Path
        $semantic = Test-TdbSemantic -TdbData $extracted
        
        return [PSCustomObject]@{
            Path = $Path
            FileType = $fileType
            Extracted = $extracted
            SemanticIssues = $semantic
            Summary = [PSCustomObject]@{
                Strings = $extracted.Strings.Count
                Unids = $extracted.Unids.Count
                Resources = $extracted.Resources.Count
                Issues = $semantic.Count
            }
        }
    }
    else {
        return [PSCustomObject]@{
            Path = $Path
            FileType = $fileType
            Error = "Unable to determine TDB file type"
        }
}

}

# ============================================================
# TDB TO XML CONVERSION (for validation)
# ============================================================

function Convert-TdbToXml {
    param(
        [PSCustomObject]$TdbData,
        [string]$OutputPath
    )
    
    # This would convert TDB entries to XML format for validation
    # Implementation depends on TDB format specifics
    
    $xml = [System.Text.StringBuilder]::new()
    [void]$xml.AppendLine('<?xml version="1.0" encoding="utf-8"?>')
    [void]$xml.AppendLine('<TranscendenceExtension>')
    
    # Convert entries to XML
    foreach ($entry in $TdbData.Entries) {
        if ($entry.Type -eq 'Section') {
            [void]$xml.AppendLine("  <!-- Section: $($entry.Section) -->")
        }
        elseif ($entry.Type -eq 'KeyValue') {
            [void]$xml.AppendLine("  <Entry key=`"$($entry.Key)`" value=`"$($entry.Value)`" />")
        }
    }
    
    [void]$xml.AppendLine('</TranscendenceExtension>')
    
    if ($OutputPath) {
        $utf8NoBom = [System.Text.UTF8Encoding]::new($false)
        [System.IO.File]::WriteAllText($OutputPath, $xml.ToString(), $utf8NoBom)
    }
    
    return $xml.ToString()
}

# ============================================================
# TDB DEPRECATION RULES
# ============================================================

$script:TdbDeprecationRules = @(
    @{
        Id = 'deprecated-tag-001'
        Pattern = '<OldWeapon>'
        Type = 'xml-tag'
        Severity = 'high'
        Suggest = 'Replace with <WeaponFire> and update attributes'
    },
    @{
        Id = 'deprecated-func-002'
        Pattern = '\(@\s+oldFunc'
        Type = 'tlisp'
        Severity = 'medium'
        Suggest = 'Use newFunc instead'
    }
)

function Test-TdbDeprecation {
    param(
        [PSCustomObject]$TdbData
    )
    
    $deprecations = @()
    $content = if ($TdbData.Parsed) { $TdbData.Parsed.Preview } else { $TdbData.Extracted.Preview }
    
    foreach ($rule in $script:TdbDeprecationRules) {
        if ($content -match $rule.Pattern) {
            $deprecations += [PSCustomObject]@{
                RuleId = $rule.Id
                Pattern = $rule.Pattern
                Type = $rule.Type
                Severity = $rule.Severity
                Suggestion = $rule.Suggest
            }
        }
    }
    
    return $deprecations
}


<#
.SYNOPSIS
    Scans Caves of Qud mods for chargen-breaking PopulationTables / Genotypes / Subtypes XML issues.

.DESCRIPTION
    Builds an index of populations, object blueprints, subtype classes/entries, and genotypes from
    Base + StreamingAssets DLC + scanned mods, then validates each mod's chargen XML.

    Dry-run by default. -Apply performs only safe structural fixes:
      - Insert Encoding="utf-8" on populations/genotypes/subtypes roots when missing
      - Remove self-referential <table Name="ThisPopulation"/> nodes
      - Rename duplicate group Names within one population to {Name}_dup{N}
      - On <class>, rename DisplayName= to ChargenTitle= when ChargenTitle is absent

.PARAMETER Path
    One or more root folders to scan. Defaults to the Mods folder (parent of _tools).

.PARAMETER IncludeWorkshop
    Also scan Steam Workshop content for CoQ (333640).

.PARAMETER Mod
    Only scan subfolder(s) whose folder name matches this (wildcards ok).

.PARAMETER Apply
    Write safe fixes to disk. Without this switch the tool only reports.

.PARAMETER NoBackup
    When -Apply is used, skip writing <file>.bak next to modified files.

.PARAMETER Report
    Markdown report path. Defaults to _tools\reports\ChargenXml_<timestamp>.md

.PARAMETER BasePath
    Game StreamingAssets Base folder (read-only index source).

.PARAMETER DlcPath
    Game StreamingAssets DLC folder (read-only index source). Optional.

.EXAMPLE
    .\Validate-ChargenXml.ps1 -IncludeWorkshop -Report .\reports\chargen.md

.EXAMPLE
    .\Validate-ChargenXml.ps1 -Mod "Proliferate and Pilfer" -Apply
#>

[CmdletBinding()]
param(
    [string[]]$Path,
    [switch]$IncludeWorkshop,
    [string]$Mod,
    [switch]$Apply,
    [switch]$NoBackup,
    [string]$Report,
    [string]$BasePath,
    [string]$DlcPath
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$ScriptRoot = $PSScriptRoot
. (Join-Path $ScriptRoot 'scripts\CoqPaths.ps1')
$ModsRoot = Get-CoqModsRoot -ToolsRoot $ScriptRoot
$SteamLibrary = Get-CoqSteamLibrary
$WorkshopRoot = Join-Path $SteamLibrary 'steamapps\workshop\content\333640'
if (-not $PSBoundParameters.ContainsKey('BasePath') -or -not $BasePath) {
    $BasePath = Join-Path $SteamLibrary 'steamapps\common\Caves of Qud\CoQ_Data\StreamingAssets\Base'
}
if (-not $PSBoundParameters.ContainsKey('DlcPath') -or -not $DlcPath) {
    $DlcPath = Join-Path $SteamLibrary 'steamapps\common\Caves of Qud\CoQ_Data\StreamingAssets\DLC'
}

if (-not $Path -or $Path.Count -eq 0) {
    $Path = @($ModsRoot)
}
if ($IncludeWorkshop -and (Test-Path -LiteralPath $WorkshopRoot)) {
    if ($Path -notcontains $WorkshopRoot) { $Path += $WorkshopRoot }
}

if (-not $Report) {
    $stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
    $Report = Join-Path $ScriptRoot "reports\ChargenXml_$stamp.md"
}

$skipDirNames = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
foreach ($n in @('_tools', 'bin', 'obj', '.git', '.vs', '.dotnet', 'node_modules', '_decompile', 'scratch')) {
    [void]$skipDirNames.Add($n)
}

$dynamicTablePrefixes = @(
    'DynamicInheritsTable:',
    'DynamicObjectsTable:',
    'DynamicSemanticTable:',
    'DynamicEncounterTable:'
)

# --- state ---
$findings = [System.Collections.Generic.List[object]]::new()
$applied = [System.Collections.Generic.List[object]]::new()
$stats = [ordered]@{
    ModsScanned          = 0
    PopulationFiles      = 0
    GenotypeFiles        = 0
    SubtypeFiles         = 0
    BlueprintFiles       = 0
    Errors               = 0
    Warns                = 0
    AppliedFixes         = 0
    PopulationsIndexed   = 0
    BlueprintsIndexed    = 0
    SubtypeClassesIndexed = 0
    SubtypesIndexed      = 0
    GenotypesIndexed     = 0
}

function Add-Finding {
    param(
        [ValidateSet('Error', 'Warn')][string]$Severity,
        [string]$Kind,   # Population | Genotype | Subtype
        [string]$Rule,
        [string]$ModName,
        [string]$File,
        [int]$Line = 0,
        [string]$Message,
        [string]$Population = '',
        [switch]$HighPriority
    )
    $f = [pscustomobject]@{
        Severity     = $Severity
        Kind         = $Kind
        Rule         = $Rule
        ModName      = $ModName
        File         = $File
        Line         = $Line
        Message      = $Message
        Population   = $Population
        HighPriority = [bool]$HighPriority
    }
    $findings.Add($f)
    if ($Severity -eq 'Error') { $stats.Errors++ } else { $stats.Warns++ }
}

function Test-SkipDirectory([System.IO.DirectoryInfo]$dir) {
    if ($skipDirNames.Contains($dir.Name)) { return $true }
    if ($dir.Name -like '_decompile*') { return $true }
    return $false
}

function Get-RelativePath([string]$root, [string]$full) {
    try {
        $r = [System.IO.Path]::GetFullPath($root).TrimEnd('\') + '\'
        $f = [System.IO.Path]::GetFullPath($full)
        if ($f.StartsWith($r, [StringComparison]::OrdinalIgnoreCase)) {
            return $f.Substring($r.Length)
        }
    } catch {}
    return $full
}

function Get-AttrValue([string]$tagText, [string]$attrName) {
    $m = [regex]::Match($tagText, "(?i)\b$([regex]::Escape($attrName))\s*=\s*`"([^`"]*)`"")
    if ($m.Success) { return $m.Groups[1].Value }
    $m = [regex]::Match($tagText, "(?i)\b$([regex]::Escape($attrName))\s*=\s*'([^']*)'")
    if ($m.Success) { return $m.Groups[1].Value }
    return $null
}

function Test-HasAttr([string]$tagText, [string]$attrName) {
    return $tagText -match "(?i)\b$([regex]::Escape($attrName))\s*="
}

function Get-LineNumberAtIndex([string]$text, [int]$index) {
    if ($index -le 0) { return 1 }
    $n = 1
    $end = [Math]::Min($index, $text.Length)
    for ($i = 0; $i -lt $end; $i++) {
        if ($text[$i] -eq "`n") { $n++ }
    }
    return $n
}

function Test-IsDynamicTable([string]$name) {
    if ([string]::IsNullOrEmpty($name)) { return $true }
    foreach ($p in $dynamicTablePrefixes) {
        if ($name.StartsWith($p, [StringComparison]::OrdinalIgnoreCase)) { return $true }
    }
    if ($name -match '\{zonetier\}|\{ownertier\}') { return $true }
    return $false
}

function Test-NumberNonPositive([string]$number) {
    if ([string]::IsNullOrWhiteSpace($number)) { return $false }
    $t = $number.Trim()
    if ($t -match '^-?\d+$') {
        return ([int]$t) -le 0
    }
    return $false
}

function Find-CaseMismatch([string]$name, [System.Collections.Generic.HashSet[string]]$exact, [System.Collections.Generic.Dictionary[string, string]]$lowerMap) {
    if ([string]::IsNullOrEmpty($name)) { return $null }
    if ($exact.Contains($name)) { return $null }
    $key = $name.ToLowerInvariant()
    if ($lowerMap.ContainsKey($key)) { return $lowerMap[$key] }
    return $null
}

function New-NameIndex {
    $exact = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
    $lower = [System.Collections.Generic.Dictionary[string, string]]::new([StringComparer]::Ordinal)
    return [pscustomobject]@{ Exact = $exact; Lower = $lower }
}

function Add-ToNameIndex($index, [string]$name) {
    if ([string]::IsNullOrEmpty($name)) { return }
    [void]$index.Exact.Add($name)
    $k = $name.ToLowerInvariant()
    if (-not $index.Lower.ContainsKey($k)) { $index.Lower[$k] = $name }
}

function Remove-FromNameIndex($index, [string]$name) {
    if ([string]::IsNullOrEmpty($name)) { return }
    [void]$index.Exact.Remove($name)
    $k = $name.ToLowerInvariant()
    if ($index.Lower.ContainsKey($k) -and $index.Lower[$k] -ceq $name) {
        [void]$index.Lower.Remove($k)
    }
}

function Get-FilesRecursive([string]$root, [string[]]$filters) {
    $list = [System.Collections.Generic.List[string]]::new()
    if (-not (Test-Path -LiteralPath $root)) { return $list }
    $stack = [System.Collections.Generic.Stack[string]]::new()
    $stack.Push($root)
    while ($stack.Count -gt 0) {
        $dir = $stack.Pop()
        try {
            foreach ($sub in [System.IO.Directory]::EnumerateDirectories($dir)) {
                $di = Get-Item -LiteralPath $sub
                if (Test-SkipDirectory $di) { continue }
                $stack.Push($sub)
            }
            foreach ($filt in $filters) {
                foreach ($f in [System.IO.Directory]::EnumerateFiles($dir, $filt)) {
                    if ($f.EndsWith('.bak', [StringComparison]::OrdinalIgnoreCase)) { continue }
                    $list.Add($f)
                }
            }
        } catch {}
    }
    return $list
}

function Read-TextLossless([string]$filePath) {
    $bytes = [System.IO.File]::ReadAllBytes($filePath)
    $bomLen = 0
    if ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) {
        $bomLen = 3
    }
    $latin1 = [System.Text.Encoding]::GetEncoding(28591)
    $content = if ($bomLen -gt 0) { $latin1.GetString($bytes, $bomLen, $bytes.Length - $bomLen) } else { $latin1.GetString($bytes) }
    return [pscustomobject]@{
        Bytes   = $bytes
        BomLen  = $bomLen
        Text    = $content
        Latin1  = $latin1
    }
}

function Write-TextLossless($fileInfo, [string]$newText, [string]$filePath) {
    $newContent = $fileInfo.Latin1.GetBytes($newText)
    if ($fileInfo.BomLen -gt 0) {
        $bom = $fileInfo.Bytes[0..($fileInfo.BomLen - 1)]
        $out = New-Object byte[] ($bom.Length + $newContent.Length)
        [Array]::Copy($bom, 0, $out, 0, $bom.Length)
        [Array]::Copy($newContent, 0, $out, $bom.Length, $newContent.Length)
    } else {
        $out = $newContent
    }
    [System.IO.File]::WriteAllBytes($filePath, $out)
}

function Strip-XmlComments([string]$text) {
    return [regex]::Replace($text, '(?s)<!--.*?-->', '')
}

function Test-RootEncoding([string]$text, [string]$rootName) {
    # true if Encoding present on root
    $m = [regex]::Match($text, "(?is)<\s*$([regex]::Escape($rootName))\b(?<attrs>[^>]*)>")
    if (-not $m.Success) { return $true } # no root — other rules handle
    return (Test-HasAttr $m.Groups['attrs'].Value 'Encoding')
}

function Try-InsertEncoding([string]$text, [string]$rootName) {
    $rootRegex = [regex]"(?is)(?<prefix>^\s*(<\?xml[^>]*\?>\s*)?((<!--.*?-->|\s)*)?)<(?<name>$([regex]::Escape($rootName)))(?<attrs>(?:\s+[\w:.\-]+\s*=\s*`"[^`"]*`")*)\s*(?<selfclose>/?)>"
    $m = $rootRegex.Match($text)
    if (-not $m.Success) { return $null }
    if (Test-HasAttr $m.Groups['attrs'].Value 'Encoding') { return $null }
    $name = $m.Groups['name'].Value
    $attrs = $m.Groups['attrs'].Value
    $selfclose = $m.Groups['selfclose'].Value
    $newTag = "<$name Encoding=`"utf-8`"$attrs$selfclose>"
    return $text.Substring(0, $m.Index) + $newTag + $text.Substring($m.Index + $m.Length)
}

# --- index builders (regex; resilient) ---

function Index-PopulationsFromFile([string]$filePath, $popIndex, [System.Collections.Generic.HashSet[string]]$basePops = $null, [switch]$AsBase) {
    $raw = Read-TextLossless $filePath
    $text = $raw.Text
    foreach ($m in [regex]::Matches($text, '(?is)<\s*population\b([^>]*)>')) {
        $name = Get-AttrValue $m.Groups[1].Value 'Name'
        if ([string]::IsNullOrEmpty($name)) { continue }
        $load = Get-AttrValue $m.Groups[1].Value 'Load'
        if ($load -and $load.Equals('Remove', [StringComparison]::OrdinalIgnoreCase)) {
            Remove-FromNameIndex $popIndex $name
            if ($basePops) { [void]$basePops.Remove($name) }
            continue
        }
        Add-ToNameIndex $popIndex $name
        if ($AsBase -and $basePops) { [void]$basePops.Add($name) }
    }
}

function Index-BlueprintsFromFile([string]$filePath, $bpIndex) {
    $raw = Read-TextLossless $filePath
    $text = $raw.Text
    foreach ($m in [regex]::Matches($text, '(?is)<\s*object\b([^>]*)>')) {
        $attrs = $m.Groups[1].Value
        $name = Get-AttrValue $attrs 'Name'
        if ([string]::IsNullOrEmpty($name)) { continue }
        $load = Get-AttrValue $attrs 'Load'
        if ($load -and $load.Equals('Remove', [StringComparison]::OrdinalIgnoreCase)) {
            Remove-FromNameIndex $bpIndex $name
            continue
        }
        Add-ToNameIndex $bpIndex $name
    }
}

function Index-SubtypesFromFile([string]$filePath, $classIndex, $subtypeIndex) {
    $raw = Read-TextLossless $filePath
    $text = $raw.Text
    foreach ($m in [regex]::Matches($text, '(?is)<\s*class\b([^>]*)>')) {
        $id = Get-AttrValue $m.Groups[1].Value 'ID'
        if (-not [string]::IsNullOrEmpty($id)) { Add-ToNameIndex $classIndex $id }
    }
    foreach ($m in [regex]::Matches($text, '(?is)<\s*subtype\b([^>]*)>')) {
        $name = Get-AttrValue $m.Groups[1].Value 'Name'
        if (-not [string]::IsNullOrEmpty($name)) { Add-ToNameIndex $subtypeIndex $name }
    }
}

function Index-GenotypesFromFile([string]$filePath, $genoIndex) {
    $raw = Read-TextLossless $filePath
    $text = $raw.Text
    foreach ($m in [regex]::Matches($text, '(?is)<\s*genotype\b([^>]*)>')) {
        $name = Get-AttrValue $m.Groups[1].Value 'Name'
        if ([string]::IsNullOrEmpty($name)) { continue }
        if ($name.StartsWith('-')) {
            Remove-FromNameIndex $genoIndex $name.Substring(1)
            continue
        }
        Add-ToNameIndex $genoIndex $name
    }
}

function Test-IsModFolder([string]$dirPath) {
    foreach ($n in @('manifest.json', 'Manifest.json', 'manifest.JSON')) {
        if (Test-Path -LiteralPath (Join-Path $dirPath $n)) { return $true }
    }
    # Local forks sometimes omit manifest but ship chargen XML at root
    foreach ($n in @('PopulationTables.xml', 'Genotypes.xml', 'Subtypes.xml')) {
        if (Test-Path -LiteralPath (Join-Path $dirPath $n)) { return $true }
    }
    return $false
}

function Get-ModUnits([string[]]$roots, [string]$modFilter) {
    $units = [System.Collections.Generic.List[object]]::new()
    foreach ($root in $roots) {
        if (-not (Test-Path -LiteralPath $root)) { continue }
        $rootFull = [System.IO.Path]::GetFullPath($root)
        # If the path itself is a mod folder, scan it as one unit (even if it has subdirs).
        if (Test-IsModFolder $rootFull) {
            $name = Split-Path -Leaf $rootFull
            if ($modFilter -and ($name -notlike $modFilter)) { continue }
            $units.Add([pscustomobject]@{ Name = $name; Root = $rootFull })
            continue
        }
        $children = @(Get-ChildItem -LiteralPath $rootFull -Directory -ErrorAction SilentlyContinue |
            Where-Object { -not (Test-SkipDirectory $_) })
        foreach ($c in $children) {
            if ($modFilter -and ($c.Name -notlike $modFilter)) { continue }
            $units.Add([pscustomobject]@{ Name = $c.Name; Root = $c.FullName })
        }
    }
    return $units
}

function Test-IsBlueprintXmlPath([string]$filePath) {
    if ($filePath -match '(?i)[\\/]ObjectBlueprints[\\/]') { return $true }
    $leaf = [System.IO.Path]::GetFileName($filePath)
    if ($leaf -ieq 'ObjectBlueprints.xml') { return $true }
    if ($leaf -like 'ObjectBlueprints*.xml') { return $true }
    return $false
}

function Get-BlueprintXmlFiles([string]$root) {
    $list = [System.Collections.Generic.List[string]]::new()
    foreach ($f in (Get-FilesRecursive $root @('*.xml'))) {
        if (Test-IsBlueprintXmlPath $f) { $list.Add($f) }
    }
    return $list
}

function Get-ChargenXmlFiles([string]$modRoot) {
    $pops = [System.Collections.Generic.List[string]]::new()
    $genos = [System.Collections.Generic.List[string]]::new()
    $subs = [System.Collections.Generic.List[string]]::new()
    foreach ($f in (Get-FilesRecursive $modRoot @('*.xml'))) {
        if (Test-IsBlueprintXmlPath $f) { continue }
        $leaf = [System.IO.Path]::GetFileName($f)
        if ($leaf -ieq 'Genotypes.xml') { $genos.Add($f); continue }
        if ($leaf -ieq 'Subtypes.xml') { $subs.Add($f); continue }
        if ($leaf -ieq 'PopulationTables.xml' -or $leaf -like '*Population*.xml') {
            $pops.Add($f)
        }
    }
    return [pscustomobject]@{ Populations = $pops; Genotypes = $genos; Subtypes = $subs }
}

# --- population validation ---

function Test-PopulationFile([string]$filePath, [string]$modName, $popIndex, $bpIndex, [System.Collections.Generic.HashSet[string]]$basePops, [System.Collections.Generic.HashSet[string]]$errorPopulations) {
    $stats.PopulationFiles++
    $raw = Read-TextLossless $filePath
    $text = $raw.Text
    $rel = $filePath

    if (-not (Test-RootEncoding $text 'populations')) {
        Add-Finding -Severity Warn -Kind Population -Rule 'missing-encoding' -ModName $modName -File $rel -Line 1 `
            -Message 'Root <populations> missing Encoding="utf-8"'
    }

    # Validate against comment-stripped text so commented-out populations don't false-positive.
    # Line numbers still map through the stripped string (comment removal shortens offsets) —
    # prefer original $text for line lookup via a parallel match on active content only.
    $active = Strip-XmlComments $text

    # Extract each population block roughly
    $popMatches = [regex]::Matches($active, '(?is)<\s*population\b([^>]*)>(.*?)</\s*population\s*>')
    if ($popMatches.Count -eq 0 -and $active -match '(?i)<\s*population\b') {
        Add-Finding -Severity Error -Kind Population -Rule 'xml-parse' -ModName $modName -File $rel -Line 1 `
            -Message 'Found <population> tags but could not parse closed population blocks' -HighPriority
    }

    $edges = @{} # popName -> list of referenced table names (for cycle detect within file)

    foreach ($pm in $popMatches) {
        $pattrs = $pm.Groups[1].Value
        $body = $pm.Groups[2].Value
        $popName = Get-AttrValue $pattrs 'Name'
        # Best-effort line in original file: search for population Name= near start
        $popLine = 1
        if (-not [string]::IsNullOrEmpty($popName)) {
            $anchor = [regex]::Match($text, "(?i)<\s*population\b[^>]*\bName\s*=\s*`"$([regex]::Escape($popName))`"")
            if ($anchor.Success) { $popLine = Get-LineNumberAtIndex $text $anchor.Index }
        }
        $load = Get-AttrValue $pattrs 'Load'

        if ([string]::IsNullOrEmpty($popName)) {
            Add-Finding -Severity Error -Kind Population -Rule 'missing-name' -ModName $modName -File $rel -Line $popLine `
                -Message '<population> missing required Name' -HighPriority
            continue
        }

        if ($load -and $load.Equals('Replace', [StringComparison]::OrdinalIgnoreCase) -and $basePops.Contains($popName)) {
            Add-Finding -Severity Warn -Kind Population -Rule 'replace-base' -ModName $modName -File $rel -Line $popLine `
                -Message "Load=`"Replace`" on base population '$popName' (can wipe worldgen/chargen tables)" -Population $popName
        }

        # Duplicate group names within this population
        $groupNames = @{}
        foreach ($gm in [regex]::Matches($body, '(?is)<\s*group\b([^>]*)>')) {
            $gattrs = $gm.Groups[1].Value
            $gName = Get-AttrValue $gattrs 'Name'
            $gLine = $popLine
            if ([string]::IsNullOrEmpty($gName)) {
                Add-Finding -Severity Error -Kind Population -Rule 'missing-group-name' -ModName $modName -File $rel -Line $gLine `
                    -Message "<population Name=`"$popName`"> contains <group> without Name" -Population $popName -HighPriority
                continue
            }
            if ($groupNames.ContainsKey($gName)) {
                Add-Finding -Severity Error -Kind Population -Rule 'duplicate-group' -ModName $modName -File $rel -Line $gLine `
                    -Message "Duplicate group name '$gName' inside population '$popName'" -Population $popName -HighPriority
                [void]$errorPopulations.Add($popName)
            } else {
                $groupNames[$gName] = $true
            }
        }

        # Empty pickone under StartingGear_*
        if ($popName.StartsWith('StartingGear_', [StringComparison]::OrdinalIgnoreCase)) {
            foreach ($gm in [regex]::Matches($body, '(?is)<\s*group\b([^>]*)>(.*?)</\s*group\s*>')) {
                $gattrs = $gm.Groups[1].Value
                $gbody = $gm.Groups[2].Value
                $style = Get-AttrValue $gattrs 'Style'
                if ($style -and $style.Equals('pickone', [StringComparison]::OrdinalIgnoreCase)) {
                    $hasChild = $gbody -match '(?i)<\s*(object|table)\b'
                    if (-not $hasChild) {
                        $gLine = Get-LineNumberAtIndex $text ($pm.Groups[2].Index + $gm.Index)
                        Add-Finding -Severity Error -Kind Population -Rule 'empty-pickone-startinggear' -ModName $modName -File $rel -Line $gLine `
                            -Message "Empty pickone group in StartingGear population '$popName'" -Population $popName -HighPriority
                        [void]$errorPopulations.Add($popName)
                    }
                }
            }
        }

        # Empty population (no object/table/group with children content)
        if ($body -notmatch '(?i)<\s*(object|table|group)\b') {
            Add-Finding -Severity Warn -Kind Population -Rule 'empty-population' -ModName $modName -File $rel -Line $popLine `
                -Message "Population '$popName' has no object/table/group children" -Population $popName
        }

        # Empty merge groups
        foreach ($gm in [regex]::Matches($body, '(?is)<\s*group\b([^>]*)>(.*?)</\s*group\s*>')) {
            $gattrs = $gm.Groups[1].Value
            $gbody = $gm.Groups[2].Value
            $gName = Get-AttrValue $gattrs 'Name'
            $gLoad = Get-AttrValue $gattrs 'Load'
            if ($gLoad -and $gLoad.Equals('Merge', [StringComparison]::OrdinalIgnoreCase) -and ($gbody -notmatch '(?i)<\s*(object|table|group)\b')) {
                $gLine = Get-LineNumberAtIndex $text ($pm.Groups[2].Index + $gm.Index)
                Add-Finding -Severity Warn -Kind Population -Rule 'empty-merge-group' -ModName $modName -File $rel -Line $gLine `
                    -Message "Empty Merge group '$gName' in population '$popName'" -Population $popName
            }
        }

        $refs = [System.Collections.Generic.List[string]]::new()

        # Tables
        foreach ($tm in [regex]::Matches($body, '(?is)<\s*table\b([^>]*)/?>')) {
            $tattrs = $tm.Groups[1].Value
            $tName = Get-AttrValue $tattrs 'Name'
            $tLoad = Get-AttrValue $tattrs 'Load'
            $tLine = $popLine
            $num = Get-AttrValue $tattrs 'Number'
            $isRemove = $tLoad -and $tLoad.Equals('Remove', [StringComparison]::OrdinalIgnoreCase)

            if ([string]::IsNullOrEmpty($tName)) {
                Add-Finding -Severity Warn -Kind Population -Rule 'table-missing-name' -ModName $modName -File $rel -Line $tLine `
                    -Message "<table> missing Name in population '$popName'" -Population $popName
                continue
            }

            # Load=Remove is a merge patch, not a recursive roll.
            if ($tName -ceq $popName -and -not $isRemove) {
                Add-Finding -Severity Error -Kind Population -Rule 'self-ref-table' -ModName $modName -File $rel -Line $tLine `
                    -Message "Self-referential <table Name=`"$tName`"/> inside population '$popName'" -Population $popName -HighPriority
                [void]$errorPopulations.Add($popName)
            } elseif (-not $isRemove) {
                $refs.Add($tName)
            }

            if (Test-NumberNonPositive $num) {
                Add-Finding -Severity Warn -Kind Population -Rule 'nonpositive-number' -ModName $modName -File $rel -Line $tLine `
                    -Message "Number=`"$num`" on table '$tName' in '$popName'" -Population $popName
            }

            if (-not (Test-IsDynamicTable $tName)) {
                if (-not $popIndex.Exact.Contains($tName)) {
                    $canon = Find-CaseMismatch $tName $popIndex.Exact $popIndex.Lower
                    if ($canon) {
                        Add-Finding -Severity Warn -Kind Population -Rule 'table-case-mismatch' -ModName $modName -File $rel -Line $tLine `
                            -Message "Table '$tName' not found; case mismatch with '$canon'" -Population $popName
                    } else {
                        Add-Finding -Severity Warn -Kind Population -Rule 'unknown-table' -ModName $modName -File $rel -Line $tLine `
                            -Message "Unknown population table '$tName' referenced from '$popName'" -Population $popName
                    }
                }
            }
        }

        # Objects
        foreach ($om in [regex]::Matches($body, '(?is)<\s*object\b([^>]*)/?>')) {
            $oattrs = $om.Groups[1].Value
            $bp = Get-AttrValue $oattrs 'Blueprint'
            $oLine = Get-LineNumberAtIndex $text ($pm.Groups[2].Index + $om.Index)
            $num = Get-AttrValue $oattrs 'Number'

            if ([string]::IsNullOrEmpty($bp)) {
                Add-Finding -Severity Warn -Kind Population -Rule 'null-blueprint' -ModName $modName -File $rel -Line $oLine `
                    -Message "<object> missing Blueprint in population '$popName'" -Population $popName
            } elseif (-not $bpIndex.Exact.Contains($bp)) {
                $canon = Find-CaseMismatch $bp $bpIndex.Exact $bpIndex.Lower
                if ($canon) {
                    Add-Finding -Severity Warn -Kind Population -Rule 'blueprint-case-mismatch' -ModName $modName -File $rel -Line $oLine `
                        -Message "Blueprint '$bp' not found; case mismatch with '$canon'" -Population $popName
                } else {
                    Add-Finding -Severity Warn -Kind Population -Rule 'unknown-blueprint' -ModName $modName -File $rel -Line $oLine `
                        -Message "Unknown blueprint '$bp' in population '$popName'" -Population $popName
                }
            }

            if (Test-NumberNonPositive $num) {
                Add-Finding -Severity Warn -Kind Population -Rule 'nonpositive-number' -ModName $modName -File $rel -Line $oLine `
                    -Message "Number=`"$num`" on object '$bp' in '$popName'" -Population $popName
            }
        }

        $edges[$popName] = $refs
    }

    # Cycle detection among populations defined in this file that reference each other
    $defined = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
    foreach ($k in $edges.Keys) { [void]$defined.Add($k) }
    $state = @{} # 0=unseen 1=stack 2=done
    $path = [System.Collections.Generic.List[string]]::new()
    $stackNodes = [System.Collections.Generic.Stack[string]]::new()

    foreach ($start in @($defined)) {
        if ($state.ContainsKey($start)) { continue }
        $stackNodes.Push($start)
        while ($stackNodes.Count -gt 0) {
            $node = $stackNodes.Peek()
            if (-not $state.ContainsKey($node)) {
                $state[$node] = 1
                $path.Add($node)
                $pushed = $false
                if ($edges.ContainsKey($node)) {
                    foreach ($n in $edges[$node]) {
                        if (-not $defined.Contains($n)) { continue }
                        if ($state.ContainsKey($n) -and $state[$n] -eq 1) {
                            $cycleStart = $path.IndexOf($n)
                            if ($cycleStart -ge 0) {
                                $parts = [System.Collections.Generic.List[string]]::new()
                                for ($i = $cycleStart; $i -lt $path.Count; $i++) { $parts.Add($path[$i]) }
                                $parts.Add($n)
                                $cycle = ($parts -join ' -> ')
                                Add-Finding -Severity Error -Kind Population -Rule 'table-cycle' -ModName $modName -File $rel -Line 1 `
                                    -Message "Population table cycle: $cycle" -Population $n -HighPriority
                                [void]$errorPopulations.Add($n)
                            }
                        } elseif (-not $state.ContainsKey($n)) {
                            $stackNodes.Push($n)
                            $pushed = $true
                            break
                        }
                    }
                }
                if ($pushed) { continue }
            }
            if ($state.ContainsKey($node) -and $state[$node] -eq 1) {
                $state[$node] = 2
                if ($path.Count -gt 0 -and $path[$path.Count - 1] -ceq $node) {
                    [void]$path.RemoveAt($path.Count - 1)
                }
            }
            [void]$stackNodes.Pop()
        }
    }

    return $raw
}

# --- genotype validation ---

function Test-GenotypeFile([string]$filePath, [string]$modName, $popIndex, $bpIndex, $classIndex, [System.Collections.Generic.HashSet[string]]$errorPopulations) {
    $stats.GenotypeFiles++
    $raw = Read-TextLossless $filePath
    $text = $raw.Text

    if (-not (Test-RootEncoding $text 'genotypes')) {
        Add-Finding -Severity Warn -Kind Genotype -Rule 'missing-encoding' -ModName $modName -File $filePath -Line 1 `
            -Message 'Root <genotypes> missing Encoding="utf-8"'
    }

    foreach ($m in [regex]::Matches($text, '(?is)<\s*genotype\b([^>]*)(/?)>')) {
        $attrs = $m.Groups[1].Value
        $line = Get-LineNumberAtIndex $text $m.Index
        $name = Get-AttrValue $attrs 'Name'

        if ([string]::IsNullOrEmpty($name)) {
            Add-Finding -Severity Error -Kind Genotype -Rule 'missing-name' -ModName $modName -File $filePath -Line $line `
                -Message '<genotype> missing required Name' -HighPriority
            continue
        }
        if ($name.StartsWith('-')) { continue }

        if (-not (Test-HasAttr $attrs 'Subtypes')) {
            Add-Finding -Severity Warn -Kind Genotype -Rule 'missing-subtypes-attr' -ModName $modName -File $filePath -Line $line `
                -Message "Genotype '$name' has no Subtypes attribute"
        } else {
            $subClass = Get-AttrValue $attrs 'Subtypes'
            if (-not [string]::IsNullOrWhiteSpace($subClass)) {
                if (-not $classIndex.Exact.Contains($subClass)) {
                    $canon = Find-CaseMismatch $subClass $classIndex.Exact $classIndex.Lower
                    if ($canon) {
                        Add-Finding -Severity Warn -Kind Genotype -Rule 'subtype-class-case' -ModName $modName -File $filePath -Line $line `
                            -Message "Genotype '$name' Subtypes='$subClass' case-mismatches class '$canon'"
                    } else {
                        Add-Finding -Severity Error -Kind Genotype -Rule 'unknown-subtype-class' -ModName $modName -File $filePath -Line $line `
                            -Message "Genotype '$name' Subtypes='$subClass' — no subtype class ID found" -HighPriority
                    }
                }
            }
        }

        $gear = Get-AttrValue $attrs 'Gear'
        if (-not [string]::IsNullOrWhiteSpace($gear)) {
            if (-not $popIndex.Exact.Contains($gear)) {
                $canon = Find-CaseMismatch $gear $popIndex.Exact $popIndex.Lower
                if ($canon) {
                    Add-Finding -Severity Warn -Kind Genotype -Rule 'gear-case-mismatch' -ModName $modName -File $filePath -Line $line `
                        -Message "Genotype '$name' Gear='$gear' case-mismatches population '$canon'"
                } else {
                    Add-Finding -Severity Error -Kind Genotype -Rule 'missing-gear-population' -ModName $modName -File $filePath -Line $line `
                        -Message "Genotype '$name' Gear='$gear' — population table not found" -Population $gear -HighPriority
                }
            } elseif ($errorPopulations.Contains($gear)) {
                Add-Finding -Severity Error -Kind Genotype -Rule 'gear-population-broken' -ModName $modName -File $filePath -Line $line `
                    -Message "Genotype '$name' Gear='$gear' points at a population with Error-level issues" -Population $gear -HighPriority
            }
        }

        $body = Get-AttrValue $attrs 'BodyObject'
        if (-not [string]::IsNullOrWhiteSpace($body)) {
            if (-not $bpIndex.Exact.Contains($body)) {
                $canon = Find-CaseMismatch $body $bpIndex.Exact $bpIndex.Lower
                if ($canon) {
                    Add-Finding -Severity Warn -Kind Genotype -Rule 'body-case-mismatch' -ModName $modName -File $filePath -Line $line `
                        -Message "Genotype '$name' BodyObject='$body' case-mismatches blueprint '$canon'"
                } else {
                    Add-Finding -Severity Warn -Kind Genotype -Rule 'unknown-bodyobject' -ModName $modName -File $filePath -Line $line `
                        -Message "Genotype '$name' BodyObject='$body' not in blueprint index"
                }
            }
        }

        if (Test-HasAttr $attrs 'Skills') {
            Add-Finding -Severity Warn -Kind Genotype -Rule 'obsolete-skills-attr' -ModName $modName -File $filePath -Line $line `
                -Message "Genotype '$name' uses obsolete Skills= attribute; prefer <skill> nodes"
        }
        if (Test-HasAttr $attrs 'Reputation') {
            Add-Finding -Severity Warn -Kind Genotype -Rule 'obsolete-reputation-attr' -ModName $modName -File $filePath -Line $line `
                -Message "Genotype '$name' uses obsolete Reputation= attribute; prefer <reputation> nodes"
        }
    }

    return $raw
}

# --- subtype validation ---

function Test-SubtypeFile([string]$filePath, [string]$modName, [string]$modRoot, $popIndex, $bpIndex, [System.Collections.Generic.HashSet[string]]$errorPopulations) {
    $stats.SubtypeFiles++
    $raw = Read-TextLossless $filePath
    $text = $raw.Text

    if (-not (Test-RootEncoding $text 'subtypes')) {
        Add-Finding -Severity Warn -Kind Subtype -Rule 'missing-encoding' -ModName $modName -File $filePath -Line 1 `
            -Message 'Root <subtypes> missing Encoding="utf-8"'
    }

    # Class blocks
    foreach ($cm in [regex]::Matches($text, '(?is)<\s*class\b([^>]*)>(.*?)</\s*class\s*>')) {
        $cattrs = $cm.Groups[1].Value
        $cbody = $cm.Groups[2].Value
        $cLine = Get-LineNumberAtIndex $text $cm.Index
        $classId = Get-AttrValue $cattrs 'ID'

        if ([string]::IsNullOrEmpty($classId)) {
            Add-Finding -Severity Error -Kind Subtype -Rule 'missing-class-id' -ModName $modName -File $filePath -Line $cLine `
                -Message '<class> missing required ID' -HighPriority
            $classId = '(unnamed)'
        }

        if ((Test-HasAttr $cattrs 'DisplayName') -and -not (Test-HasAttr $cattrs 'ChargenTitle')) {
            Add-Finding -Severity Warn -Kind Subtype -Rule 'class-displayname-unused' -ModName $modName -File $filePath -Line $cLine `
                -Message "<class ID=`"$classId`"> has DisplayName without ChargenTitle (UI uses ChargenTitle)"
        }

        $subtypeCount = ([regex]::Matches($cbody, '(?is)<\s*subtype\b')).Count
        if ($subtypeCount -eq 0) {
            # Common for title-only Merge patches against base Callings/Castes — warn, not error.
            Add-Finding -Severity Warn -Kind Subtype -Rule 'empty-class' -ModName $modName -File $filePath -Line $cLine `
                -Message "<class ID=`"$classId`"> has zero <subtype> children (ok if merging into an existing class)"
        }

        foreach ($sm in [regex]::Matches($cbody, '(?is)<\s*subtype\b([^>]*)(/?)>')) {
            $sattrs = $sm.Groups[1].Value
            $sLine = Get-LineNumberAtIndex $text ($cm.Groups[2].Index + $sm.Index)
            $sName = Get-AttrValue $sattrs 'Name'

            if ([string]::IsNullOrEmpty($sName)) {
                Add-Finding -Severity Error -Kind Subtype -Rule 'missing-subtype-name' -ModName $modName -File $filePath -Line $sLine `
                    -Message "<class ID=`"$classId`"> contains <subtype> without Name" -HighPriority
                continue
            }

            $gear = Get-AttrValue $sattrs 'Gear'
            if (-not [string]::IsNullOrWhiteSpace($gear)) {
                if (-not $popIndex.Exact.Contains($gear)) {
                    $canon = Find-CaseMismatch $gear $popIndex.Exact $popIndex.Lower
                    if ($canon) {
                        Add-Finding -Severity Warn -Kind Subtype -Rule 'gear-case-mismatch' -ModName $modName -File $filePath -Line $sLine `
                            -Message "Subtype '$sName' Gear='$gear' case-mismatches population '$canon'"
                    } else {
                        Add-Finding -Severity Error -Kind Subtype -Rule 'missing-gear-population' -ModName $modName -File $filePath -Line $sLine `
                            -Message "Subtype '$sName' Gear='$gear' — population table not found" -Population $gear -HighPriority
                    }
                } elseif ($errorPopulations.Contains($gear)) {
                    Add-Finding -Severity Error -Kind Subtype -Rule 'gear-population-broken' -ModName $modName -File $filePath -Line $sLine `
                        -Message "Subtype '$sName' Gear='$gear' points at a population with Error-level issues" -Population $gear -HighPriority
                }
            }

            $body = Get-AttrValue $sattrs 'BodyObject'
            if (-not [string]::IsNullOrWhiteSpace($body)) {
                if (-not $bpIndex.Exact.Contains($body)) {
                    $canon = Find-CaseMismatch $body $bpIndex.Exact $bpIndex.Lower
                    if ($canon) {
                        Add-Finding -Severity Warn -Kind Subtype -Rule 'body-case-mismatch' -ModName $modName -File $filePath -Line $sLine `
                            -Message "Subtype '$sName' BodyObject='$body' case-mismatches blueprint '$canon'"
                    } else {
                        Add-Finding -Severity Warn -Kind Subtype -Rule 'unknown-bodyobject' -ModName $modName -File $filePath -Line $sLine `
                            -Message "Subtype '$sName' BodyObject='$body' not in blueprint index"
                    }
                }
            }

            if (Test-HasAttr $sattrs 'Foreground') {
                Add-Finding -Severity Warn -Kind Subtype -Rule 'unused-foreground' -ModName $modName -File $filePath -Line $sLine `
                    -Message "Subtype '$sName' has unused attribute Foreground"
            }
            if (Test-HasAttr $sattrs 'Skills') {
                Add-Finding -Severity Warn -Kind Subtype -Rule 'obsolete-skills-attr' -ModName $modName -File $filePath -Line $sLine `
                    -Message "Subtype '$sName' uses obsolete Skills= attribute; prefer <skill> nodes"
            }
            if (Test-HasAttr $sattrs 'Reputation') {
                Add-Finding -Severity Warn -Kind Subtype -Rule 'obsolete-reputation-attr' -ModName $modName -File $filePath -Line $sLine `
                    -Message "Subtype '$sName' uses obsolete Reputation= attribute; prefer <reputation> nodes"
            }
            if (Test-HasAttr $sattrs 'SaveModifierVs') {
                Add-Finding -Severity Warn -Kind Subtype -Rule 'obsolete-savemodifier' -ModName $modName -File $filePath -Line $sLine `
                    -Message "Subtype '$sName' uses obsolete SaveModifierVs attribute"
            }

            $tile = Get-AttrValue $sattrs 'Tile'
            if (-not [string]::IsNullOrWhiteSpace($tile) -and ($tile -match '[/\\.]')) {
                $normTile = $tile.Replace('/', [IO.Path]::DirectorySeparatorChar).Replace('\', [IO.Path]::DirectorySeparatorChar)
                $candidates = @(
                    (Join-Path $modRoot $normTile),
                    (Join-Path (Split-Path -Parent $filePath) $normTile)
                )
                $found = $false
                foreach ($c in $candidates) {
                    if (Test-Path -LiteralPath $c) { $found = $true; break }
                }
                if (-not $found) {
                    Add-Finding -Severity Warn -Kind Subtype -Rule 'missing-tile-file' -ModName $modName -File $filePath -Line $sLine `
                        -Message "Subtype '$sName' Tile='$tile' — file not found under mod"
                }
            }
        }
    }

    return $raw
}

# --- apply fixes ---

function Backup-IfNeeded([string]$filePath) {
    if ($NoBackup) { return }
    $bak = "$filePath.bak"
    Copy-Item -LiteralPath $filePath -Destination $bak -Force
}

function Apply-PopulationStructuralFixes([string]$text, [System.Collections.Generic.List[string]]$fixNotes) {
    $popPattern = [regex]'(?is)<\s*population\b([^>]*)>(.*?)</\s*population\s*>'
    $matches = $popPattern.Matches($text)
    if ($matches.Count -eq 0) { return $text }

    $sb = [System.Text.StringBuilder]::new()
    $last = 0
    $removedSelf = 0
    $renamedGroups = 0

    foreach ($pm in $matches) {
        [void]$sb.Append($text.Substring($last, $pm.Index - $last))
        $pattrs = $pm.Groups[1].Value
        $body = $pm.Groups[2].Value
        $popName = Get-AttrValue $pattrs 'Name'
        $openLen = $pm.Groups[2].Index - $pm.Index
        $open = $text.Substring($pm.Index, $openLen)
        $close = $pm.Value.Substring($openLen + $body.Length)

        if (-not [string]::IsNullOrEmpty($popName)) {
            $tablePattern = [regex]'(?is)(\s*)<\s*table\b([^>]*)/\s*>'
            $bodySb = [System.Text.StringBuilder]::new()
            $tLast = 0
            foreach ($tm in $tablePattern.Matches($body)) {
                [void]$bodySb.Append($body.Substring($tLast, $tm.Index - $tLast))
                $tName = Get-AttrValue $tm.Groups[2].Value 'Name'
                $tLoad = Get-AttrValue $tm.Groups[2].Value 'Load'
                $isRemove = $tLoad -and $tLoad.Equals('Remove', [StringComparison]::OrdinalIgnoreCase)
                if ($tName -ceq $popName -and -not $isRemove) {
                    $removedSelf++
                    [void]$bodySb.Append($tm.Groups[1].Value)
                    [void]$bodySb.Append("<!-- removed self-ref population table: $popName -->")
                } else {
                    [void]$bodySb.Append($tm.Value)
                }
                $tLast = $tm.Index + $tm.Length
            }
            [void]$bodySb.Append($body.Substring($tLast))
            $body = $bodySb.ToString()

            $seen = @{}
            $groupPattern = [regex]'(?is)<\s*group\b([^>]*)>'
            $bodySb = [System.Text.StringBuilder]::new()
            $gLast = 0
            foreach ($gm in $groupPattern.Matches($body)) {
                [void]$bodySb.Append($body.Substring($gLast, $gm.Index - $gLast))
                $gattrs = $gm.Groups[1].Value
                $gName = Get-AttrValue $gattrs 'Name'
                if (-not [string]::IsNullOrEmpty($gName) -and $seen.ContainsKey($gName)) {
                    $seen[$gName] = [int]$seen[$gName] + 1
                    $newName = "${gName}_dup$($seen[$gName])"
                    $renamedGroups++
                    $newAttrs = [regex]::Replace($gattrs, '(?i)\bName\s*=\s*"[^"]*"', "Name=`"$newName`"")
                    [void]$bodySb.Append("<group$newAttrs>")
                } else {
                    if (-not [string]::IsNullOrEmpty($gName)) { $seen[$gName] = 0 }
                    [void]$bodySb.Append($gm.Value)
                }
                $gLast = $gm.Index + $gm.Length
            }
            [void]$bodySb.Append($body.Substring($gLast))
            $body = $bodySb.ToString()
        }

        [void]$sb.Append($open)
        [void]$sb.Append($body)
        [void]$sb.Append($close)
        $last = $pm.Index + $pm.Length
    }
    [void]$sb.Append($text.Substring($last))

    if ($removedSelf -gt 0) { $fixNotes.Add("Removed $removedSelf self-ref <table> node(s)") }
    if ($renamedGroups -gt 0) { $fixNotes.Add("Renamed $renamedGroups duplicate group Name(s) with _dupN suffix") }
    return $sb.ToString()
}

function Apply-SubtypeClassTitleFix([string]$text, [System.Collections.Generic.List[string]]$fixNotes) {
    $pattern = [regex]'(?is)<\s*class\b([^>]*)>'
    $matches = $pattern.Matches($text)
    if ($matches.Count -eq 0) { return $text }
    $sb = [System.Text.StringBuilder]::new()
    $last = 0
    $n = 0
    foreach ($m in $matches) {
        [void]$sb.Append($text.Substring($last, $m.Index - $last))
        $attrs = $m.Groups[1].Value
        if ((Test-HasAttr $attrs 'DisplayName') -and -not (Test-HasAttr $attrs 'ChargenTitle')) {
            $n++
            $newAttrs = [regex]::Replace($attrs, '(?i)\bDisplayName\s*=', 'ChargenTitle=')
            [void]$sb.Append("<class$newAttrs>")
        } else {
            [void]$sb.Append($m.Value)
        }
        $last = $m.Index + $m.Length
    }
    [void]$sb.Append($text.Substring($last))
    if ($n -gt 0) { $fixNotes.Add("Renamed $n class DisplayName= to ChargenTitle=") }
    return $sb.ToString()
}

function Apply-ChargenFixes([string]$filePath, [string]$kind) {
    $raw = Read-TextLossless $filePath
    $text = $raw.Text
    $original = $text
    $fixNotes = [System.Collections.Generic.List[string]]::new()

    $rootName = switch ($kind) {
        'Population' { 'populations' }
        'Genotype' { 'genotypes' }
        'Subtype' { 'subtypes' }
        default { $null }
    }
    if ($rootName) {
        $withEnc = Try-InsertEncoding $text $rootName
        if ($null -ne $withEnc) {
            $text = $withEnc
            $fixNotes.Add("Inserted Encoding=`"utf-8`" on <$rootName>")
        }
    }

    if ($kind -eq 'Population') {
        $text = Apply-PopulationStructuralFixes $text $fixNotes
    }
    if ($kind -eq 'Subtype') {
        $text = Apply-SubtypeClassTitleFix $text $fixNotes
    }

    if ($text -ceq $original) { return $false }

    Backup-IfNeeded $filePath
    Write-TextLossless $raw $text $filePath
    foreach ($n in $fixNotes) {
        $applied.Add([pscustomobject]@{ File = $filePath; Note = $n })
        $stats.AppliedFixes++
    }
    if ($fixNotes.Count -eq 0) {
        $applied.Add([pscustomobject]@{ File = $filePath; Note = 'Applied structural fixes' })
        $stats.AppliedFixes++
    }
    return $true
}

function Write-MarkdownReport([string]$reportPath) {
    $dir = Split-Path -Parent $reportPath
    if ($dir -and -not (Test-Path -LiteralPath $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }

    $sb = [System.Text.StringBuilder]::new()
    [void]$sb.AppendLine("# Chargen XML validation report")
    [void]$sb.AppendLine("")
    [void]$sb.AppendLine("Generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')")
    [void]$sb.AppendLine("Mode: $(if ($Apply) { 'Apply' } else { 'Dry-run' })")
    [void]$sb.AppendLine("")
    [void]$sb.AppendLine("## Summary")
    [void]$sb.AppendLine("")
    [void]$sb.AppendLine("| Metric | Count |")
    [void]$sb.AppendLine("|---|---:|")
    foreach ($k in $stats.Keys) {
        [void]$sb.AppendLine("| $k | $($stats[$k]) |")
    }
    [void]$sb.AppendLine("")

    $high = @($findings | Where-Object { $_.HighPriority -or ($_.Severity -eq 'Error' -and (
        $_.Rule -match 'gear|self-ref|cycle|duplicate-group|empty-pickone|unknown-subtype|missing-gear|gear-population'
    )) })
    if ($high.Count -gt 0) {
        [void]$sb.AppendLine("## Highest priority")
        [void]$sb.AppendLine("")
        foreach ($f in ($high | Sort-Object ModName, Kind, Line)) {
            $loc = if ($f.Line -gt 0) { ":$($f.Line)" } else { '' }
            [void]$sb.AppendLine("- **$($f.Severity)** [$($f.Kind)/$($f.Rule)] $($f.ModName) — ``$($f.File)$loc`` — $($f.Message)")
        }
        [void]$sb.AppendLine("")
    }

    if ($applied.Count -gt 0) {
        [void]$sb.AppendLine("## Applied fixes")
        [void]$sb.AppendLine("")
        foreach ($a in $applied) {
            [void]$sb.AppendLine("- ``$($a.File)`` — $($a.Note)")
        }
        [void]$sb.AppendLine("")
    }

    foreach ($kind in @('Population', 'Genotype', 'Subtype')) {
        $group = @($findings | Where-Object { $_.Kind -eq $kind } | Sort-Object ModName, File, Line)
        if ($group.Count -eq 0) { continue }
        [void]$sb.AppendLine("## $kind")
        [void]$sb.AppendLine("")
        $byMod = $group | Group-Object ModName
        foreach ($modGroup in $byMod) {
            [void]$sb.AppendLine("### $($modGroup.Name)")
            [void]$sb.AppendLine("")
            foreach ($f in $modGroup.Group) {
                $loc = if ($f.Line -gt 0) { ":$($f.Line)" } else { '' }
                [void]$sb.AppendLine("- **$($f.Severity)** ``$($f.Rule)`` — ``$($f.File)$loc`` — $($f.Message)")
            }
            [void]$sb.AppendLine("")
        }
    }

    if ($findings.Count -eq 0) {
        [void]$sb.AppendLine("_No issues found._")
        [void]$sb.AppendLine("")
    }

    [System.IO.File]::WriteAllText($reportPath, $sb.ToString(), [System.Text.UTF8Encoding]::new($false))
}

# ===================== MAIN =====================

Write-Host "Scan roots:"
foreach ($p in $Path) { Write-Host "  $p" }

$popIndex = New-NameIndex
$bpIndex = New-NameIndex
$classIndex = New-NameIndex
$subtypeIndex = New-NameIndex
$genoIndex = New-NameIndex
$basePops = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)

Write-Host "Indexing Base / DLC (read-only)..."
$indexRoots = [System.Collections.Generic.List[string]]::new()
if (Test-Path -LiteralPath $BasePath) { $indexRoots.Add([System.IO.Path]::GetFullPath($BasePath)) }
if ($DlcPath -and (Test-Path -LiteralPath $DlcPath)) { $indexRoots.Add([System.IO.Path]::GetFullPath($DlcPath)) }
$baseFull = if (Test-Path -LiteralPath $BasePath) { [System.IO.Path]::GetFullPath($BasePath) } else { '' }

foreach ($ir in $indexRoots) {
    $isBase = ($ir -eq $baseFull)
    foreach ($f in (Get-FilesRecursive $ir @('PopulationTables.xml', '*Population*.xml'))) {
        $leaf = [System.IO.Path]::GetFileName($f)
        if ($leaf -like 'ObjectBlueprint*') { continue }
        if ($isBase) {
            Index-PopulationsFromFile $f $popIndex $basePops -AsBase
        } else {
            Index-PopulationsFromFile $f $popIndex
        }
    }
    foreach ($f in (Get-BlueprintXmlFiles $ir)) {
        Index-BlueprintsFromFile $f $bpIndex
        $stats.BlueprintFiles++
    }
    foreach ($f in (Get-FilesRecursive $ir @('Subtypes.xml'))) {
        Index-SubtypesFromFile $f $classIndex $subtypeIndex
    }
    foreach ($f in (Get-FilesRecursive $ir @('Genotypes.xml'))) {
        Index-GenotypesFromFile $f $genoIndex
    }
}

Write-Host "Discovering mods..."
$modUnits = @(Get-ModUnits $Path $Mod)
Write-Host "Mod folders: $($modUnits.Count)"

# First pass: index all scanned mods into global indexes
foreach ($unit in $modUnits) {
    $files = Get-ChargenXmlFiles $unit.Root
    foreach ($f in $files.Populations) { Index-PopulationsFromFile $f $popIndex }
    foreach ($f in $files.Genotypes) { Index-GenotypesFromFile $f $genoIndex }
    foreach ($f in $files.Subtypes) { Index-SubtypesFromFile $f $classIndex $subtypeIndex }
    foreach ($f in (Get-BlueprintXmlFiles $unit.Root)) {
        Index-BlueprintsFromFile $f $bpIndex
        $stats.BlueprintFiles++
    }
}

$stats.PopulationsIndexed = $popIndex.Exact.Count
$stats.BlueprintsIndexed = $bpIndex.Exact.Count
$stats.SubtypeClassesIndexed = $classIndex.Exact.Count
$stats.SubtypesIndexed = $subtypeIndex.Exact.Count
$stats.GenotypesIndexed = $genoIndex.Exact.Count

Write-Host "Index: $($stats.PopulationsIndexed) populations, $($stats.BlueprintsIndexed) blueprints, $($stats.SubtypeClassesIndexed) subtype classes, $($stats.GenotypesIndexed) genotypes"

# Apply safe fixes first so the report/exit code reflect post-fix state.
if ($Apply) {
    Write-Host "Applying safe fixes..."
    foreach ($unit in $modUnits) {
        $files = Get-ChargenXmlFiles $unit.Root
        foreach ($f in $files.Populations) { [void](Apply-ChargenFixes $f 'Population') }
        foreach ($f in $files.Genotypes) { [void](Apply-ChargenFixes $f 'Genotype') }
        foreach ($f in $files.Subtypes) { [void](Apply-ChargenFixes $f 'Subtype') }
    }
}

$errorPopulations = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)

# Validate (populations first so gear cross-link sees error pops)
Write-Host "Validating..."
foreach ($unit in $modUnits) {
    $stats.ModsScanned++
    $files = Get-ChargenXmlFiles $unit.Root
    foreach ($f in $files.Populations) {
        $null = Test-PopulationFile $f $unit.Name $popIndex $bpIndex $basePops $errorPopulations
    }
}

foreach ($unit in $modUnits) {
    $files = Get-ChargenXmlFiles $unit.Root
    foreach ($f in $files.Genotypes) {
        $null = Test-GenotypeFile $f $unit.Name $popIndex $bpIndex $classIndex $errorPopulations
    }
    foreach ($f in $files.Subtypes) {
        $null = Test-SubtypeFile $f $unit.Name $unit.Root $popIndex $bpIndex $errorPopulations
    }
}

Write-MarkdownReport $Report

Write-Host ""
Write-Host "=== Chargen XML validation ==="
Write-Host "Mods scanned:        $($stats.ModsScanned)"
Write-Host "Population files:    $($stats.PopulationFiles)"
Write-Host "Genotype files:      $($stats.GenotypeFiles)"
Write-Host "Subtype files:       $($stats.SubtypeFiles)"
Write-Host "Errors:              $($stats.Errors)"
Write-Host "Warnings:            $($stats.Warns)"
Write-Host "Applied fixes:       $($stats.AppliedFixes)"
Write-Host "Report:              $Report"

if ($stats.Errors -gt 0) { exit 1 }
exit 0

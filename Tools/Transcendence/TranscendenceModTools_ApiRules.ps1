<#
.SYNOPSIS
  Self-Updating API Rules Engine for Transcendence Mod Tools
  
.DESCRIPTION
  This module extracts API definitions from the game's source files and
  generates a comprehensive ruleset (JSON) that validators use to:
  - Detect deprecated tags/attributes/functions
  - Validate semantic expectations
  - Suggest replacements during migration
  
  The tool watches source folders and auto-updates when the game updates.
  
.NOTES
  Version: 1.0
  Author: Transcendence Mod Tools
#>

# ============================================================
# CONFIGURATION
# ============================================================

$script:ApiRulesPath = Join-Path $PSScriptRoot "api_rules.json"
$script:ApiRulesVersion = "1.0"

# Base source directory
$script:SourceBaseDir = "D:\games\Steam\steamapps\common\Transcendence\game and dlc source"

# Main source folder (Steam updates this)
$script:MainSourceFolder = "D:\games\Steam\steamapps\common\Transcendence\game and dlc source\Transcendence_Source"

# Detect API version from source files
function Get-SourceApiVersion {
    <#
    .SYNOPSIS
      Detects the API version from Transcendence_Source by reading apiVersion attributes
    #>
    param([string]$SourcePath = $script:MainSourceFolder)
    
    if (-not (Test-Path $SourcePath)) {
        return $null
    }
    
    # Look for apiVersion in main files first
    $mainFiles = @(
        "Transcendence.xml",
        "StarsOfThePilgrim.xml",
        "CoreTypesLibrary.xml"
    )
    
    foreach ($fileName in $mainFiles) {
        $filePath = Join-Path $SourcePath $fileName
        if (Test-Path $filePath) {
            try {
                $content = Get-Content $filePath -Raw -ErrorAction SilentlyContinue
                if ($content -match 'apiVersion\s*=\s*["\x27](\d+)["\x27]') {
                    return [int]$matches[1]
                }
            }
            catch { }
        }
    }
    
    # Fallback: scan any XML file
    $xmlFiles = Get-ChildItem -LiteralPath $SourcePath -Filter "*.xml" -ErrorAction SilentlyContinue | Select-Object -First 20
    foreach ($file in $xmlFiles) {
        try {
            $content = Get-Content $file.FullName -Raw -ErrorAction SilentlyContinue
            if ($content -match 'apiVersion\s*=\s*["\x27](\d+)["\x27]') {
                return [int]$matches[1]
            }
        }
        catch { }
    }
    
    return $null
}

# Default API version - auto-detect from source, fallback to 57
$script:DetectedApiVersion = Get-SourceApiVersion
$script:DefaultApiVersion = if ($script:DetectedApiVersion) { $script:DetectedApiVersion } else { 57 }

# Auto-detect available API versions from source folders
function Get-AvailableApiVersions {
    <#
    .SYNOPSIS
      Auto-detects available API versions from source folders
    #>
    param([string]$BaseDir = $script:SourceBaseDir)
    
    $versions = @{}
    
    if (-not (Test-Path $BaseDir)) {
        Write-Warning "Source base directory not found: $BaseDir"
        return $versions
    }
    
    # Find all TranscendenceDev-* folders
    $devFolders = Get-ChildItem -LiteralPath $BaseDir -Directory -ErrorAction SilentlyContinue | Where-Object {
        $_.Name -like "TranscendenceDev-*"
    }
    
    foreach ($folder in $devFolders) {
        $folderName = $folder.Name
        $transCorePath = Join-Path $folder.FullName "Transcendence\TransCore"
        
        # Skip if TransCore doesn't exist
        if (-not (Test-Path $transCorePath)) { continue }
        
        # Parse version from folder name
        if ($folderName -match 'TranscendenceDev-integration-API(\d+)') {
            # API version format: TranscendenceDev-integration-API57
            $apiVersion = [int]$matches[1]
            $versionName = "API $apiVersion (2.x dev)"
            
            # Mark API 57 as having forum docs
            if ($apiVersion -eq 57) {
                $versionName = "API $apiVersion (2.x dev - Last with forum docs)"
            }
            
            $versions[$apiVersion] = @{
                Name = $versionName
                SourcePaths = @(
                    $transCorePath,
                    (Join-Path $BaseDir "Transcendence_Source")
                )
                FolderName = $folderName
            }
        }
        elseif ($folderName -match 'TranscendenceDev-(\d+\.\d+)') {
            # Version format: TranscendenceDev-1.9
            $versionStr = $matches[1]
            # Convert 1.9 to 19 for sorting
            $apiVersion = [int]($versionStr -replace '\.', '')
            $versionName = "API $versionStr (Steam release - Stable)"
            
            $versions[$apiVersion] = @{
                Name = $versionName
                SourcePaths = @(
                    $transCorePath,
                    (Join-Path $BaseDir "Transcendence_Source")
                )
                FolderName = $folderName
            }
        }
    }
    
    return $versions
}

# Initialize available API versions (auto-detected)
$script:ApiVersions = Get-AvailableApiVersions

# Fallback if auto-detection fails
if ($script:ApiVersions.Count -eq 0) {
    Write-Warning "No API versions auto-detected, using fallback paths"
    $script:ApiVersions = @{
        57 = @{
            Name = "API 57 (Fallback)"
            SourcePaths = @(
                "D:\games\Steam\steamapps\common\Transcendence\game and dlc source\TranscendenceDev-integration-API57\Transcendence\TransCore",
                "D:\games\Steam\steamapps\common\Transcendence\game and dlc source\Transcendence_Source"
            )
        }
    }
}

# Find latest API version
function Get-LatestApiVersion {
    <#
    .SYNOPSIS
      Returns the highest available API version number
    #>
    $versions = @($script:ApiVersions.Keys) | Sort-Object -Descending
    if ($versions.Count -gt 0) {
        return $versions[0]
    }
    return $script:DefaultApiVersion
}

# Show available versions
function Show-AvailableApiVersions {
    <#
    .SYNOPSIS
      Lists all available API versions
    #>
    Write-Host "Available API Versions:" -ForegroundColor Cyan
    Write-Host ""
    
    # Show detected version from source
    if ($script:DetectedApiVersion) {
        Write-Host "  Detected from Transcendence_Source: API $script:DetectedApiVersion" -ForegroundColor Yellow
        Write-Host ""
    }
    
    $versions = @($script:ApiVersions.Keys) | Sort-Object
    
    foreach ($version in $versions) {
        $info = $script:ApiVersions[$version]
        $marker = if ($version -eq $script:DefaultApiVersion) { " (default - matches source)" } else { "" }
        Write-Host "  API $version$marker" -ForegroundColor White -NoNewline
        Write-Host " - $($info.Name)" -ForegroundColor Gray
    }
    Write-Host ""
}

# Default source paths (can be overridden)
$script:DefaultSourcePaths = $script:ApiVersions[$script:DefaultApiVersion].SourcePaths

# ============================================================
# API RULE STRUCTURE
# ============================================================

function New-ApiRuleSet {
    <#
    .SYNOPSIS
      Creates a new empty API ruleset structure
    #>
    param([int]$ApiVersion = $script:DefaultApiVersion)
    
    return [PSCustomObject]@{
        Version = $script:ApiRulesVersion
        GeneratedAt = (Get-Date -Format "yyyy-MM-dd HH:mm:ss")
        SourcePaths = @()
        ApiVersion = $ApiVersion
        
        # Tag inventory
        Tags = @{}
        
        # Attribute inventory by tag
        Attributes = @{}
        
        # Event handlers (OnCreate, OnDestroy, etc.)
        Events = @{}
        
        # TLisp functions
        Functions = @{}
        
        # Entity definitions
        Entities = @{}
        
        # Deprecated items
        Deprecated = @{
            Tags = @()
            Attributes = @{}
            Functions = @()
            Entities = @()
        }
        
        # Semantic rules (what tags require what attributes)
        SemanticRules = @{}
        
        # Type inheritance
        TypeInheritance = @{}
        
        # Statistics
        Stats = @{
            TotalTags = 0
            TotalAttributes = 0
            TotalEvents = 0
            TotalFunctions = 0
            TotalEntities = 0
            FilesScanned = 0
        }
    }
}

# ============================================================
# TAG EXTRACTION
# ============================================================

function Get-XmlTagInventory {
    <#
    .SYNOPSIS
      Extracts all XML tags and their attributes from source files
    #>
    param(
        [string[]]$SourcePaths,
        [hashtable]$ExistingTags = @{},
        [hashtable]$ExistingAttributes = @{}
    )
    
    $tags = $ExistingTags.Clone()
    $attributes = $ExistingAttributes.Clone()
    $filesScanned = 0
    
    foreach ($sourcePath in $SourcePaths) {
        if (-not (Test-Path $sourcePath)) {
            Write-Warning "Source path not found: $sourcePath"
            continue
        }
        
        $xmlFiles = Get-ChildItem -LiteralPath $sourcePath -Filter "*.xml" -Recurse -ErrorAction SilentlyContinue
        
        foreach ($file in $xmlFiles) {
            $filesScanned++
            
            try {
                # Read file content
                $content = [System.IO.File]::ReadAllText($file.FullName, [System.Text.Encoding]::UTF8)
                
                # Extract tags using regex (faster than XML parsing, handles malformed files)
                $tagPattern = '<([a-zA-Z_][a-zA-Z0-9_:]*)\s*([^>]*?)/?>'
                $matches = [regex]::Matches($content, $tagPattern)
                
                foreach ($match in $matches) {
                    $tagName = $match.Groups[1].Value
                    $attrString = $match.Groups[2].Value
                    
                    # Skip special tags
                    if ($tagName -eq '?xml' -or $tagName.StartsWith('!')) { continue }
                    
                    # Initialize tag entry
                    if (-not $tags.ContainsKey($tagName)) {
                        $tags[$tagName] = @{
                            Count = 0
                            Files = [System.Collections.ArrayList]::new()
                            Attributes = @{}
                        }
                    }
                    $tags[$tagName].Count++
                    if ($tags[$tagName].Files -notcontains $file.Name) {
                        [void]$tags[$tagName].Files.Add($file.Name)
                    }
                    
                    # Initialize attributes entry
                    if (-not $attributes.ContainsKey($tagName)) {
                        $attributes[$tagName] = @{}
                    }
                    
                    # Extract attributes
                    $attrPattern = '(\w+)\s*=\s*["\x27]([^"\x27]*)["\x27]'
                    $attrMatches = [regex]::Matches($attrString, $attrPattern)
                    
                    foreach ($attrMatch in $attrMatches) {
                        $attrName = $attrMatch.Groups[1].Value
                        $attrValue = $attrMatch.Groups[2].Value
                        
                        # Track attribute
                        if (-not $attributes[$tagName].ContainsKey($attrName)) {
                            $attributes[$tagName][$attrName] = @{
                                Count = 0
                                SampleValues = [System.Collections.ArrayList]::new()
                            }
                        }
                        $attributes[$tagName][$attrName].Count++
                        
                        # Store sample values (up to 5)
                        if ($attributes[$tagName][$attrName].SampleValues.Count -lt 5) {
                            if ($attributes[$tagName][$attrName].SampleValues -notcontains $attrValue) {
                                [void]$attributes[$tagName][$attrName].SampleValues.Add($attrValue)
                            }
                        }
                        
                        # Also track on tag entry
                        if (-not $tags[$tagName].Attributes.ContainsKey($attrName)) {
                            $tags[$tagName].Attributes[$attrName] = 0
                        }
                        $tags[$tagName].Attributes[$attrName]++
                    }
                }
            }
            catch {
                # Skip files that can't be parsed
            }
        }
    }
    
    return @{
        Tags = $tags
        Attributes = $attributes
        FilesScanned = $filesScanned
    }
}

# ============================================================
# EVENT EXTRACTION
# ============================================================

function Get-EventInventory {
    <#
    .SYNOPSIS
      Extracts all event handler names from source files
    #>
    param([string[]]$SourcePaths)
    
    $events = @{}
    
    foreach ($sourcePath in $SourcePaths) {
        if (-not (Test-Path $sourcePath)) { continue }
        
        $xmlFiles = Get-ChildItem -LiteralPath $sourcePath -Filter "*.xml" -Recurse -ErrorAction SilentlyContinue
        
        foreach ($file in $xmlFiles) {
            try {
                $content = [System.IO.File]::ReadAllText($file.FullName, [System.Text.Encoding]::UTF8)
                
                # Find event tags (On*, Events block content)
                $eventPattern = '<(On[A-Z][a-zA-Z0-9_]*)\s*>'
                $eventMatches = [regex]::Matches($content, $eventPattern)
                
                foreach ($match in $eventMatches) {
                    $eventName = $match.Groups[1].Value
                    
                    if (-not $events.ContainsKey($eventName)) {
                        $events[$eventName] = @{
                            Count = 0
                            Files = [System.Collections.ArrayList]::new()
                        }
                    }
                    $events[$eventName].Count++
                    if ($events[$eventName].Files -notcontains $file.Name) {
                        [void]$events[$eventName].Files.Add($file.Name)
                    }
                }
                
                # Also find events inside <Events> blocks
                $eventsBlockPattern = '<Events\s*>([\s\S]*?)</Events>'
                $eventsBlockMatches = [regex]::Matches($content, $eventsBlockPattern)
                
                foreach ($blockMatch in $eventsBlockMatches) {
                    $blockContent = $blockMatch.Groups[1].Value
                    $innerEventPattern = '<(\w+)\s*>'
                    $innerMatches = [regex]::Matches($blockContent, $innerEventPattern)
                    
                    foreach ($innerMatch in $innerMatches) {
                        $eventName = $innerMatch.Groups[1].Value
                        
                        if (-not $events.ContainsKey($eventName)) {
                            $events[$eventName] = @{
                                Count = 0
                                Files = [System.Collections.ArrayList]::new()
                            }
                        }
                        $events[$eventName].Count++
                        if ($events[$eventName].Files -notcontains $file.Name) {
                            [void]$events[$eventName].Files.Add($file.Name)
                        }
                    }
                }
            }
            catch {
                # Skip files that can't be parsed
            }
        }
    }
    
    return $events
}

# ============================================================
# TLISP FUNCTION EXTRACTION
# ============================================================

function Get-TlispFunctionInventory {
    <#
    .SYNOPSIS
      Extracts TLisp function calls from source files
    #>
    param([string[]]$SourcePaths)
    
    $functions = @{}
    
    foreach ($sourcePath in $SourcePaths) {
        if (-not (Test-Path $sourcePath)) { continue }
        
        $xmlFiles = Get-ChildItem -LiteralPath $sourcePath -Filter "*.xml" -Recurse -ErrorAction SilentlyContinue
        
        foreach ($file in $xmlFiles) {
            try {
                $content = [System.IO.File]::ReadAllText($file.FullName, [System.Text.Encoding]::UTF8)
                
                # Find TLisp function calls: (functionName ...)
                $funcPattern = '\(\s*([a-zA-Z][a-zA-Z0-9_@]*)\s+'
                $funcMatches = [regex]::Matches($content, $funcPattern)
                
                foreach ($match in $funcMatches) {
                    $funcName = $match.Groups[1].Value
                    
                    # Skip common control structures that aren't functions
                    $skipList = @('if', 'and', 'or', 'not', 'block', 'loop', 'for', 'enum', 'lambda', 'switch', 'setq', 'let')
                    if ($skipList -contains $funcName) { continue }
                    
                    if (-not $functions.ContainsKey($funcName)) {
                        $functions[$funcName] = @{
                            Count = 0
                            Files = [System.Collections.ArrayList]::new()
                        }
                    }
                    $functions[$funcName].Count++
                    if ($functions[$funcName].Files -notcontains $file.Name) {
                        [void]$functions[$funcName].Files.Add($file.Name)
                    }
                }
            }
            catch {
                # Skip files that can't be parsed
            }
        }
    }
    
    return $functions
}

# ============================================================
# ENTITY EXTRACTION
# ============================================================

function Get-EntityInventory {
    <#
    .SYNOPSIS
      Extracts entity definitions from DOCTYPE sections
    #>
    param([string[]]$SourcePaths)
    
    $entities = @{}
    
    foreach ($sourcePath in $SourcePaths) {
        if (-not (Test-Path $sourcePath)) { continue }
        
        $xmlFiles = Get-ChildItem -LiteralPath $sourcePath -Filter "*.xml" -Recurse -ErrorAction SilentlyContinue
        
        foreach ($file in $xmlFiles) {
            try {
                $content = [System.IO.File]::ReadAllText($file.FullName, [System.Text.Encoding]::UTF8)
                
                # Find entity definitions
                $entityPattern = '<!ENTITY\s+(\w+)\s+["\x27]([^"\x27]*)["\x27]\s*>'
                $entityMatches = [regex]::Matches($content, $entityPattern)
                
                foreach ($match in $entityMatches) {
                    $entityName = $match.Groups[1].Value
                    $entityValue = $match.Groups[2].Value
                    
                    if (-not $entities.ContainsKey($entityName)) {
                        $entities[$entityName] = @{
                            Value = $entityValue
                            DefinedIn = $file.Name
                            IsUnid = $entityValue -match '^0x[0-9A-Fa-f]{8}$'
                        }
                    }
                }
            }
            catch {
                # Skip files that can't be parsed
            }
        }
    }
    
    return $entities
}

# ============================================================
# DEPRECATION DETECTION
# ============================================================

function Get-DeprecatedItems {
    <#
    .SYNOPSIS
      Scans for deprecated items by looking at compatibility layers
    #>
    param([string[]]$SourcePaths)
    
    $deprecated = @{
        Tags = [System.Collections.ArrayList]::new()
        Attributes = @{}
        Functions = [System.Collections.ArrayList]::new()
        Entities = [System.Collections.ArrayList]::new()
    }
    
    # Known deprecated items (hardcoded for API 57)
    $knownDeprecatedTags = @(
        'obsoleteVersion'
    )
    
    $knownDeprecatedAttrs = @{
        'ItemType' = @('massBonusPerCharge', 'valueBonusPerCharge')
        'Weapon' = @('linkedFire')
        'Missile' = @('ammoID')
    }
    
    $knownDeprecatedFunctions = @(
        'objGetArmor',
        'objArmorGetHitPoints',
        'shpGetArmor',
        'itmGetDamageType',
        'typGet'
    )
    
    foreach ($tag in $knownDeprecatedTags) {
        [void]$deprecated.Tags.Add($tag)
    }
    
    foreach ($tagName in $knownDeprecatedAttrs.Keys) {
        $deprecated.Attributes[$tagName] = $knownDeprecatedAttrs[$tagName]
    }
    
    foreach ($func in $knownDeprecatedFunctions) {
        [void]$deprecated.Functions.Add($func)
    }
    
    # Scan compatibility files for more deprecated items
    foreach ($sourcePath in $SourcePaths) {
        if (-not (Test-Path $sourcePath)) { continue }
        
        $compatFiles = Get-ChildItem -LiteralPath $sourcePath -Filter "*Compat*.xml" -Recurse -ErrorAction SilentlyContinue
        
        foreach ($file in $compatFiles) {
            try {
                $content = [System.IO.File]::ReadAllText($file.FullName, [System.Text.Encoding]::UTF8)
                
                # Look for obsolete markers in comments
                $obsoletePattern = '<!--\s*OBSOLETE:?\s*(\w+)'
                $obsoleteMatches = [regex]::Matches($content, $obsoletePattern, [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
                
                foreach ($match in $obsoleteMatches) {
                    $obsoleteItem = $match.Groups[1].Value
                    if ($deprecated.Tags -notcontains $obsoleteItem) {
                        [void]$deprecated.Tags.Add($obsoleteItem)
                    }
                }
                
                # Look for deprecated function mappings
                $deprecatedFuncPattern = '\(typSetGlobalData\s+.*DEPRECATED.*\(([a-zA-Z][a-zA-Z0-9_]*)\)'
                $deprecatedFuncMatches = [regex]::Matches($content, $deprecatedFuncPattern, [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
                
                foreach ($match in $deprecatedFuncMatches) {
                    $deprecatedFunc = $match.Groups[1].Value
                    if ($deprecated.Functions -notcontains $deprecatedFunc) {
                        [void]$deprecated.Functions.Add($deprecatedFunc)
                    }
                }
            }
            catch {
                # Skip files that can't be parsed
            }
        }
    }
    
    return $deprecated
}

# ============================================================
# SEMANTIC RULES GENERATION
# ============================================================

function Get-SemanticRules {
    <#
    .SYNOPSIS
      Generates semantic rules based on tag usage patterns
    #>
    param(
        [hashtable]$Tags,
        [hashtable]$Attributes
    )
    
    $rules = @{}
    
    # Core semantic rules for Transcendence
    $rules['ShipClass'] = @{
        RequiredAttributes = @('UNID', 'class')
        RecommendedAttributes = @('name', 'attributes', 'manufacturer')
        CommonChildren = @('Armor', 'Devices', 'Interior', 'Events')
    }
    
    $rules['StationType'] = @{
        RequiredAttributes = @('UNID')
        RecommendedAttributes = @('name', 'sovereign', 'attributes')
        CommonChildren = @('Encounters', 'Events', 'DockScreens')
    }
    
    $rules['ItemType'] = @{
        RequiredAttributes = @('UNID')
        RecommendedAttributes = @('name', 'level', 'mass', 'value')
    }
    
    $rules['Weapon'] = @{
        RequiredAttributes = @()
        RecommendedAttributes = @('type', 'damage', 'fireRate')
    }
    
    $rules['Missile'] = @{
        RequiredAttributes = @()
        RecommendedAttributes = @('lifetime', 'damage')
    }
    
    $rules['WeaponFire'] = @{
        RequiredAttributes = @()
        RecommendedAttributes = @('lifetime', 'damage')
    }
    
    $rules['Armor'] = @{
        RequiredAttributes = @()
        RecommendedAttributes = @('armorID', 'count')
    }
    
    $rules['Shields'] = @{
        RequiredAttributes = @()
        RecommendedAttributes = @('shieldID')
    }
    
    # Auto-detect required attributes based on usage patterns
    foreach ($tagName in $Tags.Keys) {
        $tagInfo = $Tags[$tagName]
        if ($tagInfo.Count -ge 10 -and $Attributes.ContainsKey($tagName)) {
            $tagAttrs = $Attributes[$tagName]
            
            # Attributes that appear in >90% of usages are likely required
            $likelyRequired = @()
            foreach ($attrName in $tagAttrs.Keys) {
                $attrInfo = $tagAttrs[$attrName]
                if ($attrInfo.Count -ge ($tagInfo.Count * 0.9)) {
                    $likelyRequired += $attrName
                }
            }
            
            if ($likelyRequired.Count -gt 0 -and -not $rules.ContainsKey($tagName)) {
                $rules[$tagName] = @{
                    RequiredAttributes = @()
                    RecommendedAttributes = $likelyRequired
                }
            }
        }
    }
    
    return $rules
}

# ============================================================
# TYPE INHERITANCE
# ============================================================

function Get-TypeInheritance {
    <#
    .SYNOPSIS
      Extracts type inheritance relationships
    #>
    param([string[]]$SourcePaths)
    
    $inheritance = @{}
    
    foreach ($sourcePath in $SourcePaths) {
        if (-not (Test-Path $sourcePath)) { continue }
        
        $xmlFiles = Get-ChildItem -LiteralPath $sourcePath -Filter "*.xml" -Recurse -ErrorAction SilentlyContinue
        
        foreach ($file in $xmlFiles) {
            try {
                $content = [System.IO.File]::ReadAllText($file.FullName, [System.Text.Encoding]::UTF8)
                
                # Find inherit attributes
                $inheritPattern = '<(\w+)\s+[^>]*inherit\s*=\s*["\x27]([^"\x27]+)["\x27]'
                $inheritMatches = [regex]::Matches($content, $inheritPattern)
                
                foreach ($match in $inheritMatches) {
                    $typeName = $match.Groups[1].Value
                    $inheritFrom = $match.Groups[2].Value
                    
                    if (-not $inheritance.ContainsKey($typeName)) {
                        $inheritance[$typeName] = [System.Collections.ArrayList]::new()
                    }
                    if ($inheritance[$typeName] -notcontains $inheritFrom) {
                        [void]$inheritance[$typeName].Add($inheritFrom)
                    }
                }
            }
            catch {
                # Skip files that can't be parsed
            }
        }
    }
    
    return $inheritance
}

# ============================================================
# AUTO-DETECT DLC SOURCES
# ============================================================

function Get-DlcSourcePaths {
    <#
    .SYNOPSIS
      Auto-detects DLC source folders
    #>
    param([string]$BaseSourcePath)
    
    $dlcPaths = @()
    $baseDir = Split-Path $BaseSourcePath -Parent
    
    if (-not $baseDir) {
        return $dlcPaths
    }
    
    # Look for DLC source folders
    $dlcPatterns = @(
        "*_Source",
        "*Source"
    )
    
    $dlcFolders = Get-ChildItem -LiteralPath $baseDir -Directory -ErrorAction SilentlyContinue | Where-Object {
        $name = $_.Name
        # Skip main source and dev branches
        if ($name -eq "Transcendence_Source" -or $name -like "TranscendenceDev-*") {
            return $false
        }
        # Include folders that look like DLC sources
        return $name -like "*_Source" -or $name -like "*Source"
    }
    
    foreach ($dlcFolder in $dlcFolders) {
        # Check if it contains XML files (likely a source folder)
        $xmlFiles = Get-ChildItem -LiteralPath $dlcFolder.FullName -Filter "*.xml" -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($xmlFiles) {
            $dlcPaths += $dlcFolder.FullName
        }
    }
    
    return $dlcPaths
}

# ============================================================
# AUTO-UPDATE CHECK
# ============================================================

function Test-ApiRulesNeedUpdate {
    <#
    .SYNOPSIS
      Checks if API rules need updating based on source file timestamps
    #>
    param(
        [string]$RulesPath = $script:ApiRulesPath,
        [int]$ApiVersion = $script:DefaultApiVersion
    )
    
    if (-not (Test-Path $RulesPath)) {
        return $true  # Rules don't exist, need to generate
    }
    
    $rulesFile = Get-Item $RulesPath
    $rulesTime = $rulesFile.LastWriteTime
    
    # Get source paths for this API version
    if (-not $script:ApiVersions.ContainsKey($ApiVersion)) {
        return $false
    }
    
    $sourcePaths = $script:ApiVersions[$ApiVersion].SourcePaths
    
    # Add DLC sources
    foreach ($sourcePath in $sourcePaths) {
        $baseDir = Split-Path $sourcePath -Parent
        $dlcPaths = Get-DlcSourcePaths -BaseSourcePath $sourcePath
        $sourcePaths += $dlcPaths
    }
    
    # Check if any source file is newer than rules
    foreach ($sourcePath in $sourcePaths) {
        if (-not (Test-Path $sourcePath)) { continue }
        
        $sourceFiles = Get-ChildItem -LiteralPath $sourcePath -Filter "*.xml" -Recurse -ErrorAction SilentlyContinue
        
        foreach ($file in $sourceFiles) {
            if ($file.LastWriteTime -gt $rulesTime) {
                return $true  # Source is newer, need update
            }
        }
    }
    
    return $false  # Rules are up to date
}

function Update-ApiRulesIfNeeded {
    <#
    .SYNOPSIS
      Automatically updates API rules if source files are newer
    #>
    param(
        [int]$ApiVersion = $script:DefaultApiVersion,
        [switch]$Force,
        [switch]$Quiet
    )
    
    if (-not $Quiet) {
        Write-Host "Checking API rules..." -ForegroundColor Gray
    }
    
    if ($Force -or (Test-ApiRulesNeedUpdate -ApiVersion $ApiVersion)) {
        if (-not $Quiet) {
            Write-Host "API rules need updating (source files changed)" -ForegroundColor Yellow
        }
        
        # Get source paths
        if (-not $script:ApiVersions.ContainsKey($ApiVersion)) {
            if (-not $Quiet) {
                Write-Host "ERROR: Unknown API version $ApiVersion" -ForegroundColor Red
            }
            return $null
        }
        
        $sourcePaths = $script:ApiVersions[$ApiVersion].SourcePaths.Clone()
        
        # Add DLC sources
        foreach ($basePath in $script:ApiVersions[$ApiVersion].SourcePaths) {
            $dlcPaths = Get-DlcSourcePaths -BaseSourcePath $basePath
            foreach ($dlcPath in $dlcPaths) {
                if ($sourcePaths -notcontains $dlcPath) {
                    $sourcePaths += $dlcPath
                }
            }
        }
        
        if (-not $Quiet) {
            Write-Host "Auto-updating API rules..." -ForegroundColor Cyan
            if ($sourcePaths.Count -gt $script:ApiVersions[$ApiVersion].SourcePaths.Count) {
                Write-Host "  Including $($sourcePaths.Count - $script:ApiVersions[$ApiVersion].SourcePaths.Count) DLC source(s)" -ForegroundColor Gray
            }
        }
        
        return Update-ApiRules -ApiVersion $ApiVersion -SourcePaths $sourcePaths
    }
    else {
        if (-not $Quiet) {
            Write-Host "API rules are up to date" -ForegroundColor Green
        }
        return Get-ApiRules
    }
}

# ============================================================
# MAIN: GENERATE API RULES
# ============================================================

function Update-ApiRules {
    <#
    .SYNOPSIS
      Generates or updates the API rules file from source
      
    .PARAMETER ApiVersion
      The API version to generate rules for (57 or 59). Default is 57 (stable).
      
    .PARAMETER SourcePaths
      Override the source paths to scan. If not specified, uses paths for the selected API version.
    #>
    param(
        [int]$ApiVersion = $script:DefaultApiVersion,
        [string[]]$SourcePaths = $null,
        [string]$OutputPath = $script:ApiRulesPath,
        [switch]$Force
    )
    
    # Use API version paths if not explicitly provided
    if (-not $SourcePaths) {
        if ($script:ApiVersions.ContainsKey($ApiVersion)) {
            $SourcePaths = $script:ApiVersions[$ApiVersion].SourcePaths.Clone()
            Write-Host "Using $($script:ApiVersions[$ApiVersion].Name)" -ForegroundColor Cyan
            
            # Auto-detect and add DLC sources
            foreach ($basePath in $script:ApiVersions[$ApiVersion].SourcePaths) {
                $dlcPaths = Get-DlcSourcePaths -BaseSourcePath $basePath
                foreach ($dlcPath in $dlcPaths) {
                    if ($SourcePaths -notcontains $dlcPath) {
                        $SourcePaths += $dlcPath
                        Write-Host "  Auto-detected DLC source: $(Split-Path -Leaf $dlcPath)" -ForegroundColor Cyan
                    }
                }
            }
        }
        else {
            Write-Host "WARNING: Unknown API version $ApiVersion, using default paths" -ForegroundColor Yellow
            $SourcePaths = $script:DefaultSourcePaths
        }
    }
    
    Write-Host "Generating API Rules..." -ForegroundColor Cyan
    Write-Host ""
    
    # Check if source paths exist
    $validPaths = @()
    foreach ($path in $SourcePaths) {
        if (Test-Path $path) {
            $validPaths += $path
            Write-Host "  Source: $path" -ForegroundColor Green
        }
        else {
            Write-Host "  Source not found: $path" -ForegroundColor Yellow
        }
    }
    
    if ($validPaths.Count -eq 0) {
        Write-Host "ERROR: No valid source paths found" -ForegroundColor Red
        return $null
    }
    
    Write-Host ""
    
    # Create new ruleset
    $ruleSet = New-ApiRuleSet -ApiVersion $ApiVersion
    $ruleSet.SourcePaths = $validPaths
    
    # Extract tags and attributes
    Write-Host "  Extracting tags and attributes..." -ForegroundColor Gray
    $tagResult = Get-XmlTagInventory -SourcePaths $validPaths
    $ruleSet.Tags = $tagResult.Tags
    $ruleSet.Attributes = $tagResult.Attributes
    $ruleSet.Stats.FilesScanned = $tagResult.FilesScanned
    $ruleSet.Stats.TotalTags = $tagResult.Tags.Count
    
    $totalAttrs = 0
    foreach ($tagName in $tagResult.Attributes.Keys) {
        # Count unique attributes for this tag
        $totalAttrs += $tagResult.Attributes[$tagName].Keys.Count
    }
    $ruleSet.Stats.TotalAttributes = $totalAttrs
    
    Write-Host "    Found $($ruleSet.Stats.TotalTags) unique tags" -ForegroundColor White
    Write-Host "    Found $totalAttrs attribute patterns" -ForegroundColor White
    
    # Extract events
    Write-Host "  Extracting events..." -ForegroundColor Gray
    $ruleSet.Events = Get-EventInventory -SourcePaths $validPaths
    $ruleSet.Stats.TotalEvents = $ruleSet.Events.Count
    Write-Host "    Found $($ruleSet.Stats.TotalEvents) unique events" -ForegroundColor White
    
    # Extract functions
    Write-Host "  Extracting TLisp functions..." -ForegroundColor Gray
    $ruleSet.Functions = Get-TlispFunctionInventory -SourcePaths $validPaths
    $ruleSet.Stats.TotalFunctions = $ruleSet.Functions.Keys.Count
    Write-Host "    Found $($ruleSet.Stats.TotalFunctions) unique functions" -ForegroundColor White
    
    # Extract entities
    Write-Host "  Extracting entities..." -ForegroundColor Gray
    $ruleSet.Entities = Get-EntityInventory -SourcePaths $validPaths
    $ruleSet.Stats.TotalEntities = $ruleSet.Entities.Count
    Write-Host "    Found $($ruleSet.Stats.TotalEntities) entity definitions" -ForegroundColor White
    
    # Get deprecated items
    Write-Host "  Detecting deprecated items..." -ForegroundColor Gray
    $ruleSet.Deprecated = Get-DeprecatedItems -SourcePaths $validPaths
    Write-Host "    Found $($ruleSet.Deprecated.Tags.Count) deprecated tags" -ForegroundColor White
    Write-Host "    Found $($ruleSet.Deprecated.Functions.Count) deprecated functions" -ForegroundColor White
    
    # Generate semantic rules
    Write-Host "  Generating semantic rules..." -ForegroundColor Gray
    $ruleSet.SemanticRules = Get-SemanticRules -Tags $tagResult.Tags -Attributes $tagResult.Attributes
    Write-Host "    Generated $($ruleSet.SemanticRules.Count) semantic rules" -ForegroundColor White
    
    # Extract type inheritance
    Write-Host "  Extracting type inheritance..." -ForegroundColor Gray
    $ruleSet.TypeInheritance = Get-TypeInheritance -SourcePaths $validPaths
    Write-Host "    Found $($ruleSet.TypeInheritance.Count) inheritance patterns" -ForegroundColor White
    
    # Save to file
    Write-Host ""
    Write-Host "Saving API rules to: $OutputPath" -ForegroundColor Cyan
    
    try {
        $json = $ruleSet | ConvertTo-Json -Depth 10 -Compress:$false
        $utf8NoBom = [System.Text.UTF8Encoding]::new($false)
        [System.IO.File]::WriteAllText($OutputPath, $json, $utf8NoBom)
        
        $fileSize = [math]::Round((Get-Item $OutputPath).Length / 1KB, 1)
        Write-Host "  Saved ($fileSize KB)" -ForegroundColor Green
    }
    catch {
        Write-Host "  ERROR: Failed to save: $_" -ForegroundColor Red
        return $null
    }
    
    Write-Host ""
    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host "  API RULES GENERATION COMPLETE" -ForegroundColor Cyan
    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  Files Scanned:    $($ruleSet.Stats.FilesScanned)" -ForegroundColor White
    Write-Host "  Unique Tags:      $($ruleSet.Stats.TotalTags)" -ForegroundColor White
    Write-Host "  Unique Events:    $($ruleSet.Stats.TotalEvents)" -ForegroundColor White
    Write-Host "  Unique Functions: $($ruleSet.Stats.TotalFunctions)" -ForegroundColor White
    Write-Host "  Entity Defs:      $($ruleSet.Stats.TotalEntities)" -ForegroundColor White
    Write-Host ""
    
    return $ruleSet
}

# ============================================================
# LOAD API RULES
# ============================================================

function Get-ApiRules {
    <#
    .SYNOPSIS
      Loads the API rules from file
    #>
    param(
        [string]$Path = $script:ApiRulesPath
    )
    
    if (-not (Test-Path $Path)) {
        Write-Warning "API rules file not found: $Path"
        Write-Host "Run Update-ApiRules to generate it." -ForegroundColor Yellow
        return $null
    }
    
    try {
        $json = Get-Content $Path -Raw
        $rules = $json | ConvertFrom-Json
        return $rules
    }
    catch {
        Write-Warning "Failed to load API rules: $_"
        return $null
    }
}

# ============================================================
# VALIDATE AGAINST API RULES
# ============================================================

function Test-ModAgainstApiRules {
    <#
    .SYNOPSIS
      Validates a mod against the current API rules
    #>
    param(
        [string]$ModPath,
        [PSCustomObject]$Rules = $null
    )
    
    if (-not $Rules) {
        $Rules = Get-ApiRules
        if (-not $Rules) {
            Write-Host "Cannot validate: No API rules loaded" -ForegroundColor Red
            return $null
        }
    }
    
    $issues = [System.Collections.ArrayList]::new()
    
    $xmlFiles = Get-ChildItem -LiteralPath $ModPath -Filter "*.xml" -Recurse -ErrorAction SilentlyContinue
    
    foreach ($file in $xmlFiles) {
        try {
            $content = [System.IO.File]::ReadAllText($file.FullName, [System.Text.Encoding]::UTF8)
            
            # Check for deprecated tags
            foreach ($deprecatedTag in $Rules.Deprecated.Tags) {
                if ($content -match "<$deprecatedTag\s") {
                    [void]$issues.Add([PSCustomObject]@{
                        File = $file.Name
                        Type = 'DeprecatedTag'
                        Item = $deprecatedTag
                        Severity = 'Warning'
                        Message = "Deprecated tag <$deprecatedTag> found"
                    })
                }
            }
            
            # Check for deprecated functions
            foreach ($deprecatedFunc in $Rules.Deprecated.Functions) {
                if ($content -match "\(\s*$deprecatedFunc\s") {
                    [void]$issues.Add([PSCustomObject]@{
                        File = $file.Name
                        Type = 'DeprecatedFunction'
                        Item = $deprecatedFunc
                        Severity = 'Warning'
                        Message = "Deprecated function ($deprecatedFunc) found"
                    })
                }
            }
            
            # Check for unknown tags
            $tagPattern = '<([a-zA-Z_][a-zA-Z0-9_:]*)\s'
            $tagMatches = [regex]::Matches($content, $tagPattern)
            
            foreach ($match in $tagMatches) {
                $tagName = $match.Groups[1].Value
                
                # Skip standard XML
                if ($tagName -eq '?xml' -or $tagName.StartsWith('!')) { continue }
                
                if (-not $Rules.Tags.$tagName -and $tagName -ne 'TranscendenceExtension' -and $tagName -ne 'TranscendenceAdventure' -and $tagName -ne 'TranscendenceLibrary' -and $tagName -ne 'TranscendenceModule') {
                    # Only flag if it's a major tag (appears at start of line)
                    $linePattern = "^\s*<$tagName\s"
                    if ($content -match "(?m)$linePattern") {
                        [void]$issues.Add([PSCustomObject]@{
                            File = $file.Name
                            Type = 'UnknownTag'
                            Item = $tagName
                            Severity = 'Info'
                            Message = "Tag <$tagName> not found in API rules (may be custom)"
                        })
                    }
                }
            }
        }
        catch {
            # Skip files that can't be parsed
        }
    }
    
    return $issues
}

# ============================================================
# EXPORT MODULE FUNCTIONS
# ============================================================

# Export functions if running as module
if ($MyInvocation.Line -match 'Import-Module') {
# Export functions if running as module
if ($MyInvocation.Line -match 'Import-Module') {
    Export-ModuleMember -Function @(
        'New-ApiRuleSet',
        'Update-ApiRules',
        'Get-ApiRules',
        'Test-ModAgainstApiRules',
        'Get-XmlTagInventory',
        'Get-EventInventory',
        'Get-TlispFunctionInventory',
        'Get-EntityInventory',
        'Get-DeprecatedItems',
        'Get-SemanticRules',
        'Get-TypeInheritance',
        'Get-DlcSourcePaths',
        'Test-ApiRulesNeedUpdate',
        'Update-ApiRulesIfNeeded'
    )
}
}


<#
.SYNOPSIS
  Build a comprehensive reference archive of all UNIDs, entities, functions, and references
  
.DESCRIPTION
  This script scans all Transcendence source files and mods to build a comprehensive
  reference database. This archive can be used for:
  - Detecting duplicate UNIDs across mods
  - Finding all references to entities/functions
  - Identifying conflicts
  - Auto-fixing missing entity declarations
  - Version-specific API detection
  
  The archive is multithreaded for performance and stores data in JSON format.
  
  NOTE: This script processes XML files exclusively. All source folders and mod folders
  are expected to contain .xml files (Transcendence game data files).
  
.EXAMPLE
  .\BuildReferenceArchive.ps1 -SourcePath "game_and_dlc_source"
  .\BuildReferenceArchive.ps1 -ModPath "Extensions" -OutputPath "mod_references.json"
  .\BuildReferenceArchive.ps1 -SourcePaths @("path1", "path2") -IncludeSource -DetectUpdates
#>

param(
    [string[]]$SourcePaths = @(),  # Array of source paths to process
    [string]$SourcePath = "",  # Single source path (for backward compatibility)
    [string]$ModPath = "",  # Defaults to Extensions relative to Transcendence installation
    [string]$OutputPath = "reference_archive",
    [int]$MaxThreads = 0,  # 0 = auto-detect based on CPU cores
    [switch]$IncludeMods,
    [switch]$IncludeSource,
    [switch]$DetectUpdates  # Detect if mods have been updated and create "current" versions
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Load shared asset generation settings
$settingsPath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "..\\AssetGenerationSettings.ps1"
if (Test-Path $settingsPath) {
    . $settingsPath
}

# Get script root for path resolution
$PSScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

<#
.SYNOPSIS
  Gets the Transcendence installation root from settings file or detects it.
#>
function Get-TranscendenceRootFromSettings {
    $toolsRoot = Split-Path $PSScriptRoot -Parent
    $settingsFile = Join-Path $toolsRoot "TranscendenceTools.ini"
    
    if (Test-Path $settingsFile) {
        $content = Get-Content $settingsFile -Raw
        if ($content -match '(?m)^\s*TranscendencePath\s*=\s*(.+)$') {
            $path = $matches[1].Trim()
            $path = [System.Environment]::ExpandEnvironmentVariables($path)
            if (Test-Path $path) {
                return $path
            }
        }
    }
    
    return $null
}

<#
.SYNOPSIS
  Detects the Transcendence installation root directory.
  
.DESCRIPTION
  First checks settings file, then searches common Steam installation locations.
#>
function Find-TranscendenceRoot {
    param(
        [string]$StartPath = $PSScriptRoot
    )
    
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
        (Split-Path -Parent (Split-Path -Parent $StartPath)),
        (Split-Path -Parent $StartPath),
        $StartPath
    )
    $searchPaths = $relativePaths + $searchPaths
    
    foreach ($path in $searchPaths) {
        if ([string]::IsNullOrWhiteSpace($path)) { continue }
        if (-not (Test-Path $path)) { continue }
        
        # Check for Transcendence.tdb (strong indicator)
        $tdbFile = Join-Path $path "Transcendence.tdb"
        if (Test-Path $tdbFile) {
            return $path
        }
        
        # Check for Extensions folder (common indicator)
        $extensionsPath = Join-Path $path "Extensions"
        if (Test-Path $extensionsPath) {
            return $path
        }
        
        # Check for Collection folder (common indicator)
        $collectionPath = Join-Path $path "Collection"
        if (Test-Path $collectionPath) {
            return $path
        }
    }
    
    # If not found, return null (caller should handle)
    return $null
}

# Auto-detect optimal thread count based on CPU cores
if ($MaxThreads -le 0) {
    try {
        $physicalCores = $null
        $logicalCores = $null
        
        # Try to get physical cores first (accounts for systems without hyperthreading)
        try {
            $processors = Get-CimInstance -ClassName Win32_Processor
            $physicalCores = ($processors | Measure-Object -Property NumberOfCores -Sum).Sum
            $logicalCores = ($processors | Measure-Object -Property NumberOfLogicalProcessors -Sum).Sum
        }
        catch {
            # Fallback methods
            try {
                $logicalCores = (Get-CimInstance -ClassName Win32_ComputerSystem).NumberOfLogicalProcessors
            }
            catch { }
            
            if (-not $logicalCores) {
                $logicalCores = $env:NUMBER_OF_PROCESSORS
            }
        }
        
        # Prefer physical cores, but use logical if physical not available
        $cpuCores = if ($physicalCores) { $physicalCores } else { $logicalCores }
        
        if ($cpuCores) {
            # For I/O-bound operations, use 2x physical cores (or 1.5x if we only have logical)
            # This accounts for systems without hyperthreading
            if ($physicalCores) {
                # We have physical cores - use 2x for I/O-bound work
                $MaxThreads = [Math]::Min([int]$physicalCores * 2, 64)
                $threadInfo = "$physicalCores physical cores"
                if ($logicalCores -and $logicalCores -gt $physicalCores) {
                    $threadInfo += " ($logicalCores logical with hyperthreading)"
                }
            }
            else {
                # Only have logical cores - be more conservative (1.5x)
                $MaxThreads = [Math]::Min([int][Math]::Ceiling($logicalCores * 1.5), 64)
                $threadInfo = "$logicalCores logical cores (physical cores not detected)"
            }
            
            Write-Host "Auto-detected CPU: $threadInfo, using $MaxThreads threads" -ForegroundColor Cyan
        }
        else {
            $MaxThreads = 8
            Write-Host "Could not detect CPU cores, defaulting to $MaxThreads threads" -ForegroundColor Yellow
        }
    }
    catch {
        $MaxThreads = 8
        Write-Host "Error detecting CPU cores, defaulting to $MaxThreads threads: $_" -ForegroundColor Yellow
    }
}
else {
    Write-Host "Using $MaxThreads threads (user-specified)" -ForegroundColor Cyan
}

# ============================================================
# REFERENCE ARCHIVE STRUCTURE
# ============================================================

$script:Archive = @{
    Version = "1.0"
    GeneratedAt = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Sources = @()
    Entities = @{}      # entityName -> { UNID, DefinedIn[], UsedIn[], ApiVersion }
    UNIDs = @{}         # unid -> { EntityName, Type, DefinedIn[], UsedIn[], ApiVersion }
    Functions = @{}     # functionName -> { DefinedIn[], UsedIn[], ApiVersion, Signature }
    Tags = @{}          # tagName -> { DefinedIn[], UsedIn[], ApiVersion }
    Conflicts = @{}     # unid -> { Entities[], Files[] }
    References = @{}    # entityName -> { References[] }
}

# Thread-safe collections
$script:EntityLock = [System.Threading.ReaderWriterLockSlim]::new()
$script:UnidLock = [System.Threading.ReaderWriterLockSlim]::new()
$script:FunctionLock = [System.Threading.ReaderWriterLockSlim]::new()
$script:TagLock = [System.Threading.ReaderWriterLockSlim]::new()

# ============================================================
# MOD/VERSION IDENTIFICATION
# ============================================================

function Get-ApiVersionFromFile {
    param([string]$FilePath)
    
    try {
        $content = Get-Content $FilePath -Raw -ErrorAction SilentlyContinue
        if (-not $content) { return 0 }
        
        if ($content -match 'apiVersion\s*=\s*["\x27](\d+)["\x27]') {
            return [int]$matches[1]
        }
    }
    catch { }
    
    return 0
}

function Get-ModIdentifier {
    <#
    .SYNOPSIS
      Identifies mod name and version from file path
    #>
    param(
        [string]$FilePath,
        [string]$ModPath,
        [string]$SourcePath
    )
    
    $fullPath = [System.IO.Path]::GetFullPath($FilePath)
    $modPathFull = if ($ModPath) { [System.IO.Path]::GetFullPath($ModPath) } else { '' }
    $sourcePathFull = if ($SourcePath) { [System.IO.Path]::GetFullPath($SourcePath) } else { '' }
    
    # Check if file is in mod path
    if ($modPathFull -and $fullPath.StartsWith($modPathFull, [System.StringComparison]::InvariantCultureIgnoreCase)) {
        $relativePath = $fullPath.Substring($modPathFull.Length).TrimStart('\', '/')
        $parts = $relativePath -split '[\\/]'
        
        if ($parts.Count -gt 0) {
            $modFolder = $parts[0]
            # Extract mod number and name (e.g., "1365_VCantHeliotropeGunship")
            if ($modFolder -match '^(\d+)_(.+)$') {
                return @{
                    Type = 'Mod'
                    Identifier = "mod_$modFolder"
                    DisplayName = $modFolder
                    FolderName = "mod_$($matches[1])_$($matches[2])"
                    ApiVersion = Get-ApiVersionFromFile -FilePath $FilePath
                }
            }
            else {
                return @{
                    Type = 'Mod'
                    Identifier = "mod_$modFolder"
                    DisplayName = $modFolder
                    FolderName = "mod_$($modFolder -replace '[^a-zA-Z0-9_]', '_')"
                    ApiVersion = Get-ApiVersionFromFile -FilePath $FilePath
                }
            }
        }
    }
    
    # Check if file is in source path
    if ($sourcePathFull -and $fullPath.StartsWith($sourcePathFull, [System.StringComparison]::InvariantCultureIgnoreCase)) {
        $relativePath = $fullPath.Substring($sourcePathFull.Length).TrimStart('\', '/')
        $parts = $relativePath -split '[\\/]'
        
        # Detect base game version from folder name
        $sourceFolder = Split-Path $sourcePathFull -Leaf
        $apiVersion = Get-ApiVersionFromFile -FilePath $FilePath
        
        if ($sourceFolder -match 'Transcendence_Source|TranscendenceDev-integration-API(\d+)') {
            $detectedVersion = if ($matches[1]) { [int]$matches[1] } else { $apiVersion }
            return @{
                Type = 'BaseGame'
                Identifier = "base_game_api$detectedVersion"
                DisplayName = "Base Game API $detectedVersion"
                FolderName = "base_game_api$detectedVersion"
                ApiVersion = $detectedVersion
            }
        }
        elseif ($apiVersion -gt 0) {
            return @{
                Type = 'BaseGame'
                Identifier = "base_game_api$apiVersion"
                DisplayName = "Base Game API $apiVersion"
                FolderName = "base_game_api$apiVersion"
                ApiVersion = $apiVersion
            }
        }
        else {
            return @{
                Type = 'BaseGame'
                Identifier = "base_game_unknown"
                DisplayName = "Base Game (Unknown Version)"
                FolderName = "base_game_unknown"
                ApiVersion = 0
            }
        }
    }
    
    # Unknown source
    return @{
        Type = 'Unknown'
        Identifier = "unknown"
        DisplayName = "Unknown Source"
        FolderName = "unknown"
        ApiVersion = Get-ApiVersionFromFile -FilePath $FilePath
    }
}

# ============================================================
# ENTITY EXTRACTION
# ============================================================

function Extract-ResourcesFromFile {
    <#
    .SYNOPSIS
      Extracts resource references (images, spritesheets) from XML file
    #>
    param(
        [string]$FilePath,
        [string]$SourcePath
    )
    
    $results = @{
        Resources = @{}
    }
    
    try {
        $content = Get-Content $FilePath -Raw -ErrorAction SilentlyContinue
        if (-not $content) { return $results }
        
        $relativePath = $FilePath.Replace($PWD.Path, '').TrimStart('\', '/')
        
        # Extract resource references from attributes (bitmap, bitmask, shadowMask, etc.)
        $resourceAttrs = @('bitmap', 'bitmask', 'shadowMask', 'image', 'icon', 'sprite', 'texture', 'filename', 'fileName')
        foreach ($attr in $resourceAttrs) {
            $pattern = "$attr\s*=\s*[""\x27]([^""\x27]+)[""\x27]"
            $matches = [regex]::Matches($content, $pattern, [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
            
            foreach ($match in $matches) {
                $resourcePath = $match.Groups[1].Value
                # Normalize path separators
                $resourcePath = $resourcePath -replace '/', '\'
                
                # Extract filename
                $resourceName = Split-Path $resourcePath -Leaf
                $resourceDir = Split-Path $resourcePath -Parent
                
                if (-not $results.Resources[$resourcePath]) {
                    $results.Resources[$resourcePath] = @{
                        Path = $resourcePath
                        Name = $resourceName
                        Directory = $resourceDir
                        ReferencedBy = @()
                        ReferenceTypes = @()
                    }
                }
                
                if ($relativePath -notin $results.Resources[$resourcePath].ReferencedBy) {
                    $results.Resources[$resourcePath].ReferencedBy += $relativePath
                }
                
                if ($attr -notin $results.Resources[$resourcePath].ReferenceTypes) {
                    $results.Resources[$resourcePath].ReferenceTypes += $attr
                }
            }
        }
        
        # Extract Image element UNIDs and their resource references
        $imagePattern = '<Image[^>]+UNID\s*=\s*["\x27]&?(\w+);?["\x27][^>]*>'
        $imageMatches = [regex]::Matches($content, $imagePattern, [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
        
        foreach ($match in $imageMatches) {
            $imageUnid = $match.Groups[1].Value
            $imageContent = $match.Value
            
            # Extract bitmap/bitmask from this Image element
            if ($imageContent -match 'bitmap\s*=\s*["\x27]([^""\x27]+)[""\x27]') {
                $bitmapPath = $matches[1].Value -replace '/', '\'
                $bitmapName = Split-Path $bitmapPath -Leaf
                
                if (-not $results.Resources[$bitmapPath]) {
                    $results.Resources[$bitmapPath] = @{
                        Path = $bitmapPath
                        Name = $bitmapName
                        Directory = Split-Path $bitmapPath -Parent
                        ReferencedBy = @()
                        ReferenceTypes = @()
                        ImageUNID = $imageUnid
                    }
                }
                
                if ($relativePath -notin $results.Resources[$bitmapPath].ReferencedBy) {
                    $results.Resources[$bitmapPath].ReferencedBy += $relativePath
                }
                
                if ('bitmap' -notin $results.Resources[$bitmapPath].ReferenceTypes) {
                    $results.Resources[$bitmapPath].ReferenceTypes += 'bitmap'
                }
                
                $results.Resources[$bitmapPath].ImageUNID = $imageUnid
            }
        }
    }
    catch {
        Write-Warning "Error extracting resources from $FilePath : $_"
    }
    
    return $results
}

function Scan-ResourceFiles {
    <#
    .SYNOPSIS
      Scans for actual resource files (images, etc.) in a directory
      Resources can be in Resources folder, root directory, or anywhere in the source tree
    #>
    param(
        [string]$SourcePath
    )
    
    $resources = @{}
    $imageExtensions = @('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tga', '.dds')
    $audioExtensions = @('.mp3', '.ogg', '.wav', '.flac', '.m4a', '.aac', '.wma')
    $resourceExtensions = $imageExtensions + $audioExtensions
    
    try {
        # Scan entire source directory recursively for resource files
        # This catches resources in Resources/, root, or any subdirectory
        foreach ($ext in $resourceExtensions) {
            $files = Get-ChildItem -LiteralPath $SourcePath -Filter "*$ext" -Recurse -ErrorAction SilentlyContinue
            
            foreach ($file in $files) {
                # Calculate relative path from source root
                $relativePath = $file.FullName.Replace($SourcePath, '').TrimStart('\', '/')
                $relativePath = $relativePath -replace '/', '\'
                
                # Get directory relative to source
                $relativeDir = $file.DirectoryName.Replace($SourcePath, '').TrimStart('\', '/')
                if ($relativeDir -eq $SourcePath) {
                    $relativeDir = ""
                }
                
                if (-not $resources[$relativePath]) {
                    $isAudio = $audioExtensions -contains $file.Extension.ToLower()
                    $isImage = $imageExtensions -contains $file.Extension.ToLower()
                    
                    $resources[$relativePath] = @{
                        Path = $relativePath
                        Name = $file.Name
                        FullPath = $file.FullName
                        Directory = $relativeDir
                        Extension = $file.Extension
                        ResourceType = if ($isAudio) { "Audio" } elseif ($isImage) { "Image" } else { "Other" }
                        Size = $file.Length
                        LastModified = $file.LastWriteTime
                        Exists = $true
                        ReferencedBy = @()
                        Location = if ($relativeDir -eq "") { "Root" } elseif ($relativeDir -match '^Resources') { "Resources" } else { "Other" }
                    }
                }
            }
        }
    }
    catch {
        Write-Warning "Error scanning resources in $SourcePath : $_"
    }
    
    return $resources
}

function Extract-EntitiesFromFile {
    param(
        [string]$FilePath,
        [int]$ApiVersion
    )
    
    $results = @{
        Entities = @{}
        UNIDs = @{}
        Functions = @{}
        Tags = @{}
    }
    
    try {
        $content = Get-Content $FilePath -Raw -ErrorAction SilentlyContinue
        if (-not $content) { return $results }
        
        $relativePath = $FilePath.Replace($PWD.Path, '').TrimStart('\', '/')
        
        # Extract entity definitions from DOCTYPE
        $entityDefRe = [regex]::new('<!ENTITY\s+(\w+)\s+["\x27]([^"\x27]+)["\x27]', [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
        $entityMatches = $entityDefRe.Matches($content)
        
        foreach ($match in $entityMatches) {
            $entityName = $match.Groups[1].Value
            $unid = $match.Groups[2].Value
            
            if (-not $results.Entities[$entityName]) {
                $results.Entities[$entityName] = @{
                    UNID = $unid
                    DefinedIn = @()
                    UsedIn = @()
                    ApiVersion = $ApiVersion
                }
            }
            
            $results.Entities[$entityName].DefinedIn += $relativePath
            
            # Track UNID
            if ($unid -match '^0x[0-9A-Fa-f]{8}$') {
                if (-not $results.UNIDs[$unid]) {
                    $results.UNIDs[$unid] = @{
                        EntityName = $entityName
                        Type = 'Entity'
                        DefinedIn = @()
                        UsedIn = @()
                        ApiVersion = $ApiVersion
                    }
                }
                $results.UNIDs[$unid].DefinedIn += $relativePath
            }
        }
        
        # Extract entity references (usage)
        $doctypeEnd = $content.IndexOf(']>')
        if ($doctypeEnd -lt 0) { $doctypeEnd = 0 } else { $doctypeEnd += 2 }
        
        $contentText = $content.Substring($doctypeEnd)
        $entityRefRe = [regex]::new('&(\w+);', [System.Text.RegularExpressions.RegexOptions]::None)
        $refMatches = $entityRefRe.Matches($contentText)
        
        $reportedRefs = @{}
        foreach ($match in $refMatches) {
            $entityName = $match.Groups[1].Value
            if (-not $reportedRefs[$entityName]) {
                $reportedRefs[$entityName] = $true
                
                if (-not $results.Entities[$entityName]) {
                    $results.Entities[$entityName] = @{
                        UNID = $null
                        DefinedIn = @()
                        UsedIn = @()
                        ApiVersion = $ApiVersion
                    }
                }
                $results.Entities[$entityName].UsedIn += $relativePath
            }
        }
        
        # Extract function calls
        $functionRe = [regex]::new('\((\w+)\s', [System.Text.RegularExpressions.RegexOptions]::None)
        $funcMatches = $functionRe.Matches($content)
        
        $reportedFuncs = @{}
        foreach ($match in $funcMatches) {
            $funcName = $match.Groups[1].Value
            if (-not $reportedFuncs[$funcName]) {
                $reportedFuncs[$funcName] = $true
                
                if (-not $results.Functions[$funcName]) {
                    $results.Functions[$funcName] = @{
                        DefinedIn = @()
                        UsedIn = @()
                        ApiVersion = $ApiVersion
                        Signature = $null
                    }
                }
                $results.Functions[$funcName].UsedIn += $relativePath
            }
        }
        
        # Extract XML tags
        $tagRe = [regex]::new('<(\w+)(?:\s|>|/)', [System.Text.RegularExpressions.RegexOptions]::None)
        $tagMatches = $tagRe.Matches($content)
        
        $reportedTags = @{}
        foreach ($match in $tagMatches) {
            $tagName = $match.Groups[1].Value
            if ($tagName -notmatch '^!|^\?|^xml') {
                if (-not $reportedTags[$tagName]) {
                    $reportedTags[$tagName] = $true
                    
                    if (-not $results.Tags[$tagName]) {
                        $results.Tags[$tagName] = @{
                            DefinedIn = @()
                            UsedIn = @()
                            ApiVersion = $ApiVersion
                        }
                    }
                    $results.Tags[$tagName].UsedIn += $relativePath
                }
            }
        }
    }
    catch {
        Write-Warning "Error processing $FilePath : $_"
    }
    
    return $results
}

# ============================================================
# MULTITHREADED FILE PROCESSING
# ============================================================

function Process-FilesThreaded {
    param(
        [string[]]$Files,
        [int]$MaxThreads = 8,
        [string]$ModPath,
        [string]$SourcePath
    )
    
    $totalFiles = $files.Count
    $jobCount = [Math]::Min($MaxThreads, $totalFiles)
    
    # Split files into chunks for each job
    $filesPerJob = [Math]::Ceiling($totalFiles / $jobCount)
    $fileChunks = @()
    for ($i = 0; $i -lt $totalFiles; $i += $filesPerJob) {
        $chunk = $files[$i..([Math]::Min($i + $filesPerJob - 1, $totalFiles - 1))]
        $fileChunks += ,$chunk
    }
    
    Write-Host "Processing $totalFiles files with $jobCount threads..." -ForegroundColor Cyan
    
    $scriptBlock = {
        param($FileChunk, $SourcePath, $ModPath)
        
        # Import functions needed in job context
        function Get-ApiVersionFromFile {
            param([string]$FilePath)
            try {
                $content = Get-Content $FilePath -Raw -ErrorAction SilentlyContinue
                if (-not $content) { return 0 }
                if ($content -match 'apiVersion\s*=\s*["\x27](\d+)["\x27]') {
                    return [int]$matches[1]
                }
            }
            catch { }
            return 0
        }
        
        function Extract-ResourcesFromFile {
            param([string]$FilePath, [string]$SourcePath)
            $results = @{ Resources = @{} }
            try {
                $content = Get-Content $FilePath -Raw -ErrorAction SilentlyContinue
                if (-not $content) { return $results }
                $relativePath = $FilePath.Replace($PWD.Path, '').TrimStart('\', '/')
                $resourceAttrs = @('bitmap', 'bitmask', 'shadowMask', 'image', 'icon', 'sprite', 'texture')
                foreach ($attr in $resourceAttrs) {
                    $pattern = "$attr\s*=\s*[""\x27]([^""\x27]+)[""\x27]"
                    $matches = [regex]::Matches($content, $pattern, [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
                    foreach ($match in $matches) {
                        $resourcePath = $match.Groups[1].Value -replace '/', '\'
                        $resourceName = Split-Path $resourcePath -Leaf
                        if (-not $results.Resources[$resourcePath]) {
                            $results.Resources[$resourcePath] = @{
                                Path = $resourcePath
                                Name = $resourceName
                                Directory = Split-Path $resourcePath -Parent
                                ReferencedBy = @()
                                ReferenceTypes = @()
                            }
                        }
                        if ($relativePath -notin $results.Resources[$resourcePath].ReferencedBy) {
                            $results.Resources[$resourcePath].ReferencedBy += $relativePath
                        }
                        if ($attr -notin $results.Resources[$resourcePath].ReferenceTypes) {
                            $results.Resources[$resourcePath].ReferenceTypes += $attr
                        }
                    }
                }
            }
            catch { }
            return $results
        }
        
        function Extract-EntitiesFromFile {
            param([string]$FilePath, [int]$ApiVersion)
            $results = @{
                Entities = @{}
                UNIDs = @{}
                Functions = @{}
                Tags = @{}
            }
            try {
                $content = Get-Content $FilePath -Raw -ErrorAction SilentlyContinue
                if (-not $content) { return $results }
                
                $relativePath = $FilePath.Replace($PWD.Path, '').TrimStart('\', '/')
                
                # Extract entity definitions from DOCTYPE
                $entityDefRe = [regex]::new('<!ENTITY\s+(\w+)\s+["\x27]([^"\x27]+)["\x27]', [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
                $entityMatches = $entityDefRe.Matches($content)
                
                foreach ($match in $entityMatches) {
                    $entityName = $match.Groups[1].Value
                    $unid = $match.Groups[2].Value
                    
                    if (-not $results.Entities[$entityName]) {
                        $results.Entities[$entityName] = @{
                            UNID = $unid
                            DefinedIn = @()
                            UsedIn = @()
                            ApiVersion = $ApiVersion
                        }
                    }
                    $results.Entities[$entityName].DefinedIn += $relativePath
                    
                    if ($unid -match '^0x[0-9A-Fa-f]{8}$') {
                        if (-not $results.UNIDs[$unid]) {
                            $results.UNIDs[$unid] = @{
                                EntityName = $entityName
                                Type = 'Entity'
                                DefinedIn = @()
                                UsedIn = @()
                                ApiVersion = $ApiVersion
                            }
                        }
                        $results.UNIDs[$unid].DefinedIn += $relativePath
                    }
                }
                
                # Extract entity references
                $doctypeEnd = $content.IndexOf(']>')
                if ($doctypeEnd -lt 0) { $doctypeEnd = 0 } else { $doctypeEnd += 2 }
                $contentText = $content.Substring($doctypeEnd)
                $entityRefRe = [regex]::new('&(\w+);', [System.Text.RegularExpressions.RegexOptions]::None)
                $refMatches = $entityRefRe.Matches($contentText)
                
                $reportedRefs = @{}
                foreach ($match in $refMatches) {
                    $entityName = $match.Groups[1].Value
                    if (-not $reportedRefs[$entityName]) {
                        $reportedRefs[$entityName] = $true
                        if (-not $results.Entities[$entityName]) {
                            $results.Entities[$entityName] = @{
                                UNID = $null
                                DefinedIn = @()
                                UsedIn = @()
                                ApiVersion = $ApiVersion
                            }
                        }
                        $results.Entities[$entityName].UsedIn += $relativePath
                    }
                }
                
                # Extract function calls
                $functionRe = [regex]::new('\((\w+)\s', [System.Text.RegularExpressions.RegexOptions]::None)
                $funcMatches = $functionRe.Matches($content)
                $reportedFuncs = @{}
                foreach ($match in $funcMatches) {
                    $funcName = $match.Groups[1].Value
                    if (-not $reportedFuncs[$funcName]) {
                        $reportedFuncs[$funcName] = $true
                        if (-not $results.Functions[$funcName]) {
                            $results.Functions[$funcName] = @{
                                DefinedIn = @()
                                UsedIn = @()
                                ApiVersion = $ApiVersion
                                Signature = $null
                            }
                        }
                        $results.Functions[$funcName].UsedIn += $relativePath
                    }
                }
                
                # Extract XML tags
                $tagRe = [regex]::new('<(\w+)(?:\s|>|/)', [System.Text.RegularExpressions.RegexOptions]::None)
                $tagMatches = $tagRe.Matches($content)
                $reportedTags = @{}
                foreach ($match in $tagMatches) {
                    $tagName = $match.Groups[1].Value
                    if ($tagName -notmatch '^!|^\?|^xml') {
                        if (-not $reportedTags[$tagName]) {
                            $reportedTags[$tagName] = $true
                            if (-not $results.Tags[$tagName]) {
                                $results.Tags[$tagName] = @{
                                    DefinedIn = @()
                                    UsedIn = @()
                                    ApiVersion = $ApiVersion
                                }
                            }
                            $results.Tags[$tagName].UsedIn += $relativePath
                        }
                    }
                }
            }
            catch { }
            return $results
        }
        
        $localResults = @{
            Entities = @{}
            UNIDs = @{}
            Functions = @{}
            Tags = @{}
            Resources = @{}
        }
        
        $processed = 0
        foreach ($file in $FileChunk) {
            $processed++
            
            # Determine API version
            $apiVersion = Get-ApiVersionFromFile -FilePath $file
            
            # Extract data
            $results = Extract-EntitiesFromFile -FilePath $file -ApiVersion $apiVersion
            
            # Extract resource references
            $resourceResults = Extract-ResourcesFromFile -FilePath $file -SourcePath $SourcePath
            
            # Add resources to results
            if (-not $results.Resources) {
                $results.Resources = @{}
            }
            foreach ($resourcePath in $resourceResults.Resources.Keys) {
                $results.Resources[$resourcePath] = $resourceResults.Resources[$resourcePath]
            }
            
            # Merge results
            foreach ($entityName in $results.Entities.Keys) {
                if (-not $localResults.Entities[$entityName]) {
                    $localResults.Entities[$entityName] = $results.Entities[$entityName]
                }
                else {
                    $localResults.Entities[$entityName].DefinedIn += $results.Entities[$entityName].DefinedIn
                    $localResults.Entities[$entityName].UsedIn += $results.Entities[$entityName].UsedIn
                }
            }
            
            foreach ($unid in $results.UNIDs.Keys) {
                if (-not $localResults.UNIDs[$unid]) {
                    $localResults.UNIDs[$unid] = $results.UNIDs[$unid]
                }
                else {
                    $localResults.UNIDs[$unid].DefinedIn += $results.UNIDs[$unid].DefinedIn
                    $localResults.UNIDs[$unid].UsedIn += $results.UNIDs[$unid].UsedIn
                }
            }
            
            foreach ($funcName in $results.Functions.Keys) {
                if (-not $localResults.Functions[$funcName]) {
                    $localResults.Functions[$funcName] = $results.Functions[$funcName]
                }
                else {
                    $localResults.Functions[$funcName].UsedIn += $results.Functions[$funcName].UsedIn
                }
            }
            
            foreach ($tagName in $results.Tags.Keys) {
                if (-not $localResults.Tags[$tagName]) {
                    $localResults.Tags[$tagName] = $results.Tags[$tagName]
                }
                else {
                    $localResults.Tags[$tagName].UsedIn += $results.Tags[$tagName].UsedIn
                }
            }
            
            # Merge resources
            foreach ($resourcePath in $resourceResults.Resources.Keys) {
                if (-not $localResults.Resources[$resourcePath]) {
                    $localResults.Resources[$resourcePath] = $resourceResults.Resources[$resourcePath]
                }
                else {
                    $localResults.Resources[$resourcePath].ReferencedBy = @($localResults.Resources[$resourcePath].ReferencedBy + $resourceResults.Resources[$resourcePath].ReferencedBy | Select-Object -Unique)
                    $localResults.Resources[$resourcePath].ReferenceTypes = @($localResults.Resources[$resourcePath].ReferenceTypes + $resourceResults.Resources[$resourcePath].ReferenceTypes | Select-Object -Unique)
                }
            }
        }
        
        return $localResults
    }
    
    # Run jobs
    $jobs = @()
    for ($i = 0; $i -lt $fileChunks.Count; $i++) {
        if ($fileChunks[$i].Count -gt 0) {
            $jobs += Start-Job -ScriptBlock $scriptBlock -ArgumentList $fileChunks[$i], $SourcePath, $ModPath
        }
    }
    
    # Wait for completion and merge results (with progress reporting)
    $allResults = @{
        Entities = @{}
        UNIDs = @{}
        Functions = @{}
        Tags = @{}
        Resources = @{}
    }
    
    $completedJobs = 0
    $totalJobs = $jobs.Count
    
    # Process results as jobs complete (more efficient for many threads)
    $jobsArray = [System.Collections.ArrayList]::new()
    foreach ($job in $jobs) {
        [void]$jobsArray.Add($job)
    }
    
    while ($jobsArray.Count -gt 0) {
        $completed = @($jobsArray | Where-Object { $_.State -eq 'Completed' })
        
        foreach ($job in $completed) {
            $jobResults = Receive-Job $job
            $completedJobs++
            
            # Merge entities
            foreach ($entityName in $jobResults.Entities.Keys) {
                if (-not $allResults.Entities[$entityName]) {
                    $allResults.Entities[$entityName] = $jobResults.Entities[$entityName]
                }
                else {
                    $allResults.Entities[$entityName].DefinedIn = @($allResults.Entities[$entityName].DefinedIn + $jobResults.Entities[$entityName].DefinedIn | Select-Object -Unique)
                    $allResults.Entities[$entityName].UsedIn = @($allResults.Entities[$entityName].UsedIn + $jobResults.Entities[$entityName].UsedIn | Select-Object -Unique)
                }
            }
            
            # Merge UNIDs
            foreach ($unid in $jobResults.UNIDs.Keys) {
                if (-not $allResults.UNIDs[$unid]) {
                    $allResults.UNIDs[$unid] = $jobResults.UNIDs[$unid]
                }
                else {
                    $allResults.UNIDs[$unid].DefinedIn = @($allResults.UNIDs[$unid].DefinedIn + $jobResults.UNIDs[$unid].DefinedIn | Select-Object -Unique)
                    $allResults.UNIDs[$unid].UsedIn = @($allResults.UNIDs[$unid].UsedIn + $jobResults.UNIDs[$unid].UsedIn | Select-Object -Unique)
                }
            }
            
            # Merge functions
            foreach ($funcName in $jobResults.Functions.Keys) {
                if (-not $allResults.Functions[$funcName]) {
                    $allResults.Functions[$funcName] = $jobResults.Functions[$funcName]
                }
                else {
                    $allResults.Functions[$funcName].UsedIn = @($allResults.Functions[$funcName].UsedIn + $jobResults.Functions[$funcName].UsedIn | Select-Object -Unique)
                }
            }
            
            # Merge tags
            foreach ($tagName in $jobResults.Tags.Keys) {
                if (-not $allResults.Tags[$tagName]) {
                    $allResults.Tags[$tagName] = $jobResults.Tags[$tagName]
                }
                else {
                    $allResults.Tags[$tagName].UsedIn = @($allResults.Tags[$tagName].UsedIn + $jobResults.Tags[$tagName].UsedIn | Select-Object -Unique)
                }
            }
            
            # Merge resources
            if ($jobResults.Resources) {
                foreach ($resourcePath in $jobResults.Resources.Keys) {
                    if (-not $allResults.Resources[$resourcePath]) {
                        $allResults.Resources[$resourcePath] = $jobResults.Resources[$resourcePath]
                    }
                    else {
                        $allResults.Resources[$resourcePath].ReferencedBy = @($allResults.Resources[$resourcePath].ReferencedBy + $jobResults.Resources[$resourcePath].ReferencedBy | Select-Object -Unique)
                        $allResults.Resources[$resourcePath].ReferenceTypes = @($allResults.Resources[$resourcePath].ReferenceTypes + $jobResults.Resources[$resourcePath].ReferenceTypes | Select-Object -Unique)
                    }
                }
            }
            
            # Remove completed job from array
            $jobsArray.Remove($job) | Out-Null
            Remove-Job $job
        }
        
        # Show progress
        if ($completedJobs -lt $totalJobs) {
            $remaining = $totalJobs - $completedJobs
            Write-Host "  Merging results: $completedJobs/$totalJobs jobs completed ($remaining remaining)..." -ForegroundColor Gray
        }
        
        # Wait a bit if no jobs completed yet
        if ($completed.Count -eq 0) {
            Start-Sleep -Milliseconds 100
        }
    }
    
    Write-Host "  All $totalJobs jobs completed and merged" -ForegroundColor Green
    
    return $allResults
}

# ============================================================
# UPDATE DETECTION
# ============================================================

function Test-ArchiveUpdated {
    <#
    .SYNOPSIS
      Detects if a mod/source has been updated since last archive
    #>
    param(
        [string]$ArchiveFolder,
        [string[]]$SourceFiles
    )
    
    if (-not (Test-Path $ArchiveFolder)) {
        return $true  # No existing archive, consider it new/updated
    }
    
    $metadataFile = Join-Path $ArchiveFolder "metadata.json"
    if (-not (Test-Path $metadataFile)) {
        return $true  # No metadata, consider it updated
    }
    
    try {
        $metadata = Get-Content $metadataFile -Raw | ConvertFrom-Json
        $lastGenerated = [DateTime]::Parse($metadata.GeneratedAt)
        
        # Check if any source files have been modified since last archive
        foreach ($file in $SourceFiles) {
            if (Test-Path $file) {
                $fileInfo = Get-Item $file
                if ($fileInfo.LastWriteTime -gt $lastGenerated) {
                    return $true  # File has been modified
                }
            }
        }
        
        return $false  # No files modified
    }
    catch {
        return $true  # Error reading metadata, assume updated
    }
}

# ============================================================
# MAIN PROCESSING
# ============================================================

Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Building Reference Archive (Split by Mod/Version)" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# Detect Transcendence installation root (optional - only used for defaults)
$transcendenceRoot = $null
if ($IncludeSource -or $IncludeMods -or [string]::IsNullOrWhiteSpace($ModPath) -or ($SourcePaths.Count -eq 0 -and [string]::IsNullOrWhiteSpace($SourcePath))) {
    $transcendenceRoot = Find-TranscendenceRoot -StartPath $PSScriptRoot
    if (-not $transcendenceRoot) {
        Write-Host "Note: Transcendence installation not detected. Specify paths explicitly if needed." -ForegroundColor Yellow
        Write-Host "  Most tools work without Transcendence - only needed when scanning Extensions/Collection." -ForegroundColor Gray
    }
}

# Set default ModPath if not specified (relative to Transcendence installation)
if ([string]::IsNullOrWhiteSpace($ModPath)) {
    if ($transcendenceRoot) {
        $ModPath = Join-Path $transcendenceRoot "Extensions"
    } else {
        # No default - user must specify if they want to scan mods
        $ModPath = ""
    }
}

# Normalize source paths - support both single path and array
if ($SourcePaths.Count -eq 0 -and $SourcePath) {
    $SourcePaths = @($SourcePath)
}
elseif ($SourcePaths.Count -eq 0) {
    if ($transcendenceRoot) {
        # Default to game_and_dlc_source folder relative to Transcendence installation
        $SourcePaths = @(Join-Path $transcendenceRoot "game_and_dlc_source")
    } else {
        # No default - user must specify if they want to scan source
        $SourcePaths = @()
    }
}

Write-Host "Processing $($SourcePaths.Count) source folder(s):" -ForegroundColor Cyan
foreach ($path in $SourcePaths) {
    Write-Host "  - $path" -ForegroundColor Gray
}
Write-Host ""

# Create output directory
$outputDir = Join-Path $PSScriptRoot $OutputPath
if (-not (Test-Path $outputDir)) {
    New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
}

# Group files by mod/version across all source paths
Write-Host "Grouping files by mod/version..." -ForegroundColor Cyan
$fileGroups = @{}

# Collect source files from all source paths
foreach ($currentSourcePath in $SourcePaths) {
    if ($IncludeSource -and (Test-Path $currentSourcePath)) {
        Write-Host "Scanning: $currentSourcePath" -ForegroundColor Cyan
        try {
            $sourceFiles = @(Get-ChildItem -LiteralPath $currentSourcePath -Filter *.xml -Recurse -ErrorAction SilentlyContinue | Select-Object -ExpandProperty FullName)
            Write-Host "  Found $($sourceFiles.Count) XML file(s)" -ForegroundColor Gray
            
            if ($sourceFiles.Count -gt 0) {
                # Show sample of files found (first 5)
                $sampleCount = [Math]::Min(5, $sourceFiles.Count)
                if ($sourceFiles.Count -le 5) {
                    Write-Host "  Files: $($sourceFiles -join ', ')" -ForegroundColor DarkGray
                } else {
                    $sample = $sourceFiles[0..($sampleCount-1)] | ForEach-Object { Split-Path $_ -Leaf }
                    Write-Host "  Sample files: $($sample -join ', ') ... and $($sourceFiles.Count - $sampleCount) more" -ForegroundColor DarkGray
                }
                
                foreach ($file in $sourceFiles) {
                    if (Test-Path $file) {
                        $modInfo = Get-ModIdentifier -FilePath $file -ModPath $ModPath -SourcePath $currentSourcePath
                        $key = $modInfo.Identifier
                        
                        if (-not $fileGroups[$key]) {
                            $fileGroups[$key] = @{
                                ModInfo = $modInfo
                                Files = @()
                                SourcePath = $currentSourcePath
                            }
                        }
                        $fileGroups[$key].Files += $file
                    } else {
                        Write-Host "  ⚠ File not found (may have been deleted): $file" -ForegroundColor Yellow
                    }
                }
            } else {
                # Check if this is an audio collection folder (no XML but has audio files)
                $audioFiles = @(Get-ChildItem -LiteralPath $currentSourcePath -Include *.mp3,*.ogg,*.wav,*.flac,*.m4a,*.aac,*.wma -Recurse -ErrorAction SilentlyContinue)
                if ($audioFiles.Count -gt 0) {
                    Write-Host "  Found $($audioFiles.Count) audio file(s) - treating as audio collection" -ForegroundColor Cyan
                    
                    # Detect if this is a Collection folder with UNID name
                    $folderName = Split-Path $currentSourcePath -Leaf
                    $isCollectionFolder = $false
                    $collectionUNID = $null
                    
                    if ($folderName -match '^([0-9A-Fa-f]{8})$') {
                        $collectionUNID = $matches[1]
                        $isCollectionFolder = $true
                        Write-Host "  Detected Collection folder with UNID: $collectionUNID" -ForegroundColor Cyan
                    }
                    
                    # Create a special group for audio collections
                    $audioKey = if ($isCollectionFolder) { "audio_collection_$collectionUNID" } else { "audio_collection_$(Split-Path $currentSourcePath -Leaf)" }
                    
                    if (-not $fileGroups[$audioKey]) {
                        $fileGroups[$audioKey] = @{
                            ModInfo = @{
                                Type = 'AudioCollection'
                                Identifier = $audioKey
                                DisplayName = if ($isCollectionFolder) { "Audio Collection ($collectionUNID)" } else { "Audio Collection: $(Split-Path $currentSourcePath -Leaf)" }
                                FolderName = $audioKey -replace '[^a-zA-Z0-9_]', '_'
                                ApiVersion = 0
                                IsCollection = $true
                                CollectionUNID = $collectionUNID
                            }
                            Files = @()  # No XML files
                            SourcePath = $currentSourcePath
                            IsAudioOnly = $true
                            AudioFileCount = $audioFiles.Count
                        }
                    }
                } else {
                    Write-Host "  ⚠ No XML files found in this directory (XML files are expected for Transcendence source/mod folders)" -ForegroundColor Yellow
                }
            }
        }
        catch {
            Write-Host "  ✗ Error scanning directory: $_" -ForegroundColor Red
        }
    } else {
        if (-not (Test-Path $currentSourcePath)) {
            Write-Host "  ✗ Path not found: $currentSourcePath" -ForegroundColor Red
        }
    }
}

# Collect mod files (XML files expected)
if ($IncludeMods -and (Test-Path $ModPath)) {
    Write-Host "Scanning mod files (XML files expected)..." -ForegroundColor Cyan
    try {
        $modFiles = @(Get-ChildItem -LiteralPath $ModPath -Filter *.xml -Recurse -ErrorAction SilentlyContinue | Select-Object -ExpandProperty FullName)
        Write-Host "  Found $($modFiles.Count) XML file(s)" -ForegroundColor Gray
        
        if ($modFiles.Count -gt 0) {
            # Show sample of files found
            $sampleCount = [Math]::Min(5, $modFiles.Count)
            if ($modFiles.Count -le 5) {
                $sample = $modFiles | ForEach-Object { Split-Path $_ -Leaf }
                Write-Host "  Files: $($sample -join ', ')" -ForegroundColor DarkGray
            } else {
                $sample = $modFiles[0..($sampleCount-1)] | ForEach-Object { Split-Path $_ -Leaf }
                Write-Host "  Sample files: $($sample -join ', ') ... and $($modFiles.Count - $sampleCount) more" -ForegroundColor DarkGray
            }
            
            $firstSourcePath = if ($SourcePaths.Count -gt 0) { $SourcePaths[0] } else { "" }
            
            foreach ($file in $modFiles) {
                if (Test-Path $file) {
                    $modInfo = Get-ModIdentifier -FilePath $file -ModPath $ModPath -SourcePath $firstSourcePath
                    $key = $modInfo.Identifier
                    
                    if (-not $fileGroups[$key]) {
                        $fileGroups[$key] = @{
                            ModInfo = $modInfo
                            Files = @()
                            SourcePath = $ModPath
                        }
                    }
                    $fileGroups[$key].Files += $file
                }
            }
        } else {
            Write-Host "  ⚠ No XML files found in mod directory (XML files are expected for Transcendence mods)" -ForegroundColor Yellow
        }
    }
    catch {
        Write-Host "  ✗ Error scanning mod directory: $_" -ForegroundColor Red
    }
}

if ($fileGroups.Count -eq 0) {
    Write-Host "No files found to process!" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Found $($fileGroups.Count) mod/version groups:" -ForegroundColor Green
foreach ($key in $fileGroups.Keys | Sort-Object) {
    $group = $fileGroups[$key]
    Write-Host "  $($group.ModInfo.DisplayName): $($group.Files.Count) files (API $($group.ModInfo.ApiVersion))" -ForegroundColor Gray
}
Write-Host ""

# Process each group separately
$archiveIndexArchives = [System.Collections.ArrayList]::new()
$archiveIndexTotalEntities = 0
$archiveIndexTotalUNIDs = 0
$archiveIndexTotalFunctions = 0
$archiveIndexTotalTags = 0
$archiveIndexTotalResources = 0
$archiveIndexTotalConflicts = 0

$utf8NoBom = [System.Text.UTF8Encoding]::new($false)

foreach ($key in $fileGroups.Keys | Sort-Object) {
    $group = $fileGroups[$key]
    $modInfo = $group.ModInfo
    $files = $group.Files
    $groupSourcePath = $group.SourcePath
    $isAudioOnly = $group.IsAudioOnly
    
    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host "  Processing: $($modInfo.DisplayName)" -ForegroundColor Cyan
    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
    if ($isAudioOnly) {
        Write-Host "  Type: Audio Collection" -ForegroundColor Gray
        Write-Host "  Audio Files: $($group.AudioFileCount)" -ForegroundColor Gray
    } else {
        Write-Host "  Files: $($files.Count)" -ForegroundColor Gray
        Write-Host "  API Version: $($modInfo.ApiVersion)" -ForegroundColor Gray
    }
    Write-Host "  Source: $groupSourcePath" -ForegroundColor Gray
    Write-Host ""
    
    # Check if this mod has been updated
    $modFolder = Join-Path $outputDir $modInfo.FolderName
    $isUpdated = $false
    if ($DetectUpdates -and -not $isAudioOnly) {
        $isUpdated = Test-ArchiveUpdated -ArchiveFolder $modFolder -SourceFiles $files
        if ($isUpdated) {
            Write-Host "  ⚠ Mod has been updated since last archive - will create 'current' version" -ForegroundColor Yellow
        }
    }
    
    # Process files (multithreaded) - skip if audio-only (no XML to process)
    if ($isAudioOnly) {
        $results = @{
            Entities = @{}
            UNIDs = @{}
            Functions = @{}
            Tags = @{}
            Resources = @{}
        }
    } else {
        $results = Process-FilesThreaded -Files $files -MaxThreads $MaxThreads -ModPath $ModPath -SourcePath $groupSourcePath
    }
    
    # Scan for actual resource files
    Write-Host "Scanning resource files..." -ForegroundColor Cyan
    $scannedResources = Scan-ResourceFiles -SourcePath $groupSourcePath
    Write-Host "  Found $($scannedResources.Count) resource file(s)" -ForegroundColor Gray
    
    # Merge scanned resources with referenced resources
    $allResources = @{}
    
    # First, add all referenced resources (from XML)
    foreach ($resourcePath in $results.Resources.Keys) {
        $allResources[$resourcePath] = $results.Resources[$resourcePath]
        # Ensure IsReferenced property exists
        if (-not $allResources[$resourcePath].PSObject.Properties['IsReferenced']) {
            $allResources[$resourcePath] | Add-Member -MemberType NoteProperty -Name 'IsReferenced' -Value $true -Force
        } else {
            $allResources[$resourcePath].IsReferenced = $true
        }
    }
    
    # Then, add scanned resources (actual files)
    foreach ($resourcePath in $scannedResources.Keys) {
        if (-not $allResources[$resourcePath]) {
            $allResources[$resourcePath] = $scannedResources[$resourcePath]
            # Ensure all required properties exist
            if (-not $allResources[$resourcePath].PSObject.Properties['IsReferenced']) {
                $allResources[$resourcePath] | Add-Member -MemberType NoteProperty -Name 'IsReferenced' -Value $false -Force
            } else {
                $allResources[$resourcePath].IsReferenced = $false
            }
            if (-not $allResources[$resourcePath].PSObject.Properties['ReferencedBy']) {
                $allResources[$resourcePath] | Add-Member -MemberType NoteProperty -Name 'ReferencedBy' -Value @() -Force
            }
            if (-not $allResources[$resourcePath].PSObject.Properties['ReferenceTypes']) {
                $allResources[$resourcePath] | Add-Member -MemberType NoteProperty -Name 'ReferenceTypes' -Value @() -Force
            }
        }
        else {
            # Merge file info with reference info
            $allResources[$resourcePath].Exists = $scannedResources[$resourcePath].Exists
            $allResources[$resourcePath].Size = $scannedResources[$resourcePath].Size
            $allResources[$resourcePath].LastModified = $scannedResources[$resourcePath].LastModified
            $allResources[$resourcePath].FullPath = $scannedResources[$resourcePath].FullPath
            # Keep IsReferenced = true since it was referenced
        }
    }
    
    # Ensure all resources have IsReferenced property
    foreach ($resourcePath in $allResources.Keys) {
        if (-not $allResources[$resourcePath].PSObject.Properties['IsReferenced']) {
            $allResources[$resourcePath] | Add-Member -MemberType NoteProperty -Name 'IsReferenced' -Value $false -Force
        }
    }
    
    # Create archive for this mod/version
    $archive = @{
        Version = "1.0"
        GeneratedAt = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        ModInfo = $modInfo
        Entities = $results.Entities
        UNIDs = $results.UNIDs
        Functions = $results.Functions
        Tags = $results.Tags
        Resources = $allResources
        Conflicts = @{}
        References = @{}
    }
    
    # Detect conflicts (duplicate UNIDs)
    Write-Host "Detecting conflicts..." -ForegroundColor Cyan
    foreach ($unid in $archive.UNIDs.Keys) {
        $unidInfo = $archive.UNIDs[$unid]
        if ($unidInfo.DefinedIn.Count -gt 1) {
            $archive.Conflicts[$unid] = @{
                UNID = $unid
                EntityName = $unidInfo.EntityName
                Files = $unidInfo.DefinedIn
                Count = $unidInfo.DefinedIn.Count
            }
        }
    }
    
    Write-Host "  Found $($archive.Conflicts.Count) UNID conflicts" -ForegroundColor $(if ($archive.Conflicts.Count -gt 0) { 'Yellow' } else { 'Green' })
    
    # Build reference map
    Write-Host "Building reference map..." -ForegroundColor Cyan
    foreach ($entityName in $archive.Entities.Keys) {
        $entity = $archive.Entities[$entityName]
        $archive.References[$entityName] = @{
            EntityName = $entityName
            UNID = $entity.UNID
            DefinedIn = $entity.DefinedIn
            UsedIn = $entity.UsedIn
            ReferenceCount = $entity.UsedIn.Count
        }
    }
    
    # Create folder for this mod/version
    $modFolder = Join-Path $outputDir $modInfo.FolderName
    if (-not (Test-Path $modFolder)) {
        New-Item -ItemType Directory -Path $modFolder -Force | Out-Null
    }
    
    # Save separate JSON files
    Write-Host "Saving archive files..." -ForegroundColor Cyan
    
    # Save entities
    $entitiesFile = Join-Path $modFolder "entities.json"
    $json = $archive.Entities | ConvertTo-Json -Depth 10 -Compress:$false
    [System.IO.File]::WriteAllText($entitiesFile, $json, $utf8NoBom)
    $entitiesSize = [math]::Round((Get-Item $entitiesFile).Length / 1KB, 2)
    Write-Host "  entities.json ($entitiesSize KB)" -ForegroundColor Gray
    
    # Save UNIDs
    $unidsFile = Join-Path $modFolder "unids.json"
    $json = $archive.UNIDs | ConvertTo-Json -Depth 10 -Compress:$false
    [System.IO.File]::WriteAllText($unidsFile, $json, $utf8NoBom)
    $unidsSize = [math]::Round((Get-Item $unidsFile).Length / 1KB, 2)
    Write-Host "  unids.json ($unidsSize KB)" -ForegroundColor Gray
    
    # Save functions
    $functionsFile = Join-Path $modFolder "functions.json"
    $json = $archive.Functions | ConvertTo-Json -Depth 10 -Compress:$false
    [System.IO.File]::WriteAllText($functionsFile, $json, $utf8NoBom)
    $functionsSize = [math]::Round((Get-Item $functionsFile).Length / 1KB, 2)
    Write-Host "  functions.json ($functionsSize KB)" -ForegroundColor Gray
    
    # Save tags
    $tagsFile = Join-Path $modFolder "tags.json"
    $json = $archive.Tags | ConvertTo-Json -Depth 10 -Compress:$false
    [System.IO.File]::WriteAllText($tagsFile, $json, $utf8NoBom)
    $tagsSize = [math]::Round((Get-Item $tagsFile).Length / 1KB, 2)
    Write-Host "  tags.json ($tagsSize KB)" -ForegroundColor Gray
    
    # Save resources
    $resourcesFile = Join-Path $modFolder "resources.json"
    $json = $archive.Resources | ConvertTo-Json -Depth 10 -Compress:$false
    [System.IO.File]::WriteAllText($resourcesFile, $json, $utf8NoBom)
    $resourcesSize = [math]::Round((Get-Item $resourcesFile).Length / 1KB, 2)
    Write-Host "  resources.json ($resourcesSize KB)" -ForegroundColor Gray
    
    # Save conflicts
    $conflictsFile = Join-Path $modFolder "conflicts.json"
    $json = $archive.Conflicts | ConvertTo-Json -Depth 10 -Compress:$false
    [System.IO.File]::WriteAllText($conflictsFile, $json, $utf8NoBom)
    Write-Host "  conflicts.json" -ForegroundColor Gray
    
    # Save references
    $referencesFile = Join-Path $modFolder "references.json"
    $json = $archive.References | ConvertTo-Json -Depth 10 -Compress:$false
    [System.IO.File]::WriteAllText($referencesFile, $json, $utf8NoBom)
    Write-Host "  references.json" -ForegroundColor Gray
    
    # Save metadata
    $metadataFile = Join-Path $modFolder "metadata.json"
    
    # Calculate referenced/unreferenced resources
    $resourcesReferenced = 0
    $resourcesUnreferenced = 0
    foreach ($prop in $archive.Resources.PSObject.Properties) {
        $resource = $archive.Resources[$prop.Name]
        if ($resource -and $resource.PSObject.Properties['IsReferenced'] -and $resource.IsReferenced) {
            $resourcesReferenced++
        } else {
            $resourcesUnreferenced++
        }
    }
    
    $metadata = @{
        Version = $archive.Version
        GeneratedAt = $archive.GeneratedAt
        ModInfo = $modInfo
        Statistics = @{
            Entities = ($archive.Entities.PSObject.Properties | Measure-Object).Count
            UNIDs = ($archive.UNIDs.PSObject.Properties | Measure-Object).Count
            Functions = ($archive.Functions.PSObject.Properties | Measure-Object).Count
            Tags = ($archive.Tags.PSObject.Properties | Measure-Object).Count
            Resources = ($archive.Resources.PSObject.Properties | Measure-Object).Count
            ResourcesReferenced = $resourcesReferenced
            ResourcesUnreferenced = $resourcesUnreferenced
            Conflicts = $archive.Conflicts.Count
            Files = $files.Count
        }
        IsUpdated = $isUpdated
    }
    $json = $metadata | ConvertTo-Json -Depth 10 -Compress:$false
    [System.IO.File]::WriteAllText($metadataFile, $json, $utf8NoBom)
    Write-Host "  metadata.json" -ForegroundColor Gray
    
    # If updated, create a "current" version
    if ($isUpdated -and $DetectUpdates) {
        $currentFolder = Join-Path $outputDir "$($modInfo.FolderName)_current"
        Write-Host "Creating 'current' version archive..." -ForegroundColor Cyan
        
        if (-not (Test-Path $currentFolder)) {
            New-Item -ItemType Directory -Path $currentFolder -Force | Out-Null
        }
        
        # Copy all files to current folder
        Copy-Item -Path (Join-Path $modFolder "*.json") -Destination $currentFolder -Force
        Write-Host "  Created: $currentFolder" -ForegroundColor Green
        
        # Update metadata to mark as current
        $currentMetadata = $metadata.PSObject.Copy()
        $currentMetadata.IsCurrent = $true
        $currentMetadataFile = Join-Path $currentFolder "metadata.json"
        $json = $currentMetadata | ConvertTo-Json -Depth 10 -Compress:$false
        [System.IO.File]::WriteAllText($currentMetadataFile, $json, $utf8NoBom)
    }
    
    # Update index
    $archiveEntry = @{
        Identifier = $modInfo.Identifier
        DisplayName = $modInfo.DisplayName
        FolderName = $modInfo.FolderName
        Type = $modInfo.Type
        ApiVersion = $modInfo.ApiVersion
        Statistics = $metadata.Statistics
        IsUpdated = $isUpdated
        HasCurrentVersion = ($isUpdated -and $DetectUpdates)
    }
    [void]$archiveIndexArchives.Add($archiveEntry)
    
    $archiveIndexTotalEntities = $archiveIndexTotalEntities + ($archive.Entities.PSObject.Properties | Measure-Object).Count
    $archiveIndexTotalUNIDs = $archiveIndexTotalUNIDs + ($archive.UNIDs.PSObject.Properties | Measure-Object).Count
    $archiveIndexTotalFunctions = $archiveIndexTotalFunctions + ($archive.Functions.PSObject.Properties | Measure-Object).Count
    $archiveIndexTotalTags = $archiveIndexTotalTags + ($archive.Tags.PSObject.Properties | Measure-Object).Count
    $archiveIndexTotalResources = $archiveIndexTotalResources + ($archive.Resources.PSObject.Properties | Measure-Object).Count
    $archiveIndexTotalConflicts = $archiveIndexTotalConflicts + $archive.Conflicts.Count
    
    Write-Host ""
    Write-Host "  Saved to: $modFolder" -ForegroundColor Green
    Write-Host ""
}

# Save index file
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Saving Archive Index" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

$archiveIndex = @{
    Version = "1.0"
    GeneratedAt = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Archives = $archiveIndexArchives
    TotalEntities = $archiveIndexTotalEntities
    TotalUNIDs = $archiveIndexTotalUNIDs
    TotalFunctions = $archiveIndexTotalFunctions
    TotalTags = $archiveIndexTotalTags
    TotalResources = $archiveIndexTotalResources
    TotalConflicts = $archiveIndexTotalConflicts
}

$indexFile = Join-Path $outputDir "index.json"
$json = $archiveIndex | ConvertTo-Json -Depth 10 -Compress:$false
[System.IO.File]::WriteAllText($indexFile, $json, $utf8NoBom)

$indexSize = [math]::Round((Get-Item $indexFile).Length / 1KB, 2)
Write-Host "  Saved: $indexFile ($indexSize KB)" -ForegroundColor Green

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Archive Statistics" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Archives:     $($archiveIndex.Archives.Count)" -ForegroundColor White
Write-Host "  Entities:     $($archiveIndex.TotalEntities)" -ForegroundColor White
Write-Host "  UNIDs:        $($archiveIndex.TotalUNIDs)" -ForegroundColor White
Write-Host "  Functions:    $($archiveIndex.TotalFunctions)" -ForegroundColor White
Write-Host "  Tags:         $($archiveIndex.TotalTags)" -ForegroundColor White
Write-Host "  Resources:    $($archiveIndex.TotalResources)" -ForegroundColor White
Write-Host "  Conflicts:    $($archiveIndex.TotalConflicts)" -ForegroundColor $(if ($archiveIndex.TotalConflicts -gt 0) { 'Yellow' } else { 'Green' })
Write-Host ""
Write-Host "  Output Directory: $outputDir" -ForegroundColor Green
Write-Host ""


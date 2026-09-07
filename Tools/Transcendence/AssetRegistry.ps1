<#
.SYNOPSIS
    Unified Asset Registry Manager - Central registry for all mod assets.

.DESCRIPTION
    Manages a JSON-based asset registry that drives automatic asset generation
    across multiple games (Elin, Terraria, Starbound, Transcendence).
    
    Features:
    - Add/update/remove registry entries

# Load shared asset generation settings
$settingsPath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "..\\AssetGenerationSettings.ps1"
if (Test-Path $settingsPath) {
    . $settingsPath
}
    - Generate assets from registry
    - Batch process by school, type, or tags
    - Export to multiple game formats
    - Validate registry against schema

.PARAMETER RegistryPath
    Path to registry JSON file (default: asset_registry.json)

.PARAMETER Action
    Action to perform: Add, Update, Remove, List, Generate, Validate, Export

.PARAMETER EntryId
    Entry ID for Add/Update/Remove operations

.PARAMETER EntryData
    Entry data (hashtable or JSON string)

.PARAMETER Filter
    Filter entries by school, type, or tags

.PARAMETER GameFormat
    Game format for export: Elin, Terraria, Starbound, All

.PARAMETER OutputDir
    Output directory for generated assets

.EXAMPLE
    .\AssetRegistry.ps1 -Action Add -EntryId "nature_verdant_pulse" -EntryData @{name="Verdant Pulse"; type="spell"; school="Nature Magic"}

.EXAMPLE
    .\AssetRegistry.ps1 -Action Generate -Filter @{school="Nature Magic"} -GameFormat All

.EXAMPLE
    .\AssetRegistry.ps1 -Action List -Filter @{type="spell"}
#>

[CmdletBinding()]
param(
    [string]$RegistryPath = "asset_registry.json",
    
    [ValidateSet("Add", "Update", "Remove", "List", "Generate", "Validate", "Export", "Init")]
    [string]$Action = "List",
    
    [string]$EntryId = "",
    
    [object]$EntryData = $null,
    
    [hashtable]$Filter = @{},
    
    [ValidateSet("Elin", "Terraria", "Starbound", "Transcendence", "All")]
    [string]$GameFormat = "All",
    
    [string]$OutputDir = "GeneratedAssets",
    
    [switch]$Force
)

$ErrorActionPreference = "Stop"

# ============================================================
# CONFIGURATION
# ============================================================

$script:SchemaPath = Join-Path $PSScriptRoot "asset_registry_schema.json"
$RegistryPath = [System.IO.Path]::GetFullPath($RegistryPath)

# ============================================================
# HELPER FUNCTIONS
# ============================================================

function Load-Registry {
    param([string]$Path)
    
    if (-not (Test-Path $Path)) {
        return @{
            metadata = @{
                version = "1.0"
                modName = "Unnamed Mod"
                author = ""
                lastUpdated = (Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ")
            }
            entries = @()
        }
    }
    
    try {
        $content = Get-Content $Path -Raw -Encoding UTF8 | ConvertFrom-Json
        return $content
    }
    catch {
        Write-Host "Error loading registry: $_" -ForegroundColor Red
        return $null
    }
}

function Save-Registry {
    param(
        [object]$Registry,
        [string]$Path
    )
    
    $Registry.metadata.lastUpdated = (Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ")
    
    $json = $Registry | ConvertTo-Json -Depth 20 -Compress:$false
    [System.IO.File]::WriteAllText($Path, $json, [System.Text.UTF8Encoding]::new($false))
}

function Validate-Entry {
    param([object]$Entry)
    
    $errors = @()
    
    # Required fields
    $required = @("id", "type", "name", "visual", "export")
    foreach ($field in $required) {
        if (-not $Entry.PSObject.Properties.Name -contains $field) {
            $errors += "Missing required field: $field"
        }
    }
    
    # Validate ID format
    if ($Entry.id -and $Entry.id -notmatch '^[a-z0-9_]+$') {
        $errors += "ID must be lowercase alphanumeric with underscores only: $($Entry.id)"
    }
    
    # Validate visual.icon
    if ($Entry.visual -and $Entry.visual.icon) {
        $icon = $Entry.visual.icon
        if (-not $icon.palette -or $icon.palette.Count -eq 0) {
            $errors += "Icon palette is required"
        }
        foreach ($color in $icon.palette) {
            if ($color -notmatch '^#([A-Fa-f0-9]{6})$') {
                $errors += "Invalid color format: $color (must be #RRGGBB)"
            }
        }
    }
    
    return $errors
}

function Filter-Entries {
    param(
        [array]$Entries,
        [hashtable]$Filter
    )
    
    if ($Filter.Count -eq 0) {
        return $Entries
    }
    
    $filtered = $Entries | Where-Object {
        $match = $true
        
        if ($Filter.ContainsKey("school")) {
            $match = $match -and $_.school -eq $Filter["school"]
        }
        
        if ($Filter.ContainsKey("type")) {
            $match = $match -and $_.type -eq $Filter["type"]
        }
        
        if ($Filter.ContainsKey("tags")) {
            $requiredTags = $Filter["tags"]
            if ($requiredTags -is [string]) {
                $requiredTags = @($requiredTags)
            }
            foreach ($tag in $requiredTags) {
                $match = $match -and $_.tags -contains $tag
            }
        }
        
        if ($Filter.ContainsKey("id")) {
            $match = $match -and $_.id -eq $Filter["id"]
        }
        
        return $match
    }
    
    return $filtered
}

function Generate-AssetsFromRegistry {
    param(
        [array]$Entries,
        [string]$GameFormat,
        [string]$OutputDir
    )
    
    Write-Host "Generating assets from registry..." -ForegroundColor Cyan
    Write-Host "  Entries: $($Entries.Count)" -ForegroundColor Gray
    Write-Host "  Format: $GameFormat" -ForegroundColor Gray
    Write-Host ""
    
    $successCount = 0
    
    foreach ($entry in $Entries) {
        Write-Host "Processing: $($entry.name) ($($entry.id))" -ForegroundColor Cyan
        
        # Generate based on export flags
        if ($GameFormat -eq "All" -or $GameFormat -eq "Elin") {
            if ($entry.export.elin) {
                Write-Host "  Generating Elin assets..." -ForegroundColor Gray
                
                # Convert registry entry to Elin format
                $spellDesc = if ($entry.description) {
                    "$($entry.school) - $($entry.name): $($entry.description)"
                } else {
                    "$($entry.school) - $($entry.name)"
                }
                
                # Parameters will be built in the try block below
                
                try {
                    $elinScript = Join-Path $PSScriptRoot "ElinSpellAssetGenerator.ps1"
                    
                    # Build parameter hashtable for splatting
                    $schoolDir = if ($entry.school) { $entry.school -replace '[^\w\s]', '' -replace '\s+', '_' } else { "Unknown" }
                    $elinParams = @{
                        SpellDescription = $spellDesc
                        SpellName = $entry.name
                        OutputDir = (Join-Path $OutputDir "Elin\$schoolDir")
                    }
                    
                    if ($entry.visual.icon) { $elinParams.GenerateIcon = $true }
                    if ($entry.visual.fx) { 
                        $elinParams.GenerateFX = $true
                        $frameCount = if ($entry.visual.fx.frames) { $entry.visual.fx.frames } else { 4 }
                        $elinParams.FXFrames = $frameCount
                    }
                    if ($entry.visual.projectile) {
                        $elinParams.GenerateProjectile = $true
                        $projFrames = if ($entry.visual.projectile.frames) { $entry.visual.projectile.frames } else { 2 }
                        $elinParams.ProjectileFrames = $projFrames
                    }
                    if ($entry.visual.buff) {
                        $elinParams.GenerateBuff = $true
                    }
                    
                    if ($entry.generation -and $entry.generation.useAI) {
                        $elinParams.UseAI = $true
                    }
                    
                    & $elinScript @elinParams 2>&1 | Out-Null
                    $successCount++
                }
                catch {
                    Write-Host "    Error: $_" -ForegroundColor Red
                }
            }
        }
        
        # Add Terraria/Starbound generation here when needed
        # Similar pattern for other games
        
        Write-Host ""
    }
    
    Write-Host "Generated assets for $successCount/$($Entries.Count) entries" -ForegroundColor $(if ($successCount -eq $Entries.Count) { "Green" } else { "Yellow" })
}

# ============================================================
# MAIN EXECUTION
# ============================================================

Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Unified Asset Registry Manager" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# Initialize registry if needed
if ($Action -eq "Init") {
    $registry = @{
        metadata = @{
            version = "1.0"
            modName = "My Mod"
            author = ""
            lastUpdated = (Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ")
        }
        entries = @()
    }
    
    Save-Registry -Registry $registry -Path $RegistryPath
    Write-Host "Initialized registry: $RegistryPath" -ForegroundColor Green
    exit 0
}

# Load registry
$registry = Load-Registry -Path $RegistryPath
if ($null -eq $registry) {
    Write-Host "Error: Could not load registry" -ForegroundColor Red
    exit 1
}

# Execute action
switch ($Action) {
    "List" {
        $entries = Filter-Entries -Entries $registry.entries -Filter $Filter
        
        Write-Host "Registry: $RegistryPath" -ForegroundColor Gray
        Write-Host "Total entries: $($registry.entries.Count)" -ForegroundColor Gray
        Write-Host "Filtered entries: $($entries.Count)" -ForegroundColor Gray
        Write-Host ""
        
        if ($entries.Count -eq 0) {
            Write-Host "No entries found" -ForegroundColor Yellow
        } else {
            foreach ($entry in $entries) {
                Write-Host "  [$($entry.id)] $($entry.name)" -ForegroundColor Cyan
                Write-Host "    Type: $($entry.type)" -ForegroundColor Gray
                if ($entry.school) {
                    Write-Host "    School: $($entry.school)" -ForegroundColor Gray
                }
                if ($entry.tags -and $entry.tags.Count -gt 0) {
                    Write-Host "    Tags: $($entry.tags -join ', ')" -ForegroundColor Gray
                }
                Write-Host ""
            }
        }
    }
    
    "Add" {
        if ([string]::IsNullOrWhiteSpace($EntryId)) {
            Write-Host "Error: EntryId required for Add action" -ForegroundColor Red
            exit 1
        }
        
        # Check if ID already exists
        $existing = $registry.entries | Where-Object { $_.id -eq $EntryId }
        if ($existing -and -not $Force) {
            Write-Host "Error: Entry with ID '$EntryId' already exists. Use -Force to overwrite or Update action." -ForegroundColor Red
            exit 1
        }
        
        # Convert EntryData to object
        $newEntry = $null
        
        if ($EntryData -is [string]) {
            # Check if it's a file path or JSON string
            if (Test-Path $EntryData) {
                $newEntry = Get-Content $EntryData -Raw -Encoding UTF8 | ConvertFrom-Json
            } else {
                $newEntry = $EntryData | ConvertFrom-Json
            }
        } elseif ($EntryData -is [PSCustomObject]) {
            $newEntry = $EntryData
        } elseif ($null -ne $EntryData) {
            # Try to convert hashtable via JSON
            try {
                $json = $EntryData | ConvertTo-Json -Depth 20 -Compress:$false
                $newEntry = $json | ConvertFrom-Json
            }
            catch {
                Write-Host "Error: Could not convert EntryData. Use JSON file path or PSCustomObject." -ForegroundColor Red
                Write-Host "  Error: $_" -ForegroundColor Red
                exit 1
            }
        } else {
            Write-Host "Error: EntryData is required for Add action" -ForegroundColor Red
            exit 1
        }
        
        # Ensure ID matches
        $newEntry | Add-Member -MemberType NoteProperty -Name "id" -Value $EntryId -Force
        
        # Validate
        $errors = Validate-Entry -Entry $newEntry
        if ($errors.Count -gt 0) {
            Write-Host "Validation errors:" -ForegroundColor Red
            foreach ($error in $errors) {
                Write-Host "  - $error" -ForegroundColor Red
            }
            exit 1
        }
        
        # Add or update
        if ($existing) {
            $index = [array]::IndexOf($registry.entries, $existing)
            $registry.entries[$index] = $newEntry
            Write-Host "Updated entry: $EntryId" -ForegroundColor Green
        } else {
            $registry.entries += $newEntry
            Write-Host "Added entry: $EntryId" -ForegroundColor Green
        }
        
        Save-Registry -Registry $registry -Path $RegistryPath
    }
    
    "Update" {
        if ([string]::IsNullOrWhiteSpace($EntryId)) {
            Write-Host "Error: EntryId required for Update action" -ForegroundColor Red
            exit 1
        }
        
        $existing = $registry.entries | Where-Object { $_.id -eq $EntryId }
        if (-not $existing) {
            Write-Host "Error: Entry with ID '$EntryId' not found" -ForegroundColor Red
            exit 1
        }
        
        # Merge EntryData with existing
        $updateData = if ($EntryData -is [hashtable]) {
            $EntryData
        } elseif ($EntryData -is [string]) {
            $EntryData | ConvertFrom-Json | ConvertTo-Hashtable
        } else {
            Write-Host "Error: EntryData must be hashtable or JSON string" -ForegroundColor Red
            exit 1
        }
        
        # Update fields
        foreach ($key in $updateData.Keys) {
            $existing.$key = $updateData[$key]
        }
        
        # Validate
        $errors = Validate-Entry -Entry $existing
        if ($errors.Count -gt 0) {
            Write-Host "Validation errors:" -ForegroundColor Red
            foreach ($error in $errors) {
                Write-Host "  - $error" -ForegroundColor Red
            }
            exit 1
        }
        
        Save-Registry -Registry $registry -Path $RegistryPath
        Write-Host "Updated entry: $EntryId" -ForegroundColor Green
    }
    
    "Remove" {
        if ([string]::IsNullOrWhiteSpace($EntryId)) {
            Write-Host "Error: EntryId required for Remove action" -ForegroundColor Red
            exit 1
        }
        
        $existing = $registry.entries | Where-Object { $_.id -eq $EntryId }
        if (-not $existing) {
            Write-Host "Error: Entry with ID '$EntryId' not found" -ForegroundColor Red
            exit 1
        }
        
        $registry.entries = $registry.entries | Where-Object { $_.id -ne $EntryId }
        Save-Registry -Registry $registry -Path $RegistryPath
        Write-Host "Removed entry: $EntryId" -ForegroundColor Green
    }
    
    "Validate" {
        Write-Host "Validating registry..." -ForegroundColor Cyan
        Write-Host ""
        
        $allErrors = @()
        foreach ($entry in $registry.entries) {
            $errors = Validate-Entry -Entry $entry
            if ($errors.Count -gt 0) {
                Write-Host "  [$($entry.id)] Errors:" -ForegroundColor Red
                foreach ($error in $errors) {
                    Write-Host "    - $error" -ForegroundColor Red
                    $allErrors += "$($entry.id): $error"
                }
            } else {
                Write-Host "  [$($entry.id)] ✓ Valid" -ForegroundColor Green
            }
        }
        
        Write-Host ""
        if ($allErrors.Count -eq 0) {
            Write-Host "Registry is valid!" -ForegroundColor Green
        } else {
            Write-Host "Found $($allErrors.Count) error(s)" -ForegroundColor Red
            exit 1
        }
    }
    
    "Generate" {
        $entries = Filter-Entries -Entries $registry.entries -Filter $Filter
        
        if ($entries.Count -eq 0) {
            Write-Host "No entries match filter" -ForegroundColor Yellow
            exit 0
        }
        
        Generate-AssetsFromRegistry -Entries $entries -GameFormat $GameFormat -OutputDir $OutputDir
    }
    
    "Export" {
        Write-Host "Export functionality - to be implemented" -ForegroundColor Yellow
        # Future: Export registry to game-specific formats
    }
}

Write-Host ""


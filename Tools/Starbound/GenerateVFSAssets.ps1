#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Generate assets for the Virtual File System (VFS).
    
.DESCRIPTION
    Generates visual assets for:
    - File type icons
    - Directory/folder icons
    - Archive icons
    - Mount/unmount indicators
    - VFS status indicators
    - Cache status indicators
    - File browser UI elements
    
.PARAMETER ModPath
    Path to the mod directory
    
.PARAMETER OllamaModel
    Ollama model to use
    
.PARAMETER UseCppBackend
    Use C++ backend for generation
#>

param(
    [Parameter(Mandatory=$false)]
    [string]$ModPath = "F:\Games\OpenStarbound\mods\Magi-Tech Arcane Alchemy and Sorcery",
    
    [Parameter(Mandatory=$false)]
    [string]$OllamaModel = "codellama:7b-instruct",
    
    [Parameter(Mandatory=$false)]
    [bool]$UseCppBackend = $true)

$ErrorActionPreference = "Stop"
# Validate ModPath is not empty
if ([string]::IsNullOrWhiteSpace($ModPath)) {
    Write-Host "Error: ModPath cannot be empty" -ForegroundColor Red
    Write-Host "  Please provide a valid mod path or use the default" -ForegroundColor Gray
    exit 1
}


# Load shared asset generation settings
$settingsPath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "..\\AssetGenerationSettings.ps1"
if (Test-Path $settingsPath) {
    . $settingsPath
}
$PSScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$assetGenerator = Join-Path $PSScriptRoot "StarboundOllamaAssetGenerator.ps1"

Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Virtual File System (VFS) Asset Generator" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

$generated = 0
$failed = 0

# ============================================================
# 1. FILE TYPE ICONS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating File Type Icons" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$fileTypes = @(
    @{ Id = "file_generic"; Name = "Generic File"; Desc = "Generic file icon, file, 32x32" },
    @{ Id = "file_text"; Name = "Text File"; Desc = "Text file icon, text document, 32x32" },
    @{ Id = "file_json"; Name = "JSON File"; Desc = "JSON file icon, JSON document, 32x32" },
    @{ Id = "file_lua"; Name = "Lua File"; Desc = "Lua file icon, Lua script, 32x32" },
    @{ Id = "file_image"; Name = "Image File"; Desc = "Image file icon, image file, 32x32" },
    @{ Id = "file_audio"; Name = "Audio File"; Desc = "Audio file icon, audio file, 32x32" },
    @{ Id = "file_binary"; Name = "Binary File"; Desc = "Binary file icon, binary file, 32x32" }
)

# Validate $ModPath before Join-Path
$fileTypeOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($fileTypeOutputDir)) {
    Write-Host "  [FAIL] fileTypeOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($fileTypeOutputDir)) {
    Write-Host "  [FAIL] fileTypeOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $fileTypeOutputDir)) {
    New-Item -ItemType Directory -Path $fileTypeOutputDir -Force | Out-Null
}

foreach ($fileType in $fileTypes) {
    Write-Host "Generating file type icon: $($fileType.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Icon"
            AssetName = $fileType.Id
            Prompt = "$($fileType.Desc). File type icon for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $fileTypeOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($fileType.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($fileType.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 2. DIRECTORY/FOLDER ICONS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Directory/Folder Icons" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$directoryIcons = @(
    @{ Id = "folder_generic"; Name = "Generic Folder"; Desc = "Generic folder icon, directory, 32x32" },
    @{ Id = "folder_open"; Name = "Open Folder"; Desc = "Open folder icon, open directory, 32x32" },
    @{ Id = "folder_root"; Name = "Root Folder"; Desc = "Root folder icon, root directory, 32x32" },
    @{ Id = "folder_mounted"; Name = "Mounted Folder"; Desc = "Mounted folder icon, mounted directory, 32x32" }
)

# Validate $ModPath before Join-Path
$directoryOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($directoryOutputDir)) {
    Write-Host "  [FAIL] directoryOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($directoryOutputDir)) {
    Write-Host "  [FAIL] directoryOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $directoryOutputDir)) {
    New-Item -ItemType Directory -Path $directoryOutputDir -Force | Out-Null
}

foreach ($icon in $directoryIcons) {
    Write-Host "Generating directory icon: $($icon.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Icon"
            AssetName = $icon.Id
            Prompt = "$($icon.Desc). Directory icon for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $directoryOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($icon.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($icon.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 3. ARCHIVE ICONS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Archive Icons" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$archiveIcons = @(
    @{ Id = "archive_generic"; Name = "Generic Archive"; Desc = "Generic archive icon, archive file, 32x32" },
    @{ Id = "archive_zip"; Name = "ZIP Archive"; Desc = "ZIP archive icon, ZIP file, 32x32" },
    @{ Id = "archive_mounted"; Name = "Mounted Archive"; Desc = "Mounted archive icon, mounted archive, 32x32" }
)

# Validate $ModPath before Join-Path
$archiveOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($archiveOutputDir)) {
    Write-Host "  [FAIL] archiveOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($archiveOutputDir)) {
    Write-Host "  [FAIL] archiveOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $archiveOutputDir)) {
    New-Item -ItemType Directory -Path $archiveOutputDir -Force | Out-Null
}

foreach ($icon in $archiveIcons) {
    Write-Host "Generating archive icon: $($icon.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Icon"
            AssetName = $icon.Id
            Prompt = "$($icon.Desc). Archive icon for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $archiveOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($icon.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($icon.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 4. MOUNT/UNMOUNT INDICATORS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Mount/Unmount Indicators" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$mountIndicators = @(
    @{ Id = "mount_mounted"; Name = "Mounted"; Desc = "Mounted indicator icon, mounted source, 32x32" },
    @{ Id = "mount_unmounted"; Name = "Unmounted"; Desc = "Unmounted indicator icon, unmounted source, 32x32" },
    @{ Id = "mount_button"; Name = "Mount Button"; Desc = "Mount button icon, mount source, 32x32" },
    @{ Id = "unmount_button"; Name = "Unmount Button"; Desc = "Unmount button icon, unmount source, 32x32" }
)

# Validate $ModPath before Join-Path
$mountOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($mountOutputDir)) {
    Write-Host "  [FAIL] mountOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($mountOutputDir)) {
    Write-Host "  [FAIL] mountOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $mountOutputDir)) {
    New-Item -ItemType Directory -Path $mountOutputDir -Force | Out-Null
}

foreach ($indicator in $mountIndicators) {
    Write-Host "Generating mount indicator: $($indicator.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Icon"
            AssetName = $indicator.Id
            Prompt = "$($indicator.Desc). Mount/unmount indicator for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $mountOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($indicator.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($indicator.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 5. VFS STATUS INDICATORS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating VFS Status Indicators" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$statusIndicators = @(
    @{ Id = "status_ready"; Name = "VFS Ready"; Desc = "VFS ready indicator icon, system ready, 32x32" },
    @{ Id = "status_indexing"; Name = "Indexing"; Desc = "Indexing indicator icon, building index, 32x32" },
    @{ Id = "status_index_valid"; Name = "Index Valid"; Desc = "Index valid indicator icon, index valid, 32x32" },
    @{ Id = "status_index_invalid"; Name = "Index Invalid"; Desc = "Index invalid indicator icon, index invalid, 32x32" },
    @{ Id = "status_error"; Name = "VFS Error"; Desc = "VFS error indicator icon, system error, 32x32" }
)

# Validate $ModPath before Join-Path
$statusOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($statusOutputDir)) {
    Write-Host "  [FAIL] statusOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($statusOutputDir)) {
    Write-Host "  [FAIL] statusOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $statusOutputDir)) {
    New-Item -ItemType Directory -Path $statusOutputDir -Force | Out-Null
}

foreach ($indicator in $statusIndicators) {
    Write-Host "Generating status indicator: $($indicator.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Icon"
            AssetName = $indicator.Id
            Prompt = "$($indicator.Desc). VFS status indicator for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $statusOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($indicator.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($indicator.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 6. CACHE STATUS INDICATORS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Cache Status Indicators" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$cacheIndicators = @(
    @{ Id = "cache_enabled"; Name = "Cache Enabled"; Desc = "Cache enabled indicator icon, cache on, 32x32" },
    @{ Id = "cache_disabled"; Name = "Cache Disabled"; Desc = "Cache disabled indicator icon, cache off, 32x32" },
    @{ Id = "cache_hit"; Name = "Cache Hit"; Desc = "Cache hit indicator icon, cache hit, 32x32" },
    @{ Id = "cache_miss"; Name = "Cache Miss"; Desc = "Cache miss indicator icon, cache miss, 32x32" },
    @{ Id = "cache_full"; Name = "Cache Full"; Desc = "Cache full indicator icon, cache full, 32x32" }
)

# Validate $ModPath before Join-Path
$cacheOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($cacheOutputDir)) {
    Write-Host "  [FAIL] cacheOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($cacheOutputDir)) {
    Write-Host "  [FAIL] cacheOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $cacheOutputDir)) {
    New-Item -ItemType Directory -Path $cacheOutputDir -Force | Out-Null
}

foreach ($indicator in $cacheIndicators) {
    Write-Host "Generating cache indicator: $($indicator.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Icon"
            AssetName = $indicator.Id
            Prompt = "$($indicator.Desc). Cache status indicator for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $cacheOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($indicator.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($indicator.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 7. FILE BROWSER UI ELEMENTS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating File Browser UI Elements" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$browserUI = @(
    @{ Id = "ui_panel_browser"; Name = "File Browser Panel"; Desc = "File browser panel background, file browser UI, 256x256" },
    @{ Id = "ui_panel_mounts"; Name = "Mounts Panel"; Desc = "Mounts panel background, mount management UI, 128x128" },
    @{ Id = "ui_button_refresh"; Name = "Refresh Button"; Desc = "Refresh button icon, refresh file list, 32x32" },
    @{ Id = "ui_button_rebuild_index"; Name = "Rebuild Index Button"; Desc = "Rebuild index button icon, rebuild index, 32x32" },
    @{ Id = "ui_button_clear_cache"; Name = "Clear Cache Button"; Desc = "Clear cache button icon, clear cache, 32x32" },
    @{ Id = "ui_button_search"; Name = "Search Button"; Desc = "Search button icon, search files, 32x32" }
)

# Validate $ModPath before Join-Path
$browserUIOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($browserUIOutputDir)) {
    Write-Host "  [FAIL] browserUIOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($browserUIOutputDir)) {
    Write-Host "  [FAIL] browserUIOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $browserUIOutputDir)) {
    New-Item -ItemType Directory -Path $browserUIOutputDir -Force | Out-Null
}

foreach ($element in $browserUI) {
    Write-Host "Generating browser UI element: $($element.Name)" -ForegroundColor Cyan
    
    try {
        $assetType = if ($element.Id -like "*panel*") { "Texture" } else { "Icon" }
        
        $params = @{
            AssetType = $assetType
            AssetName = $element.Id
            Prompt = "$($element.Desc). File browser UI element for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $browserUIOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($element.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($element.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# SUMMARY
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Generation Complete" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "Generated: $generated assets" -ForegroundColor Green
Write-Host "Failed: $failed assets" -ForegroundColor $(if ($failed -gt 0) { "Red" } else { "Green" })
Write-Host ""
Write-Host "Assets saved to:" -ForegroundColor Gray
Write-Host "  File Types: $(Join-Path $ModPath 'assets\vfs\file_types')" -ForegroundColor Gray
Write-Host "  Directories: $(Join-Path $ModPath 'assets\vfs\directories')" -ForegroundColor Gray
Write-Host "  Archives: $(Join-Path $ModPath 'assets\vfs\archives')" -ForegroundColor Gray
Write-Host "  Mount: $(Join-Path $ModPath 'assets\vfs\mount')" -ForegroundColor Gray
Write-Host "  Status: $(Join-Path $ModPath 'assets\vfs\status')" -ForegroundColor Gray
Write-Host "  Cache: $(Join-Path $ModPath 'assets\vfs\cache')" -ForegroundColor Gray
Write-Host "  UI: $(Join-Path $ModPath 'assets\vfs\ui')" -ForegroundColor Gray
Write-Host ""

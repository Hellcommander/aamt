<#
.SYNOPSIS
  Source Folder Watcher for Auto-Updating API Rules
  
.DESCRIPTION
  Uses FileSystemWatcher to monitor the game's source folders and
  automatically regenerate API rules when files change.
  
  This keeps the mod tools always aligned with the latest API.
  
.NOTES
  Version: 1.0
  Author: Transcendence Mod Tools
#>

# ============================================================
# CONFIGURATION
# ============================================================

$script:WatcherInstances = @{}
$script:LastUpdateTime = [datetime]::MinValue
$script:UpdateDebounceMs = 5000  # Wait 5 seconds after last change before updating

# Base source directory
$script:BaseSourceDir = "D:\games\Steam\steamapps\common\Transcendence\game and dlc source"

# Default source paths to watch (will be auto-expanded with DLC sources)
$script:DefaultWatchPaths = @(
    "D:\games\Steam\steamapps\common\Transcendence\game and dlc source\TranscendenceDev-integration-API57\Transcendence\TransCore",
    "D:\games\Steam\steamapps\common\Transcendence\game and dlc source\Transcendence_Source"
)

# ============================================================
# WATCHER MANAGEMENT
# ============================================================

function Start-SourceWatcher {
    <#
    .SYNOPSIS
      Starts watching source folders for changes
    #>
    param(
        [string[]]$WatchPaths = $script:DefaultWatchPaths,
        [switch]$AutoUpdate,
        [int]$DebounceMs = 5000
    )
    
    Write-Host "Starting Source Watcher..." -ForegroundColor Cyan
    Write-Host ""
    
    $script:UpdateDebounceMs = $DebounceMs
    
    # Load API rules module
    $apiRulesModule = Join-Path $PSScriptRoot 'TranscendenceModTools_ApiRules.ps1'
    if (Test-Path $apiRulesModule) {
        . $apiRulesModule
    }
    else {
        Write-Host "ERROR: API Rules module not found: $apiRulesModule" -ForegroundColor Red
        return $false
    }
    
    # Stop any existing watchers
    Stop-SourceWatcher
    
    # Auto-detect and add DLC sources
    $allWatchPaths = @($WatchPaths)
    foreach ($basePath in $WatchPaths) {
        if (Test-Path $basePath) {
            $baseDir = Split-Path $basePath -Parent
            $dlcFolders = Get-ChildItem -LiteralPath $baseDir -Directory -ErrorAction SilentlyContinue | Where-Object {
                $name = $_.Name
                if ($name -eq "Transcendence_Source" -or $name -like "TranscendenceDev-*") {
                    return $false
                }
                return $name -like "*_Source" -or $name -like "*Source"
            }
            
            foreach ($dlcFolder in $dlcFolders) {
                $xmlFiles = Get-ChildItem -LiteralPath $dlcFolder.FullName -Filter "*.xml" -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
                if ($xmlFiles -and $allWatchPaths -notcontains $dlcFolder.FullName) {
                    $allWatchPaths += $dlcFolder.FullName
                    Write-Host "  Auto-detected DLC source: $($dlcFolder.Name)" -ForegroundColor Cyan
                }
            }
        }
    }
    
    $watcherCount = 0
    
    foreach ($watchPath in $allWatchPaths) {
        if (-not (Test-Path $watchPath)) {
            Write-Host "  Path not found, skipping: $watchPath" -ForegroundColor Yellow
            continue
        }
        
        try {
            $watcher = New-Object System.IO.FileSystemWatcher
            $watcher.Path = $watchPath
            $watcher.Filter = "*.xml"
            $watcher.IncludeSubdirectories = $true
            $watcher.EnableRaisingEvents = $true
            $watcher.NotifyFilter = [System.IO.NotifyFilters]::LastWrite -bor [System.IO.NotifyFilters]::FileName -bor [System.IO.NotifyFilters]::DirectoryName
            
            # Create action for changes
            $action = {
                $path = $Event.SourceEventArgs.FullPath
                $changeType = $Event.SourceEventArgs.ChangeType
                $fileName = Split-Path -Leaf $path
                
                # Log change
                $timestamp = Get-Date -Format "HH:mm:ss"
                Write-Host "[$timestamp] $changeType`: $fileName" -ForegroundColor DarkGray
                
                # Debounce: only trigger update after a pause in changes
                $script:LastChangeTime = Get-Date
            }
            
            # Register events
            Register-ObjectEvent $watcher Changed -Action $action -SourceIdentifier "SourceWatcher_Changed_$watcherCount" | Out-Null
            Register-ObjectEvent $watcher Created -Action $action -SourceIdentifier "SourceWatcher_Created_$watcherCount" | Out-Null
            Register-ObjectEvent $watcher Deleted -Action $action -SourceIdentifier "SourceWatcher_Deleted_$watcherCount" | Out-Null
            Register-ObjectEvent $watcher Renamed -Action $action -SourceIdentifier "SourceWatcher_Renamed_$watcherCount" | Out-Null
            
            $script:WatcherInstances[$watchPath] = $watcher
            $watcherCount++
            
            Write-Host "  Watching: $watchPath" -ForegroundColor Green
        }
        catch {
            Write-Host "  ERROR watching $watchPath`: $_" -ForegroundColor Red
        }
    }
    
    if ($watcherCount -gt 0) {
        Write-Host ""
        Write-Host "Watching $watcherCount source folder(s)" -ForegroundColor Cyan
        Write-Host "Press Ctrl+C to stop, or call Stop-SourceWatcher" -ForegroundColor Gray
        
        if ($AutoUpdate) {
            Write-Host ""
            Write-Host "Auto-update enabled - API rules will regenerate on changes" -ForegroundColor Yellow
            
            # Start background job to check for updates
            $updateJob = Start-Job -ScriptBlock {
                param($debounceMs, $toolsDir)
                
                # Import the module in the job
                . (Join-Path $toolsDir 'TranscendenceModTools_ApiRules.ps1')
                
                $lastCheck = Get-Date
                
                while ($true) {
                    Start-Sleep -Milliseconds 1000
                    
                    # Check if enough time has passed since last change
                    $timeSinceLastChange = (Get-Date) - $script:LastChangeTime
                    
                    if ($script:LastChangeTime -gt $lastCheck -and $timeSinceLastChange.TotalMilliseconds -gt $debounceMs) {
                        Write-Host "`n[$(Get-Date -Format 'HH:mm:ss')] Regenerating API rules..." -ForegroundColor Cyan
                        Update-ApiRules
                        $lastCheck = Get-Date
                    }
                }
            } -ArgumentList $script:UpdateDebounceMs, $PSScriptRoot
            
            $script:UpdateJob = $updateJob
        }
        
        return $true
    }
    else {
        Write-Host "No folders being watched" -ForegroundColor Yellow
        return $false
    }
}

function Stop-SourceWatcher {
    <#
    .SYNOPSIS
      Stops all source watchers
    #>
    
    # Unregister events
    Get-EventSubscriber | Where-Object { $_.SourceIdentifier -like "SourceWatcher_*" } | Unregister-Event -ErrorAction SilentlyContinue
    
    # Dispose watchers
    foreach ($path in $script:WatcherInstances.Keys) {
        $watcher = $script:WatcherInstances[$path]
        if ($watcher) {
            $watcher.EnableRaisingEvents = $false
            $watcher.Dispose()
        }
    }
    
    $script:WatcherInstances = @{}
    
    # Stop update job
    if ($script:UpdateJob) {
        Stop-Job $script:UpdateJob -ErrorAction SilentlyContinue
        Remove-Job $script:UpdateJob -ErrorAction SilentlyContinue
        $script:UpdateJob = $null
    }
    
    Write-Host "Source watcher stopped" -ForegroundColor Gray
}

function Get-WatcherStatus {
    <#
    .SYNOPSIS
      Gets the current status of source watchers
    #>
    
    $status = @{
        IsWatching = $script:WatcherInstances.Count -gt 0
        WatchedPaths = @($script:WatcherInstances.Keys)
        LastUpdateTime = $script:LastUpdateTime
    }
    
    return $status
}

# ============================================================
# MANUAL TRIGGER
# ============================================================

function Invoke-SourceUpdate {
    <#
    .SYNOPSIS
      Manually triggers an API rules update
    #>
    param(
        [string[]]$SourcePaths = $script:DefaultWatchPaths
    )
    
    # Load API rules module
    $apiRulesModule = Join-Path $PSScriptRoot 'TranscendenceModTools_ApiRules.ps1'
    if (Test-Path $apiRulesModule) {
        . $apiRulesModule
    }
    else {
        Write-Host "ERROR: API Rules module not found: $apiRulesModule" -ForegroundColor Red
        return $null
    }
    
    $result = Update-ApiRules -SourcePaths $SourcePaths
    $script:LastUpdateTime = Get-Date
    
    return $result
}

# ============================================================
# CHANGE DETECTION
# ============================================================

function Get-SourceChanges {
    <#
    .SYNOPSIS
      Compares current source with stored API rules to detect changes
    #>
    param(
        [string[]]$SourcePaths = $script:DefaultWatchPaths
    )
    
    # Load API rules module
    $apiRulesModule = Join-Path $PSScriptRoot 'TranscendenceModTools_ApiRules.ps1'
    if (Test-Path $apiRulesModule) {
        . $apiRulesModule
    }
    else {
        Write-Host "ERROR: API Rules module not found" -ForegroundColor Red
        return $null
    }
    
    # Load existing rules
    $existingRules = Get-ApiRules
    if (-not $existingRules) {
        Write-Host "No existing API rules found - run Update-ApiRules first" -ForegroundColor Yellow
        return $null
    }
    
    Write-Host "Scanning for API changes..." -ForegroundColor Cyan
    Write-Host ""
    
    # Get current state
    $currentTags = Get-XmlTagInventory -SourcePaths $SourcePaths
    $currentEvents = Get-EventInventory -SourcePaths $SourcePaths
    $currentFunctions = Get-TlispFunctionInventory -SourcePaths $SourcePaths
    $currentEntities = Get-EntityInventory -SourcePaths $SourcePaths
    
    $changes = @{
        NewTags = [System.Collections.ArrayList]::new()
        RemovedTags = [System.Collections.ArrayList]::new()
        NewEvents = [System.Collections.ArrayList]::new()
        RemovedEvents = [System.Collections.ArrayList]::new()
        NewFunctions = [System.Collections.ArrayList]::new()
        RemovedFunctions = [System.Collections.ArrayList]::new()
        NewEntities = [System.Collections.ArrayList]::new()
        RemovedEntities = [System.Collections.ArrayList]::new()
    }
    
    # Compare tags
    $existingTagNames = @($existingRules.Tags.PSObject.Properties.Name)
    $currentTagNames = @($currentTags.Tags.Keys)
    
    foreach ($tag in $currentTagNames) {
        if ($existingTagNames -notcontains $tag) {
            [void]$changes.NewTags.Add($tag)
        }
    }
    
    foreach ($tag in $existingTagNames) {
        if ($currentTagNames -notcontains $tag) {
            [void]$changes.RemovedTags.Add($tag)
        }
    }
    
    # Compare events
    $existingEventNames = @($existingRules.Events.PSObject.Properties.Name)
    $currentEventNames = @($currentEvents.Keys)
    
    foreach ($event in $currentEventNames) {
        if ($existingEventNames -notcontains $event) {
            [void]$changes.NewEvents.Add($event)
        }
    }
    
    foreach ($event in $existingEventNames) {
        if ($currentEventNames -notcontains $event) {
            [void]$changes.RemovedEvents.Add($event)
        }
    }
    
    # Compare functions
    $existingFuncNames = @($existingRules.Functions.PSObject.Properties.Name)
    $currentFuncNames = @($currentFunctions.Keys)
    
    foreach ($func in $currentFuncNames) {
        if ($existingFuncNames -notcontains $func) {
            [void]$changes.NewFunctions.Add($func)
        }
    }
    
    foreach ($func in $existingFuncNames) {
        if ($currentFuncNames -notcontains $func) {
            [void]$changes.RemovedFunctions.Add($func)
        }
    }
    
    # Compare entities
    $existingEntityNames = @($existingRules.Entities.PSObject.Properties.Name)
    $currentEntityNames = @($currentEntities.Keys)
    
    foreach ($entity in $currentEntityNames) {
        if ($existingEntityNames -notcontains $entity) {
            [void]$changes.NewEntities.Add($entity)
        }
    }
    
    foreach ($entity in $existingEntityNames) {
        if ($currentEntityNames -notcontains $entity) {
            [void]$changes.RemovedEntities.Add($entity)
        }
    }
    
    # Report changes
    $hasChanges = $false
    
    if ($changes.NewTags.Count -gt 0) {
        $hasChanges = $true
        Write-Host "New Tags ($($changes.NewTags.Count)):" -ForegroundColor Green
        foreach ($tag in $changes.NewTags | Select-Object -First 10) {
            Write-Host "  + $tag" -ForegroundColor Green
        }
        if ($changes.NewTags.Count -gt 10) {
            Write-Host "  ... and $($changes.NewTags.Count - 10) more" -ForegroundColor Gray
        }
        Write-Host ""
    }
    
    if ($changes.RemovedTags.Count -gt 0) {
        $hasChanges = $true
        Write-Host "Removed Tags ($($changes.RemovedTags.Count)):" -ForegroundColor Red
        foreach ($tag in $changes.RemovedTags | Select-Object -First 10) {
            Write-Host "  - $tag" -ForegroundColor Red
        }
        if ($changes.RemovedTags.Count -gt 10) {
            Write-Host "  ... and $($changes.RemovedTags.Count - 10) more" -ForegroundColor Gray
        }
        Write-Host ""
    }
    
    if ($changes.NewFunctions.Count -gt 0) {
        $hasChanges = $true
        Write-Host "New Functions ($($changes.NewFunctions.Count)):" -ForegroundColor Green
        foreach ($func in $changes.NewFunctions | Select-Object -First 10) {
            Write-Host "  + $func" -ForegroundColor Green
        }
        if ($changes.NewFunctions.Count -gt 10) {
            Write-Host "  ... and $($changes.NewFunctions.Count - 10) more" -ForegroundColor Gray
        }
        Write-Host ""
    }
    
    if ($changes.RemovedFunctions.Count -gt 0) {
        $hasChanges = $true
        Write-Host "Removed Functions ($($changes.RemovedFunctions.Count)):" -ForegroundColor Red
        foreach ($func in $changes.RemovedFunctions | Select-Object -First 10) {
            Write-Host "  - $func" -ForegroundColor Red
        }
        if ($changes.RemovedFunctions.Count -gt 10) {
            Write-Host "  ... and $($changes.RemovedFunctions.Count - 10) more" -ForegroundColor Gray
        }
        Write-Host ""
    }
    
    if (-not $hasChanges) {
        Write-Host "No API changes detected" -ForegroundColor Green
    }
    
    return $changes
}

# ============================================================
# EXPORT
# ============================================================

Export-ModuleMember -Function @(
    'Start-SourceWatcher',
    'Stop-SourceWatcher',
    'Get-WatcherStatus',
    'Invoke-SourceUpdate',
    'Get-SourceChanges'
)


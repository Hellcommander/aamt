#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Generate assets for the SimulationAgent System.
    
.DESCRIPTION
    Generates visual assets for:
    - Phase indicators (Phase 1-15)
    - Module icons (Orbital, World State, Physics, NPC, Procedural, Flight Control, etc.)
    - Simulation state indicators
    - Debug rendering indicators
    - UI control elements
    - Performance monitoring indicators
    - Simulation event effects
    
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
Write-Host "  SimulationAgent System Asset Generator" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

$generated = 0
$failed = 0

# ============================================================
# 1. PHASE INDICATORS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Phase Indicators" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$phases = @(
    @{ Id = "phase_1"; Name = "Phase 1"; Desc = "Phase 1 indicator icon, core world and physics, 32x32" },
    @{ Id = "phase_2"; Name = "Phase 2"; Desc = "Phase 2 indicator icon, simulation phase 2, 32x32" },
    @{ Id = "phase_3"; Name = "Phase 3"; Desc = "Phase 3 indicator icon, simulation phase 3, 32x32" },
    @{ Id = "phase_4"; Name = "Phase 4"; Desc = "Phase 4 indicator icon, simulation phase 4, 32x32" },
    @{ Id = "phase_5"; Name = "Phase 5"; Desc = "Phase 5 indicator icon, simulation phase 5, 32x32" },
    @{ Id = "phase_6"; Name = "Phase 6"; Desc = "Phase 6 indicator icon, procedural generation, 32x32" },
    @{ Id = "phase_7"; Name = "Phase 7"; Desc = "Phase 7 indicator icon, simulation phase 7, 32x32" },
    @{ Id = "phase_8"; Name = "Phase 8"; Desc = "Phase 8 indicator icon, simulation phase 8, 32x32" },
    @{ Id = "phase_9"; Name = "Phase 9"; Desc = "Phase 9 indicator icon, simulation phase 9, 32x32" },
    @{ Id = "phase_10"; Name = "Phase 10"; Desc = "Phase 10 indicator icon, simulation phase 10, 32x32" },
    @{ Id = "phase_11"; Name = "Phase 11"; Desc = "Phase 11 indicator icon, simulation phase 11, 32x32" },
    @{ Id = "phase_12"; Name = "Phase 12"; Desc = "Phase 12 indicator icon, simulation phase 12, 32x32" },
    @{ Id = "phase_14"; Name = "Phase 14"; Desc = "Phase 14 indicator icon, flight control, 32x32" },
    @{ Id = "phase_15"; Name = "Phase 15"; Desc = "Phase 15 indicator icon, simulation phase 15, 32x32" }
)

# Validate $ModPath before Join-Path
$phaseOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($phaseOutputDir)) {
    Write-Host "  [FAIL] phaseOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($phaseOutputDir)) {
    Write-Host "  [FAIL] phaseOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $phaseOutputDir)) {
    New-Item -ItemType Directory -Path $phaseOutputDir -Force | Out-Null
}

foreach ($phase in $phases) {
    Write-Host "Generating phase indicator: $($phase.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Icon"
            AssetName = $phase.Id
            Prompt = "$($phase.Desc). Simulation phase indicator for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $phaseOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($phase.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($phase.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 2. MODULE ICONS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Module Icons" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$modules = @(
    @{ Id = "module_orbital"; Name = "Orbital Module"; Desc = "Orbital simulation module icon, orbital mechanics, 32x32" },
    @{ Id = "module_world_state"; Name = "World State Module"; Desc = "World state module icon, world state management, 32x32" },
    @{ Id = "module_physics"; Name = "Physics Module"; Desc = "Physics module icon, physics simulation, 32x32" },
    @{ Id = "module_npc"; Name = "NPC Module"; Desc = "NPC module icon, NPC simulation, 32x32" },
    @{ Id = "module_procedural"; Name = "Procedural Module"; Desc = "Procedural generation module icon, procedural generation, 32x32" },
    @{ Id = "module_flight_control"; Name = "Flight Control Module"; Desc = "Flight control module icon, flight control, 32x32" },
    @{ Id = "module_star_field"; Name = "Star Field Module"; Desc = "Star field module icon, star field generation, 32x32" },
    @{ Id = "module_noise"; Name = "Noise Module"; Desc = "Noise generation module icon, noise generation, 32x32" }
)

# Validate $ModPath before Join-Path
$moduleOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($moduleOutputDir)) {
    Write-Host "  [FAIL] moduleOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($moduleOutputDir)) {
    Write-Host "  [FAIL] moduleOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $moduleOutputDir)) {
    New-Item -ItemType Directory -Path $moduleOutputDir -Force | Out-Null
}

foreach ($module in $modules) {
    Write-Host "Generating module icon: $($module.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Icon"
            AssetName = $module.Id
            Prompt = "$($module.Desc). Simulation module icon for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $moduleOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($module.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($module.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 3. SIMULATION STATE INDICATORS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Simulation State Indicators" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$states = @(
    @{ Id = "state_active"; Name = "Active State"; Desc = "Active simulation state indicator, simulation active, 32x32" },
    @{ Id = "state_paused"; Name = "Paused State"; Desc = "Paused simulation state indicator, simulation paused, 32x32" },
    @{ Id = "state_stopped"; Name = "Stopped State"; Desc = "Stopped simulation state indicator, simulation stopped, 32x32" },
    @{ Id = "state_error"; Name = "Error State"; Desc = "Error simulation state indicator, simulation error, 32x32" },
    @{ Id = "state_initializing"; Name = "Initializing State"; Desc = "Initializing simulation state indicator, simulation initializing, 32x32" },
    @{ Id = "state_shutting_down"; Name = "Shutting Down State"; Desc = "Shutting down simulation state indicator, simulation shutting down, 32x32" }
)

# Validate $ModPath before Join-Path
$stateOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($stateOutputDir)) {
    Write-Host "  [FAIL] stateOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($stateOutputDir)) {
    Write-Host "  [FAIL] stateOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $stateOutputDir)) {
    New-Item -ItemType Directory -Path $stateOutputDir -Force | Out-Null
}

foreach ($state in $states) {
    Write-Host "Generating state indicator: $($state.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Icon"
            AssetName = $state.Id
            Prompt = "$($state.Desc). Simulation state indicator for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $stateOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($state.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($state.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 4. DEBUG RENDERING INDICATORS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Debug Rendering Indicators" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$debugIndicators = @(
    @{ Id = "debug_enabled"; Name = "Debug Enabled"; Desc = "Debug rendering enabled indicator, debug active, 32x32" },
    @{ Id = "debug_disabled"; Name = "Debug Disabled"; Desc = "Debug rendering disabled indicator, debug inactive, 32x32" },
    @{ Id = "debug_physics"; Name = "Debug Physics"; Desc = "Debug physics rendering indicator, physics debug, 32x32" },
    @{ Id = "debug_collision"; Name = "Debug Collision"; Desc = "Debug collision rendering indicator, collision debug, 32x32" },
    @{ Id = "debug_pathfinding"; Name = "Debug Pathfinding"; Desc = "Debug pathfinding rendering indicator, pathfinding debug, 32x32" }
)

# Validate $ModPath before Join-Path
$debugOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($debugOutputDir)) {
    Write-Host "  [FAIL] debugOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($debugOutputDir)) {
    Write-Host "  [FAIL] debugOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $debugOutputDir)) {
    New-Item -ItemType Directory -Path $debugOutputDir -Force | Out-Null
}

foreach ($indicator in $debugIndicators) {
    Write-Host "Generating debug indicator: $($indicator.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Icon"
            AssetName = $indicator.Id
            Prompt = "$($indicator.Desc). Debug rendering indicator for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $debugOutputDir
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
# 5. UI CONTROL ELEMENTS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating UI Control Elements" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$uiControls = @(
    @{ Id = "control_play"; Name = "Play Control"; Desc = "Play simulation control button, play, 32x32" },
    @{ Id = "control_pause"; Name = "Pause Control"; Desc = "Pause simulation control button, pause, 32x32" },
    @{ Id = "control_stop"; Name = "Stop Control"; Desc = "Stop simulation control button, stop, 32x32" },
    @{ Id = "control_reset"; Name = "Reset Control"; Desc = "Reset simulation control button, reset, 32x32" },
    @{ Id = "control_step"; Name = "Step Control"; Desc = "Step simulation control button, step, 32x32" },
    @{ Id = "control_speed_up"; Name = "Speed Up Control"; Desc = "Speed up simulation control button, speed up, 32x32" },
    @{ Id = "control_slow_down"; Name = "Slow Down Control"; Desc = "Slow down simulation control button, slow down, 32x32" }
)

# Validate $ModPath before Join-Path
$uiOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($uiOutputDir)) {
    Write-Host "  [FAIL] uiOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($uiOutputDir)) {
    Write-Host "  [FAIL] uiOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $uiOutputDir)) {
    New-Item -ItemType Directory -Path $uiOutputDir -Force | Out-Null
}

foreach ($control in $uiControls) {
    Write-Host "Generating UI control: $($control.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Icon"
            AssetName = $control.Id
            Prompt = "$($control.Desc). Simulation UI control for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $uiOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($control.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($control.Name) : $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ============================================================
# 6. PERFORMANCE MONITORING INDICATORS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Performance Monitoring Indicators" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$performanceIndicators = @(
    @{ Id = "perf_cpu"; Name = "CPU Performance"; Desc = "CPU performance indicator, CPU usage, 32x32" },
    @{ Id = "perf_memory"; Name = "Memory Performance"; Desc = "Memory performance indicator, memory usage, 32x32" },
    @{ Id = "perf_fps"; Name = "FPS Performance"; Desc = "FPS performance indicator, frames per second, 32x32" },
    @{ Id = "perf_entity_count"; Name = "Entity Count"; Desc = "Entity count indicator, entity count, 32x32" },
    @{ Id = "perf_update_time"; Name = "Update Time"; Desc = "Update time indicator, update time, 32x32" },
    @{ Id = "perf_good"; Name = "Good Performance"; Desc = "Good performance indicator, performance good, 32x32" },
    @{ Id = "perf_warning"; Name = "Warning Performance"; Desc = "Warning performance indicator, performance warning, 32x32" },
    @{ Id = "perf_critical"; Name = "Critical Performance"; Desc = "Critical performance indicator, performance critical, 32x32" }
)

# Validate $ModPath before Join-Path
$perfOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($perfOutputDir)) {
    Write-Host "  [FAIL] perfOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($perfOutputDir)) {
    Write-Host "  [FAIL] perfOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $perfOutputDir)) {
    New-Item -ItemType Directory -Path $perfOutputDir -Force | Out-Null
}

foreach ($indicator in $performanceIndicators) {
    Write-Host "Generating performance indicator: $($indicator.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Icon"
            AssetName = $indicator.Id
            Prompt = "$($indicator.Desc). Performance monitoring indicator for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $perfOutputDir
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
# 7. SIMULATION EVENT EFFECTS
# ============================================================
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host "  Generating Simulation Event Effects" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Yellow
Write-Host ""

$eventEffects = @(
    @{ Id = "event_entry_started"; Name = "Entry Started"; Desc = "Entry started particle effect, atmospheric entry, 64x64" },
    @{ Id = "event_entry_completed"; Name = "Entry Completed"; Desc = "Entry completed particle effect, entry complete, 64x64" },
    @{ Id = "event_burnout_started"; Name = "Burnout Started"; Desc = "Burnout started particle effect, atmospheric burnout, 64x64" },
    @{ Id = "event_burnout_ended"; Name = "Burnout Ended"; Desc = "Burnout ended particle effect, burnout complete, 64x64" },
    @{ Id = "event_layer_changed"; Name = "Layer Changed"; Desc = "Layer changed particle effect, atmospheric layer transition, 64x64" },
    @{ Id = "event_npc_spawned"; Name = "NPC Spawned"; Desc = "NPC spawned particle effect, NPC spawn, 64x64" },
    @{ Id = "event_npc_despawned"; Name = "NPC Despawned"; Desc = "NPC despawned particle effect, NPC despawn, 64x64" },
    @{ Id = "event_entity_collision"; Name = "Entity Collision"; Desc = "Entity collision particle effect, collision, 64x64" }
)

# Validate $ModPath before Join-Path
$eventOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($eventOutputDir)) {
    Write-Host "  [FAIL] eventOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($eventOutputDir)) {
    Write-Host "  [FAIL] eventOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $eventOutputDir)) {
    New-Item -ItemType Directory -Path $eventOutputDir -Force | Out-Null
}

foreach ($effect in $eventEffects) {
    Write-Host "Generating event effect: $($effect.Name)" -ForegroundColor Cyan
    
    try {
        $params = @{
            AssetType = "Particle"
            AssetName = $effect.Id
            Prompt = "$($effect.Desc). Simulation event effect for Starbound."
            OllamaModel = $OllamaModel
            OutputDir = $eventOutputDir
        }
        
        $params['UseCppBackend'] = $UseCppBackend
        
        & $assetGenerator @params | Out-Null
        
        $generated++
        Write-Host "  [OK] Generated: $($effect.Name)" -ForegroundColor Green
    } catch {
        $failed++
        Write-Host "  [FAIL] $($effect.Name) : $_" -ForegroundColor Red
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
Write-Host "  Phases: $(Join-Path $ModPath 'assets\simulation\phases')" -ForegroundColor Gray
Write-Host "  Modules: $(Join-Path $ModPath 'assets\simulation\modules')" -ForegroundColor Gray
Write-Host "  States: $(Join-Path $ModPath 'assets\simulation\states')" -ForegroundColor Gray
Write-Host "  Debug: $(Join-Path $ModPath 'assets\simulation\debug')" -ForegroundColor Gray
Write-Host "  UI Controls: $(Join-Path $ModPath 'assets\simulation\ui')" -ForegroundColor Gray
Write-Host "  Performance: $(Join-Path $ModPath 'assets\simulation\performance')" -ForegroundColor Gray
Write-Host "  Events: $(Join-Path $ModPath 'assets\simulation\events')" -ForegroundColor Gray
Write-Host ""

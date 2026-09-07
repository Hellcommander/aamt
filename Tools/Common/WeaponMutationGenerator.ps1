# Weapon Mutation Generator
# Orchestrates the complete pipeline for generating weapon mutations

param(
    [Parameter(Mandatory=$false)]
    [string]$RegistryPath = "weapon_mutation_example.json",
    
    [Parameter(Mandatory=$false)]
    [string]$MutationId = "",
    
    [Parameter(Mandatory=$false)]
    [string]$OutputDir = "TestOutput/WeaponMutations",
    
    [Parameter(Mandatory=$false)]
    [switch]$SkipValidation = $false,
    
    [Parameter(Mandatory=$false)]
    [switch]$SkipXML = $false,
    
    [Parameter(Mandatory=$false)]
    [switch]$SkipBalance = $false,
    
    [Parameter(Mandatory=$false)]
    [switch]$CombinedXML = $true
)

$ErrorActionPreference = "Stop"

# Load shared asset generation settings
$settingsPath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "..\\AssetGenerationSettings.ps1"
if (Test-Path $settingsPath) {
    . $settingsPath
}

# Configuration
$ToolsDir = $PSScriptRoot
$RegistryFile = Join-Path $ToolsDir $RegistryPath

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Weapon Mutation Generator" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Validate registry
if (-not $SkipValidation) {
    Write-Host "Validating registry..." -ForegroundColor Yellow
    $schemaPath = Join-Path $ToolsDir "weapon_mutation_registry_schema.json"
    if (Test-Path $schemaPath) {
        python (Join-Path $ToolsDir "validate_registry.py") --registry $RegistryFile --schema $schemaPath
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Registry validation failed!" -ForegroundColor Red
            exit 1
        }
        Write-Host "Registry validation passed!" -ForegroundColor Green
    } else {
        Write-Host "Schema not found, skipping validation" -ForegroundColor Yellow
    }
    Write-Host ""
}

# Create output directories
$xmlOutput = Join-Path $OutputDir "XML"
$balanceOutput = Join-Path $OutputDir "Balance"
$codeOutput = Join-Path $OutputDir "Code"
New-Item -ItemType Directory -Force -Path $xmlOutput | Out-Null
New-Item -ItemType Directory -Force -Path $balanceOutput | Out-Null
New-Item -ItemType Directory -Force -Path $codeOutput | Out-Null

# XML export
if (-not $SkipXML) {
    Write-Host "Exporting mutations to XML..." -ForegroundColor Yellow
    
    $exporterScript = Join-Path $ToolsDir "..\Transcendence\transcendence_weapon_mutation_exporter.py"
    $exporterArgs = @(
        "--registry", $RegistryFile,
        "--output-dir", (Resolve-Path $xmlOutput).Path
    )
    
    if ($MutationId) {
        $exporterArgs += "--mutation-id", $MutationId
    }
    
    if ($CombinedXML) {
        $exporterArgs += "--combined"
    }
    
    python $exporterScript $exporterArgs
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "XML export failed!" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "XML export complete!" -ForegroundColor Green
    Write-Host ""
    
    # Generate behavior code
    Write-Host "Generating behavior code..." -ForegroundColor Yellow
    $behaviorScript = Join-Path $ToolsDir "weapon_mutation_behavior_generator.py"
    $behaviorOutput = Join-Path $codeOutput "weapon_mutation_behaviors.xml"
    
    python $behaviorScript --registry $RegistryFile --output $behaviorOutput
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "WARNING: Behavior code generation failed (may not be critical)" -ForegroundColor Yellow
    } else {
        Write-Host "Behavior code generation complete!" -ForegroundColor Green
        Write-Host "  Location: $behaviorOutput" -ForegroundColor Cyan
    }
    Write-Host ""
} else {
    Write-Host "Skipping XML export (--SkipXML)" -ForegroundColor Yellow
    Write-Host ""
}

# Balance analysis
if (-not $SkipBalance) {
    Write-Host "Running balance analysis..." -ForegroundColor Yellow
    
    $balancerScript = Join-Path $ToolsDir "weapon_mutation_balancer.py"
    $balanceReportPath = Join-Path $balanceOutput "balance_report.txt"
    
    python $balancerScript $RegistryFile $balanceReportPath
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Balance analysis failed!" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "Balance analysis complete!" -ForegroundColor Green
    Write-Host "  Report: $balanceReportPath" -ForegroundColor Cyan
    Write-Host ""
} else {
    Write-Host "Skipping balance analysis (--SkipBalance)" -ForegroundColor Yellow
    Write-Host ""
}

# Summary
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Generation Summary" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Count mutations
$registryContent = Get-Content $RegistryFile | ConvertFrom-Json
$mutationCount = ($registryContent.mutations | Measure-Object).Count
$minorCount = ($registryContent.mutations | Where-Object { $_.tier -eq "minor" } | Measure-Object).Count
$majorCount = ($registryContent.mutations | Where-Object { $_.tier -eq "major" } | Measure-Object).Count
$corruptCount = ($registryContent.mutations | Where-Object { $_.tier -eq "corrupt" } | Measure-Object).Count

Write-Host "Mutations in registry: $mutationCount" -ForegroundColor White
Write-Host "  Minor: $minorCount" -ForegroundColor Gray
Write-Host "  Major: $majorCount" -ForegroundColor Gray
Write-Host "  Corrupt: $corruptCount" -ForegroundColor Gray
Write-Host ""

if (-not $SkipXML) {
    $xmlFiles = Get-ChildItem -Path $xmlOutput -Filter "*.xml" -ErrorAction SilentlyContinue
    Write-Host "XML files generated: $($xmlFiles.Count)" -ForegroundColor White
    Write-Host "  Location: $xmlOutput" -ForegroundColor Gray
    Write-Host ""
}

if (-not $SkipBalance) {
    if (Test-Path (Join-Path $balanceOutput "balance_report.txt")) {
        Write-Host "Balance report generated" -ForegroundColor White
        Write-Host "  Location: $balanceOutput" -ForegroundColor Gray
        Write-Host ""
    }
}

if (-not $SkipXML) {
    if (Test-Path (Join-Path $codeOutput "weapon_mutation_behaviors.xml")) {
        Write-Host "Behavior code generated" -ForegroundColor White
        Write-Host "  Location: $codeOutput" -ForegroundColor Gray
        Write-Host ""
    }
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Generation complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan


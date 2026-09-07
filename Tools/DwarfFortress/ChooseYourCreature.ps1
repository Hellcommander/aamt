# ChooseYourCreature.ps1
# AI-Assisted Modding Tools (AAMT) — Dwarf Fortress Creature + Civ orchestrator

[CmdletBinding()]
param(
    [ValidateSet("New", "Import", "Validate", "Analyze", "Generate", "Art", "Install", "Pack", "Editor", "Gui", "AdventureKit")]
    [string]$Action = "New",

    [string]$Id,
    [string]$Name,
    [ValidateSet(
        "humanoid_civ", "winged_humanoid", "hoofed_humanoid", "avian_folk", "centauroid",
        "quadruped_grasp", "insectoid", "tentacled", "hematophyte",
        "arachnid", "avian", "aquatic", "serpentine", "amorphous", "shelled_quadruped"
    )]
    [string]$Preset = "humanoid_civ",

    [string]$Spec,
    [string]$Culture = "dwarf_industry",
    [ValidateSet("harsh", "liquid", "guttural")]
    [string]$Phonology = "harsh",

    # Import
    [string]$Raw,
    [string]$ObjectId,
    [string]$Kind = "CREATURE",

    [switch]$Fix,
    [switch]$Police,
    [switch]$NoSD,
    [switch]$Force,
    [switch]$Blender,
    [switch]$AdventureKit,
    [int]$Workers = 0
)

$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$cli = Join-Path $here "df_civ_cli.py"
$editor = Join-Path $here "df_body_editor.py"

function Get-PythonExe {
    foreach ($c in @("python", "py")) {
        try { return (Get-Command $c -ErrorAction Stop).Source } catch {}
    }
    throw "Python not found on PATH."
}

function Invoke-DfCli([string[]]$CliArgs) {
    $py = Get-PythonExe
    Write-Host (">> {0} {1} {2}" -f $py, $cli, ($CliArgs -join " ")) -ForegroundColor DarkCyan
    & $py $cli @CliArgs
    if ($LASTEXITCODE -ne 0) {
        throw "df_civ_cli.py failed with exit code $LASTEXITCODE"
    }
}

function Resolve-SpecPath {
    if (-not [string]::IsNullOrWhiteSpace($Spec)) { return $Spec }
    if (-not [string]::IsNullOrWhiteSpace($Id)) {
        $outRoot = Join-Path (Split-Path $here -Parent) "Output\DwarfFortress\$($Id.ToUpper())\creature.json"
        return $outRoot
    }
    throw "Provide -Spec or -Id"
}

switch ($Action) {
    "New" {
        if ([string]::IsNullOrWhiteSpace($Id) -or [string]::IsNullOrWhiteSpace($Name)) {
            throw "New requires -Id and -Name"
        }
        $args = @("new", "--id", $Id, "--name", $Name, "--preset", $Preset, "--culture", $Culture, "--phonology", $Phonology)
        Invoke-DfCli $args
    }
    "Import" {
        if ([string]::IsNullOrWhiteSpace($Raw) -or [string]::IsNullOrWhiteSpace($ObjectId)) {
            throw "Import requires -Raw and -ObjectId"
        }
        $args = @("import", "--raw", $Raw, "--object-id", $ObjectId, "--kind", $Kind)
        if (-not [string]::IsNullOrWhiteSpace($Id)) { $args += @("--id", $Id) }
        if (-not [string]::IsNullOrWhiteSpace($Spec)) { $args += @("--output", $Spec) }
        Invoke-DfCli $args
    }
    "Validate" {
        $sp = Resolve-SpecPath
        $args = @("validate", "--spec", $sp)
        if ($Fix) { $args += "--fix" }
        if ($Police) { $args += "--police" }
        Invoke-DfCli $args
    }
    "Analyze" {
        $sp = Resolve-SpecPath
        $args = @("analyze", "--spec", $sp)
        if ($Fix) { $args += "--fix-layout" }
        if ($Police) { $args += "--police" }
        if ($Workers -gt 0) { $args += @("--workers", "$Workers") }
        Invoke-DfCli $args
    }
    "Generate" {
        $sp = Resolve-SpecPath
        $args = @("generate", "--spec", $sp)
        if ($Fix) { $args += "--fix" }
        if ($AdventureKit) { $args += "--adventure-kit" }
        Invoke-DfCli $args
    }
    "Art" {
        $sp = Resolve-SpecPath
        $args = @("art", "--spec", $sp)
        if ($NoSD) { $args += "--no-sd" }
        if ($Force) { $args += "--force" }
        if ($Blender) { $args += "--blender" }
        if ($Workers -gt 0) { $args += @("--workers", "$Workers") }
        Invoke-DfCli $args
    }
    "AdventureKit" {
        $sp = Resolve-SpecPath
        Invoke-DfCli @("adventure-kit", "--spec", $sp)
    }
    "Install" {
        $sp = Resolve-SpecPath
        Invoke-DfCli @("install", "--spec", $sp)
    }
    "Pack" {
        $sp = Resolve-SpecPath
        Invoke-DfCli @("pack", "--spec", $sp)
    }
    "Editor" {
        $sp = $null
        try { $sp = Resolve-SpecPath } catch {}
        $eargs = @("editor")
        if ($sp) { $eargs += @("--spec", $sp) }
        Invoke-DfCli $eargs
    }
    "Gui" {
        & (Join-Path $here "ChooseYourCreature-GUI.ps1")
    }
}

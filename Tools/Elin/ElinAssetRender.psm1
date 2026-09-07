<#
.SYNOPSIS
    Local-AI (SD) + procedural image render helper for Elin generators.

.DESCRIPTION
    Calls generate_asset_image.py (elin_sd auto/fallback) and writes Unity .meta
    via Shared/UnityAssetExport.psm1. Also wraps Shared/pbr_skin_generator.py.
#>

$script:ElinDir = $PSScriptRoot
$script:SharedDir = Join-Path (Split-Path $PSScriptRoot -Parent) "Shared"

Import-Module (Join-Path $script:SharedDir "UnityAssetExport.psm1") -Force -ErrorAction SilentlyContinue

function Write-ElinTempJson {
    param([Parameter(Mandatory)]$Object, [Parameter(Mandatory)][string]$Path)
    $json = $Object | ConvertTo-Json -Depth 10
    Write-ElinTempText -Path $Path -Content $json
}

function Write-ElinTempText {
    <#
    .SYNOPSIS
        Write UTF-8 without BOM (safe for Python / Unity tooling).
    #>
    param(
        [Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory)][string]$Content
    )
    if (Get-Command Write-AamtUtf8NoBom -ErrorAction SilentlyContinue) {
        Write-AamtUtf8NoBom -Path $Path -Content $Content
        return
    }
    $dir = Split-Path $Path -Parent
    if ($dir -and -not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
    $utf8NoBom = New-Object System.Text.UTF8Encoding $false
    [System.IO.File]::WriteAllText($Path, $Content, $utf8NoBom)
}

function Invoke-ElinPython {
    param([Parameter(Mandatory)][string]$PythonExe, [Parameter(Mandatory)][string[]]$Args)
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $output = & $PythonExe @Args 2>&1
        return @{ Code = $LASTEXITCODE; Output = $output }
    } finally {
        $ErrorActionPreference = $prevEap
    }
}

function Invoke-ElinAssetImage {
    <#
    .SYNOPSIS
        Generate one PNG from a hashtable/JSON-compatible spec via generate_asset_image.py.
    #>
    param(
        [Parameter(Mandatory)]$Spec,
        [Parameter(Mandatory)][string]$OutputPath,
        [ValidateSet("icon", "sprite", "texture", "spell_asset")]
        [string]$AssetType = "icon",
        [int]$Size = 256,
        [ValidateSet("auto", "on", "off")]
        [string]$Sd = "auto",
        [ValidateSet("", "default", "sprite", "gui", "normal")]
        [string]$MetaKind = "sprite"
    )

    $pyScript = Join-Path $script:ElinDir "generate_asset_image.py"
    if (-not (Test-Path $pyScript)) {
        Write-Warning "Invoke-ElinAssetImage: generate_asset_image.py missing"
        return $false
    }
    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if (-not $pythonCmd) { $pythonCmd = Get-Command python3 -ErrorAction SilentlyContinue }
    if (-not $pythonCmd) {
        Write-Warning "Invoke-ElinAssetImage: Python not in PATH"
        return $false
    }

    $outDir = Split-Path -Parent $OutputPath
    if ($outDir -and -not (Test-Path $outDir)) {
        New-Item -ItemType Directory -Path $outDir -Force | Out-Null
    }

    $tempSpec = Join-Path $env:TEMP ("elin_spec_" + [guid]::NewGuid().ToString("N") + ".json")
    try {
        if ($Spec -is [hashtable]) {
            if (-not $Spec.ContainsKey("size")) { $Spec["size"] = $Size }
            Write-ElinTempJson -Object $Spec -Path $tempSpec
        } else {
            $obj = $Spec | ConvertTo-Json -Depth 10 | ConvertFrom-Json
            if (-not $obj.size) { $obj | Add-Member -NotePropertyName size -NotePropertyValue $Size -Force }
            Write-ElinTempJson -Object $obj -Path $tempSpec
        }

        $run = Invoke-ElinPython -PythonExe $pythonCmd.Source -Args @(
            $pyScript, "--spec", $tempSpec, "--output", $OutputPath,
            "--type", $AssetType, "--size", "$Size", "--sd", $Sd
        )
        if ($run.Output) { $run.Output | ForEach-Object { Write-Host "    $_" -ForegroundColor Gray } }
        if ($run.Code -ne 0 -or -not (Test-Path $OutputPath)) { return $false }

        if ($MetaKind -and (Get-Command Write-AamtUnityTextureMeta -ErrorAction SilentlyContinue)) {
            [void](Write-AamtUnityTextureMeta -Path $OutputPath -Kind $MetaKind -Overwrite)
        }
        return $true
    } catch {
        Write-Warning "Invoke-ElinAssetImage failed: $_"
        return $false
    } finally {
        Remove-Item $tempSpec -Force -ErrorAction SilentlyContinue
    }
}

function Invoke-ElinPbrSkin {
    <#
    .SYNOPSIS
        Generate a PBR skin map set via Shared/pbr_skin_generator.py.
    #>
    param(
        [Parameter(Mandatory)][string]$OutputDir,
        [Parameter(Mandatory)][string]$Name,
        $Spec = @{},
        [ValidateSet("draft", "standard", "high", "ultra")]
        [string]$Quality = "standard",
        [int]$Size = 0,
        [switch]$NoSd,
        [switch]$Glow
    )
    $py = Get-Command python -ErrorAction SilentlyContinue
    if (-not $py) { $py = Get-Command python3 -ErrorAction SilentlyContinue }
    $script = Join-Path $script:SharedDir "pbr_skin_generator.py"
    if (-not $py -or -not (Test-Path $script)) {
        Write-Warning "Invoke-ElinPbrSkin: python or pbr_skin_generator.py missing"
        return $false
    }
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
    $tempSpec = Join-Path $env:TEMP ("elin_pbr_spec_" + [guid]::NewGuid().ToString("N") + ".json")
    try {
        Write-ElinTempJson -Object $Spec -Path $tempSpec
        $args = @($script, "--output-dir", $OutputDir, "--name", $Name, "--spec", $tempSpec, "--quality", $Quality)
        if ($Size -gt 0) { $args += @("--size", "$Size") }
        if ($NoSd) { $args += "--no-sd" }
        if ($Glow) { $args += "--glow" }
        $run = Invoke-ElinPython -PythonExe $py.Source -Args $args
        if ($run.Output) { $run.Output | ForEach-Object { Write-Host "    $_" -ForegroundColor Gray } }
        return (($run.Code -eq 0) -and (Test-Path (Join-Path $OutputDir "${Name}_diffuse.png")))
    } finally {
        Remove-Item $tempSpec -Force -ErrorAction SilentlyContinue
    }
}

Export-ModuleMember -Function Invoke-ElinAssetImage, Invoke-ElinPbrSkin, Write-ElinTempJson, Write-ElinTempText

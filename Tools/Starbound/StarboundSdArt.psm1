<#
.SYNOPSIS
    Stable Diffusion art for the Starbound generators (replaces System.Drawing placeholder art).

.DESCRIPTION
    Thin wrapper over Tools\Shared\sd_art.py. Starts the SD3.5 server (:1338) on demand,
    generates real art, downsizes it to the game cell size and writes a PNG.

    There is no procedural fallback: when SD cannot deliver, New-StarboundSdArt throws,
    unless the caller passes -AllowProcedural (or AAMT_SD_STRICT=0), in which case it
    returns $false and the caller may draw its old placeholder.

.EXAMPLE
    Import-Module .\StarboundSdArt.psm1
    New-StarboundSdArt -Kind sheet -Prompt "mossy cobblestone floor texture" `
        -OutputPath .\cobble.png -Width 8 -Height 8 -Count 5 -Columns 5 -Pixel
#>

function Resolve-StarboundSdPython {
    if ($env:AAMT_PYTHON -and (Test-Path -LiteralPath $env:AAMT_PYTHON)) { return $env:AAMT_PYTHON }
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    $cmd = Get-Command python3 -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    return $null
}

function Test-StarboundSdStrict {
    return ($env:AAMT_SD_STRICT -ne '0')
}

function New-StarboundSdArt {
    <#
    .SYNOPSIS
    Generates one sprite (-Kind sprite) or a grid of cells (-Kind sheet) with Stable Diffusion.
    Returns $true when the PNG was written. Throws when SD fails, unless procedural output
    is explicitly allowed, in which case it returns $false.
    #>
    [CmdletBinding()]
    param(
        [ValidateSet("sprite", "sheet")][string]$Kind = "sprite",
        [Parameter(Mandatory = $true)][string]$Prompt,
        [Parameter(Mandatory = $true)][string]$OutputPath,
        [Parameter(Mandatory = $true)][int]$Width,
        [Parameter(Mandatory = $true)][int]$Height,
        [int]$Count = 1,
        [int]$Columns = 0,
        [string[]]$Variants = @(),
        [string]$SdKind = "icon",
        [switch]$Transparent,
        [switch]$Pixel,
        [int]$Colors = 24,
        [int]$Seed = 0,
        [switch]$NoFit,        # sprites: do not crop to the subject and fill the cell
        [switch]$Consistent,   # sheets: keep one subject across cells (img2img from cell 1)
        [double]$Strength = 0.72,
        [switch]$AllowProcedural
    )

    $allow = $AllowProcedural.IsPresent -or -not (Test-StarboundSdStrict)
    $python = Resolve-StarboundSdPython
    $script = Join-Path (Split-Path -Parent $PSScriptRoot) "Shared\sd_art.py"
    $problem = $null
    if (-not $python) { $problem = "Python not found" }
    elseif (-not (Test-Path -LiteralPath $script)) { $problem = "missing helper: $script" }

    if (-not $problem) {
        $dir = Split-Path -Parent $OutputPath
        if ($dir -and -not (Test-Path -LiteralPath $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }

        $argList = @($script, $Kind, "--prompt", $Prompt, "--output", $OutputPath,
            "--width", "$Width", "--height", "$Height", "--kind", $SdKind, "--colors", "$Colors")
        if ($Transparent) { $argList += "--transparent" }
        if ($Pixel) { $argList += "--pixel" }
        # Single sprites: crop to the subject so small cells (16-48px) are not mostly empty.
        if ($Transparent -and $Kind -eq "sprite" -and -not $NoFit) { $argList += "--fit" }
        if ($Seed -gt 0) { $argList += @("--seed", "$Seed") }
        if ($Kind -eq "sheet") {
            $argList += @("--count", "$Count", "--columns", "$Columns")
            if ($Consistent) {
                $argList += @("--consistent", "--strength", ([string]$Strength))
            }
            if ($Variants.Count -gt 0) { $argList += @("--variants", ($Variants -join "|")) }
        }

        $output = & $python @argList 2>&1
        if ($LASTEXITCODE -eq 0 -and (Test-Path -LiteralPath $OutputPath)) { return $true }
        $problem = "SD art generation failed: " + (($output | Select-Object -Last 3) -join " ")
    }

    if ($allow) {
        Write-Host "  [WARN] $problem - procedural placeholder explicitly allowed" -ForegroundColor Yellow
        return $false
    }
    throw "$problem. Refusing procedural placeholder art (pass -AllowProcedural or set AAMT_SD_STRICT=0 to permit it)."
}

Export-ModuleMember -Function New-StarboundSdArt, Test-StarboundSdStrict

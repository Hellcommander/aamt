#Requires -Version 5.1
<#
.SYNOPSIS
  Unpack a granted Qud Lab private pack (simulator + SimHost + Unity LoadFrom host).
.DESCRIPTION
  Access-gated. A git clone of AAMT does not include this. Requires a legitimate
  Caves of Qud install; the pack must not contain game DLLs or assets.
#>
param(
    [Parameter(ParameterSetName = 'zip', Mandatory = $true)]
    [string]$Archive,

    [Parameter(ParameterSetName = 'dir', Mandatory = $true)]
    [string]$SourceDir,

    [string]$LabRoot = $PSScriptRoot
)

$ErrorActionPreference = 'Stop'
$sim = Join-Path $LabRoot 'src\QudLab.Simulator'
$hostDir = Join-Path $LabRoot 'src\QudLab.SimHost'
$unity = Join-Path $LabRoot 'UnityProject\Assets\QudLab\Scripts'

function Copy-IfPresent([string]$from, [string]$toFile) {
    if (Test-Path -LiteralPath $from) {
        $destDir = Split-Path $toFile -Parent
        New-Item -ItemType Directory -Force -Path $destDir | Out-Null
        Copy-Item -LiteralPath $from -Destination $toFile -Force
        Write-Host "  $(Split-Path $toFile -Leaf)"
    }
}

$extract = $SourceDir
$tmp = $null
if ($PSCmdlet.ParameterSetName -eq 'zip') {
    if (-not (Test-Path -LiteralPath $Archive)) {
        throw "Archive not found: $Archive"
    }
    $tmp = Join-Path $env:TEMP ("QudLabPrivate-" + [guid]::NewGuid().ToString('n'))
    New-Item -ItemType Directory -Path $tmp | Out-Null
    Expand-Archive -LiteralPath $Archive -DestinationPath $tmp -Force
    $extract = $tmp
    $nested = Get-ChildItem -LiteralPath $tmp -Directory | Select-Object -First 1
    if ($nested -and -not (Test-Path (Join-Path $extract 'RestrictedSimulator.cs'))) {
        if (Test-Path (Join-Path $nested.FullName 'RestrictedSimulator.cs')) {
            $extract = $nested.FullName
        } elseif (Test-Path (Join-Path $nested.FullName 'QudLab.Simulator')) {
            $extract = $nested.FullName
        }
    }
}

Write-Host "Installing Qud Lab private pack from $extract"

$simSrc = $extract
if (Test-Path (Join-Path $extract 'QudLab.Simulator')) {
    $simSrc = Join-Path $extract 'QudLab.Simulator'
} elseif (Test-Path (Join-Path $extract 'src\QudLab.Simulator')) {
    $simSrc = Join-Path $extract 'src\QudLab.Simulator'
}

Get-ChildItem -LiteralPath $simSrc -Filter '*.cs' -File -ErrorAction SilentlyContinue |
    Where-Object { $_.Directory.Name -ne 'PublicStubs' } |
    ForEach-Object { Copy-Item $_.FullName (Join-Path $sim $_.Name) -Force; Write-Host "  Simulator\$($_.Name)" }

$hostSrc = Join-Path $extract 'QudLab.SimHost'
if (-not (Test-Path $hostSrc)) { $hostSrc = Join-Path $extract 'src\QudLab.SimHost' }
Copy-IfPresent (Join-Path $hostSrc 'Program.cs') (Join-Path $hostDir 'Program.cs')
Copy-IfPresent (Join-Path $extract 'Program.cs') (Join-Path $hostDir 'Program.cs')

$unitySrc = Join-Path $extract 'Unity'
if (-not (Test-Path $unitySrc)) { $unitySrc = Join-Path $extract 'Scripts' }
foreach ($name in @('QudManagedHost.cs', 'QudRestrictedObjectSim.cs', 'QudZoneGetProbe.cs')) {
    Copy-IfPresent (Join-Path $unitySrc $name) (Join-Path $unity $name)
    Copy-IfPresent (Join-Path $extract $name) (Join-Path $unity $name)
}

if ($tmp) { Remove-Item -LiteralPath $tmp -Recurse -Force -ErrorAction SilentlyContinue }

if (-not (Test-Path (Join-Path $sim 'RestrictedSimulator.cs'))) {
    throw "Pack did not contain RestrictedSimulator.cs. Ask the maintainer for the Qud Lab private archive."
}

Write-Host "Private pack in place. Rebuild QudLab.sln. Game DLLs must stay in your Caves of Qud install."

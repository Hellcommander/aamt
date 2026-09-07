#Requires -Version 5.1
<#
.SYNOPSIS
  Install a granted Qud Lab private pack (compiled DLLs preferred).
.DESCRIPTION
  Access-gated. A git clone of AAMT does not include this. Requires a legitimate
  Caves of Qud install and the .NET 8 runtime. The pack must not contain game DLLs.

  Preferred layout (compiled, portable net8.0 IL — Windows/Linux/macOS):
    QudLab.Simulator.Private.dll
    QudLab.SimHost.Private.dll

  Legacy source zips (RestrictedSimulator.cs) still unpack for maintainer rebuilds.
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
$packDir = Join-Path $LabRoot 'pack\private'

function Copy-IfPresent([string]$from, [string]$toFile) {
    if (Test-Path -LiteralPath $from) {
        $destDir = Split-Path $toFile -Parent
        New-Item -ItemType Directory -Force -Path $destDir | Out-Null
        Copy-Item -LiteralPath $from -Destination $toFile -Force
        Write-Host "  $(Split-Path $toFile -Leaf) -> $toFile"
    }
}

function Find-File([string]$root, [string]$name) {
    $direct = Join-Path $root $name
    if (Test-Path -LiteralPath $direct) { return $direct }
    $hit = Get-ChildItem -LiteralPath $root -Filter $name -Recurse -File -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if ($hit) { return $hit.FullName }
    return $null
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
    if ($nested -and -not (Find-File $extract 'QudLab.Simulator.Private.dll') -and -not (Find-File $extract 'RestrictedSimulator.cs')) {
        $extract = $nested.FullName
    }
}

Write-Host "Installing Qud Lab private pack from $extract"
New-Item -ItemType Directory -Force -Path $packDir | Out-Null

$simDll = Find-File $extract 'QudLab.Simulator.Private.dll'
$hostDll = Find-File $extract 'QudLab.SimHost.Private.dll'
$installedDll = $false

if ($simDll) {
    Copy-Item $simDll (Join-Path $packDir 'QudLab.Simulator.Private.dll') -Force
    Write-Host "  pack\private\QudLab.Simulator.Private.dll"
    $installedDll = $true
}
if ($hostDll) {
    Copy-Item $hostDll (Join-Path $packDir 'QudLab.SimHost.Private.dll') -Force
    Write-Host "  pack\private\QudLab.SimHost.Private.dll"
}

$binRoots = @(
    (Join-Path $LabRoot 'artifacts\bin\QudLab.Cli\Release\net8.0'),
    (Join-Path $LabRoot 'artifacts\bin\QudLab.Cli\Debug\net8.0'),
    (Join-Path $LabRoot 'artifacts\bin\QudLab.SimHost\Release\net8.0'),
    (Join-Path $LabRoot 'artifacts\bin\QudLab.SimHost\Debug\net8.0'),
    (Join-Path $LabRoot 'artifacts\bin\QudLab.Assistant\Release\net8.0'),
    (Join-Path $LabRoot 'artifacts\bin\QudLab.Assistant\Debug\net8.0'),
    (Join-Path $LabRoot 'artifacts\bin\QudLab.Ai\Release\net8.0'),
    (Join-Path $LabRoot 'artifacts\bin\QudLab.Gui\Release\net8.0')
)
if ($installedDll) {
    foreach ($bin in $binRoots) {
        if (-not (Test-Path $bin)) { continue }
        Copy-IfPresent (Join-Path $packDir 'QudLab.Simulator.Private.dll') (Join-Path $bin 'QudLab.Simulator.Private.dll')
        Copy-IfPresent (Join-Path $packDir 'QudLab.SimHost.Private.dll') (Join-Path $bin 'QudLab.SimHost.Private.dll')
    }
}

$unitySrc = Join-Path $extract 'Unity'
if (-not (Test-Path $unitySrc)) { $unitySrc = Join-Path $extract 'Scripts' }
foreach ($name in @('QudManagedHost.cs', 'QudRestrictedObjectSim.cs', 'QudZoneGetProbe.cs')) {
    Copy-IfPresent (Join-Path $unitySrc $name) (Join-Path $unity $name)
    Copy-IfPresent (Join-Path $extract $name) (Join-Path $unity $name)
}

# Legacy source pack (maintainer rebuild)
$simSrc = $extract
if (Test-Path (Join-Path $extract 'QudLab.Simulator')) {
    $simSrc = Join-Path $extract 'QudLab.Simulator'
} elseif (Test-Path (Join-Path $extract 'src\QudLab.Simulator')) {
    $simSrc = Join-Path $extract 'src\QudLab.Simulator'
}

$copiedCs = $false
if (Test-Path $simSrc) {
    Get-ChildItem -LiteralPath $simSrc -Filter '*.cs' -File -ErrorAction SilentlyContinue |
        Where-Object { $_.Directory.Name -ne 'PublicStubs' } |
        ForEach-Object {
            Copy-Item $_.FullName (Join-Path $sim $_.Name) -Force
            Write-Host "  Simulator\$($_.Name) (source — rebuild Simulator.Private)"
            $copiedCs = $true
        }
}

$hostSrc = Join-Path $extract 'QudLab.SimHost'
if (-not (Test-Path $hostSrc)) { $hostSrc = Join-Path $extract 'src\QudLab.SimHost' }
Copy-IfPresent (Join-Path $hostSrc 'Program.cs') (Join-Path $hostDir 'Program.cs')
Copy-IfPresent (Join-Path $extract 'Program.cs') (Join-Path $hostDir 'Program.cs')

if ($tmp) { Remove-Item -LiteralPath $tmp -Recurse -Force -ErrorAction SilentlyContinue }

if (-not $installedDll -and -not (Test-Path (Join-Path $sim 'RestrictedSimulator.cs'))) {
    throw "Pack had neither QudLab.Simulator.Private.dll nor RestrictedSimulator.cs."
}

if ($copiedCs -and -not $installedDll) {
    Write-Host "Source pack installed. Build with .\Build-PrivatePack.ps1 then rebuild QudLab.sln."
} else {
    Write-Host "Compiled pack in place (portable net8.0). Rebuild QudLab.sln so CLI/SimHost pick up the DLLs."
    Write-Host "Game DLLs must stay in your Caves of Qud install. NO WARRANTY — use at your own risk."
}

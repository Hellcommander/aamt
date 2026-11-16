<#
.SYNOPSIS
  Packs the SealedAudio D2RLoader plugin and a mod's sealed archives into a zip that D2RMM (Custom) imports as a
  D2RLoader package.

.DESCRIPTION
  The zip holds
      d2rloader\plugins\sealedaudio.dll
      d2rloader\plugins\SealedAudio\*.mtsa
  and never a key file: archives sealed with a local key (Seal-LocalAudio.ps1) open only where that key is in the local
  key store (%LOCALAPPDATA%\SealedAudio\keys); *.key files beside the archives are skipped with a warning.
  D2RMM deploys files under d2rloader\plugins\ into the output mod's d2rloader\plugins\ unchanged, and the plugin looks
  for its archives in d2rloader\plugins\SealedAudio when d2rloader\SealedAudio is absent. Import the zip in D2RMM's
  D2RLoader plugin manager, then install the mods as usual.

.EXAMPLE
  .\New-D2rmmPackage.ps1 -Archives "D:\mods\MyMod\d2rloader\SealedAudio" -Out "D:\mods\sealedaudio-mymod.zip"
#>
param(
    # Folder with the *.mtsa archives (audio_seal.py seal output), or a single .mtsa file.
    [Parameter(Mandatory)] [string] $Archives,
    # Zip to write; its name (without .zip) becomes the package name in D2RMM.
    [Parameter(Mandatory)] [string] $Out,
    # The plugin to pack; defaults to the build.bat output.
    [string] $Dll = (Join-Path $PSScriptRoot '..\..\bin\d2rloader\sealedaudio.dll')
)
$ErrorActionPreference = 'Stop'

if (-not (Test-Path -LiteralPath $Dll -PathType Leaf)) { throw "Plugin not found: $Dll (run build.bat first)" }
if (-not (Test-Path -LiteralPath $Archives)) { throw "Archives not found: $Archives" }
$files = if (Test-Path -LiteralPath $Archives -PathType Leaf) { @(Get-Item -LiteralPath $Archives) }
         else { @(Get-ChildItem -LiteralPath $Archives -File | Where-Object { $_.Extension -eq '.mtsa' }) }
$keys = if (Test-Path -LiteralPath $Archives -PathType Container) { @(Get-ChildItem -LiteralPath $Archives -File -Filter '*.key') } else { @() }
foreach ($k in $keys) { Write-Warning "not packed (keys never ship): $($k.FullName)" }
if (-not ($files | Where-Object Extension -eq '.mtsa')) { throw "No .mtsa archives in $Archives" }

$stage = Join-Path ([IO.Path]::GetTempPath()) ("sa_d2rmm_" + [guid]::NewGuid().ToString('N'))
try {
    $plugins = Join-Path $stage 'd2rloader\plugins'
    New-Item -ItemType Directory -Path (Join-Path $plugins 'SealedAudio') -Force | Out-Null
    Copy-Item -LiteralPath $Dll -Destination (Join-Path $plugins 'sealedaudio.dll')
    foreach ($f in $files) { Copy-Item -LiteralPath $f.FullName -Destination (Join-Path $plugins 'SealedAudio') }

    $outFull = [IO.Path]::GetFullPath($Out)
    New-Item -ItemType Directory -Path (Split-Path $outFull) -Force | Out-Null
    if (Test-Path -LiteralPath $outFull) { Remove-Item -LiteralPath $outFull -Force }
    # Entries are added one by one: Windows PowerShell's ZipFile.CreateFromDirectory writes '\' separators, and the zip
    # format (and D2RMM's importer) expects '/'.
    Add-Type -AssemblyName System.IO.Compression, System.IO.Compression.FileSystem
    $zip = [IO.Compression.ZipFile]::Open($outFull, [IO.Compression.ZipArchiveMode]::Create)
    try {
        foreach ($f in Get-ChildItem -LiteralPath $stage -Recurse -File) {
            $entry = $f.FullName.Substring($stage.Length + 1).Replace('\', '/')
            [void][IO.Compression.ZipFileExtensions]::CreateEntryFromFile($zip, $f.FullName, $entry)
            "  $entry"
        }
    }
    finally { $zip.Dispose() }
    "Wrote $outFull"
}
finally {
    Remove-Item -LiteralPath $stage -Recurse -Force -ErrorAction SilentlyContinue
}

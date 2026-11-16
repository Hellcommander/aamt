<#
.SYNOPSIS
  Seals a Diablo II Resurrected mod's sounds against editing: every player's game plays them, nobody can change them.

.DESCRIPTION
  1. Seals every sound under -Include (paths relative to the mod's data folder) into -Archive as MTSA2: the audio is
     encrypted (AES-256-GCM) with the plugin's key, so the game decrypts it in memory on any machine and no sound file
     sits in the mod in the clear; the archive is signed with the signing key
     %LOCALAPPDATA%\SealedAudio\keys\<KeyName>.signkey (made on first use; audio_seal.py seal --sign), which never ships.
  2. Verifies the signature (audio_seal.py verify --signer).
  3. License gate (the reason this exists: licensed sounds may not ship as loose files): fails if any loose audio file
     (.wav .ogg .flac .mp3) is left in the mod folder, or any key file (*.key, *.signkey) sits in it or beside the archive.
     With -Map the sounds are sealed straight from the licensed library (D:\assets\audio), so they are never copied into
     the mod at all; library files are never deleted.
  4. With -Package, zips sealedaudio.dll and the archives for D2RMM (New-D2rmmPackage.ps1, which never packs keys) and
     checks the zip holds no key and no loose audio.

  The plugin (core 1.4+) checks the signature at game start: an archive changed by even one byte is refused and its
  sounds stay silent. With -Pin it writes SealedSigner.h and rebuilds the plugin so it accepts only archives signed by
  this key (a re-sealed copy signed by someone else is refused too). Back the signing key up privately: without it you
  cannot ship a new version a pinned plugin accepts.

.EXAMPLE
  .\Seal-LocalAudio.ps1 -Data "D:\mods\MyMod\MyMod.mpq\data" -Archive "D:\mods\MyMod\d2rloader\SealedAudio\mymod.mtsa" -Remove -Pin
.EXAMPLE
  .\Seal-LocalAudio.ps1 -Data "...\data" -Archive "...\d2rloader\SealedAudio\mymod.mtsa" -Package "D:\out\sealedaudio-mymod.zip"
.EXAMPLE
  # sounds.json: { "/hd/global/sfx/mymod/chain.wav": "D:/assets/audio/made/impact/anchor_chain.wav", ... }
  .\Seal-LocalAudio.ps1 -Data "...\data" -Archive "...\d2rloader\SealedAudio\mymod.mtsa" -Map sounds.json -Package "D:\out\mymod.zip"
#>
param(
    # The mod's data folder (the one holding hd\ and global\); archive paths are relative to it.
    [Parameter(Mandatory)] [string] $Data,
    # The archive to write, e.g. <mod>\d2rloader\SealedAudio\<mod>.mtsa.
    [Parameter(Mandatory)] [string] $Archive,
    # The signing key's name in the local store; defaults to the archive's name. Reuse a name to sign new versions.
    [string] $KeyName,
    # The build key the plugin carries (audio_seal.py --game NAME, made on first use, never shipped). Diablo II Resurrected has its own;
    # build.bat builds the plugin with the same name, so keep the two equal.
    [string] $GameKey = 'd2r',
    # Pin the plugin to this signing key: write src\SealedSigner.h and rebuild sealedaudio.dll (build.bat).
    [switch] $Pin,
    # Folders under -Data to seal.
    [string[]] $Include = @('hd\global\sfx', 'global\sfx'),
    # Instead of -Include: a JSON object {game path: source file} naming sounds in the licensed library.
    [string] $Map,
    # Delete the loose sounds once sealed (the copy you ship).
    [switch] $Remove,
    # Also write the D2RMM package zip here.
    [string] $Package,
    # The plugin to pack with -Package; defaults to the build.bat output.
    [string] $Dll,
    # The Python to run audio_seal.py with.
    [string] $Python = 'python'
)
$ErrorActionPreference = 'Stop'

$sealer = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..\..\Shared\audio_seal.py'))
if (-not (Test-Path -LiteralPath $sealer)) { throw "audio_seal.py not found: $sealer" }
if (-not (Test-Path -LiteralPath $Data -PathType Container)) { throw "Data folder not found: $Data" }
$Archive = [IO.Path]::GetFullPath($Archive)
if (-not $KeyName) { $KeyName = [IO.Path]::GetFileNameWithoutExtension($Archive) }

function Invoke-Sealer([string[]] $arguments) {
    & $Python $sealer @arguments
    if ($LASTEXITCODE -ne 0) { throw "audio_seal.py $($arguments[0]) failed (exit $LASTEXITCODE)" }
}

# 1. seal: encrypted with Diablo II Resurrected's own build key (the plugin carries it), signed with the local signing key
$sealArgs = @('seal', $Data, $Archive, '--game', $GameKey, '--sign', $KeyName)
if ($Map) { $sealArgs += @('--map', $Map) } else { $sealArgs += @('--include') + $Include }
if ($Remove) { $sealArgs += '--remove' }
Invoke-Sealer $sealArgs

# 2. the signature verifies, and it is this signing key's
Invoke-Sealer @('verify', $Archive, '--signer', $KeyName)

# optional: a plugin that accepts only this signer
if ($Pin) {
    $header = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..\src\SealedSigner.h'))
    Invoke-Sealer @('write-cpp-signer', $header, '--sign', $KeyName)
    & cmd /c "`"$(Join-Path $PSScriptRoot 'build.bat')`""
    if ($LASTEXITCODE -ne 0) { throw "build.bat failed (exit $LASTEXITCODE)" }
}

# 3. no key anywhere that ships: the mod folder (the parent of the .mpq, else the data folder) and beside the archive
$dataFull = [IO.Path]::GetFullPath($Data).TrimEnd('\')
$modRoot = $dataFull
$mpq = (Get-Item -LiteralPath $dataFull).Parent
if ($mpq -and $mpq.Name -like '*.mpq') { $modRoot = $mpq.Parent.FullName }
$scan = @($modRoot, (Split-Path $Archive)) | Select-Object -Unique
# (by extension: -Include does not filter together with -LiteralPath in Windows PowerShell 5)
$leaks = @($scan | ForEach-Object { Get-ChildItem -LiteralPath $_ -Recurse -File -ErrorAction SilentlyContinue } |
         Where-Object { $_.Extension -in '.key', '.signkey' }) | Sort-Object FullName -Unique
if ($leaks) {
    $leaks | ForEach-Object { Write-Warning "key file in what ships: $($_.FullName)" }
    throw "Remove these key files before shipping (a signed archive needs none of them)."
}
"No key files in $($scan -join ', ')"
$audio = @('.wav', '.ogg', '.flac', '.mp3')
$loose = @(Get-ChildItem -LiteralPath $modRoot -Recurse -File -ErrorAction SilentlyContinue | Where-Object { $_.Extension -in $audio })
if ($loose) {
    $loose | Select-Object -First 20 | ForEach-Object { Write-Warning "loose audio in the mod: $($_.FullName)" }
    throw "$($loose.Count) loose audio file(s) in $modRoot; licensed sounds may not ship loose. Seal them (-Remove) or take them out."
}
"No loose audio in $modRoot"

# 4. the D2RMM package, audited
if ($Package) {
    $pkgArgs = @{ Archives = (Split-Path $Archive); Out = $Package }
    if ($Dll) { $pkgArgs.Dll = $Dll }
    & (Join-Path $PSScriptRoot 'New-D2rmmPackage.ps1') @pkgArgs
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $zip = [IO.Compression.ZipFile]::OpenRead([IO.Path]::GetFullPath($Package))
    try {
        $bad = @($zip.Entries | Where-Object { $_.FullName -like '*.key' -or $_.FullName -like '*.signkey' } | ForEach-Object FullName)
        $badAudio = @($zip.Entries | Where-Object { [IO.Path]::GetExtension($_.FullName).ToLowerInvariant() -in $audio } | ForEach-Object FullName)
    }
    finally { $zip.Dispose() }
    if ($bad) { throw "The package holds key files: $($bad -join ', ')" }
    if ($badAudio) { throw "The package holds loose audio: $($badAudio -join ', ')" }
    "Package checked: no key files and no loose audio in $Package"
}

$keyFile = Join-Path $env:LOCALAPPDATA "SealedAudio\keys\$KeyName.signkey"
""
"The signing key stays here: $keyFile"
"Back it up privately. Players need nothing but the mod: the plugin decrypts the sounds in memory and refuses an edited archive."

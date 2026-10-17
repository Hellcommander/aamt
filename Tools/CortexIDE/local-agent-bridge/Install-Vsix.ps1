<#
.SYNOPSIS
  Install the built Local Agent Bridge VSIX into CortexIDE. Close CortexIDE first.

.DESCRIPTION
  1. Backs up any installed copy of this extension, and of its pre-rename id
     arend.cursor-agent-bridge, to <extensions dir>\..\extension-backups.
  2. Uninstalls arend.cursor-agent-bridge (same extension under its old name).
  3. Drops the old "cursor-bridge" entry from %USERPROFILE%\.cortexide\mcp.json.
     It points into the old extension folder. The extension writes its new
     "local-agent-bridge" entry on the next start.
  4. Runs cortexide.cmd --install-extension <vsix> --force and checks extensions.json.

.PARAMETER Vsix
  VSIX to install. Default: the newest local-agent-bridge-*.vsix next to this script.

.PARAMETER Build
  Run Build-Vsix.ps1 first.

.PARAMETER CortexIDE
  CortexIDE CLI. Default: D:\tools\CortexIDE\bin\cortexide.cmd

.PARAMETER ExtensionsDir
  Install into this extensions folder instead of CortexIDE's own
  (%USERPROFILE%\.cortexide\extensions). Lets you test the install while CortexIDE is open.
  mcp.json is left alone in this mode.

.EXAMPLE
  .\Install-Vsix.ps1 -Build
#>
[CmdletBinding()]
param(
    [string]$Vsix,
    [switch]$Build,
    [string]$CortexIDE = 'D:\tools\CortexIDE\bin\cortexide.cmd',
    [string]$ExtensionsDir
)

$ErrorActionPreference = 'Stop'

$id = 'arend.local-agent-bridge'
$legacyId = 'arend.cursor-agent-bridge'
$customDir = [bool]$ExtensionsDir
if (-not $customDir) { $ExtensionsDir = Join-Path $env:USERPROFILE '.cortexide\extensions' }
$cliArgs = @()
if ($customDir) { $cliArgs = @('--extensions-dir', $ExtensionsDir) }

if (-not (Test-Path -LiteralPath $CortexIDE)) { throw "CortexIDE CLI not found: $CortexIDE" }

if (-not $customDir) {
    $installRoot = Split-Path (Split-Path $CortexIDE)
    $running = Get-Process -Name CortexIDE -ErrorAction SilentlyContinue |
        Where-Object { $_.Path -and $_.Path.StartsWith($installRoot, [StringComparison]::OrdinalIgnoreCase) }
    if ($running) { throw 'CortexIDE is running. Close it, then run this script again.' }
}

if ($Build) {
    & (Join-Path $PSScriptRoot 'Build-Vsix.ps1')
}

if (-not $Vsix) {
    $Vsix = Get-ChildItem -LiteralPath $PSScriptRoot -Filter 'local-agent-bridge-*.vsix' |
        Sort-Object LastWriteTime -Descending | Select-Object -First 1 -ExpandProperty FullName
    if (-not $Vsix) { throw 'No local-agent-bridge-*.vsix here. Run .\Build-Vsix.ps1 or pass -Build.' }
}
$Vsix = (Resolve-Path -LiteralPath $Vsix).Path

# 1. Back up installed copies (old and new id) before anything replaces them.
if (Test-Path -LiteralPath $ExtensionsDir) {
    $backupRoot = Join-Path (Split-Path $ExtensionsDir) 'extension-backups'
    $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    foreach ($dir in Get-ChildItem -LiteralPath $ExtensionsDir -Directory |
            Where-Object { $_.Name -like "$id-*" -or $_.Name -like "$legacyId-*" }) {
        $version = 'unknown'
        $pkgFile = Join-Path $dir.FullName 'package.json'
        if (Test-Path -LiteralPath $pkgFile) { $version = (Get-Content -LiteralPath $pkgFile -Raw | ConvertFrom-Json).version }
        $name = ($dir.Name -replace '^arend\.', '') -replace '-\d+\.\d+\.\d+$', ''
        $dest = Join-Path $backupRoot "$name-$version-$stamp"
        New-Item -ItemType Directory -Force -Path $backupRoot | Out-Null
        Copy-Item -LiteralPath $dir.FullName -Destination $dest -Recurse
        Write-Host "Backed up $($dir.Name) -> $dest"
    }
}

# 2. Remove the pre-rename extension.
$installed = & $CortexIDE @cliArgs --list-extensions
if ($installed -contains $legacyId) {
    & $CortexIDE @cliArgs --uninstall-extension $legacyId
    if ($LASTEXITCODE) { throw "Uninstalling $legacyId failed (exit $LASTEXITCODE)." }
}

# 3. Drop the stale MCP entry (node keeps the file's JSON layout the way the extension writes it).
if (-not $customDir) {
    $mcp = Join-Path $env:USERPROFILE '.cortexide\mcp.json'
    if (Test-Path -LiteralPath $mcp) {
        # Single quotes only: Windows PowerShell 5.1 mangles double quotes in native arguments.
        $js = "const fs = require('fs'); const f = process.argv[1]; const j = JSON.parse(fs.readFileSync(f, 'utf8'));" +
              " const old = j.mcpServers && j.mcpServers['cursor-bridge'];" +
              " if (old && /cursor-agent-bridge/i.test(JSON.stringify(old.args || []))) {" +
              " delete j.mcpServers['cursor-bridge']; fs.writeFileSync(f, JSON.stringify(j, null, 2), 'utf8');" +
              " console.log('Removed cursor-bridge from ' + f); }"
        node -e $js $mcp
        if ($LASTEXITCODE) { throw "Updating $mcp failed." }
    }
}

# 4. Install and confirm.
& $CortexIDE @cliArgs --install-extension $Vsix --force
if ($LASTEXITCODE) { throw "Install failed (exit $LASTEXITCODE)." }

$registry = Join-Path $ExtensionsDir 'extensions.json'
$list = Get-Content -LiteralPath $registry -Raw | ConvertFrom-Json
$entry = @($list) | Where-Object { $_.identifier.id -eq $id }
if (-not $entry) { throw "$id is missing from $registry after install." }
Write-Host "Installed $id $($entry.version) at $(Join-Path $ExtensionsDir $entry.relativeLocation)"
if (-not $customDir) { Write-Host 'Start CortexIDE (or reload the window) to load it.' }

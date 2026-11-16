#Requires -Version 5.1
<#
.SYNOPSIS
  Clone third-party sources that AAMT must not vendor (license isolation).
.DESCRIPTION
  Does not fetch the Qud Lab private simulator pack.
#>
param(
    [switch]$All,
    [switch]$TES5Edit,
    [switch]$FrankyCLI,
    [switch]$Arzedit,
    [switch]$RenoDx,
    [switch]$BitKnit,
    [switch]$AgentBridge,
    # With -AgentBridge: also build the REA clone (npm ci + build, prebuilt Windows addon copied in),
    # link it as the global `rea` command, and put 7-Zip on the user PATH.
    [switch]$BuildRea,
    [string]$ToolsRoot = $PSScriptRoot
)

$ErrorActionPreference = 'Stop'
if (-not ($TES5Edit -or $FrankyCLI -or $Arzedit -or $RenoDx -or $BitKnit -or $AgentBridge -or $All)) {
    $All = $true
}
if ($All) {
    $TES5Edit = $true
    $FrankyCLI = $true
    $Arzedit = $true
}

function Invoke-GitClone([string]$Url, [string]$Dest, [string]$Branch = '') {
    if (Test-Path (Join-Path $Dest '.git')) {
        Write-Host "Already cloned: $Dest"
        git -C $Dest pull --ff-only
        return
    }
    if ((Test-Path $Dest) -and (Get-ChildItem $Dest -Force | Where-Object { $_.Name -ne 'README.md' })) {
        Write-Host "Skip clone (folder not empty): $Dest"
        return
    }
    New-Item -ItemType Directory -Force -Path (Split-Path $Dest) | Out-Null
    if ($Branch) {
        git clone --depth 1 --branch $Branch --single-branch $Url $Dest
    } else {
        git clone --depth 1 $Url $Dest
    }
}

Write-Host "AAMT third-party fetch (gitignored; licenses stay upstream). Qud Lab sim is NOT included."

if ($TES5Edit) {
    Write-Host "`n[TES5Edit MPL-2.0]"
    $sync = Join-Path $ToolsRoot 'XEdit\Sync-TES5Edit.ps1'
    if (-not (Test-Path $sync)) { throw "Missing $sync" }
    & $sync
    Write-Host "Place xEdit64.exe / SF1Edit64.exe (4.1.5q+) in Tools\XEdit\bin yourself."
}

if ($FrankyCLI) {
    Write-Host "`n[FrankyCLI MIT - Bryn Stringer]"
    Invoke-GitClone 'https://github.com/kaosnyrb/FrankyCLI.git' (Join-Path $ToolsRoot 'FrankyCLI')
}

if ($Arzedit) {
    Write-Host "`n[arzedit - QuasiMod]"
    Invoke-GitClone 'https://gitlab.com/QuasiMod/arzedit.git' (Join-Path $ToolsRoot 'GrimDawn\arzedit\arzedit-master')
}

if ($RenoDx) {
    Write-Host "`n[RenoDX MIT - plus nested third-party]"
    Invoke-GitClone 'https://github.com/clshortfuse/renodx.git' (Join-Path $ToolsRoot 'GrimDawn\renodx-src')
}

if ($BitKnit) {
    Write-Host "`n[ooz (no licence file upstream; not MIT) - reference source of the BitKnit decoder (bitknit.cpp)]"
    Invoke-GitClone 'https://github.com/powzix/ooz.git' (Join-Path $ToolsRoot 'DiabloII\thirdparty\ooz')
    Write-Host "Reference only. The Diablo II tools load a Python port, bitknit.py with decompress(data, size),"
    Write-Host "from %LOCALAPPDATA%\D2RModAssets\thirdparty or the folder named by D2R_BITKNIT. Keep both out of the repo."
}

if ($AgentBridge) {
    # Optional libraries the CortexIDE Local Agent Bridge loads at run time from
    # Tools\Shared\third_party (or localAgentBridge.agent.thirdPartyDir). Never bundled into the VSIX.
    $tp = Join-Path $ToolsRoot 'Shared\third_party'
    New-Item -ItemType Directory -Force -Path $tp | Out-Null
    Write-Host "`n[REA - Reverse Engineer Anything, MIT (morluto) - MCP server]"
    Invoke-GitClone 'https://github.com/morluto/rea.git' (Join-Path $tp 'Reverse-Engineer-anything')
    Write-Host "`n[rea-agents (prebuilt npm package, MIT) + pdfjs-dist (Apache-2.0, Mozilla)]"
    $npmDir = Join-Path $tp 'node'
    New-Item -ItemType Directory -Force -Path $npmDir | Out-Null
    $pkg = Join-Path $npmDir 'package.json'
    if (-not (Test-Path $pkg)) { '{ "name": "aamt-agent-bridge-third-party", "private": true }' | Set-Content -Encoding UTF8 $pkg }
    $old = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
    npm install --prefix $npmDir --no-audit --no-fund --save-exact rea-agents@6.0.0 pdfjs-dist@5 2>&1 | Write-Host
    $code = $LASTEXITCODE; $ErrorActionPreference = $old
    if ($code) { throw "npm install failed (exit $code)" }

    if ($BuildRea) {
        Write-Host "`n[Build REA from the clone; the bridge prefers a built clone over the npm package]"
        $rea = Join-Path $tp 'Reverse-Engineer-anything'
        $old = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
        Push-Location $rea
        try {
            npm ci --no-audit --no-fund 2>&1 | Write-Host
            if ($LASTEXITCODE) { throw "REA npm ci failed (exit $LASTEXITCODE)" }
            npm run build 2>&1 | Write-Host
            if ($LASTEXITCODE) { throw "REA build failed (exit $LASTEXITCODE)" }
            # The Windows addon only builds on Linux/MinGW; reuse the one from the same-version npm package.
            $pre = Join-Path $npmDir 'node_modules\rea-agents\native\windows\build'
            if (Test-Path $pre) {
                New-Item -ItemType Directory -Force -Path 'native\windows\build' | Out-Null
                Copy-Item (Join-Path $pre '*') 'native\windows\build' -Force
                node scripts/verify-windows-native-artifact.mjs 2>&1 | Write-Host
            }
            npm link --no-audit --no-fund --ignore-scripts 2>&1 | Write-Host
        } finally { Pop-Location; $ErrorActionPreference = $old }
        $sz = Join-Path $env:ProgramFiles '7-Zip'
        $userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
        if ((Test-Path (Join-Path $sz '7z.exe')) -and (($userPath -split ';') -notcontains $sz)) {
            [Environment]::SetEnvironmentVariable('Path', ($userPath.TrimEnd(';') + ';' + $sz), 'User')
            Write-Host "Added to user PATH: $sz"
        }
        Write-Host "Ghidra for REA: set GHIDRA_INSTALL_DIR and JAVA_HOME (JDK 21+) as user variables, then run: rea doctor --provider ghidra"
    }
}

Write-Host @"

Done. Not fetched (on purpose):
  - Caves of Qud / other game installs
  - Qud Lab private simulator (Fetch-PrivatePack.ps1 after access is granted)
  - Pixelorama (install to D:\tools\Orama Interactive\Pixelorama)
  - TranscendenceDev (Prepare-X64Workspace.py --api-root <official tree>)
  - Ollama / SD weights / Hugging Face caches

See ../LICENSING.md and ../THIRD_PARTY.md
"@

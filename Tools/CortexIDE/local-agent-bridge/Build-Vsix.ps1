<#
.SYNOPSIS
  Package Local Agent Bridge as local-agent-bridge-<version>.vsix in this folder.

.DESCRIPTION
  media\react.production.min.js and media\react-dom.production.min.js are React 18.3.1
  (MIT, Meta). They are third-party, so they stay out of git (see THIRD_PARTY.md).
  This script downloads them from unpkg when missing and refuses any copy whose SHA-256
  differs from the pinned build. It then runs the tests and
  `npx @vscode/vsce package --no-dependencies`.

.PARAMETER SkipTests
  Package without running `node test/run.js` first.

.EXAMPLE
  .\Build-Vsix.ps1
#>
[CmdletBinding()]
param([switch]$SkipTests)

$ErrorActionPreference = 'Stop'

$react = @(
    @{ File = 'react.production.min.js'
       Url = 'https://unpkg.com/react@18.3.1/umd/react.production.min.js'
       Sha256 = 'D949F1C3687AEDADCEDAC85261865F29B17CD273997E7F6B2BFC53B2F9D4C4DD' },
    @{ File = 'react-dom.production.min.js'
       Url = 'https://unpkg.com/react-dom@18.3.1/umd/react-dom.production.min.js'
       Sha256 = '35F4F974F4B2BCD44DA73963347F8952E341F83909E4498227D4E26B98F66F0D' }
)

Push-Location -LiteralPath $PSScriptRoot
try {
    foreach ($r in $react) {
        $path = Join-Path $PSScriptRoot "media\$($r.File)"
        $fetched = $false
        if (-not (Test-Path -LiteralPath $path)) {
            Write-Host "Fetching $($r.Url)"
            Invoke-WebRequest -Uri $r.Url -OutFile $path -UseBasicParsing
            $fetched = $true
        }
        $hash = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash
        if ($hash -ne $r.Sha256) {
            if ($fetched) { Remove-Item -LiteralPath $path }
            throw "$($r.File): SHA-256 $hash does not match the pinned React 18.3.1 build. Delete it and rerun."
        }
    }

    if (-not $SkipTests) {
        node test/run.js
        if ($LASTEXITCODE) { throw "Tests failed (exit $LASTEXITCODE). Fix them or pass -SkipTests." }
    }

    npx --yes @vscode/vsce package --no-dependencies --allow-missing-repository
    if ($LASTEXITCODE) { throw "vsce package failed (exit $LASTEXITCODE)." }

    $pkg = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'package.json') -Raw | ConvertFrom-Json
    $vsix = Join-Path $PSScriptRoot "$($pkg.name)-$($pkg.version).vsix"
    if (-not (Test-Path -LiteralPath $vsix)) { throw "Expected $vsix after packaging." }
    Write-Host "Built $vsix"
}
finally {
    Pop-Location
}

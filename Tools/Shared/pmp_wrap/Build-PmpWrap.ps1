<#
.SYNOPSIS
Builds pmpwrap.dll: pmp-library (C++, MIT) behind a plain C interface for Tools\Shared\pmp_lib.py.

.DESCRIPTION
pmp-library is not part of this repository. Clone it first:

    git clone https://github.com/pmp-library/pmp-library Tools\Shared\third_party\pmp-library

The build tree and the DLL go to Tools\Shared\third_party\pmp-build (ignored by git, like the
clone). Needs CMake 3.20+ and the MSVC C++ build tools (checked with CMake 4.5.0 and Build
Tools 18, pmp-library 3.0.0-310-gfc0bfd7a).

.EXAMPLE
.\Build-PmpWrap.ps1
.\Build-PmpWrap.ps1 -PmpRoot D:\src\pmp-library -Clean
#>
param(
    [string]$PmpRoot = (Join-Path $PSScriptRoot '..\third_party\pmp-library'),
    [string]$BuildDir = (Join-Path $PSScriptRoot '..\third_party\pmp-build'),
    [switch]$Clean
)
$ErrorActionPreference = 'Stop'
if (-not (Test-Path (Join-Path $PmpRoot 'src\pmp\surface_mesh.h'))) {
    throw "pmp-library not found in $PmpRoot. Clone https://github.com/pmp-library/pmp-library there."
}
$cmake = (Get-Command cmake -ErrorAction SilentlyContinue)?.Source
if (-not $cmake) { $cmake = 'D:\tools\CMake\bin\cmake.exe' }
if (-not (Test-Path $cmake)) { throw 'cmake not found (put it on PATH)' }
if ($Clean -and (Test-Path $BuildDir)) { Remove-Item -Recurse -Force $BuildDir -Confirm:$false }
& $cmake -S $PSScriptRoot -B $BuildDir -A x64 "-DPMP_ROOT=$((Resolve-Path $PmpRoot).Path)"
if ($LASTEXITCODE) { throw 'cmake configure failed' }
& $cmake --build $BuildDir --config Release --target pmpwrap --parallel
if ($LASTEXITCODE) { throw 'build failed' }
$dll = Get-ChildItem -Path $BuildDir -Recurse -Filter pmpwrap.dll | Sort-Object LastWriteTime | Select-Object -Last 1
if (-not $dll) { throw 'pmpwrap.dll was not produced' }
$target = Join-Path $BuildDir 'pmpwrap.dll'
if ($dll.FullName -ne $target) { Copy-Item $dll.FullName $target -Force }
Write-Host "built $target"

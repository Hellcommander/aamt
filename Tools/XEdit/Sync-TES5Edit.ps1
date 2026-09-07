#Requires -Version 5.1
$ErrorActionPreference = 'Stop'
$repo = Join-Path $PSScriptRoot 'vendor\TES5Edit'
$branch = 'dev-4.1.6'
$remote = 'https://github.com/TES5Edit/TES5Edit.git'

if (-not (Test-Path (Join-Path $repo '.git'))) {
    New-Item -ItemType Directory -Path (Split-Path $repo) -Force | Out-Null
    git clone --depth 1 --filter=blob:none --sparse --branch $branch --single-branch $remote $repo
    git -C $repo sparse-checkout set Core
} else {
    git -C $repo fetch origin $branch
    git -C $repo checkout $branch
    git -C $repo pull --ff-only origin $branch
}

git -C $repo log -1 --format='%H%n%s%n%ci'
if (-not (Test-Path (Join-Path $repo 'Core\wbDefinitionsSF1.pas'))) {
    throw 'wbDefinitionsSF1.pas missing after sync'
}
Write-Host "Starfield definitions ready: $repo\Core\wbDefinitionsSF1.pas"

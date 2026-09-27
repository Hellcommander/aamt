<#
.SYNOPSIS
  Shelve current QudLab chat-index/task, optionally swap to high-context vLLM.
  Next proxy/Agent turn injects SHELVED CONTEXT automatically.

.EXAMPLE
  .\Escalate-VllmContext.ps1
  .\Escalate-VllmContext.ps1 -Task "fix Broodmother CS0618"
  .\Escalate-VllmContext.ps1 -ShelveOnly
#>
[CmdletBinding()]
param(
    [string]$Task = '',
    [string]$ToModel = $(if ($env:QUDLAB_HIGH_CTX_MODEL) { $env:QUDLAB_HIGH_CTX_MODEL } else { 'Qwen/Qwen2.5-Coder-7B-Instruct-AWQ' }),
    [switch]$NoSwap,
    [switch]$ShelveOnly,
    [switch]$NoFrontend
)

$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$cli = Join-Path $here 'escalate_cli.py'

$pyCands = @(
    'E:\tools\miniconda3\python.exe',
    "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe",
    "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe"
)
$py = $null
foreach ($c in $pyCands) {
    if (Test-Path -LiteralPath $c) { $py = $c; break }
}
if (-not $py) {
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if ($cmd) { $py = $cmd.Source }
}
if (-not $py) { throw 'Python not found' }

$action = if ($ShelveOnly -or $NoSwap) { 'shelve' } else { 'escalate' }
$argList = @($cli, $action, '--to-model', $ToModel)
if ($Task) { $argList += @('--task', $Task) }
if ($NoFrontend) { $argList += '--no-frontend' }

Write-Host "Escalate context: $action -> $ToModel" -ForegroundColor Cyan
& $py @argList
exit $LASTEXITCODE

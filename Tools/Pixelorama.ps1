# AAMT Pixelorama host. Forwards to Shared/pixelorama_client.py
#   .\Pixelorama.ps1 status
#   .\Pixelorama.ps1 open .\sprite.pxo
#   .\Pixelorama.ps1 see --out .\shot.png
#   .\Pixelorama.ps1 export .\sprite.pxo --out .\out.png

param(
    [Parameter(Position = 0, ValueFromRemainingArguments = $true)]
    [string[]]$ArgsRest
)

$ErrorActionPreference = 'Stop'
$toolsRoot = $PSScriptRoot
. (Join-Path $toolsRoot 'Shared\ToolPaths.ps1')

$py = Get-AamtSDPython
$client = Join-Path $toolsRoot 'Shared\pixelorama_client.py'
if (-not (Test-Path -LiteralPath $client)) {
    Write-Error "Missing $client"
    exit 2
}

$cmd = @($py, $client)
if ($ArgsRest -and $ArgsRest.Count -gt 0) {
    $cmd += $ArgsRest
} else {
    $cmd += 'status'
}

& $cmd[0] $cmd[1..($cmd.Length - 1)]
exit $LASTEXITCODE

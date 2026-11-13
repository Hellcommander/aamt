<#
.SYNOPSIS
    Sends more script lines to a game started with Invoke-D2RBotTest.ps1 -NoWait and prints what the BotHarness plugin logged for them.
.DESCRIPTION
    Appends the lines to script.txt in the run folder, waits until the plugin has carried them out, and prints the new
    part of result.log. Without -Run it uses the newest run folder.
.EXAMPLE
    .\Send-D2RBotCommand.ps1 -Root 'D:\games\Diablo II Resurrected' 'console god 1', 'screenshot town'
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory, Position = 0)][string[]]$Lines,
    [string]$Root = $env:D2R_PATH,
    [string]$Run,
    [int]$TimeoutSec = 120
)
$ErrorActionPreference = 'Stop'
if (-not $Run) {
    if (-not $Root) { throw 'Pass -Run <run folder>, or -Root (or set D2R_PATH) to use the newest run.' }
    $Run = (Get-ChildItem (Join-Path $Root 'd2rloader\botharness\runs') -Directory | Sort-Object Name | Select-Object -Last 1).FullName
}
$script = Join-Path $Run 'script.txt'
$log = Join-Path $Run 'result.log'
if (-not (Test-Path $script)) { throw "No script.txt in $Run" }

function Read-Log {
    # The plugin keeps result.log open for writing, so read it with sharing allowed.
    if (-not (Test-Path $log)) { return '' }
    $stream = [IO.File]::Open($log, 'Open', 'Read', 'ReadWrite, Delete')
    try { (New-Object IO.StreamReader $stream).ReadToEnd() } finally { $stream.Dispose() }
}

$before = (Read-Log).Length
$marker = 'sent-' + [Guid]::NewGuid().ToString('N').Substring(0, 8)
$isExit = $Lines | Where-Object { $_ -match '^\s*(exit|quit)\b' }
$all = if ($isExit) { $Lines } else { @($Lines) + "log $marker" }
[IO.File]::AppendAllText($script, (($all -join "`n") + "`n"), (New-Object Text.UTF8Encoding $false))

$deadline = (Get-Date).AddSeconds($TimeoutSec)
$done = $false
while (-not $done -and (Get-Date) -lt $deadline) {
    Start-Sleep -Milliseconds 250
    $text = Read-Log
    $done = if ($isExit) { $text -match '\] RESULT ' } else { $text.Contains("NOTE   $marker") }
    if (-not $done -and -not (Get-Process -Name 'D2RLoader', 'D2R' -ErrorAction SilentlyContinue)) { break }
}
$text = Read-Log
$new = if ($text.Length -gt $before) { $text.Substring($before) } else { '' }
$new -split "`r?`n" | Where-Object { $_ -and $_ -notmatch "$marker" } | ForEach-Object { $_ }
if (-not $done) {
    if (Get-Process -Name 'D2RLoader', 'D2R' -ErrorAction SilentlyContinue) { "NOT FINISHED after $TimeoutSec s (the game is still running)."; exit 2 }
    'THE GAME IS NO LONGER RUNNING.'; exit 3
}
exit 0

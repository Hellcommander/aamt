<#
.SYNOPSIS
    Starts Diablo II: Resurrected with the BotHarness plugin armed, runs a test script in the game, and reports the result (see README.md).
.DESCRIPTION
    Makes a run folder under <Root>\d2rloader\botharness\runs, puts the script there as script.txt, and starts
    D2RLoader with BOTHARNESS_DIR pointing at it. The plugin writes result.log and screenshots to the same folder.
    Exit code: 0 = RESULT PASS, 1 = RESULT FAIL, 2 = no result (crash, timeout, plugin not loaded).
.EXAMPLE
    .\Invoke-D2RBotTest.ps1 -Root 'D:\games\Diablo II Resurrected' -Script .\BotScripts\smoke-menu.txt
.EXAMPLE
    # Step by step: start the game, then add lines to script.txt in the printed folder and read result.log.
    .\Invoke-D2RBotTest.ps1 -Root 'D:\games\Diablo II Resurrected' -Commands 'waitfor menu','screenshot menu' -NoWait
#>
[CmdletBinding()]
param(
    [string]$Root = $env:D2R_PATH,
    [string]$Script,
    [string[]]$Commands,
    [string]$Character,
    [string]$Mod = 'D2RMM',
    [string]$GameArgs = '-txt',
    [int]$TimeoutSec = 300,
    [switch]$NoWait
)
$ErrorActionPreference = 'Stop'
if (-not $Root -or -not (Test-Path (Join-Path $Root 'D2RLoader.exe'))) { throw 'Pass -Root (or set D2R_PATH) to the folder that contains D2RLoader.exe.' }
if (-not $Script -and -not $Commands) { throw 'Pass -Script <file> or -Commands <lines>.' }
if ($Script -and -not (Test-Path $Script)) { throw "Script not found: $Script" }
if (Get-Process -Name 'D2RLoader', 'D2R' -ErrorAction SilentlyContinue) { throw 'The game is already running. Close it first.' }

$dll = @((Join-Path $Root "mods\$Mod\d2rloader\plugins"), (Join-Path $Root 'd2rloader\plugins')) |
    Where-Object { Test-Path $_ } |
    ForEach-Object { Get-ChildItem $_ -Filter '*botharness*.dll' } |
    Select-Object -First 1
if (-not $dll) { throw "botharness.dll is not installed for mod '$Mod'. In D2RMM: Plugins > Refresh, enable BotHarness, Install mods." }

if ($Character) {
    # The main menu lists characters by last played and selects the first, which is the one "ui MainMenuHD:Play"
    # enters. The script cannot see a character's name, so check here that the wanted one was played last.
    $saves = Join-Path ([Environment]::GetFolderPath('UserProfile')) 'Saved Games\Diablo II Resurrected'
    $newest = Get-ChildItem $saves -Recurse -Filter '*.d2s' -ErrorAction SilentlyContinue | Sort-Object LastWriteTime | Select-Object -Last 1
    if (-not $newest -or $newest.BaseName -ne $Character) {
        throw "The character played last is '$($newest.BaseName)', not '$Character'. Enter a game with '$Character' once (and leave), so the menu selects it."
    }
}

$run = Join-Path $Root ('d2rloader\botharness\runs\' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
New-Item -ItemType Directory -Force $run | Out-Null
$lines = if ($Script) { Get-Content $Script } else { $Commands }
# No byte order mark, and a line feed after the last line: the plugin runs complete lines only.
[IO.File]::WriteAllText((Join-Path $run 'script.txt'), (($lines -join "`n") + "`n"), (New-Object Text.UTF8Encoding $false))

$started = Get-Date
$env:BOTHARNESS_DIR = $run
try {
    $arguments = (@('-mod', $Mod, $GameArgs) | Where-Object { $_ }) -join ' '
    $process = Start-Process -FilePath (Join-Path $Root 'D2RLoader.exe') -ArgumentList $arguments -WorkingDirectory $Root -PassThru
} finally {
    Remove-Item Env:BOTHARNESS_DIR
}
Write-Host "Run folder: $run"
if ($NoWait) {
    Write-Host 'Started. Add lines to script.txt (end with "exit"); read result.log and shots\ in the run folder.'
    exit 0
}

$log = Join-Path $run 'result.log'
$deadline = $started.AddSeconds($TimeoutSec)
$timedOut = $false
while (Get-Process -Name 'D2RLoader', 'D2R' -ErrorAction SilentlyContinue) {
    if ((Get-Date) -gt $deadline) {
        $timedOut = $true
        Get-Process -Name 'D2RLoader', 'D2R' -ErrorAction SilentlyContinue | Stop-Process -Force
        break
    }
    Start-Sleep -Milliseconds 500
}

if (Test-Path $log) { Get-Content $log | Write-Host } else { Write-Host 'No result.log: the plugin did not load (see d2rloader\logs).' }
if ($timedOut) { Write-Host "TIMEOUT: the game was still running after $TimeoutSec s and was stopped." }
$crashes = Join-Path $Root 'd2rloader\crashes'
if (Test-Path $crashes) {
    Get-ChildItem $crashes -Recurse -File | Where-Object { $_.LastWriteTime -ge $started } | ForEach-Object { Write-Host "CRASH REPORT: $($_.FullName)" }
}

$hasResult = (Test-Path $log) -and (Select-String -Path $log -Pattern '\] RESULT (PASS|FAIL)' -Quiet)
$loaderLog = Join-Path $Root 'd2rloader\logs\d2rloader.log'
if (-not $hasResult -and (Test-Path $loaderLog) -and (Get-Item $loaderLog).LastWriteTime -ge $started) {
    # The game ended on its own before the script did: show what the loader complained about.
    $errors = @(Select-String -Path $loaderLog -Pattern '\[ERROR\]')
    if ($errors) {
        Write-Host "LOADER ERRORS ($($errors.Count) in $loaderLog), last 12:"
        $errors | Select-Object -Last 12 | ForEach-Object { Write-Host ('  ' + $_.Line.Substring(0, [Math]::Min(300, $_.Line.Length))) }
    }
}

$result = if (Test-Path $log) { Select-String -Path $log -Pattern '\] RESULT (PASS|FAIL)' | Select-Object -Last 1 } else { $null }
if (-not $result) { Write-Host 'NO RESULT: the script did not reach "exit" (crash, timeout, or the game was closed).'; exit 2 }
if ($timedOut) { exit 2 }
if ($result.Matches[0].Groups[1].Value -eq 'PASS') { exit 0 } else { exit 1 }

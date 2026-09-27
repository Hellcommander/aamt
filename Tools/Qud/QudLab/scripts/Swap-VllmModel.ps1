<#
.SYNOPSIS
  List / status / swap the live WSL vLLM model (one at a time on 11GB).

.EXAMPLE
  .\Swap-VllmModel.ps1 list
  .\Swap-VllmModel.ps1 status
  .\Swap-VllmModel.ps1 swap -Model Qwen/Qwen2.5-Coder-7B-Instruct-AWQ
  .\Swap-VllmModel.ps1 swap -Model Qwen/Qwen2.5-3B-Instruct -RestartFrontend
#>
[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [ValidateSet('list', 'status', 'swap', 'stop')]
    [string]$Action = 'status',

    [string]$Model = $(if ($env:QUDLAB_VLLM_MODEL) { $env:QUDLAB_VLLM_MODEL } elseif ($env:QUDLAB_HF_MODEL) { $env:QUDLAB_HF_MODEL } else { '' }),

    [int]$Port = 8000,

    [switch]$RestartFrontend,

    [int]$FrontendPort = 30000,

    [string]$ExtraArgs = ''
)

$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$labRoot = Split-Path -Parent $here
$serveScript = Join-Path $here 'Serve-Vllm.ps1'
$frontendScript = Join-Path $here 'Serve-Sglang.ps1'
$settings = Join-Path $env:LOCALAPPDATA 'QudLab\gui-llm.txt'
$v1 = "http://127.0.0.1:$Port/v1"

$Presets = @(
    'Qwen/Qwen2.5-Coder-7B-Instruct-AWQ',
    'Qwen/Qwen2.5-3B-Instruct',
    'Qwen/Qwen2.5-Coder-3B-Instruct',
    'Qwen/Qwen2.5-7B-Instruct-AWQ',
    'Qwen/Qwen2.5-7B-Instruct-GPTQ-Int4',
    'Qwen/Qwen2.5-1.5B-Instruct'
)

function Get-HfCacheRoots {
    $roots = New-Object System.Collections.Generic.List[string]
    foreach ($c in @(
            $env:HF_HOME,
            'D:\hf-cache',
            (Join-Path $env:USERPROFILE '.cache\huggingface'),
            (Join-Path $env:USERPROFILE '.cache\huggingface\hub')
        )) {
        if (-not $c) { continue }
        $hub = if ((Split-Path -Leaf $c) -eq 'hub') { $c } else { Join-Path $c 'hub' }
        if (Test-Path -LiteralPath $hub) { $roots.Add((Resolve-Path -LiteralPath $hub).Path) }
        elseif (Test-Path -LiteralPath $c) { $roots.Add((Resolve-Path -LiteralPath $c).Path) }
    }
    $roots | Select-Object -Unique
}

function Get-LastSelectedModel {
    if (-not (Test-Path -LiteralPath $settings)) { return '' }
    try {
        $raw = Get-Content -LiteralPath $settings -Raw -ErrorAction SilentlyContinue
        if ($null -eq $raw) { return '' }
        return $raw.Trim()
    } catch { return '' }
}

function Test-LikelyChatModel([string]$id) {
    if ($Presets -contains $id) { return $true }
    $l = $id.ToLowerInvariant()
    if ($l -match 'stable-diffusion|stable-audio|trellis|clap|lora|sdxl|vae|controlnet') { return $false }
    if ($l -match 'qwen|llama|mistral|mixtral|deepseek|phi-|gemma|yi-|codellama|command-r') { return $true }
    if ($l -match 'instruct|chat|coder') { return $true }
    return $false
}

function Get-CachedHfModels {
    $set = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    foreach ($p in $Presets) { [void]$set.Add($p) }
    $last = Get-LastSelectedModel
    if ($last) { [void]$set.Add($last) }
    foreach ($hub in Get-HfCacheRoots) {
        Get-ChildItem -LiteralPath $hub -Directory -Filter 'models--*' -ErrorAction SilentlyContinue | ForEach-Object {
            $name = $_.Name
            if ($name -like 'models--*') {
                $id = $name.Substring(8).Replace('--', '/')
                if (($id -match '/') -and (Test-LikelyChatModel $id)) { [void]$set.Add($id) }
            }
        }
    }
    $set | Sort-Object
}

function Get-LiveVllmModels {
    try {
        $r = Invoke-RestMethod -Uri ($v1.TrimEnd('/') + '/models') -TimeoutSec 3
        @($r.data | ForEach-Object { [string]$_.id } | Where-Object { $_ })
    } catch {
        @()
    }
}

function Test-VllmUp {
    try {
        $null = Invoke-WebRequest -Uri ($v1.TrimEnd('/') + '/models') -UseBasicParsing -TimeoutSec 2
        return $true
    } catch {
        return $false
    }
}

function Stop-VllmPort {
    Write-Host "Stopping listeners on :$Port and WSL vllm..." -ForegroundColor Yellow
    $conns = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    foreach ($procId in @($conns.OwningProcess | Sort-Object -Unique)) {
        if (-not $procId) { continue }
        try {
            Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
            Write-Host "  killed Windows PID $procId"
        } catch { }
    }
    try {
        wsl -d Ubuntu -u arendeth -- bash -lc "pkill -f '[v]llm' || pkill -f 'VLLM::EngineCore' || true" 2>$null | Out-Null
    } catch { }
    Start-Sleep -Seconds 2
    for ($i = 0; $i -lt 20 -and (Test-VllmUp); $i++) {
        Start-Sleep -Milliseconds 400
        try { wsl -d Ubuntu -u arendeth -- bash -lc "pkill -9 -f '[v]llm' || true" 2>$null | Out-Null } catch { }
    }
    if (Test-VllmUp) {
        Write-Host "WARNING: :$Port still answering after stop" -ForegroundColor Red
        return $false
    }
    return $true
}

function Save-LastModel([string]$id) {
    $dir = Split-Path -Parent $settings
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
    Set-Content -LiteralPath $settings -Value $id.Trim() -Encoding utf8
}

function Start-VllmModel([string]$id) {
    if (-not (Test-Path -LiteralPath $serveScript)) { throw "Missing $serveScript" }
    Save-LastModel $id
    $env:QUDLAB_VLLM_MODEL = $id
    $env:QUDLAB_HF_MODEL = $id
    Write-Host "Starting vLLM with $id on :$Port ..." -ForegroundColor Cyan
    $arg = @(
        '-NoProfile', '-ExecutionPolicy', 'Bypass',
        '-File', $serveScript,
        '-Model', $id,
        '-Port', "$Port"
    )
    if ($ExtraArgs) { $arg += @('-ExtraArgs', $ExtraArgs) }
    Start-Process -FilePath 'powershell.exe' -ArgumentList $arg -WorkingDirectory $labRoot
    for ($i = 0; $i -lt 120; $i++) {
        Start-Sleep -Seconds 2
        $live = Get-LiveVllmModels
        if ($live.Count -gt 0) {
            Write-Host "vLLM up: $v1  loaded=$($live -join ', ')" -ForegroundColor Green
            return $true
        }
        Write-Host ("  waiting... {0}s" -f (($i + 1) * 2))
    }
    Write-Host "Timed out waiting for /v1/models - check the vLLM window / WSL." -ForegroundColor Red
    return $false
}

function Restart-Frontend([string]$id) {
    if (-not (Test-Path -LiteralPath $frontendScript)) {
        Write-Host "No frontend script; skip :$FrontendPort" -ForegroundColor DarkYellow
        return
    }
    $fe = Get-NetTCPConnection -LocalPort $FrontendPort -State Listen -ErrorAction SilentlyContinue
    foreach ($procId in @($fe.OwningProcess | Sort-Object -Unique)) {
        if (-not $procId) { continue }
        $cim = Get-CimInstance Win32_Process -Filter ("ProcessId={0}" -f $procId) -ErrorAction SilentlyContinue
        $cmd = [string]$cim.CommandLine
        if ($cmd -match 'openai-proxy|sglang') {
            Write-Host "Restarting frontend PID $procId with model-name $id"
            Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
        }
    }
    Start-Sleep -Seconds 1
    $arg = @(
        '-NoProfile', '-ExecutionPolicy', 'Bypass',
        '-File', $frontendScript,
        '-Remote', '-RemoteUrl', "http://127.0.0.1:$Port/v1",
        '-Port', "$FrontendPort",
        '-Model', $id
    )
    Start-Process -FilePath 'powershell.exe' -ArgumentList $arg -WorkingDirectory $labRoot -WindowStyle Minimized
}

switch ($Action) {
    'list' {
        Write-Host "Cached / preset models (pick one - only one fits in 11GB VRAM):"
        $last = Get-LastSelectedModel
        Get-CachedHfModels | ForEach-Object {
            $mark = if ($last -and ($_ -eq $last)) { ' *last*' } else { '' }
            Write-Host ("  {0}{1}" -f $_, $mark)
        }
        exit 0
    }
    'status' {
        $live = Get-LiveVllmModels
        if ($live.Count -eq 0) {
            Write-Host "vLLM :$Port DOWN"
            $last = Get-LastSelectedModel
            if (-not $last) { $last = '(none)' }
            Write-Host "last selected: $last"
            exit 1
        }
        Write-Host "vLLM :$Port UP"
        Write-Host ("loaded: {0}" -f ($live -join ', '))
        exit 0
    }
    'stop' {
        if (Stop-VllmPort) { Write-Host "Stopped."; exit 0 }
        exit 1
    }
    'swap' {
        if (-not $Model) {
            Write-Host "Usage: Swap-VllmModel.ps1 swap -Model org/name [-RestartFrontend]" -ForegroundColor Red
            Write-Host "Try: Swap-VllmModel.ps1 list"
            exit 2
        }
        $live = Get-LiveVllmModels
        if ($live -contains $Model) {
            Write-Host "Already loaded: $Model"
            if ($RestartFrontend) { Restart-Frontend $Model }
            exit 0
        }
        if ($live.Count -gt 0) {
            Write-Host ("Currently loaded: {0} - swapping to {1}" -f ($live -join ', '), $Model)
        }
        if (-not (Stop-VllmPort)) { exit 1 }
        if (-not (Start-VllmModel $Model)) { exit 1 }
        if ($RestartFrontend) { Restart-Frontend $Model }
        exit 0
    }
}

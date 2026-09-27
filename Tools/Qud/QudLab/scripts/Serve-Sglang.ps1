param(
    [string]$Model = $(if ($env:QUDLAB_SGLANG_MODEL) { $env:QUDLAB_SGLANG_MODEL } elseif ($env:QUDLAB_HF_MODEL) { $env:QUDLAB_HF_MODEL } else { "Qwen/Qwen2.5-Coder-7B-Instruct-AWQ" }),
    [int]$Port = 30000,
    [string]$RemoteUrl = $(if ($env:QUDLAB_VLLM_URL) { $env:QUDLAB_VLLM_URL } else { "http://127.0.0.1:8000/v1" }),
    [switch]$Remote,
    [switch]$Local,
    [switch]$Router,
    [string]$ExtraArgs = ""
)

# ASCII-only: Windows PowerShell 5.1 misparses UTF-8 em-dashes as string quotes.
$ErrorActionPreference = "Continue"
if (Get-Variable -Name PSNativeCommandUseErrorActionPreference -ErrorAction SilentlyContinue) {
    $PSNativeCommandUseErrorActionPreference = $false
}

$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$proxy = Join-Path $here "openai-proxy.py"

function Resolve-Python {
    $cands = New-Object System.Collections.Generic.List[string]
    foreach ($known in @(
            "E:\tools\miniconda3\python.exe",
            "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe",
            "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe"
        )) {
        if (Test-Path $known) { $cands.Add($known) }
    }
    foreach ($name in @("python", "python3", "py")) {
        $cmd = Get-Command $name -ErrorAction SilentlyContinue
        if ($cmd -and $cmd.Source -and ($cmd.Source -notmatch "WindowsApps")) {
            $cands.Add($cmd.Source)
        }
    }
    foreach ($py in $cands) {
        & $py -c "import sys" 2>$null | Out-Null
        if ($LASTEXITCODE -eq 0) { return $py }
    }
    throw "Python not on PATH. Install Python 3.12+ (or Miniconda) for the SGLang frontend."
}

function Resolve-AdvertiseModel([string]$requested, [string]$v1url) {
    $aliases = @("vllm-backend", "vllm", "remote", "openai", "unknown", "")
    try {
        $resp = Invoke-RestMethod -Uri ($v1url.TrimEnd("/") + "/models") -TimeoutSec 5
        $wid = [string]$resp.data[0].id
        if ($wid -and ($aliases -notcontains $wid.ToLowerInvariant())) {
            return $wid
        }
    } catch { }
    if ($requested -and ($aliases -notcontains $requested.ToLowerInvariant())) {
        return $requested
    }
    return "Qwen/Qwen2.5-Coder-7B-Instruct-AWQ"
}

function Strip-V1Prefix([string]$url) {
    $u = $url.Trim().TrimEnd("/")
    if ($u -match "/v1$") { return $u.Substring(0, $u.Length - 3) }
    return $u
}

function Test-PyModule([string]$py, [string]$mod) {
    & $py -c "import $mod" 2>$null | Out-Null
    return ($LASTEXITCODE -eq 0)
}

function Ensure-Router([string]$py) {
    if (Test-PyModule $py "sglang_router") { return $true }
    Write-Host "Installing sglang-router (SGLang Model Gateway) into this Python..."
    & $py -m pip install --user sglang-router
    return (Test-PyModule $py "sglang_router")
}

function Free-ListenPort([int]$port) {
    $conns = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    if (-not $conns) { return }
    foreach ($procId in ($conns.OwningProcess | Sort-Object -Unique)) {
        $cim = Get-CimInstance Win32_Process -Filter ("ProcessId={0}" -f $procId) -ErrorAction SilentlyContinue
        $cmd = [string]$cim.CommandLine
        $ours = ($cmd -match "openai-proxy\.py") -or ($cmd -match "sglang_router") -or ($cmd -match "sglang\.launch_server")
        if (-not $ours) {
            Write-Host ("Port {0} is in use by PID {1} (not a Qud Lab frontend). Close it first." -f $port, $procId) -ForegroundColor Red
            Write-Host $cmd
            exit 1
        }
        Write-Host ("Stopping leftover frontend PID {0} on :{1}" -f $procId, $port)
        Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep -Seconds 1
}

if ($Local) {
    $py = Resolve-Python
    if (-not (Test-PyModule $py "sglang")) {
        Write-Host "Full SGLang runtime is not installed in this Windows Python." -ForegroundColor Red
        Write-Host "GPU inference stays in WSL vLLM. Use the gateway frontend:"
        Write-Host "  qudlab vllm serve --model Qwen/Qwen2.5-Coder-7B-Instruct-AWQ"
        Write-Host "  qudlab sglang serve --remote"
        Write-Host "https://github.com/sgl-project/sglang"
        exit 1
    }
    Write-Host "Launching SGLang runtime (sglang.launch_server) on :$Port"
    Write-Host "OpenAI API: http://127.0.0.1:$Port/v1"
    Free-ListenPort $Port
    $launch = @(
        "-m", "sglang.launch_server",
        "--model-path", $Model,
        "--host", "127.0.0.1",
        "--port", "$Port",
        "--tool-call-parser", "qwen25"
    )
    if ($ExtraArgs) { $launch += $ExtraArgs.Split(" ", [System.StringSplitOptions]::RemoveEmptyEntries) }
    & $py @launch
    exit $LASTEXITCODE
}

if (-not $RemoteUrl.StartsWith("http://") -and -not $RemoteUrl.StartsWith("https://")) {
    $RemoteUrl = "http://" + $RemoteUrl.Trim()
}
if ($RemoteUrl -notmatch "/v1") { $RemoteUrl = $RemoteUrl.TrimEnd("/") + "/v1" }

$py = Resolve-Python
$worker = Strip-V1Prefix $RemoteUrl
$Model = Resolve-AdvertiseModel $Model $RemoteUrl

Write-Host "OpenAI frontend -> vLLM (Cursor / Cortex / LM Studio)"
Write-Host "  python:    $py"
Write-Host "  frontend:  http://127.0.0.1:$Port/v1"
Write-Host "  backend:   $RemoteUrl"
Write-Host "  model id:  $Model"
Write-Host "Full SGLang GPU runtime is --local (replaces vLLM). sglang_router openai-backend is optional --router."
Write-Host "Start vLLM first if health checks fail: qudlab vllm serve --model Qwen/Qwen2.5-Coder-7B-Instruct-AWQ"
Free-ListenPort $Port

$wantRouter = $Router -or ($env:QUDLAB_SGLANG_ROUTER -eq "1")
if ($wantRouter -and (Ensure-Router $py)) {
    $parser = "qwen"
    if ($Model -match "Qwen2\.5|qwen2\.5") { $parser = "qwen" }
    $innerPort = 30001
    Free-ListenPort $innerPort
    $router = @(
        "-m", "sglang_router.launch_router",
        "--backend", "openai",
        "--worker-urls", $worker,
        "--host", "127.0.0.1",
        "--port", "$innerPort",
        "--history-backend", "none",
        "--tool-call-parser", $parser,
        "--policy", "cache_aware",
        "--model-path", $Model
    )
    if ($ExtraArgs) { $router += $ExtraArgs.Split(" ", [System.StringSplitOptions]::RemoveEmptyEntries) }
    Write-Host "Using sglang_router openai-backend on :$innerPort (lists model id=unknown; proxy rewrites it)."
    $routerProc = Start-Process -FilePath $py -ArgumentList $router -PassThru -WindowStyle Hidden
    $ready = $false
    for ($i = 0; $i -lt 20; $i++) {
        Start-Sleep -Milliseconds 400
        try {
            $null = Invoke-RestMethod -Uri "http://127.0.0.1:$innerPort/health" -TimeoutSec 1
            $ready = $true
            break
        } catch { }
    }
    if (-not $ready) {
        Write-Host "Router on :$innerPort did not become ready; proxy will still rewrite /v1/models from vLLM." -ForegroundColor Yellow
    }
    try {
        & $py $proxy --host 127.0.0.1 --port $Port --remote ("http://127.0.0.1:{0}/v1" -f $innerPort) --models-from $RemoteUrl --model-name $Model
        exit $LASTEXITCODE
    } finally {
        if ($routerProc -and -not $routerProc.HasExited) {
            Stop-Process -Id $routerProc.Id -Force -ErrorAction SilentlyContinue
        }
    }
}

Write-Host "Skipping sglang_router (openai-backend would advertise id=unknown). Proxy talks to vLLM."
if (-not (Test-Path $proxy)) {
    Write-Host "Missing proxy script: $proxy" -ForegroundColor Red
    exit 1
}
& $py $proxy --host 127.0.0.1 --port $Port --remote $RemoteUrl --models-from $RemoteUrl --model-name $Model
exit $LASTEXITCODE

param(
    [string]$Model = $(if ($env:QUDLAB_VLLM_MODEL) { $env:QUDLAB_VLLM_MODEL } elseif ($env:QUDLAB_HF_MODEL) { $env:QUDLAB_HF_MODEL } else { "Qwen/Qwen2.5-Coder-7B-Instruct-AWQ" }),
    [int]$Port = 8000,
    [string]$ExtraArgs = ""
)

$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
# scripts -> QudLab -> Qud -> Tools
$toolsRoot = Split-Path (Split-Path (Split-Path $here -Parent) -Parent) -Parent
$tokenModule = Join-Path $toolsRoot "Shared\HfTokenSwitch.psm1"
if (-not (Test-Path $tokenModule)) {
    $tokenModule = "D:\games\Ai assisted toolkit\Tools\Shared\HfTokenSwitch.psm1"
}

function Ensure-HfToken {
    if ($env:HF_TOKEN) { return }
    if (Test-Path $tokenModule) {
        Import-Module $tokenModule -Force
        foreach ($profileName in @("media", "training")) {
            try {
                Use-AamtHfToken -Profile $profileName -Quiet | Out-Null
                if ($env:HF_TOKEN) {
                    Write-Host ("HF Hub: using stored profile '{0}' ({1})" -f $profileName, $env:AAMT_HF_ACTIVE_TOKEN_NAME)
                    return
                }
            } catch { }
        }
        foreach ($n in @(Get-AamtHfStoredTokenNames)) {
            if (-not $n) { continue }
            try {
                Use-AamtHfToken -Profile $n -Quiet | Out-Null
                if ($env:HF_TOKEN) {
                    Write-Host ("HF Hub: using stored token '{0}'" -f $n)
                    return
                }
            } catch { }
        }
    }
    try {
        $tok = & hf auth token 2>$null
        if ($tok) { $env:HF_TOKEN = ($tok | Select-Object -Last 1).ToString().Trim() }
    } catch { }
}

Ensure-HfToken
if ($env:HF_TOKEN) {
    $env:HUGGING_FACE_HUB_TOKEN = $env:HF_TOKEN
} else {
    Write-Host "HF Hub: no stored token found. Backend will log unauthenticated / unknown until you run hf auth login." -ForegroundColor Yellow
}

# Empty HF_TOKEN in WSLENV would wipe a WSL-side login. Only forward if set.
$wslEnvParts = New-Object System.Collections.Generic.List[string]
if ($env:HF_TOKEN) {
    $wslEnvParts.Add("HF_TOKEN/u")
    $wslEnvParts.Add("HUGGING_FACE_HUB_TOKEN/u")
}
if (-not $env:HF_HOME -and (Test-Path "D:\hf-cache")) {
    $env:HF_HOME = "D:\hf-cache"
}
if ($env:HF_HOME) { $wslEnvParts.Add("HF_HOME/u") }
$wslEnvParts.AddRange([string[]]@(
        "VLLM_PORT/u",
        "VLLM_GPU_UTIL/u",
        "VLLM_MAX_MODEL_LEN/u",
        "VLLM_MAX_NUM_SEQS/u",
        "VLLM_SWAP_SPACE/u",
        "VLLM_CPU_OFFLOAD_GB/u",
        "VLLM_DTYPE/u",
        "QUDLAB_HF_MODEL/u",
        "QUDLAB_VLLM_MODEL/u",
        "VLLM_USE_V2_MODEL_RUNNER/u",
        "VLLM_WSL2_ENABLE_PIN_MEMORY/u"
    ))
$env:WSLENV = ($wslEnvParts -join ":")
$env:VLLM_PORT = "$Port"
# 64k context; KV overflow spills to RAM via --swap-space (see wsl-vllm-serve.sh).
$env:VLLM_MAX_MODEL_LEN = $(if ($env:VLLM_MAX_MODEL_LEN) { $env:VLLM_MAX_MODEL_LEN } else { "65536" })
$env:VLLM_MAX_NUM_SEQS = $(if ($env:VLLM_MAX_NUM_SEQS) { $env:VLLM_MAX_NUM_SEQS } else { "1" })
$env:VLLM_GPU_UTIL = $(if ($env:VLLM_GPU_UTIL) { $env:VLLM_GPU_UTIL } else { "0.72" })
$env:VLLM_SWAP_SPACE = $(if ($env:VLLM_SWAP_SPACE) { $env:VLLM_SWAP_SPACE } else { "24" })
$env:VLLM_DTYPE = $(if ($env:VLLM_DTYPE) { $env:VLLM_DTYPE } else { "auto" })
$env:QUDLAB_HF_MODEL = $Model
$env:QUDLAB_VLLM_MODEL = $Model

$localServe = Join-Path $here "wsl-vllm-serve.sh"
$installPy = Join-Path $here "install-wsl-serve.py"
if (Test-Path $localServe) {
    $py = "E:\tools\miniconda3\python.exe"
    if (-not (Test-Path $py)) { $py = "python" }
    & $py $installPy $localServe
    if ($LASTEXITCODE -ne 0) { throw "Failed to install LF serve.sh into WSL" }
}

Write-Host "Launching vLLM 0.29 with Hugging Face model: $Model"
Write-Host "OpenAI API: http://127.0.0.1:$Port/v1"
if ($env:HF_TOKEN) {
    Write-Host "HF Hub: token forwarded into WSL (not printed)"
} else {
    Write-Host "HF Hub: unauthenticated"
}

$wslArgs = @(
    "-d", "Ubuntu", "-u", "arendeth", "--",
    "bash", "/home/arendeth/vllm/serve.sh", $Model
)
if ($ExtraArgs) {
    $wslArgs += $ExtraArgs.Split(" ", [System.StringSplitOptions]::RemoveEmptyEntries)
}
& wsl @wslArgs
exit $LASTEXITCODE

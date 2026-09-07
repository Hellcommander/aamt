<#
.SYNOPSIS
    Stable Audio 3 integration for Transcendence / AAMT sound effects.

.DESCRIPTION
    Wraps Shared\stable_audio_generate.py (stable-audio-3 library).
    Default model: medium. For short SFX without Flash-Attn, use small-sfx.
#>

$script:StableAudioModel = if ($env:AAMT_STABLE_AUDIO_MODEL) {
    $env:AAMT_STABLE_AUDIO_MODEL
} else {
    "medium"
}

$script:StableAudioDir = if ($env:AAMT_STABLE_AUDIO_DIR) {
    $env:AAMT_STABLE_AUDIO_DIR
} else {
    "E:\tools\stable-audio"
}

function Find-StableAudioPython {
    if ($env:AAMT_STABLE_AUDIO_PYTHON -and (Test-Path $env:AAMT_STABLE_AUDIO_PYTHON)) {
        return $env:AAMT_STABLE_AUDIO_PYTHON
    }
    if ($env:AAMT_PYTHON -and (Test-Path $env:AAMT_PYTHON)) {
        return $env:AAMT_PYTHON
    }

    $candidates = @(
        "E:\tools\miniconda3\python.exe",
        "C:\Python312\python.exe",
        "C:\Python313\python.exe",
        "C:\Python314\python.exe"
    )
    foreach ($c in $candidates) {
        if (Test-Path $c) {
            $check = & $c -c "import torch; print('1' if torch.cuda.is_available() else '0')" 2>$null
            if ($check -eq "1") { return $c }
        }
    }

    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    return $null
}

function Get-StableAudioGeneratorScript {
    $path = Join-Path $PSScriptRoot "stable_audio_generate.py"
    if (Test-Path $path) { return $path }
    return $null
}

function Import-StableAudioEnv {
    $envFile = Join-Path $script:StableAudioDir "aamt_stable_audio_env.ps1"
    if (Test-Path $envFile) { . $envFile }

    # Weights on install drive; never override HF_HOME (token lives in user profile)
    $hfHub = Join-Path $script:StableAudioDir "hub"
    if (-not $env:HUGGINGFACE_HUB_CACHE) { $env:HUGGINGFACE_HUB_CACHE = $hfHub }
    if (-not $env:HF_HUB_CACHE) { $env:HF_HUB_CACHE = $hfHub }

    # Prefer media download token for SA3 gated weights
    $tokenSwitch = Join-Path $PSScriptRoot "HfTokenSwitch.psm1"
    if (Test-Path $tokenSwitch) {
        Import-Module $tokenSwitch -Force -ErrorAction SilentlyContinue
        try { Use-AamtHfMediaToken -Quiet | Out-Null } catch { }
    }

    $repo = Join-Path $script:StableAudioDir "stable-audio-3"
    if (Test-Path $repo) {
        if ($env:PYTHONPATH) {
            if ($env:PYTHONPATH -notlike "*$repo*") {
                $env:PYTHONPATH = "$repo;$env:PYTHONPATH"
            }
        } else {
            $env:PYTHONPATH = $repo
        }
    }
}

function Test-StableAudioReady {
    param([switch]$Verbose)
    Import-StableAudioEnv
    $py = Find-StableAudioPython
    $script = Get-StableAudioGeneratorScript
    if (-not $py) {
        if ($Verbose) { Write-Host "  [StableAudio] Python not found" -ForegroundColor Yellow }
        return $false
    }
    if (-not $script) {
        if ($Verbose) { Write-Host "  [StableAudio] stable_audio_generate.py missing" -ForegroundColor Yellow }
        return $false
    }
    $out = & $py $script --check-only 2>&1
    $ok = ($LASTEXITCODE -eq 0)
    if ($Verbose) {
        if ($ok) {
            Write-Host "  [StableAudio] Ready: $out" -ForegroundColor Green
            Write-Host "  [StableAudio] Python: $py" -ForegroundColor Gray
        } else {
            Write-Host "  [StableAudio] Not ready: $out" -ForegroundColor Yellow
        }
    }
    return $ok
}

function Invoke-StableAudioGeneration {
    <#
    .SYNOPSIS
    Generate a WAV sound effect via Stable Audio 3.
    #>
    param(
        [Parameter(Mandatory = $true)][string]$Prompt,
        [Parameter(Mandatory = $true)][string]$OutputPath,
        [string]$NegativePrompt = "Low quality, muffled, distorted, silence",
        [double]$Seconds = 4.0,
        [Nullable[int]]$Steps = $null,
        [Nullable[int]]$Seed = $null,
        [string]$Model = "",
        [string]$PythonPath = "",
        [switch]$Verbose
    )

    Import-StableAudioEnv

    $py = if ($PythonPath) { $PythonPath } else { Find-StableAudioPython }
    $gen = Get-StableAudioGeneratorScript
    if (-not $py) { throw "No Python found for Stable Audio. Run Setup-StableAudio.ps1" }
    if (-not $gen) { throw "stable_audio_generate.py not found under Shared\" }

    if ([string]::IsNullOrWhiteSpace($Model)) { $Model = $script:StableAudioModel }

    $outDir = Split-Path -Parent $OutputPath
    if ($outDir -and -not (Test-Path $outDir)) {
        New-Item -ItemType Directory -Path $outDir -Force | Out-Null
    }

    $argsList = @(
        $gen,
        "--prompt", $Prompt,
        "--output", $OutputPath,
        "--negative-prompt", $NegativePrompt,
        "--seconds", "$Seconds",
        "--model", $Model
    )
    if ($null -ne $Steps) { $argsList += @("--steps", "$Steps") }
    if ($null -ne $Seed) { $argsList += @("--seed", "$Seed") }

    if ($Verbose) {
        Write-Host "  [StableAudio] $py $($argsList -join ' ')" -ForegroundColor Gray
    }

    & $py @argsList
    if ($LASTEXITCODE -ne 0) {
        throw "Stable Audio generation failed (exit $LASTEXITCODE)"
    }
    if (-not (Test-Path $OutputPath)) {
        throw "Expected output missing: $OutputPath"
    }
    return (Resolve-Path $OutputPath).Path
}

Export-ModuleMember -Function Find-StableAudioPython, Test-StableAudioReady, Invoke-StableAudioGeneration, Get-StableAudioGeneratorScript, Import-StableAudioEnv

<#
.SYNOPSIS
    Hugging Face login helper for AAMT tools.

.DESCRIPTION
    Uses the account this machine is already logged in with (`hf auth login`, or an
    HF_TOKEN you set yourself). No token names, profiles or secrets live in the repo.
    The old -Profile values (media, training, ...) are accepted and ignored.

.EXAMPLE
    Import-Module .\Shared\HfTokenSwitch.psm1
    Use-AamtHfToken -Profile media
#>

function Resolve-AamtHfPython {
    if ($env:AAMT_STABLE_AUDIO_PYTHON -and (Test-Path $env:AAMT_STABLE_AUDIO_PYTHON)) {
        return $env:AAMT_STABLE_AUDIO_PYTHON
    }
    if ($env:AAMT_PYTHON -and (Test-Path $env:AAMT_PYTHON)) {
        return $env:AAMT_PYTHON
    }
    foreach ($c in @(
        "E:\tools\miniconda3\python.exe",
        "C:\Python314\python.exe",
        "C:\Python313\python.exe",
        "C:\Python312\python.exe"
    )) {
        if (Test-Path $c) { return $c }
    }
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    return $null
}

function Get-AamtHfTokenName {
    param([string]$Profile = "default")
    return "hf login"
}

function Use-AamtHfToken {
    <#
    .SYNOPSIS
    Confirm a Hugging Face login exists and export it as HF_TOKEN for this process
    (needed by child processes such as WSL). -Profile is ignored.
    #>
    param(
        [string]$Profile = "default",
        [switch]$Quiet
    )

    $py = Resolve-AamtHfPython
    $switchPy = Join-Path $PSScriptRoot "hf_token_switch.py"
    if (-not $py) { throw "Python not found for HF login check" }
    if (-not (Test-Path $switchPy)) { throw "Missing $switchPy" }

    $raw = & $py $switchPy --print-env 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "No Hugging Face login found. Run: hf auth login`n$raw"
    }

    foreach ($line in @($raw)) {
        $s = "$line"
        if ($s -match '^(AAMT_HF_ACTIVE_TOKEN_NAME|HF_TOKEN|HUGGING_FACE_HUB_TOKEN)=(.*)$') {
            Set-Item -Path "Env:$($matches[1])" -Value $matches[2]
        }
    }

    if (-not $env:HF_TOKEN) {
        throw "Hugging Face login check did not produce a token. Run: hf auth login"
    }

    if (-not $Quiet) {
        Write-Host "[HF] Using the existing Hugging Face login" -ForegroundColor Green
    }
    return $env:AAMT_HF_ACTIVE_TOKEN_NAME
}

function Use-AamtHfMediaToken {
    param([switch]$Quiet)
    Use-AamtHfToken -Quiet:$Quiet
}

function Use-AamtHfTrainingToken {
    param([switch]$Quiet)
    Use-AamtHfToken -Quiet:$Quiet
}

function Get-AamtHfStoredTokenNames {
    $py = Resolve-AamtHfPython
    if (-not $py) { return @() }
    & $py -c "from huggingface_hub.utils._auth import get_stored_tokens; print(chr(10).join(get_stored_tokens().keys()))" 2>$null
}

Export-ModuleMember -Function Use-AamtHfToken, Use-AamtHfMediaToken, Use-AamtHfTrainingToken, Get-AamtHfTokenName, Get-AamtHfStoredTokenNames, Resolve-AamtHfPython

<#
.SYNOPSIS
    Auto-switch Hugging Face tokens by display name for AAMT tools.

.DESCRIPTION
    Reads tokens from the machine's HF stored_tokens (hf auth login).
    Never stores secrets in the repo — only token *names* / profile aliases.

.EXAMPLE
    Import-Module .\Shared\HfTokenSwitch.psm1
    Use-AamtHfToken -Profile media        # SD3.5 Token
    Use-AamtHfToken -Profile training     # Custom Modul for creation
#>

$script:DefaultProfiles = @{
    media           = "SD3.5 Token"
    sd              = "SD3.5 Token"
    "stable-audio"  = "SD3.5 Token"
    sd35            = "SD3.5 Token"
    training        = "Custom Modul for creation"
    primordialis    = "Custom Modul for creation"
    lora            = "Custom Modul for creation"
    peft            = "Custom Modul for creation"
}

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
    param([Parameter(Mandatory = $true)][string]$Profile)
    $key = $Profile.Trim().ToLowerInvariant()
    switch ($key) {
        { $_ -in @("media", "sd", "stable-audio", "sd35") } {
            if ($env:AAMT_HF_TOKEN_MEDIA) { return $env:AAMT_HF_TOKEN_MEDIA }
        }
        { $_ -in @("training", "primordialis", "lora", "peft") } {
            if ($env:AAMT_HF_TOKEN_TRAINING) { return $env:AAMT_HF_TOKEN_TRAINING }
        }
    }
    if ($script:DefaultProfiles.ContainsKey($key)) {
        return $script:DefaultProfiles[$key]
    }
    return $Profile
}

function Use-AamtHfToken {
    <#
    .SYNOPSIS
    Set HF_TOKEN in this process from a stored token display name / profile.
    #>
    param(
        [Parameter(Mandatory = $true)][string]$Profile,
        [switch]$Quiet
    )

    $py = Resolve-AamtHfPython
    $switchPy = Join-Path $PSScriptRoot "hf_token_switch.py"
    if (-not $py) { throw "Python not found for HF token switch" }
    if (-not (Test-Path $switchPy)) { throw "Missing $switchPy" }

    $raw = & $py $switchPy $Profile --print-env 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "HF token switch failed for profile '$Profile': $raw"
    }

    foreach ($line in @($raw)) {
        $s = "$line"
        if ($s -match '^(AAMT_HF_ACTIVE_TOKEN_NAME|AAMT_HF_ACTIVE_PROFILE|HF_TOKEN|HUGGING_FACE_HUB_TOKEN)=(.*)$') {
            Set-Item -Path "Env:$($matches[1])" -Value $matches[2]
        }
    }

    if (-not $env:HF_TOKEN) {
        throw "HF token switch did not set HF_TOKEN for profile '$Profile'"
    }

    $tokenName = $env:AAMT_HF_ACTIVE_TOKEN_NAME
    if (-not $Quiet) {
        Write-Host "[HF] Using token profile '$Profile' -> '$tokenName'" -ForegroundColor Green
    }
    return $tokenName
}

function Use-AamtHfMediaToken {
    param([switch]$Quiet)
    Use-AamtHfToken -Profile media -Quiet:$Quiet
}

function Use-AamtHfTrainingToken {
    param([switch]$Quiet)
    Use-AamtHfToken -Profile training -Quiet:$Quiet
}

function Get-AamtHfStoredTokenNames {
    $py = Resolve-AamtHfPython
    if (-not $py) { return @() }
    & $py -c "from huggingface_hub.utils._auth import get_stored_tokens; print(chr(10).join(get_stored_tokens().keys()))" 2>$null
}

Export-ModuleMember -Function Use-AamtHfToken, Use-AamtHfMediaToken, Use-AamtHfTrainingToken, Get-AamtHfTokenName, Get-AamtHfStoredTokenNames, Resolve-AamtHfPython

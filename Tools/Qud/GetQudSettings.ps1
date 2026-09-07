# Helper script to load settings.json for Qud Unity asset generator
# Returns a hashtable with settings. Live game Unity version overrides blank/stale JSON.

function Get-QudSettings {
    $settingsPath = Join-Path $PSScriptRoot "settings.json"
    
    if (-not (Test-Path $settingsPath)) {
        Write-Warning "settings.json not found at $settingsPath"
        return $null
    }
    
    try {
        # BOM-tolerant read
        $raw = [System.IO.File]::ReadAllText($settingsPath)
        if ($raw.Length -gt 0 -and [int][char]$raw[0] -eq 0xFEFF) {
            $raw = $raw.Substring(1)
        }
        $settings = $raw | ConvertFrom-Json

        $gameRoot = if ($env:QUD_GAME_ROOT) {
            $env:QUD_GAME_ROOT
        } elseif ($settings.gameRoot) {
            $settings.gameRoot
        } else {
            "E:\SteamLibrary\steamapps\common\Caves of Qud"
        }

        $unityVersion = [string]$settings.unityVersion
        $unityEditorPath = [string]$settings.unityEditorPath

        $sharedResolver = Join-Path (Split-Path $PSScriptRoot -Parent) "Shared\UnityVersionResolver.psm1"
        if (Test-Path $sharedResolver) {
            Import-Module $sharedResolver -Force -ErrorAction SilentlyContinue
            if ((Get-Command Get-GameUnityVersion -ErrorAction SilentlyContinue) -and (Test-Path $gameRoot)) {
                $detected = Get-GameUnityVersion -GameRoot $gameRoot
                if ($detected) {
                    $unityVersion = $detected
                    if (Get-Command Find-MatchingUnityEditor -ErrorAction SilentlyContinue) {
                        $exe = Find-MatchingUnityEditor -RequiredVersion $detected -ManualPath $unityEditorPath -Quiet
                        if ($exe) { $unityEditorPath = $exe }
                    }
                }
            }
        }

        return @{
            UnityPath = $settings.unityPath
            UnityEditorPath = $unityEditorPath
            ProjectPath = $settings.projectPath
            UnityVersion = $unityVersion
            GameRoot = $gameRoot
        }
    }
    catch {
        Write-Error "Failed to parse settings.json: $_"
        return $null
    }
}

# Export function if script is being sourced
if ($MyInvocation.InvocationName -ne '.') {
    $settings = Get-QudSettings
    if ($settings) {
        Write-Host "Game Root: $($settings.GameRoot)" -ForegroundColor Cyan
        Write-Host "Unity Path: $($settings.UnityPath)" -ForegroundColor Cyan
        Write-Host "Unity Editor: $($settings.UnityEditorPath)" -ForegroundColor Cyan
        Write-Host "Project Path: $($settings.ProjectPath)" -ForegroundColor Cyan
        Write-Host "Unity Version: $($settings.UnityVersion)" -ForegroundColor Cyan
    }
}

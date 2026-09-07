<#
.SYNOPSIS
    Generate spell / projectile / ship assets via Shared local SD + Ollama + optional Blender mesh.

.DESCRIPTION
    Wraps Shared/game_asset_kind.py. With -UnityLayout, writes under
    Assets/Resources/{System}/{Spells|Projectiles|Ships}/{Name}/.
    With -Defs, also writes gameplay JSON/XML. Import into Unity via:
      Import-Module Shared/UnityAssetExport.psm1
      Invoke-AamtUnityImportDefs -ProjectPath $ModPath -RequiredVersion 2021.3.45f2

.EXAMPLE
    .\GenerateGameAsset.ps1 -Kind spell -Theme "verdant pulse" -Name VerdantPulse -ModPath "E:\mod" -SystemName NatureMagic -Mesh -NoSd

.EXAMPLE
    .\GenerateGameAsset.ps1 -Kind ship -Theme "obsidian frigate" -Name ObsidianFrigate -OutDir "$env:TEMP\ships" -Mesh -NoSd
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [ValidateSet("spell", "projectile", "ship")]
    [string]$Kind,

    [Parameter(Mandatory)][string]$Theme,
    [Parameter(Mandatory)][string]$Name,

    [string]$ModPath = "",
    [string]$OutDir = "",
    [string]$SystemName = "GameAssets",

    [switch]$UnityLayout,
    [switch]$Mesh,
    [switch]$NoSd,
    [switch]$NoOllama,
    [string]$Model = "qwen2.5-coder:7b",
    [string]$OllamaUrl = "http://127.0.0.1:11434",
    [int]$FxFrames = 4,
    [int]$ProjFrames = 2,
    [switch]$Defs,

    # Ship: skip unique Armor/Shield HUD (circular + default shield instead)
    [switch]$NoUniqueHud,

    # After -Defs spell packs, copy JSON+icons into live Elin BepInEx injector
    [switch]$DeployElin,
    [string]$ElinRoot = "E:\SteamLibrary\steamapps\common\Elin",

    # After -Defs projectile/ship packs, copy XML+bitmaps into Transcendence Extensions/
    [switch]$DeployTx,
    [string]$TxRoot = "D:\games\Steam\steamapps\common\Transcendence"
)

$ErrorActionPreference = "Stop"
$shared = $PSScriptRoot
$py = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $py) { throw "python not on PATH" }

$root = if ($ModPath) { $ModPath } elseif ($OutDir) { $OutDir } else { Join-Path $env:TEMP "aamt_game_asset" }
if ($ModPath) { $UnityLayout = $true }
# Default: deploy when -Defs (functional pipeline).
if ($Defs -and $Kind -eq "spell") { $DeployElin = $true }
if ($Defs -and ($Kind -eq "projectile" -or $Kind -eq "ship")) { $DeployTx = $true }

$script = Join-Path $shared "game_asset_kind.py"
$pyArgs = @(
    $script,
    "--kind", $Kind,
    "--theme", $Theme,
    "--name", $Name,
    "--out-dir", $root,
    "--system", $SystemName,
    "--model", $Model,
    "--ollama-url", $OllamaUrl,
    "--fx-frames", "$FxFrames",
    "--proj-frames", "$ProjFrames"
)
if ($UnityLayout) { $pyArgs += "--unity-layout" }
if ($Mesh) { $pyArgs += "--mesh" }
if ($NoSd) { $pyArgs += "--no-sd" }
if ($NoOllama) { $pyArgs += "--no-ollama" }
if ($Defs) { $pyArgs += "--defs" }
if ($NoUniqueHud) { $pyArgs += "--no-unique-hud" }

Write-Host "GenerateGameAsset: $Kind / $Name -> $root" -ForegroundColor Cyan
& $py @pyArgs
$code = $LASTEXITCODE
if ($code -ne 0) { exit $code }

if ($DeployElin -and $Kind -eq "spell") {
    $deploy = Join-Path (Split-Path $shared -Parent) "Elin\Deploy-AamtElinAbility.ps1"
    if (-not (Test-Path $deploy)) {
        Write-Warning "Deploy script missing: $deploy"
    } else {
        # Unity layout nests under Assets/Resources/{System}/Spells/{Name}
        $searchRoot = $root
        $nested = Join-Path $root "Assets\Resources\$SystemName\Spells\$Name"
        if (Test-Path $nested) { $searchRoot = $nested }
        else {
            $alt = Get-ChildItem -LiteralPath $root -Recurse -Filter "*_elin_ability.json" -File -ErrorAction SilentlyContinue |
                Select-Object -First 1
            if ($alt) { $searchRoot = $alt.DirectoryName }
        }
        Write-Host "Deploying Elin ability defs from $searchRoot ..." -ForegroundColor Cyan
        & $deploy -SourceDir $searchRoot -ElinRoot $ElinRoot
    }
}

if ($DeployTx -and ($Kind -eq "projectile" -or $Kind -eq "ship")) {
    $deploy = Join-Path (Split-Path $shared -Parent) "Transcendence\Deploy-AamtTranscendence.ps1"
    if (-not (Test-Path $deploy)) {
        Write-Warning "Deploy script missing: $deploy"
    } else {
        $folder = if ($Kind -eq "ship") { "Ships" } else { "Projectiles" }
        $searchRoot = $root
        $nested = Join-Path $root "Assets\Resources\$SystemName\$folder\$Name"
        if (Test-Path $nested) { $searchRoot = $nested }
        else {
            $alt = Get-ChildItem -LiteralPath $root -Recurse -Filter "*_transcendence.xml" -File -ErrorAction SilentlyContinue |
                Select-Object -First 1
            if ($alt) { $searchRoot = $alt.DirectoryName }
        }
        Write-Host "Deploying Transcendence extension from $searchRoot ..." -ForegroundColor Cyan
        & $deploy -SourceDir $searchRoot -TxRoot $TxRoot
    }
}

exit 0

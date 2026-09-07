<#
.SYNOPSIS
  Transcendence API Switcher - pick a TranscendenceDev-integration-APIxx tree,
  compile Transcendence.exe from it, and deploy into the Steam game folder.

.DESCRIPTION
  Completes the incomplete CompileApiFolder workflow for exe switching:
    1. Discover TranscendenceDev* / TranscendenceDev-integration-API* folders
    2. Select by API number (or path)
    3. Build Transcendence\Transcendence.sln (NOT Alchemy\CCShell)
    4. Backup + deploy Transcendence.exe (and optional tools) to game root
    5. Remember the active API in ApiSwitcher.config.json

  Default configuration is "Debug For Contributors" (Hexarc stub — no Multiverse
  username/password; proprietary HexarcKeys.h is not in source).
  For Steam Multiverse: -Configuration SteamRelease and keep steam_api.dll enabled.

.EXAMPLE
  .\TranscendenceApiSwitcher.ps1
  .\TranscendenceApiSwitcher.ps1 -Api 59
  .\TranscendenceApiSwitcher.ps1 -Api 59 -Deploy -CompileTdb
  .\TranscendenceApiSwitcher.ps1 -List
  .\TranscendenceApiSwitcher.ps1 -ApiFolder "D:\...\TranscendenceDev-integration-API59" -Configuration "Release"
#>

[CmdletBinding(DefaultParameterSetName = "Interactive")]
param(
    [Parameter(ParameterSetName = "ByNumber")]
    [int]$Api = 0,

    [Parameter(ParameterSetName = "ByPath", Position = 0)]
    [string]$ApiFolder = "",

    [ValidateSet(
        "Debug For Contributors",
        "Preview For Contributors",
        "Release",
        "Debug",
        "SteamRelease",
        "SteamDebug"
    )]
    [string]$Configuration = "Debug For Contributors",

    [ValidateSet("Win32", "x64")]
    [string]$Platform = "x64",

    [string]$GameRoot = "D:\games\Steam\steamapps\common\Transcendence",

    [switch]$List,
    [switch]$Status,
    [switch]$CompileOnly,   # build but do not deploy
    [switch]$Deploy,        # force deploy (default when not -CompileOnly)
    [switch]$NoDeploy,      # alias for -CompileOnly
    [switch]$CompileTdb,    # after deploy, rebuild Transcendence.tdb from Transcendence_Source
    [switch]$DeployTools,   # also copy TransCompiler/TransData if built
    [switch]$UseVS2026,
    [switch]$SkipSdkCheck,
    [switch]$SkipX64Autofix,
    [switch]$ForceX64Autofix,
    [switch]$SkipSegmentedShipsAutofix,
    [switch]$ForceSegmentedShipsAutofix,
    [switch]$SkipResizeApiAutofix,
    [switch]$ForceResizeApiAutofix,
    [switch]$DisableSteamApi,  # rename steam_api.dll so Steam won't auto-update
    [switch]$UseX64Workspace,  # build from Tools/.../_x64_workspace (official tree untouched)
    [switch]$SyncX64Workspace, # refresh workspace from official then re-apply overlays
    [switch]$NonInteractive,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$ScriptDir = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
$ConfigPath = Join-Path $ScriptDir "ApiSwitcher.config.json"

# ============================================================
# Helpers
# ============================================================

function Write-Header([string]$Title) {
    Write-Host ""
    Write-Host ("=" * 60) -ForegroundColor Cyan
    Write-Host "  $Title" -ForegroundColor Cyan
    Write-Host ("=" * 60) -ForegroundColor Cyan
    Write-Host ""
}

function Get-ApiSwitcherConfig {
    $cfg = [ordered]@{
        GameRoot        = $GameRoot
        ActiveApiFolder = ""
        ActiveApi       = 0
        LastConfiguration = "Debug For Contributors"
        SearchRoots     = @(
            (Join-Path $GameRoot "game_and_dlc_source"),
            $GameRoot,
            (Join-Path $GameRoot "Tools")
        )
        VisualStudioPath = ""
    }
    if (Test-Path $ConfigPath) {
        try {
            $loaded = Get-Content $ConfigPath -Raw | ConvertFrom-Json
            foreach ($p in $loaded.PSObject.Properties) {
                $cfg[$p.Name] = $p.Value
            }
        } catch {
            Write-Host "Warning: could not parse $ConfigPath - using defaults" -ForegroundColor Yellow
        }
    }
    return $cfg
}

function Save-ApiSwitcherConfig($cfg) {
    $json = ($cfg | ConvertTo-Json -Depth 6)
    [System.IO.File]::WriteAllText($ConfigPath, $json, [System.Text.UTF8Encoding]::new($false))
}

function Get-ApiVersionFromTree([string]$Folder) {
    $hdr = Join-Path $Folder "Mammoth\Include\TSEVersions.h"
    if (Test-Path $hdr) {
        $m = Select-String -Path $hdr -Pattern 'API_VERSION\s*=\s*(\d+)' | Select-Object -First 1
        if ($m) { return [int]$m.Matches.Groups[1].Value }
    }
    if ((Split-Path $Folder -Leaf) -match 'API(\d+)') {
        return [int]$Matches[1]
    }
    return 0
}

function Find-ApiTrees {
    param($cfg)

    $found = @{}
    $roots = @()
    if ($cfg.SearchRoots) { $roots += @($cfg.SearchRoots) }
    $roots += @(
        (Join-Path $cfg.GameRoot "game_and_dlc_source"),
        $cfg.GameRoot
    )
    $roots = $roots | Select-Object -Unique

    foreach ($root in $roots) {
        if (-not (Test-Path -LiteralPath $root)) { continue }
        Get-ChildItem -LiteralPath $root -Directory -ErrorAction SilentlyContinue |
            Where-Object {
                $_.Name -match '^TranscendenceDev' -or
                $_.Name -match 'integration-API\d+'
            } |
            ForEach-Object {
                $sln = Join-Path $_.FullName "Transcendence\Transcendence.sln"
                if (-not (Test-Path -LiteralPath $sln)) { return }
                $api = Get-ApiVersionFromTree $_.FullName
                $key = $_.FullName.ToLowerInvariant()
                $found[$key] = [pscustomobject]@{
                    Name     = $_.Name
                    Path     = $_.FullName
                    Api      = $api
                    Solution = $sln
                    GameDir  = Join-Path $_.FullName "Transcendence\Game"
                }
            }
    }

    return @($found.Values | Sort-Object Api, Name)
}

function Get-CurrentGameInfo([string]$Root) {
    $exe = Join-Path $Root "Transcendence.exe"
    $info = [ordered]@{
        ExePath        = $exe
        Exists         = (Test-Path $exe)
        ProductVersion = ""
        FileVersion    = ""
        Length         = 0
        Modified       = $null
    }
    if ($info.Exists) {
        $vi = (Get-Item $exe).VersionInfo
        $item = Get-Item $exe
        $info.ProductVersion = $vi.ProductVersion
        $info.FileVersion = $vi.FileVersion
        $info.Length = $item.Length
        $info.Modified = $item.LastWriteTime
    }
    return [pscustomobject]$info
}

function Find-MSBuild {
    param([switch]$PreferVS2026, [string]$ConfiguredPath)

    if ($ConfiguredPath -and (Test-Path (Join-Path $ConfiguredPath "MSBuild\Current\Bin\MSBuild.exe"))) {
        return @{
            VsPath = $ConfiguredPath
            MsBuild = (Join-Path $ConfiguredPath "MSBuild\Current\Bin\MSBuild.exe")
        }
    }

    $vswhere = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"
    $candidates = @()

    if ($PreferVS2026) {
        $candidates += @(
            "D:\tools\Microsoft Visual Studio\18\Community",
            "${env:ProgramFiles}\Microsoft Visual Studio\18\Community",
            "${env:ProgramFiles}\Microsoft Visual Studio\2026\Community"
        )
    }
    $candidates += @(
        "D:\tools\Microsoft Visual Studio\18\Community",
        "${env:ProgramFiles}\Microsoft Visual Studio\2022\Community",
        "${env:ProgramFiles}\Microsoft Visual Studio\2022\Professional",
        "${env:ProgramFiles}\Microsoft Visual Studio\2022\Enterprise"
    )

    if (Test-Path $vswhere) {
        try {
            $latest = & $vswhere -latest -products * -requires Microsoft.Component.MSBuild -property installationPath 2>$null
            if ($latest) { $candidates = @($latest.Trim()) + $candidates }
        } catch {}
    }

    foreach ($vs in ($candidates | Select-Object -Unique)) {
        if ([string]::IsNullOrWhiteSpace($vs)) { continue }
        $msb = Join-Path $vs "MSBuild\Current\Bin\MSBuild.exe"
        if (Test-Path $msb) {
            return @{ VsPath = $vs; MsBuild = $msb }
        }
    }
    return $null
}

function Get-BestToolset([string]$VsPath) {
    $toolsetRoot = Join-Path $VsPath "VC\Tools\MSVC"
    if (-not (Test-Path $toolsetRoot)) { return "v143" }
    # Map by presence; VS 2022+/18 -> v143 is common
    return "v143"
}

function Get-PythonForAutofix {
    foreach ($c in @("python", "py", "python3")) {
        try {
            $v = & $c -c "import sys; print(sys.executable)" 2>$null
            if ($LASTEXITCODE -eq 0 -and $v) {
                $exe = if ($v -is [array]) { $v[-1] } else { "$v" }
                $exe = $exe.Trim()
                if ($exe -and (Test-Path -LiteralPath $exe)) {
                    return @{ Source = $exe }
                }
            }
        } catch {}
    }
    throw "Python not found for autofix scripts."
}

function Invoke-ApiTreeAutofix {
    param(
        [string]$ApiFolder,
        [string]$Platform,
        [string]$SteamworksSdk = "",
        [switch]$SkipX64Autofix,
        [switch]$ForceX64Autofix,
        [switch]$SkipSegmentedShipsAutofix,
        [switch]$ForceSegmentedShipsAutofix,
        [switch]$SkipResizeApiAutofix,
        [switch]$ForceResizeApiAutofix,
        [switch]$DryRun
    )

    $py = Get-PythonForAutofix
    $api59Extra = @("--api-root", $ApiFolder)
    if ($SteamworksSdk) {
        $api59Extra += @("--steamworks-sdk", $SteamworksSdk)
    }
    $fixes = @(
        @{
            Skip = $SkipSegmentedShipsAutofix
            Force = $ForceSegmentedShipsAutofix
            Script = "Fix-TranscendenceSegmentedShips.py"
            Extra = @($ApiFolder)
        },
        @{
            Skip = $SkipResizeApiAutofix
            Force = $ForceResizeApiAutofix
            Script = "Fix-TranscendenceResizeAPI.py"
            Extra = @("--api-root", $ApiFolder)
        }
    )
    if ($Platform -eq "x64") {
        $fixes += @(
            @{
                Skip = $SkipX64Autofix
                Force = $ForceX64Autofix
                Script = "Fix-TranscendenceX64.py"
                Extra = @($ApiFolder)
            },
            @{
                Skip = $SkipX64Autofix
                Force = $ForceX64Autofix
                Script = "Fix-TranscendenceX64V3.py"
                Extra = @("--api-root", $ApiFolder)
            },
            @{
                Skip = $SkipX64Autofix
                Force = $ForceX64Autofix
                Script = "Fix-TranscendenceJobSystem.py"
                Extra = @("--api-root", $ApiFolder)
            },
            @{
                Skip = $false
                Force = $false
                Script = "Fix-TranscendenceOptionalLibraries.py"
                Extra = @("--api-root", $ApiFolder)
            },
            @{
                Skip = $false
                Force = $false
                Script = "Fix-TranscendenceSysEventRegister.py"
                Extra = @("--api-root", $ApiFolder)
            },
            @{
                Skip = $false
                Force = $false
                Script = "Fix-Api59BuildProjects.py"
                Extra = $api59Extra
            },
            @{
                Skip = $false
                Force = $false
                Script = "Fix-Api59X64Deps.py"
                Extra = @("--api-root", $ApiFolder)
            },
            @{
                Skip = $false
                Force = $false
                Script = "Audit-X64Libs.py"
                Extra = @("--api-root", $ApiFolder)
            }
        )
    }

    foreach ($f in $fixes) {
        if ($f.Skip) { continue }
        $path = Join-Path $ScriptDir $f.Script
        if (-not (Test-Path $path)) {
            Write-Host "  skip missing autofix: $($f.Script)" -ForegroundColor DarkYellow
            continue
        }
        $a = @($path) + @($f.Extra)
        if ($f.Force) { $a += "--force" }
        if ($DryRun) { $a += "--dry-run" }
        Write-Host "Autofix: $($f.Script)" -ForegroundColor Cyan
        & $py.Source @a 2>&1 | ForEach-Object { Write-Host $_ }
        if ($LASTEXITCODE -ne 0) {
            throw "Autofix failed: $($f.Script) (exit $LASTEXITCODE)"
        }
    }
}

function Get-X64WorkspacePath([string]$OfficialApiFolder) {
    $name = Split-Path $OfficialApiFolder -Leaf
    return (Join-Path $ScriptDir "_x64_workspace\$name")
}

function Invoke-PrepareX64Workspace {
    param(
        [string]$OfficialApiFolder,
        [switch]$Sync,
        [switch]$ApplyFixes,
        [switch]$Force,
        [switch]$DryRun
    )
    $ws = Get-X64WorkspacePath $OfficialApiFolder
    $py = Get-PythonForAutofix
    $prep = Join-Path $ScriptDir "Prepare-X64Workspace.py"
    $a = @(
        $prep,
        "--api-root", $OfficialApiFolder,
        "--workspace", $ws
    )
    if ($Sync) { $a += "--sync" }
    if ($ApplyFixes) { $a += "--apply-fixes" }
    if ($Force) { $a += "--force" }
    Write-Host "Preparing x64 workspace (official tree untouched):" -ForegroundColor Cyan
    Write-Host "  official:  $OfficialApiFolder" -ForegroundColor DarkGray
    Write-Host "  workspace: $ws" -ForegroundColor DarkGray
    if ($DryRun) {
        Write-Host "[DryRun] $($a -join ' ')" -ForegroundColor Yellow
        return $ws
    }
    # Python prints to success stream — do not capture into return value.
    & $py.Source @a 2>&1 | ForEach-Object { Write-Host $_ }
    if ($LASTEXITCODE -ne 0) { throw "Prepare-X64Workspace failed ($LASTEXITCODE)" }
    if (-not (Test-Path (Join-Path $ws "Transcendence\Transcendence.sln"))) {
        throw "Workspace missing Transcendence.sln: $ws"
    }
    return $ws
}

function Invoke-ApiBuild {
    param(
        [string]$Solution,
        [string]$MsBuild,
        [string]$Configuration,
        [string]$Platform,
        [string]$Toolset,
        [switch]$DryRun
    )

    # Steam* configs: build the .sln so JPEG/zlib ActiveCfg remaps apply
    # (LibJPEG has no SteamRelease|x64; sln maps it to Release|x64).
    # Other configs: build the game vcxproj (avoids MSB4057 with /t: names).
    $gameProj = Join-Path (Split-Path $Solution -Parent) "Transcendence\Transcendence.vcxproj"
    $compilerProj = Join-Path (Split-Path $Solution -Parent) "TransCompiler\TransCompiler.vcxproj"
    if (-not (Test-Path $gameProj)) {
        throw "Transcendence.vcxproj not found next to solution: $gameProj"
    }

    $useSolution = ($Configuration -match '(?i)^Steam')
    $buildRoot = if ($useSolution) { $Solution } else { $gameProj }

    $msArgs = @(
        $buildRoot,
        "/p:Configuration=$Configuration",
        "/p:Platform=$Platform",
        "/p:LanguageStandard=stdcpp20",
        "/p:TreatWarningAsError=false",
        "/m",
        "/v:minimal",
        "/nologo"
    )
    if ($Toolset -and $Platform -ne "x64") {
        $msArgs += "/p:PlatformToolset=$Toolset"
    }

    Write-Host "MSBuild: $MsBuild" -ForegroundColor Gray
    Write-Host "Target:  $buildRoot" -ForegroundColor Gray
    Write-Host ("Config: {0} | {1} | toolset {2}" -f $Configuration, $Platform, $Toolset) -ForegroundColor Gray
    Write-Host ""

    if ($DryRun) {
        Write-Host ("[DryRun] Would run: msbuild {0}" -f ($msArgs -join ' ')) -ForegroundColor Yellow
        return $true
    }

    $log = Join-Path $env:TEMP ("tx_api_build_{0:yyyyMMdd_HHmmss}.log" -f (Get-Date))
    Write-Host ("Running: {0} {1}" -f $MsBuild, ($msArgs -join ' ')) -ForegroundColor DarkGray

    $oldEap = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        & $MsBuild @msArgs 2>&1 | Tee-Object -FilePath $log | ForEach-Object {
            $line = "$_"
            if ($line -match "error ") { Write-Host $line -ForegroundColor Red }
            elseif ($line -match "warning ") { Write-Host $line -ForegroundColor DarkYellow }
            else { Write-Host $line }
        }
        $code = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $oldEap
    }

    if ($null -eq $code) { $code = 1 }
    # TransCompiler when building game vcxproj only (solution build already includes it if mapped)
    if ($code -eq 0 -and -not $useSolution -and (Test-Path $compilerProj)) {
        Write-Host "Building TransCompiler..." -ForegroundColor Gray
        $cArgs = @(
            $compilerProj,
            "/p:Configuration=$Configuration",
            "/p:Platform=$Platform",
            "/p:LanguageStandard=stdcpp20",
            "/p:TreatWarningAsError=false",
            "/m",
            "/v:minimal",
            "/nologo"
        )
        & $MsBuild @cArgs 2>&1 | Tee-Object -FilePath $log -Append | ForEach-Object {
            $line = "$_"
            if ($line -match "error ") { Write-Host $line -ForegroundColor Red }
            elseif ($line -match "warning ") { Write-Host $line -ForegroundColor DarkYellow }
            else { Write-Host $line }
        }
        if ($LASTEXITCODE -ne 0) {
            Write-Host "TransCompiler build failed (game exe may still be usable)" -ForegroundColor Yellow
        }
    }

    Write-Host ""
    Write-Host "Build log: $log" -ForegroundColor Gray
    return ($code -eq 0)
}

function Deploy-BuiltExe {
    param(
        [string]$ApiGameDir,
        [string]$ApiFolder,
        [string]$DestRoot,
        [string]$Platform = "x64",
        [string]$Configuration = "Debug For Contributors",
        [switch]$DeployTools,
        [switch]$DisableSteamApi,
        [switch]$DryRun
    )

    $srcExe = Join-Path $ApiGameDir "Transcendence.exe"
    if (-not (Test-Path $srcExe)) {
        throw "Built exe not found: $srcExe - build may have failed or OutDir differs."
    }

    $bakRoot = Join-Path $DestRoot "Tools\Transcendence\_ext_fix_backups\api_switch_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
    $files = @("Transcendence.exe", "zlib1.dll", "Transcendence.pdb")
    if ($DeployTools) {
        $files += @("TransCompiler.exe", "TransData.exe")
    }

    # TransCompiler often lands under Transcendence\x64\<Config>\ rather than Game\
    $toolCandidates = @()
    if ($ApiFolder) {
        $toolCandidates += @(
            (Join-Path $ApiFolder "Transcendence\Game"),
            (Join-Path $ApiFolder ("Transcendence\{0}\{1}" -f $Platform, $Configuration)),
            (Join-Path $ApiFolder ("Transcendence\x64\{0}" -f $Configuration))
        )
    }
    $toolCandidates += @($ApiGameDir)

    New-Item -ItemType Directory -Force -Path $bakRoot | Out-Null
    foreach ($name in $files) {
        $src = $null
        if ($name -in @("TransCompiler.exe", "TransData.exe")) {
            foreach ($dir in $toolCandidates) {
                $cand = Join-Path $dir $name
                if (Test-Path $cand) { $src = $cand; break }
            }
        } else {
            $src = Join-Path $ApiGameDir $name
            if (-not (Test-Path $src) -and $name -eq "zlib1.dll") {
                # Fall back to Alchemy/zlib runtime if Game copy missing
                $z = Join-Path $ApiFolder "Alchemy\zlib-1.2.7\zlib1.dll"
                if (Test-Path $z) { $src = $z }
            }
        }
        $dst = Join-Path $DestRoot $name
        if (-not $src -or -not (Test-Path $src)) {
            if ($name -eq "Transcendence.pdb") { continue }
            Write-Host "  skip missing build output: $name" -ForegroundColor DarkYellow
            continue
        }
        if (Test-Path $dst) {
            Copy-Item -Force $dst (Join-Path $bakRoot $name)
            Write-Host "  backup $name -> $bakRoot" -ForegroundColor Gray
        }
        if ($DryRun) {
            Write-Host "  [DryRun] Would copy $src -> $dst" -ForegroundColor Yellow
        } else {
            Copy-Item -Force $src $dst
            $item = Get-Item $dst
            Write-Host "  deployed $name ($([math]::Round($item.Length/1MB,1)) MB, $($item.LastWriteTime))" -ForegroundColor Green
        }
    }

    if ($DisableSteamApi -and -not $DryRun) {
        $steam = Join-Path $DestRoot "steam_api.dll"
        $disabled = Join-Path $DestRoot "steam_api.dll.steam_disabled"
        if (Test-Path $steam) {
            Move-Item -Force $steam $disabled
            Write-Host "  disabled SteamAPI -> steam_api.dll.steam_disabled" -ForegroundColor Yellow
        }
        $steam64 = Join-Path $DestRoot "steam_api64.dll"
        $disabled64 = Join-Path $DestRoot "steam_api64.dll.steam_disabled"
        if (Test-Path $steam64) {
            Move-Item -Force $steam64 $disabled64
            Write-Host "  disabled SteamAPI64 -> steam_api64.dll.steam_disabled" -ForegroundColor Yellow
        }
    } elseif (-not $DryRun) {
        # x64 Multiverse needs steam_api64.dll next to the exe (stock Steam ship is often 32-bit steam_api.dll only)
        $sdk64 = Join-Path $ApiFolder "Mammoth\SteamUtil\steam\lib\win64\steam_api64.dll"
        $dst64 = Join-Path $DestRoot "steam_api64.dll"
        if (Test-Path $sdk64) {
            Copy-Item -Force $sdk64 $dst64
            Write-Host "  deployed steam_api64.dll (x64 Steam Multiverse)" -ForegroundColor Green
        } else {
            Write-Host "  warn: steam_api64.dll missing under SteamUtil SDK - Multiverse Steam login will fail" -ForegroundColor Yellow
        }
        # Re-enable previously disabled Steam DLLs
        foreach ($pair in @(
            @("steam_api.dll.steam_disabled", "steam_api.dll"),
            @("steam_api64.dll.steam_disabled", "steam_api64.dll")
        )) {
            $dis = Join-Path $DestRoot $pair[0]
            $en = Join-Path $DestRoot $pair[1]
            if ((Test-Path $dis) -and -not (Test-Path $en)) {
                Move-Item -Force $dis $en
                Write-Host "  restored $($pair[1])" -ForegroundColor Green
            }
        }
    }
    return $bakRoot
}

function Show-Status($cfg, $trees) {
    Write-Header "Transcendence API Switcher - Status"
    $game = Get-CurrentGameInfo $cfg.GameRoot
    Write-Host "Game root: $($cfg.GameRoot)"
    if ($game.Exists) {
        Write-Host "Current exe: $($game.ProductVersion) / $($game.FileVersion)"
        Write-Host "  $($game.ExePath)"
        Write-Host "  Modified: $($game.Modified)  Size: $($game.Length)"
    } else {
        Write-Host "Current exe: (missing)" -ForegroundColor Yellow
    }
    Write-Host "Active API (config): $($cfg.ActiveApi)  $($cfg.ActiveApiFolder)"
    Write-Host "Last configuration: $($cfg.LastConfiguration)"
    Write-Host ""
    Write-Host "Available API trees:" -ForegroundColor Cyan
    if (-not $trees -or $trees.Count -eq 0) {
        Write-Host "  (none found - place TranscendenceDev-integration-APIxx under game_and_dlc_source)" -ForegroundColor Yellow
        return
    }
    foreach ($t in $trees) {
        $mark = if ($cfg.ActiveApiFolder -and ($t.Path -eq $cfg.ActiveApiFolder)) { "*" } else { " " }
        Write-Host ("  {0} API {1,-3}  {2}" -f $mark, $t.Api, $t.Name)
        Write-Host ("           {0}" -f $t.Path) -ForegroundColor DarkGray
    }
}

function Select-ApiTreeInteractive($trees) {
    if (-not $trees -or $trees.Count -eq 0) {
        throw "No TranscendenceDev-integration-API* trees with Transcendence\Transcendence.sln found."
    }
    Write-Header "Select API to compile & deploy"
    for ($i = 0; $i -lt $trees.Count; $i++) {
        $t = $trees[$i]
        Write-Host ("  [{0}] API {1}  {2}" -f ($i + 1), $t.Api, $t.Name)
        Write-Host ("       {0}" -f $t.Path) -ForegroundColor DarkGray
    }
    Write-Host ""
    $choice = Read-Host "Enter number (1-$($trees.Count)), or API version (e.g. 59)"
    if ($choice -match '^\d+$') {
        $n = [int]$choice
        if ($n -ge 1 -and $n -le $trees.Count) { return $trees[$n - 1] }
        $byApi = @($trees | Where-Object { $_.Api -eq $n })
        if ($byApi.Count -eq 1) { return $byApi[0] }
        if ($byApi.Count -gt 1) {
            Write-Host "Multiple trees for API $n - pick by index instead." -ForegroundColor Yellow
            return Select-ApiTreeInteractive $byApi
        }
    }
    throw "Invalid selection: $choice"
}

# ============================================================
# Main
# ============================================================

$cfg = Get-ApiSwitcherConfig
if ($GameRoot -and $GameRoot -ne $cfg.GameRoot) { $cfg.GameRoot = $GameRoot }

$trees = Find-ApiTrees $cfg

if ($List -or $Status) {
    Show-Status $cfg $trees
    exit 0
}

# Resolve target tree
$target = $null
if ($ApiFolder) {
    $ApiFolder = [IO.Path]::GetFullPath($ApiFolder.Trim('"', "'"))
    if (-not (Test-Path $ApiFolder)) { throw "ApiFolder not found: $ApiFolder" }
    $sln = Join-Path $ApiFolder "Transcendence\Transcendence.sln"
    if (-not (Test-Path $sln)) { throw "Missing Transcendence\Transcendence.sln under $ApiFolder" }
    $target = [pscustomobject]@{
        Name = Split-Path $ApiFolder -Leaf
        Path = $ApiFolder
        Api = (Get-ApiVersionFromTree $ApiFolder)
        Solution = $sln
        GameDir = Join-Path $ApiFolder "Transcendence\Game"
    }
}
elseif ($Api -gt 0) {
    $matches = @($trees | Where-Object { $_.Api -eq $Api })
    if ($matches.Count -eq 0) {
        throw "No API $Api tree found. Use -List to see available folders (e.g. TranscendenceDev-integration-API59)."
    }
    if ($matches.Count -gt 1) {
        Write-Host "Multiple API $Api trees; using first:" -ForegroundColor Yellow
        $matches | ForEach-Object { Write-Host "  $($_.Path)" }
    }
    $target = $matches[0]
}
elseif ($NonInteractive) {
    if ($cfg.ActiveApiFolder -and (Test-Path $cfg.ActiveApiFolder)) {
        $ApiFolder = $cfg.ActiveApiFolder
        $target = [pscustomobject]@{
            Name = Split-Path $ApiFolder -Leaf
            Path = $ApiFolder
            Api = (Get-ApiVersionFromTree $ApiFolder)
            Solution = (Join-Path $ApiFolder "Transcendence\Transcendence.sln")
            GameDir = Join-Path $ApiFolder "Transcendence\Game"
        }
    } else {
        throw "NonInteractive requires -Api, -ApiFolder, or a saved ActiveApiFolder."
    }
}
else {
    Show-Status $cfg $trees
    $target = Select-ApiTreeInteractive $trees
}

Write-Header "Switch -> API $($target.Api) ($($target.Name))"
Write-Host "Official: $($target.Path)"
Write-Host "Configuration: $Configuration | $Platform"
Write-Host ""

$vs = Find-MSBuild -PreferVS2026:$UseVS2026 -ConfiguredPath $cfg.VisualStudioPath
if (-not $vs) {
    throw "MSBuild / Visual Studio not found. Install VS 2022+ with C++ workload, or set VisualStudioPath in ApiSwitcher.config.json"
}
Write-Host "Visual Studio: $($vs.VsPath)" -ForegroundColor Gray
$toolset = Get-BestToolset $vs.VsPath

# Optional: reuse CompileApiFolder SDK check lightly
if (-not $SkipSdkCheck) {
    $kits = "C:\Program Files (x86)\Windows Kits\10\Include"
    if (Test-Path $kits) {
        Write-Host "Windows SDK: found under $kits" -ForegroundColor Gray
    } else {
        Write-Host "Warning: Windows Kits Include not found - build may fail" -ForegroundColor Yellow
    }
}

# x64 default: patch/build in an isolated workspace so official trees stay clean.
$officialPath = $target.Path
if ($Platform -eq "x64" -and -not $PSBoundParameters.ContainsKey("UseX64Workspace")) {
    $UseX64Workspace = $true
}

$buildRoot = $officialPath
if ($UseX64Workspace -and $Platform -eq "x64") {
    $ws = Invoke-PrepareX64Workspace -OfficialApiFolder $officialPath `
        -Sync:$SyncX64Workspace -ApplyFixes:$false -Force:$ForceX64Autofix -DryRun:$DryRun
    $buildRoot = $ws
    $target = [pscustomobject]@{
        Name     = $target.Name
        Path     = $ws
        Api      = $target.Api
        Solution = (Join-Path $ws "Transcendence\Transcendence.sln")
        GameDir  = (Join-Path $ws "Transcendence\Game")
        Official = $officialPath
    }
    Write-Host "Build root (workspace): $($target.Path)" -ForegroundColor Cyan
} else {
    $target | Add-Member -NotePropertyName Official -NotePropertyValue $officialPath -Force
    Write-Host "Build root (direct): $($target.Path)" -ForegroundColor Yellow
}

$sdkPath = ""
if ($cfg.SteamworksSdk) { $sdkPath = [string]$cfg.SteamworksSdk }
Invoke-ApiTreeAutofix -ApiFolder $target.Path -Platform $Platform `
    -SteamworksSdk $sdkPath `
    -SkipX64Autofix:$SkipX64Autofix -ForceX64Autofix:$ForceX64Autofix `
    -SkipSegmentedShipsAutofix:$SkipSegmentedShipsAutofix -ForceSegmentedShipsAutofix:$ForceSegmentedShipsAutofix `
    -SkipResizeApiAutofix:$SkipResizeApiAutofix -ForceResizeApiAutofix:$ForceResizeApiAutofix `
    -DryRun:$DryRun

$ok = Invoke-ApiBuild -Solution $target.Solution -MsBuild $vs.MsBuild `
    -Configuration $Configuration -Platform $Platform -Toolset $toolset -DryRun:$DryRun

if (-not $ok) {
    Write-Host ""
    Write-Host "Build FAILED." -ForegroundColor Red
    Write-Host "Tips:" -ForegroundColor Yellow
    Write-Host "  - Prefer -Configuration 'Debug For Contributors' for engine work" -ForegroundColor Gray
    Write-Host "  - Multiverse: Steam identity via steam_api64.dll; launch from Steam while logged in" -ForegroundColor Gray
    Write-Host "  - Hexarc username/password Multiverse needs HexarcKeys.h (not in public source)" -ForegroundColor Gray
    Write-Host "  - Pass -DisableSteamApi only to intentionally disable Multiverse/Steam" -ForegroundColor Gray
    Write-Host "  - Use -Platform x64 (default) for API59 64-bit client" -ForegroundColor Gray
    Write-Host "  - Try -UseVS2026 if you have VS 18 / C++20 tooling" -ForegroundColor Gray
    exit 1
}

Write-Host "Build succeeded." -ForegroundColor Green

$doDeploy = -not ($CompileOnly -or $NoDeploy)
if ($Deploy) { $doDeploy = $true }
# Default: disable SteamAPI for Contributors/engine builds (stops Steam overwriting).
# Keep Steam API enabled by default so Multiverse can work on custom builds.
# Pass -DisableSteamApi only for isolated smoke tests without Steam.
if (-not $PSBoundParameters.ContainsKey('DisableSteamApi')) {
    $DisableSteamApi = $false
}

if ($doDeploy) {
    Write-Host ""
    Write-Host "Deploying to $($cfg.GameRoot) ..." -ForegroundColor Cyan
    # Close running game if possible
    Get-Process Transcendence -ErrorAction SilentlyContinue | ForEach-Object {
        Write-Host "  Stopping running Transcendence (PID $($_.Id))..." -ForegroundColor Yellow
        if (-not $DryRun) { $_ | Stop-Process -Force }
    }
    $bak = Deploy-BuiltExe -ApiGameDir $target.GameDir -ApiFolder $target.Path `
        -DestRoot $cfg.GameRoot -Platform $Platform -Configuration $Configuration `
        -DeployTools:$DeployTools -DisableSteamApi:$DisableSteamApi -DryRun:$DryRun
    Write-Host "Deploy complete. Backup: $bak" -ForegroundColor Green

    # Smoke test: require text Debug.log (no SteamAPI)
    if (-not $DryRun) {
        Write-Host "Smoke-testing Transcendence.exe (no SteamAPI) ..." -ForegroundColor Cyan
        $exe = Join-Path $cfg.GameRoot "Transcendence.exe"
        $log = Join-Path $cfg.GameRoot "Debug.log"
        Remove-Item $log -Force -ErrorAction SilentlyContinue
        $p = Start-Process -FilePath $exe -WorkingDirectory $cfg.GameRoot -PassThru
        Start-Sleep -Seconds 15
        if (-not $p.HasExited) {
            Write-Host "Smoke OK: still running after 15s" -ForegroundColor Green
            Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
        } else {
            Write-Host "Smoke FAIL: exited $($p.ExitCode) after $([math]::Round(($p.ExitTime - $p.StartTime).TotalSeconds,1))s" -ForegroundColor Red
        }
        if (Test-Path $log) {
            $raw = Get-Content $log -Raw -ErrorAction SilentlyContinue
            if ($raw -match "Transcendence 2\.0") {
                Write-Host "Debug.log OK (text session)" -ForegroundColor Green
            } else {
                Write-Host "Debug.log WARN: not a normal text session (len=$($raw.Length))" -ForegroundColor Yellow
            }
        } else {
            Write-Host "Debug.log WARN: missing" -ForegroundColor Yellow
        }
    }
} else {
    Write-Host "Skipping deploy (-CompileOnly). Output: $($target.GameDir)\Transcendence.exe" -ForegroundColor Yellow
}

if ($CompileTdb -and -not $DryRun) {
    $tc = Join-Path $cfg.GameRoot "TransCompiler.exe"
    $coreXml = Join-Path $cfg.GameRoot "game_and_dlc_source\Transcendence_Source\Transcendence.xml"
    $outTdb = Join-Path $cfg.GameRoot "Transcendence.tdb"
    if ((Test-Path $tc) -and (Test-Path $coreXml)) {
        Write-Host ""
        Write-Host "Recompiling Transcendence.tdb ..." -ForegroundColor Cyan
        Push-Location $cfg.GameRoot
        try {
            & $tc "/input:`"$coreXml`"" "/output:`"$outTdb`"" "/digest"
            if ($LASTEXITCODE -eq 0) {
                Write-Host "Transcendence.tdb OK" -ForegroundColor Green
            } else {
                Write-Host "Transcendence.tdb compile failed (exit $LASTEXITCODE)" -ForegroundColor Red
            }
        } finally { Pop-Location }
    } else {
        Write-Host "Skip TDB compile (need TransCompiler.exe + Transcendence_Source)" -ForegroundColor Yellow
    }
}

# Persist official API path (not workspace)
$cfg.ActiveApiFolder = $officialPath
$cfg.ActiveApi = $target.Api
$cfg.LastConfiguration = $Configuration
$cfg.VisualStudioPath = $vs.VsPath
if (-not $DryRun) { Save-ApiSwitcherConfig $cfg }

Write-Host ""
Write-Host "Active API is now $($target.Api): $officialPath" -ForegroundColor Green
if ($UseX64Workspace -and $Platform -eq "x64") {
    Write-Host "x64 workspace: $($target.Path)" -ForegroundColor Cyan
}
$game = Get-CurrentGameInfo $cfg.GameRoot
if ($game.Exists) {
    Write-Host "Game exe: $($game.ProductVersion) ($($game.Modified))" -ForegroundColor Green
}
exit 0

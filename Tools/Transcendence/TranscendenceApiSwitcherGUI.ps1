<#
.SYNOPSIS
  GUI for Transcendence API Switcher — pick TranscendenceDev-integration-APIxx,
  compile Transcendence.exe, deploy to the game folder.

.EXAMPLE
  pwsh -STA -File .\TranscendenceApiSwitcherGUI.ps1
  .\TranscendenceApiSwitcherGUI.bat
#>

#Requires -Version 5.1

param(
    [string]$GameRoot = "D:\games\Steam\steamapps\common\Transcendence"
)

if ([Environment]::UserInteractive) {
    try {
        if ([Threading.Thread]::CurrentThread.GetApartmentState() -ne 'STA') {
            $argList = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-STA', '-File', $PSCommandPath) + $args
            Start-Process -FilePath (Get-Process -Id $PID).Path -ArgumentList $argList -Wait
            exit $LASTEXITCODE
        }
    } catch {}
}

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
[System.Windows.Forms.Application]::EnableVisualStyles()

$script:ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$script:SwitcherPs1 = Join-Path $script:ScriptDir "TranscendenceApiSwitcher.ps1"
$script:ConfigPath = Join-Path $script:ScriptDir "ApiSwitcher.config.json"
$script:Busy = $false
$script:Child = $null
$script:LogFile = $null

# Dot-source helpers (functions only — script returns early when dotsourced)
. $script:SwitcherPs1

function Append-Log {
    param([string]$Text, [System.Drawing.Color]$Color = [System.Drawing.Color]::Gainsboro)
    if (-not $script:txtLog -or $script:txtLog.IsDisposed) { return }
    if ($script:txtLog.InvokeRequired) {
        $script:txtLog.BeginInvoke([Action[string, System.Drawing.Color]] {
            param($t, $c) Append-Log $t $c
        }, $Text, $Color) | Out-Null
        return
    }
    $script:txtLog.SelectionStart = $script:txtLog.TextLength
    $script:txtLog.SelectionLength = 0
    $script:txtLog.SelectionColor = $Color
    $script:txtLog.AppendText($Text.TrimEnd() + "`r`n")
    $script:txtLog.ScrollToCaret()
}

function Get-GuiConfig {
    $cfg = Get-ApiSwitcherConfig
    if ($GameRoot) { $cfg.GameRoot = $GameRoot }
    return $cfg
}

function Refresh-Ui {
    $cfg = Get-GuiConfig
    $trees = @(Find-ApiTrees $cfg)
    $script:Trees = $trees

    $script:lstApis.Items.Clear()
    $selectedIndex = 0
    for ($i = 0; $i -lt $trees.Count; $i++) {
        $t = $trees[$i]
        $label = "API {0}  —  {1}" -f $t.Api, $t.Name
        [void]$script:lstApis.Items.Add($label)
        if ($cfg.ActiveApiFolder -and ($t.Path -eq $cfg.ActiveApiFolder)) {
            $selectedIndex = $i
        }
    }
    if ($trees.Count -gt 0) {
        $script:lstApis.SelectedIndex = $selectedIndex
        Update-SelectionDetails
    }

    $game = Get-CurrentGameInfo $cfg.GameRoot
    $active = if ($cfg.ActiveApi) { "API $($cfg.ActiveApi)" } else { "(none)" }
    $exeLine = if ($game.Exists) {
        "$($game.ProductVersion)  |  $($game.FileVersion)  |  $($game.Modified)"
    } else { "(Transcendence.exe missing)" }

    $script:lblGame.Text = "Game: $($cfg.GameRoot)"
    $script:lblExe.Text = "Installed exe: $exeLine"
    $script:lblActive.Text = "Configured active: $active"
    if ($cfg.LastConfiguration) {
        $idx = $script:cmbConfig.Items.IndexOf($cfg.LastConfiguration)
        if ($idx -ge 0) { $script:cmbConfig.SelectedIndex = $idx }
    }
}

function Get-SelectedTree {
    if ($script:lstApis.SelectedIndex -lt 0) { return $null }
    return $script:Trees[$script:lstApis.SelectedIndex]
}

function Update-SelectionDetails {
    $t = Get-SelectedTree
    if (-not $t) {
        $script:lblPath.Text = "Path: —"
        return
    }
    $script:lblPath.Text = "Path: $($t.Path)"
}

function Set-Busy([bool]$Busy) {
    $script:Busy = $Busy
    foreach ($c in @(
        $script:btnRefresh, $script:btnBrowse, $script:btnBuildDeploy,
        $script:btnCompileOnly, $script:btnOpenFolder, $script:lstApis,
        $script:cmbConfig, $script:cmbPlatform, $script:chkDeployTools,
        $script:chkCompileTdb, $script:chkUseVS2026, $script:chkDryRun,
        $script:chkSegmentedShips, $script:chkForceSegmentedShips,
        $script:chkResizeApi, $script:chkForceResizeApi, $script:chkForceX64
    )) {
        if ($c -and -not $c.IsDisposed) { $c.Enabled = -not $Busy }
    }
    $script:btnCancel.Enabled = $Busy
    $script:progress.Style = if ($Busy) {
        [System.Windows.Forms.ProgressBarStyle]::Marquee
    } else {
        [System.Windows.Forms.ProgressBarStyle]::Continuous
    }
    if (-not $Busy) { $script:progress.Value = 0 }
}

function Start-SwitcherJob {
    param(
        [Parameter(Mandatory)]$Tree,
        [switch]$CompileOnly
    )

    if ($script:Busy) { return }
    if (-not (Test-Path $script:SwitcherPs1)) {
        [System.Windows.Forms.MessageBox]::Show("Missing TranscendenceApiSwitcher.ps1", "API Switcher") | Out-Null
        return
    }

    $cfg = Get-GuiConfig
    $configName = [string]$script:cmbConfig.SelectedItem
    $platform = [string]$script:cmbPlatform.SelectedItem

    $argList = [System.Collections.Generic.List[string]]::new()
    $argList.Add('-NoProfile')
    $argList.Add('-ExecutionPolicy'); $argList.Add('Bypass')
    $argList.Add('-File'); $argList.Add($script:SwitcherPs1)
    $argList.Add('-ApiFolder'); $argList.Add($Tree.Path)
    $argList.Add('-Configuration'); $argList.Add($configName)
    $argList.Add('-Platform'); $argList.Add($platform)
    $argList.Add('-GameRoot'); $argList.Add($cfg.GameRoot)
    $argList.Add('-NonInteractive')
    if ($CompileOnly) { $argList.Add('-CompileOnly') }
    if ($script:chkDeployTools.Checked) { $argList.Add('-DeployTools') }
    if ($script:chkCompileTdb.Checked) { $argList.Add('-CompileTdb') }
    if ($script:chkUseVS2026.Checked) { $argList.Add('-UseVS2026') }
    if ($script:chkDryRun.Checked) { $argList.Add('-DryRun') }
    if (-not $script:chkSegmentedShips.Checked) { $argList.Add('-SkipSegmentedShipsAutofix') }
    if ($script:chkForceSegmentedShips.Checked) { $argList.Add('-ForceSegmentedShipsAutofix') }
    if (-not $script:chkResizeApi.Checked) { $argList.Add('-SkipResizeApiAutofix') }
    if ($script:chkForceResizeApi.Checked) { $argList.Add('-ForceResizeApiAutofix') }
    if ($script:chkForceX64.Checked) { $argList.Add('-ForceX64Autofix') }

    $script:LogFile = Join-Path $env:TEMP ("tx_api_gui_{0:yyyyMMdd_HHmmss}.log" -f (Get-Date))
    $errFile = "$($script:LogFile).err"
    Set-Content -Path $script:LogFile -Value "" -Encoding UTF8
    Set-Content -Path $errFile -Value "" -Encoding UTF8

    Append-Log "────────────────────────────────────────" ([System.Drawing.Color]::DeepSkyBlue)
    Append-Log "Starting: API $($Tree.Api) — $($Tree.Name)" ([System.Drawing.Color]::DeepSkyBlue)
    $displayArgs = foreach ($a in $argList) {
        if ($a -match '[\s"]') { '"' + ($a -replace '"', '`"') + '"' } else { $a }
    }
    Append-Log ($displayArgs -join ' ') ([System.Drawing.Color]::DimGray)

    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = (Get-Command pwsh).Source
    # ProcessStartInfo ArgumentList not on older .NET — use Arguments string carefully
    $quoted = foreach ($a in $argList) {
        if ($a -match '[\s"]') { '"' + ($a -replace '"', '\"') + '"' } else { $a }
    }
    $psi.Arguments = ($quoted -join ' ')
    $psi.UseShellExecute = $false
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.CreateNoWindow = $true
    $psi.WorkingDirectory = $cfg.GameRoot

    $proc = New-Object System.Diagnostics.Process
    $proc.StartInfo = $psi
    $proc.EnableRaisingEvents = $true

    $script:OutBuilder = New-Object System.Text.StringBuilder
    $handler = {
        if (-not [string]::IsNullOrEmpty($EventArgs.Data)) {
            $line = $EventArgs.Data
            $script:form.BeginInvoke([Action[string]] {
                param($l)
                $color = [System.Drawing.Color]::Gainsboro
                if ($l -match 'error|FAILED|Error:') { $color = [System.Drawing.Color]::Salmon }
                elseif ($l -match 'succeeded|OK|deployed|Active API') { $color = [System.Drawing.Color]::LightGreen }
                elseif ($l -match 'Warning') { $color = [System.Drawing.Color]::Khaki }
                Append-Log $l $color
            }, $line) | Out-Null
            Add-Content -Path $script:LogFile -Value $line -Encoding UTF8
        }
    }
    Register-ObjectEvent -InputObject $proc -EventName OutputDataReceived -Action $handler | Out-Null
    Register-ObjectEvent -InputObject $proc -EventName ErrorDataReceived -Action $handler | Out-Null

    Set-Busy $true
    [void]$proc.Start()
    $proc.BeginOutputReadLine()
    $proc.BeginErrorReadLine()
    $script:Child = $proc

    $script:timer.Tag = $proc
    $script:timer.Start()
}

function On-TimerTick {
    $proc = $script:Child
    if (-not $proc) { $script:timer.Stop(); Set-Busy $false; return }
    if (-not $proc.HasExited) { return }

    $script:timer.Stop()
    $code = $proc.ExitCode
    if ($null -eq $code) { $code = -1 }
    if ($code -eq 0) {
        Append-Log "Finished successfully (exit 0)." ([System.Drawing.Color]::LightGreen)
    } else {
        Append-Log "Finished with exit code $code." ([System.Drawing.Color]::Salmon)
        # Surface MSBuild errors if async stdout was empty/missed
        $buildLogs = @(Get-ChildItem -Path $env:TEMP -Filter "tx_api_build_*.log" -ErrorAction SilentlyContinue |
            Sort-Object LastWriteTime -Descending |
            Select-Object -First 1)
        if ($buildLogs) {
            $errLines = @(Get-Content -LiteralPath $buildLogs[0].FullName -ErrorAction SilentlyContinue |
                Where-Object { $_ -match 'error |FAILED|fatal error' } |
                Select-Object -Last 12)
            foreach ($el in $errLines) {
                Append-Log $el ([System.Drawing.Color]::Salmon)
            }
            Append-Log "Build log: $($buildLogs[0].FullName)" ([System.Drawing.Color]::DimGray)
        }
    }
    Append-Log "Log file: $($script:LogFile)" ([System.Drawing.Color]::DimGray)
    $script:Child = $null
    Set-Busy $false
    Refresh-Ui
    Get-EventSubscriber | Where-Object { $_.SourceObject -eq $proc } | Unregister-Event -Force -ErrorAction SilentlyContinue
}

# ============================================================
# Form layout
# ============================================================

$form = New-Object System.Windows.Forms.Form
$form.Text = "Transcendence API Switcher"
$form.Size = New-Object System.Drawing.Size(920, 680)
$form.StartPosition = "CenterScreen"
$form.MinimumSize = New-Object System.Drawing.Size(760, 520)
$form.BackColor = [System.Drawing.Color]::FromArgb(28, 30, 34)
$form.ForeColor = [System.Drawing.Color]::Gainsboro
$form.Font = New-Object System.Drawing.Font("Segoe UI", 9)

$panelTop = New-Object System.Windows.Forms.Panel
$panelTop.Dock = "Top"
$panelTop.Height = 210
$panelTop.Padding = New-Object System.Windows.Forms.Padding(12)
$panelTop.BackColor = [System.Drawing.Color]::FromArgb(36, 39, 44)

$lblTitle = New-Object System.Windows.Forms.Label
$lblTitle.Text = "API Switcher"
$lblTitle.Font = New-Object System.Drawing.Font("Segoe UI Semibold", 16)
$lblTitle.ForeColor = [System.Drawing.Color]::White
$lblTitle.Location = New-Object System.Drawing.Point(12, 10)
$lblTitle.AutoSize = $true

$lblSub = New-Object System.Windows.Forms.Label
$lblSub.Text = "Compile Transcendence.exe from TranscendenceDev-integration-APIxx and deploy"
$lblSub.ForeColor = [System.Drawing.Color]::Silver
$lblSub.Location = New-Object System.Drawing.Point(14, 42)
$lblSub.AutoSize = $true

$script:lblGame = New-Object System.Windows.Forms.Label
$script:lblGame.Location = New-Object System.Drawing.Point(14, 68)
$script:lblGame.Size = New-Object System.Drawing.Size(880, 18)
$script:lblGame.ForeColor = [System.Drawing.Color]::LightSteelBlue

$script:lblExe = New-Object System.Windows.Forms.Label
$script:lblExe.Location = New-Object System.Drawing.Point(14, 88)
$script:lblExe.Size = New-Object System.Drawing.Size(880, 18)

$script:lblActive = New-Object System.Windows.Forms.Label
$script:lblActive.Location = New-Object System.Drawing.Point(14, 108)
$script:lblActive.Size = New-Object System.Drawing.Size(880, 18)
$script:lblActive.ForeColor = [System.Drawing.Color]::MediumSpringGreen

$lblList = New-Object System.Windows.Forms.Label
$lblList.Text = "Available API trees"
$lblList.Location = New-Object System.Drawing.Point(14, 136)
$lblList.AutoSize = $true

$script:lstApis = New-Object System.Windows.Forms.ListBox
$script:lstApis.Location = New-Object System.Drawing.Point(14, 156)
$script:lstApis.Size = New-Object System.Drawing.Size(560, 44)
$script:lstApis.BackColor = [System.Drawing.Color]::FromArgb(22, 24, 28)
$script:lstApis.ForeColor = [System.Drawing.Color]::White
$script:lstApis.BorderStyle = "FixedSingle"
$script:lstApis.Add_SelectedIndexChanged({ Update-SelectionDetails })

$script:btnRefresh = New-Object System.Windows.Forms.Button
$script:btnRefresh.Text = "Refresh"
$script:btnRefresh.Location = New-Object System.Drawing.Point(590, 156)
$script:btnRefresh.Size = New-Object System.Drawing.Size(100, 28)
$script:btnRefresh.FlatStyle = "Flat"
$script:btnRefresh.Add_Click({ Refresh-Ui })

$script:btnBrowse = New-Object System.Windows.Forms.Button
$script:btnBrowse.Text = "Browse…"
$script:btnBrowse.Location = New-Object System.Drawing.Point(700, 156)
$script:btnBrowse.Size = New-Object System.Drawing.Size(100, 28)
$script:btnBrowse.FlatStyle = "Flat"
$script:btnBrowse.Add_Click({
    $dlg = New-Object System.Windows.Forms.FolderBrowserDialog
    $dlg.Description = "Select TranscendenceDev-integration-APIxx folder"
    $cfg = Get-GuiConfig
    $dlg.SelectedPath = Join-Path $cfg.GameRoot "game_and_dlc_source"
    if ($dlg.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) {
        $path = $dlg.SelectedPath
        $sln = Join-Path $path "Transcendence\Transcendence.sln"
        if (-not (Test-Path $sln)) {
            [System.Windows.Forms.MessageBox]::Show(
                "Folder must contain Transcendence\Transcendence.sln",
                "Invalid API folder") | Out-Null
            return
        }
        $tree = [pscustomobject]@{
            Name = Split-Path $path -Leaf
            Path = $path
            Api = (Get-ApiVersionFromTree $path)
            Solution = $sln
            GameDir = Join-Path $path "Transcendence\Game"
        }
        $script:Trees = @($tree) + @($script:Trees | Where-Object { $_.Path -ne $path })
        $script:lstApis.Items.Clear()
        foreach ($t in $script:Trees) {
            [void]$script:lstApis.Items.Add(("API {0}  —  {1}" -f $t.Api, $t.Name))
        }
        $script:lstApis.SelectedIndex = 0
        Append-Log "Added folder: $path" ([System.Drawing.Color]::LightSteelBlue)
    }
})

$script:btnOpenFolder = New-Object System.Windows.Forms.Button
$script:btnOpenFolder.Text = "Open folder"
$script:btnOpenFolder.Location = New-Object System.Drawing.Point(810, 156)
$script:btnOpenFolder.Size = New-Object System.Drawing.Size(80, 28)
$script:btnOpenFolder.FlatStyle = "Flat"
$script:btnOpenFolder.Add_Click({
    $t = Get-SelectedTree
    if ($t) { Start-Process explorer.exe $t.Path }
})

$panelTop.Controls.AddRange(@(
    $lblTitle, $lblSub, $script:lblGame, $script:lblExe, $script:lblActive,
    $lblList, $script:lstApis, $script:btnRefresh, $script:btnBrowse, $script:btnOpenFolder
))

$panelOpts = New-Object System.Windows.Forms.Panel
$panelOpts.Dock = "Top"
$panelOpts.Height = 196
$panelOpts.BackColor = [System.Drawing.Color]::FromArgb(32, 34, 38)

$script:lblPath = New-Object System.Windows.Forms.Label
$script:lblPath.Location = New-Object System.Drawing.Point(14, 8)
$script:lblPath.Size = New-Object System.Drawing.Size(880, 18)
$script:lblPath.ForeColor = [System.Drawing.Color]::DarkGray

$lblCfg = New-Object System.Windows.Forms.Label
$lblCfg.Text = "Configuration"
$lblCfg.Location = New-Object System.Drawing.Point(14, 36)
$lblCfg.AutoSize = $true

$script:cmbConfig = New-Object System.Windows.Forms.ComboBox
$script:cmbConfig.Location = New-Object System.Drawing.Point(110, 32)
$script:cmbConfig.Size = New-Object System.Drawing.Size(220, 24)
$script:cmbConfig.DropDownStyle = "DropDownList"
$script:cmbConfig.BackColor = [System.Drawing.Color]::FromArgb(22, 24, 28)
$script:cmbConfig.ForeColor = [System.Drawing.Color]::White
@(
    "Debug For Contributors",
    "Preview For Contributors",
    "Release",
    "Debug",
    "SteamRelease",
    "SteamDebug"
) | ForEach-Object { [void]$script:cmbConfig.Items.Add($_) }
$script:cmbConfig.SelectedIndex = 0

$lblPlat = New-Object System.Windows.Forms.Label
$lblPlat.Text = "Platform"
$lblPlat.Location = New-Object System.Drawing.Point(350, 36)
$lblPlat.AutoSize = $true

$script:cmbPlatform = New-Object System.Windows.Forms.ComboBox
$script:cmbPlatform.Location = New-Object System.Drawing.Point(420, 32)
$script:cmbPlatform.Size = New-Object System.Drawing.Size(90, 24)
$script:cmbPlatform.DropDownStyle = "DropDownList"
$script:cmbPlatform.BackColor = [System.Drawing.Color]::FromArgb(22, 24, 28)
$script:cmbPlatform.ForeColor = [System.Drawing.Color]::White
[void]$script:cmbPlatform.Items.Add("Win32")
[void]$script:cmbPlatform.Items.Add("x64")
$script:cmbPlatform.SelectedIndex = 1  # default x64 (runs Kernel INT_PTR autofix)

$script:chkDeployTools = New-Object System.Windows.Forms.CheckBox
$script:chkDeployTools.Text = "Deploy TransCompiler/TransData"
$script:chkDeployTools.Location = New-Object System.Drawing.Point(14, 68)
$script:chkDeployTools.AutoSize = $true
$script:chkDeployTools.ForeColor = [System.Drawing.Color]::Gainsboro

$script:chkCompileTdb = New-Object System.Windows.Forms.CheckBox
$script:chkCompileTdb.Text = "Rebuild Transcendence.tdb after deploy"
$script:chkCompileTdb.Location = New-Object System.Drawing.Point(250, 68)
$script:chkCompileTdb.AutoSize = $true

$script:chkUseVS2026 = New-Object System.Windows.Forms.CheckBox
$script:chkUseVS2026.Text = "Prefer VS 2026 / C++20"
$script:chkUseVS2026.Location = New-Object System.Drawing.Point(520, 68)
$script:chkUseVS2026.AutoSize = $true
$script:chkUseVS2026.Checked = $true

$script:chkDryRun = New-Object System.Windows.Forms.CheckBox
$script:chkDryRun.Text = "Dry run"
$script:chkDryRun.Location = New-Object System.Drawing.Point(720, 68)
$script:chkDryRun.AutoSize = $true

$script:chkSegmentedShips = New-Object System.Windows.Forms.CheckBox
$script:chkSegmentedShips.Text = "Segmented ships autofix (Space Whale / snake spine)"
$script:chkSegmentedShips.Location = New-Object System.Drawing.Point(14, 94)
$script:chkSegmentedShips.AutoSize = $true
$script:chkSegmentedShips.Checked = $true
$script:chkSegmentedShips.ForeColor = [System.Drawing.Color]::PaleTurquoise

$script:chkForceSegmentedShips = New-Object System.Windows.Forms.CheckBox
$script:chkForceSegmentedShips.Text = "Force re-apply"
$script:chkForceSegmentedShips.Location = New-Object System.Drawing.Point(400, 94)
$script:chkForceSegmentedShips.AutoSize = $true
$script:chkForceSegmentedShips.ForeColor = [System.Drawing.Color]::Gainsboro

$script:chkForceX64 = New-Object System.Windows.Forms.CheckBox
$script:chkForceX64.Text = "Force x64 autofix"
$script:chkForceX64.Location = New-Object System.Drawing.Point(520, 94)
$script:chkForceX64.AutoSize = $true
$script:chkForceX64.ForeColor = [System.Drawing.Color]::Gainsboro

$script:chkResizeApi = New-Object System.Windows.Forms.CheckBox
$script:chkResizeApi.Text = "Resize API autofix (objSetVisualScale / paint scale)"
$script:chkResizeApi.Location = New-Object System.Drawing.Point(14, 118)
$script:chkResizeApi.AutoSize = $true
$script:chkResizeApi.Checked = $true
$script:chkResizeApi.ForeColor = [System.Drawing.Color]::PaleTurquoise

$script:chkForceResizeApi = New-Object System.Windows.Forms.CheckBox
$script:chkForceResizeApi.Text = "Force re-apply"
$script:chkForceResizeApi.Location = New-Object System.Drawing.Point(400, 118)
$script:chkForceResizeApi.AutoSize = $true
$script:chkForceResizeApi.ForeColor = [System.Drawing.Color]::Gainsboro

$script:btnBuildDeploy = New-Object System.Windows.Forms.Button
$script:btnBuildDeploy.Text = "Build + Deploy"
$script:btnBuildDeploy.Location = New-Object System.Drawing.Point(14, 150)
$script:btnBuildDeploy.Size = New-Object System.Drawing.Size(140, 32)
$script:btnBuildDeploy.FlatStyle = "Flat"
$script:btnBuildDeploy.BackColor = [System.Drawing.Color]::FromArgb(40, 120, 80)
$script:btnBuildDeploy.ForeColor = [System.Drawing.Color]::White
$script:btnBuildDeploy.Add_Click({
    $t = Get-SelectedTree
    if (-not $t) {
        [System.Windows.Forms.MessageBox]::Show("Select an API tree first.") | Out-Null
        return
    }
    Start-SwitcherJob -Tree $t
})

$script:btnCompileOnly = New-Object System.Windows.Forms.Button
$script:btnCompileOnly.Text = "Compile only"
$script:btnCompileOnly.Location = New-Object System.Drawing.Point(164, 150)
$script:btnCompileOnly.Size = New-Object System.Drawing.Size(120, 32)
$script:btnCompileOnly.FlatStyle = "Flat"
$script:btnCompileOnly.BackColor = [System.Drawing.Color]::FromArgb(50, 70, 110)
$script:btnCompileOnly.ForeColor = [System.Drawing.Color]::White
$script:btnCompileOnly.Add_Click({
    $t = Get-SelectedTree
    if (-not $t) { return }
    Start-SwitcherJob -Tree $t -CompileOnly
})

$script:btnCancel = New-Object System.Windows.Forms.Button
$script:btnCancel.Text = "Cancel"
$script:btnCancel.Location = New-Object System.Drawing.Point(294, 150)
$script:btnCancel.Size = New-Object System.Drawing.Size(90, 32)
$script:btnCancel.FlatStyle = "Flat"
$script:btnCancel.Enabled = $false
$script:btnCancel.Add_Click({
    if ($script:Child -and -not $script:Child.HasExited) {
        try { $script:Child.Kill() } catch {}
        Append-Log "Cancelled by user." ([System.Drawing.Color]::Khaki)
    }
})

$script:progress = New-Object System.Windows.Forms.ProgressBar
$script:progress.Location = New-Object System.Drawing.Point(400, 156)
$script:progress.Size = New-Object System.Drawing.Size(490, 20)

$panelOpts.Controls.AddRange(@(
    $script:lblPath, $lblCfg, $script:cmbConfig, $lblPlat, $script:cmbPlatform,
    $script:chkDeployTools, $script:chkCompileTdb, $script:chkUseVS2026, $script:chkDryRun,
    $script:chkSegmentedShips, $script:chkForceSegmentedShips, $script:chkForceX64,
    $script:chkResizeApi, $script:chkForceResizeApi,
    $script:btnBuildDeploy, $script:btnCompileOnly, $script:btnCancel, $script:progress
))

$script:txtLog = New-Object System.Windows.Forms.RichTextBox
$script:txtLog.Dock = "Fill"
$script:txtLog.ReadOnly = $true
$script:txtLog.BackColor = [System.Drawing.Color]::FromArgb(18, 19, 22)
$script:txtLog.ForeColor = [System.Drawing.Color]::Gainsboro
$script:txtLog.Font = New-Object System.Drawing.Font("Consolas", 9)
$script:txtLog.BorderStyle = "None"

$script:timer = New-Object System.Windows.Forms.Timer
$script:timer.Interval = 500
$script:timer.Add_Tick({ On-TimerTick })

$form.Controls.Add($script:txtLog)
$form.Controls.Add($panelOpts)
$form.Controls.Add($panelTop)

$form.Add_Shown({
    Append-Log "Transcendence API Switcher GUI ready." ([System.Drawing.Color]::LightSteelBlue)
    Append-Log "Segmented ships autofix enables objAttachShipSection for Space Whale / snake ships." ([System.Drawing.Color]::PaleTurquoise)
    Append-Log "Resize API autofix enables objSetVisualScale for CrossMod ResizeAPI.xml." ([System.Drawing.Color]::PaleTurquoise)
    Refresh-Ui
})

$form.Add_FormClosing({
    if ($script:Child -and -not $script:Child.HasExited) {
        try { $script:Child.Kill() } catch {}
    }
    $script:timer.Stop()
})

$script:form = $form
[void]$form.ShowDialog()

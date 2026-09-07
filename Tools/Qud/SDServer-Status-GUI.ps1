# SDServer-Status-GUI.ps1
# Live status for the local SD3.5 API server (:1338) - use with any generate/start bat.
#
# Usage:
#   powershell -STA -File SDServer-Status-GUI.ps1
#   SDServer-Status-GUI.bat
#   SDServer-Status-GUI.bat -StartServer

param(
    [switch]$StartServer
)

$ErrorActionPreference = "Stop"
$crashLog = Join-Path $env:TEMP "sd_status_gui_crash.log"
$WindowTitle = "SD Server Status - :1338"

function Write-Crash([string]$msg) {
    try {
        "$(Get-Date -Format o) $msg" | Out-File -FilePath $crashLog -Append -Encoding utf8
    } catch {}
}

# Re-launch only when not STA (Open-SDStatusGui already uses Hidden+STA)
if ([System.Threading.Thread]::CurrentThread.GetApartmentState() -ne [System.Threading.ApartmentState]::STA) {
    $argList = @(
        "-STA",
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-WindowStyle", "Hidden",
        "-File", $MyInvocation.MyCommand.Path
    )
    if ($StartServer) { $argList += "-StartServer" }
    Start-Process -FilePath "powershell.exe" -ArgumentList $argList -WindowStyle Hidden | Out-Null
    exit 0
}

try {
Add-Type -AssemblyName System.Windows.Forms, System.Drawing -ErrorAction Stop
[System.Windows.Forms.Application]::EnableVisualStyles()

# Single-instance via window title (no sticky mutex flash-exit)
try {
    Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class SdGuiNative {
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
  [DllImport("user32.dll")] public static extern bool IsIconic(IntPtr hWnd);
}
"@ -ErrorAction SilentlyContinue
    $existing = Get-Process -ErrorAction SilentlyContinue | Where-Object {
        $_.MainWindowTitle -eq $WindowTitle -and $_.Id -ne $PID -and $_.MainWindowHandle -ne [IntPtr]::Zero
    } | Select-Object -First 1
    if ($existing) {
        $hwnd = $existing.MainWindowHandle
        if ([SdGuiNative]::IsIconic($hwnd)) { [SdGuiNative]::ShowWindow($hwnd, 9) | Out-Null }
        else { [SdGuiNative]::ShowWindow($hwnd, 5) | Out-Null }
        [SdGuiNative]::SetForegroundWindow($hwnd) | Out-Null
        exit 0
    }
} catch {}

$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$toolsRoot = Split-Path $here -Parent
$startPs = Join-Path $toolsRoot "Start-StableDiffusionServer.ps1"
$sdRoot = "E:\tools\sd3.5\sd3.5"
$outLog = Join-Path $sdRoot "sd_server.out.log"
$errLog = Join-Path $sdRoot "sd_server.err.log"
$pingUrl = "http://127.0.0.1:1338/ping"

function Get-SdPing {
    try {
        $resp = Invoke-WebRequest -Uri $pingUrl -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
        return @{ Ok = $true; Json = ($resp.Content | ConvertFrom-Json); Raw = $resp.Content }
    } catch {
        return @{ Ok = $false; Json = $null; Raw = $_.Exception.Message }
    }
}

function Get-LogTail([string]$path, [int]$lines = 80) {
    if (-not (Test-Path -LiteralPath $path)) { return "(log not found: $path)" }
    try {
        return (Get-Content -LiteralPath $path -Tail $lines -ErrorAction Stop) -join "`r`n"
    } catch {
        return "(could not read log: $($_.Exception.Message))"
    }
}

function Append-UiLog([string]$msg) {
    $ts = Get-Date -Format "HH:mm:ss"
    $boxLog.AppendText("[$ts] $msg`r`n")
    $boxLog.SelectionStart = $boxLog.TextLength
    $boxLog.ScrollToCaret()
}

$form = New-Object Windows.Forms.Form
$form.Text = $WindowTitle
$form.Size = New-Object Drawing.Size(920, 720)
$form.StartPosition = "CenterScreen"
$form.MinimumSize = New-Object Drawing.Size(720, 520)
$form.Font = New-Object Drawing.Font("Segoe UI", 9)

$pnlTop = New-Object Windows.Forms.Panel
$pnlTop.Dock = "Top"
$pnlTop.Height = 118
$pnlTop.BackColor = [Drawing.Color]::FromArgb(32, 36, 40)

$lblBig = New-Object Windows.Forms.Label
$lblBig.Text = "CHECKING..."
$lblBig.ForeColor = [Drawing.Color]::Gold
$lblBig.Font = New-Object Drawing.Font("Segoe UI Semibold", 22)
$lblBig.Location = New-Object Drawing.Point(16, 12)
$lblBig.AutoSize = $true
$pnlTop.Controls.Add($lblBig)

$lblDetail = New-Object Windows.Forms.Label
$lblDetail.Text = "Polling http://127.0.0.1:1338/ping"
$lblDetail.ForeColor = [Drawing.Color]::Gainsboro
$lblDetail.Location = New-Object Drawing.Point(18, 54)
$lblDetail.Size = New-Object Drawing.Size(870, 50)
$pnlTop.Controls.Add($lblDetail)

$pnlBtn = New-Object Windows.Forms.FlowLayoutPanel
$pnlBtn.Dock = "Top"
$pnlBtn.Height = 44
$pnlBtn.Padding = New-Object Windows.Forms.Padding(8, 6, 8, 6)

function New-Btn([string]$text, [int]$w = 110) {
    $b = New-Object Windows.Forms.Button
    $b.Text = $text
    $b.Width = $w
    $b.Height = 30
    $pnlBtn.Controls.Add($b)
    return $b
}

$btnStart = New-Btn "Start SD" 100
$btnForce = New-Btn "Force Restart" 110
$btnRefresh = New-Btn "Refresh" 90
$btnLogs = New-Btn "Open Log Folder" 120
$btnCopy = New-Btn "Copy /ping JSON" 120
$chkAuto = New-Object Windows.Forms.CheckBox
$chkAuto.Text = "Auto-refresh 1s"
$chkAuto.Checked = $true
$chkAuto.AutoSize = $true
$chkAuto.Margin = New-Object Windows.Forms.Padding(12, 6, 0, 0)
$pnlBtn.Controls.Add($chkAuto)

$split = New-Object Windows.Forms.SplitContainer
$split.Dock = "Fill"
$split.Orientation = "Horizontal"
$split.SplitterDistance = 160

# Dock order: Fill first, then Top panels (last Top = topmost visually)
$form.Controls.Add($split)
$form.Controls.Add($pnlBtn)
$form.Controls.Add($pnlTop)

$grid = New-Object Windows.Forms.DataGridView
$grid.Dock = "Fill"
$grid.ReadOnly = $true
$grid.AllowUserToAddRows = $false
$grid.AllowUserToDeleteRows = $false
$grid.RowHeadersVisible = $false
$grid.SelectionMode = "FullRowSelect"
$grid.AutoSizeColumnsMode = "Fill"
$grid.BackgroundColor = [Drawing.Color]::White
[void]$grid.Columns.Add("Key", "Key")
[void]$grid.Columns.Add("Value", "Value")
$grid.Columns[0].FillWeight = 35
$grid.Columns[1].FillWeight = 65
$split.Panel1.Controls.Add($grid)

$tabs = New-Object Windows.Forms.TabControl
$tabs.Dock = "Fill"
$split.Panel2.Controls.Add($tabs)

function New-LogTab([string]$title) {
    $tab = New-Object Windows.Forms.TabPage
    $tab.Text = $title
    $box = New-Object Windows.Forms.TextBox
    $box.Multiline = $true
    $box.ScrollBars = "Both"
    $box.Dock = "Fill"
    $box.Font = New-Object Drawing.Font("Consolas", 9)
    $box.ReadOnly = $true
    $box.WordWrap = $false
    $tab.Controls.Add($box)
    [void]$tabs.TabPages.Add($tab)
    return $box
}

$boxOut = New-LogTab "sd_server.out.log"
$boxErr = New-LogTab "sd_server.err.log"
$boxLog = New-LogTab "GUI / jobs"

$status = New-Object Windows.Forms.StatusStrip
$statLabel = New-Object Windows.Forms.ToolStripStatusLabel
$statLabel.Spring = $true
$statLabel.TextAlign = "MiddleLeft"
$statLabel.Text = "Ready."
[void]$status.Items.Add($statLabel)
$form.Controls.Add($status)

$script:lastOutLen = -1
$script:lastErrLen = -1
$script:starting = $false

function Set-GridFromPing($ping) {
    $grid.Rows.Clear()
    if (-not $ping.Ok -or -not $ping.Json) {
        [void]$grid.Rows.Add("reachable", "no")
        [void]$grid.Rows.Add("error", $ping.Raw)
        return
    }
    $j = $ping.Json
    foreach ($name in @(
        "status", "model_state", "ready", "model", "version",
        "offload", "offload_policy", "gpu_free_gb", "gpu_total_gb",
        "rebalance", "headroom_gb", "max_sequence_length", "safety_checker"
    )) {
        $val = $j.PSObject.Properties[$name]
        if ($null -ne $val) { [void]$grid.Rows.Add($name, [string]$val.Value) }
    }
}

function Update-StatusUi {
    # Never let a poll/format/log glitch tear down the WinForms message loop.
    try {
        $ping = Get-SdPing
        Set-GridFromPing $ping

        if (-not $ping.Ok) {
            $lblBig.Text = "DOWN"
            $lblBig.ForeColor = [Drawing.Color]::Salmon
            $lblDetail.Text = "No response on :1338 - Start SD or wait for pipeline boot.`r`n$($ping.Raw)"
            $statLabel.Text = "SD down | $(Get-Date -Format 'HH:mm:ss')"
        } else {
            $j = $ping.Json
            $state = [string]$j.model_state
            $ready = [bool]$j.ready
            if ($state -eq "ready" -and $ready) {
                $lblBig.Text = "READY"
                $lblBig.ForeColor = [Drawing.Color]::LightGreen
            } elseif ($state -eq "loading" -or -not $ready) {
                $lblBig.Text = "LOADING..."
                $lblBig.ForeColor = [Drawing.Color]::Gold
            } elseif ($state -eq "error") {
                $lblBig.Text = "ERROR"
                $lblBig.ForeColor = [Drawing.Color]::OrangeRed
            } else {
                $lblBig.Text = ($(if ($state) { $state.ToUpperInvariant() } else { "UNKNOWN" }))
                $lblBig.ForeColor = [Drawing.Color]::Khaki
            }
            $freeGb = if ($null -ne $j.gpu_free_gb) { [double]$j.gpu_free_gb } else { 0.0 }
            $totalGb = if ($null -ne $j.gpu_total_gb) { [double]$j.gpu_total_gb } else { 0.0 }
            $off = [string]$j.offload
            $hint = if ($off -eq "gpu") {
                "CUDA util spikes only while generating (Task Manager: GPU -> Cuda, not 3D)"
            } elseif ($off -in @("model", "sequential", "shared")) {
                "CPU-offload active: weights in RAM, modules shuttle to VRAM — expect CPU + low average GPU%"
            } else { "" }
            $lblDetail.Text = ("model={0}  offload={1}  GPU {2:N1}/{3:N1} GB free  |  {4}`r`n{5}" -f `
                $j.model, $off, $freeGb, $totalGb, (Get-Date -Format "HH:mm:ss"), $hint)
            $statLabel.Text = "SD $state | ready=$ready | offload=$off | ping ok"
        }

        foreach ($pair in @(
            @{ Path = $outLog; Box = $boxOut; Key = "Out" },
            @{ Path = $errLog; Box = $boxErr; Key = "Err" }
        )) {
            if (-not (Test-Path -LiteralPath $pair.Path)) { continue }
            $len = (Get-Item -LiteralPath $pair.Path -ErrorAction Stop).Length
            $prev = if ($pair.Key -eq "Out") { $script:lastOutLen } else { $script:lastErrLen }
            if ($len -ne $prev) {
                $pair.Box.Text = Get-LogTail $pair.Path 100
                $pair.Box.SelectionStart = $pair.Box.TextLength
                $pair.Box.ScrollToCaret()
                if ($pair.Key -eq "Out") { $script:lastOutLen = $len } else { $script:lastErrLen = $len }
            }
        }

        $jobLogs = @(Get-ChildItem -Path $env:TEMP -Filter "broodmother_*_status.log" -ErrorAction SilentlyContinue |
            Sort-Object LastWriteTime -Descending | Select-Object -First 1)
        if ($jobLogs) {
            $tail = ((Get-Content -LiteralPath $jobLogs[0].FullName -Tail 2 -ErrorAction SilentlyContinue) -join " | ")
            if ($tail) {
                $msg = "{0}: {1}" -f $jobLogs[0].Name, $tail
                if ($msg.Length -gt 140) { $msg = $msg.Substring(0, 140) }
                $statLabel.Text = $msg
            }
        }
    } catch {
        try {
            Write-Crash ("Update-StatusUi: " + $_.Exception.Message)
            $statLabel.Text = "UI poll error (GUI stays open): $($_.Exception.Message)"
        } catch {}
    }
}

function Start-SdServer([bool]$force) {
    if ($script:starting) {
        Append-UiLog "Start already in progress..."
        return
    }
    $script:starting = $true
    $btnStart.Enabled = $false
    $btnForce.Enabled = $false
    if ($force) {
        Append-UiLog "Force-restarting SD (CLIP-only defaults)..."
    } else {
        Append-UiLog "Starting SD..."
    }

    $env:SD_SKIP_T5 = "1"
    $env:SD_ALLOW_T5_RAM = "0"
    $env:SD_REBALANCE = "0"
    $env:SD_HEADROOM_GB = "0"
    $env:SD_MAX_CPU_GB = "24"
    $env:SD_MAX_GPU_GB = "10"
    $env:SD_ALLOW_NONADMIN = "1"

    if (-not (Test-Path -LiteralPath $startPs)) {
        Append-UiLog "ERROR: missing $startPs"
        $script:starting = $false
        $btnStart.Enabled = $true
        $btnForce.Enabled = $true
        return
    }

    $arg = if ($force) { "-Force -WaitSec 150 -NoStatusGui" } else { "-WaitSec 150 -NoStatusGui" }

    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = "powershell.exe"
    $psi.Arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$startPs`" $arg"
    $psi.UseShellExecute = $false
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.CreateNoWindow = $true
    $psi.WorkingDirectory = $toolsRoot

    $p = New-Object System.Diagnostics.Process
    $p.StartInfo = $psi
    $p.EnableRaisingEvents = $true
    [void]$p.Start()

    $outHandler = [System.Diagnostics.DataReceivedEventHandler] {
        param($sender, $e)
        if ($e.Data) {
            $form.BeginInvoke([Action] {
                Append-UiLog $e.Data
            }) | Out-Null
        }
    }
    $p.add_OutputDataReceived($outHandler)
    $p.add_ErrorDataReceived($outHandler)
    $p.BeginOutputReadLine()
    $p.BeginErrorReadLine()

    $watcher = New-Object Windows.Forms.Timer
    $watcher.Interval = 500
    $watcher.Add_Tick({
        if ($p.HasExited) {
            $watcher.Stop()
            Append-UiLog ("Start script exited code={0}" -f $p.ExitCode)
            $script:starting = $false
            $btnStart.Enabled = $true
            $btnForce.Enabled = $true
            Update-StatusUi
        }
    })
    $watcher.Start()
}

$btnStart.Add_Click({ Start-SdServer $false })
$btnForce.Add_Click({ Start-SdServer $true })
$btnRefresh.Add_Click({ Update-StatusUi })
$btnLogs.Add_Click({
    if (Test-Path -LiteralPath $sdRoot) { Start-Process explorer.exe $sdRoot }
    else { [Windows.Forms.MessageBox]::Show("SD folder missing: $sdRoot") | Out-Null }
})
$btnCopy.Add_Click({
    $ping = Get-SdPing
    if ($ping.Ok) {
        [Windows.Forms.Clipboard]::SetText($ping.Raw)
        Append-UiLog "Copied /ping JSON to clipboard"
    } else {
        [Windows.Forms.Clipboard]::SetText([string]$ping.Raw)
        Append-UiLog "Copied error text to clipboard"
    }
})

$timer = New-Object Windows.Forms.Timer
$timer.Interval = 1000
$timer.Add_Tick({
    try {
        if ($chkAuto.Checked) { Update-StatusUi }
    } catch {
        Write-Crash ("timer tick: " + $_.Exception.Message)
    }
})
$timer.Start()

$form.Add_Shown({
    try {
        Append-UiLog "SD Status GUI open. Watching :1338 + logs"
        Append-UiLog "Server is launched with NO console window — closing this GUI does not kill SD."
        Update-StatusUi
        if ($StartServer) { Start-SdServer $true }
    } catch {
        Write-Crash ("Form Shown: " + $_.Exception.Message)
        Append-UiLog ("Shown handler error: " + $_.Exception.Message)
    }
})
$form.Add_FormClosed({
    try { $timer.Stop() } catch {}
})

[Windows.Forms.Application]::Run($form)
} catch {
    Write-Crash ("GUI fatal: " + $_.Exception.Message + "`n" + $_.ScriptStackTrace)
    try {
        Add-Type -AssemblyName System.Windows.Forms -ErrorAction SilentlyContinue
        [Windows.Forms.MessageBox]::Show(
            "SD Status GUI crashed.`n`n$($_.Exception.Message)`n`nDetails: $crashLog",
            "SD Status GUI",
            [Windows.Forms.MessageBoxButtons]::OK,
            [Windows.Forms.MessageBoxIcon]::Error
        ) | Out-Null
    } catch {}
    exit 1
}

# Open SD Status GUI if not already running (safe to call from any bat/ps1).
# Launches a HIDDEN powershell host so you don't get a console flash.
param(
    [switch]$StartServer
)

$ErrorActionPreference = "Continue"
$gui = Join-Path $PSScriptRoot "SDServer-Status-GUI.ps1"
$crashLog = Join-Path $env:TEMP "sd_status_gui_crash.log"

if (-not (Test-Path -LiteralPath $gui)) {
    "$(Get-Date -Format o) GUI script missing: $gui" | Out-File $crashLog -Append
    exit 1
}

$WindowTitle = "SD Server Status - :1338"

# If already open, focus it and exit (no new process / no flash)
try {
    Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class SdGuiFocus {
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
  [DllImport("user32.dll")] public static extern bool IsIconic(IntPtr hWnd);
}
"@ -ErrorAction SilentlyContinue

    $existing = Get-Process -ErrorAction SilentlyContinue | Where-Object {
        $_.MainWindowTitle -eq $WindowTitle -and $_.MainWindowHandle -ne [IntPtr]::Zero
    } | Select-Object -First 1

    if ($existing) {
        $hwnd = $existing.MainWindowHandle
        if ([SdGuiFocus]::IsIconic($hwnd)) { [SdGuiFocus]::ShowWindow($hwnd, 9) | Out-Null }
        else { [SdGuiFocus]::ShowWindow($hwnd, 5) | Out-Null }
        [SdGuiFocus]::SetForegroundWindow($hwnd) | Out-Null
        exit 0
    }
} catch {}

$argList = @(
    "-STA",
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-WindowStyle", "Hidden",
    "-File", $gui
)
if ($StartServer) { $argList += "-StartServer" }

# Hidden host = no black console flash
Start-Process -FilePath "powershell.exe" -ArgumentList $argList -WindowStyle Hidden | Out-Null
exit 0

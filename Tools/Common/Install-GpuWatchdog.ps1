<#
.SYNOPSIS
    Registers (or removes) GpuWatchdog.ps1 as a scheduled task that starts at logon with administrator rights, so it
    can restart the graphics device when the driver loses the card.
.DESCRIPTION
    Run from an ELEVATED PowerShell (Run as administrator); the task needs "highest privileges" for pnputil.
    Task name: "AAMT GPU Watchdog". The watchdog only restarts the NVIDIA display device; it changes no driver or
    Windows setting. Remove it again with -Uninstall.
.EXAMPLE
    powershell -ExecutionPolicy Bypass -File Install-GpuWatchdog.ps1
.EXAMPLE
    powershell -ExecutionPolicy Bypass -File Install-GpuWatchdog.ps1 -Uninstall
#>
[CmdletBinding()]
param(
    [switch]$Uninstall,
    [switch]$DryRun,
    [int]$IntervalSec = 30
)

$TaskName = 'AAMT GPU Watchdog'
$id = [Security.Principal.WindowsIdentity]::GetCurrent()
if (-not (New-Object Security.Principal.WindowsPrincipal $id).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Error 'Run this from an elevated PowerShell (Run as administrator).'
    exit 1
}

if ($Uninstall) {
    if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
        Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
        Write-Host "Removed the task '$TaskName'."
    } else { Write-Host "No task '$TaskName'." }
    exit 0
}

$script = Join-Path $PSScriptRoot 'GpuWatchdog.ps1'
$argList = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$script`" -IntervalSec $IntervalSec"
if ($DryRun) { $argList += ' -DryRun' }
$action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument $argList
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $id.Name
# The logged-on user, elevated: the marker lands in that user's %LOCALAPPDATA%, where the toolkit looks.
$principal = New-ScheduledTaskPrincipal -UserId $id.Name -LogonType Interactive -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit ([TimeSpan]::Zero) `
    -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force | Out-Null
Start-ScheduledTask -TaskName $TaskName
Write-Host "Installed and started '$TaskName' (runs at logon, elevated). Log: $env:LOCALAPPDATA\AamtGpuHub\gpu_watchdog.log"

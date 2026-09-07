# Script to make PowerShell 7 the default PowerShell
# Run this script as Administrator

Write-Host "Making PowerShell 7 the default PowerShell..." -ForegroundColor Cyan
Write-Host ""

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "ERROR: This script must be run as Administrator!" -ForegroundColor Red
    Write-Host "Right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    exit 1
}

$pwshPath = "C:\Program Files\PowerShell\7\pwsh.exe"

if (-not (Test-Path $pwshPath)) {
    Write-Host "ERROR: PowerShell 7 not found at: $pwshPath" -ForegroundColor Red
    exit 1
}

# Method 1: Add to PATH (User PATH)
Write-Host "Method 1: Adding PowerShell 7 to User PATH..." -ForegroundColor Yellow
$pwshDir = Split-Path $pwshPath -Parent
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
$pathArray = $userPath -split ';'

if ($pathArray -notcontains $pwshDir) {
    $newPath = $userPath + ";$pwshDir"
    [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
    Write-Host "  ✓ Added PowerShell 7 directory to User PATH" -ForegroundColor Green
} else {
    Write-Host "  ✓ PowerShell 7 already in User PATH" -ForegroundColor Green
}

# Method 2: Create pwsh alias in PowerShell profile
Write-Host ""
Write-Host "Method 2: Creating pwsh alias in PowerShell profile..." -ForegroundColor Yellow
$profilePath = $PROFILE.CurrentUserAllHosts
$profileDir = Split-Path $profilePath -Parent

if (-not (Test-Path $profileDir)) {
    New-Item -ItemType Directory -Path $profileDir -Force | Out-Null
}

$aliasCode = @"
# PowerShell 7 alias
Set-Alias -Name pwsh -Value "$pwshPath" -Scope Global -Force
"@

if (Test-Path $profilePath) {
    $profileContent = Get-Content $profilePath -Raw
    if ($profileContent -notmatch "PowerShell 7 alias") {
        Add-Content -Path $profilePath -Value "`n$aliasCode"
        Write-Host "  ✓ Added pwsh alias to profile" -ForegroundColor Green
    } else {
        Write-Host "  ✓ pwsh alias already in profile" -ForegroundColor Green
    }
} else {
    Set-Content -Path $profilePath -Value $aliasCode
    Write-Host "  ✓ Created profile with pwsh alias" -ForegroundColor Green
}

# Method 3: Set as default in Windows Terminal (if installed)
Write-Host ""
Write-Host "Method 3: Checking Windows Terminal settings..." -ForegroundColor Yellow
$wtSettingsPath = "$env:LOCALAPPDATA\Packages\Microsoft.WindowsTerminal_8wekyb3d8bbwe\LocalState\settings.json"
if (Test-Path $wtSettingsPath) {
    Write-Host "  ℹ Windows Terminal found. You can set PowerShell 7 as default in Windows Terminal settings." -ForegroundColor Cyan
    Write-Host "    Open Windows Terminal → Settings → Default profile → Select 'PowerShell 7'" -ForegroundColor Gray
} else {
    Write-Host "  ℹ Windows Terminal not found (optional)" -ForegroundColor Gray
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Setup Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "To use PowerShell 7:" -ForegroundColor Yellow
Write-Host "  1. Open a new terminal/command prompt" -ForegroundColor White
Write-Host "  2. Type 'pwsh' to launch PowerShell 7" -ForegroundColor White
Write-Host "  3. Or use: 'C:\Program Files\PowerShell\7\pwsh.exe'" -ForegroundColor White
Write-Host ""
Write-Host "Note: You may need to restart your terminal for PATH changes to take effect." -ForegroundColor Gray
Write-Host ""

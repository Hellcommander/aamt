# Isolated load of ApiMigrator.Core.dll for PowerShell hosts.
# Dot-source after setting $ApiMigratorToolsRoot to the _tools folder.
# Loads the assembly from a byte copy so the shared bin\Release DLL is not locked
# (concurrent CLI / GUI / another PS1 can still rebuild or load it).

if (-not (Get-Variable -Name ApiMigratorToolsRoot -Scope Script -ErrorAction SilentlyContinue) -or
    -not $ApiMigratorToolsRoot) {
    $ApiMigratorToolsRoot = Split-Path $PSScriptRoot -Parent
}

function Get-ApiMigratorCoreDllPath {
    Join-Path $ApiMigratorToolsRoot 'src\ApiMigrator.Core\bin\Release\net8.0\ApiMigrator.Core.dll'
}

function Test-ApiMigratorCoreLoaded {
    [bool]([AppDomain]::CurrentDomain.GetAssemblies() |
        Where-Object { $_.GetName().Name -eq 'ApiMigrator.Core' })
}

function Import-ApiMigratorCoreIsolated {
    param([Parameter(Mandatory)][string]$DllPath)

    if (Test-ApiMigratorCoreLoaded) { return }

    $bytes = $null
    $last = $null
    for ($n = 0; $n -lt 20; $n++) {
        try {
            $fs = [System.IO.File]::Open(
                $DllPath,
                [System.IO.FileMode]::Open,
                [System.IO.FileAccess]::Read,
                [System.IO.FileShare]::ReadWrite -bor [System.IO.FileShare]::Delete)
            try {
                $len = [int]$fs.Length
                $bytes = New-Object byte[] $len
                $read = 0
                while ($read -lt $len) {
                    $nread = $fs.Read($bytes, $read, $len - $read)
                    if ($nread -le 0) { break }
                    $read += $nread
                }
            }
            finally { $fs.Dispose() }
            break
        }
        catch {
            $last = $_
            Start-Sleep -Milliseconds (50 * ($n + 1))
        }
    }
    if ($null -eq $bytes) {
        throw "Could not read ApiMigrator.Core.dll (another process may have an exclusive lock): $last"
    }

    try {
        [void][System.Reflection.Assembly]::Load($bytes)
        return
    }
    catch {
        $last = $_
    }

    # Fallback: shadow-copy the output folder and Add-Type from the copy.
    $srcDir = Split-Path -Parent $DllPath
    $destDir = Join-Path ([System.IO.Path]::GetTempPath()) (
        "CoQ.ApiMigrator\ps-$PID-$([guid]::NewGuid().ToString('n'))")
    New-Item -ItemType Directory -Force -Path $destDir | Out-Null
    $copied = $false
    for ($n = 0; $n -lt 20; $n++) {
        try {
            Copy-Item -Path (Join-Path $srcDir '*') -Destination $destDir -Force
            $copied = $true
            break
        }
        catch {
            $last = $_
            Start-Sleep -Milliseconds (50 * ($n + 1))
        }
    }
    if (-not $copied) {
        throw "Could not isolate ApiMigrator.Core.dll: $last"
    }
    Add-Type -Path (Join-Path $destDir 'ApiMigrator.Core.dll')
}

function Ensure-ApiMigratorCoreDll {
    param([string]$ToolsRoot = $ApiMigratorToolsRoot)

    $proj = Join-Path $ToolsRoot 'src\ApiMigrator.Core\ApiMigrator.Core.csproj'
    $dll = Join-Path $ToolsRoot 'src\ApiMigrator.Core\bin\Release\net8.0\ApiMigrator.Core.dll'
    $buildTimeoutMs = 180000
    $mutex = New-Object System.Threading.Mutex($false, 'Local\CoQ.ApiMigrator.Core.Build')
    $got = $false
    try {
        $got = $mutex.WaitOne($buildTimeoutMs)
        if (-not $got) {
            if (Test-Path -LiteralPath $dll) {
                Write-Warning "Timed out waiting for ApiMigrator.Core build lock; using existing DLL."
            }
            else {
                throw "Timed out waiting for ApiMigrator.Core build lock (${buildTimeoutMs}ms). Another migrator may be stuck mid-build."
            }
        }
        else {
            $srcNewest = Get-ChildItem -LiteralPath (Join-Path $ToolsRoot 'src\ApiMigrator.Core') -Filter '*.cs' -File -Recurse -ErrorAction SilentlyContinue |
                Sort-Object LastWriteTime -Descending |
                Select-Object -First 1 -ExpandProperty LastWriteTime
            $needsBuild = -not (Test-Path -LiteralPath $dll)
            if (-not $needsBuild -and $srcNewest) {
                $dllTime = (Get-Item -LiteralPath $dll).LastWriteTime
                if ($srcNewest -gt $dllTime) { $needsBuild = $true }
            }
            if ($needsBuild) {
                Write-Host "Building ApiMigrator.Core..." -ForegroundColor DarkCyan
                $psi = New-Object System.Diagnostics.ProcessStartInfo
                $psi.FileName = 'dotnet'
                $psi.Arguments = "build `"$proj`" -c Release -v q --nologo"
                $psi.UseShellExecute = $false
                $psi.CreateNoWindow = $true
                $p = [System.Diagnostics.Process]::Start($psi)
                if (-not $p.WaitForExit($buildTimeoutMs)) {
                    try { $p.Kill() } catch {}
                    if (-not (Test-Path -LiteralPath $dll)) {
                        throw "dotnet build ApiMigrator.Core timed out after ${buildTimeoutMs}ms (killed)."
                    }
                    Write-Warning "dotnet build ApiMigrator.Core timed out; using existing DLL."
                }
                elseif ($p.ExitCode -ne 0 -or -not (Test-Path -LiteralPath $dll)) {
                    if (Test-Path -LiteralPath $dll) {
                        Write-Warning "dotnet build ApiMigrator.Core failed (exit $($p.ExitCode)); using existing DLL (another process may have it open)."
                    }
                    else {
                        throw "Could not build ApiMigrator.Core at $dll (exit $($p.ExitCode); required for programmatic fixes)."
                    }
                }
            }
        }
    }
    finally {
        if ($got) { [void]$mutex.ReleaseMutex() }
        $mutex.Dispose()
    }

    Import-ApiMigratorCoreIsolated -DllPath $dll
    return $dll
}

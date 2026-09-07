# ChooseYourCreature-GUI.ps1
# Launch AAMT Dwarf Fortress Creature Studio in the browser.

$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$editor = Join-Path $here "df_body_editor.py"

function Get-PythonExe {
    foreach ($c in @("python", "py")) {
        try { return (Get-Command $c -ErrorAction Stop).Source } catch {}
    }
    throw "Python not found on PATH."
}

$py = Get-PythonExe
$spec = $env:AAMT_DF_SPEC
$argList = @($editor)
if (-not [string]::IsNullOrWhiteSpace($spec) -and (Test-Path $spec)) {
    $argList += @("--spec", $spec)
}

Write-Host "Opening Creature Studio (Ctrl+C to stop the server)..." -ForegroundColor DarkCyan
& $py @argList
exit $LASTEXITCODE

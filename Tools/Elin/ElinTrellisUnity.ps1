<#
.SYNOPSIS
    Elin + Starfield dual asset pipeline (Cursor concepts -> TRELLIS -> Unity/SF).

.EXAMPLE
    .\ElinTrellisUnity.ps1 stage
    .\ElinTrellisUnity.ps1 publish-concepts
    .\ElinTrellisUnity.ps1 trellis -Id DragonMagic,BloodMagic -Keep
    .\ElinTrellisUnity.ps1 deploy-elin -Id DragonMagic
    .\ElinTrellisUnity.ps1 import-spells
#>
[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [ValidateSet("stage", "publish-concepts", "status", "deploy-ui", "deploy-icons", "trellis", "deploy-elin", "import-spells", "preview-spells")]
    [string]$Command = "status",

    [string[]]$Id = @(),
    [switch]$All,
    [switch]$Keep,
    [switch]$DryRun,
    [string]$System = ""
)

$ErrorActionPreference = "Stop"
$py = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $py) { throw "python not found" }
$here = $PSScriptRoot

switch ($Command) {
    "import-spells" {
        $argsList = @((Join-Path $here "elin_starfield_spell_bridge.py"), "import")
        if ($DryRun) { $argsList += "--dry-run" }
        if ($System) { $argsList += @("--system", $System) }
        & $py @argsList
        break
    }
    "preview-spells" {
        $argsList = @((Join-Path $here "elin_starfield_spell_bridge.py"), "preview")
        if ($System) { $argsList += @("--system", $System) }
        & $py @argsList
        break
    }
    default {
        $argsList = @((Join-Path $here "elin_trellis_unity.py"), $Command)
        foreach ($i in $Id) { $argsList += @("--id", $i) }
        if ($All) { $argsList += "--all" }
        if ($Keep -and $Command -eq "trellis") { $argsList += "--keep" }
        & $py @argsList
    }
}
exit $LASTEXITCODE

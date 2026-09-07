# AI-Assisted Modding Tools (AAMT) - Soulash 2 Skill Creator
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ArgsRest
)
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $here
# No args → Studio editor (same as double-clicking SkillCreator.bat)
if (-not $ArgsRest -or $ArgsRest.Count -eq 0) {
    $ArgsRest = @("editor")
}
python (Join-Path $here "s2_skill_cli.py") @ArgsRest
exit $LASTEXITCODE

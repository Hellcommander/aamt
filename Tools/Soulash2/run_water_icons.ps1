$py = if (Test-Path "E:\tools\miniconda3\python.exe") { "E:\tools\miniconda3\python.exe" } else { "python" }
$gen = Join-Path $PSScriptRoot "generate_mod_branding_assets.py"
$jobs = @(
    @{m="E:\SteamLibrary\steamapps\common\Soulash 2\data\mods\arendeth_hemohydraulic_magic"; t="hemohydraulic"},
    @{m="E:\SteamLibrary\steamapps\common\Soulash 2\data\mods\arendeth_water_magic"; t="hydromancy"}
)
foreach ($j in $jobs) {
    Write-Host "ICON $($j.t)"
    & $py $gen --mod-path $j.m --theme $j.t --mode icon --quality mechanical --max-attempts 2 --skip-backup
}

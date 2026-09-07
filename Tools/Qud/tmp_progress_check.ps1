Write-Host '=== python brood/sd ==='
Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
  Where-Object { $_.CommandLine -match 'broodmother|server\.py|generate_brood' } |
  ForEach-Object {
    'PID={0} MB={1} {2}' -f $_.ProcessId, [math]::Round($_.WorkingSetSize/1MB), $_.CommandLine
  }
if (-not $?) { 'none' }
Write-Host '=== ollama ==='
Get-Process ollama* -ErrorAction SilentlyContinue | ForEach-Object { '{0} PID={1}' -f $_.Name, $_.Id }
Write-Host '=== SD ==='
try { Invoke-RestMethod http://127.0.0.1:1338/ping -TimeoutSec 2 | Out-Null; 'SD up' } catch { 'SD down' }
Write-Host '=== logs ==='
foreach ($n in @('broodmother_biomutation_assets.log','broodmother_ollama_prompts.log','broodmother_fresh_assets.log')) {
  $p = Join-Path $env:TEMP $n
  if (Test-Path $p) {
    Write-Host ("--- {0} ---" -f $n)
    Get-Content $p -Tail 12
  }
}
Write-Host '=== drafts count ==='
$d = Join-Path $env:USERPROFILE 'AppData\LocalLow\Freehold Games\CavesOfQud\Mods\Broodmother Mutation\DesignDrafts'
if (Test-Path $d) {
  (Get-ChildItem $d -Filter '*_design_draft.png' -ErrorAction SilentlyContinue | Measure-Object).Count.ToString() + ' design drafts'
  (Get-ChildItem $d -Filter 'prompt_pack.json' -ErrorAction SilentlyContinue | ForEach-Object { 'prompt_pack.json ' + $_.Length + ' bytes ' + $_.LastWriteTime })
}

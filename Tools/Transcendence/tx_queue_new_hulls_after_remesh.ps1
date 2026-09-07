# After Dragon + Shark + Manta TRELLIS 1024 GLBs exist, run SD skins → bake → 120 facings → SA3.
# Do not overlap TRELLIS. Texture batch stops TRELLIS before SD.
$ErrorActionPreference = "Continue"
$mesh = "D:\games\Ai assisted toolkit\Tools\Shared\Concepts\meshes"
$tx = "D:\games\Ai assisted toolkit\Tools\Transcendence"
$ids = @(
  "scBiometalDragon", "scBiometalDragonSegment", "scBiometalDragonTail", "scBiometalDragonDrone",
  "scSpaceShark", "scSpaceSharkScout", "scSpaceSharkApex",
  "scSpaceSharkSegment", "scSpaceSharkTail", "scSpaceSharkDrone",
  "scSpaceManta", "scSpaceMantaScout", "scSpaceMantaGuardian", "scSpaceMantaRift",
  "scSpaceMantaWing", "scSpaceMantaTail", "scSpaceMantaDrone"
)

function Get-ReadyCount {
  $ready = 0
  foreach ($id in $ids) {
    $p = Join-Path $mesh "$id.glb"
    if ((Test-Path $p) -and ((Get-Item $p).Length -ge 400000)) { $ready++ }
  }
  return $ready
}

function Test-RemeshRunning {
  $hits = Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -like '*tx_concept_remesh_batch.py*' }
  return [bool]$hits
}

function Invoke-PyIds {
  param([string]$Script, [string[]]$Extra = @())
  $pyArgs = @((Join-Path $tx $Script)) + $Extra
  foreach ($id in $ids) { $pyArgs += @("--id", $id) }
  Write-Host "[pipeline] python $($pyArgs -join ' ')"
  python @pyArgs
  Write-Host "[pipeline] $Script exit $LASTEXITCODE"
  return $LASTEXITCODE
}

Write-Host "[pipeline] waiting for $($ids.Count) new-hull GLBs..."
while ($true) {
  $ready = Get-ReadyCount
  Write-Host "[pipeline] remesh ready $ready/$($ids.Count) remeshProc=$(Test-RemeshRunning)"
  if ($ready -eq $ids.Count -and -not (Test-RemeshRunning)) { break }
  Start-Sleep -Seconds 45
}

Write-Host "[pipeline] TRELLIS remesh complete; starting textures (stops TRELLIS)..."
$code = Invoke-PyIds "tx_concept_texture_batch.py"
Write-Host "[pipeline] textures done (code $code); republishing Starfield copies..."
python (Join-Path $tx "tx_publish_starfield.py")
Write-Host "[pipeline] publish exit $LASTEXITCODE; starting 120-facings..."
$code = Invoke-PyIds "tx_concept_spritesheet_batch.py"
Write-Host "[pipeline] sheets done (code $code); starting SA3 audio..."
$code = Invoke-PyIds "tx_concept_audio_batch.py"
Write-Host "[pipeline] audio done (code $code). New hull pipeline finished."
exit $code

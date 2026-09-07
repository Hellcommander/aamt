# Wait for Biometal Dragon 1024 remesh, then remesh Space Shark family (same TRELLIS server).
$ErrorActionPreference = "Stop"
$env:AAMT_TRELLIS_KEEP_SERVER = "1"
$mesh = "D:\games\Ai assisted toolkit\Tools\Shared\Concepts\meshes"
$dragonIds = @("scBiometalDragon", "scBiometalDragonSegment", "scBiometalDragonTail", "scBiometalDragonDrone")
$sharkIds = @(
  "scSpaceShark", "scSpaceSharkScout", "scSpaceSharkApex",
  "scSpaceSharkSegment", "scSpaceSharkTail", "scSpaceSharkDrone"
)

Write-Host "[queue] waiting for dragon GLBs..."
while ($true) {
  $ready = 0
  foreach ($id in $dragonIds) {
    $p = Join-Path $mesh "$id.glb"
    if ((Test-Path $p) -and ((Get-Item $p).Length -ge 400000)) { $ready++ }
  }
  Write-Host "[queue] dragon ready $ready/$($dragonIds.Count)"
  if ($ready -eq $dragonIds.Count) { break }
  Start-Sleep -Seconds 30
}

Write-Host "[queue] starting Space Shark remesh..."
$args = @("D:\games\Ai assisted toolkit\Tools\Transcendence\tx_concept_remesh_batch.py", "--force")
foreach ($id in $sharkIds) { $args += @("--id", $id) }
python @args
exit $LASTEXITCODE

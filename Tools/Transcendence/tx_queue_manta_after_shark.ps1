# Wait for Space Shark 1024 remesh, then remesh Space Manta family (same TRELLIS server).
$ErrorActionPreference = "Stop"
$env:AAMT_TRELLIS_KEEP_SERVER = "1"
$mesh = "D:\games\Ai assisted toolkit\Tools\Shared\Concepts\meshes"
$sharkIds = @(
  "scSpaceShark", "scSpaceSharkScout", "scSpaceSharkApex",
  "scSpaceSharkSegment", "scSpaceSharkTail", "scSpaceSharkDrone"
)
$mantaIds = @(
  "scSpaceManta", "scSpaceMantaScout", "scSpaceMantaGuardian", "scSpaceMantaRift",
  "scSpaceMantaWing", "scSpaceMantaTail", "scSpaceMantaDrone"
)

Write-Host "[queue] waiting for shark GLBs..."
while ($true) {
  $ready = 0
  foreach ($id in $sharkIds) {
    $p = Join-Path $mesh "$id.glb"
    if ((Test-Path $p) -and ((Get-Item $p).Length -ge 400000)) { $ready++ }
  }
  Write-Host "[queue] shark ready $ready/$($sharkIds.Count)"
  if ($ready -eq $sharkIds.Count) { break }
  Start-Sleep -Seconds 30
}

Write-Host "[queue] starting Space Manta remesh..."
$pyArgs = @("D:\games\Ai assisted toolkit\Tools\Transcendence\tx_concept_remesh_batch.py", "--force")
foreach ($id in $mantaIds) { $pyArgs += @("--id", $id) }
python @pyArgs
exit $LASTEXITCODE

#Requires -Version 5.1
<#
.SYNOPSIS
  Sanity-check what a public clone would share (untracked, not ignored).
#>
param(
    [int]$MaxFileMB = 2,
    [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
)

Set-Location -LiteralPath $RepoRoot
$untracked = @(git ls-files --others --exclude-standard)
if ($untracked.Count -eq 0) {
    Write-Host 'No untracked files (nothing staged for first commit yet, or working tree clean).'
    exit 0
}

$total = 0L
$large = @()
$media = @()
$mediaExt = '\.(png|jpg|jpeg|gif|webp|glb|gltf|wav|ogg|mp3|dll|exe|zip|7z|pxo|blend|fbx|obj)$'

foreach ($rel in $untracked) {
    if (-not (Test-Path -LiteralPath $rel)) { continue }
    $item = Get-Item -LiteralPath $rel -Force
    $total += $item.Length
    if ($item.Length -gt ($MaxFileMB * 1MB)) {
        $large += [PSCustomObject]@{ MB = [math]::Round($item.Length / 1MB, 2); Path = $rel }
    }
    if ($rel -match $mediaExt) {
        $media += $rel
    }
}

Write-Host ("Public share candidate: {0} files, {1:N1} MB" -f $untracked.Count, ($total / 1MB))

if ($large.Count -gt 0) {
    Write-Host "`nFiles larger than ${MaxFileMB} MB:"
    $large | Sort-Object MB -Descending | Format-Table -AutoSize
}

if ($media.Count -gt 0) {
    Write-Host "`nBinary/media still untracked (review before commit):"
    $media | ForEach-Object { "  $_" }
    exit 1
}

if ($large.Count -gt 0) {
    exit 1
}

Write-Host 'OK — no large or binary leaks in untracked share.'
exit 0

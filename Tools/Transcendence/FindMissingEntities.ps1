# Find missing entity declarations
param([string]$FilePath)

$content = Get-Content $FilePath -Raw

# Find all entity references
$entityRefs = [regex]::Matches($content, '&([a-zA-Z][a-zA-Z0-9_]*);') | ForEach-Object { $_.Groups[1].Value } | Sort-Object -Unique

# Find all declared entities
$declared = [regex]::Matches($content, '<!ENTITY\s+([a-zA-Z][a-zA-Z0-9_]*)\s+') | ForEach-Object { $_.Groups[1].Value } | Sort-Object -Unique

# Find missing
$missing = $entityRefs | Where-Object { $declared -notcontains $_ }

Write-Host "Missing entities in $(Split-Path -Leaf $FilePath):" -ForegroundColor Cyan
$missing | ForEach-Object { Write-Host "  $_" -ForegroundColor White }

return $missing


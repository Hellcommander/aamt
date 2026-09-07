param(
	[Parameter(Mandatory = $true)]
	[string]$ModRoot
)

$ErrorActionPreference = "Stop"
if (-not (Test-Path $ModRoot)) {
	throw "Mod root not found: $ModRoot"
}

$files = Get-ChildItem -Path $ModRoot -Recurse -Include *.effect,*.unit,*.inc,*.sval
$missing = @()

foreach ($file in $files) {
	$text = Get-Content -Raw -Path $file.FullName
	$matches = [regex]::Matches($text, 'texture\s*=\s*"(?:\./|\.\./)([^"]+)"')
	foreach ($m in $matches) {
		$rel = $m.Groups[1].Value
		# Resolve relative to file directory with ../ support
		$candidate = Join-Path $file.DirectoryName ($m.Groups[0].Value -replace 'texture\s*=\s*"', '' -replace '"$', '')
		# Simpler: build from capture
		$base = $file.DirectoryName
		$parts = ($m.Value -replace '.*?"', '' -replace '"$', '')
		$resolved = [System.IO.Path]::GetFullPath((Join-Path $base $parts))
		if (-not (Test-Path $resolved)) {
			$missing += [pscustomobject]@{
				File = $file.FullName.Substring($ModRoot.Length).TrimStart('\')
				Texture = $parts
				Resolved = $resolved
			}
		}
	}
}

if ($missing.Count -eq 0) {
	Write-Host "No missing relative textures found under $ModRoot"
} else {
	Write-Host "Missing relative textures ($($missing.Count)):"
	$missing | Format-Table -AutoSize
}

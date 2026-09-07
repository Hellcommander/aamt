param(
	[string]$ModRoot = "F:\SteamLibrary\steamapps\common\Hammerwatch 2\Druidic_Warden",
	[string]$ToolsOut = "",
	[string]$TifsRoot = "F:\SteamLibrary\steamapps\common\Hammerwatch 2\hw2_tgas",
	[ValidateSet("absolute", "local")]
	[string]$TextureMode = "absolute",

	[string]$Forms = "shambler,wolf,boar,spider"
)

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$py = Join-Path $scriptDir "generate_wildshape_body.py"

if (-not $ToolsOut) {
	$ToolsOut = Join-Path $scriptDir "GeneratedAssets\wildshape"
}

Write-Host "Generating shambler wildshape body unit (texture-mode=$TextureMode)..."
& python $py --mod-root $ModRoot --tools-out $ToolsOut --tifs-root $TifsRoot --texture-mode $TextureMode --forms $Forms
if ($LASTEXITCODE -ne 0) {
	throw "generate_wildshape_body.py failed ($LASTEXITCODE)"
}
Write-Host "Done."

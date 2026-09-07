# TranscendenceAssetGenerator.Functions.ps1
# Real media writers (dot-sourced before the AssetType switch). Never .info.txt stubs.

$script:TxProcPy = Join-Path (Split-Path -Parent $PSScriptRoot) "Shared\tx_procedural_assets.py"
$script:TxSharedGen = Join-Path (Split-Path -Parent $PSScriptRoot) "Shared\GenerateGameAsset.ps1"

function Invoke-TxProcedural {
    param(
        [Parameter(Mandatory)][string[]]$Args
    )
    $py = (Get-Command python -ErrorAction SilentlyContinue).Source
    if (-not $py) { throw "python not on PATH (required for procedural TX assets)" }
    if (-not (Test-Path -LiteralPath $script:TxProcPy)) {
        throw "Missing procedural writer: $script:TxProcPy"
    }
    & $py $script:TxProcPy @Args
    if ($LASTEXITCODE -ne 0) { throw "tx_procedural_assets.py failed ($LASTEXITCODE): $($Args -join ' ')" }
}

function Ensure-Dir([string]$Path) {
    if ($Path -and -not (Test-Path -LiteralPath $Path)) {
        New-Item -ItemType Directory -Path $Path -Force | Out-Null
    }
}

function Move-NewestPngTo {
    param([string]$Dir, [string]$Dest)
    if (Test-Path -LiteralPath $Dest) { return $true }
    $newest = Get-ChildItem -LiteralPath $Dir -Filter "*.png" -File -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if ($newest) {
        Copy-Item -LiteralPath $newest.FullName -Destination $Dest -Force
        return $true
    }
    return $false
}

function Create-RealIcon {
    param([string]$Path, [int]$Size, [string]$Color = "#4488ff", [string]$NovaDriftStyle = "")
    Ensure-Dir (Split-Path -Parent $Path)
    Invoke-TxProcedural -Args @("icon", "--path", $Path, "--size", "$Size", "--color", $Color)
}

function Create-RealTexture {
    param([string]$Path, [int]$Width, [int]$Height, [string]$Color = "#2a2a3a")
    Ensure-Dir (Split-Path -Parent $Path)
    Invoke-TxProcedural -Args @("texture", "--path", $Path, "--width", "$Width", "--height", "$Height", "--color", $Color)
}

function Create-RealSpritesheet {
    param([string]$Path, [int]$Columns, [int]$Rows, [int]$Cell, [string]$Color = "#4488ff")
    Ensure-Dir (Split-Path -Parent $Path)
    Invoke-TxProcedural -Args @("spritesheet", "--path", $Path, "--columns", "$Columns", "--rows", "$Rows", "--cell", "$Cell", "--color", $Color)
}

function Invoke-TxAiAudio {
    param(
        [string]$Prompt,
        [string]$DestPath,
        [double]$Duration = 2.5,
        [string]$Archetype = "impact"
    )
    $py = (Get-Command python -ErrorAction SilentlyContinue).Source
    $pipe = Join-Path $PSScriptRoot "tx_ai_pipeline.py"
    if (-not ($py -and (Test-Path -LiteralPath $pipe))) { return $false }
    Ensure-Dir (Split-Path -Parent $DestPath)
    & $py $pipe audio --prompt $Prompt --out $DestPath --duration $Duration --archetype $Archetype
    return ($LASTEXITCODE -eq 0 -and (Test-Path -LiteralPath $DestPath))
}

function Create-RealAudio {
    param([string]$Path, [int]$Duration, [int]$SampleRate, [string]$AudioType)
    $arch = switch -Regex ($AudioType) {
        "UI|Interface|Click" { "ui" }
        "Ambient|Ambience|Loop" { "ambience" }
        "Weapon|Laser|Gun" { "laser" }
        "Impact|Hit|Crash" { "impact" }
        default { "ship" }
    }
    $prompt = "Transcendence $AudioType game sound effect, short SFX, no music, no speech, no lyrics"
    if (-not (Invoke-TxAiAudio -Prompt $prompt -DestPath $Path -Duration $Duration -Archetype $arch)) {
        throw "Shared audio stage failed for $Path. Need Stable Audio 3 and/or D:\assets\audio. Procedural sine stubs are disabled."
    }
}

function Create-RealBeacon {
    param([string]$InactivePath, [string]$ActivePath, [int]$InactiveSize, [int]$ActiveSize, [string]$Color)
    Ensure-Dir (Split-Path -Parent $InactivePath)
    Ensure-Dir (Split-Path -Parent $ActivePath)
    Invoke-TxProcedural -Args @(
        "beacon",
        "--inactive", $InactivePath,
        "--active", $ActivePath,
        "--color", $Color,
        "--inactive-size", "$InactiveSize",
        "--active-size", "$ActiveSize"
    )
}

function Create-RealPowerIcon {
    param([string]$Path, [int]$Size, [string]$Style, [string]$Color)
    Ensure-Dir (Split-Path -Parent $Path)
    Invoke-TxProcedural -Args @("power", "--path", $Path, "--size", "$Size", "--style", $Style, "--color", $Color)
}

function Create-RealModel {
    param([string]$Path, [string]$Name)
    Ensure-Dir (Split-Path -Parent $Path)
    Invoke-TxProcedural -Args @("model", "--path", $Path, "--name", $Name)
}

# Back-compat aliases (old names still called by leftover paths)
function Create-PlaceholderIcon { param([string]$Path, [int]$Size, [string]$Color, [string]$NovaDriftStyle = "") { Create-RealIcon @PSBoundParameters } }
function Create-PlaceholderTexture { param([string]$Path, [int]$Width, [int]$Height, [string]$Color) { Create-RealTexture @PSBoundParameters } }
function Create-PlaceholderSpritesheet {
    param([string]$Path, [int]$Width, [int]$Height, [int]$IconSize, [int]$Facings = 120, [int]$Columns = 10, [string]$NovaDriftStyle = "")
    $rows = [math]::Max(1, [math]::Ceiling($Facings / [math]::Max(1, $Columns)))
    $cell = if ($IconSize -gt 0) { $IconSize } else { [math]::Max(16, [int]($Width / [math]::Max(1, $Columns))) }
    Create-RealSpritesheet -Path $Path -Columns $Columns -Rows $rows -Cell $cell -Color "#4488ff"
}
function Create-PlaceholderAudio { param([string]$Path, [int]$Duration, [int]$SampleRate, [string]$AudioType) { Create-RealAudio @PSBoundParameters } }
function Create-PlaceholderBeacon { param([string]$InactivePath, [string]$ActivePath, [int]$InactiveSize, [int]$ActiveSize, [string]$Color) { Create-RealBeacon @PSBoundParameters } }
function Create-PlaceholderPowerIcon { param([string]$Path, [int]$Size, [string]$Style, [string]$Color) { Create-RealPowerIcon @PSBoundParameters } }
function Create-PlaceholderModel { param([string]$Path, [string]$Name) { Create-RealModel @PSBoundParameters } }

function Invoke-TxAiTexture {
    param(
        [string]$Prompt,
        [string]$OutputDir,
        [string]$DestPath,
        [string]$AssetType,
        [string]$OllamaModel,
        [int]$Size
    )
    $py = (Get-Command python -ErrorAction SilentlyContinue).Source
    $pipe = Join-Path $PSScriptRoot "tx_ai_pipeline.py"
    if ($py -and (Test-Path -LiteralPath $pipe)) {
        Ensure-Dir (Split-Path -Parent $DestPath)
        $kind = switch ($AssetType) {
            "Weapon" { "icon" }
            "Icon" { "icon" }
            "Planet" { "sprite" }
            "Texture" { "texture" }
            default { "icon" }
        }
        & $py $pipe image --prompt $Prompt --out $DestPath --kind $kind --size $Size
        if ($LASTEXITCODE -eq 0 -and (Test-Path -LiteralPath $DestPath)) { return $true }
    }
    $aiScript = Join-Path $PSScriptRoot "AssetMakerAI.ps1"
    if (-not (Test-Path -LiteralPath $aiScript)) { return $false }
    & $aiScript -Action GenerateTexture -AssetType $AssetType -InputData $Prompt -OutputPath $OutputDir -OllamaModel $OllamaModel -TextureSize $Size -TextureMethod "Procedural"
    if (Test-Path -LiteralPath $DestPath) { return $true }
    return (Move-NewestPngTo -Dir $OutputDir -Dest $DestPath)
}

function Generate-WeaponIcon {
    param(
        [string]$Name, [string]$Description, [string]$OutputDir, [hashtable]$Specs,
        [switch]$UseAI, [string]$OllamaModel, [int]$Size, [string]$NovaDriftStyle = ""
    )
    $iconPath = Join-Path $OutputDir "$Name`_icon.png"
    $ok = $false
    if ($UseAI) {
        $styleNote = if ($NovaDriftStyle) { " Nova Drift $NovaDriftStyle weapon style." } else { "" }
        $prompt = "Generate a weapon icon for Transcendence: $Description.$styleNote Size: ${Size}x${Size}."
        $ok = Invoke-TxAiTexture -Prompt $prompt -OutputDir $OutputDir -DestPath $iconPath -AssetType Weapon -OllamaModel $OllamaModel -Size $Size
    }
    if (-not $ok) { Create-RealIcon -Path $iconPath -Size $Size -Color "#ff4444" -NovaDriftStyle $NovaDriftStyle }
    Write-Log "Weapon icon created: $iconPath" "SUCCESS"
}

function Generate-ItemIcon {
    param(
        [string]$Name, [string]$Description, [string]$OutputDir, [hashtable]$Specs,
        [switch]$UseAI, [string]$OllamaModel, [int]$Size, [string]$NovaDriftStyle = ""
    )
    $iconPath = Join-Path $OutputDir "$Name`_icon.png"
    $ok = $false
    if ($UseAI) {
        $styleNote = if ($NovaDriftStyle) { " Nova Drift $NovaDriftStyle item style." } else { "" }
        $prompt = "Generate an item icon for Transcendence: $Description.$styleNote Size: ${Size}x${Size}."
        $ok = Invoke-TxAiTexture -Prompt $prompt -OutputDir $OutputDir -DestPath $iconPath -AssetType Item -OllamaModel $OllamaModel -Size $Size
    }
    if (-not $ok) { Create-RealIcon -Path $iconPath -Size $Size -Color "#44ff44" -NovaDriftStyle $NovaDriftStyle }
    Write-Log "Item icon created: $iconPath" "SUCCESS"
}

function Generate-Icon {
    param(
        [string]$Name, [string]$Description, [string]$OutputDir, [hashtable]$Specs,
        [switch]$UseAI, [string]$OllamaModel, [int]$Size
    )
    $iconPath = Join-Path $OutputDir "$Name`_icon.png"
    $ok = $false
    if ($UseAI) {
        $prompt = "Generate an icon for Transcendence: $Description. Size: ${Size}x${Size}."
        $ok = Invoke-TxAiTexture -Prompt $prompt -OutputDir $OutputDir -DestPath $iconPath -AssetType Icon -OllamaModel $OllamaModel -Size $Size
    }
    if (-not $ok) { Create-RealIcon -Path $iconPath -Size $Size -Color "#4444ff" }
    Write-Log "Icon created: $iconPath" "SUCCESS"
}

function Generate-Projectile {
    param(
        [string]$Name, [string]$Description, [string]$OutputDir, [hashtable]$Specs,
        [switch]$UseAI, [string]$OllamaModel, [int]$Size
    )
    Ensure-Dir $OutputDir
    $projectilePath = Join-Path $OutputDir "$Name`_projectile.png"
    $ok = $false
    if ($UseAI) {
        $prompt = "Generate a projectile sprite for Transcendence: $Description. Size: ${Size}x${Size}."
        $ok = Invoke-TxAiTexture -Prompt $prompt -OutputDir $OutputDir -DestPath $projectilePath -AssetType Projectile -OllamaModel $OllamaModel -Size $Size
    }
    if (-not $ok) { Create-RealIcon -Path $projectilePath -Size $Size -Color "#ffff44" }
    Write-Log "Projectile created: $projectilePath" "SUCCESS"
    return $true
}

function Generate-ShipTexture {
    param(
        [string]$Name, [string]$Description, [string]$OutputDir, [hashtable]$Specs,
        [switch]$UseAI, [string]$OllamaModel, [int]$Width, [int]$Height
    )
    $texturePath = Join-Path $OutputDir "$Name`_texture.png"
    Ensure-Dir $OutputDir
    # Prefer Shared pbr/mesh skin when present beside an existing ship pack
    $skinPy = Join-Path (Split-Path -Parent $PSScriptRoot) "Shared\pbr_skin_generator.py"
    $ok = $false
    if ($UseAI) {
        $prompt = "Generate a seamless ship hull texture for Transcendence: $Description. ${Width}x${Height}."
        $ok = Invoke-TxAiTexture -Prompt $prompt -OutputDir $OutputDir -DestPath $texturePath -AssetType Texture -OllamaModel $OllamaModel -Size ([math]::Max($Width, $Height))
    }
    if (-not $ok -and (Test-Path -LiteralPath $skinPy)) {
        $py = (Get-Command python -ErrorAction SilentlyContinue).Source
        if ($py) {
            try {
                $skinDir = Join-Path $OutputDir "_pbr_tmp"
                Ensure-Dir $skinDir
                & $py $skinPy --theme $(if ($Description) { $Description } else { $Name }) --output-dir $skinDir --name $Name --size ([math]::Max($Width, $Height)) --no-sd 2>$null
                $albedo = Get-ChildItem -LiteralPath $skinDir -Filter "*Albedo*" -File -ErrorAction SilentlyContinue | Select-Object -First 1
                if (-not $albedo) { $albedo = Get-ChildItem -LiteralPath $skinDir -Filter "*.png" -File -ErrorAction SilentlyContinue | Select-Object -First 1 }
                if ($albedo) {
                    Copy-Item -LiteralPath $albedo.FullName -Destination $texturePath -Force
                    $ok = $true
                }
            } catch { }
        }
    }
    if (-not $ok) { Create-RealTexture -Path $texturePath -Width $Width -Height $Height -Color "#2a2a3a" }
    Write-Log "Ship texture created: $texturePath" "SUCCESS"
}

function Generate-ShipModel {
    param(
        [string]$Name, [string]$Description, [string]$OutputDir, [hashtable]$Specs,
        [switch]$UseAI, [string]$OllamaModel, [string]$BlenderPath,
        [int]$Facings = 120, [int]$FrameWidth = 150, [int]$FrameHeight = 150, [int]$Columns = 10
    )
    $modelPath = Join-Path $OutputDir "$Name`_model.obj"
    $glbPath = Join-Path $OutputDir "$Name`_model.glb"
    Ensure-Dir $OutputDir
    $ok = $false
    $py = (Get-Command python -ErrorAction SilentlyContinue).Source
    $pipe = Join-Path $PSScriptRoot "tx_ai_pipeline.py"
    if ($UseAI -and $py -and (Test-Path -LiteralPath $pipe)) {
        Write-Log "Trying Shared TRELLIS concept-mesh via tx_ai_pipeline..." "INFO"
        $theme = if ($Description) { $Description } else { $Name }
        $concept = Join-Path $PSScriptRoot "References\$Name.png"
        if (-not (Test-Path -LiteralPath $concept)) {
            $concept = Join-Path $PSScriptRoot "References\space_whale_concept.png"
        }
        $prompt = "cinematic 3D concept, three-quarter view, single $theme capital ship sculpt, studio lighting. Not a 2D sprite, not top-down."
        $cmArgs = @($pipe, "concept-mesh", "--prompt", $prompt, "--out", $glbPath, "--id", $Name)
        if (Test-Path -LiteralPath $concept) { $cmArgs += @("--concept", $concept) }
        & $py @cmArgs
        if ($LASTEXITCODE -eq 0 -and (Test-Path -LiteralPath $glbPath)) {
            $ok = $true
            $modelPath = $glbPath
        }
    }
    # Prefer Shared blender mesh exporter when TRELLIS did not produce a model
    $meshPy = Join-Path (Split-Path -Parent $PSScriptRoot) "Shared\blender_aamt_mesh.py"
    if (-not $ok -and $BlenderPath -and (Test-Path $BlenderPath) -and (Test-Path $meshPy)) {
        Write-Log "Using Shared blender_aamt_mesh.py for ship model..." "INFO"
        try {
            & $BlenderPath --background --python $meshPy -- --theme $(if ($Description) { $Description } else { $Name }) --out $modelPath 2>$null
            if (Test-Path -LiteralPath $modelPath) { $ok = $true }
        } catch { }
    }
    if (-not $ok) { Create-RealModel -Path $modelPath -Name $Name }
    Write-Log "Ship model created: $modelPath" "SUCCESS"
}

function Generate-ShipSpritesheet {
    param(
        [string]$Name, [string]$Description, [string]$OutputDir, [hashtable]$Specs,
        [switch]$UseAI, [string]$OllamaModel, [int]$Facings = 120,
        [int]$FrameWidth = 150, [int]$FrameHeight = 150, [int]$Columns = 10, [int]$Rows = 12,
        [string]$NovaDriftStyle = "", [string]$BlenderPath = "", [string]$ModelPath = ""
    )
    $sheetPath = Join-Path $OutputDir "$Name.jpg"
    Ensure-Dir $OutputDir
    $commonExport = Join-Path (Split-Path -Parent $PSScriptRoot) "Common\blender_asset_spritesheet_export.py"
    $shipExport = Join-Path (Split-Path -Parent $PSScriptRoot) "Common\blender_ship_spritesheet_export.py"
    $ok = $false
    if ($ModelPath -and (Test-Path $ModelPath) -and $BlenderPath -and (Test-Path $BlenderPath)) {
        $script = if (Test-Path $shipExport) { $shipExport } else { $commonExport }
        if (Test-Path $script) {
            Write-Log "Using Blender spritesheet export: $script" "INFO"
            try {
                & $BlenderPath --background --python $script -- --model $ModelPath --out $sheetPath --facings $Facings --columns $Columns 2>$null
                if (Test-Path -LiteralPath $sheetPath) { $ok = $true }
            } catch { }
        }
    }
    if (-not $ok) {
        $rows = if ($Rows -gt 0) { $Rows } else { [math]::Ceiling($Facings / [math]::Max(1, $Columns)) }
        Create-RealSpritesheet -Path $sheetPath -Columns $Columns -Rows $rows -Cell $FrameWidth -Color "#4488ff"
    }
    Write-Log "Ship spritesheet created: $sheetPath" "SUCCESS"
}

function Generate-ShipHeroImage {
    param(
        [string]$Name, [string]$Description, [string]$OutputDir, [hashtable]$Specs,
        [switch]$UseAI, [string]$OllamaModel, [string]$BlenderPath = "", [string]$ModelPath = ""
    )
    $heroPath = Join-Path $OutputDir "$Name`Large.jpg"
    Create-RealSpritesheet -Path $heroPath -Columns 1 -Rows 1 -Cell 320 -Color "#7ec8ff"
    Write-Log "Hero image created: $heroPath" "SUCCESS"
}

function Generate-ShipXML {
    param([string]$Name, [string]$OutputDir, [int]$Facings = 120, [int]$FrameWidth = 150, [int]$FrameHeight = 150)
    $xmlPath = Join-Path $OutputDir "$Name`_ImageReference.xml"
    $viewportRatio = 0.005625
    $xmlContent = @"
<!-- Image Reference for $Name -->
<Image imageID="&rs$Name`Image;" imageWidth="$FrameWidth" imageHeight="$FrameHeight" rotationCount="$Facings" viewportRatio="$viewportRatio" rotationOffset="17" />
<HeroImage imageID="&rs$Name`Large;" imageWidth="320" imageHeight="320"/>
"@
    Set-Content -Path $xmlPath -Value $xmlContent -Encoding UTF8
    Write-Log "XML reference created: $xmlPath" "SUCCESS"
}

function Generate-ShipAsset {
    param(
        [string]$Name, [string]$Description, [string]$OutputDir, [hashtable]$Specs,
        [switch]$UseAI, [string]$OllamaModel, [string]$BlenderPath,
        [int]$Facings = 120, [int]$FrameWidth = 150, [int]$FrameHeight = 150,
        [int]$SpritesheetColumns = 10, [string]$NovaDriftStyle = ""
    )
    Write-Log "Generating complete ship asset package with $Facings facings..." "INFO"
    $spritesheetRows = [math]::Ceiling($Facings / $SpritesheetColumns)
    $ModelPath = Join-Path $OutputDir "$Name`_model.obj"
    Generate-ShipSpritesheet -Name $Name -Description $Description -OutputDir $OutputDir -Specs $Specs -UseAI:$UseAI -OllamaModel $OllamaModel -Facings $Facings -FrameWidth $FrameWidth -FrameHeight $FrameHeight -Columns $SpritesheetColumns -Rows $spritesheetRows -NovaDriftStyle $NovaDriftStyle -BlenderPath $BlenderPath -ModelPath $ModelPath
    Generate-ShipHeroImage -Name $Name -Description $Description -OutputDir $OutputDir -Specs $Specs -UseAI:$UseAI -OllamaModel $OllamaModel -BlenderPath $BlenderPath -ModelPath $ModelPath
    Generate-ShipModel -Name $Name -Description $Description -OutputDir $OutputDir -Specs $Specs -UseAI:$UseAI -OllamaModel $OllamaModel -BlenderPath $BlenderPath -Facings $Facings -FrameWidth $FrameWidth -FrameHeight $FrameHeight -Columns $SpritesheetColumns
    Generate-Icon -Name "$Name`_Icon" -Description "Icon for $Description" -OutputDir $OutputDir -Specs $Specs -UseAI:$UseAI -OllamaModel $OllamaModel -Size $Specs.IconSize
    Generate-ShipXML -Name $Name -OutputDir $OutputDir -Facings $Facings -FrameWidth $FrameWidth -FrameHeight $FrameHeight
}

function Generate-PlanetAsset {
    param(
        [string]$Name, [string]$Description, [string]$OutputDir, [hashtable]$Specs,
        [switch]$UseAI, [string]$OllamaModel, [string]$BlenderPath
    )
    Ensure-Dir $OutputDir
    $planetPath = Join-Path $OutputDir "$Name`_planet.png"
    $seed = [math]::Abs($Name.GetHashCode() % 100000)
    $ok = $false
    if ($UseAI) {
        $prompt = "Generate a planet surface icon for Transcendence: $Description. Circular planet with atmosphere."
        $ok = Invoke-TxAiTexture -Prompt $prompt -OutputDir $OutputDir -DestPath $planetPath -AssetType Planet -OllamaModel $OllamaModel -Size 256
    }
    if (-not $ok) {
        Invoke-TxProcedural -Args @("planet", "--path", $planetPath, "--size", "256", "--seed", "$seed")
    }
    Write-Log "Planet asset created: $planetPath" "SUCCESS"
}

function Generate-Spritesheet {
    param(
        [string]$Name, [string]$Description, [string]$OutputDir, [hashtable]$Specs,
        [int]$Columns, [int]$Rows, [string]$ResourceName,
        [string]$BlenderPath = "", [string]$ModelPath = "",
        [string]$AssetType = "item", [string]$GameFormat = "Transcendence", [string]$OutputFormat = "PNG"
    )
    $cell = if ($Specs.IconSize) { [int]$Specs.IconSize } else { 64 }
    $ext = if ($OutputFormat -eq "JPG") { "jpg" } else { "png" }
    $sheetPath = Join-Path $OutputDir "$Name`_spritesheet.$ext"
    # Prefer Common blender asset spritesheet when model+blender available
    $commonExport = Join-Path (Split-Path -Parent $PSScriptRoot) "Common\blender_asset_spritesheet_export.py"
    if ($ModelPath -and (Test-Path $ModelPath) -and $BlenderPath -and (Test-Path $BlenderPath) -and (Test-Path $commonExport)) {
        Write-Log "Using Common blender_asset_spritesheet_export.py..." "INFO"
        & $BlenderPath --background --python $commonExport -- --model $ModelPath --out $sheetPath --columns $Columns --rows $Rows
        if (Test-Path $sheetPath) {
            Write-Log "Spritesheet created: $sheetPath" "SUCCESS"
            return
        }
    }
    Create-RealSpritesheet -Path $sheetPath -Columns $Columns -Rows $Rows -Cell $cell -Color "#4488ff"
    Write-Log "Spritesheet created: $sheetPath" "SUCCESS"
}

function Generate-AudioAsset {
    param(
        [string]$Name, [string]$Description, [string]$OutputDir, [hashtable]$Specs,
        [switch]$UseAI, [string]$OllamaModel, [int]$Duration = 3, [int]$SampleRate = 44100, [string]$AudioType = "Effect"
    )
    Ensure-Dir $OutputDir
    $audioPath = Join-Path $OutputDir "$Name.wav"
    $arch = switch -Regex ($AudioType) {
        "UI|Interface|Click" { "ui" }
        "Ambient|Ambience|Loop" { "ambience" }
        "Weapon|Laser|Gun" { "laser" }
        "Impact|Hit|Crash" { "impact" }
        default { "ship" }
    }
    $prompt = if ($Description) {
        "Transcendence $AudioType: $Description. Short game SFX, no music, no speech."
    } else {
        "Transcendence $Name $AudioType game sound effect, short SFX, no music, no speech"
    }
    if (-not (Invoke-TxAiAudio -Prompt $prompt -DestPath $audioPath -Duration $Duration -Archetype $arch)) {
        throw "Shared audio stage failed for $audioPath"
    }
    Write-Log "Audio asset created: $audioPath" "SUCCESS"
}

function Generate-BeaconAsset {
    param(
        [string]$Name, [string]$Description, [string]$OutputDir, [hashtable]$Specs,
        [switch]$UseAI, [string]$OllamaModel, [string]$BlenderPath = "", [string]$BeaconColor = "Green"
    )
    Ensure-Dir $OutputDir
    $inactivePath = Join-Path $OutputDir "${Name}_Inactive.png"
    $activePath = Join-Path $OutputDir "${Name}_Active.png"
    Create-RealBeacon -InactivePath $inactivePath -ActivePath $activePath -InactiveSize 32 -ActiveSize 150 -Color $BeaconColor
    Write-Log "Beacon assets created: $inactivePath / $activePath" "SUCCESS"
}

function Generate-PowerIcon {
    param(
        [string]$Name, [string]$Description, [string]$OutputDir, [hashtable]$Specs,
        [switch]$UseAI, [string]$OllamaModel, [int]$Size = 96,
        [string]$IconStyle = "Crystal", [string]$IconColor = "Green"
    )
    Ensure-Dir $OutputDir
    $iconPath = Join-Path $OutputDir "$Name.png"
    $ok = $false
    if ($UseAI) {
        $prompt = "Generate a $IconStyle power ability icon in $IconColor for Transcendence: $Description. ${Size}x${Size}."
        $ok = Invoke-TxAiTexture -Prompt $prompt -OutputDir $OutputDir -DestPath $iconPath -AssetType Icon -OllamaModel $OllamaModel -Size $Size
    }
    if (-not $ok) { Create-RealPowerIcon -Path $iconPath -Size $Size -Style $IconStyle -Color $IconColor }
    Write-Log "Power icon created: $iconPath" "SUCCESS"
}

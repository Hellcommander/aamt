# ChooseYourFighter.ps1
# AI-Assisted Modding Tools (AAMT) — Caves of Qud
# Import Recur/saves → CoQ tile replacement + unfiltered detailed art (fighter & minions).

[CmdletBinding()]
param(
    [ValidateSet("List", "Import", "Tile", "Art", "Gui", "Install")]
    [string]$Action = "List",

    [string]$Path,

    [string]$Output,

    [string]$UserData = "$env:USERPROFILE\AppData\LocalLow\Freehold Games\CavesOfQud",

    [ValidateSet("vanilla", "2x", "3x", "4x")]
    [string]$TileSize = "vanilla",

    [ValidateSet("classic", "truecolor")]
    [string]$ColorMode = "truecolor",

    [switch]$Animated,

    [int]$Frames = 8,

    # Detailed painting / SD draft / folder of keyframes. Truecolor never stamps a silhouette.
    [string]$FromImage,

    # Canonical body painting (mutations). Auto-pinned on first bake as base\{id}_base.png.
    [string]$BaseImage,

    # Outfit overlay / updated portrait. Does not replace the base body.
    [string]$GearImage,

    [switch]$SaveBase,

    # Rebake from pinned base; optional SD img2img or -GearImage for the new outfit.
    [switch]$UpdateGear,

    [string[]]$Overlay,

    [string]$PinOverlay,

    [switch]$ListOverlays,

    [switch]$NoAutoOverlays,

    [switch]$NoSD,

    [switch]$AllowSilhouette,

    # Base body + one PNG per mutation feature; Arendeth_CYFTiles stacks the ones the player has in game
    [switch]$Layered,

    # Head drawn on layered sheets; auto = the fighter's headStyle, cat for feline fighters, else from its name/genotype/mutations
    [ValidateSet("auto", "cat", "plain", "canine", "equine", "avian", "reptile", "insect", "fish", "robot", "skull", "fungal", "plant")]
    [string]$HeadStyle = "auto",

    # Truecolor: bake in Bright Qud's palette (Bright Qud then only adds its outline/shadow)
    [switch]$BrightPalette,

    # Unfiltered art (UncensoredCharacterImageGenerator)
    [switch]$GenerateDetailedArt,
    [switch]$GenerateMinionArt,
    [switch]$NoBroodlingsInScene,
    [switch]$NoConjoinedInScene,
    [int]$BroodlingLimit = 3,
    [int]$MinionLimit = 12,
    [ValidateSet("all", "followers", "broodlings", "conjoined")]
    [string]$MinionFilter = "all",

    [switch]$GeneratePortrait, # alias of GenerateDetailedArt

    # Character-sheet portrait for Arendeth_CYFTiles (Install / Tile -InstallMod): any PNG, e.g.
    # SD art from -Action Art or cyf_compose_fighter.py --portrait; installed as Textures\Portraits\<id>.png.
    # Without it, Install copies the work folder's own Textures\Portraits\<id>.png if there is one.
    [string]$PortraitImage,

    [switch]$Pretty,

    # Copy tile PNGs + rebuild CYF xml into Mods/Arendeth_CYFTiles (requires Kernelmethod CYF)
    [switch]$InstallMod,

    [string]$ModRoot
)

$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$importer = Join-Path $here "qud_fighter_import.py"
$tiler = Join-Path $here "qud_fighter_tile_generator.py"
$portraitScript = Join-Path (Split-Path $here -Parent) "UncensoredCharacterImageGenerator.ps1"

if ($GeneratePortrait) { $GenerateDetailedArt = $true }

function Get-CYFModRoot {
    if (-not [string]::IsNullOrWhiteSpace($ModRoot)) { return $ModRoot }
    $root = Join-Path $UserData "Mods\Arendeth_CYFTiles"
    return $root
}

function Escape-XmlText([string]$Text) {
    if ($null -eq $Text) { return "" }
    return ((($Text -replace '&', '&amp;') -replace '<', '&lt;') -replace '>', '&gt;')
}

function Escape-XmlAttr([string]$Text) {
    return ((Escape-XmlText $Text) -replace '"', '&quot;')
}

function Get-CYFAnimationFromManifest($Man) {
    $length = 160
    $framesAttr = ""
    $part = [string]$Man.suggestedAnimationPart
    if ($part -match 'AnimationLength="(\d+)"') { $length = [int]$Matches[1] }
    if ($part -match 'TileAnimationFrames="([^"]+)"') { $framesAttr = $Matches[1] }
    if ([string]::IsNullOrWhiteSpace($framesAttr) -and $Man.frames) {
        $rels = @()
        $i = 0
        $n = @($Man.frames).Count
        if ($n -lt 1) { $n = 1 }
        $step = [Math]::Max(1, [int]($length / $n))
        foreach ($fp in @($Man.frames)) {
            $name = [IO.Path]::GetFileName([string]$fp)
            $rels += ("{0}=Creatures/{1}" -f ($i * $step), $name)
            $i++
        }
        $framesAttr = $rels -join ","
    }
    return @{ Length = $length; Frames = $framesAttr }
}

function Rebuild-CYFModXml {
    param([string]$Root)
    $fightersDir = Join-Path $Root "Fighters"
    New-Item -ItemType Directory -Path $fightersDir -Force | Out-Null
    $entries = @()
    Get-ChildItem -Path $fightersDir -Directory -ErrorAction SilentlyContinue | ForEach-Object {
        $tileJson = Get-ChildItem $_.FullName -Filter "*.tile.json" | Select-Object -First 1
        if (-not $tileJson) { return }
        $man = Get-Content -Raw $tileJson.FullName | ConvertFrom-Json
        $id = $_.Name
        $fighterJson = Get-ChildItem $_.FullName -Filter "*.fighter.json" | Select-Object -First 1
        $name = $id
        $geno = "Mutated Human"
        $desc = $name
        if ($fighterJson) {
            $fj = Get-Content -Raw $fighterJson.FullName | ConvertFrom-Json
            if ($fj.name) { $name = [string]$fj.name }
            if ($fj.genotype) { $geno = [string]$fj.genotype }
            if ($fj.promptDescription) { $desc = [string]$fj.promptDescription }
            elseif ($fj.description) { $desc = [string]$fj.description }
        }
        if ($geno -match 'Genotype$') { $geno = "Mutated Human" }
        $anim = Get-CYFAnimationFromManifest $man
        $tileRel = if ($man.renderTile) { [string]$man.renderTile } else { "Creatures/$id.png" }
        $fg = if ($man.foreground) { [string]$man.foreground } else { "y" }
        $det = if ($man.detail) { [string]$man.detail } else { "W" }
        $mode = if ($man.colorMode) { [string]$man.colorMode } else { "classic" }
        $layerSet = $man.layerSet
        $entries += [pscustomobject]@{
            LayerSet    = $layerSet
            Id          = $id
            Name        = $name
            Genotype    = $geno
            Tile        = $tileRel
            Foreground  = $fg
            Detail      = $det
            ColorMode   = $mode
            AnimLength  = $anim.Length
            AnimFrames  = $anim.Frames
            Description = $desc
        }
    }

    $fighterXml = New-Object System.Text.StringBuilder
    [void]$fighterXml.AppendLine('<?xml version="1.0" encoding="utf-8"?>')
    [void]$fighterXml.AppendLine('<cyffighters Encoding="utf-8">')
    foreach ($e in $entries) {
        $line = '  <fighter ID="{0}" Name="{1}" Tile="{2}" Foreground="{3}" Detail="{4}" ColorMode="{5}" AnimationLength="{6}"' -f @(
            (Escape-XmlAttr $e.Id),
            (Escape-XmlAttr $e.Name),
            (Escape-XmlAttr $e.Tile),
            (Escape-XmlAttr $e.Foreground),
            (Escape-XmlAttr $e.Detail),
            (Escape-XmlAttr $e.ColorMode),
            $e.AnimLength
        )
        if ($e.AnimFrames) {
            $line += (' TileAnimationFrames="{0}"' -f (Escape-XmlAttr $e.AnimFrames))
        }
        $ls = $e.LayerSet
        $plans = @()
        if ($ls) { $plans = @(@($ls.plans) | Where-Object { $_ -and $_.id -and $_.sheet }) }
        if ($plans.Count -gt 0) {
            $size = @(@($ls.tileSize) | Where-Object { $_ })
            if ($size.Count -eq 2) {
                $line += (' LayerTileWidth="{0}" LayerTileHeight="{1}"' -f [int]$size[0], [int]$size[1])
            }
            if ($ls.brightQudFallback -eq $false) { $line += ' BrightQudFallback="false"' }
            $hide = @(@($ls.hideLayers) | Where-Object { $_ } | ForEach-Object { [string]$_ })
            if ($hide.Count -gt 0) { $line += (' HideLayers="{0}"' -f (Escape-XmlAttr ($hide -join ","))) }
            $tileHide = @(@($ls.tileHideLayers) | Where-Object { $_ } | ForEach-Object { [string]$_ })
            if ($tileHide.Count -gt 0) { $line += (' TileHideLayers="{0}"' -f (Escape-XmlAttr ($tileHide -join ","))) }
        }
        $line += ">"
        [void]$fighterXml.AppendLine($line)
        [void]$fighterXml.AppendLine(('    <description>{0}</description>' -f (Escape-XmlText $e.Description)))
        # Layered fighters: one <plan> per body-plan sheet (Textures/<sheet>), one
        # <layer> per sheet row; the mod picks the plan from the player's anatomy.
        foreach ($pl in $plans) {
            $anat = @(@($pl.anatomies) | Where-Object { $_ } | ForEach-Object { [string]$_ })
            $baseFrames = 1
            if ($pl.base -and [int]$pl.base.frames -gt 0) { $baseFrames = [int]$pl.base.frames }
            $grips = @(@($pl.grips) | Where-Object { $null -ne $_ } | ForEach-Object { '{0},{1}' -f [int]$_[0], [int]$_[1] }) -join ";"
            $gripAttr = ""
            if ($grips) { $gripAttr = ' Grips="{0}"' -f $grips }
            [void]$fighterXml.AppendLine(('    <plan ID="{0}" Sheet="{1}" Anatomies="{2}" BaseFrames="{3}"{4}>' -f @(
                (Escape-XmlAttr ([string]$pl.id)),
                (Escape-XmlAttr ([string]$pl.sheet)),
                (Escape-XmlAttr ($anat -join ",")),
                $baseFrames,
                $gripAttr
            )))
            foreach ($l in @(@($pl.layers) | Where-Object { $_ })) {
                $ll = '      <layer ID="{0}" Z="{1}"' -f (Escape-XmlAttr ([string]$l.id)), (Escape-XmlAttr ([string]$l.z))
                if ($null -ne $l.row) { $ll += (' Row="{0}" Frames="{1}"' -f [int]$l.row, [Math]::Max(1, [int]$l.frames)) }
                foreach ($k in @("mutations", "equipped", "effects", "limbs", "covers", "unless")) {
                    $vals = @(@($l.$k) | Where-Object { $_ } | ForEach-Object { [string]$_ })
                    if ($vals.Count -gt 0) {
                        $attr = $k.Substring(0, 1).ToUpper() + $k.Substring(1)
                        $ll += (' {0}="{1}"' -f $attr, (Escape-XmlAttr ($vals -join ",")))
                    }
                }
                if ([int]$l.minLevel -gt 0) { $ll += (' MinLevel="{0}"' -f [int]$l.minLevel) }
                if ($l.requires) { $ll += (' Requires="{0}"' -f (Escape-XmlAttr ([string]$l.requires))) }
                if ([int]$l.fade -gt 0) { $ll += (' Fade="{0}"' -f [int]$l.fade) }
                [void]$fighterXml.AppendLine($ll + ' />')
            }
            [void]$fighterXml.AppendLine('    </plan>')
        }
        [void]$fighterXml.AppendLine('  </fighter>')
    }
    [void]$fighterXml.AppendLine('</cyffighters>')
    [System.IO.File]::WriteAllText((Join-Path $Root "Fighters.xml"), $fighterXml.ToString(), [Text.UTF8Encoding]::new($false))

    $emb = New-Object System.Text.StringBuilder
    [void]$emb.AppendLine('<?xml version="1.0" encoding="utf-8"?>')
    [void]$emb.AppendLine('<embarkmodules Encoding="utf-8">')
    [void]$emb.AppendLine('  <module Class="XRL.CharacterBuilds.Qud.QudPregenModule">')
    [void]$emb.AppendLine('    <pregens>')
    foreach ($e in $entries) {
        [void]$emb.AppendLine(('      <pregen Name="{0}" Genotype="{1}" Tile="{2}" Foreground="{3}" Detail="{4}" Background="k">' -f @(
            (Escape-XmlAttr $e.Name),
            (Escape-XmlAttr $e.Genotype),
            (Escape-XmlAttr $e.Tile),
            (Escape-XmlAttr $e.Foreground),
            (Escape-XmlAttr $e.Detail)
        )))
        [void]$emb.AppendLine('        <code></code>')
        [void]$emb.AppendLine('        <description>')
        [void]$emb.AppendLine((Escape-XmlText $e.Description))
        [void]$emb.AppendLine('        </description>')
        [void]$emb.AppendLine('      </pregen>')
    }
    [void]$emb.AppendLine('    </pregens>')
    [void]$emb.AppendLine('  </module>')
    [void]$emb.AppendLine('</embarkmodules>')
    [System.IO.File]::WriteAllText((Join-Path $Root "EmbarkModules.xml"), $emb.ToString(), [Text.UTF8Encoding]::new($false))

    $cyfXml = New-Object System.Text.StringBuilder
    [void]$cyfXml.AppendLine('<?xml version="1.0" encoding="utf-8"?>')
    [void]$cyfXml.AppendLine('<KernelmethodChooseYourFighter Encoding="utf-8">')
    [void]$cyfXml.AppendLine('  <group ID="Arendeth_CYFTiles" Name="- Arendeth Character Looks">')
    foreach ($e in $entries) {
        $modelId = "Arendeth_CYF_" + $e.Id
        [void]$cyfXml.AppendLine(('    <model ID="{0}" Name="{1}">' -f (Escape-XmlAttr $modelId), (Escape-XmlAttr $e.Name)))
        [void]$cyfXml.AppendLine(('      <tile Path="{0}" Foreground="{1}" DetailColor="{2}" />' -f @(
            (Escape-XmlAttr $e.Tile),
            (Escape-XmlAttr $e.Foreground),
            (Escape-XmlAttr $e.Detail)
        )))
        [void]$cyfXml.AppendLine('    </model>')
    }
    [void]$cyfXml.AppendLine('  </group>')
    [void]$cyfXml.AppendLine('</KernelmethodChooseYourFighter>')
    [System.IO.File]::WriteAllText((Join-Path $Root "ChooseYourFighter.xml"), $cyfXml.ToString(), [Text.UTF8Encoding]::new($false))

    $anyTrue = @($entries | Where-Object { $_.ColorMode -eq "truecolor" }).Count -gt 0
    $modconfigPath = Join-Path $Root "modconfig.json"
    if ($anyTrue -or -not (Test-Path $modconfigPath)) {
        '{"shaderMode": 1}' + [Environment]::NewLine | Set-Content -Path $modconfigPath -Encoding UTF8
    }
    return $entries
}

function Install-CYFOutput {
    param([string]$WorkOut)
    if ([string]::IsNullOrWhiteSpace($WorkOut) -or -not (Test-Path $WorkOut)) {
        throw "Install requires -Path to a CYF fighter output folder (contains Textures\Creatures and *.tile.json)."
    }
    $root = Get-CYFModRoot
    if (-not (Test-Path (Join-Path $root "manifest.json"))) {
        throw "Arendeth_CYFTiles missing at $root - enable Kernelmethod Choose Your Fighter and keep Mods\Arendeth_CYFTiles."
    }
    $work = (Resolve-Path $WorkOut).Path
    $tileJson = Get-ChildItem $work -Filter "*.tile.json" -File | Select-Object -First 1
    if (-not $tileJson) {
        throw "No *.tile.json in $work"
    }
    $id = [IO.Path]::GetFileNameWithoutExtension($tileJson.Name) -replace '\.tile$', ''
    $texSrc = Join-Path $work "Textures\Creatures"
    if (-not (Test-Path $texSrc)) {
        throw "Missing Textures\Creatures under $work"
    }
    $texDst = Join-Path $root "Textures\Creatures"
    New-Item -ItemType Directory -Path $texDst -Force | Out-Null
    $copied = @()
    Get-ChildItem $texSrc -Filter "$id.png" -File | ForEach-Object {
        Copy-Item $_.FullName (Join-Path $texDst $_.Name) -Force
        $copied += $_.Name
    }
    Get-ChildItem $texSrc -Filter "$id`_frame*.png" -File | ForEach-Object {
        Copy-Item $_.FullName (Join-Path $texDst $_.Name) -Force
        $copied += $_.Name
    }
    # Layered fighters: one sheet per body plan under Textures\Layers\<id>\.
    $layerSrc = Join-Path $work "Textures\Layers\$id"
    if (Test-Path $layerSrc) {
        $layerDst = Join-Path $root "Textures\Layers\$id"
        New-Item -ItemType Directory -Path $layerDst -Force | Out-Null
        Get-ChildItem $layerSrc -Filter "*.png" -File | ForEach-Object {
            Copy-Item $_.FullName (Join-Path $layerDst $_.Name) -Force
            $copied += "Layers/$id/" + $_.Name
        }
    }
    if ($copied.Count -lt 1) {
        throw "No $id.png / $id`_frame*.png under $texSrc"
    }
    # Character-sheet portrait (CYFPortrait.cs): -PortraitImage wins over the work folder's own.
    $portraitSrc = $null
    if (-not [string]::IsNullOrWhiteSpace($PortraitImage)) {
        if (-not (Test-Path $PortraitImage -PathType Leaf)) { throw "PortraitImage not found: $PortraitImage" }
        if ([IO.Path]::GetExtension($PortraitImage) -ne ".png") { throw "PortraitImage must be a PNG: $PortraitImage" }
        $portraitSrc = (Resolve-Path $PortraitImage).Path
    } else {
        $own = Join-Path $work "Textures\Portraits\$id.png"
        if (Test-Path $own -PathType Leaf) { $portraitSrc = $own }
    }
    if ($portraitSrc) {
        $portraitDst = Join-Path $root "Textures\Portraits"
        New-Item -ItemType Directory -Path $portraitDst -Force | Out-Null
        Copy-Item $portraitSrc (Join-Path $portraitDst "$id.png") -Force
        $copied += "Portraits/$id.png"
    }
    # Layered portrait (cyf_portrait_layers.py): Textures\Portraits\<id>\portrait.xml + layer PNGs,
    # including the items\ subfolder of equipment layers (cyf_portrait_items.py --fitted).
    $layeredSrc = Join-Path $work "Textures\Portraits\$id"
    if (Test-Path (Join-Path $layeredSrc "portrait.xml")) {
        $layeredDst = Join-Path $root "Textures\Portraits\$id"
        New-Item -ItemType Directory -Path $layeredDst -Force | Out-Null
        $srcFull = (Resolve-Path $layeredSrc).Path.TrimEnd('\') + '\'
        Get-ChildItem $layeredSrc -File -Recurse | Where-Object { $_.Extension -in ".png", ".xml" } | ForEach-Object {
            $rel = $_.FullName.Substring($srcFull.Length)
            $dst = Join-Path $layeredDst $rel
            New-Item -ItemType Directory -Path (Split-Path $dst) -Force | Out-Null
            Copy-Item $_.FullName $dst -Force
            $copied += "Portraits/$id/" + ($rel -replace '\\', '/')
        }
    }
    $meta = Join-Path $root "Fighters\$id"
    New-Item -ItemType Directory -Path $meta -Force | Out-Null
    Copy-Item $tileJson.FullName (Join-Path $meta $tileJson.Name) -Force
    $fighterJson = Get-ChildItem $work -Filter "*.fighter.json" -File | Select-Object -First 1
    if ($fighterJson) {
        Copy-Item $fighterJson.FullName (Join-Path $meta $fighterJson.Name) -Force
    }
    $entries = Rebuild-CYFModXml -Root $root
    Write-Host ("Installed {0} into {1} ({2} PNGs). Fighters in mod: {3}" -f $id, $root, $copied.Count, $entries.Count) -ForegroundColor Green
    return @{ ModRoot = $root; Id = $id; Files = $copied; Count = $entries.Count }
}

function Get-PythonExe {
    foreach ($c in @("python", "py")) {
        try {
            $p = Get-Command $c -ErrorAction Stop
            return $p.Source
        } catch {}
    }
    throw "Python not found on PATH. Install Python 3.8+."
}

function Invoke-FighterImport {
    param([string[]]$PyArgs)
    $py = Get-PythonExe
    & $py $importer @PyArgs
    if ($LASTEXITCODE -ne 0) {
        throw "qud_fighter_import.py failed (exit $LASTEXITCODE)"
    }
}

function Invoke-UnfilteredArtJob {
    param(
        [Parameter(Mandatory)][hashtable]$Job,
        [string]$OutDir = ""
    )
    if (-not (Test-Path $portraitScript)) {
        throw "Unfiltered art script missing: $portraitScript"
    }
    $params = @{
        Description   = [string]$Job.description
        CharacterName = [string]$Job.characterName
        GameType      = "Qud"
        Mutations     = @($Job.mutations)
        Traits        = @($Job.traits)
        NoOpen        = $true
    }
    if ($OutDir) {
        $safe = (($Job.characterName -as [string]) -replace '[^\w\-]+', '-')
        if ([string]::IsNullOrWhiteSpace($safe)) { $safe = "art" }
        $params.OutputPath = Join-Path $OutDir ("{0}_{1}.png" -f $Job.kind, $safe)
    }
    Write-Host ("  [art] {0}: {1}" -f $Job.kind, $Job.characterName) -ForegroundColor Yellow
    & $portraitScript @params
}

if ($Action -eq "Gui") {
    $gui = Join-Path $here "ChooseYourFighter-GUI.ps1"
    if (-not (Test-Path $gui)) { throw "GUI script missing: $gui" }
    powershell -STA -NoProfile -ExecutionPolicy Bypass -File $gui
    exit $LASTEXITCODE
}

if ($Action -eq "List") {
    Invoke-FighterImport -PyArgs @("--userdata", $UserData, "list")
    exit 0
}

if ($Action -eq "Import") {
    if ([string]::IsNullOrWhiteSpace($Path)) {
        throw "Import requires -Path (Recur .xml or save folder)."
    }
    $pyArgs = @("--userdata", $UserData, "import", $Path)
    if ($Pretty) { $pyArgs += "--pretty" }
    if (-not [string]::IsNullOrWhiteSpace($Output)) {
        $pyArgs += @("-o", $Output)
    }

    $jsonText = & (Get-PythonExe) $importer @pyArgs
    if ($LASTEXITCODE -ne 0) { throw "Import failed." }

    if ([string]::IsNullOrWhiteSpace($Output)) {
        Write-Output $jsonText
        $fighter = $jsonText | ConvertFrom-Json
    } else {
        Write-Host "Wrote $Output" -ForegroundColor Green
        $fighter = Get-Content -Raw $Output | ConvertFrom-Json
    }

    Write-Host ""
    Write-Host "Fighter: $($fighter.name)  [source=$($fighter.source) fidelity=$($fighter.fidelity)]" -ForegroundColor Cyan
    Write-Host ("  Mutations ({0}): {1}" -f @($fighter.mutationLabels).Count, (($fighter.mutationLabels | Select-Object -First 12) -join ", "))
    Write-Host ("  Broodlings/Conjoined/Followers: {0}/{1}/{2}" -f $fighter.broodlingCount, $fighter.conjoinedCount, $fighter.followerCount)

    if ($GenerateDetailedArt -or $GenerateMinionArt) {
        $artArgs = @("--userdata", $UserData, "art", $(if ($Output) { $Output } else { $Path }), "--pretty", "--minions", "--broodling-limit", "$BroodlingLimit", "--minion-limit", "$MinionLimit")
        if ($NoBroodlingsInScene) { $artArgs += "--no-broodlings" }
        if ($NoConjoinedInScene) { $artArgs += "--no-conjoined" }
        if ($MinionFilter -eq "followers") { $artArgs += "--followers-only" }
        elseif ($MinionFilter -eq "broodlings") { $artArgs += "--broodlings-only" }
        elseif ($MinionFilter -eq "conjoined") { $artArgs += "--conjoined-only" }
        $artJson = & (Get-PythonExe) $importer @artArgs
        if ($LASTEXITCODE -ne 0) { throw "Art payload build failed." }
        $art = $artJson | ConvertFrom-Json
        $artOut = if ($Output) { Split-Path -Parent $Output } else { Join-Path $here "..\Output\Fighters\$($fighter.id)" }
        New-Item -ItemType Directory -Path $artOut -Force | Out-Null
        if ($GenerateDetailedArt) {
            Invoke-UnfilteredArtJob -Job @{
                kind          = "fighter"
                characterName = $art.fighter.characterName
                description   = $art.fighter.description
                mutations     = @($art.fighter.mutations)
                traits        = @($art.fighter.traits)
            } -OutDir $artOut
        }
        if ($GenerateMinionArt) {
            foreach ($m in @($art.minions)) {
                Invoke-UnfilteredArtJob -Job @{
                    kind          = "minion"
                    characterName = $m.characterName
                    description   = $m.description
                    mutations     = @($m.mutations)
                    traits        = @($m.traits)
                } -OutDir $artOut
            }
        }
    }
    exit 0
}

if ($Action -eq "Art") {
    if ([string]::IsNullOrWhiteSpace($Path)) {
        throw "Art requires -Path (Recur/save/.fighter.json)."
    }
    $artArgs = @(
        "--userdata", $UserData, "art", $Path, "--pretty", "--minions",
        "--broodling-limit", "$BroodlingLimit", "--minion-limit", "$MinionLimit"
    )
    if ($NoBroodlingsInScene) { $artArgs += "--no-broodlings" }
    if ($NoConjoinedInScene) { $artArgs += "--no-conjoined" }
    if ($MinionFilter -eq "followers") { $artArgs += "--followers-only" }
    elseif ($MinionFilter -eq "broodlings") { $artArgs += "--broodlings-only" }
    elseif ($MinionFilter -eq "conjoined") { $artArgs += "--conjoined-only" }
    if ($Output) { $artArgs += @("-o", $Output) }

    $artJson = & (Get-PythonExe) $importer @artArgs
    if ($LASTEXITCODE -ne 0) { throw "Art payload build failed." }

    if ($Output -and -not ($GenerateDetailedArt -or $GenerateMinionArt)) {
        Write-Host "Wrote art payloads: $Output" -ForegroundColor Green
        exit 0
    }

    $art = if ($Output) { Get-Content -Raw $Output | ConvertFrom-Json } else { $artJson | ConvertFrom-Json }
    $artOut = if ($Output) { Split-Path -Parent $Output } else { Join-Path $here "..\Output\Fighters\art" }
    New-Item -ItemType Directory -Path $artOut -Force | Out-Null

    # Default Art action generates fighter + minions unless switches narrow it
    $doFighter = $true
    $doMinions = $true
    if ($GenerateDetailedArt -and -not $GenerateMinionArt) { $doMinions = $false }
    if ($GenerateMinionArt -and -not $GenerateDetailedArt -and -not $GeneratePortrait) { $doFighter = $false }

    if ($doFighter) {
        Invoke-UnfilteredArtJob -Job @{
            kind          = "fighter"
            characterName = $art.fighter.characterName
            description   = $art.fighter.description
            mutations     = @($art.fighter.mutations)
            traits        = @($art.fighter.traits)
        } -OutDir $artOut
    }
    if ($doMinions) {
        foreach ($m in @($art.minions)) {
            Invoke-UnfilteredArtJob -Job @{
                kind          = "minion"
                characterName = $m.characterName
                description   = $m.description
                mutations     = @($m.mutations)
                traits        = @($m.traits)
            } -OutDir $artOut
        }
    }
    Write-Host "Art output folder: $artOut" -ForegroundColor Green
    exit 0
}

if ($Action -eq "Tile") {
    if ($ListOverlays) {
        if ([string]::IsNullOrWhiteSpace($Output) -and -not [string]::IsNullOrWhiteSpace($Path)) {
            if ((Test-Path $Path) -and (Get-Item $Path).PSIsContainer) {
                $Output = $Path
            } elseif ($Path -like "*.fighter.json") {
                $Output = Split-Path -Parent $Path
            }
        }
        if ([string]::IsNullOrWhiteSpace($Output)) {
            throw "List overlays requires -Output (fighter work folder)."
        }
        & (Get-PythonExe) $tiler "--list-overlays" "-o" $Output
        if ($LASTEXITCODE -ne 0) { throw "List overlays failed." }
        exit 0
    }
    if ([string]::IsNullOrWhiteSpace($Path)) {
        throw "Tile requires -Path to a .fighter.json (or Recur/save to import first)."
    }
    $fighterJson = $Path
    $workOut = $Output
    if ($Path -notlike "*.fighter.json" -and $Path -notlike "*.json") {
        $tmpDir = Join-Path $here "..\Output\Fighters\_tmp"
        New-Item -ItemType Directory -Path $tmpDir -Force | Out-Null
        $fighterJson = Join-Path $tmpDir "import.fighter.json"
        & (Get-PythonExe) $importer "--userdata" $UserData "import" $Path "--pretty" "-o" $fighterJson
        if ($LASTEXITCODE -ne 0) { throw "Import failed before tiling." }
    }
    if ([string]::IsNullOrWhiteSpace($workOut)) {
        $id = ([IO.Path]::GetFileNameWithoutExtension($fighterJson) -replace '\.fighter$', '')
        $workOut = Join-Path $here "..\Output\Fighters\$id"
    }
    New-Item -ItemType Directory -Path $workOut -Force | Out-Null

    $tileArgs = @(
        $fighterJson, "-o", $workOut,
        "--size", $TileSize,
        "--color-mode", $ColorMode,
        "--frames", "$Frames"
    )
    if ($Animated) { $tileArgs += "--animated" }
    if (-not [string]::IsNullOrWhiteSpace($FromImage)) { $tileArgs += @("--from-image", $FromImage) }
    if (-not [string]::IsNullOrWhiteSpace($BaseImage)) { $tileArgs += @("--base-image", $BaseImage) }
    if (-not [string]::IsNullOrWhiteSpace($GearImage)) { $tileArgs += @("--gear-image", $GearImage) }
    if ($SaveBase) { $tileArgs += "--save-base" }
    if ($UpdateGear) { $tileArgs += "--update-gear" }
    foreach ($ov in @($Overlay)) {
        if (-not [string]::IsNullOrWhiteSpace($ov)) { $tileArgs += @("--overlay", $ov) }
    }
    if (-not [string]::IsNullOrWhiteSpace($PinOverlay)) { $tileArgs += @("--pin-overlay", $PinOverlay) }
    if ($NoAutoOverlays) { $tileArgs += "--no-auto-overlays" }
    if ($NoSD) { $tileArgs += "--no-sd" }
    if ($AllowSilhouette) { $tileArgs += "--allow-silhouette" }
    if ($Layered) { $tileArgs += "--layered" }
    if ($HeadStyle -and $HeadStyle -ne "auto") { $tileArgs += @("--head-style", $HeadStyle) }
    if ($BrightPalette) { $tileArgs += "--bright-palette" }

    $animNote = if ($Animated) { ', animated' } else { '' }
    Write-Host "Generating CoQ tile ($ColorMode, $TileSize$animNote - detailed art / kitty layout)..." -ForegroundColor Cyan
    & (Get-PythonExe) $tiler @tileArgs
    if ($LASTEXITCODE -ne 0) { throw "Tile generation failed." }
    if ($Layered) {
        # Crystal Delight body (no head, no feet, 4 prism arms): a crystal layer over the biped person.
        & (Get-PythonExe) (Join-Path $here "cyf_crystal_layer.py") $workOut
        if ($LASTEXITCODE -ne 0) { Write-Warning "Crystal layer not added." }
    }
    Write-Host "Output: $workOut" -ForegroundColor Green
    if ($InstallMod) {
        [void](Install-CYFOutput -WorkOut $workOut)
    }
    exit 0
}

if ($Action -eq "Install") {
    if ([string]::IsNullOrWhiteSpace($Path)) {
        throw "Install requires -Path to a CYF fighter output folder."
    }
    [void](Install-CYFOutput -WorkOut $Path)
    exit 0
}

# ChooseYourFighter-GUI.ps1
# Recur/saves → CoQ tile + unfiltered detailed art (fighter scene & per-minion portraits).

if ([System.Threading.Thread]::CurrentThread.GetApartmentState() -ne [System.Threading.ApartmentState]::STA) {
    Write-Host "Relaunching in STA mode..." -ForegroundColor Yellow
    powershell -STA -NoProfile -ExecutionPolicy Bypass -File $MyInvocation.MyCommand.Path
    exit $LASTEXITCODE
}

Add-Type -AssemblyName System.Windows.Forms, System.Drawing -ErrorAction Stop

$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$importer = Join-Path $here "qud_fighter_import.py"
$tiler = Join-Path $here "qud_fighter_tile_generator.py"
$portraitScript = Join-Path (Split-Path $here -Parent) "UncensoredCharacterImageGenerator.ps1"
$userdata = Join-Path $env:USERPROFILE "AppData\LocalLow\Freehold Games\CavesOfQud"
$outDir = Join-Path $here "..\Output\Fighters"
if (-not (Test-Path $outDir)) { New-Item -ItemType Directory -Path $outDir -Force | Out-Null }

function Get-PythonExe {
    foreach ($c in @("python", "py")) {
        try { return (Get-Command $c -ErrorAction Stop).Source } catch {}
    }
    throw "Python not found on PATH."
}

function Invoke-Py([string]$Script, [string[]]$Args) {
    $py = Get-PythonExe
    $all = @($Script) + $Args
    $quoted = $all | ForEach-Object { if ($_ -match '\s') { '"{0}"' -f $_ } else { $_ } }
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $py
    $psi.Arguments = ($quoted -join " ")
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow = $true
    $p = [System.Diagnostics.Process]::Start($psi)
    $stdout = $p.StandardOutput.ReadToEnd()
    $stderr = $p.StandardError.ReadToEnd()
    $p.WaitForExit()
    if ($p.ExitCode -ne 0) {
        throw "Python failed:`n$stderr`n$stdout"
    }
    return $stdout
}

function Invoke-UnfilteredArtJob([hashtable]$Job, [string]$OutFolder) {
    if (-not (Test-Path $portraitScript)) {
        throw "Unfiltered art script missing:`n$portraitScript"
    }
    $safe = (($Job.characterName -as [string]) -replace '[^\w\-]+', '-')
    if ([string]::IsNullOrWhiteSpace($safe)) { $safe = "art" }
    $outPath = Join-Path $OutFolder ("{0}_{1}.png" -f $Job.kind, $safe)
    & $portraitScript `
        -Description ([string]$Job.description) `
        -CharacterName ([string]$Job.characterName) `
        -GameType "Qud" `
        -Mutations @($Job.mutations) `
        -Traits @($Job.traits) `
        -OutputPath $outPath `
        -NoOpen
}

$form = New-Object System.Windows.Forms.Form
$form.Text = "Choose Your Fighter — CoQ Tile + Unfiltered Art"
$form.Size = New-Object System.Drawing.Size(1020, 980)
$form.StartPosition = "CenterScreen"
$form.MinimumSize = New-Object System.Drawing.Size(980, 900)

$lblSources = New-Object System.Windows.Forms.Label
$lblSources.Text = "Recur exports + saves"
$lblSources.Location = New-Object System.Drawing.Point(12, 12)
$lblSources.AutoSize = $true
$form.Controls.Add($lblSources)

$list = New-Object System.Windows.Forms.ListBox
$list.Location = New-Object System.Drawing.Point(12, 36)
$list.Size = New-Object System.Drawing.Size(420, 420)
$list.IntegralHeight = $false
$form.Controls.Add($list)

$btnRefresh = New-Object System.Windows.Forms.Button
$btnRefresh.Text = "Refresh"
$btnRefresh.Location = New-Object System.Drawing.Point(12, 468)
$btnRefresh.Size = New-Object System.Drawing.Size(100, 28)
$form.Controls.Add($btnRefresh)

$btnBrowse = New-Object System.Windows.Forms.Button
$btnBrowse.Text = "Browse..."
$btnBrowse.Location = New-Object System.Drawing.Point(122, 468)
$btnBrowse.Size = New-Object System.Drawing.Size(100, 28)
$form.Controls.Add($btnBrowse)

$btnImportSelected = New-Object System.Windows.Forms.Button
$btnImportSelected.Text = "Load Selected"
$btnImportSelected.Location = New-Object System.Drawing.Point(232, 468)
$btnImportSelected.Size = New-Object System.Drawing.Size(120, 28)
$form.Controls.Add($btnImportSelected)

$lblPreview = New-Object System.Windows.Forms.Label
$lblPreview.Text = "Fighter preview"
$lblPreview.Location = New-Object System.Drawing.Point(450, 12)
$lblPreview.AutoSize = $true
$form.Controls.Add($lblPreview)

$txtPreview = New-Object System.Windows.Forms.TextBox
$txtPreview.Location = New-Object System.Drawing.Point(450, 36)
$txtPreview.Size = New-Object System.Drawing.Size(540, 300)
$txtPreview.Multiline = $true
$txtPreview.ScrollBars = "Vertical"
$txtPreview.Font = New-Object System.Drawing.Font("Consolas", 9)
$txtPreview.ReadOnly = $true
$form.Controls.Add($txtPreview)

# --- Tile group ---
$grpTile = New-Object System.Windows.Forms.GroupBox
$grpTile.Text = "In-game player tile (base body + optional gear overlay)"
$grpTile.Location = New-Object System.Drawing.Point(450, 348)
$grpTile.Size = New-Object System.Drawing.Size(540, 268)
$form.Controls.Add($grpTile)

$lblSize = New-Object System.Windows.Forms.Label
$lblSize.Text = "Size:"
$lblSize.Location = New-Object System.Drawing.Point(12, 28)
$lblSize.AutoSize = $true
$grpTile.Controls.Add($lblSize)

$cmbSize = New-Object System.Windows.Forms.ComboBox
$cmbSize.Location = New-Object System.Drawing.Point(60, 24)
$cmbSize.Size = New-Object System.Drawing.Size(220, 24)
$cmbSize.DropDownStyle = "DropDownList"
[void]$cmbSize.Items.AddRange(@("vanilla (16x24)", "2x (32x48)", "3x (48x72)", "4x (64x96)"))
$cmbSize.SelectedIndex = 0
$grpTile.Controls.Add($cmbSize)

$lblMode = New-Object System.Windows.Forms.Label
$lblMode.Text = "Colors:"
$lblMode.Location = New-Object System.Drawing.Point(300, 28)
$lblMode.AutoSize = $true
$grpTile.Controls.Add($lblMode)

$cmbMode = New-Object System.Windows.Forms.ComboBox
$cmbMode.Location = New-Object System.Drawing.Point(360, 24)
$cmbMode.Size = New-Object System.Drawing.Size(160, 24)
$cmbMode.DropDownStyle = "DropDownList"
[void]$cmbMode.Items.AddRange(@("classic (B/W/A)", "truecolor"))
$cmbMode.SelectedIndex = 1
$grpTile.Controls.Add($cmbMode)

$chkAnimated = New-Object System.Windows.Forms.CheckBox
$chkAnimated.Text = "Animated idle frames + AnimatedMaterialGeneric XML"
$chkAnimated.Location = New-Object System.Drawing.Point(12, 60)
$chkAnimated.AutoSize = $true
$chkAnimated.Checked = $true
$grpTile.Controls.Add($chkAnimated)

$chkKeepDetail = New-Object System.Windows.Forms.CheckBox
$chkKeepDetail.Text = "From detailed art / SD (do not stamp a 2-color silhouette)"
$chkKeepDetail.Location = New-Object System.Drawing.Point(12, 84)
$chkKeepDetail.AutoSize = $true
$chkKeepDetail.Checked = $true
$grpTile.Controls.Add($chkKeepDetail)

$chkInstallMod = New-Object System.Windows.Forms.CheckBox
$chkInstallMod.Text = "Install into Mods/Arendeth_CYFTiles (requires CYF)"
$chkInstallMod.Location = New-Object System.Drawing.Point(12, 108)
$chkInstallMod.AutoSize = $true
$chkInstallMod.Checked = $true
$grpTile.Controls.Add($chkInstallMod)

$lblBase = New-Object System.Windows.Forms.Label
$lblBase.Text = "Base: (auto-pin on first bake)"
$lblBase.Location = New-Object System.Drawing.Point(12, 134)
$lblBase.Size = New-Object System.Drawing.Size(380, 18)
$grpTile.Controls.Add($lblBase)

$btnBase = New-Object System.Windows.Forms.Button
$btnBase.Text = "Base image..."
$btnBase.Location = New-Object System.Drawing.Point(400, 130)
$btnBase.Size = New-Object System.Drawing.Size(120, 24)
$grpTile.Controls.Add($btnBase)

$lblGear = New-Object System.Windows.Forms.Label
$lblGear.Text = "Gear: (optional overlay for outfit swaps)"
$lblGear.Location = New-Object System.Drawing.Point(12, 160)
$lblGear.Size = New-Object System.Drawing.Size(380, 18)
$grpTile.Controls.Add($lblGear)

$btnGear = New-Object System.Windows.Forms.Button
$btnGear.Text = "Gear image..."
$btnGear.Location = New-Object System.Drawing.Point(400, 156)
$btnGear.Size = New-Object System.Drawing.Size(120, 24)
$grpTile.Controls.Add($btnGear)

$chkSaveBase = New-Object System.Windows.Forms.CheckBox
$chkSaveBase.Text = "Overwrite pinned base"
$chkSaveBase.Location = New-Object System.Drawing.Point(12, 186)
$chkSaveBase.AutoSize = $true
$grpTile.Controls.Add($chkSaveBase)

$chkAutoOverlays = New-Object System.Windows.Forms.CheckBox
$chkAutoOverlays.Text = "Auto-match overlays from equipped gear"
$chkAutoOverlays.Location = New-Object System.Drawing.Point(220, 186)
$chkAutoOverlays.AutoSize = $true
$chkAutoOverlays.Checked = $true
$grpTile.Controls.Add($chkAutoOverlays)

$chkUpdateGear = New-Object System.Windows.Forms.CheckBox
$chkUpdateGear.Text = "Gear update from base (keep body, change outfit)"
$chkUpdateGear.Location = New-Object System.Drawing.Point(12, 210)
$chkUpdateGear.AutoSize = $true
$grpTile.Controls.Add($chkUpdateGear)

$btnTile = New-Object System.Windows.Forms.Button
$btnTile.Text = "Generate Tile"
$btnTile.Location = New-Object System.Drawing.Point(12, 232)
$btnTile.Size = New-Object System.Drawing.Size(140, 28)
$grpTile.Controls.Add($btnTile)

# --- Unfiltered art group ---
$grpArt = New-Object System.Windows.Forms.GroupBox
$grpArt.Text = "Unfiltered detailed art (UncensoredCharacterImageGenerator)"
$grpArt.Location = New-Object System.Drawing.Point(12, 624)
$grpArt.Size = New-Object System.Drawing.Size(978, 200)
$form.Controls.Add($grpArt)

$chkDetailedArt = New-Object System.Windows.Forms.CheckBox
$chkDetailedArt.Text = "Generate detailed fighter art (what they really look like)"
$chkDetailedArt.Location = New-Object System.Drawing.Point(12, 28)
$chkDetailedArt.AutoSize = $true
$chkDetailedArt.Checked = $true
$grpArt.Controls.Add($chkDetailedArt)

$chkSceneBrood = New-Object System.Windows.Forms.CheckBox
$chkSceneBrood.Text = "Include a few broodlings in the fighter scene"
$chkSceneBrood.Location = New-Object System.Drawing.Point(40, 56)
$chkSceneBrood.AutoSize = $true
$chkSceneBrood.Checked = $true
$grpArt.Controls.Add($chkSceneBrood)

$chkSceneConj = New-Object System.Windows.Forms.CheckBox
$chkSceneConj.Text = "Include conjoined mates in the fighter scene"
$chkSceneConj.Location = New-Object System.Drawing.Point(40, 80)
$chkSceneConj.AutoSize = $true
$chkSceneConj.Checked = $true
$grpArt.Controls.Add($chkSceneConj)

$chkMinionArt = New-Object System.Windows.Forms.CheckBox
$chkMinionArt.Text = "Also generate separate art for minions / followers"
$chkMinionArt.Location = New-Object System.Drawing.Point(12, 112)
$chkMinionArt.AutoSize = $true
$chkMinionArt.Checked = $true
$grpArt.Controls.Add($chkMinionArt)

$lblMinionFilter = New-Object System.Windows.Forms.Label
$lblMinionFilter.Text = "Minion set:"
$lblMinionFilter.Location = New-Object System.Drawing.Point(40, 144)
$lblMinionFilter.AutoSize = $true
$grpArt.Controls.Add($lblMinionFilter)

$cmbMinionFilter = New-Object System.Windows.Forms.ComboBox
$cmbMinionFilter.Location = New-Object System.Drawing.Point(120, 140)
$cmbMinionFilter.Size = New-Object System.Drawing.Size(280, 24)
$cmbMinionFilter.DropDownStyle = "DropDownList"
[void]$cmbMinionFilter.Items.AddRange(@(
    "All (broodlings + conjoined + followers)",
    "Followers only (normal companions)",
    "Broodlings only",
    "Conjoined only"
))
$cmbMinionFilter.SelectedIndex = 0
$grpArt.Controls.Add($cmbMinionFilter)

$lblArtHint = New-Object System.Windows.Forms.Label
$lblArtHint.Text = "Uses your Tools\UncensoredCharacterImageGenerator (unfiltered). Minion art = one image per companion. Needs SD3 + Ollama."
$lblArtHint.Location = New-Object System.Drawing.Point(12, 176)
$lblArtHint.Size = New-Object System.Drawing.Size(950, 36)
$grpArt.Controls.Add($lblArtHint)

$btnArt = New-Object System.Windows.Forms.Button
$btnArt.Text = "Generate Unfiltered Art"
$btnArt.Location = New-Object System.Drawing.Point(450, 834)
$btnArt.Size = New-Object System.Drawing.Size(200, 36)
$form.Controls.Add($btnArt)

$btnExport = New-Object System.Windows.Forms.Button
$btnExport.Text = "Export JSON only"
$btnExport.Location = New-Object System.Drawing.Point(660, 834)
$btnExport.Size = New-Object System.Drawing.Size(140, 36)
$form.Controls.Add($btnExport)

$status = New-Object System.Windows.Forms.Label
$status.Text = "Ready — Recur export gives companions (followers / broodlings / conjoined)."
$status.Location = New-Object System.Drawing.Point(12, 878)
$status.Size = New-Object System.Drawing.Size(980, 36)
$form.Controls.Add($status)

$script:entries = @()
$script:currentFighter = $null
$script:baseImage = ""
$script:gearImage = ""

function Set-ImageLabel([System.Windows.Forms.Label]$Label, [string]$Prefix, [string]$Path, [string]$Empty) {
    if ([string]::IsNullOrWhiteSpace($Path)) {
        $Label.Text = $Prefix + $Empty
    } else {
        $Label.Text = $Prefix + [IO.Path]::GetFileName($Path)
    }
}

function Pick-Png([string]$Title, [string]$StartDir) {
    $dlg = New-Object System.Windows.Forms.OpenFileDialog
    $dlg.Title = $Title
    $dlg.Filter = "PNG image|*.png|All|*.*"
    if (-not [string]::IsNullOrWhiteSpace($StartDir) -and (Test-Path $StartDir)) {
        $dlg.InitialDirectory = $StartDir
    }
    if ($dlg.ShowDialog() -eq "OK") { return $dlg.FileName }
    return $null
}

function Format-FighterPreview($f) {
    $lines = @()
    $lines += "$($f.name)  |  L$($f.level)  |  $($f.source) ($($f.fidelity))"
    if ($f.type_name) { $lines += "Type: $($f.type_name)" }
    if ($f.genotype -or $f.subtype) { $lines += "Geno/Sub: $($f.genotype) / $($f.subtype)" }
    $lines += "Minions: broodlings=$($f.broodlingCount) conjoined=$($f.conjoinedCount) followers=$($f.followerCount)"
    $lines += ""
    $lines += "MUTATIONS ($($f.mutationLabels.Count))"
    $lines += ($f.mutationLabels -join "`r`n")
    $lines += ""
    $lines += "CYBERNETICS ($($f.cyberneticLabels.Count))"
    $lines += ($(if ($f.cyberneticLabels.Count) { $f.cyberneticLabels -join "`r`n" } else { "(none)" }))
    $lines += ""
    $lines += "EQUIPPED ($($f.equipmentLabels.Count))"
    $lines += ($(if ($f.equipmentLabels.Count) { $f.equipmentLabels -join "`r`n" } else { "(none)" }))
    if ($f.companions -and $f.companions.Count) {
        $lines += ""
        $lines += "COMPANIONS"
        foreach ($c in $f.companions) {
            $role = if ($c.role) { $c.role } else { "follower" }
            $lines += "  - [$role] $($c.name) L$($c.level) ($($c.blueprint))"
        }
    }
    return ($lines -join "`r`n")
}

function Save-CurrentFighterJson {
    $safe = ($script:currentFighter.id -replace '[^\w\-]+', '-')
    if ([string]::IsNullOrWhiteSpace($safe)) { $safe = "fighter" }
    $fighterDir = Join-Path $outDir $safe
    New-Item -ItemType Directory -Path $fighterDir -Force | Out-Null
    $out = Join-Path $fighterDir ("{0}.fighter.json" -f $safe)
    ($script:currentFighter | ConvertTo-Json -Depth 12) | Set-Content -Path $out -Encoding UTF8
    return @{ Json = $out; Dir = $fighterDir; Id = $safe }
}

function Refresh-Sources {
    $status.Text = "Scanning Recur Characters\ and Saves..."
    $form.Refresh()
    $raw = Invoke-Py $importer @("--userdata", $userdata, "list", "--json")
    $data = $raw | ConvertFrom-Json
    $script:entries = @()
    $list.Items.Clear()
    foreach ($r in @($data.recur)) {
        $label = "[Recur] L$($r.level)  $($r.name)"
        $script:entries += [pscustomobject]@{ Label = $label; Path = $r.path }
        [void]$list.Items.Add($label)
    }
    foreach ($s in @($data.saves)) {
        $loc = if ($s.location) { " @ $($s.location)" } else { "" }
        $label = "[Save ] L$($s.level)  $($s.name)$loc"
        $script:entries += [pscustomobject]@{ Label = $label; Path = $s.path }
        [void]$list.Items.Add($label)
    }
    $status.Text = ("Found {0} Recur export(s), {1} save(s)." -f @($data.recur).Count, @($data.saves).Count)
}

function Load-Selected {
    if ($list.SelectedIndex -lt 0) {
        [System.Windows.Forms.MessageBox]::Show("Select a Recur export or save first.", "Choose Your Fighter")
        return
    }
    $entry = $script:entries[$list.SelectedIndex]
    $status.Text = "Importing $($entry.Path)..."
    $form.Refresh()
    try {
        $raw = Invoke-Py $importer @("--userdata", $userdata, "import", $entry.Path, "--pretty")
        $script:currentFighter = $raw | ConvertFrom-Json
        $txtPreview.Text = Format-FighterPreview $script:currentFighter
        $status.Text = "Loaded $($script:currentFighter.name) [brood=$($script:currentFighter.broodlingCount) conj=$($script:currentFighter.conjoinedCount) followers=$($script:currentFighter.followerCount)]"
        $safe = ($script:currentFighter.id -replace '[^\w\-]+', '-')
        Sync-PinnedImages (Join-Path $outDir $safe) $safe
    } catch {
        $status.Text = "Import failed"
        [System.Windows.Forms.MessageBox]::Show("$_", "Import failed", "OK", "Error")
    }
}

function Sync-PinnedImages([string]$Dir, [string]$Id) {
    $base = Join-Path $Dir ("base\{0}_base.png" -f $Id)
    if (Test-Path $base) {
        $script:baseImage = $base
        Set-ImageLabel $lblBase "Base: " $base "(auto-pin on first bake)"
    }
    $gear = Join-Path $Dir ("gear\{0}_gear.png" -f $Id)
    if (Test-Path $gear) {
        $script:gearImage = $gear
        Set-ImageLabel $lblGear "Gear: " $gear "(optional overlay for outfit swaps)"
    }
}

$btnRefresh.Add_Click({ Refresh-Sources })
$btnImportSelected.Add_Click({ Load-Selected })
$list.Add_DoubleClick({ Load-Selected })

$btnBase.Add_Click({
    $start = if ($script:currentFighter) { Join-Path $outDir ($script:currentFighter.id -replace '[^\w\-]+', '-') } else { $outDir }
    $picked = Pick-Png "Canonical body painting (no swappable outfit)" $start
    if ($picked) {
        $script:baseImage = $picked
        Set-ImageLabel $lblBase "Base: " $picked "(auto-pin on first bake)"
    }
})

$btnGear.Add_Click({
    $start = if ($script:currentFighter) { Join-Path $outDir ($script:currentFighter.id -replace '[^\w\-]+', '-') } else { $outDir }
    $picked = Pick-Png "Gear overlay / updated outfit portrait" $start
    if ($picked) {
        $script:gearImage = $picked
        Set-ImageLabel $lblGear "Gear: " $picked "(optional overlay for outfit swaps)"
        $chkUpdateGear.Checked = $true
    }
})

$btnBrowse.Add_Click({
    $dlg = New-Object System.Windows.Forms.OpenFileDialog
    $dlg.Filter = "Recur XML|*.xml|Fighter JSON|*.fighter.json|Primary.json|Primary.json|All|*.*"
    $dlg.InitialDirectory = (Join-Path $userdata "Characters")
    if ($dlg.ShowDialog() -eq "OK") {
        try {
            $raw = Invoke-Py $importer @("--userdata", $userdata, "import", $dlg.FileName, "--pretty")
            $script:currentFighter = $raw | ConvertFrom-Json
            $txtPreview.Text = Format-FighterPreview $script:currentFighter
            $status.Text = "Loaded $($script:currentFighter.name)"
        } catch {
            [System.Windows.Forms.MessageBox]::Show("$_", "Import failed", "OK", "Error")
        }
    }
})

$btnExport.Add_Click({
    if (-not $script:currentFighter) {
        [System.Windows.Forms.MessageBox]::Show("Load a fighter first.", "Choose Your Fighter")
        return
    }
    $paths = Save-CurrentFighterJson
    $status.Text = "Wrote $($paths.Json)"
    [System.Windows.Forms.MessageBox]::Show("Saved:`n$($paths.Json)", "Exported")
})

$btnTile.Add_Click({
    if (-not $script:currentFighter) {
        [System.Windows.Forms.MessageBox]::Show("Load a fighter first.", "Choose Your Fighter")
        return
    }
    try {
        $paths = Save-CurrentFighterJson
        $sizeKey = @("vanilla", "2x", "3x", "4x")[$cmbSize.SelectedIndex]
        $modeKey = @("classic", "truecolor")[$cmbMode.SelectedIndex]
        $tileArgs = @($paths.Json, "-o", $paths.Dir, "--size", $sizeKey, "--color-mode", $modeKey)
        if ($chkAnimated.Checked) { $tileArgs += "--animated" }
        if ($chkKeepDetail.Checked) {
            if ($modeKey -eq "truecolor" -and -not $chkUpdateGear.Checked) { $tileArgs += "--sd" }
        } else {
            $tileArgs += @("--no-sd", "--allow-silhouette")
        }
        if (-not [string]::IsNullOrWhiteSpace($script:baseImage)) { $tileArgs += @("--base-image", $script:baseImage) }
        if (-not [string]::IsNullOrWhiteSpace($script:gearImage)) { $tileArgs += @("--gear-image", $script:gearImage) }
        if ($chkSaveBase.Checked) { $tileArgs += "--save-base" }
        if ($chkUpdateGear.Checked) { $tileArgs += "--update-gear" }
        if ($chkUpdateGear.Checked -and -not $chkKeepDetail.Checked) { $tileArgs += "--no-sd" }
        if (-not $chkAutoOverlays.Checked) { $tileArgs += "--no-auto-overlays" }
        if (-not [string]::IsNullOrWhiteSpace($script:gearImage)) { $tileArgs += @("--pin-overlay", "chest=from-image") }
        $status.Text = "Generating tile..."
        $form.Refresh()
        $raw = Invoke-Py $tiler $tileArgs
        $man = $raw | ConvertFrom-Json
        $msg = "Tile:`n$($man.staticTile)`r`nFG=$($man.foreground) Detail=$($man.detail)"
        if ($man.baseImage) { $msg += "`r`nBase: $($man.baseImage)" }
        if ($man.overlaySelection) { $msg += "`r`nOverlays: $($man.overlaySelection | ConvertTo-Json -Compress)" }
        if ($chkInstallMod.Checked) {
            $cyfCli = Join-Path $here "ChooseYourFighter.ps1"
            & powershell -NoProfile -ExecutionPolicy Bypass -File $cyfCli -Action Install -Path $paths.Dir -UserData $userdata
            if ($LASTEXITCODE -ne 0) { throw "Install into Arendeth_CYFTiles failed." }
            $msg += "`r`n`r`nInstalled into Mods\Arendeth_CYFTiles (Kernelmethod CYF picker)"
        }
        $status.Text = "Tile: $($man.staticTile)"
        if ($man.baseImage) {
            $script:baseImage = [string]$man.baseImage
            Set-ImageLabel $lblBase "Base: " $script:baseImage "(auto-pin on first bake)"
        }
        if ($man.gearImage) {
            $script:gearImage = [string]$man.gearImage
            Set-ImageLabel $lblGear "Gear: " $script:gearImage "(optional overlay for outfit swaps)"
        }
        [System.Windows.Forms.MessageBox]::Show($msg, "Tile ready")
    } catch {
        [System.Windows.Forms.MessageBox]::Show("$_", "Tile failed", "OK", "Error")
    }
})

$btnArt.Add_Click({
    if (-not $script:currentFighter) {
        [System.Windows.Forms.MessageBox]::Show("Load a fighter first.", "Choose Your Fighter")
        return
    }
    if (-not $chkDetailedArt.Checked -and -not $chkMinionArt.Checked) {
        [System.Windows.Forms.MessageBox]::Show("Enable fighter art and/or minion art.", "Choose Your Fighter")
        return
    }
    try {
        $paths = Save-CurrentFighterJson
        $artArgs = @("--userdata", $userdata, "art", $paths.Json, "--pretty", "--minions", "--broodling-limit", "3", "--minion-limit", "12")
        if (-not $chkSceneBrood.Checked) { $artArgs += "--no-broodlings" }
        if (-not $chkSceneConj.Checked) { $artArgs += "--no-conjoined" }
        switch ($cmbMinionFilter.SelectedIndex) {
            1 { $artArgs += "--followers-only" }
            2 { $artArgs += "--broodlings-only" }
            3 { $artArgs += "--conjoined-only" }
        }
        $status.Text = "Building unfiltered art payloads..."
        $form.Refresh()
        $artRaw = Invoke-Py $importer $artArgs
        $art = $artRaw | ConvertFrom-Json
        ($art | ConvertTo-Json -Depth 10) | Set-Content -Path (Join-Path $paths.Dir "art_payloads.json") -Encoding UTF8

        $done = @()
        if ($chkDetailedArt.Checked) {
            $status.Text = "Generating fighter detailed art..."
            $form.Refresh()
            Invoke-UnfilteredArtJob @{
                kind          = "fighter"
                characterName = $art.fighter.characterName
                description   = $art.fighter.description
                mutations     = @($art.fighter.mutations)
                traits        = @($art.fighter.traits)
            } $paths.Dir
            $done += "fighter"
        }
        if ($chkMinionArt.Checked) {
            $i = 0
            foreach ($m in @($art.minions)) {
                $i++
                $status.Text = "Generating minion art $i / $(@($art.minions).Count): $($m.characterName) [$($m.role)]"
                $form.Refresh()
                Invoke-UnfilteredArtJob @{
                    kind          = "minion"
                    characterName = $m.characterName
                    description   = $m.description
                    mutations     = @($m.mutations)
                    traits        = @($m.traits)
                } $paths.Dir
                $done += $m.characterName
            }
        }
        $status.Text = "Art written to $($paths.Dir)"
        [System.Windows.Forms.MessageBox]::Show(
            ("Generated {0} image job(s) in:`n{1}`n`n{2}" -f $done.Count, $paths.Dir, ($done -join ", ")),
            "Unfiltered art"
        )
    } catch {
        $status.Text = "Art generation failed"
        [System.Windows.Forms.MessageBox]::Show("$_", "Art failed", "OK", "Error")
    }
})

try { Refresh-Sources } catch { $status.Text = "Scan failed: $_" }
[void]$form.ShowDialog()

# AtlasArtTranslator-GUI.ps1
# Browse Atlas of Qud Automap tiles → img2img illustrated art

if ([System.Threading.Thread]::CurrentThread.GetApartmentState() -ne [System.Threading.ApartmentState]::STA) {
    powershell -STA -NoProfile -ExecutionPolicy Bypass -File $MyInvocation.MyCommand.Path
    exit $LASTEXITCODE
}

Add-Type -AssemblyName System.Windows.Forms, System.Drawing -ErrorAction Stop
$ErrorActionPreference = "Stop"

$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$pyHelper = Join-Path $here "qud_atlas_art.py"
$shared = Join-Path (Split-Path $here -Parent) "Shared"
$sdModule = Join-Path $shared "StableDiffusionIntegration.psm1"
$userdata = Join-Path $env:USERPROFILE "AppData\LocalLow\Freehold Games\CavesOfQud"
$outRoot = Join-Path $here "..\Output\AtlasArt"
New-Item -ItemType Directory -Path $outRoot -Force | Out-Null

function Get-PythonExe {
    foreach ($c in @("python", "py")) {
        try { return (Get-Command $c -ErrorAction Stop).Source } catch {}
    }
    throw "Python not found."
}

function Invoke-Py([string[]]$PyArgs) {
    $py = Get-PythonExe
    $all = @($pyHelper) + $PyArgs
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
    if ($p.ExitCode -ne 0) { throw "Python failed:`n$stderr`n$stdout" }
    return $stdout
}

$form = New-Object Windows.Forms.Form
$form.Text = "Atlas Art Translator — Automap tiles → illustrated map"
$form.Size = New-Object Drawing.Size(1040, 760)
$form.StartPosition = "CenterScreen"

$lblSaves = New-Object Windows.Forms.Label
$lblSaves.Text = "Saves with Automap/tiles (Atlas of Qud)"
$lblSaves.Location = New-Object Drawing.Point(12, 12)
$lblSaves.AutoSize = $true
$form.Controls.Add($lblSaves)

$listSaves = New-Object Windows.Forms.ListBox
$listSaves.Location = New-Object Drawing.Point(12, 36)
$listSaves.Size = New-Object Drawing.Size(400, 200)
$form.Controls.Add($listSaves)

$lblTiles = New-Object Windows.Forms.Label
$lblTiles.Text = "Zone tiles"
$lblTiles.Location = New-Object Drawing.Point(12, 248)
$lblTiles.AutoSize = $true
$form.Controls.Add($lblTiles)

$listTiles = New-Object Windows.Forms.ListBox
$listTiles.Location = New-Object Drawing.Point(12, 272)
$listTiles.Size = New-Object Drawing.Size(400, 320)
$form.Controls.Add($listTiles)

$btnRefresh = New-Object Windows.Forms.Button
$btnRefresh.Text = "Refresh"
$btnRefresh.Location = New-Object Drawing.Point(12, 604)
$btnRefresh.Size = New-Object Drawing.Size(100, 28)
$form.Controls.Add($btnRefresh)

$btnBrowse = New-Object Windows.Forms.Button
$btnBrowse.Text = "Browse PNG..."
$btnBrowse.Location = New-Object Drawing.Point(122, 604)
$btnBrowse.Size = New-Object Drawing.Size(110, 28)
$form.Controls.Add($btnBrowse)

$pic = New-Object Windows.Forms.PictureBox
$pic.Location = New-Object Drawing.Point(430, 36)
$pic.Size = New-Object Drawing.Size(580, 270)
$pic.SizeMode = "Zoom"
$pic.BorderStyle = "FixedSingle"
$form.Controls.Add($pic)

$grp = New-Object Windows.Forms.GroupBox
$grp.Text = "Translate (img2img)"
$grp.Location = New-Object Drawing.Point(430, 320)
$grp.Size = New-Object Drawing.Size(580, 280)
$form.Controls.Add($grp)

$lblStyle = New-Object Windows.Forms.Label
$lblStyle.Text = "Style:"
$lblStyle.Location = New-Object Drawing.Point(12, 28)
$lblStyle.AutoSize = $true
$grp.Controls.Add($lblStyle)

$cmbStyle = New-Object Windows.Forms.ComboBox
$cmbStyle.DropDownStyle = "DropDownList"
$cmbStyle.Location = New-Object Drawing.Point(70, 24)
$cmbStyle.Size = New-Object Drawing.Size(200, 24)
[void]$cmbStyle.Items.AddRange(@(
    "cartography (keep layout ~0.42)",
    "landscape (illustrated ~0.60)",
    "dream (loose ~0.78)"
))
$cmbStyle.SelectedIndex = 1
$grp.Controls.Add($cmbStyle)

$chkOllama = New-Object Windows.Forms.CheckBox
$chkOllama.Text = "Ollama vision caption (layout notes for the prompt)"
$chkOllama.Location = New-Object Drawing.Point(12, 60)
$chkOllama.AutoSize = $true
$chkOllama.Checked = $true
$grp.Controls.Add($chkOllama)

$chkParasang = New-Object Windows.Forms.CheckBox
$chkParasang.Text = "Stitch full parasang (3x3) around selected zone"
$chkParasang.Location = New-Object Drawing.Point(12, 88)
$chkParasang.AutoSize = $true
$grp.Controls.Add($chkParasang)

$lblPrompt = New-Object Windows.Forms.Label
$lblPrompt.Text = "Prompt preview (filled on Prepare / Generate)"
$lblPrompt.Location = New-Object Drawing.Point(12, 120)
$lblPrompt.AutoSize = $true
$grp.Controls.Add($lblPrompt)

$txtPrompt = New-Object Windows.Forms.TextBox
$txtPrompt.Multiline = $true
$txtPrompt.ScrollBars = "Vertical"
$txtPrompt.Location = New-Object Drawing.Point(12, 144)
$txtPrompt.Size = New-Object Drawing.Size(552, 90)
$txtPrompt.Font = New-Object Drawing.Font("Consolas", 8)
$grp.Controls.Add($txtPrompt)

$btnGen = New-Object Windows.Forms.Button
$btnGen.Text = "Generate illustrated art"
$btnGen.Location = New-Object Drawing.Point(12, 244)
$btnGen.Size = New-Object Drawing.Size(200, 28)
$grp.Controls.Add($btnGen)

$status = New-Object Windows.Forms.Label
$status.Text = "Ready — needs Atlas of Qud zone captures under <Save>\Automap\tiles"
$status.Location = New-Object Drawing.Point(12, 680)
$status.Size = New-Object Drawing.Size(1000, 28)
$form.Controls.Add($status)

$script:atlases = @()
$script:currentTilesDir = ""
$script:selectedPng = ""

function Style-Key {
    return @("cartography", "landscape", "dream")[$cmbStyle.SelectedIndex]
}

function Refresh-Saves {
    $status.Text = "Scanning Automap/tiles..."
    $form.Refresh()
    $raw = Invoke-Py @("--userdata", $userdata, "list", "--json", "--tiles")
    $script:atlases = @($raw | ConvertFrom-Json)
    $listSaves.Items.Clear()
    $listTiles.Items.Clear()
    $script:currentTilesDir = ""
    foreach ($a in $script:atlases) {
        [void]$listSaves.Items.Add(("[{0} tiles] {1}" -f $a.tile_count, $a.save_name))
    }
    if ($script:atlases.Count -eq 0) {
        $status.Text = "No Automap/tiles found. Explore with Atlas of Qud (Ctrl+M) first."
    } else {
        $status.Text = ("Found {0} save atlas folder(s)." -f $script:atlases.Count)
    }
}

function Show-Preview([string]$png) {
    if (-not $png -or -not (Test-Path $png)) { return }
    if ($pic.Image) { $pic.Image.Dispose(); $pic.Image = $null }
    $pic.Image = [Drawing.Image]::FromFile($png)
    $script:selectedPng = $png
}

$listSaves.Add_SelectedIndexChanged({
    if ($listSaves.SelectedIndex -lt 0) { return }
    $a = $script:atlases[$listSaves.SelectedIndex]
    $script:currentTilesDir = $a.tiles_dir
    $listTiles.Items.Clear()
    foreach ($t in @($a.tiles)) {
        [void]$listTiles.Items.Add($t.zone_id)
    }
    $status.Text = $a.tiles_dir
})

$listTiles.Add_SelectedIndexChanged({
    if ($listTiles.SelectedIndex -lt 0 -or $listSaves.SelectedIndex -lt 0) { return }
    $a = $script:atlases[$listSaves.SelectedIndex]
    $t = @($a.tiles)[$listTiles.SelectedIndex]
    Show-Preview $t.path
})

$btnRefresh.Add_Click({ Refresh-Saves })

$btnBrowse.Add_Click({
    $dlg = New-Object Windows.Forms.OpenFileDialog
    $dlg.Filter = "Atlas PNG|*.png|All|*.*"
    $dlg.InitialDirectory = $userdata
    if ($dlg.ShowDialog() -eq "OK") {
        Show-Preview $dlg.FileName
        $script:currentTilesDir = Split-Path $dlg.FileName -Parent
        $status.Text = $dlg.FileName
    }
})

$btnGen.Add_Click({
    if (-not $script:selectedPng -or -not (Test-Path $script:selectedPng)) {
        [Windows.Forms.MessageBox]::Show("Select or browse an Atlas zone PNG first.")
        return
    }
    try {
        if (-not (Test-Path $sdModule)) { throw "SD module missing: $sdModule" }
        Import-Module $sdModule -Force

        $style = Style-Key
        $zone = [IO.Path]::GetFileNameWithoutExtension($script:selectedPng)
        $outDir = Join-Path $outRoot $zone
        New-Item -ItemType Directory -Path $outDir -Force | Out-Null
        $jobFile = Join-Path $outDir "job.json"

        $prep = @("--userdata", $userdata, "prepare", "--style", $style, "-o", $jobFile, "--out-dir", $outDir)
        if ($chkOllama.Checked) { $prep += "--ollama" }

        if ($chkParasang.Checked) {
            $parts = $zone -split '\.'
            if ($parts.Count -ne 6) { throw "Parasang stitch needs a standard zone id filename." }
            $parasang = "{0}.{1}.{2}.{3}" -f $parts[0], $parts[1], $parts[2], $parts[5]
            $tilesDir = if ($script:currentTilesDir) { $script:currentTilesDir } else { Split-Path $script:selectedPng -Parent }
            $prep += @($tilesDir, "--parasang", $parasang)
        } else {
            $prep += @($script:selectedPng)
        }

        $status.Text = "Preparing job (caption/stitch)..."
        $form.Refresh()
        [void](Invoke-Py $prep)
        $job = Get-Content -Raw $jobFile | ConvertFrom-Json
        $txtPrompt.Text = $job.prompt
        if ($job.sourceImage) { Show-Preview $job.sourceImage }

        $status.Text = "Generating img2img ($style, strength=$($job.strength))..."
        $form.Refresh()
        Generate-AssetImageWithSD3 `
            -Prompt $job.prompt `
            -NegativePrompt $job.negativePrompt `
            -OutputPath $job.outputImage `
            -Width ([int]$job.width) `
            -Height ([int]$job.height) `
            -ReferenceImagePath $job.sourceImage `
            -ImageStrength ([double]$job.strength) `
            -EnhanceWithOllama:$false `
            -AutoStartServer:$false

        $status.Text = "Wrote $($job.outputImage)"
        if (Test-Path $job.outputImage) { Show-Preview $job.outputImage }
        [Windows.Forms.MessageBox]::Show("Saved:`n$($job.outputImage)", "Atlas Art")
    } catch {
        $status.Text = "Failed"
        [Windows.Forms.MessageBox]::Show("$_", "Atlas Art failed", "OK", "Error")
    }
})

try { Refresh-Saves } catch { $status.Text = "Scan failed: $_" }
[void]$form.ShowDialog()
if ($pic.Image) { $pic.Image.Dispose() }

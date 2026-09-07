# Thematic net-zero balancer for TT_ExtraBackgrounds Factions.xml
# Strategy per background:
#  1) Protect primary kinship positives (largest / named)
#  2) Ensure lore-based enemy factions exist (AddNegatives)
#  3) Grow existing + new negatives to cover the positive budget
#  4) Only then trim secondary positives; never erase kinship identity

param(
  [string]$Path = "C:\Users\Arend\AppData\LocalLow\Freehold Games\CavesOfQud\Mods\TT_ExtraBackgrounds\Factions.xml",
  [switch]$WhatIf
)

$ErrorActionPreference = 'Stop'

# Primary kinship faction(s) to protect when trimming positives
$Primary = @{
  AndroidKin = @('Androids')
  AntelopeHerdmate = @('Antelopes')
  ApeKin = @('Apes')
  ArachnidKin = @('Arachnids')
  BaboonKin = @('Baboons')
  BaetylAnswerer = @('Baetyls')
  BatKin = @('Winged Mammals')
  BearBrother = @('Bears')
  BirdCaller = @('Birds')
  CannibalSympathizer = @('Cannibals')
  CatCompanion = @('Cats')
  ChavvahPilgrim = @('Chavvah')
  CoiledLambAcolyte = @('Resheph')
  ConsortiumFactor = @('Consortium')
  CrabScuttler = @('Crabs')
  CragmenschKin = @('Cragmensch')
  DaughterOfExile = @('Daughters')
  DogCompanion = @('Dogs')
  DromadCaravaneer = @('Dromad')
  EntropicDiplomat = @('Entropic')
  EquineRider = @('Equines')
  EzraVillager = @('Ezra')
  FarmersGuildhand = @('Farmers')
  FishSpeaker = @('Fish')
  FlowerSpeaker = @('Flowers')
  FrogPondkin = @('Frogs')
  FungalCohabitant = @('Fungi')
  GlowWightKin = @('Glow Wights')
  GrazingHedonist = @('Prey')
  GyreWightSympathizer = @('Gyre Wights')
  HindrenExile = @('Hindren')
  InsectWhisperer = @('Insects')
  IssachariScion = @('Issachari')
  JoppaVillager = @('Joppa')
  KyakukyaVillager = @('Kyakukya')
  MamonInitiate = @('Mamon')
  MechanimistNovice = @('Mechanimists')
  MerchantsGuilder = @('Merchants')
  MolluskFriend = @('Mollusks')
  MopangoClimber = @('Mopango')
  NewlySentientAdvocate = @('Newly Sentient Beings')
  OozeCohabitant = @('Oozes')
  PariahFounder = @('Pariahs')
  PsychicConcord = @('Glow Wights','Entropic')
  ReefDiver = @('Fish','Mollusks','Crabs')
  RootSpeaker = @('Roots')
  RuinsScrounger = @('Robots','Baetyls')
  SaltMarshOrphan = @('Fish','Joppa','Pariahs')
  ScrapKin = @('Robots')
  SightlessEnvoy = @('Seekers')
  StarappleFarmhand = @('Farmers')
  StiltPilgrim = @('Mechanimists','Resheph')
  StrangerMarked = @('Strangers')
  SucculentKin = @('Succulents')
  SultanTombGawker = @('Hermits','Baetyls','SultanCult1')
  SvardymKin = @('Svardym')
  SwineFriend = @('Swine')
  TemplarApostate = @('Templar') # residual hierarchy; still primary identity marker
  TortoiseElder = @('Tortoises')
  TreeSpeaker = @('Trees')
  TrollKin = @('Trolls')
  UnshelledReptileKin = @('Unshelled Reptiles')
  UrchinFriend = @('Urchins')
  VineWalker = @('Vines')
  WardenErrant = @('Wardens')
  WaterBaronHeir = @('Water')
  WatervineHarvester = @('Joppa','Farmers')
  WaystationCook = @('Merchants')
  WormDelver = @('Worms')
  YdFreeholder = @('YdFreehold')
}

# Lore enemies to ensure exist (added if missing). Values are starting magnitudes; may grow during balance.
$EnsureNeg = @{
  AndroidKin = @{ Templar = -400; Barathrumites = -200; Seekers = -200; Mechanimists = -250 }
  AntelopeHerdmate = @{ Cats = -350; Hunters = -200; Dogs = -100 }
  ApeKin = @{ Goatfolk = -350; Snapjaws = -100; Hindren = -100 }
  ArachnidKin = @{ Insects = -400; Birds = -175; Dogs = -150 }
  BaboonKin = @{ Goatfolk = -400; Snapjaws = -250; Wardens = -150; Hindren = -100 }
  BaetylAnswerer = @{ Girsh = -350; Templar = -250; Wardens = -150; Seekers = -100 }
  BatKin = @{ Frogs = -200; Svardym = -200; Cats = -150 }
  BearBrother = @{ Snapjaws = -350; Dogs = -200; Joppa = -150; Wardens = -75 }
  BirdCaller = @{ 'Unshelled Reptiles' = -300; Cats = -150; Arachnids = -100 }
  CannibalSympathizer = @{ Joppa = -300; Wardens = -300; Dogs = -200; Hindren = -100; Pariahs = -100 }
  CatCompanion = @{ Prey = -200; Antelopes = -200; Dogs = -150 }
  ChavvahPilgrim = @{ Templar = -300; Girsh = -250; 'Gyre Wights' = -150; Entropic = -150 }
  CoiledLambAcolyte = @{ Girsh = -350; Seekers = -200; Entropic = -150; Mamon = -150 }
  ConsortiumFactor = @{ Templar = -450; Girsh = -200; Barathrumites = -150; Snapjaws = -100 }
  CrabScuttler = @{ Birds = -400; Cats = -200; Dogs = -150; Equines = -125 }
  CragmenschKin = @{ Wardens = -300; Flowers = -200; Farmers = -150; 'Newly Sentient Beings' = -150 }
  DaughterOfExile = @{ Templar = -500; Seekers = -100; Girsh = -100 }
  DogCompanion = @{ Cats = -150; Snapjaws = -150; Cannibals = -100 }
  DromadCaravaneer = @{ Snapjaws = -350; Girsh = -250; Cannibals = -150 }
  EntropicDiplomat = @{ Templar = -500; Wardens = -400; Farmers = -200; Mechanimists = -200; Barathrumites = -150; Hindren = -150 }
  EquineRider = @{ Cats = -250; Hunters = -200; Dogs = -100 }
  EzraVillager = @{ Snapjaws = -250; Goatfolk = -200; Templar = -150; Girsh = -100 }
  FarmersGuildhand = @{ Snapjaws = -300; Vines = -200; Girsh = -150; Trolls = -100 }
  FishSpeaker = @{ Crabs = -300; Birds = -250; Cats = -200 }
  FlowerSpeaker = @{ Barathrumites = -300; Girsh = -250; Templar = -150; Robots = -100 }
  FrogPondkin = @{ Birds = -450; Cats = -250; Dogs = -150; Hunters = -125 }
  FungalCohabitant = @{ Consortium = -250; Farmers = -200; Merchants = -100; Wardens = -100 }
  GlowWightKin = @{ Wardens = -400; Flowers = -350; Hindren = -250; Chavvah = -200; Templar = -250; Mechanimists = -150 }
  GrazingHedonist = @{ Cats = -350; Hunters = -250 }
  GyreWightSympathizer = @{ Templar = -350; Mechanimists = -250; Wardens = -150; Resheph = -100 }
  HindrenExile = @{ Girsh = -400; Issachari = -200; Snapjaws = -150; Templar = -100; Goatfolk = -100 }
  InsectWhisperer = @{ Arachnids = -350; Svardym = -200; Birds = -125; Frogs = -100 }
  IssachariScion = @{ Joppa = -300; Hindren = -200; Flowers = -100; Fish = -100 }
  JoppaVillager = @{ Snapjaws = -250; Issachari = -200; Goatfolk = -150; Girsh = -100; Mamon = -50 }
  KyakukyaVillager = @{ Snapjaws = -300; Girsh = -250; Cannibals = -100; Templar = -100 }
  MamonInitiate = @{ Joppa = -450; Wardens = -200; Hindren = -150; Resheph = -150 }
  MechanimistNovice = @{ Barathrumites = -300; Templar = -200; 'Gyre Wights' = -200; Seekers = -100 }
  MerchantsGuilder = @{ Snapjaws = -350; Girsh = -250; Cannibals = -150; Trolls = -100 }
  MolluskFriend = @{ Birds = -400; Cats = -200; Dogs = -175 }
  MopangoClimber = @{ Girsh = -350; Templar = -150; Snapjaws = -100; Seekers = -50 }
  NewlySentientAdvocate = @{ Templar = -450; Mechanimists = -100; Seekers = -100; Wardens = -100 }
  OozeCohabitant = @{ Consortium = -300; Farmers = -250; Merchants = -150 }
  PariahFounder = @{ Girsh = -400; Templar = -300; Wardens = -200; Snapjaws = -150; Issachari = -150 }
  PsychicConcord = @{ Templar = -500; Wardens = -450; Joppa = -250; Barathrumites = -250; Mechanimists = -200; Hindren = -150 }
  ReefDiver = @{ Templar = -450; Barathrumites = -200; Seekers = -150; Snapjaws = -150; Girsh = -150 }
  RootSpeaker = @{ Farmers = -400; Merchants = -150; Equines = -75 }
  RuinsScrounger = @{ Girsh = -400; Templar = -150; Seekers = -100; Cannibals = -50 }
  SaltMarshOrphan = @{ Issachari = -250; Snapjaws = -200; Goatfolk = -90 }
  ScrapKin = @{ Templar = -500; Seekers = -250; Mechanimists = -150 }
  SightlessEnvoy = @{ Wardens = -350; Joppa = -300; Templar = -200; Resheph = -150 }
  StarappleFarmhand = @{ Girsh = -400; Snapjaws = -250; Vines = -150; Trolls = -100 }
  StiltPilgrim = @{ Templar = -300; Seekers = -250; 'Gyre Wights' = -150; Girsh = -100 }
  StrangerMarked = @{ Joppa = -250; Wardens = -250; Ezra = -100; Kyakukya = -100 }
  SucculentKin = @{ Goatfolk = -350 }
  SultanTombGawker = @{ Girsh = -400; Templar = -350; Wardens = -100; Snapjaws = -100 }
  SvardymKin = @{ Insects = -450; Birds = -250; Cats = -175 }
  SwineFriend = @{ Snapjaws = -450; Dogs = -125; Cats = -100 }
  TemplarApostate = @{ 'Gyre Wights' = -250; Daughters = -200; 'Newly Sentient Beings' = -200; Mechanimists = -150; Chavvah = -150; Hindren = -100; Pariahs = -100 }
  TortoiseElder = @{ Cats = -200; Dogs = -175; Hunters = -175 }
  TreeSpeaker = @{ Barathrumites = -400; Robots = -150; Templar = -100; Girsh = -50 }
  TrollKin = @{ Joppa = -300; Seekers = -250; Wardens = -150; Ezra = -100; Kyakukya = -100 }
  UnshelledReptileKin = @{ Birds = -450; Cats = -200; Dogs = -175 }
  UrchinFriend = @{ Dogs = -300; Cats = -300; Equines = -150 }
  VineWalker = @{ Farmers = -450; Merchants = -150; Equines = -75 }
  WardenErrant = @{ Snapjaws = -400; 'Gyre Wights' = -250; Cannibals = -150; Girsh = -100 }
  WaterBaronHeir = @{ Pariahs = -350; Templar = -300; Snapjaws = -200; Girsh = -100; Hindren = -100 }
  WatervineHarvester = @{ Issachari = -300; Snapjaws = -250; Goatfolk = -50 }
  WaystationCook = @{ Girsh = -400; Snapjaws = -250; Cannibals = -150; Trolls = -50 }
  WormDelver = @{ Farmers = -400; Merchants = -150; Equines = -75; Birds = -100 }
  YdFreeholder = @{ Templar = -400; Girsh = -200; Seekers = -100 }
}

function Round25([double]$v) { [int]([Math]::Round($v / 25.0) * 25) }
function Floor25([double]$v) { [int]([Math]::Floor($v / 25.0) * 25) }

$xml = New-Object System.Xml.XmlDocument
$xml.Load($Path)

# Index: factionName -> XmlElement; also bg -> list of {Faction, Node, Value}
$factionNodes = @{}
foreach ($f in $xml.SelectNodes('/factions/faction')) {
  $factionNodes[$f.GetAttribute('Name')] = $f
}

$byBg = @{}
foreach ($f in $xml.SelectNodes('/factions/faction')) {
  $fname = $f.GetAttribute('Name')
  foreach ($pr in @($f.SelectNodes('partreputation'))) {
    if ($null -eq $pr) { continue }
    $bg = $pr.GetAttribute('About')
    if (-not $byBg.ContainsKey($bg)) { $byBg[$bg] = @() }
    $byBg[$bg] += [pscustomobject]@{ Faction = $fname; Node = $pr; Value = [int]$pr.GetAttribute('Value') }
  }
}

function Ensure-Faction([string]$name) {
  if ($factionNodes.ContainsKey($name)) { return $factionNodes[$name] }
  # create merge shell
  $f = $xml.CreateElement('faction')
  $f.SetAttribute('Name', $name)
  $f.SetAttribute('Load', 'Merge')
  [void]$xml.DocumentElement.AppendChild($f)
  $factionNodes[$name] = $f
  return $f
}

function Set-PartRep([string]$faction, [string]$bg, [int]$value) {
  $f = Ensure-Faction $faction
  $existing = $null
  foreach ($pr in @($f.SelectNodes('partreputation'))) {
    if ($null -ne $pr -and $pr.GetAttribute('About') -eq $bg) { $existing = $pr; break }
  }
  if ($null -eq $existing) {
    $pr = $xml.CreateElement('partreputation')
    $pr.SetAttribute('About', $bg)
    $pr.SetAttribute('Value', [string]$value)
    [void]$f.AppendChild($pr)
    if (-not $byBg.ContainsKey($bg)) { $byBg[$bg] = @() }
    $byBg[$bg] += [pscustomobject]@{ Faction = $faction; Node = $pr; Value = $value }
  } else {
    $cur = [int]$existing.GetAttribute('Value')
    # For ensures: take the more negative (or keep if already worse)
    if ($value -lt 0 -and $cur -gt $value) {
      $existing.SetAttribute('Value', [string]$value)
    } elseif ($value -gt 0 -and $cur -lt $value -and $cur -ge 0) {
      # don't auto-grow positives via ensure
    }
    # refresh byBg cache value
    for ($i=0; $i -lt $byBg[$bg].Count; $i++) {
      if ($byBg[$bg][$i].Faction -eq $faction) {
        $byBg[$bg][$i].Value = [int]$existing.GetAttribute('Value')
        $byBg[$bg][$i].Node = $existing
      }
    }
  }
}

function Get-Entries([string]$bg) {
  # rebuild from live XML
  $list = @()
  foreach ($f in $xml.SelectNodes('/factions/faction')) {
    $fname = $f.GetAttribute('Name')
    foreach ($pr in @($f.SelectNodes('partreputation'))) {
      if ($null -eq $pr) { continue }
      if ($pr.GetAttribute('About') -eq $bg) {
        $list += [pscustomobject]@{ Faction = $fname; Node = $pr; Value = [int]$pr.GetAttribute('Value') }
      }
    }
  }
  return $list
}

function Set-EntryValue($entry, [int]$value) {
  $entry.Node.SetAttribute('Value', [string]$value)
  $entry.Value = $value
}

$report = New-Object System.Collections.Generic.List[string]
$backgrounds = @($byBg.Keys | Sort-Object)

foreach ($bg in $backgrounds) {
  # 1) ensure thematic negatives
  if ($EnsureNeg.ContainsKey($bg)) {
    foreach ($kv in $EnsureNeg[$bg].GetEnumerator()) {
      if ($null -eq $kv.Value) { continue }
      if ($kv.Value -ge 0) { continue }
      Set-PartRep $kv.Key $bg ([int]$kv.Value)
    }
  }

  $entries = @(Get-Entries $bg)
  $pos = @($entries | Where-Object { $_.Value -gt 0 })
  $neg = @($entries | Where-Object { $_.Value -lt 0 })
  $posSum = 0; foreach ($e in $pos) { $posSum += $e.Value }
  $negSum = 0; foreach ($e in $neg) { $negSum += -$e.Value }
  $prim = @()
  if ($Primary.ContainsKey($bg)) { $prim = @($Primary[$bg]) }

  # Special: TemplarApostate — apostate fled Putus; keep Templar as mild residual, not +700
  if ($bg -eq 'TemplarApostate') {
    foreach ($e in $pos) {
      if ($e.Faction -eq 'Templar' -and $e.Value -gt 250) {
        Set-EntryValue $e 250
      }
    }
    $entries = @(Get-Entries $bg)
    $pos = @($entries | Where-Object { $_.Value -gt 0 })
    $neg = @($entries | Where-Object { $_.Value -lt 0 })
    $posSum = 0; foreach ($e in $pos) { $posSum += $e.Value }
    $negSum = 0; foreach ($e in $neg) { $negSum += -$e.Value }
  }

  # Target: match positives with equal negatives. Prefer growing negatives.
  # Soft-cap primary kinship so budgets stay readable (kin ~400-650 typically).
  foreach ($e in $pos) {
    $isPrim = $prim -contains $e.Faction
    $cap = if ($isPrim) { 650 } else { 300 }
    if ($e.Value -gt $cap) {
      Set-EntryValue $e $cap
    }
  }
  $entries = @(Get-Entries $bg)
  $pos = @($entries | Where-Object { $_.Value -gt 0 })
  $neg = @($entries | Where-Object { $_.Value -lt 0 })
  $posSum = 0; foreach ($e in $pos) { $posSum += $e.Value }
  $negSum = 0; foreach ($e in $neg) { $negSum += -$e.Value }

  $deficit = $posSum - $negSum  # need this much more |neg| (or less pos)

  if ($deficit -gt 0 -and $neg.Count -gt 0) {
    # Grow negatives proportionally, cap individual at -500
    $room = @{}
    $totalRoom = 0
    foreach ($e in $neg) {
      $cap = 500
      $r = $cap - (-$e.Value)
      if ($r -lt 0) { $r = 0 }
      $room[$e.Faction] = $r
      $totalRoom += $r
    }
    $grow = [Math]::Min($deficit, $totalRoom)
    if ($grow -gt 0 -and $totalRoom -gt 0) {
      $assigned = 0
      $order = @($neg | Sort-Object { -$room[$_.Faction] }, { $_.Value })
      # largest remainder in 25s
      $shares = @{}
      foreach ($e in $neg) {
        $raw = $grow * 1.0 * $room[$e.Faction] / $totalRoom
        $flo = Floor25 $raw
        $shares[$e.Faction] = @{ flo = $flo; frac = $raw - $flo }
        $assigned += $flo
      }
      $remain = Round25 ($grow - $assigned)
      # fix rounding: remain should be multiple of 25
      $remain = [int]($grow - $assigned)
      $remain = [int]([Math]::Floor($remain / 25.0) * 25)
      foreach ($e in ($order | Sort-Object { -$shares[$_.Faction].frac })) {
        if ($remain -lt 25) { break }
        $add = [Math]::Min(25, $room[$e.Faction] - $shares[$e.Faction].flo)
        if ($add -ge 25) {
          $shares[$e.Faction].flo += 25
          $remain -= 25
        }
      }
      foreach ($e in $neg) {
        $add = $shares[$e.Faction].flo
        if ($add -gt 0) { Set-EntryValue $e ($e.Value - $add) }
      }
      $deficit -= ($grow - ($remain))
      # recompute deficit precisely
      $entries = @(Get-Entries $bg)
      $pos = @($entries | Where-Object { $_.Value -gt 0 })
      $neg = @($entries | Where-Object { $_.Value -lt 0 })
      $posSum = 0; foreach ($e in $pos) { $posSum += $e.Value }
      $negSum = 0; foreach ($e in $neg) { $negSum += -$e.Value }
      $deficit = $posSum - $negSum
    }
  }

  # Still deficit: trim secondary positives first, then primaries if needed
  if ($deficit -gt 0) {
    $secondaries = @($pos | Where-Object { $prim -notcontains $_.Faction } | Sort-Object Value -Descending)
    foreach ($e in $secondaries) {
      if ($deficit -le 0) { break }
      $minKeep = 50
      $canCut = $e.Value - $minKeep
      if ($canCut -le 0) { continue }
      $cut = [Math]::Min($deficit, $canCut)
      $cut = Round25 $cut
      if ($cut -gt $canCut) { $cut = Floor25 $canCut }
      if ($cut -lt 25 -and $canCut -ge $deficit) { $cut = $deficit } # allow non-25 if last
      if ($cut -le 0) { continue }
      Set-EntryValue $e ($e.Value - $cut)
      $deficit -= $cut
    }
  }

  if ($deficit -gt 0) {
    # trim primaries toward floor 300 (or 200 if still needed)
    $primaries = @($pos | Where-Object { $prim -contains $_.Faction } | Sort-Object Value -Descending)
    foreach ($floor in @(300, 200, 100, 50)) {
      if ($deficit -le 0) { break }
      $entries = @(Get-Entries $bg)
      $pos = @($entries | Where-Object { $_.Value -gt 0 })
      $primaries = @($pos | Where-Object { $prim -contains $_.Faction } | Sort-Object Value -Descending)
      foreach ($e in $primaries) {
        if ($deficit -le 0) { break }
        $canCut = $e.Value - $floor
        if ($canCut -le 0) { continue }
        $cut = [Math]::Min($deficit, $canCut)
        $cut = Floor25 $cut
        if ($cut -le 0 -and $canCut -ge $deficit) { $cut = $deficit }
        if ($cut -le 0) { continue }
        Set-EntryValue $e ($e.Value - $cut)
        $deficit -= $cut
      }
    }
  }

  # Surplus negatives (neg > pos): shrink negatives toward ensure floors / -50
  $entries = @(Get-Entries $bg)
  $posSum = 0; $negSum = 0
  $pos = @(); $neg = @()
  foreach ($e in $entries) {
    if ($e.Value -gt 0) { $pos += $e; $posSum += $e.Value }
    elseif ($e.Value -lt 0) { $neg += $e; $negSum += -$e.Value }
  }
  $surplus = $negSum - $posSum
  if ($surplus -gt 0) {
    foreach ($e in ($neg | Sort-Object Value)) { # most negative first
      if ($surplus -le 0) { break }
      $floor = -50
      if ($EnsureNeg.ContainsKey($bg) -and $EnsureNeg[$bg].ContainsKey($e.Faction)) {
        $floor = [Math]::Min(-50, [int]$EnsureNeg[$bg][$e.Faction])
      }
      $canEase = (-$e.Value) - (-$floor)
      if ($canEase -le 0) { continue }
      $ease = [Math]::Min($surplus, $canEase)
      $ease = Floor25 $ease
      if ($ease -le 0 -and $canEase -ge $surplus) { $ease = $surplus }
      if ($ease -le 0) { continue }
      Set-EntryValue $e ($e.Value + $ease)
      $surplus -= $ease
    }
  }

  # Exact net fix: nudge largest non-primary entry
  $entries = @(Get-Entries $bg)
  $net = 0; foreach ($e in $entries) { $net += $e.Value }
  if ($net -ne 0) {
    $candidates = @($entries | Where-Object { $prim -notcontains $_.Faction } | Sort-Object { [Math]::Abs($_.Value) } -Descending)
    if ($candidates.Count -eq 0) { $candidates = @($entries | Sort-Object { [Math]::Abs($_.Value) } -Descending) }
    $t = $candidates[0]
    Set-EntryValue $t ($t.Value - $net)
    $net2 = 0; foreach ($e in (Get-Entries $bg)) { $net2 += $e.Value }
    [void]$report.Add("${bg}: net $net -> $net2 (nudge $($t.Faction))")
  } else {
    [void]$report.Add("${bg}: net 0")
  }
}

if (-not $WhatIf) {
  $settings = New-Object System.Xml.XmlWriterSettings
  $settings.Indent = $true
  $settings.IndentChars = '  '
  $settings.Encoding = New-Object System.Text.UTF8Encoding $false
  $settings.NewLineChars = "`r`n"
  $ms = New-Object System.IO.MemoryStream
  $xw = [System.Xml.XmlWriter]::Create($ms, $settings)
  $xml.Save($xw); $xw.Close()
  [System.IO.File]::WriteAllBytes($Path, $ms.ToArray())
}

$report | ForEach-Object { $_ }

# verify
$xml2 = [xml](Get-Content -Raw $Path)
$totals = @{}
foreach ($faction in $xml2.factions.faction) {
  foreach ($pr in @($faction.partreputation)) {
    if ($null -eq $pr) { continue }
    $bg = [string]$pr.About
    if (-not $totals.ContainsKey($bg)) { $totals[$bg] = 0 }
    $totals[$bg] += [int]$pr.Value
  }
}
''
'=== VERIFY ==='
$bad = 0
$totals.GetEnumerator() | Sort-Object Name | ForEach-Object {
  if ($_.Value -ne 0) { $bad++; "{0,-28} net={1,6} ***" -f $_.Key, $_.Value }
  else { "{0,-28} net={1,6}" -f $_.Key, $_.Value }
}
"nonzero: $bad / $($totals.Count)"

<#
.SYNOPSIS
    Terraria content generator — full tModLoader packs for Portal, Weapon, Projectile, Item, Creature.

.DESCRIPTION
    Produces drop-in ModSources folders with C# gameplay + procedural PNG art + build.txt + localization.
    Portal delegates to TerrariaPortalGenerator.ps1; other kinds use Emit-TerrariaContentModPack.ps1.

.EXAMPLE
    .\TerrariaAssetGenerator.ps1 -AssetType Weapon -Name EmberBrand -DamageClass Melee -Description "molten blade"
    .\TerrariaAssetGenerator.ps1 -AssetType Projectile -Name ArcBolt -WithAmmoItem
    .\TerrariaAssetGenerator.ps1 -AssetType Item -Name StarTonic -ItemKind Consumable
    .\TerrariaAssetGenerator.ps1 -AssetType Creature -Name MossCrawler -Life 120
    .\TerrariaAssetGenerator.ps1 -AssetType Portal -Name VoidGate -Preset Void
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [ValidateSet("Portal", "Weapon", "Projectile", "Item", "Creature")]
    [string]$AssetType,

    [Parameter(Mandatory)]
    [string]$Name,

    [string]$Description = "",
    [string]$OutputDir = "",
    [string]$Color = "",

    # Portal
    [ValidateSet("Void", "Fire", "Ice", "Electric", "Nature", "Shadow", "Light", "Custom")]
    [string]$Preset = "Void",

    # Weapon
    [ValidateSet("Melee", "Ranged", "Magic")]
    [string]$DamageClass = "Melee",
    [int]$Damage = 24,
    [int]$UseTime = 20,

    # Projectile
    [switch]$WithAmmoItem,

    # Item
    [ValidateSet("Material", "Consumable", "Accessory")]
    [string]$ItemKind = "Material",

    # Creature
    [int]$Life = 80,
    [int]$Defense = 6,
    [int]$NpcDamage = 12,

    [int]$Size = 0
)

$ErrorActionPreference = "Stop"
$PSScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $OutputDir = Join-Path $PSScriptRoot "Output"
}
if (-not [System.IO.Path]::IsPathRooted($OutputDir)) {
    $OutputDir = Join-Path (Get-Location) $OutputDir
}
if (-not (Test-Path -LiteralPath $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
}

Write-Host "═══════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Terraria Asset Generator ($AssetType)" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "Name: $Name" -ForegroundColor White
Write-Host "Out:  $OutputDir" -ForegroundColor Gray

$result = $null

switch ($AssetType) {
    "Portal" {
        $portalGen = Join-Path $PSScriptRoot "TerrariaPortalGenerator.ps1"
        if (-not (Test-Path -LiteralPath $portalGen)) { throw "Missing $portalGen" }
        $portalArgs = @{
            PortalName = $Name
            Preset = $Preset
            Description = $Description
            OutputDir = $OutputDir
        }
        $result = & $portalGen @portalArgs
    }
    "Weapon" {
        . (Join-Path $PSScriptRoot "Emit-TerrariaContentModPack.ps1")
        $c = if ($Color) { $Color } else { "#c8c8ff" }
        $sz = if ($Size -gt 0) { $Size } else { 40 }
        $result = Emit-TerrariaWeaponMod -Name $Name -OutputDir $OutputDir -Description $Description `
            -Color $c -DamageClass $DamageClass -Damage $Damage -UseTime $UseTime -Size $sz
    }
    "Projectile" {
        . (Join-Path $PSScriptRoot "Emit-TerrariaContentModPack.ps1")
        $c = if ($Color) { $Color } else { "#88ccff" }
        $sz = if ($Size -gt 0) { $Size } else { 32 }
        $result = Emit-TerrariaProjectileMod -Name $Name -OutputDir $OutputDir -Description $Description `
            -Color $c -Damage $Damage -Size $sz -WithAmmoItem:$WithAmmoItem
    }
    "Item" {
        . (Join-Path $PSScriptRoot "Emit-TerrariaContentModPack.ps1")
        $c = if ($Color) { $Color } else { "#88ffaa" }
        $sz = if ($Size -gt 0) { $Size } else { 32 }
        $result = Emit-TerrariaItemMod -Name $Name -OutputDir $OutputDir -Description $Description `
            -Color $c -ItemKind $ItemKind -Size $sz
    }
    "Creature" {
        . (Join-Path $PSScriptRoot "Emit-TerrariaContentModPack.ps1")
        $c = if ($Color) { $Color } else { "#66aa66" }
        $sz = if ($Size -gt 0) { $Size } else { 40 }
        $dmg = if ($NpcDamage -gt 0) { $NpcDamage } else { $Damage }
        $result = Emit-TerrariaCreatureMod -Name $Name -OutputDir $OutputDir -Description $Description `
            -Color $c -Life $Life -Damage $dmg -Defense $Defense -Size $sz
    }
}

Write-Host ""
Write-Host "Done." -ForegroundColor Green
if ($result -and $result.ModRoot) {
    Write-Host "ModSources folder: $($result.ModRoot)" -ForegroundColor Cyan
} elseif ($result -and $result.ModName) {
    Write-Host "Mod: $($result.ModName)" -ForegroundColor Cyan
}
return $result

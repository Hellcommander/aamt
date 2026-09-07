#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Generate weapon-fire and magic-cast animation assets for mech forms.
    
.DESCRIPTION
    Generates animation spritesheets for:
    - Weapon actions (Aim, Fire, Reload, Holster)
    - Magic casting (Orb Emergence, Channel, Cast, Dissipation)
    - All 10 mech forms with complete animation cycles

# Load shared asset generation settings
$settingsPath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "..\\AssetGenerationSettings.ps1"
if (Test-Path $settingsPath) {
    . $settingsPath
}
    
.PARAMETER ModPath
    Path to the mod directory
    
.PARAMETER OllamaModel
    Ollama model to use
    
.PARAMETER PlanningModel
    Planning model for Ollama
    
.PARAMETER VisualModel
    Visual model for Ollama
    
.PARAMETER UseCppBackend
    Use C++ backend for generation
    
.PARAMETER SkipExisting
    Skip assets that already exist
#>

param(
    [Parameter(Mandatory=$false)]
    [string]$ModPath = "F:\Games\OpenStarbound\mods\Magi-Tech Arcane Alchemy and Sorcery",
    
    [Parameter(Mandatory=$false)]
    [string]$OllamaModel = "codellama:7b-instruct",
    
    [Parameter(Mandatory=$false)]
    [string]$PlanningModel = "",
    
    [Parameter(Mandatory=$false)]
    [string]$VisualModel = "wizardlm-uncensored",
    
    [Parameter(Mandatory=$false)]
    [bool]$UseCppBackend = $true,
    
    [Parameter(Mandatory=$false)]
    [switch]$SkipExisting
)

$ErrorActionPreference = "Stop"
# Validate ModPath is not empty
if ([string]::IsNullOrWhiteSpace($ModPath)) {
    Write-Host "Error: ModPath cannot be empty" -ForegroundColor Red
    Write-Host "  Please provide a valid mod path or use the default" -ForegroundColor Gray
    exit 1
}

$PSScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$assetGenerator = Join-Path $PSScriptRoot "StarboundOllamaAssetGenerator.ps1"

Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Mech Weapon & Magic Animation Generator" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

$generated = 0
$failed = 0
$skipped = 0

# Define mech forms (matching GenerateMechSets.ps1)
$mechForms = @(
    @{Id="phoenix_mk3"; Name="Phoenix MK3"; Element="fire"; Theme="phoenix"},
    @{Id="elemental_guardian"; Name="Elemental Guardian"; Element="elemental"; Theme="elemental"},
    @{Id="cosmic_voyager"; Name="Cosmic Voyager"; Element="cosmic"; Theme="cosmic"},
    @{Id="void_phantom"; Name="Void Phantom"; Element="void"; Theme="void"},
    @{Id="arcane_rune_weaver"; Name="Arcane Rune Weaver"; Element="arcane"; Theme="rune"},
    @{Id="storm_breaker"; Name="Storm Breaker"; Element="electric"; Theme="storm"},
    @{Id="crystal_sentinel"; Name="Crystal Sentinel"; Element="crystal"; Theme="crystal"},
    @{Id="nebula_drifter"; Name="Nebula Drifter"; Element="cosmic"; Theme="nebula"},
    @{Id="shadow_stalker"; Name="Shadow Stalker"; Element="dark"; Theme="stealth"},
    @{Id="runic_warden"; Name="Runic Warden"; Element="rune"; Theme="rune"}
)

# Weapon animation cycles
$weaponAnimations = @(
    @{Id="weaponAim"; Name="Weapon Aim"; Frames=6; Desc="Mech lifts and angles weapon, aiming stance"},
    @{Id="weaponFire"; Name="Weapon Fire"; Frames=4; Desc="Recoil and muzzle-flash blast, firing action"},
    @{Id="weaponReload"; Name="Weapon Reload"; Frames=8; Desc="Magazine swap or energy pack load, reloading sequence"},
    @{Id="weaponHolster"; Name="Weapon Holster"; Frames=6; Desc="Return weapon to rest position, holstering motion"}
)

# Magic animation cycles
$magicAnimations = @(
    @{Id="orbEmergence"; Name="Orb Emergence"; Frames=6; Desc="Orb materializes in mech hand/chamber, magical orb appears"},
    @{Id="magicChannel"; Name="Magic Channel"; Frames=8; Desc="Mech winds up energy into orb, charging magical energy"},
    @{Id="magicCast"; Name="Magic Cast"; Frames=6; Desc="Orb projects magic burst or bolt, casting spell"},
    @{Id="orbDissipation"; Name="Orb Dissipation"; Frames=4; Desc="Residual glow fades after cast, orb fades away"}
)

# Generate weapon animations for each form
Write-Host "Generating Weapon Animation Spritesheets..." -ForegroundColor Yellow
Write-Host ""

foreach ($form in $mechForms) {
    foreach ($anim in $weaponAnimations) {
        $animId = "${form.Id}_${anim.Id}"
        # Validate $ModPath before Join-Path
$animPath = Join-Path $ModPath "animations\mechs\forms\${animId}.animation"
 if ([string]::IsNullOrWhiteSpace($animPath)) {
            Write-Host "  [FAIL] animPath is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
            continue
        }
 if ([string]::IsNullOrWhiteSpace($animPath)) {
            Write-Host "  [FAIL] animPath is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
            continue
        }
        
        if ($SkipExisting -and (Test-Path $animPath)) {
            $skipped++
            Write-Host "  [SKIP] Animation already exists: $animId" -ForegroundColor Gray
        } else {
            try {
                $params = @{
                    AssetType = "AnimationSprite"
                    AssetName = $animId
                    Prompt = "An animation spritesheet for $($form.Name) mech: $($anim.Name) - $($anim.Desc). $($form.Element) elemental mech, side-profile view, $($anim.Frames) frames, 96x96 pixels per frame, horizontal spritesheet. $($form.Theme) theme styling."
                    OllamaModel = $OllamaModel
                    # Validate $ModPath before Join-Path
$tempOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($tempOutputDir)) {
                        Write-Host "  [FAIL] tempOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                        continue
                    }
 if ([string]::IsNullOrWhiteSpace($tempOutputDir)) {
                        Write-Host "  [FAIL] OutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                        continue
                    }
            OutputDir = $tempOutputDir
                }
                if ($PlanningModel) { $params['PlanningModel'] = $PlanningModel }
                if ($VisualModel) { $params['VisualModel'] = $VisualModel }
                $params['UseCppBackend'] = $UseCppBackend
                
                # Add animation-specific parameters
                $animParams = @{
                    FrameCount = $anim.Frames
                    FrameWidth = 96
                    FrameHeight = 96
                    AnimationCycle = if ($anim.Frames -le 4) { 0.3 } elseif ($anim.Frames -le 6) { 0.5 } else { 0.8 }
                    AnimationType = "WeaponAction"
                }
                $params['Parameters'] = $animParams
                
                & $assetGenerator @params | Out-Null
                $generated++
                Write-Host "  [OK] Generated weapon animation: $animId ($($anim.Frames) frames)" -ForegroundColor Green
            } catch {
                $failed++
                Write-Host "  [FAIL] Weapon animation $animId : $_" -ForegroundColor Red
            }
        }
    }
}

Write-Host ""

# Generate magic animations for each form
Write-Host "Generating Magic Animation Spritesheets..." -ForegroundColor Yellow
Write-Host ""

foreach ($form in $mechForms) {
    foreach ($anim in $magicAnimations) {
        $animId = "${form.Id}_${anim.Id}"
        # Validate $ModPath before Join-Path
$animPath = Join-Path $ModPath "animations\mechs\forms\${animId}.animation"
 if ([string]::IsNullOrWhiteSpace($animPath)) {
            Write-Host "  [FAIL] animPath is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
            continue
        }
 if ([string]::IsNullOrWhiteSpace($animPath)) {
            Write-Host "  [FAIL] animPath is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
            continue
        }
        
        if ($SkipExisting -and (Test-Path $animPath)) {
            $skipped++
            Write-Host "  [SKIP] Animation already exists: $animId" -ForegroundColor Gray
        } else {
            try {
                $params = @{
                    AssetType = "AnimationSprite"
                    AssetName = $animId
                    Prompt = "An animation spritesheet for $($form.Name) mech: $($anim.Name) - $($anim.Desc). $($form.Element) elemental mech, side-profile view, $($anim.Frames) frames, 96x96 pixels per frame, horizontal spritesheet. $($form.Theme) theme styling with magical energy effects."
                    OllamaModel = $OllamaModel
                    # Validate $ModPath before Join-Path
$tempOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($tempOutputDir)) {
                        Write-Host "  [FAIL] tempOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                        continue
                    }
 if ([string]::IsNullOrWhiteSpace($tempOutputDir)) {
                        Write-Host "  [FAIL] OutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                        continue
                    }
            OutputDir = $tempOutputDir
                }
                if ($PlanningModel) { $params['PlanningModel'] = $PlanningModel }
                if ($VisualModel) { $params['VisualModel'] = $VisualModel }
                $params['UseCppBackend'] = $UseCppBackend
                
                # Add animation-specific parameters
                $animParams = @{
                    FrameCount = $anim.Frames
                    FrameWidth = 96
                    FrameHeight = 96
                    AnimationCycle = if ($anim.Frames -le 4) { 0.4 } elseif ($anim.Frames -le 6) { 0.6 } else { 1.0 }
                    AnimationType = "MagicCast"
                }
                $params['Parameters'] = $animParams
                
                & $assetGenerator @params | Out-Null
                $generated++
                Write-Host "  [OK] Generated magic animation: $animId ($($anim.Frames) frames)" -ForegroundColor Green
            } catch {
                $failed++
                Write-Host "  [FAIL] Magic animation $animId : $_" -ForegroundColor Red
            }
        }
    }
}

Write-Host ""

# Generate VFX particles for weapon and magic effects
Write-Host "Generating Weapon & Magic VFX Particles..." -ForegroundColor Yellow
Write-Host ""

$vfxParticles = @(
    @{Id="muzzleFlash"; Name="Muzzle Flash"; Type="Electric"; Desc="Muzzle flash particle for weapon fire, bright flash"},
    @{Id="weaponSmoke"; Name="Weapon Smoke"; Type="Smoke"; Desc="Smoke trail from weapon fire"},
    @{Id="magicOrbEmerge"; Name="Magic Orb Emerge"; Type="Magic"; Desc="Particle effect for orb emergence, magical energy"},
    @{Id="magicOrbChannel"; Name="Magic Orb Channel"; Type="Magic"; Desc="Particle effect for channeling, swirling energy"},
    @{Id="magicOrbCast"; Name="Magic Orb Cast"; Type="Electric"; Desc="Particle effect for spell cast, energy burst"},
    @{Id="magicOrbDissipate"; Name="Magic Orb Dissipate"; Type="Magic"; Desc="Particle effect for orb dissipation, fading glow"},
    @{Id="weaponReloadEnergy"; Name="Weapon Reload Energy"; Type="Electric"; Desc="Energy effect during weapon reload"},
    @{Id="weaponAimGlow"; Name="Weapon Aim Glow"; Type="Magic"; Desc="Glowing effect when aiming weapon"}
)

foreach ($particle in $vfxParticles) {
    # Validate $ModPath before Join-Path
$particlePath = Join-Path $ModPath "particles\magitech\${particle.Id}.particle"
 if ([string]::IsNullOrWhiteSpace($particlePath)) {
        Write-Host "  [FAIL] particlePath is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
        continue
    }
 if ([string]::IsNullOrWhiteSpace($particlePath)) {
        Write-Host "  [FAIL] particlePath is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
        continue
    }
    if ($SkipExisting -and (Test-Path $particlePath)) {
        $skipped++
        Write-Host "  [SKIP] Particle already exists: $($particle.Id)" -ForegroundColor Gray
    } else {
        try {
            $params = @{
                AssetType = "Particle"
                AssetName = $particle.Id
                Prompt = "A particle effect: $($particle.Name) - $($particle.Desc). $($particle.Type) type effect"
                OllamaModel = $OllamaModel
                # Validate $ModPath before Join-Path
$tempOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($tempOutputDir)) {
                    Write-Host "  [FAIL] tempOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                    continue
                }
 if ([string]::IsNullOrWhiteSpace($tempOutputDir)) {
                    Write-Host "  [FAIL] OutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                    continue
                }
            OutputDir = $tempOutputDir
            }
            if ($PlanningModel) { $params['PlanningModel'] = $PlanningModel }
            if ($VisualModel) { $params['VisualModel'] = $VisualModel }
            $params['UseCppBackend'] = $UseCppBackend
            
            & $assetGenerator @params | Out-Null
            $generated++
            Write-Host "  [OK] Generated particle: $($particle.Id)" -ForegroundColor Green
        } catch {
            $failed++
            Write-Host "  [FAIL] Particle $($particle.Id) : $_" -ForegroundColor Red
        }
    }
}

Write-Host ""

# Generate sound effects for weapon and magic actions
Write-Host "Generating Weapon & Magic Sound Effects..." -ForegroundColor Yellow
Write-Host ""

$sounds = @(
    @{Id="weapon_aim"; Type="Mechanical"; Desc="Sound when mech aims weapon, mechanical whir"},
    @{Id="weapon_fire"; Type="Impact"; Desc="Weapon firing sound, explosive blast"},
    @{Id="weapon_reload"; Type="Mechanical"; Desc="Weapon reload sound, magazine click and energy pack load"},
    @{Id="weapon_holster"; Type="Mechanical"; Desc="Weapon holster sound, mechanical click"},
    @{Id="magic_orb_emerge"; Type="Magic"; Desc="Sound when magic orb emerges, magical materialization"},
    @{Id="magic_channel"; Type="Magic"; Desc="Sound when channeling magic, low hum building energy"},
    @{Id="magic_cast"; Type="Electric"; Desc="Sound when casting spell, loud magical blast"},
    @{Id="magic_orb_dissipate"; Type="Magic"; Desc="Sound when orb dissipates, fading magical energy"}
)

foreach ($sound in $sounds) {
    # Validate $ModPath before Join-Path
$soundPath = Join-Path $ModPath "sfx\${sound.Id}.ogg"
 if ([string]::IsNullOrWhiteSpace($soundPath)) {
        Write-Host "  [FAIL] soundPath is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
        continue
    }
 if ([string]::IsNullOrWhiteSpace($soundPath)) {
        Write-Host "  [FAIL] soundPath is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
        continue
    }
    if ($SkipExisting -and (Test-Path $soundPath)) {
        $skipped++
        Write-Host "  [SKIP] Sound already exists: $($sound.Id)" -ForegroundColor Gray
    } else {
        try {
            $params = @{
                AssetType = "Sound"
                AssetName = $sound.Id
                Prompt = "A sound effect: $($sound.Desc). $($sound.Type) type sound"
                OllamaModel = $OllamaModel
                # Validate $ModPath before Join-Path
$tempOutputDir = Join-Path $ModPath "assets"
 if ([string]::IsNullOrWhiteSpace($tempOutputDir)) {
                    Write-Host "  [FAIL] tempOutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                    continue
                }
 if ([string]::IsNullOrWhiteSpace($tempOutputDir)) {
                    Write-Host "  [FAIL] OutputDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
                    continue
                }
            OutputDir = $tempOutputDir
            }
            if ($PlanningModel) { $params['PlanningModel'] = $PlanningModel }
            if ($VisualModel) { $params['VisualModel'] = $VisualModel }
            $params['UseCppBackend'] = $UseCppBackend
            
            # Add sound-specific parameters
            $soundParams = @{
                SoundType = $sound.Type
                Format = "ogg"
            }
            $params['Parameters'] = $soundParams
            
            & $assetGenerator @params | Out-Null
            $generated++
            Write-Host "  [OK] Generated sound: $($sound.Id)" -ForegroundColor Green
        } catch {
            $failed++
            Write-Host "  [FAIL] Sound $($sound.Id) : $_" -ForegroundColor Red
        }
    }
}

Write-Host ""

# Generate JSON config template for form animations
Write-Host "Generating Animation JSON Config Templates..." -ForegroundColor Yellow
Write-Host ""

# Validate $ModPath before Join-Path
$configDir = Join-Path $ModPath "Data\Config\Mechs\animations"
 if ([string]::IsNullOrWhiteSpace($configDir)) {
    Write-Host "  [FAIL] configDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
 if ([string]::IsNullOrWhiteSpace($configDir)) {
    Write-Host "  [FAIL] configDir is null (${ModPath}: '${ModPath}')" -ForegroundColor Red
    continue
}
if (-not (Test-Path $configDir)) {
    New-Item -ItemType Directory -Path $configDir -Force | Out-Null
}

# Create weapon animation config template
$weaponConfig = @{
    weaponAimAnimation = @{
        frames = 6
        frameSize = @(96, 96)
        image = "/sprites/forms/{formId}_weaponAim.png"
    }
    weaponFireAnimation = @{
        frames = 4
        frameSize = @(96, 96)
        image = "/sprites/forms/{formId}_weaponFire.png"
    }
    weaponReloadAnimation = @{
        frames = 8
        frameSize = @(96, 96)
        image = "/sprites/forms/{formId}_weaponReload.png"
    }
    weaponHolsterAnimation = @{
        frames = 6
        frameSize = @(96, 96)
        image = "/sprites/forms/{formId}_weaponHolster.png"
    }
}

$weaponConfigPath = Join-Path $configDir "weapon_animations_template.json"
$weaponConfig | ConvertTo-Json -Depth 10 | Set-Content -Path $weaponConfigPath -Encoding UTF8
Write-Host "  [OK] Created weapon animation config template" -ForegroundColor Green
$generated++

# Create magic animation config template
$magicConfig = @{
    orbEmergenceAnimation = @{
        frames = 6
        frameSize = @(96, 96)
        image = "/sprites/forms/{formId}_orbEmerge.png"
    }
    magicChannelAnimation = @{
        frames = 8
        frameSize = @(96, 96)
        image = "/sprites/forms/{formId}_magicChannel.png"
    }
    magicCastAnimation = @{
        frames = 6
        frameSize = @(96, 96)
        image = "/sprites/forms/{formId}_magicCast.png"
    }
    orbDissipateAnimation = @{
        frames = 4
        frameSize = @(96, 96)
        image = "/sprites/forms/{formId}_orbDissipate.png"
    }
}

$magicConfigPath = Join-Path $configDir "magic_animations_template.json"
$magicConfig | ConvertTo-Json -Depth 10 | Set-Content -Path $magicConfigPath -Encoding UTF8
Write-Host "  [OK] Created magic animation config template" -ForegroundColor Green
$generated++

# Create enhanced form config template with all new fields
$enhancedFormTemplate = @{
    id = "example_form"
    displayName = "Example Form"
    tags = @("movement", "air")
    elementAffinity = "electric"
    factions = @{
        allow = @("player", "ally")
        deny = @("hostile")
    }
    levelCap = 10
    xpPerKill = 5
    upgradeSlots = 2
    stats = @{
        speedMult = 1.0
        armorMult = 1.0
    }
    statFormulas = @{
        speedMult = "1 + level*0.05"
        armorMult = "1 + level*0.1"
    }
    locomotion = @{
        type = "bipedal"
        maxSpeed = 8
        acceleration = 40
        groundDrag = 50
        airControl = 0.3
    }
    abilities = @{
        charge = @{
            inputAction = "mechFormAbility"
            type = "press"
            cooldown = 4.0
            force = 60.0
            damage = 35
            stunDuration = 1.5
        }
    }
    vfxEnter = "/vfx/forms/{formId}_enter.particle"
    vfxLoop = "/vfx/forms/{formId}_loop.particle"
    vfxExit = "/vfx/forms/{formId}_exit.particle"
    sfxEnter = "forms/{formId}_enter.wav"
    sfxExit = "forms/{formId}_exit.wav"
    collisionBox = @(
        @(-1.0, -1.5),
        @(1.0, -1.5),
        @(1.0, 1.5),
        @(-1.0, 1.5)
    )
    environment = @{
        underwater = @{
            speedMult = 0.6
            acceleration = 0.5
        }
        lava = @{
            armorMult = 0.8
        }
    }
    weaponAimAnimation = @{
        frames = 6
        frameSize = @(96, 96)
        image = "/sprites/forms/{formId}_weaponAim.png"
    }
    weaponFireAnimation = @{
        frames = 4
        frameSize = @(96, 96)
        image = "/sprites/forms/{formId}_weaponFire.png"
    }
    weaponReloadAnimation = @{
        frames = 8
        frameSize = @(96, 96)
        image = "/sprites/forms/{formId}_weaponReload.png"
    }
    weaponHolsterAnimation = @{
        frames = 6
        frameSize = @(96, 96)
        image = "/sprites/forms/{formId}_weaponHolster.png"
    }
    orbEmergenceAnimation = @{
        frames = 6
        frameSize = @(96, 96)
        image = "/sprites/forms/{formId}_orbEmerge.png"
    }
    magicChannelAnimation = @{
        frames = 8
        frameSize = @(96, 96)
        image = "/sprites/forms/{formId}_magicChannel.png"
    }
    magicCastAnimation = @{
        frames = 6
        frameSize = @(96, 96)
        image = "/sprites/forms/{formId}_magicCast.png"
    }
    orbDissipateAnimation = @{
        frames = 4
        frameSize = @(96, 96)
        image = "/sprites/forms/{formId}_orbDissipate.png"
    }
    onEnter = "FormBus.{FormName}.enter"
    onUpdate = "FormBus.{FormName}.update"
    onExit = "FormBus.{FormName}.exit"
}

$formTemplatePath = Join-Path $configDir "enhanced_form_template.json"
$enhancedFormTemplate | ConvertTo-Json -Depth 10 | Set-Content -Path $formTemplatePath -Encoding UTF8
Write-Host "  [OK] Created enhanced form config template" -ForegroundColor Green
$generated++

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Generation Complete" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "Generated: $generated assets" -ForegroundColor Green
Write-Host "Skipped: $skipped assets (already exist)" -ForegroundColor Gray
Write-Host "Failed: $failed assets" -ForegroundColor $(if ($failed -gt 0) { "Red" } else { "Green" })
Write-Host ""
Write-Host "Animation Breakdown:" -ForegroundColor Yellow
Write-Host "  - Weapon animations: $($weaponAnimations.Count) types × $($mechForms.Count) forms = $($weaponAnimations.Count * $mechForms.Count) animations" -ForegroundColor Gray
Write-Host "  - Magic animations: $($magicAnimations.Count) types × $($mechForms.Count) forms = $($magicAnimations.Count * $mechForms.Count) animations" -ForegroundColor Gray
Write-Host "  - Total frames: $($weaponAnimations.Count * $mechForms.Count * 24 + $magicAnimations.Count * $mechForms.Count * 24) frames" -ForegroundColor Gray
Write-Host ""
Write-Host "Config templates saved to: $configDir" -ForegroundColor Cyan
Write-Host ""

# Script to organize tools by game type
# Use script's directory as Tools root (portable)
$toolsPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $toolsPath

# Function to move files
function Move-FilesToFolder {
    param(
        [string[]]$Files,
        [string]$Folder
    )

# Load shared asset generation settings
$settingsPath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) ".\\AssetGenerationSettings.ps1"
if (Test-Path $settingsPath) {
    . $settingsPath
}
    
    $destPath = Join-Path $toolsPath $Folder
    if (-not (Test-Path $destPath)) {
        New-Item -ItemType Directory -Path $destPath -Force | Out-Null
    }
    
    foreach ($pattern in $Files) {
        $matchedFiles = Get-ChildItem -Path $toolsPath -Filter $pattern -ErrorAction SilentlyContinue
        foreach ($file in $matchedFiles) {
            if ($file -and -not $file.PSIsContainer) {
                try {
                    Move-Item -Path $file.FullName -Destination $destPath -Force -ErrorAction Stop
                    Write-Host "Moved: $($file.Name) -> $Folder"
                } catch {
                    Write-Warning "Failed to move $($file.Name): $_"
                }
            }
        }
    }
}

# Qud files
$qudFiles = @(
    "BakeQudTile.*", "ExportQudTiles.*", "QudTileAIGenerator.*", "qud_tile_*", 
    "QUD_TILE_*", "DRAWING_TO_QUD_TILE_GUIDE.md"
)
Move-FilesToFolder -Files $qudFiles -Folder "Qud"

# Nova Drift files
$novaDriftFiles = @(
    "NovaDriftFXGenerator.*", "nova_drift_fx_*", "blender_nova_drift_fx_renderer.*",
    "NOVA_DRIFT_*"
)
Move-FilesToFolder -Files $novaDriftFiles -Folder "NovaDrift"

# ToME files
$tomeFiles = @(
    "LaunchToME*", "tome_*", "tomegen_*", "tomegen_settings.json",
    "TOME_*", "requirements_tome_checker.txt"
)
Move-FilesToFolder -Files $tomeFiles -Folder "ToME"

# CDDA files
$cddaFiles = @(
    "CDDABeeSwarmGenerator.*"
)
Move-FilesToFolder -Files $cddaFiles -Folder "CDDA"
# Move CDDAMods folder separately
if (Test-Path "CDDAMods") {
    Move-Item -Path "CDDAMods" -Destination "CDDA" -Force -ErrorAction SilentlyContinue
    Write-Host "Moved: CDDAMods -> CDDA"
}

# Elin files
$elinFiles = @(
    "ElinTextureGenerator.*", "ElinSpellAssetGenerator.*", "elin_*", "ELIN_*"
)
Move-FilesToFolder -Files $elinFiles -Folder "Elin"
# Move ElinAssets folder separately
if (Test-Path "ElinAssets") {
    Move-Item -Path "ElinAssets" -Destination "Elin" -Force -ErrorAction SilentlyContinue
    Write-Host "Moved: ElinAssets -> Elin"
}

# Terraria files
$terrariaFiles = @(
    "GenerateTerrariaPortals.*", "TerrariaPortal*", "terraria_portal_*", "TERRARIA_*"
)
Move-FilesToFolder -Files $terrariaFiles -Folder "Terraria"

# Starbound files
$starboundFiles = @(
    "Starbound*", "STARBOUND_*"
)
Move-FilesToFolder -Files $starboundFiles -Folder "Starbound"

# Ratlich files
$ratlichFiles = @(
    "generate_ratlich_assets*", "LaunchRatlichAssetGenerator.*", "ratlich_talents.json",
    "RATLICH_ASSET_GENERATOR_GUIDE.md", "extract_ratlich_talents.*"
)
Move-FilesToFolder -Files $ratlichFiles -Folder "Ratlich"

# Glutton files
$gluttonFiles = @(
    "glutton_remade_talents.json", "extract_glutton_talents.*", "GLUTTON_REMADE_ASSETS_GUIDE.md"
)
Move-FilesToFolder -Files $gluttonFiles -Folder "Glutton"

# Smog Devil files
$smogDevilFiles = @(
    "generate_smog_devil_assets.*", "smog_devil_talents.json", "SMOG_DEVIL_ASSETS_GENERATION.md"
)
Move-FilesToFolder -Files $smogDevilFiles -Folder "SmogDevil"

# Soulash files
$soulashFiles = @(
    "SoulashAssetGenerator.*", "SOULASH_ASSET_GENERATOR_GUIDE.md"
)
Move-FilesToFolder -Files $soulashFiles -Folder "Soulash"

# Common/Shared tools (Blender setup, general utilities)
$commonFiles = @(
    "AddBlenderToPath.*", "FindBlender.*", "BLENDER_*", "blender_rigging_*",
    "blender_asset_spritesheet_export.*", "blender_projectile_renderer.*",
    "blender_shield_*", "bake_texture.*", "BatchBakeTextures.*",
    "check_blender_output.*", "CROSS_GAME_SPRITESHEET_GUIDE.md", "cross_game_spritesheet.*",
    "CrossGameSpritesheet.*", "CrossModCompatibilityAssetGenerator.*",
    "ai_material_generator.*", "material_generator.*", "GenerateMaterialSpec.*",
    "particle_*", "ParticleEffectGenerator.*", "PARTICLE_*",
    "projectile_*", "ProjectileSystemGenerator.*", "PROJECTILE_*",
    "shield_*", "ShieldArmorSystemGenerator.*", "ShieldAuraGenerator.*", "SHIELD_*",
    "weapon_mutation_*", "WeaponMutationGenerator.*", "WEAPON_MUTATION_*",
    "ollama_*", "OllamaVisualVariationGenerator.*", "OLLAMA_*",
    "analyze_variations.*", "filter_low_quality_variations.*", "generate_test_images.*",
    "CreateQuickTestSamples.*", "GenerateQualityTestAssets.*", "QUALITY_*",
    "file_safety_validator.*", "validate_registry.*", "example_registry_entry.json",
    "asset_registry_schema.json", "create_registry_template.*",
    "line_drawing_processor.*", "LINE_DRAWING_TO_ASSET_GUIDE.md",
    "sketch_to_mesh.*", "SKETCH_TO_ASSET_GUIDE.md",
    "spritesheet_assembly.*", "SPRITESHEET_FORMAT_GUIDE.md",
    "extract_talents.*", "list_synergies.*", "SYNERGY_EXAMPLES.md"
)
Move-FilesToFolder -Files $commonFiles -Folder "Common"

# Transcendence-specific files (Space Whale, mod tools, etc.)
$transcendenceFiles = @(
    "SpaceWhale*", "space_whale_*", "SPACE_WHALE_*",
    "Transcendence*", "transcendence_*", "TRANSCENDENCE_*",
    "CheckTranscendenceXml*", "ExportToTranscendenceXML.*",
    "mod_fixer*", "MOD_FIXER_*", "requirements_mod_fixer.txt",
    "CompileApiFolder.*", "GenerateApiRules.*", "api_rules*", "API_RULES_*",
    "ProcessModsFor207.*", "UpdateModToApi.*", "ValidateModAgainstApi.*",
    "FixMod.*", "FixCommonIssues.*", "FixBOM.*", "FixMissingHumanSpaceLibrary.*",
    "ScanMod.*", "QuickScan.*", "FindMissingEntities.*",
    "GetXmlIssues.*", "CheckQuality.*", "ShowErrors.*",
    "AssetGeneratorControlRoom*", "AssetMakerAI.*", "AssetRegistry.*",
    "GenerateAllAssets.*", "GenerateAssetTextures.*", "GenerateAudioAssets.*",
    "GenerateComprehensiveAssets.*", "GenerateFXAssets.*", "GenerateRigging.*",
    "GenerateSpritesheet120Facings.*", "GenerateTextures.*", "GenerateVisualLanguage.*",
    "MultiAssetGenerator.*", "LaunchAssetGeneratorGUI.*", "LaunchControlRoom.*",
    "LaunchModFixer.*", "BuildReferenceArchive.*", "RunMultiArchive.*",
    "ValidateArchive.*", "RunAllTests.*", "Test*",
    "CometGenerator.*",
    "ASSET_*", "AUTO_UPDATE_GUIDE.md", "BATCH_FILE_COMPARISON.md",
    "CHANGELOG.md", "CONTROL_ROOM_*", "DEPENDENCY_GRAPH_*", "DIFF_MODE_GUIDE.md",
    "DRAG_*", "EVENT_FLOW_GUIDE.md", "EXPORT_MOD_ASSETS_GUIDE.md",
    "FEATURES.md", "FIXING_GUIDE.md", "HEALTH_REPORT_GUIDE.md",
    "IMAGE_QUALITY_ASSESSMENT.md", "INHERITANCE_RESOLUTION_GUIDE.md",
    "INSTALL_GUIDE.md", "LIVE_PREVIEW_GUIDE.md", "LOGGER_*", "LOGGING_*",
    "MASTER_SYSTEM_OVERVIEW.md", "MIGRATION_SAFETY_*", "MULTI_*",
    "NODE_GROUPS_EXPORT_GUIDE.md", "PRODUCTION_TEXTURE_PIPELINE_GUIDE.md",
    "QUICK_REFERENCE.md", "QUICK_START*.md", "README*.md", "RELEASE_NOTES.md",
    "RESOURCE_INTEGRITY_GUIDE.md", "SEMANTIC_VALIDATION_GUIDE.md",
    "SHADER_RECIPES.md", "SYSTEM_*", "TEXTURE_BAKER_GUIDE.md",
    "TML_STATIC_ANALYSIS_GUIDE.md", "TODO*.md", "TROUBLESHOOTING.md",
    "UNID_INTELLIGENCE_GUIDE.md", "UPDATE_207_*", "VERSION_*",
    "VISUAL_QUALITY_TEST.md", "WORKFLOW_207.md", "WIZARDLM_VISUAL_SAFETY.md",
    "CODELAMA_*", "DUAL_MODEL_*", "FunctionList_*", "ui_data_binding_model.json",
    "test_*", "example_*", "entity_analysis_*.txt", "process_log_*.txt",
    "scan_results_*.txt", "tool_debug.log", "transcendence_integration_examples.xml"
)
Move-FilesToFolder -Files $transcendenceFiles -Folder "Transcendence"

Write-Host "`nOrganization complete!"
Write-Host "All files have been organized into game-specific folders."


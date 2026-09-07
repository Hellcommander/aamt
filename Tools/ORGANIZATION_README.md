# Tools Organization

This directory has been organized into game-specific folders to make it easier to find files depending on the game type you're working with.

## Folder Structure

### Game-Specific Folders

- **ElementalReforged/** - Monster race armor/asset generator for Elemental Reforged (LH_Legacy_Expansion)
- **Transcendence/** - All Transcendence-specific tools, mod fixers, Space Whale generators, API tools, documentation, and art assets
  - **Transcendence/TranscendenceArt/** - Transcendence art assets and model references (races, ships, items, etc.)
  - **Transcendence/NovaDrift/** - Nova Drift-style FX generators for Transcendence (AI-generated visual effects inspired by Nova Drift)
  - **Transcendence/RegistryGeneratedAssets/** - Transcendence registry-generated assets (if any, per-game registry assets)
- **Qud/** - Caves of Qud tile generators and exporters
- **DwarfFortress/** - Dwarf Fortress creature + civilization tool (ChooseYourCreature, RAW writers, body editor)
- **ToME/** - Tales of Maj'Eyal asset generators and mod checkers
  - **ToME/Ratlich/** - Ratlich race mod asset generators
  - **ToME/Glutton/** - Glutton character mod asset tools
  - **ToME/SmogDevil/** - Smog Devil mod asset generators
- **CDDA/** - Cataclysm: Dark Days Ahead tools (bee swarm generator, mods)
- **Elin/** - Elin texture and spell asset generators
  - **Elin/RegistryGeneratedAssets/** - Elin registry-generated assets (per-game registry assets)
- **Terraria/** - Terraria portal generators
- **Starbound/** - Starbound asset generators (animations, behaviors, ships, tiles, etc.)
- **Soulash/** - Soulash asset generators

### Shared/Common Tools

- **Common/** - Cross-game tools and utilities:
  - Blender setup and rendering tools
  - Material generators
  - Particle effect generators
  - Projectile system generators
  - Shield/armor generators
  - Weapon mutation generators
  - Quality assessment tools
  - Registry validators
  - Visual variation generators
  - Spritesheet assembly tools
  - And other shared utilities

### Output and Data Folders

The following folders remain in the root directory as they contain generated assets, backups, logs, and reference data:

- **AI_Generated_Assets/** - AI-generated asset files
- **Backups/** - Backup files
- **ExportedAssets/** - Exported game assets
- **GeneratedAssets/** - Generated asset files
- **Logs/** - Tool execution logs
- **Output/** - Output files from various generators
- **ParticleEffects/** - Particle effect test files
- **QualityTestAssets_Final/** - Quality test results
- **reference_archive_*** - Reference archive folders
- **SDK/** - Software development kit files
- **TestAssets_QualityCheck/** - Quality check test assets
- **TestBaked/** - Baked texture tests
- **TestCometAssets/** - Comet asset tests
- **TestCrossGame/** - Cross-game test files
- **TestOutput/** - Test output files

## Quick Reference

- **Looking for Transcendence tools?** → Check `Transcendence/` folder
- **Looking for Blender or shared utilities?** → Check `Common/` folder
- **Looking for Dwarf Fortress civ/creature tools?** → Check `DwarfFortress/` folder
- **Looking for game-specific generators?** → Check the appropriate game folder (Qud, DwarfFortress, ToME, etc.)
- **Looking for Nova Drift-style effects for Transcendence?** → Check `Transcendence/NovaDrift/` folder
- **Looking for ToME mod tools?** → Check `ToME/Ratlich/`, `ToME/Glutton/`, or `ToME/SmogDevil/` folders
- **Looking for generated assets?** → Check `Output/` or `GeneratedAssets/` folders
- **Looking for registry-generated assets?** → Check the game-specific folder (e.g., `Elin/RegistryGeneratedAssets/`)
- **Looking for logs?** → Check `Logs/` folder

## Organization Script

The `OrganizeTools.ps1` script in the root directory was used to organize these files. You can review it to understand how files were categorized, or run it again if you add new files that need organization.


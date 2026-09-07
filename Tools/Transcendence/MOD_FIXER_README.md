# Mod Fixer - Ollama-Assisted Mod Fixing System

A comprehensive, profile-based mod fixing system that uses local Ollama models to safely fix mod issues with automated validation and sandboxing.

## Features

- **Per-Game Profiles**: YAML-based profiles for different game engines (ToME, Unity, Minecraft Fabric)
- **Ollama Integration**: Uses local Ollama models with intelligent model routing
- **Sandbox Safety**: All fixes tested in isolated sandbox before application
- **Automated Validation**: Runs game-specific validation commands
- **Rollback Support**: Automatic rollback patch generation
- **Fix Reports**: Detailed JSON reports with traceability

## Quick Start

### Prerequisites

1. **Ollama installed and running** (http://localhost:11434)
2. **Python 3.8+** with required packages:
   ```bash
   pip install pyyaml requests
   ```

3. **Recommended models**:
   - CodeLlama-34B (for code generation)
   - WizardLM-uncensored-13B (for visual/orchestration)

### Basic Usage

```bash
# Fix a ToME mod issue (dry-run)
python mod_fixer.py path/to/mod --profile tome --issue "missing sprite reference"

# Fix with specific template
python mod_fixer.py path/to/mod --profile tome --issue "syntax error" --template fix_syntax_error

# Apply fix (after reviewing dry-run)
python mod_fixer.py path/to/mod --profile tome --issue "missing sprite" --apply

# Save fix report
python mod_fixer.py path/to/mod --profile tome --issue "balance issue" --output-report fix_report.json
```

## Profile System

Profiles define game-specific rules, validation commands, and safety limits. Profiles are stored in `mod_fixer_profiles/`:

- `tome.yaml` - Tales of Maj'Eyal (T-Engine4)
- `unity.yaml` - Unity mods
- `minecraft_fabric.yaml` - Minecraft Fabric mods
- `transcendence.yaml` - Transcendence XML mods

### Profile Structure

```yaml
game: "tome"
engine: "T-Engine4"
system_prompt: |
  You are a local mod fixer...
allowed_files:
  - "*.lua"
  - "data/**/*.png"
validation:
  - command: "lua -l luacheck"
    description: "Lint Lua files"
safety:
  sandbox: "directory"
  max_changes: 200
  timeout_seconds: 60
prompts:
  fix_missing_sprite: |
    Find missing sprite references...
```

## Prompt Templates

Ready-to-use prompt templates are available in `mod_fixer_prompts.py`:

### ToME Templates

- `fix_missing_sprite` - Fix missing sprite references
- `balance_talent` - Balance talent parameters
- `fix_syntax_error` - Fix Lua syntax errors
- `fix_missing_locale` - Generate missing locale entries
- `fix_manifest` - Fix or generate mod manifest

### Unity Templates

- `fix_prefab_refs` - Fix broken prefab references
- `optimize_textures` - Suggest texture compression settings
- `fix_assembly_refs` - Fix missing assembly references
- `fix_compile_errors` - Fix C# compilation errors

### Minecraft Fabric Templates

- `fix_mixin` - Fix mixin configuration errors
- `fix_fabric_json` - Fix fabric.mod.json
- `fix_resource_paths` - Fix incorrect resource paths
- `balance_item` - Balance item properties

### Transcendence Templates

- `fix_invalid_entity` - Fix invalid entity references
- `fix_xml_syntax` - Fix XML syntax errors
- `fix_tml_syntax` - Fix TML syntax errors
- `fix_bom` - Remove UTF-8 BOM
- `fix_entity_encoding` - Fix entity encoding in strings
- `fix_missing_entity` - Add missing entity definitions
- `fix_event_handler` - Fix event handler issues
- `fix_self_closing_tags` - Convert to self-closing tags
- `fix_doctype_entities` - Fix DOCTYPE entity definitions

## Workflow

### 1. Profile Selection

The system loads the appropriate profile based on `--profile` argument. The profile sets:
- System prompt for Ollama
- Allowed file types
- Validation commands
- Safety limits

### 2. Preflight Analysis

Before generating fixes, the system:
- Validates mod structure
- Checks for common issues
- Collects context files

### 3. Fix Generation

Ollama generates a fix using:
- Profile system prompt
- Issue description
- Context files
- Prompt template (if specified)

### 4. Sandbox Testing

All fixes are applied in a sandbox:
- Copy of mod in temp directory
- Patch applied
- Validation commands run
- Results captured

### 5. Review and Approval

The system presents:
- Unified diff of changes
- Validation results
- Rollback patch
- Fix report metadata

### 6. Application

After human approval (`--apply` flag):
- Patch applied to real mod
- Final validation run
- Fix report saved

## Safety Features

### Sandboxing

- **Directory Mode**: Copy mod to temp directory (default)
- **Container Mode**: Docker container (future)
- **Runspace Mode**: PowerShell runspace (Windows)

### Limits

- `max_changes`: Maximum lines changed per fix
- `timeout_seconds`: Maximum execution time
- `max_file_size_mb`: Maximum file size to process

### Validation

Each profile defines validation commands:
- Linters (luacheck, etc.)
- Build systems (gradle, dotnet)
- Engine smoke tests
- Custom validators

### Rollback

Every fix includes:
- Automatic rollback patch generation
- Rollback patch hash in report
- Manual rollback instructions

## Fix Reports

Reports are saved as JSON with:

```json
{
  "profile": "tome",
  "prompt": "Fix missing sprite...",
  "model_version": "codellama:34b",
  "patch_hash": "a1b2c3d4...",
  "rollback_hash": "e5f6g7h8...",
  "validation_results": {
    "Lint Lua files": {
      "success": true,
      "stdout": "...",
      "stderr": ""
    }
  },
  "timestamp": "2025-01-15T10:30:00",
  "applied": false,
  "files_changed": ["data/talents/gen_talent_123.lua"],
  "lines_changed": 15
}
```

## Examples

### Example 1: Fix Missing Sprite

```bash
python mod_fixer.py ./my_tome_mod \
  --profile tome \
  --issue "missing sprite 'gfx/sprites/gen_proj_123.png' referenced in data/talents/gen_talent_123.lua" \
  --template fix_missing_sprite \
  --context-files "data/talents/gen_talent_123.lua"
```

### Example 2: Balance Talent

```bash
python mod_fixer.py ./my_tome_mod \
  --profile tome \
  --issue "talent gen_talent_123 is overpowered, needs balance adjustment" \
  --template balance_talent \
  --context-files "data/talents/gen_talent_123.lua"
```

### Example 3: Fix Unity Prefab

```bash
python mod_fixer.py ./my_unity_mod \
  --profile unity \
  --issue "broken prefab reference in Assets/Prefabs/MyPrefab.prefab" \
  --template fix_prefab_refs \
  --context-files "Assets/Prefabs/MyPrefab.prefab"
```

### Example 4: Fix Transcendence Entity

```bash
python mod_fixer.py ./my_transcendence_mod \
  --profile transcendence \
  --issue "Invalid entity: itMyWeapon" \
  --template fix_invalid_entity \
  --context-files "*.xml"
```

### Example 5: Fix Transcendence TML Syntax

```bash
python mod_fixer.py ./my_transcendence_mod \
  --profile transcendence \
  --issue "unbalanced parentheses in OnDamage event" \
  --template fix_tml_syntax \
  --context-files "MyMod.xml"
```

## Integration with Existing Tools

The mod fixer integrates with existing ToME tools:

- Uses `ollama_model_router.py` for model selection
- Compatible with `tome_mod_checker.py` for validation
- Can be called from `tome_asset_generator_ai.py`

## Advanced Usage

### Custom Profiles

Create custom profiles in `mod_fixer_profiles/`:

```yaml
game: "my_game"
engine: "Custom Engine"
system_prompt: |
  Custom system prompt...
# ... rest of profile
```

### Custom Prompt Templates

Add templates to `mod_fixer_prompts.py`:

```python
@staticmethod
def my_custom_template(game: str, **kwargs) -> str:
    return f"""[PROFILE: {game}]
CONTEXT:
...
TASK:
...
"""
```

### Batch Processing

Process multiple mods:

```bash
for mod in mods/*/; do
  python mod_fixer.py "$mod" --profile tome --issue "common issue" --output-report "reports/$(basename $mod).json"
done
```

## Troubleshooting

### Ollama Not Available

- Check Ollama is running: `curl http://localhost:11434/api/tags`
- Verify model router can detect models
- Check firewall/network settings

### Validation Failures

- Ensure validation commands are installed
- Check command paths in profile
- Review validation output in fix report

### Patch Application Errors

- Verify file permissions
- Check disk space
- Review patch format (unified diff)

## Best Practices

1. **Always dry-run first**: Review fixes before applying
2. **Use templates**: Leverage prompt templates for consistency
3. **Review reports**: Check validation results before applying
4. **Keep backups**: Backup mods before applying fixes
5. **Version control**: Commit fixes to version control
6. **Test thoroughly**: Test fixed mods in-game

## See Also

- [MOD_FIXER_QUICK_START.md](MOD_FIXER_QUICK_START.md) - Quick start guide
- [MOD_FIXER_SUMMARY.md](MOD_FIXER_SUMMARY.md) - Implementation summary
- [MOD_FIXER_TRANSCENDENCE_GUIDE.md](MOD_FIXER_TRANSCENDENCE_GUIDE.md) - Transcendence-specific guide

## License

Part of the Transcendence Mod Tools collection.


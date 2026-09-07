# Mod Fixer Quick Start Guide

## Installation

1. **Install Python dependencies:**
   ```bash
   pip install -r requirements_mod_fixer.txt
   ```

2. **Ensure Ollama is running:**
   ```bash
   # Check if Ollama is available
   curl http://localhost:11434/api/tags
   ```

3. **Install recommended models:**
   ```bash
   ollama pull codellama:34b
   ollama pull wizardlm-uncensored:13b
   ```

## Quick Examples

### Fix Missing Sprite (ToME)

```bash
python mod_fixer.py "path/to/tome_mod" \
  --profile tome \
  --issue "missing sprite 'gfx/sprites/gen_proj_123.png' referenced in data/talents/gen_talent_123.lua" \
  --template fix_missing_sprite
```

### Fix Syntax Error (ToME)

```bash
python mod_fixer.py "path/to/tome_mod" \
  --profile tome \
  --issue "syntax error: unexpected symbol near 'end' at line 45" \
  --template fix_syntax_error \
  --context-files "data/talents/gen_talent_123.lua"
```

### Balance Talent (ToME)

```bash
python mod_fixer.py "path/to/tome_mod" \
  --profile tome \
  --issue "talent gen_talent_123 is overpowered" \
  --template balance_talent \
  --context-files "data/talents/gen_talent_123.lua"
```

### Fix Unity Prefab Reference

```bash
python mod_fixer.py "path/to/unity_mod" \
  --profile unity \
  --issue "broken prefab reference in Assets/Prefabs/MyPrefab.prefab" \
  --template fix_prefab_refs
```

### Fix Minecraft Fabric Mixin

```bash
python mod_fixer.py "path/to/fabric_mod" \
  --profile minecraft_fabric \
  --issue "mixin error: target class not found" \
  --template fix_mixin \
  --context-files "src/main/java/com/example/MyMixin.java"
```

## Using the Batch Launcher (Windows)

```batch
REM Basic usage
LaunchModFixer.bat "path\to\mod" --profile tome --issue "your issue description"

REM With template
LaunchModFixer.bat "path\to\mod" --profile tome --issue "syntax error" --template fix_syntax_error

REM Apply fix (after reviewing dry-run)
LaunchModFixer.bat "path\to\mod" --profile tome --issue "missing sprite" --apply
```

## Workflow

1. **Dry-run first** (default):
   ```bash
   python mod_fixer.py mod_path --profile tome --issue "description"
   ```

2. **Review the output:**
   - Check the diff
   - Review validation results
   - Verify files changed

3. **Apply if satisfied:**
   ```bash
   python mod_fixer.py mod_path --profile tome --issue "description" --apply
   ```

4. **Save report:**
   ```bash
   python mod_fixer.py mod_path --profile tome --issue "description" --output-report report.json
   ```

## Available Templates

### ToME Templates
- `fix_missing_sprite` - Fix missing sprite references
- `balance_talent` - Balance talent parameters
- `fix_syntax_error` - Fix Lua syntax errors
- `fix_missing_locale` - Generate missing locale entries
- `fix_manifest` - Fix or generate mod manifest

### Unity Templates
- `fix_prefab_refs` - Fix broken prefab references
- `optimize_textures` - Suggest texture compression
- `fix_assembly_refs` - Fix missing assembly references
- `fix_compile_errors` - Fix C# compilation errors

### Minecraft Fabric Templates
- `fix_mixin` - Fix mixin configuration errors
- `fix_fabric_json` - Fix fabric.mod.json
- `fix_resource_paths` - Fix incorrect resource paths
- `balance_item` - Balance item properties

## Troubleshooting

### "Ollama is not available"
- Ensure Ollama is running: `ollama serve`
- Check URL: `curl http://localhost:11434/api/tags`
- Verify models are installed: `ollama list`

### "Profile not found"
- Check profile exists in `mod_fixer_profiles/`
- Verify profile name matches exactly (tome, unity, minecraft_fabric)

### "Validation failed"
- Ensure validation commands are installed
- Check command paths in profile YAML
- Review validation output in fix report

### "Patch exceeds max_changes"
- Review the fix - it may be too large
- Increase `max_changes` in profile if needed
- Consider breaking into smaller fixes

## Next Steps

- Read [MOD_FIXER_README.md](MOD_FIXER_README.md) for detailed documentation
- Explore profile customization in `mod_fixer_profiles/`
- Add custom templates in `mod_fixer_prompts.py`


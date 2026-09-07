# Mod Fixer for Transcendence - Quick Guide

## Overview

The mod fixer now supports Transcendence XML mods with specialized profiles and prompt templates for common Transcendence-specific issues.

## Quick Start

### Fix Invalid Entity Reference

```bash
python mod_fixer.py "path/to/transcendence_mod" \
  --profile transcendence \
  --issue "Invalid entity: itMyWeapon" \
  --template fix_invalid_entity \
  --context-files "*.xml"
```

### Fix XML Syntax Error

```bash
python mod_fixer.py "path/to/transcendence_mod" \
  --profile transcendence \
  --issue "content expected at line 45" \
  --template fix_xml_syntax \
  --context-files "MyMod.xml"
```

### Fix TML Syntax Error

```bash
python mod_fixer.py "path/to/transcendence_mod" \
  --profile transcendence \
  --issue "unbalanced parentheses in event handler" \
  --template fix_tml_syntax \
  --context-files "MyMod.xml"
```

### Remove UTF-8 BOM

```bash
python mod_fixer.py "path/to/transcendence_mod" \
  --profile transcendence \
  --issue "UTF-8 BOM detected" \
  --template fix_bom \
  --context-files "MyMod.xml"
```

### Fix Missing Entity Definition

```bash
python mod_fixer.py "path/to/transcendence_mod" \
  --profile transcendence \
  --issue "entity itMyWeapon not defined" \
  --template fix_missing_entity \
  --context-files "MyMod.xml"
```

### Fix Event Handler Issues

```bash
python mod_fixer.py "path/to/transcendence_mod" \
  --profile transcendence \
  --issue "event handler needs block wrapper" \
  --template fix_event_handler \
  --context-files "MyMod.xml"
```

## Transcendence-Specific Templates

### Available Templates

1. **fix_invalid_entity** - Fix invalid entity references by adding DOCTYPE definitions
2. **fix_xml_syntax** - Fix XML syntax errors (unclosed tags, mismatched quotes)
3. **fix_tml_syntax** - Fix TML syntax errors (unbalanced parentheses, event handlers)
4. **fix_bom** - Remove UTF-8 BOM from XML files
5. **fix_entity_encoding** - Fix entity encoding issues (escape < and > in strings)
6. **fix_missing_entity** - Add missing entity definitions to DOCTYPE
7. **fix_event_handler** - Fix event handler issues (block wrappers, parameter checks)
8. **fix_self_closing_tags** - Convert empty tags to self-closing format
9. **fix_doctype_entities** - Fix DOCTYPE entity definitions

## Common Transcendence Issues

### 1. Invalid Entity References

**Error**: `Invalid entity: itMyWeapon`

**Fix**: Add entity definition to DOCTYPE:
```xml
<!ENTITY itMyWeapon "0xE1272001">
```

**Template**: `fix_invalid_entity`

### 2. UTF-8 BOM

**Error**: `<?XML prologue expected` or BOM detected

**Fix**: Remove BOM bytes from file start

**Template**: `fix_bom`

### 3. Content Expected

**Error**: `content expected at line X`

**Causes**:
- Raw `>` character in content
- Unbalanced parentheses in TML
- Missing closing tag

**Template**: `fix_xml_syntax` or `fix_tml_syntax`

### 4. Event Handler Issues

**Error**: Multiple expressions in event handler

**Fix**: Wrap in `(block Nil ...)`:
```xml
<OnDamage>
    (block Nil
        (objIncData gSource "damageCount" 1)
        (objSetData gSource "lastDamage" (unvGetTick))
    )
</OnDamage>
```

**Template**: `fix_event_handler`

### 5. Entity Encoding in Strings

**Error**: `Mismatched quote` in xmlCreate

**Fix**: Escape `<` and `>` as `&lt;` and `&gt;`:
```xml
(xmlCreate "&lt;Item&gt;Weapon&lt;/Item&gt;")
```

**Template**: `fix_entity_encoding`

## Integration with TranscendenceModTools

The mod fixer integrates with `TranscendenceModTools.ps1` for validation:

- Uses `TranscendenceModTools.ps1 -AutoScan` for validation
- Detects common error patterns
- Suggests appropriate templates

## Entity Naming Conventions

The fixer understands Transcendence entity prefixes:

- `it` = item
- `sc` = ship
- `st` = station
- `vt` = virtual
- `rs` = resource
- `ef` = effect
- `sn` = sound
- `sv` = sovereign
- `ds` = dockscreen
- `tb` = table
- `ba` = base

## UNID Ranges

The fixer validates UNID ranges:

- **Mods**: `0xE0000000` - `0xEFFFFFFF` or `0xD0000000` - `0xDFFFFFFF`
- **Base Game**: `0x00000000` - `0x00FFFFFF`
- **Libraries**: `0x00010000` - `0x0001FFFF`
- **DLC**: `0x00800000` - `0x009FFFFF`

## Example Workflow

1. **Scan for issues**:
   ```bash
   pwsh -File TranscendenceModTools.ps1 -AutoScan -Path "path/to/mod"
   ```

2. **Fix specific issue**:
   ```bash
   python mod_fixer.py "path/to/mod" \
     --profile transcendence \
     --issue "Invalid entity: itMyWeapon" \
     --template fix_invalid_entity
   ```

3. **Review and apply**:
   ```bash
   python mod_fixer.py "path/to/mod" \
     --profile transcendence \
     --issue "Invalid entity: itMyWeapon" \
     --template fix_invalid_entity \
     --apply
   ```

## Best Practices

1. **Always dry-run first** - Review fixes before applying
2. **Use specific templates** - Match template to error type
3. **Check validation results** - Review TranscendenceModTools output
4. **Backup mods** - Keep backups before applying fixes
5. **Test in-game** - Verify fixes work in Transcendence

## Troubleshooting

### "Profile not found: transcendence"
- Ensure `mod_fixer_profiles/transcendence.yaml` exists
- Check profile name spelling

### "TranscendenceModTools.ps1 not found"
- Ensure `TranscendenceModTools.ps1` is in Tools directory
- Validation will skip if not found (non-fatal)

### "Ollama not available"
- Check Ollama is running: `curl http://localhost:11434/api/tags`
- Install recommended models: `ollama pull codellama:34b`

## See Also

- [MOD_FIXER_README.md](MOD_FIXER_README.md) - Full documentation
- [MOD_FIXER_QUICK_START.md](MOD_FIXER_QUICK_START.md) - General quick start
- [TranscendenceModTools.ps1](TranscendenceModTools.ps1) - XML checker


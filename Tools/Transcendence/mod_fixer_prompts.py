#!/usr/bin/env python3
"""
Mod Fixer Prompt Templates
Ready-to-use prompt templates for common mod fixing tasks.
"""

from typing import Dict, List, Optional, Any
from pathlib import Path


class PromptTemplates:
    """Collection of prompt templates for mod fixing."""
    
    @staticmethod
    def fix_missing_sprite(
        game: str,
        file_list: List[str],
        missing_sprite: str,
        reference_file: str
    ) -> str:
        """Template for fixing missing sprite references."""
        return f"""[PROFILE: {game}]
CONTEXT:
- file list: {', '.join(file_list)}
- errors: "missing sprite '{missing_sprite}' referenced in {reference_file}"
TASK:
1) Produce a unified diff that adds a safe placeholder sprite metadata file and updates the talent to reference it.
2) Provide a rollback diff.
3) Output validation commands to run.
FORMAT: return only a JSON object with keys: diff, rollback_diff, validation_commands, notes."""

    @staticmethod
    def balance_talent(
        game: str,
        talent_file: str,
        current_params: Dict[str, Any]
    ) -> str:
        """Template for balancing a talent."""
        params_str = '\n'.join([f"  - {k}: {v}" for k, v in current_params.items()])
        return f"""[PROFILE: {game}]
CONTEXT:
- file: {talent_file}
- current parameters:
{params_str}
TASK:
Given talent parameters, compute balanceScore and suggest tuned mana/cooldown values.
Ensure the talent follows game balance guidelines.
FORMAT: return only a JSON object with keys: diff, rollback_diff, validation_commands, notes."""

    @staticmethod
    def fix_syntax_error(
        game: str,
        file_path: str,
        error_message: str,
        error_line: Optional[int] = None
    ) -> str:
        """Template for fixing syntax errors."""
        line_info = f" at line {error_line}" if error_line else ""
        return f"""[PROFILE: {game}]
CONTEXT:
- file: {file_path}
- errors: "{error_message}"{line_info}
TASK:
Fix the syntax error in the provided file.
Return only the corrected code with minimal changes.
FORMAT: return only a JSON object with keys: diff, rollback_diff, validation_commands, notes."""

    @staticmethod
    def fix_missing_locale(
        game: str,
        asset_ids: List[str],
        locale_file: Optional[str] = None
    ) -> str:
        """Template for generating missing locale entries."""
        ids_str = ', '.join(asset_ids)
        return f"""[PROFILE: {game}]
CONTEXT:
- missing locale entries for: {ids_str}
- locale file: {locale_file or 'auto-detect'}
TASK:
Generate missing locale entries for the provided asset IDs.
Use proper translation wrapping and mod compatibility patterns.
FORMAT: return only a JSON object with keys: diff, rollback_diff, validation_commands, notes."""

    @staticmethod
    def fix_manifest(
        game: str,
        mod_path: str,
        current_manifest: Optional[str] = None
    ) -> str:
        """Template for fixing mod manifest."""
        manifest_info = f"\n- current manifest:\n{current_manifest[:500]}" if current_manifest else ""
        return f"""[PROFILE: {game}]
CONTEXT:
- mod path: {mod_path}{manifest_info}
TASK:
Fix or generate mod manifest with proper metadata, version, author, dependencies, and load order.
FORMAT: return only a JSON object with keys: diff, rollback_diff, validation_commands, notes."""

    @staticmethod
    def fix_prefab_refs(
        game: str,
        prefab_file: str,
        broken_refs: List[str]
    ) -> str:
        """Template for fixing broken prefab references (Unity)."""
        refs_str = '\n'.join([f"  - {ref}" for ref in broken_refs])
        return f"""[PROFILE: {game}]
CONTEXT:
- file: {prefab_file}
- broken references:
{refs_str}
TASK:
Detect broken prefab references and generate a patch that rebinds or creates placeholder prefabs.
Include GUID mappings and asset metadata updates.
FORMAT: return only a JSON object with keys: diff, rollback_diff, validation_commands, notes."""

    @staticmethod
    def optimize_textures(
        game: str,
        texture_files: List[str],
        target_size: Optional[str] = None
    ) -> str:
        """Template for optimizing textures (Unity)."""
        files_str = ', '.join(texture_files)
        size_info = f"\n- target size: {target_size}" if target_size else ""
        return f"""[PROFILE: {game}]
CONTEXT:
- files: {files_str}{size_info}
TASK:
Suggest texture compression and mipmap settings for given PNGs.
Provide a scriptable import settings JSON for Unity.
FORMAT: return only a JSON object with keys: diff, rollback_diff, validation_commands, notes."""

    @staticmethod
    def fix_mixin(
        game: str,
        mixin_file: str,
        error_message: str
    ) -> str:
        """Template for fixing mixin errors (Minecraft Fabric)."""
        return f"""[PROFILE: {game}]
CONTEXT:
- file: {mixin_file}
- errors: "{error_message}"
TASK:
Fix mixin configuration errors or broken mixin classes.
Ensure proper annotations and target class references.
FORMAT: return only a JSON object with keys: diff, rollback_diff, validation_commands, notes."""

    @staticmethod
    def fix_fabric_json(
        game: str,
        fabric_json_path: str,
        current_content: Optional[str] = None
    ) -> str:
        """Template for fixing fabric.mod.json."""
        content_info = f"\n- current content:\n{current_content[:500]}" if current_content else ""
        return f"""[PROFILE: {game}]
CONTEXT:
- file: {fabric_json_path}{content_info}
TASK:
Fix or generate fabric.mod.json with proper schema, dependencies, and entrypoints.
FORMAT: return only a JSON object with keys: diff, rollback_diff, validation_commands, notes."""

    @staticmethod
    def fix_compile_errors(
        game: str,
        source_files: List[str],
        error_messages: List[str]
    ) -> str:
        """Template for fixing compilation errors."""
        files_str = ', '.join(source_files)
        errors_str = '\n'.join([f"  - {err}" for err in error_messages])
        return f"""[PROFILE: {game}]
CONTEXT:
- files: {files_str}
- errors:
{errors_str}
TASK:
Fix compilation errors in the provided files.
Ensure compatibility with game API and version.
FORMAT: return only a JSON object with keys: diff, rollback_diff, validation_commands, notes."""

    @staticmethod
    def balance_item(
        game: str,
        item_file: str,
        item_type: str,
        current_stats: Dict[str, Any]
    ) -> str:
        """Template for balancing item properties (Minecraft)."""
        stats_str = '\n'.join([f"  - {k}: {v}" for k, v in current_stats.items()])
        return f"""[PROFILE: {game}]
CONTEXT:
- file: {item_file}
- item type: {item_type}
- current stats:
{stats_str}
TASK:
Suggest balanced item properties (damage, durability, enchantability) for given item class.
FORMAT: return only a JSON object with keys: diff, rollback_diff, validation_commands, notes."""

    # Transcendence-specific templates
    
    @staticmethod
    def fix_invalid_entity(
        game: str,
        xml_file: str,
        missing_entities: List[str],
        unid_range: Optional[str] = None
    ) -> str:
        """Template for fixing invalid entity references (Transcendence)."""
        entities_str = '\n'.join([f"  - {e}" for e in missing_entities])
        unid_info = f"\n- suggested UNID range: {unid_range}" if unid_range else ""
        return f"""[PROFILE: {game}]
CONTEXT:
- file: {xml_file}
- missing entities:
{entities_str}{unid_info}
TASK:
Fix invalid entity references by adding missing entity definitions to DOCTYPE section.
Ensure entity names match references and UNIDs are in valid ranges.
Use proper entity prefix conventions (it=item, sc=ship, st=station, vt=virtual, rs=resource, ef=effect, sn=sound, sv=sovereign, ds=dockscreen, tb=table, ba=base).
FORMAT: return only a JSON object with keys: diff, rollback_diff, validation_commands, notes."""

    @staticmethod
    def fix_xml_syntax(
        game: str,
        xml_file: str,
        error_message: str,
        error_line: Optional[int] = None
    ) -> str:
        """Template for fixing XML syntax errors (Transcendence)."""
        line_info = f" at line {error_line}" if error_line else ""
        return f"""[PROFILE: {game}]
CONTEXT:
- file: {xml_file}
- errors: "{error_message}"{line_info}
TASK:
Fix XML syntax errors (unclosed tags, mismatched quotes, malformed attributes).
Ensure proper UTF-8 encoding declaration (<?xml version="1.0" encoding="utf-8"?>) and no BOM.
FORMAT: return only a JSON object with keys: diff, rollback_diff, validation_commands, notes."""

    @staticmethod
    def fix_tml_syntax(
        game: str,
        xml_file: str,
        error_message: str,
        error_line: Optional[int] = None
    ) -> str:
        """Template for fixing TML syntax errors (Transcendence)."""
        line_info = f" at line {error_line}" if error_line else ""
        return f"""[PROFILE: {game}]
CONTEXT:
- file: {xml_file}
- errors: "{error_message}"{line_info}
TASK:
Fix TML (Transcendence Markup Language) syntax errors in code blocks.
Ensure balanced parentheses, proper block structure, and correct event handler format.
Wrap multiple expressions in event handlers with (block Nil ...).
Check event parameters (aDamageHP, aDamageType) exist before use.
FORMAT: return only a JSON object with keys: diff, rollback_diff, validation_commands, notes."""

    @staticmethod
    def fix_bom(
        game: str,
        xml_file: str
    ) -> str:
        """Template for removing UTF-8 BOM (Transcendence)."""
        return f"""[PROFILE: {game}]
CONTEXT:
- file: {xml_file}
- issue: UTF-8 BOM detected
TASK:
Remove UTF-8 BOM from XML file. Transcendence requires UTF-8 without BOM.
Ensure file starts with <?xml version="1.0" encoding="utf-8"?> without BOM bytes.
FORMAT: return only a JSON object with keys: diff, rollback_diff, validation_commands, notes."""

    @staticmethod
    def fix_entity_encoding(
        game: str,
        xml_file: str,
        problematic_strings: List[str]
    ) -> str:
        """Template for fixing entity encoding issues (Transcendence)."""
        strings_str = '\n'.join([f"  - {s[:100]}" for s in problematic_strings])
        return f"""[PROFILE: {game}]
CONTEXT:
- file: {xml_file}
- problematic strings:
{strings_str}
TASK:
Fix entity encoding issues (escape < and > as &lt; and &gt; in strings).
Especially important for xmlCreate and string literals.
FORMAT: return only a JSON object with keys: diff, rollback_diff, validation_commands, notes."""

    @staticmethod
    def fix_missing_entity(
        game: str,
        xml_file: str,
        entity_name: str,
        suggested_unid: Optional[str] = None
    ) -> str:
        """Template for adding missing entity definition (Transcendence)."""
        unid_info = f"\n- suggested UNID: {suggested_unid}" if suggested_unid else ""
        return f"""[PROFILE: {game}]
CONTEXT:
- file: {xml_file}
- missing entity: {entity_name}{unid_info}
TASK:
Add missing entity definition to DOCTYPE section.
Verify UNID ranges are appropriate (mods: 0xE0000000-0xEFFFFFFF or 0xD0000000-0xDFFFFFFF).
Use proper entity prefix conventions.
FORMAT: return only a JSON object with keys: diff, rollback_diff, validation_commands, notes."""

    @staticmethod
    def fix_event_handler(
        game: str,
        xml_file: str,
        event_name: str,
        error_message: str
    ) -> str:
        """Template for fixing event handler issues (Transcendence)."""
        return f"""[PROFILE: {game}]
CONTEXT:
- file: {xml_file}
- event: {event_name}
- errors: "{error_message}"
TASK:
Fix event handler issues:
- Wrap multiple expressions in (block Nil ...)
- Check event parameters exist before use (aDamageHP, aDamageType, etc.)
- Ensure proper return values (Nil or modified value)
- Add explicit else clauses to if statements when needed
FORMAT: return only a JSON object with keys: diff, rollback_diff, validation_commands, notes."""

    @staticmethod
    def fix_self_closing_tags(
        game: str,
        xml_file: str,
        tag_names: Optional[List[str]] = None
    ) -> str:
        """Template for fixing self-closing tags (Transcendence)."""
        tags_info = f"\n- tags to fix: {', '.join(tag_names)}" if tag_names else ""
        return f"""[PROFILE: {game}]
CONTEXT:
- file: {xml_file}{tags_info}
TASK:
Convert empty tags to self-closing format: <Device/> instead of <Device></Device>
Common tags that should be self-closing: Device, Image, Effect, etc.
FORMAT: return only a JSON object with keys: diff, rollback_diff, validation_commands, notes."""

    @staticmethod
    def fix_doctype_entities(
        game: str,
        xml_file: str,
        issues: List[str]
    ) -> str:
        """Template for fixing DOCTYPE entity definitions (Transcendence)."""
        issues_str = '\n'.join([f"  - {i}" for i in issues])
        return f"""[PROFILE: {game}]
CONTEXT:
- file: {xml_file}
- issues:
{issues_str}
TASK:
Fix DOCTYPE entity definitions:
- Ensure all referenced entities are defined
- Use proper UNID format (0x followed by 8 hex digits)
- Follow entity naming conventions (it=item, sc=ship, st=station, etc.)
- Group entities logically (mod items, base game items, etc.)
FORMAT: return only a JSON object with keys: diff, rollback_diff, validation_commands, notes."""

    @staticmethod
    def fix_api_compatibility(
        game: str,
        mod_path: str,
        api_issues: Dict[str, Any],
        current_api_version: int
    ) -> str:
        """Template for fixing API compatibility issues (Transcendence)."""
        issues_summary = f"""
- Current API version: {current_api_version}
- Total issues: {api_issues.get('total_issues', 0)}
  - Errors: {api_issues.get('errors', 0)}
  - Warnings: {api_issues.get('warnings', 0)}
  - Info: {api_issues.get('infos', 0)}
"""
        
        # Add sample issues
        sample_issues = []
        issues_by_file = api_issues.get('issues_by_file', {})
        for file_path, issues in list(issues_by_file.items())[:10]:
            for issue in issues[:5]:
                line_info = f" (line {issue.get('line', '?')})" if issue.get('line') else ""
                sample_issues.append(f"  - {file_path}{line_info}: [{issue.get('code')}] {issue.get('message')}")
                if issue.get('suggestion'):
                    sample_issues.append(f"    → {issue.get('suggestion')}")
        
        issues_detail = '\n'.join(sample_issues) if sample_issues else "  (no issues found)"
        
        return f"""[PROFILE: {game}]
CONTEXT:
- mod path: {mod_path}
- API compatibility check results:{issues_summary}
- detailed issues:
{issues_detail}
TASK:
Fix API compatibility issues based on current API source:
- Update deprecated functions to current API equivalents
- Replace deprecated tags with current alternatives
- Remove or update deprecated attributes
- Update apiVersion attribute to current API version ({current_api_version})
- Fix function signatures (e.g., Register now requires Registrar parameter)
- Update objDestroy calls to include objSource parameter
- Ensure all used functions/tags/attributes exist in current API
FORMAT: return only a JSON object with keys: diff, rollback_diff, validation_commands, notes."""


# Convenience function to get template by name
def get_template(template_name: str, **kwargs) -> str:
    """Get a prompt template by name with arguments."""
    templates = PromptTemplates()
    method = getattr(templates, template_name, None)
    if not method:
        raise ValueError(f"Template '{template_name}' not found")
    return method(**kwargs)


# Example usage patterns
EXAMPLE_USAGE = {
    "fix_missing_sprite": {
        "description": "Fix missing sprite reference in ToME mod",
        "example": get_template(
            "fix_missing_sprite",
            game="tome",
            file_list=["data/talents/gen_talent_123.lua"],
            missing_sprite="gfx/sprites/gen_proj_123.png",
            reference_file="data/talents/gen_talent_123.lua"
        )
    },
    "balance_talent": {
        "description": "Balance a ToME talent",
        "example": get_template(
            "balance_talent",
            game="tome",
            talent_file="data/talents/gen_talent_123.lua",
            current_params={
                "mana": 20,
                "cooldown": 10,
                "range": 5
            }
        )
    },
    "fix_syntax_error": {
        "description": "Fix Lua syntax error",
        "example": get_template(
            "fix_syntax_error",
            game="tome",
            file_path="data/talents/gen_talent_123.lua",
            error_message="unexpected symbol near 'end'",
            error_line=45
        )
    }
}


if __name__ == '__main__':
    # Print available templates
    print("Available Prompt Templates:")
    print("=" * 60)
    for name, info in EXAMPLE_USAGE.items():
        print(f"\n{name}:")
        print(f"  {info['description']}")
        print(f"  Example:\n{info['example'][:200]}...")


"""
Registry Validation Tool
Validates JSON registry files against their schemas.
"""

import json
import argparse
import sys
import os

def validate_json_schema(data, schema):
    """Simple JSON schema validation (basic checks)"""
    errors = []
    
    # Check required fields from schema
    if 'required' in schema:
        for field in schema['required']:
            if field not in data:
                errors.append(f"Missing required field: {field}")
    
    # Check property types
    if 'properties' in schema:
        for prop, prop_schema in schema['properties'].items():
            if prop in data:
                prop_type = prop_schema.get('type')
                if prop_type:
                    if prop_type == 'string' and not isinstance(data[prop], str):
                        errors.append(f"Field '{prop}' must be a string")
                    elif prop_type == 'number' and not isinstance(data[prop], (int, float)):
                        errors.append(f"Field '{prop}' must be a number")
                    elif prop_type == 'integer' and not isinstance(data[prop], int):
                        errors.append(f"Field '{prop}' must be an integer")
                    elif prop_type == 'boolean' and not isinstance(data[prop], bool):
                        errors.append(f"Field '{prop}' must be a boolean")
                    elif prop_type == 'array' and not isinstance(data[prop], list):
                        errors.append(f"Field '{prop}' must be an array")
                    elif prop_type == 'object' and not isinstance(data[prop], dict):
                        errors.append(f"Field '{prop}' must be an object")
    
    # Check enum values
    if 'properties' in schema:
        for prop, prop_schema in schema['properties'].items():
            if prop in data and 'enum' in prop_schema:
                if data[prop] not in prop_schema['enum']:
                    errors.append(f"Field '{prop}' must be one of: {', '.join(prop_schema['enum'])}")
    
    return errors

def validate_registry_file(registry_path, schema_path=None):
    """Validate a registry JSON file"""
    if not os.path.exists(registry_path):
        print(f"Error: Registry file not found: {registry_path}")
        return False
    
    # Load registry
    try:
        with open(registry_path, 'r') as f:
            registry = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in registry file: {e}")
        return False
    
    # Load schema if provided
    schema = None
    if schema_path and os.path.exists(schema_path):
        try:
            with open(schema_path, 'r') as f:
                schema = json.load(f)
        except json.JSONDecodeError as e:
            print(f"Warning: Invalid JSON in schema file: {e}")
            schema = None
    
    errors = []
    
    # Basic structure validation
    if 'version' not in registry:
        errors.append("Missing 'version' field")
    
    # Validate based on registry type
    if 'projectiles' in registry:
        # Projectile registry
        for idx, projectile in enumerate(registry.get('projectiles', [])):
            if 'id' not in projectile:
                errors.append(f"Projectile {idx}: Missing 'id' field")
            if 'type' not in projectile:
                errors.append(f"Projectile {idx}: Missing 'type' field")
            if 'visual' not in projectile:
                errors.append(f"Projectile {idx}: Missing 'visual' field")
            if 'physics' not in projectile:
                errors.append(f"Projectile {idx}: Missing 'physics' field")
            if 'damage' not in projectile:
                errors.append(f"Projectile {idx}: Missing 'damage' field")
            if 'export' not in projectile:
                errors.append(f"Projectile {idx}: Missing 'export' field")
    
    elif 'shields' in registry or 'armor' in registry:
        # Shield/armor registry
        for idx, shield in enumerate(registry.get('shields', [])):
            if 'id' not in shield:
                errors.append(f"Shield {idx}: Missing 'id' field")
            if 'maxStrength' not in shield:
                errors.append(f"Shield {idx}: Missing 'maxStrength' field")
            if 'visual' not in shield:
                errors.append(f"Shield {idx}: Missing 'visual' field")
            if 'export' not in shield:
                errors.append(f"Shield {idx}: Missing 'export' field")
        
        for idx, armor in enumerate(registry.get('armor', [])):
            if 'id' not in armor:
                errors.append(f"Armor {idx}: Missing 'id' field")
            if 'slots' not in armor:
                errors.append(f"Armor {idx}: Missing 'slots' field")
            if 'export' not in armor:
                errors.append(f"Armor {idx}: Missing 'export' field")
    
    elif 'effects' in registry:
        # FX registry
        for idx, effect in enumerate(registry.get('effects', [])):
            if 'id' not in effect:
                errors.append(f"Effect {idx}: Missing 'id' field")
            if 'type' not in effect:
                errors.append(f"Effect {idx}: Missing 'type' field")
            if 'style' not in effect:
                errors.append(f"Effect {idx}: Missing 'style' field")
            if 'visual' not in effect:
                errors.append(f"Effect {idx}: Missing 'visual' field")
            if 'export' not in effect:
                errors.append(f"Effect {idx}: Missing 'export' field")
    
    elif 'auras' in registry:
        # Aura registry
        for idx, aura in enumerate(registry.get('auras', [])):
            if 'id' not in aura:
                errors.append(f"Aura {idx}: Missing 'id' field")
            if 'type' not in aura:
                errors.append(f"Aura {idx}: Missing 'type' field")
            if 'visual' not in aura:
                errors.append(f"Aura {idx}: Missing 'visual' field")
            if 'particles' not in aura:
                errors.append(f"Aura {idx}: Missing 'particles' field")
            if 'behavior' not in aura:
                errors.append(f"Aura {idx}: Missing 'behavior' field")
            if 'export' not in aura:
                errors.append(f"Aura {idx}: Missing 'export' field")
    
    # Validate with schema if provided
    if schema and 'definitions' in schema:
        # Find matching definition
        if 'projectiles' in registry and 'projectile' in schema['definitions']:
            for projectile in registry.get('projectiles', []):
                schema_errors = validate_json_schema(projectile, schema['definitions']['projectile'])
                errors.extend(schema_errors)
        elif 'shields' in registry and 'shieldProfile' in schema['definitions']:
            for shield in registry.get('shields', []):
                schema_errors = validate_json_schema(shield, schema['definitions']['shieldProfile'])
                errors.extend(schema_errors)
        elif 'effects' in registry and 'fxProfile' in schema['definitions']:
            for effect in registry.get('effects', []):
                schema_errors = validate_json_schema(effect, schema['definitions']['fxProfile'])
                errors.extend(schema_errors)
        elif 'auras' in registry and 'shieldAura' in schema['definitions']:
            for aura in registry.get('auras', []):
                schema_errors = validate_json_schema(aura, schema['definitions']['shieldAura'])
                errors.extend(schema_errors)
    
    # Report errors
    if errors:
        print(f"Validation failed for {registry_path}:")
        for error in errors:
            print(f"  - {error}")
        return False
    else:
        print(f"Validation passed for {registry_path}")
        return True

def main():
    parser = argparse.ArgumentParser(description='Validate registry JSON files')
    parser.add_argument('--registry', required=True, help='Path to registry JSON file')
    parser.add_argument('--schema', help='Path to JSON schema file (optional)')
    
    args = parser.parse_args()
    
    success = validate_registry_file(args.registry, args.schema)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()


"""
Transcendence Weapon Mutation XML Exporter
Exports weapon mutations as Transcendence XML items/devices.
"""

import json
import os
import argparse
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom

def export_mutation_xml(mutation_data):
    """Export weapon mutation as Transcendence XML"""
    root = Element('ItemType')
    
    # Basic attributes
    unid = mutation_data['export']['unid']
    unid_clean = unid.strip('&;')
    root.set('UNID', f"&{unid_clean};")
    root.set('name', mutation_data['name'])
    
    # Item type
    root.set('level', '1')
    root.set('value', str(int(100 * (1 - mutation_data.get('rarity', 0.5)))))  # Higher rarity = lower value
    
    # Description
    description = SubElement(root, 'Description')
    description.text = mutation_data.get('description', '')
    
    # Item properties
    properties = SubElement(root, 'Properties')
    
    # Mutation tier
    tier = mutation_data.get('tier', 'minor')
    properties.set('mutTier', tier)
    properties.set('mutSlotCost', str(mutation_data.get('slotCost', 1)))
    
    if mutation_data.get('instability', 0) > 0:
        properties.set('mutInstability', str(mutation_data['instability']))
    
    # Effects
    effects = mutation_data.get('effects', {})
    if effects:
        effects_elem = SubElement(properties, 'MutEffects')
        
        for key, value in effects.items():
            if isinstance(value, (int, float)):
                effects_elem.set(key, str(value))
            elif isinstance(value, bool):
                effects_elem.set(key, 'true' if value else 'false')
            elif isinstance(value, str):
                effects_elem.set(key, value)
    
    # Tradeoffs
    tradeoffs = mutation_data.get('tradeoffs', {})
    if tradeoffs:
        tradeoffs_elem = SubElement(properties, 'MutTradeoffs')
        
        for key, value in tradeoffs.items():
            if isinstance(value, (int, float)):
                tradeoffs_elem.set(key, str(value))
    
    # Compatibility
    compatibility = mutation_data.get('compatibility', {})
    if compatibility:
        compat_elem = SubElement(properties, 'MutCompatibility')
        
        if 'synergizesWith' in compatibility:
            synergies = ','.join(compatibility['synergizesWith'])
            compat_elem.set('synergizesWith', synergies)
        
        if 'conflictsWith' in compatibility:
            conflicts = ','.join(compatibility['conflictsWith'])
            compat_elem.set('conflictsWith', conflicts)
        
        if 'tags' in compatibility:
            tags = ','.join(compatibility['tags'])
            compat_elem.set('tags', tags)
    
    # Weapon types
    weapon_types = mutation_data.get('weaponTypes', ['all'])
    if weapon_types:
        types_elem = SubElement(properties, 'MutWeaponTypes')
        types_elem.set('types', ','.join(weapon_types))
    
    # Image (optional)
    if 'image' in mutation_data.get('export', {}):
        image = SubElement(root, 'Image')
        image.set('UNID', f"&{unid_clean}Image;")
        image_desc = SubElement(image, 'ImageDesc')
        image_desc.set('bitmap', mutation_data['export']['image'])
    
    return root

def export_mutation_xml_file(mutation_data, output_path):
    """Export mutation XML to file"""
    root = export_mutation_xml(mutation_data)
    
    # Format XML
    xml_str = tostring(root, encoding='unicode')
    dom = minidom.parseString(xml_str)
    pretty_xml = dom.toprettyxml(indent='  ')
    
    # Fix UNID encoding (ensure &UNID; format)
    pretty_xml = pretty_xml.replace('&amp;', '&')
    
    # Write to file
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(pretty_xml)
    
    print(f"Mutation XML exported: {output_path}")

def export_mutation_system_xml(registry_path, output_path):
    """Export complete mutation system XML (all mutations in one file)"""
    with open(registry_path, 'r') as f:
        registry = json.load(f)
    
    root = Element('TranscendenceExtension')
    root.set('UNID', '&extWeaponMutations;')
    root.set('name', 'Weapon Mutation System')
    root.set('version', '1.0.0')
    
    # Add all mutations
    for mutation in registry.get('mutations', []):
        mutation_elem = export_mutation_xml(mutation)
        root.append(mutation_elem)
    
    # Format XML
    xml_str = tostring(root, encoding='unicode')
    dom = minidom.parseString(xml_str)
    pretty_xml = dom.toprettyxml(indent='  ')
    
    # Fix UNID encoding
    pretty_xml = pretty_xml.replace('&amp;', '&')
    
    # Write to file
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(pretty_xml)
    
    print(f"Mutation system XML exported: {output_path}")

def main():
    parser = argparse.ArgumentParser(description='Export weapon mutations as Transcendence XML')
    parser.add_argument('--registry', required=True, help='Path to mutation registry JSON')
    parser.add_argument('--mutation-id', help='Specific mutation ID to export (exports all if not specified)')
    parser.add_argument('--output-dir', required=True, help='Output directory for XML files')
    parser.add_argument('--combined', action='store_true', help='Export all mutations in one file')
    
    args = parser.parse_args()
    
    # Load registry
    with open(args.registry, 'r') as f:
        registry = json.load(f)
    
    if args.combined:
        # Export all in one file
        output_path = os.path.join(args.output_dir, 'weapon_mutations.xml')
        export_mutation_system_xml(args.registry, output_path)
    else:
        # Export individual files
        mutations = registry.get('mutations', [])
        
        if args.mutation_id:
            mutations = [m for m in mutations if m['id'] == args.mutation_id]
        
        for mutation in mutations:
            output_path = os.path.join(args.output_dir, f"{mutation['id']}.xml")
            export_mutation_xml_file(mutation, output_path)
    
    print("Export complete!")

if __name__ == "__main__":
    main()


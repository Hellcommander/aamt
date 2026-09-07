"""
Transcendence Shield and Armor XML Exporter
Exports shield and armor registry entries to Transcendence XML format.
"""

import json
import os
import argparse
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom

def prettify_xml(elem):
    """Return a pretty-printed XML string for the Element"""
    rough_string = tostring(elem, 'unicode')
    reparsed = minidom.parseString(rough_string)
    xml_string = reparsed.toprettyxml(indent="  ")
    # Fix UNID encoding: Transcendence expects & not &amp;
    import re
    xml_string = re.sub(r'(UNID|unid)="&amp;([^"]+)"', r'\1="&\2"', xml_string)
    return xml_string

def export_shield_xml(shield_data):
    """Export a shield to Transcendence XML"""
    root = Element('TranscendenceModule')
    root.set('apiVersion', '57')
    
    # Create ShieldType element (or appropriate Transcendence element)
    shield = SubElement(root, 'ShieldType')
    
    # UNID
    unid = shield_data['export']['unid']
    shield.set('unid', unid)
    
    # Name
    name = shield_data.get('id', 'Unknown').replace('_', ' ').title()
    name_elem = SubElement(shield, 'name')
    name_elem.text = name
    
    # Shield properties
    shield.set('maxHP', str(shield_data['maxStrength']))
    shield.set('rechargeRate', str(shield_data.get('rechargeRate', 6.0)))
    shield.set('rechargeDelay', str(int(shield_data.get('rechargeDelay', 2.5) * 180)))  # Convert to ticks
    
    # Visual
    visual = shield_data.get('visual', {})
    
    # Image
    image_path = shield_data['export']['resourcePaths'].get('sprite', '')
    if image_path:
        image_elem = SubElement(shield, 'image')
        image_elem.text = image_path
    
    # Visual properties
    visual_elem = SubElement(shield, 'visual')
    visual_elem.set('radius', str(visual.get('radius', 1.6)))
    visual_elem.set('thickness', str(visual.get('thickness', 0.08)))
    
    if visual.get('color'):
        visual_elem.set('color', visual['color'])
    if visual.get('glowColor'):
        visual_elem.set('glowColor', visual['glowColor'])
    
    # FX
    fx = shield_data.get('fx', {})
    if fx:
        fx_elem = SubElement(shield, 'fx')
        fx_elem.set('hitFlashDuration', str(fx.get('hitFlashDuration', 0.12)))
        fx_elem.set('hitPulseStrength', str(fx.get('hitPulseStrength', 1.6)))
        
        # Sound
        if 'sound' in fx:
            sound = fx['sound']
            sound_elem = SubElement(fx_elem, 'sound')
            if 'hit' in sound:
                sound_elem.set('hit', sound['hit'])
            if 'break' in sound:
                sound_elem.set('break', sound['break'])
            if 'recharge' in sound:
                sound_elem.set('recharge', sound['recharge'])
    
    # Particle profile reference
    if visual.get('particleProfile'):
        particle_elem = SubElement(shield, 'particleProfile')
        particle_elem.text = visual['particleProfile']
    
    return root

def export_armor_xml(armor_data):
    """Export armor to Transcendence XML"""
    root = Element('TranscendenceModule')
    root.set('apiVersion', '57')
    
    # Create ArmorType element
    armor = SubElement(root, 'ArmorType')
    
    # UNID
    unid = armor_data['export']['unid']
    armor.set('unid', unid)
    
    # Name
    name = armor_data.get('id', 'Unknown').replace('_', ' ').title()
    name_elem = SubElement(armor, 'name')
    name_elem.text = name
    
    # Slots
    slots_elem = SubElement(armor, 'slots')
    for slot_data in armor_data.get('slots', []):
        slot = SubElement(slots_elem, 'slot')
        slot.set('name', slot_data['slot'])
        slot.set('maxHP', str(slot_data['maxHp']))
        
        # Damage reduction
        if 'damageReduction' in slot_data:
            reduction = slot_data['damageReduction']
            for damage_type, reduction_value in reduction.items():
                reduction_elem = SubElement(slot, 'reduction')
                reduction_elem.set('type', damage_type)
                reduction_elem.set('value', str(reduction_value))
    
    # Visual
    visual = armor_data.get('visual', {})
    if visual:
        visual_elem = SubElement(armor, 'visual')
        if visual.get('overlayTexture'):
            visual_elem.set('overlay', visual['overlayTexture'])
        if visual.get('normalMap'):
            visual_elem.set('normalMap', visual['normalMap'])
    
    return root

def export_registry(registry_path, output_dir):
    """Export all shields and armor from registry to XML files"""
    with open(registry_path, 'r') as f:
        registry = json.load(f)
    
    shields = registry.get('shields', [])
    armor = registry.get('armor', [])
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Export shields
    for shield in shields:
        xml_root = export_shield_xml(shield)
        filename = f"{shield['id']}.xml"
        output_path = os.path.join(output_dir, filename)
        
        xml_string = prettify_xml(xml_root)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(xml_string)
        
        print(f"Exported shield: {output_path}")
    
    # Export armor
    for armor_item in armor:
        xml_root = export_armor_xml(armor_item)
        filename = f"{armor_item['id']}.xml"
        output_path = os.path.join(output_dir, filename)
        
        xml_string = prettify_xml(xml_root)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(xml_string)
        
        print(f"Exported armor: {output_path}")

def main():
    parser = argparse.ArgumentParser(description='Export shield/armor registry to Transcendence XML')
    parser.add_argument('--registry', required=True, help='Path to shield/armor registry JSON')
    parser.add_argument('--output-dir', required=True, help='Output directory for XML files')
    
    args = parser.parse_args()
    
    export_registry(args.registry, args.output_dir)
    print("Export complete!")

if __name__ == "__main__":
    main()


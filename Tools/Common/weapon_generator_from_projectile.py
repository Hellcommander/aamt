"""
Weapon Generator from Projectile Registry
Generates complete Transcendence Weapon XML from projectile registry entries.
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
    return reparsed.toprettyxml(indent="  ")

def create_weapon_from_projectile(projectile_data):
    """Create a complete Weapon element from projectile registry data"""
    physics = projectile_data.get('physics', {})
    damage = projectile_data.get('damage', {})
    fx = projectile_data.get('fx', {})
    visual = projectile_data.get('visual', {})
    palette = visual.get('palette', {})
    
    weapon = Element('Weapon')
    
    # Determine weapon type
    projectile_type = projectile_data.get('type', 'Laser')
    if projectile_type == "Missile":
        weapon.set('type', 'missile')
    else:
        weapon.set('type', 'projectile')
    
    # Damage
    damage_str = f"{damage.get('damageType', 'laser')}:{damage.get('baseDamage', 0)}"
    if damage.get('areaRadius', 0) > 0:
        damage_str += f"; area:{damage.get('areaRadius', 0)}"
    weapon.set('damage', damage_str)
    
    # Speed
    if 'speed' in physics:
        if weapon.get('type') == 'missile':
            weapon.set('missileSpeed', str(physics['speed']))
        else:
            weapon.set('speed', str(physics['speed']))
    
    # Lifetime (convert seconds to ticks: 1 second = 180 ticks)
    if 'lifetime' in physics:
        weapon.set('lifetime', str(int(physics['lifetime'] * 180)))
    
    # Fire rate (default based on projectile type)
    if projectile_type == "Laser":
        weapon.set('fireRate', '30')
    elif projectile_type == "Missile":
        weapon.set('fireRate', '60')
    else:
        weapon.set('fireRate', '45')
    
    # Homing
    if physics.get('homingStrength', 0) > 0:
        weapon.set('autoAcquireTarget', 'true')
        if weapon.get('type') == 'missile':
            # Maneuver rate: 0-100, based on turnRate
            maneuver = min(100, int(physics.get('turnRate', 0) / 2))
            weapon.set('maneuverRate', str(maneuver))
    
    # Hit points (for missiles)
    if weapon.get('type') == 'missile':
        weapon.set('hitPoints', str(damage.get('baseDamage', 50) // 10))
    
    # Power use (estimated)
    base_power = damage.get('baseDamage', 0) * 10
    weapon.set('powerUse', str(base_power))
    
    # Sound
    if 'sound' in fx and 'fire' in fx['sound']:
        weapon.set('sound', fx['sound']['fire'])
    
    # Effect
    effect = SubElement(weapon, 'Effect')
    
    if projectile_type == "Laser":
        ray = SubElement(effect, 'Ray')
        ray.set('style', 'smooth')
        ray.set('shape', 'oval')
        sprite_size = visual.get('spriteSize', [32, 32])
        ray.set('width', str(sprite_size[0]))
        ray.set('length', str(sprite_size[1]))
        
        material = visual.get('material', {})
        intensity = int(material.get('glowIntensity', 2.0) * 8)
        ray.set('intensity', str(intensity))
        
        if palette.get('primary'):
            ray.set('primaryColor', palette['primary'])
        if palette.get('secondary'):
            ray.set('secondaryColor', palette['secondary'])
    
    elif projectile_type == "Missile":
        # ParticleComet for exhaust trail
        trail = fx.get('trail', {})
        if trail.get('enabled', False):
            comet = SubElement(effect, 'ParticleComet')
            comet.set('particleCount', str(trail.get('particleCount', 64)))
            sprite_size = visual.get('spriteSize', [48, 48])
            comet.set('width', str(sprite_size[0] // 4))
            comet.set('length', str(trail.get('length', 40)))
            
            if palette.get('trail'):
                comet.set('primaryColor', palette['trail'])
            if palette.get('glow'):
                comet.set('secondaryColor', palette['glow'])
        
        # Ray for missile body
        ray = SubElement(effect, 'Ray')
        ray.set('style', 'smooth')
        ray.set('shape', 'oval')
        sprite_size = visual.get('spriteSize', [48, 48])
        ray.set('width', str(sprite_size[0]))
        ray.set('length', str(sprite_size[1]))
        
        if palette.get('primary'):
            ray.set('primaryColor', palette['primary'])
        if palette.get('secondary'):
            ray.set('secondaryColor', palette['secondary'])
    
    else:
        # Generic projectile
        ray = SubElement(effect, 'Ray')
        ray.set('style', 'smooth')
        ray.set('shape', 'oval')
        sprite_size = visual.get('spriteSize', [32, 32])
        ray.set('width', str(sprite_size[0]))
        ray.set('length', str(sprite_size[1]))
        
        material = visual.get('material', {})
        intensity = int(material.get('glowIntensity', 2.0) * 8)
        ray.set('intensity', str(intensity))
        
        if palette.get('primary'):
            ray.set('primaryColor', palette['primary'])
        if palette.get('secondary'):
            ray.set('secondaryColor', palette['secondary'])
    
    return weapon

def create_item_type_with_weapon(projectile_data, unid_prefix="&pl"):
    """Create a complete ItemType with embedded Weapon"""
    root = Element('ItemType')
    
    # Generate UNID from projectile ID
    projectile_id = projectile_data.get('id', 'unknown')
    unid = f"{unid_prefix}{projectile_id.replace('_', '')};"
    root.set('UNID', unid)
    
    # Name
    name = projectile_id.replace('_', ' ').title()
    root.set('name', name)
    
    # Basic item properties
    root.set('level', '1')
    root.set('value', '100')
    root.set('mass', '1000')
    root.set('frequency', 'common')
    
    # Description
    description = f"Projectile weapon firing {name}"
    root.set('description', description)
    
    # Image (if available)
    image_path = projectile_data.get('export', {}).get('resourcePaths', {}).get('image', '')
    if image_path:
        image = SubElement(root, 'Image')
        image.set('imageID', f"&rsProjectiles;")
        image.set('imageX', '0')
        image.set('imageY', '0')
        image.set('imageWidth', '96')
        image.set('imageHeight', '96')
    
    # Weapon
    weapon = create_weapon_from_projectile(projectile_data)
    root.append(weapon)
    
    return root

def export_registry_to_weapons(registry_path, output_dir, create_items=False):
    """Export all projectiles from registry to Weapon XML files"""
    with open(registry_path, 'r') as f:
        registry = json.load(f)
    
    projectiles = registry.get('projectiles', [])
    
    os.makedirs(output_dir, exist_ok=True)
    
    for projectile in projectiles:
        if create_items:
            xml_root = create_item_type_with_weapon(projectile)
        else:
            xml_root = Element('TranscendenceModule')
            xml_root.set('apiVersion', '57')
            weapon = create_weapon_from_projectile(projectile)
            xml_root.append(weapon)
        
        # Generate filename
        filename = f"{projectile['id']}_weapon.xml"
        output_path = os.path.join(output_dir, filename)
        
        # Write XML
        xml_string = prettify_xml(xml_root)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(xml_string)
        
        print(f"Exported weapon: {output_path}")

def main():
    parser = argparse.ArgumentParser(description='Generate Transcendence Weapon XML from projectile registry')
    parser.add_argument('--registry', required=True, help='Path to projectile registry JSON')
    parser.add_argument('--output-dir', required=True, help='Output directory for XML files')
    parser.add_argument('--create-items', action='store_true', help='Create complete ItemType elements instead of just Weapon')
    
    args = parser.parse_args()
    
    export_registry_to_weapons(args.registry, args.output_dir, args.create_items)
    print("Export complete!")

if __name__ == "__main__":
    main()


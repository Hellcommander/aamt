"""
Transcendence Projectile XML Exporter
Exports projectile registry entries to Transcendence XML format with UNID mapping.
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

def export_projectile_effect(projectile_data):
    """Export projectile as Effect element for use in Weapon definitions"""
    fx = projectile_data.get('fx', {})
    visual = projectile_data.get('visual', {})
    palette = visual.get('palette', {})
    
    effect = Element('Effect')
    
    projectile_type = projectile_data.get('type', 'Laser')
    
    if projectile_type == "Laser":
        # Ray effect for lasers
        ray = SubElement(effect, 'Ray')
        ray.set('style', 'smooth')
        ray.set('shape', 'oval')
        ray.set('width', str(visual.get('spriteSize', [32, 32])[0]))
        ray.set('length', str(visual.get('spriteSize', [32, 32])[1]))
        
        if palette.get('primary'):
            ray.set('primaryColor', palette['primary'])
        if palette.get('secondary'):
            ray.set('secondaryColor', palette['secondary'])
        
        # Intensity based on glow
        material = visual.get('material', {})
        intensity = int(material.get('glowIntensity', 2.0) * 8)
        ray.set('intensity', str(intensity))
    
    elif projectile_type == "Missile":
        # ParticleComet for missiles
        comet = SubElement(effect, 'ParticleComet')
        trail = fx.get('trail', {})
        comet.set('particleCount', str(trail.get('particleCount', 64)))
        comet.set('width', str(visual.get('spriteSize', [48, 48])[0] // 4))
        comet.set('length', str(trail.get('length', 40)))
        
        if palette.get('trail'):
            comet.set('primaryColor', palette['trail'])
        if palette.get('glow'):
            comet.set('secondaryColor', palette['glow'])
    
    else:
        # Generic projectile effect
        ray = SubElement(effect, 'Ray')
        ray.set('style', 'smooth')
        ray.set('shape', 'oval')
        ray.set('width', str(visual.get('spriteSize', [32, 32])[0]))
        ray.set('length', str(visual.get('spriteSize', [32, 32])[1]))
        
        if palette.get('primary'):
            ray.set('primaryColor', palette['primary'])
        if palette.get('secondary'):
            ray.set('secondaryColor', palette['secondary'])
    
    return effect

def export_projectile_xml(projectile_data, template_type):
    """Export a single projectile to Transcendence XML as Weapon-compatible format"""
    root = Element('TranscendenceModule')
    root.set('apiVersion', '57')
    
    # Create a comment block for the projectile
    comment = f"Projectile: {projectile_data.get('id', 'Unknown')}"
    
    # Export as Effect element (for use in Weapon definitions)
    effect = export_projectile_effect(projectile_data)
    root.append(effect)
    
    # Also create a runtime adapter comment with physics mapping
    physics = projectile_data.get('physics', {})
    damage = projectile_data.get('damage', {})
    
    # Create Image element for projectile sprite
    visual = projectile_data.get('visual', {})
    image_path = projectile_data['export']['resourcePaths'].get('image', '')
    
    if image_path:
        image = SubElement(root, 'Image')
        unid = projectile_data['export']['unid']
        image.set('UNID', unid)
        
        image_desc = SubElement(image, 'ImageDesc')
        image_desc.set('bitmap', image_path)
        
        # Frame count and rotations
        frames = visual.get('frames', 1)
        rotations = visual.get('rotations', 1)
        image_desc.set('frameCount', str(frames))
        image_desc.set('rotationCount', str(rotations))
        image_desc.set('ticksPerFrame', '1')
        image_desc.set('bitmask', 'none')
    
    return root
    
    # Physics
    physics = projectile_data.get('physics', {})
    
    # Speed
    if 'speed' in physics:
        speed_elem = SubElement(elem, 'speed')
        speed_elem.text = str(physics['speed'])
    
    # Lifetime
    if 'lifetime' in physics:
        lifetime_elem = SubElement(elem, 'lifetime')
        lifetime_elem.text = str(int(physics['lifetime'] * 180))  # Convert to ticks
    
    # Damage
    damage = projectile_data.get('damage', {})
    
    # Damage type and value
    if 'baseDamage' in damage:
        damage_elem = SubElement(elem, 'damage')
        damage_elem.set('type', damage.get('damageType', 'laser'))
        damage_elem.text = str(damage['baseDamage'])
    
    # Area of effect
    if damage.get('areaRadius', 0) > 0:
        aoe_elem = SubElement(elem, 'areaOfEffect')
        aoe_elem.text = str(damage['areaRadius'])
    
    # Homing
    if physics.get('homingStrength', 0) > 0:
        homing_elem = SubElement(elem, 'homing')
        homing_elem.text = str(int(physics['homingStrength'] * 100))
    
    # Acceleration
    if physics.get('acceleration', 0) > 0:
        accel_elem = SubElement(elem, 'acceleration')
        accel_elem.text = str(physics['acceleration'])
    
    # Turn rate
    if physics.get('turnRate', 0) > 0:
        turn_elem = SubElement(elem, 'turnRate')
        turn_elem.text = str(physics['turnRate'])
    
    # Gravity
    if physics.get('gravity', 0) != 0:
        gravity_elem = SubElement(elem, 'gravity')
        gravity_elem.text = str(physics['gravity'])
    
    # Drag
    if physics.get('drag', 0) > 0:
        drag_elem = SubElement(elem, 'drag')
        drag_elem.text = str(physics['drag'])
    
    # Ricochet
    if physics.get('ricochet', {}).get('enabled', False):
        ricochet_elem = SubElement(elem, 'ricochet')
        ricochet_elem.set('maxBounces', str(physics['ricochet']['maxBounces']))
        ricochet_elem.set('damageRetention', str(physics['ricochet']['damageRetention']))
    
    # Penetration
    if physics.get('penetration', {}).get('enabled', False):
        penetration_elem = SubElement(elem, 'penetration')
        penetration_elem.set('maxTargets', str(physics['penetration']['maxTargets']))
        penetration_elem.set('damageFalloff', str(physics['penetration']['damageFalloff']))
    
    # Status effects
    status_effects = damage.get('statusEffects', [])
    if status_effects:
        effects_elem = SubElement(elem, 'statusEffects')
        for effect in status_effects:
            effect_elem = SubElement(effects_elem, 'effect')
            effect_elem.set('type', effect['type'])
            if 'duration' in effect:
                effect_elem.set('duration', str(int(effect['duration'] * 180)))
            if 'chance' in effect:
                effect_elem.set('chance', str(effect['chance']))
    
    # FX - Trail
    fx = projectile_data.get('fx', {})
    if fx.get('trail', {}).get('enabled', False):
        trail_elem = SubElement(elem, 'trail')
        trail_elem.set('length', str(fx['trail']['length']))
        trail_elem.set('fade', str(fx['trail']['fade']))
        if 'color' in fx['trail']:
            trail_elem.set('color', fx['trail']['color'])
    
    # FX - Light emission
    if fx.get('lightEmission', {}).get('enabled', False):
        light_elem = SubElement(elem, 'lightEmission')
        light_elem.set('intensity', str(fx['lightEmission']['intensity']))
        light_elem.set('radius', str(fx['lightEmission']['radius']))
        if 'color' in fx['lightEmission']:
            light_elem.set('color', fx['lightEmission']['color'])
    
    # FX - Sound
    if 'sound' in fx:
        sound = fx['sound']
        if 'fire' in sound:
            sound_elem = SubElement(elem, 'fireSound')
            sound_elem.text = sound['fire']
        if 'impact' in sound:
            sound_elem = SubElement(elem, 'impactSound')
            sound_elem.text = sound['impact']
    
    return root

def export_registry(registry_path, output_dir):
    """Export all projectiles from registry to XML files"""
    with open(registry_path, 'r') as f:
        registry = json.load(f)
    
    projectiles = registry.get('projectiles', [])
    
    os.makedirs(output_dir, exist_ok=True)
    
    for projectile in projectiles:
        template_type = projectile['export']['xmlTemplate']
        xml_root = export_projectile_xml(projectile, template_type)
        
        # Generate filename from projectile ID
        filename = f"{projectile['id']}.xml"
        output_path = os.path.join(output_dir, filename)
        
        # Write XML
        xml_string = prettify_xml(xml_root)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(xml_string)
        
        print(f"Exported: {output_path}")

def main():
    parser = argparse.ArgumentParser(description='Export projectile registry to Transcendence XML')
    parser.add_argument('--registry', required=True, help='Path to projectile registry JSON')
    parser.add_argument('--output-dir', required=True, help='Output directory for XML files')
    
    args = parser.parse_args()
    
    export_registry(args.registry, args.output_dir)
    print("Export complete!")

if __name__ == "__main__":
    main()



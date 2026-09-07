"""
Transcendence FX XML Exporter
Exports Nova Drift style FX to Transcendence XML format with spritesheet and particle definitions.
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

def export_fx_xml(fx_data):
    """Export an FX to Transcendence XML"""
    root = Element('TranscendenceModule')
    root.set('apiVersion', '57')
    
    # Create Image element for FX spritesheet
    image = SubElement(root, 'Image')
    
    # UNID
    unid = fx_data['export']['unid']
    image.set('UNID', unid)
    
    # Image description
    image_desc = SubElement(image, 'ImageDesc')
    
    # Bitmap path
    sprite_path = fx_data['export']['resourcePaths'].get('sprite', '')
    if sprite_path:
        image_desc.set('bitmap', sprite_path)
    
    # Frame count
    frames = fx_data['visual'].get('frames', 12)
    image_desc.set('frameCount', str(frames))
    
    # Ticks per frame
    transcendence = fx_data['export'].get('transcendence', {})
    ticks_per_frame = transcendence.get('ticksPerFrame', 1)
    image_desc.set('ticksPerFrame', str(ticks_per_frame))
    
    # Rotation count
    rotation_frames = transcendence.get('rotationFrames', 1)
    image_desc.set('rotationCount', str(rotation_frames))
    
    # Bitmask (none for additive effects)
    image_desc.set('bitmask', 'none')
    
    # Create EffectType element if this is an effect
    fx_type = fx_data.get('type', 'fx')
    transcendence_as = transcendence.get('as', 'explosion')
    
    if fx_type in ['explosion', 'impact', 'muzzle', 'trail']:
        effect = SubElement(root, 'EffectType')
        effect.set('unid', unid.replace('fx', 'ef'))
        
        # Name
        name = fx_data.get('id', 'Unknown').replace('_', ' ').title()
        name_elem = SubElement(effect, 'name')
        name_elem.text = name
        
        # Image reference
        image_ref = SubElement(effect, 'image')
        image_ref.text = unid
        
        # Effect properties based on type
        if fx_type == 'explosion':
            effect.set('type', 'explosion')
            # Add explosion-specific properties
            visual = fx_data.get('visual', {})
            if visual.get('distortionStrength', 0) > 0:
                distortion_elem = SubElement(effect, 'distortion')
                distortion_elem.set('strength', str(visual['distortionStrength']))
        
        elif fx_type == 'impact':
            effect.set('type', 'impact')
        
        elif fx_type == 'muzzle':
            effect.set('type', 'muzzle')
        
        elif fx_type == 'trail':
            effect.set('type', 'trail')
    
    return root

def export_particle_xml(particle_profile_path, fx_unid):
    """Export particle profile to Transcendence-compatible format"""
    if not os.path.exists(particle_profile_path):
        return None
    
    with open(particle_profile_path, 'r') as f:
        profile = json.load(f)
    
    root = Element('TranscendenceModule')
    root.set('apiVersion', '57')
    
    # Create particle system definition
    particles = SubElement(root, 'ParticleSystem')
    particles.set('unid', fx_unid.replace('fx', 'ps'))
    
    # Particle definitions
    for particle_data in profile.get('particles', []):
        particle = SubElement(particles, 'Particle')
        particle.set('type', particle_data.get('type', 'burst'))
        particle.set('blend', particle_data.get('blend', 'additive'))
        
        # Position
        pos = particle_data.get('position', [0, 0, 0])
        particle.set('x', str(pos[0]))
        particle.set('y', str(pos[1]))
        particle.set('z', str(pos[2]))
        
        # Velocity
        vel = particle_data.get('velocity', [0, 0, 0])
        particle.set('vx', str(vel[0]))
        particle.set('vy', str(vel[1]))
        particle.set('vz', str(vel[2]))
        
        # Properties
        particle.set('size', str(particle_data.get('size', 0.05)))
        particle.set('lifetime', str(particle_data.get('lifetime', 0.5)))
        
        # Color
        color = particle_data.get('color', [1, 1, 1, 1])
        particle.set('r', str(color[0]))
        particle.set('g', str(color[1]))
        particle.set('b', str(color[2]))
        particle.set('a', str(color[3]))
    
    return root

def export_registry(registry_path, output_dir, particle_profiles_dir=None):
    """Export all FX from registry to XML files"""
    with open(registry_path, 'r') as f:
        registry = json.load(f)
    
    effects = registry.get('effects', [])
    
    os.makedirs(output_dir, exist_ok=True)
    
    for fx in effects:
        # Export FX XML
        xml_root = export_fx_xml(fx)
        filename = f"{fx['id']}.xml"
        output_path = os.path.join(output_dir, filename)
        
        xml_string = prettify_xml(xml_root)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(xml_string)
        
        print(f"Exported FX: {output_path}")
        
        # Export particle XML if particle profile exists
        if particle_profiles_dir:
            particle_profile_path = fx['export']['resourcePaths'].get('particleProfile', '')
            if particle_profile_path:
                full_path = os.path.join(particle_profiles_dir, os.path.basename(particle_profile_path))
                if os.path.exists(full_path):
                    particle_xml = export_particle_xml(full_path, fx['export']['unid'])
                    if particle_xml:
                        particle_filename = f"{fx['id']}_particles.xml"
                        particle_output_path = os.path.join(output_dir, particle_filename)
                        particle_xml_string = prettify_xml(particle_xml)
                        with open(particle_output_path, 'w', encoding='utf-8') as f:
                            f.write(particle_xml_string)
                        print(f"Exported particles: {particle_output_path}")

def main():
    parser = argparse.ArgumentParser(description='Export Nova Drift FX registry to Transcendence XML')
    parser.add_argument('--registry', required=True, help='Path to FX registry JSON')
    parser.add_argument('--output-dir', required=True, help='Output directory for XML files')
    parser.add_argument('--particle-profiles-dir', help='Directory containing particle profile JSON files')
    
    args = parser.parse_args()
    
    export_registry(args.registry, args.output_dir, args.particle_profiles_dir)
    print("Export complete!")

if __name__ == "__main__":
    main()


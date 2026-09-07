"""
Transcendence Shield Aura XML Exporter
Exports shield aura registry entries to Transcendence XML format.
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

def export_aura_xml(aura_data):
    """Export a shield aura to Transcendence XML"""
    root = Element('TranscendenceModule')
    root.set('apiVersion', '57')
    
    # Create AuraType element
    aura = SubElement(root, 'AuraType')
    
    # UNID
    unid = aura_data['export']['unid']
    aura.set('unid', unid)
    
    # Name
    name = aura_data.get('id', 'Unknown').replace('_', ' ').title()
    name_elem = SubElement(aura, 'name')
    name_elem.text = name
    
    # Visual properties
    visual = aura_data.get('visual', {})
    visual_elem = SubElement(aura, 'visual')
    visual_elem.set('radiusMin', str(visual.get('radiusMin', 1.2)))
    visual_elem.set('radiusMax', str(visual.get('radiusMax', 2.4)))
    visual_elem.set('baseColor', visual.get('baseColor', '#66ccff'))
    
    if visual.get('windColor'):
        visual_elem.set('windColor', visual['windColor'])
    
    # Alpha noise properties
    alpha_elem = SubElement(aura, 'alphaNoise')
    alpha_elem.set('speed', str(visual.get('alphaNoiseSpeed', 1.8)))
    alpha_elem.set('scale', str(visual.get('alphaNoiseScale', 3.2)))
    alpha_elem.set('strength', str(visual.get('alphaNoiseStrength', 0.6)))
    
    # Distortion properties
    if visual.get('distortionStrength', 0) > 0:
        distortion_elem = SubElement(aura, 'distortion')
        distortion_elem.set('strength', str(visual['distortionStrength']))
        distortion_elem.set('frequency', str(visual.get('distortionFrequency', 2.6)))
        distortion_elem.set('type', visual.get('distortionType', 'heatHaze'))
    
    # Image
    image_path = aura_data['export']['resourcePaths'].get('auraSprite', '')
    if image_path:
        image_elem = SubElement(aura, 'image')
        image_elem.text = image_path
    
    # Particle properties
    particles = aura_data.get('particles', {})
    if particles:
        particles_elem = SubElement(aura, 'particles')
        particles_elem.set('orbitCount', str(particles.get('orbitCount', 24)))
        particles_elem.set('orbitSpeedMin', str(particles.get('orbitSpeedMin', 0.4)))
        particles_elem.set('orbitSpeedMax', str(particles.get('orbitSpeedMax', 1.6)))
        particles_elem.set('gravityStrength', str(particles.get('gravityStrength', 0.8)))
    
    # Behavior properties
    behavior = aura_data.get('behavior', {})
    if behavior:
        behavior_elem = SubElement(aura, 'behavior')
        behavior_elem.set('projectileInfluence', str(behavior.get('projectileInfluence', True)).lower())
        behavior_elem.set('projectileOrbitTime', str(behavior.get('projectileOrbitTime', 0.3)))
        behavior_elem.set('projectileInfluenceRadius', str(behavior.get('projectileInfluenceRadius', 2.0)))
        behavior_elem.set('projectileGravityStrength', str(behavior.get('projectileGravityStrength', 0.6)))
        behavior_elem.set('shieldScaleWithHP', str(behavior.get('shieldScaleWithHP', True)).lower())
    
    return root

def export_registry(registry_path, output_dir):
    """Export all auras from registry to XML files"""
    with open(registry_path, 'r') as f:
        registry = json.load(f)
    
    auras = registry.get('auras', [])
    
    os.makedirs(output_dir, exist_ok=True)
    
    for aura in auras:
        xml_root = export_aura_xml(aura)
        filename = f"{aura['id']}.xml"
        output_path = os.path.join(output_dir, filename)
        
        xml_string = prettify_xml(xml_root)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(xml_string)
        
        print(f"Exported aura: {output_path}")

def main():
    parser = argparse.ArgumentParser(description='Export shield aura registry to Transcendence XML')
    parser.add_argument('--registry', required=True, help='Path to aura registry JSON')
    parser.add_argument('--output-dir', required=True, help='Output directory for XML files')
    
    args = parser.parse_args()
    
    export_registry(args.registry, args.output_dir)
    print("Export complete!")

if __name__ == "__main__":
    main()


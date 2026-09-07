"""
Transcendence Space Whale Ship XML Exporter
Exports space whale ship definitions as Transcendence XML.
"""

import json
import os
import sys
import argparse
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom

def export_ship_xml(ship_data):
    """Export space whale ship as Transcendence XML"""
    # Validate required fields
    if 'export' not in ship_data:
        raise ValueError("Ship data missing 'export' section")
    if 'unid' not in ship_data['export']:
        raise ValueError("Ship data missing 'export.unid' field")
    if 'id' not in ship_data:
        raise ValueError("Ship data missing 'id' field")
    
    root = Element('ShipClass')
    
    # Basic ship attributes
    unid = ship_data['export']['unid']
    # Remove existing & and ; if present, then add them
    unid_clean = unid.strip('&;')
    if not unid_clean:
        raise ValueError("UNID cannot be empty after cleaning")
    
    root.set('UNID', f"&{unid_clean};")
    root.set('name', ship_data['id'].replace('_', ' ').title())
    
    # Ship stats
    stats = ship_data.get('stats', {})
    
    # Armor and hull
    armor = SubElement(root, 'Armor')
    armor.set('armorID', f"&{unid_clean}Armor;")
    
    # Shields
    shield_config = ship_data.get('systems', {}).get('shield', {})
    if shield_config.get('maxStrength', 0) > 0:
        shields = SubElement(root, 'Shields')
        shields.set('type', 'light')
        shields.set('HP', str(int(shield_config['maxStrength'])))
        shields.set('regen', str(shield_config.get('rechargeRate', 8)))
    
    # Image
    image = SubElement(root, 'Image')
    image.set('UNID', f"&{unid_clean}Image;")
    image_desc = SubElement(image, 'ImageDesc')
    
    resource_paths = ship_data['export'].get('resourcePaths', {})
    image_desc.set('bitmap', resource_paths.get('shipImage', f"Resources/Ships/{ship_data['id']}.png"))
    
    # 120 facings support
    facings = ship_data['export'].get('facings', 120)
    if resource_paths.get('shipMask'):
        image_desc.set('bitmask', resource_paths.get('shipMask'))
    else:
        image_desc.set('bitmask', 'none')
    
    image_desc.set('frameCount', str(facings))
    image_desc.set('ticksPerFrame', '1')
    image_desc.set('rotationCount', str(facings))
    
    # Large image for ship selection
    if 'shipLarge' in resource_paths:
        large_image = SubElement(root, 'Image')
        large_image.set('UNID', f"&{unid_clean}Large;")
        large_image_desc = SubElement(large_image, 'ImageDesc')
        large_image_desc.set('bitmap', resource_paths['shipLarge'])
        large_image_desc.set('bitmask', 'none')
        large_image_desc.set('loadOnUse', 'true')
    
    # Drive
    drive = SubElement(root, 'Drive')
    drive.set('maxSpeed', str(stats.get('baseSpeed', 0.3) * 100))
    drive.set('thrust', str(stats.get('acceleration', 0.1) * 100))
    drive.set('maneuver', str(stats.get('turnRate', 0.15) * 100))
    drive.set('powerUse', '50')
    
    # Cargo
    cargo = SubElement(root, 'CargoSpace')
    cargo.set('capacity', '100')
    
    # Reactor
    reactor = SubElement(root, 'Reactor')
    reactor.set('power', '500')
    
    # Bio-Core system (as device)
    bio_core = ship_data.get('systems', {}).get('bioCore', {})
    if bio_core:
        device = SubElement(root, 'Device')
        device.set('deviceID', f"&{unid_clean}BioCore;")
        device.set('slots', '1')
        device.set('damagedOnLowPower', 'false')
    
    # Orbit Field (as device/effect)
    orbit_field = ship_data.get('systems', {}).get('orbitField', {})
    if orbit_field:
        effect = SubElement(root, 'Effect')
        effect.set('type', 'aura')
        effect.set('UNID', f"&{unid_clean}OrbitField;")
        effect.set('radius', str(orbit_field.get('radius', 2.5)))
    
    # Drone Bay (as device)
    drone_bay = ship_data.get('systems', {}).get('droneBay', {})
    if drone_bay:
        device = SubElement(root, 'Device')
        device.set('deviceID', f"&{unid_clean}DroneBay;")
        device.set('slots', '1')
        device.set('damagedOnLowPower', 'false')
    
    # Abilities (as devices)
    abilities = ship_data.get('systems', {}).get('abilities', {})
    if abilities.get('solarWindToggle'):
        device = SubElement(root, 'Device')
        device.set('deviceID', f"&{unid_clean}SolarWind;")
        device.set('slots', '1')
    
    if abilities.get('songPulse'):
        device = SubElement(root, 'Device')
        device.set('deviceID', f"&{unid_clean}SongPulse;")
        device.set('slots', '1')
    
    if abilities.get('feedingSurge'):
        device = SubElement(root, 'Device')
        device.set('deviceID', f"&{unid_clean}FeedingSurge;")
        device.set('slots', '1')
    
    # Regeneration (as device)
    if stats.get('regenerationRate', 0) > 0:
        device = SubElement(root, 'Device')
        device.set('deviceID', f"&{unid_clean}Regeneration;")
        device.set('slots', '1')
    
    return root

def export_ship_xml_file(ship_data, output_path):
    """Export ship XML to file"""
    try:
        # Validate required data
        if not ship_data:
            raise ValueError("Ship data is empty or None")
        
        if 'id' not in ship_data:
            raise ValueError("Ship data missing required 'id' field")
        
        if 'export' not in ship_data or 'unid' not in ship_data['export']:
            raise ValueError(f"Ship '{ship_data.get('id', 'unknown')}' missing required 'export.unid' field")
        
        root = export_ship_xml(ship_data)
        
        # Format XML
        try:
            xml_str = tostring(root, encoding='unicode')
            dom = minidom.parseString(xml_str)
            pretty_xml = dom.toprettyxml(indent='  ')
        except Exception as e:
            raise ValueError(f"Failed to format XML: {e}")
        
        # Fix UNID encoding (ensure &UNID; format)
        pretty_xml = pretty_xml.replace('&amp;', '&')
        
        # Write to file
        try:
            output_dir = os.path.dirname(output_path)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(pretty_xml)
        except IOError as e:
            raise IOError(f"Failed to write XML file '{output_path}': {e}")
        
        print(f"✓ Ship XML exported: {output_path}")
        
    except Exception as e:
        ship_id = ship_data.get('id', 'unknown') if ship_data else 'unknown'
        print(f"✗ Failed to export ship '{ship_id}': {e}", file=sys.stderr)
        raise

def main():
    try:
        parser = argparse.ArgumentParser(description='Export space whale ships as Transcendence XML')
        parser.add_argument('--registry', required=True, help='Path to ship registry JSON')
        parser.add_argument('--ship-id', help='Specific ship ID to export (exports all if not specified)')
        parser.add_argument('--output-dir', required=True, help='Output directory for XML files')
        
        args = parser.parse_args()
        
        # Validate registry file exists
        if not os.path.exists(args.registry):
            raise FileNotFoundError(f"Registry file not found: {args.registry}")
        
        # Create output directory if it doesn't exist
        os.makedirs(args.output_dir, exist_ok=True)
        
        # Load registry
        try:
            with open(args.registry, 'r', encoding='utf-8') as f:
                registry = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in registry file: {e}")
        except Exception as e:
            raise IOError(f"Failed to read registry file: {e}")
        
        ships = registry.get('ships', [])
        
        if not ships:
            raise ValueError("No ships found in registry")
        
        if args.ship_id:
            ships = [s for s in ships if s.get('id') == args.ship_id]
            if not ships:
                raise ValueError(f"Ship ID '{args.ship_id}' not found in registry")
        
        print(f"Exporting {len(ships)} ship(s) to: {args.output_dir}")
        
        successful = 0
        failed = 0
        
        for ship in ships:
            ship_id = ship.get('id', 'unknown')
            output_path = os.path.join(args.output_dir, f"{ship_id}.xml")
            try:
                export_ship_xml_file(ship, output_path)
                successful += 1
            except Exception as e:
                failed += 1
                print(f"✗ Failed to export ship '{ship_id}': {e}", file=sys.stderr)
                import traceback
                traceback.print_exc()
                # Continue with next ship
                continue
        
        print(f"\n{'='*60}")
        print(f"Export complete! Successful: {successful}, Failed: {failed}")
        if failed > 0:
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\nExport interrupted by user", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"\n✗ Fatal error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()


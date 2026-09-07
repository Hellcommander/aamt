#!/usr/bin/env python3
"""
Create Quick Test Samples
Generates simple test images and XML files for GUI testing
"""

import os
from pathlib import Path
from datetime import datetime

def create_test_samples(output_dir: Path, count: int = 5):
    """Create simple test images and XML files."""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Creating {count} test samples in {output_dir}...")
    
    # Try to use PIL if available
    try:
        from PIL import Image, ImageDraw, ImageFont
        use_pil = True
    except ImportError:
        use_pil = False
        print("PIL not available, creating placeholder files...")
    
    # Create test images
    for i in range(count):
        # Texture image
        texture_name = f"test_texture_{i+1:02d}_diffuse.png"
        texture_path = output_dir / texture_name
        
        if use_pil:
            img = Image.new('RGB', (256, 256), color='#1a2a3a')
            draw = ImageDraw.Draw(img)
            # Draw a simple pattern
            draw.rectangle([50, 50, 200, 200], fill='#66ccff', outline='#88ffff', width=2)
            draw.text((128, 128), f"Texture {i+1}", fill='#ffffff', anchor='mm')
            img.save(texture_path)
            print(f"  Created: {texture_name}")
        else:
            # Create empty file as placeholder
            texture_path.touch()
            print(f"  Created placeholder: {texture_name}")
        
        # Emission texture
        emission_name = f"test_texture_{i+1:02d}_emission.png"
        emission_path = output_dir / emission_name
        
        if use_pil:
            img = Image.new('RGB', (256, 256), color='#000000')
            draw = ImageDraw.Draw(img)
            draw.ellipse([80, 80, 176, 176], fill='#66ccff')
            img.save(emission_path)
            print(f"  Created: {emission_name}")
        else:
            emission_path.touch()
            print(f"  Created placeholder: {emission_name}")
    
    # Create a spritesheet sample
    spritesheet_name = "test_spritesheet_120_facings.png"
    spritesheet_path = output_dir / spritesheet_name
    
    if use_pil:
        # Create a larger image to simulate spritesheet
        img = Image.new('RGB', (512, 512), color='#1a2a3a')
        draw = ImageDraw.Draw(img)
        # Draw a simple ship shape
        points = [(256, 50), (200, 200), (150, 400), (256, 450), (362, 400), (312, 200)]
        draw.polygon(points, fill='#66ccff', outline='#88ffff', width=3)
        draw.text((256, 256), "Spritesheet\nSample", fill='#ffffff', anchor='mm')
        img.save(spritesheet_path)
        print(f"  Created: {spritesheet_name}")
    else:
        spritesheet_path.touch()
        print(f"  Created placeholder: {spritesheet_name}")
    
    # Create a sample XML file
    xml_name = "test_space_whale_ship.xml"
    xml_path = output_dir / xml_name
    
    xml_content = f"""<?xml version="1.0" encoding="utf-8"?>
<TranscendenceExtension>
    <ShipClass UNID="&swTestShip;"
               class="&unidCommonShip;"
               manufacturer="Test Manufacturer">
        <Properties>
            <ShipClass>
                <Name>Test Space Whale Ship</Name>
                <Description>Sample XML file for GUI testing</Description>
            </ShipClass>
        </Properties>
        <Image imageID="&rsSpaceWhaleShip;" imageX="0" imageY="0" imageWidth="256" imageHeight="256" imageFrameCount="120" imageTicksPerFrame="1"/>
    </ShipClass>
</TranscendenceExtension>
<!-- Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} -->
"""
    
    with open(xml_path, 'w', encoding='utf-8') as f:
        f.write(xml_content)
    print(f"  Created: {xml_name}")
    
    print()
    print(f"Created {count*2 + 2} test files:")
    print(f"  - {count} texture images")
    print(f"  - {count} emission images")
    print(f"  - 1 spritesheet")
    print(f"  - 1 XML file")
    print()
    print(f"All files saved to: {output_dir}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Create quick test samples for GUI")
    parser.add_argument("--output", type=Path, default="Output/TestSamples",
                        help="Output directory for test samples")
    parser.add_argument("--count", type=int, default=5,
                        help="Number of texture samples to create")
    args = parser.parse_args()
    
    create_test_samples(args.output, args.count)


#!/usr/bin/env python3
"""
Extract first frame from portal spritesheet for item texture
"""

import sys
from pathlib import Path
from PIL import Image

def extract_item_texture(spritesheet_path: str, output_path: str):
    """Extract first 16x16 frame from portal spritesheet for item texture."""
    try:
        # Open spritesheet (should be 128x16 for 8 frames of 16x16)
        img = Image.open(spritesheet_path)
        
        # Extract first frame (leftmost 16x16)
        item_img = img.crop((0, 0, 16, 16))
        
        # Save as item texture
        output_path_obj = Path(output_path)
        output_path_obj.parent.mkdir(parents=True, exist_ok=True)
        item_img.save(output_path, 'PNG', optimize=False, compress_level=1)
        
        return True
    except Exception as e:
        print(f"Error extracting item texture: {e}", file=sys.stderr)
        return False

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: extract_portal_item.py <spritesheet_path> <output_path>", file=sys.stderr)
        sys.exit(1)
    
    spritesheet_path = sys.argv[1]
    output_path = sys.argv[2]
    
    success = extract_item_texture(spritesheet_path, output_path)
    sys.exit(0 if success else 1)

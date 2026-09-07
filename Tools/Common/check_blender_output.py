"""Check Blender-generated output files"""
from PIL import Image
import os

print("=" * 60)
print("Blender Renderer Test Results")
print("=" * 60)

# Check Nova Burst FX
nova_path = "TestOutput/BlenderFX/nova_burst_01.png"
if os.path.exists(nova_path):
    img = Image.open(nova_path)
    size = os.path.getsize(nova_path)
    print(f"\n[OK] Nova Burst FX Spritesheet:")
    print(f"   Dimensions: {img.size[0]}x{img.size[1]}")
    print(f"   Mode: {img.mode}")
    print(f"   Frames: {img.size[0]//64}")
    print(f"   File Size: {size:,} bytes")
else:
    print(f"\n[FAIL] Nova Burst FX not found at {nova_path}")

# Check Shield Aura
aura_path = "TestOutput/BlenderAura/solar_wind_shield.png"
if os.path.exists(aura_path):
    img = Image.open(aura_path)
    size = os.path.getsize(aura_path)
    print(f"\n[OK] Shield Aura Spritesheet:")
    print(f"   Dimensions: {img.size[0]}x{img.size[1]}")
    print(f"   Mode: {img.mode}")
    print(f"   Frames per HP: {img.size[0]//64}")
    print(f"   HP Levels: {img.size[1]//64}")
    print(f"   File Size: {size:,} bytes")
else:
    print(f"\n[FAIL] Shield Aura not found at {aura_path}")

print("\n" + "=" * 60)


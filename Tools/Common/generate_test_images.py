"""
Generate Test Images for Quality Assessment
Creates placeholder/test images to demonstrate the asset generation pipeline
and validate image quality requirements.
"""

from PIL import Image, ImageDraw, ImageFilter
import os
import json
import math

def create_plasma_bolt_image(size=32, frames=1):
    """Create a test plasma bolt image"""
    images = []
    
    for frame in range(frames):
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Core glow
        center = size // 2
        radius = size // 3
        
        # Outer glow (orange)
        for r in range(radius, 0, -2):
            alpha = int(255 * (1 - r / radius) * 0.6)
            color = (255, 102, 0, alpha)
            draw.ellipse([center - r, center - r, center + r, center + r], fill=color)
        
        # Inner core (yellow)
        core_radius = radius // 2
        draw.ellipse([center - core_radius, center - core_radius, 
                     center + core_radius, center + core_radius], 
                    fill=(255, 215, 0, 255))
        
        # Pulse effect (for animated frames)
        if frames > 1:
            pulse = 0.5 + 0.5 * math.sin(frame * 2 * math.pi / frames)
            pulse_radius = int(core_radius * (0.8 + 0.2 * pulse))
            draw.ellipse([center - pulse_radius, center - pulse_radius,
                         center + pulse_radius, center + pulse_radius],
                        fill=(255, 255, 255, int(255 * pulse * 0.5)))
        
        images.append(img)
    
    return images

def create_homing_missile_image(size=48, frames=4, rotations=8):
    """Create a test homing missile spritesheet"""
    images = []
    
    for frame in range(frames):
        for rotation in range(rotations):
            img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            
            center = size // 2
            angle = rotation * 2 * math.pi / rotations
            
            # Missile body (elongated)
            length = size // 2
            width = size // 6
            
            # Calculate points for rotated rectangle
            cos_a = math.cos(angle)
            sin_a = math.sin(angle)
            
            points = [
                (center + cos_a * length - sin_a * width, center + sin_a * length + cos_a * width),
                (center + cos_a * length + sin_a * width, center + sin_a * length - cos_a * width),
                (center - cos_a * length + sin_a * width, center - sin_a * length - cos_a * width),
                (center - cos_a * length - sin_a * width, center - sin_a * length + cos_a * width)
            ]
            
            # Draw missile body
            draw.polygon(points, fill=(192, 192, 192, 255), outline=(255, 0, 0, 255))
            
            # Exhaust trail (for animation)
            if frame > 0:
                trail_length = frame * 4
                trail_points = [
                    (center - cos_a * length, center - sin_a * length),
                    (center - cos_a * (length + trail_length), center - sin_a * (length + trail_length)),
                    (center - cos_a * (length + trail_length) + sin_a * width, 
                     center - sin_a * (length + trail_length) - cos_a * width),
                    (center - cos_a * length + sin_a * width, center - sin_a * length - cos_a * width)
                ]
                draw.polygon(trail_points, fill=(255, 102, 0, 150))
            
            images.append(img)
    
    return images

def create_shield_aura_image(size=64, frames=12, shield_hp=1.0):
    """Create a test shield aura image with alpha noise effect"""
    images = []
    
    for frame in range(frames):
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        center = size // 2
        radius_min = int(size * 0.2 * shield_hp)
        radius_max = int(size * 0.4 * shield_hp)
        
        # Animated alpha noise effect
        time = frame / frames
        
        # Draw multiple rings with varying alpha
        for ring in range(5):
            r = radius_min + (radius_max - radius_min) * ring / 5
            noise = 0.5 + 0.5 * math.sin(time * 10 + ring * 2)
            alpha = int(100 * noise * shield_hp)
            
            # Base color (cyan)
            color = (102, 204, 255, alpha)
            draw.ellipse([center - r, center - r, center + r, center + r], 
                        outline=color, width=2)
        
        # Core glow
        core_radius = radius_min // 2
        core_alpha = int(150 * shield_hp)
        draw.ellipse([center - core_radius, center - core_radius,
                     center + core_radius, center + core_radius],
                    fill=(170, 255, 255, core_alpha))
        
        images.append(img)
    
    return images

def create_fx_explosion_image(size=64, frames=12):
    """Create a test Nova Drift-style explosion FX"""
    images = []
    
    for frame in range(frames):
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        center = size // 2
        progress = frame / frames
        
        # Core expansion
        if progress < 0.3:
            core_scale = progress / 0.3
        else:
            core_scale = 1.0 - (progress - 0.3) / 0.7
        
        core_radius = int(size * 0.3 * core_scale)
        
        # Core glow (magenta)
        for r in range(core_radius, 0, -1):
            alpha = int(255 * (1 - r / core_radius) * core_scale)
            color = (255, 102, 255, alpha)
            draw.ellipse([center - r, center - r, center + r, center + r], fill=color)
        
        # Shockwave ring
        if progress > 0.1:
            shockwave_progress = (progress - 0.1) / 0.3
            shockwave_radius = int(size * 0.2 + shockwave_progress * size * 0.4)
            shockwave_alpha = int(200 * (1 - shockwave_progress))
            draw.ellipse([center - shockwave_radius, center - shockwave_radius,
                         center + shockwave_radius, center + shockwave_radius],
                        outline=(255, 153, 255, shockwave_alpha), width=2)
        
        # Particle burst (simplified)
        if progress < 0.5:
            particle_count = int(12 * (1 - progress * 2))
            for i in range(particle_count):
                angle = i * 2 * math.pi / 12
                dist = int(size * 0.3 * progress * 2)
                x = int(center + math.cos(angle) * dist)
                y = int(center + math.sin(angle) * dist)
                draw.ellipse([x - 2, y - 2, x + 2, y + 2], fill=(255, 255, 255, 200))
        
        images.append(img)
    
    return images

def create_spritesheet(images, output_path, layout='horizontal'):
    """Create a spritesheet from a list of images"""
    if not images:
        return
    
    img_width, img_height = images[0].size
    
    if layout == 'horizontal':
        spritesheet_width = len(images) * img_width
        spritesheet_height = img_height
    else:  # vertical
        spritesheet_width = img_width
        spritesheet_height = len(images) * img_height
    
    spritesheet = Image.new('RGBA', (spritesheet_width, spritesheet_height), (0, 0, 0, 0))
    
    for idx, img in enumerate(images):
        if layout == 'horizontal':
            x = idx * img_width
            y = 0
        else:
            x = 0
            y = idx * img_height
        spritesheet.paste(img, (x, y), img)
    
    spritesheet.save(output_path, 'PNG')
    print(f"Spritesheet saved: {output_path} ({len(images)} frames)")

def create_mask_from_image(image_path, output_path):
    """Create a black/white mask from an image's alpha channel"""
    img = Image.open(image_path)
    
    # Convert to mask (black background, white where alpha > 0)
    mask = Image.new('L', img.size, 0)
    alpha = img.split()[3] if img.mode == 'RGBA' else img.convert('L')
    
    # Threshold: white where alpha > 128
    mask_data = alpha.point(lambda p: 255 if p > 128 else 0)
    mask.paste(mask_data)
    
    # Save as BMP (Transcendence requirement)
    mask.convert('RGB').save(output_path.replace('.png', '.bmp'), 'BMP')
    print(f"Mask saved: {output_path.replace('.png', '.bmp')}")

def main():
    output_dir = "TestOutput/GeneratedImages"
    os.makedirs(output_dir, exist_ok=True)
    
    print("Generating test images for quality assessment...")
    print("=" * 60)
    
    # 1. Plasma Bolt (single frame)
    print("\n1. Generating Plasma Bolt...")
    plasma_images = create_plasma_bolt_image(size=32, frames=1)
    create_spritesheet(plasma_images, f"{output_dir}/plasma_bolt.png")
    create_mask_from_image(f"{output_dir}/plasma_bolt.png", f"{output_dir}/plasma_bolt_mask.bmp")
    
    # 2. Homing Missile (4 frames x 8 rotations = 32 frames)
    print("\n2. Generating Homing Missile...")
    missile_images = create_homing_missile_image(size=48, frames=4, rotations=8)
    create_spritesheet(missile_images, f"{output_dir}/homing_missile.png")
    
    # 3. Shield Aura (12 frames, multiple HP levels)
    print("\n3. Generating Shield Aura...")
    for hp_level in [0.25, 0.5, 0.75, 1.0]:
        aura_images = create_shield_aura_image(size=64, frames=12, shield_hp=hp_level)
        create_spritesheet(aura_images, f"{output_dir}/solar_wind_shield_hp{int(hp_level*100)}.png")
    
    # 4. FX Explosion (12 frames)
    print("\n4. Generating FX Explosion...")
    explosion_images = create_fx_explosion_image(size=64, frames=12)
    create_spritesheet(explosion_images, f"{output_dir}/nova_burst_01.png")
    
    # 5. Create a larger hero image for ship selection
    print("\n5. Generating Hero Image...")
    hero_img = Image.new('RGBA', (256, 256), (0, 0, 0, 0))
    draw = ImageDraw.Draw(hero_img)
    center = 128
    
    # Large shield aura
    for r in range(100, 0, -5):
        alpha = int(100 * (1 - r / 100))
        color = (102, 204, 255, alpha)
        draw.ellipse([center - r, center - r, center + r, center + r], outline=color, width=3)
    
    hero_img.save(f"{output_dir}/shield_hero_large.png", 'PNG')
    create_mask_from_image(f"{output_dir}/shield_hero_large.png", f"{output_dir}/shield_hero_large_mask.bmp")
    
    print("\n" + "=" * 60)
    print("Image generation complete!")
    print(f"Output directory: {output_dir}")
    print("\nGenerated files:")
    for file in sorted(os.listdir(output_dir)):
        file_path = os.path.join(output_dir, file)
        size = os.path.getsize(file_path)
        print(f"  - {file} ({size:,} bytes)")

if __name__ == "__main__":
    main()


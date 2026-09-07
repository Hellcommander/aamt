"""
Particle Choreography System for Nova Drift Style FX
Generates particle motion patterns: radial burst, spiral, chaotic, orbital
Exports particle profiles for Transcendence integration
"""

import json
import math
import random
from typing import List, Dict, Tuple
from dataclasses import dataclass, asdict

@dataclass
class Particle:
    """Single particle definition"""
    type: str  # burst, core, shockwave
    position: Tuple[float, float, float]
    velocity: Tuple[float, float, float]
    size: float
    lifetime: float
    color: Tuple[float, float, float, float]
    blend: str = "additive"

@dataclass
class ParticleChoreography:
    """Complete particle choreography for an FX"""
    particles: List[Particle]
    motionPattern: str
    totalDuration: float

def generate_radial_burst(particles_config: Dict, frame_time: float = 0.0) -> List[Particle]:
    """Generate radial burst particle pattern"""
    count = particles_config.get('burstCount', 24)
    speed_min = particles_config.get('burstSpeedMin', 0.8)
    speed_max = particles_config.get('burstSpeedMax', 2.4)
    size_min = particles_config.get('sizeMin', 0.02)
    size_max = particles_config.get('sizeMax', 0.08)
    life_min = particles_config.get('lifetimeMin', 0.2)
    life_max = particles_config.get('lifetimeMax', 0.6)
    
    particles = []
    
    for i in range(count):
        # Random angle
        angle = (i / count) * 2 * math.pi
        angle += (random.random() - 0.5) * 0.2  # Add some randomness
        
        # Random speed
        speed = speed_min + (speed_max - speed_min) * random.random()
        
        # Velocity vector
        vx = math.cos(angle) * speed
        vy = math.sin(angle) * speed
        vz = (random.random() - 0.5) * 0.3  # Slight Z variation
        
        # Size and lifetime
        size = size_min + (size_max - size_min) * random.random()
        lifetime = life_min + (life_max - life_min) * random.random()
        
        # Color (white to core color gradient)
        color = (1.0, 1.0, 1.0, 1.0)
        
        particle = Particle(
            type="burst",
            position=(0.0, 0.0, 0.0),
            velocity=(vx, vy, vz),
            size=size,
            lifetime=lifetime,
            color=color,
            blend=particles_config.get('blend', 'additive')
        )
        particles.append(particle)
    
    return particles

def generate_spiral(particles_config: Dict, frame_time: float = 0.0) -> List[Particle]:
    """Generate spiral particle pattern"""
    count = particles_config.get('burstCount', 24)
    speed_min = particles_config.get('burstSpeedMin', 0.8)
    speed_max = particles_config.get('burstSpeedMax', 2.4)
    
    particles = []
    spiral_turns = 2.0
    
    for i in range(count):
        # Spiral angle
        t = i / count
        angle = t * spiral_turns * 2 * math.pi
        
        # Spiral radius increases
        radius = t * 0.5
        
        # Speed increases with radius
        speed = speed_min + (speed_max - speed_min) * t
        
        # Position on spiral
        px = math.cos(angle) * radius
        py = math.sin(angle) * radius
        pz = (random.random() - 0.5) * 0.2
        
        # Velocity tangent to spiral
        vx = -math.sin(angle) * speed + math.cos(angle) * speed * 0.5
        vy = math.cos(angle) * speed + math.sin(angle) * speed * 0.5
        vz = (random.random() - 0.5) * 0.2
        
        size = particles_config.get('sizeMin', 0.02) + (particles_config.get('sizeMax', 0.08) - particles_config.get('sizeMin', 0.02)) * random.random()
        lifetime = particles_config.get('lifetimeMin', 0.2) + (particles_config.get('lifetimeMax', 0.6) - particles_config.get('lifetimeMin', 0.2)) * random.random()
        
        particle = Particle(
            type="burst",
            position=(px, py, pz),
            velocity=(vx, vy, vz),
            size=size,
            lifetime=lifetime,
            color=(1.0, 1.0, 1.0, 1.0),
            blend=particles_config.get('blend', 'additive')
        )
        particles.append(particle)
    
    return particles

def generate_chaotic(particles_config: Dict, frame_time: float = 0.0) -> List[Particle]:
    """Generate chaotic/turbulent particle pattern"""
    count = particles_config.get('burstCount', 24)
    speed_min = particles_config.get('burstSpeedMin', 0.8)
    speed_max = particles_config.get('burstSpeedMax', 2.4)
    
    particles = []
    
    for i in range(count):
        # Random direction
        angle1 = random.random() * 2 * math.pi
        angle2 = random.random() * math.pi
        
        # Random speed
        speed = speed_min + (speed_max - speed_min) * random.random()
        
        # Spherical coordinates to cartesian
        vx = speed * math.sin(angle2) * math.cos(angle1)
        vy = speed * math.sin(angle2) * math.sin(angle1)
        vz = speed * math.cos(angle2)
        
        # Add turbulence
        vx += (random.random() - 0.5) * 0.3
        vy += (random.random() - 0.5) * 0.3
        vz += (random.random() - 0.5) * 0.3
        
        size = particles_config.get('sizeMin', 0.02) + (particles_config.get('sizeMax', 0.08) - particles_config.get('sizeMin', 0.02)) * random.random()
        lifetime = particles_config.get('lifetimeMin', 0.2) + (particles_config.get('lifetimeMax', 0.6) - particles_config.get('lifetimeMin', 0.2)) * random.random()
        
        particle = Particle(
            type="burst",
            position=(0.0, 0.0, 0.0),
            velocity=(vx, vy, vz),
            size=size,
            lifetime=lifetime,
            color=(1.0, 1.0, 1.0, 1.0),
            blend=particles_config.get('blend', 'additive')
        )
        particles.append(particle)
    
    return particles

def generate_core_particles(core_config: Dict) -> List[Particle]:
    """Generate slow-drifting core particles"""
    count = core_config.get('count', 8)
    speed_min = core_config.get('speedMin', 0.1)
    speed_max = core_config.get('speedMax', 0.3)
    life_min = core_config.get('lifeMin', 0.4)
    life_max = core_config.get('lifeMax', 0.8)
    
    particles = []
    
    for i in range(count):
        # Random direction
        angle = random.random() * 2 * math.pi
        speed = speed_min + (speed_max - speed_min) * random.random()
        
        vx = math.cos(angle) * speed
        vy = math.sin(angle) * speed
        vz = (random.random() - 0.5) * 0.1
        
        lifetime = life_min + (life_max - life_min) * random.random()
        
        particle = Particle(
            type="core",
            position=(0.0, 0.0, 0.0),
            velocity=(vx, vy, vz),
            size=0.03,
            lifetime=lifetime,
            color=(1.0, 0.8, 0.6, 1.0),
            blend="additive"
        )
        particles.append(particle)
    
    return particles

def generate_shockwave_particles(shockwave_config: Dict, frame_time: float = 0.0) -> List[Particle]:
    """Generate ring-expanding shockwave particles"""
    count = shockwave_config.get('count', 12)
    ring_radius = shockwave_config.get('ringRadius', 0.5)
    expand_speed = shockwave_config.get('expandSpeed', 1.5)
    
    particles = []
    current_radius = ring_radius + expand_speed * frame_time
    
    for i in range(count):
        angle = (i / count) * 2 * math.pi
        
        # Position on ring
        px = math.cos(angle) * current_radius
        py = math.sin(angle) * current_radius
        pz = 0.0
        
        # Velocity outward
        vx = math.cos(angle) * expand_speed
        vy = math.sin(angle) * expand_speed
        vz = 0.0
        
        particle = Particle(
            type="shockwave",
            position=(px, py, pz),
            velocity=(vx, vy, vz),
            size=0.04,
            lifetime=0.3,
            color=(1.0, 1.0, 1.0, 1.0),
            blend="additive"
        )
        particles.append(particle)
    
    return particles

def create_particle_choreography(fx_data: Dict) -> ParticleChoreography:
    """Create complete particle choreography from FX registry data"""
    particles_config = fx_data.get('particles', {})
    motion_pattern = particles_config.get('motionPattern', 'radialBurst')
    
    all_particles = []
    
    # Generate burst particles based on motion pattern
    if motion_pattern == "radialBurst":
        burst_particles = generate_radial_burst(particles_config)
    elif motion_pattern == "spiral":
        burst_particles = generate_spiral(particles_config)
    elif motion_pattern == "chaotic":
        burst_particles = generate_chaotic(particles_config)
    else:
        burst_particles = generate_radial_burst(particles_config)
    
    all_particles.extend(burst_particles)
    
    # Generate core particles if enabled
    core_config = particles_config.get('coreParticles', {})
    if core_config.get('enabled', True):
        core_particles = generate_core_particles(core_config)
        all_particles.extend(core_particles)
    
    # Generate shockwave particles if enabled
    shockwave_config = particles_config.get('shockwaveParticles', {})
    if shockwave_config.get('enabled', False):
        shockwave_particles = generate_shockwave_particles(shockwave_config)
        all_particles.extend(shockwave_particles)
    
    # Calculate total duration
    timing = fx_data.get('timing', {})
    total_duration = timing.get('totalDuration', None)
    if not total_duration:
        total_duration = timing.get('coreExpandTime', 0.12) + timing.get('fadeOutTime', 0.3)
    
    return ParticleChoreography(
        particles=all_particles,
        motionPattern=motion_pattern,
        totalDuration=total_duration
    )

def export_particle_profile(choreography: ParticleChoreography, output_path: str):
    """Export particle choreography to JSON profile"""
    profile = {
        "version": "1.0.0",
        "motionPattern": choreography.motionPattern,
        "totalDuration": choreography.totalDuration,
        "particles": []
    }
    
    for particle in choreography.particles:
        profile["particles"].append({
            "type": particle.type,
            "position": list(particle.position),
            "velocity": list(particle.velocity),
            "size": particle.size,
            "lifetime": particle.lifetime,
            "color": list(particle.color),
            "blend": particle.blend
        })
    
    with open(output_path, 'w') as f:
        json.dump(profile, f, indent=2)
    
    print(f"Particle profile exported: {output_path}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate particle choreography from FX registry')
    parser.add_argument('--fx-json', required=True, help='Path to FX JSON data (single effect)')
    parser.add_argument('--output', required=True, help='Output path for particle profile JSON')
    
    args = parser.parse_args()
    
    # Load FX data
    with open(args.fx_json, 'r') as f:
        fx_data = json.load(f)
    
    # Create choreography
    choreography = create_particle_choreography(fx_data)
    
    # Export profile
    export_particle_profile(choreography, args.output)


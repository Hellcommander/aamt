"""
Projectile Orbit Behavior System
Implements gravity well behavior for projectiles entering shield aura.
Projectiles get "caught" and orbit the player like a center of gravity.
"""

import math
import random
from dataclasses import dataclass
from typing import Tuple, Optional

@dataclass
class Projectile:
    """Projectile state"""
    position: Tuple[float, float, float]
    velocity: Tuple[float, float, float]
    inOrbit: bool = False
    orbitTime: float = 0.0
    orbitStartTime: float = 0.0

@dataclass
class AuraBehavior:
    """Aura behavior configuration"""
    projectileInfluence: bool = True
    projectileOrbitTime: float = 0.3
    projectileInfluenceRadius: float = 2.0
    projectileGravityStrength: float = 0.6
    projectileTangentialBlend: float = 0.4
    projectileInwardPull: float = 0.2
    orbitSpeedMin: float = 0.4
    orbitSpeedMax: float = 1.6
    shieldHP: float = 1.0  # 0.0-1.0

def perpendicular_2d(vec: Tuple[float, float]) -> Tuple[float, float]:
    """Get perpendicular vector (90 degree rotation)"""
    return (-vec[1], vec[0])

def normalize_2d(vec: Tuple[float, float]) -> Tuple[float, float]:
    """Normalize 2D vector"""
    length = math.sqrt(vec[0]**2 + vec[1]**2)
    if length == 0:
        return (0.0, 0.0)
    return (vec[0] / length, vec[1] / length)

def length_2d(vec: Tuple[float, float]) -> float:
    """Get 2D vector length"""
    return math.sqrt(vec[0]**2 + vec[1]**2)

def lerp(a: float, b: float, t: float) -> float:
    """Linear interpolation"""
    return a + (b - a) * t

def update_projectile_in_aura(
    projectile: Projectile,
    aura_center: Tuple[float, float, float],
    aura_behavior: AuraBehavior,
    dt: float
) -> Projectile:
    """
    Update projectile behavior when inside aura influence radius.
    Implements gravity well: projectiles orbit the center.
    """
    if not aura_behavior.projectileInfluence:
        return projectile
    
    # Calculate 2D position relative to aura center
    dx = projectile.position[0] - aura_center[0]
    dy = projectile.position[1] - aura_center[1]
    dir_2d = (dx, dy)
    dist_2d = length_2d(dir_2d)
    
    # Check if in influence radius
    if dist_2d > aura_behavior.projectileInfluenceRadius:
        # Outside influence - release from orbit
        if projectile.inOrbit:
            projectile.inOrbit = False
            projectile.orbitTime = 0.0
        return projectile
    
    # Enter orbit if not already
    if not projectile.inOrbit:
        projectile.inOrbit = True
        projectile.orbitStartTime = 0.0
        projectile.orbitTime = 0.0
    
    # Update orbit time
    projectile.orbitTime += dt
    
    # Check orbit time limit
    if aura_behavior.projectileOrbitTime > 0.0:
        if projectile.orbitTime > aura_behavior.projectileOrbitTime:
            # Release projectile
            projectile.inOrbit = False
            projectile.orbitTime = 0.0
            return projectile
    
    # Calculate radial and tangential vectors
    if dist_2d > 0.001:  # Avoid division by zero
        radial = normalize_2d(dir_2d)
        tangent = perpendicular_2d(radial)
    else:
        # At center, use random direction
        angle = random.random() * 2 * math.pi
        radial = (math.cos(angle), math.sin(angle))
        tangent = perpendicular_2d(radial)
    
    # Get current orbit speed (scaled with shield HP)
    current_orbit_speed = lerp(
        aura_behavior.orbitSpeedMin,
        aura_behavior.orbitSpeedMax,
        aura_behavior.shieldHP
    )
    
    # Calculate tangential velocity
    tangent_vel = (
        tangent[0] * current_orbit_speed,
        tangent[1] * current_orbit_speed
    )
    
    # Blend projectile velocity toward tangential (orbit)
    blend_factor = aura_behavior.projectileTangentialBlend * aura_behavior.projectileGravityStrength * dt
    blend_factor = min(blend_factor, 1.0)  # Clamp to 1.0
    
    vx = lerp(projectile.velocity[0], tangent_vel[0], blend_factor)
    vy = lerp(projectile.velocity[1], tangent_vel[1], blend_factor)
    vz = projectile.velocity[2]  # Keep Z velocity
    
    # Add inward pull (gravity well effect)
    if dist_2d > 0.001:
        inward_pull = (
            -radial[0] * aura_behavior.projectileInwardPull * dt,
            -radial[1] * aura_behavior.projectileInwardPull * dt
        )
        vx += inward_pull[0]
        vy += inward_pull[1]
    
    # Update projectile velocity
    projectile.velocity = (vx, vy, vz)
    
    return projectile

def calculate_orbit_radius(
    projectile: Projectile,
    aura_center: Tuple[float, float, float]
) -> float:
    """Calculate current orbit radius of projectile"""
    dx = projectile.position[0] - aura_center[0]
    dy = projectile.position[1] - aura_center[1]
    return length_2d((dx, dy))

def calculate_orbit_angle(
    projectile: Projectile,
    aura_center: Tuple[float, float, float]
) -> float:
    """Calculate current orbit angle of projectile"""
    dx = projectile.position[0] - aura_center[0]
    dy = projectile.position[1] - aura_center[1]
    return math.atan2(dy, dx)

# Example usage
if __name__ == "__main__":
    
    # Create test projectile
    proj = Projectile(
        position=(2.0, 0.0, 0.0),
        velocity=(1.0, 0.0, 0.0)  # Moving right
    )
    
    # Create aura behavior
    aura = AuraBehavior(
        projectileInfluence=True,
        projectileOrbitTime=0.3,
        projectileInfluenceRadius=2.0,
        projectileGravityStrength=0.6,
        projectileTangentialBlend=0.4,
        projectileInwardPull=0.2,
        orbitSpeedMin=0.4,
        orbitSpeedMax=1.6,
        shieldHP=1.0
    )
    
    # Aura center (player position)
    center = (0.0, 0.0, 0.0)
    
    # Simulate orbit
    print("Simulating projectile orbit...")
    for i in range(30):
        proj = update_projectile_in_aura(proj, center, aura, 0.016)  # ~60 FPS
        
        # Update position
        proj.position = (
            proj.position[0] + proj.velocity[0] * 0.016,
            proj.position[1] + proj.velocity[1] * 0.016,
            proj.position[2] + proj.velocity[2] * 0.016
        )
        
        radius = calculate_orbit_radius(proj, center)
        angle = calculate_orbit_angle(proj, center)
        
        print(f"Frame {i}: pos=({proj.position[0]:.2f}, {proj.position[1]:.2f}), "
              f"vel=({proj.velocity[0]:.2f}, {proj.velocity[1]:.2f}), "
              f"radius={radius:.2f}, angle={math.degrees(angle):.1f}°, "
              f"inOrbit={proj.inOrbit}")


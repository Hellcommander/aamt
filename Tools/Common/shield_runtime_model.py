"""
Shield Runtime State Model
Implements ShieldInstance with damage handling, recharge logic, and state management.
"""

import json
from dataclasses import dataclass, field
from typing import Optional, List
from enum import Enum
import time

class ShieldState(Enum):
    """Shield runtime states"""
    ACTIVE = "active"
    RECHARGING = "recharging"
    BROKEN = "broken"
    OVERLOADED = "overloaded"

@dataclass
class DamageEvent:
    """Standardized damage event"""
    amount: float
    damageType: str  # kinetic, laser, plasma, ion, thermo, etc.
    position: tuple = (0.0, 0.0, 0.0)  # (x, y, z) hit position
    direction: tuple = (0.0, 0.0, 0.0)  # (x, y, z) hit direction vector
    timestamp: float = field(default_factory=time.time)

@dataclass
class ShieldInstance:
    """Runtime state for a single active shield"""
    profileId: str
    maxStrength: float
    currentStrength: float
    rechargeRate: float  # per second
    rechargeDelay: float  # seconds
    absorptionCurve: str  # linear, exponential, logarithmic, step
    
    # Runtime state
    state: ShieldState = ShieldState.ACTIVE
    isRecharging: bool = False
    lastHitTime: float = 0.0
    visualIntensity: float = 1.0
    hitFlashIntensity: float = 0.0
    hitFlashTime: float = 0.0
    
    # Hit tracking
    hitCount: int = 0
    breakCount: int = 0
    
    def __post_init__(self):
        """Initialize from profile"""
        self.currentStrength = self.maxStrength
        self.lastHitTime = time.time()
    
    def ApplyDamage(self, damageEvent: DamageEvent) -> float:
        """
        Apply damage to shield.
        Returns remaining damage that passes through.
        """
        current_time = time.time()
        self.lastHitTime = current_time
        self.hitCount += 1
        
        # Calculate absorption based on curve
        absorption = self._CalculateAbsorption()
        
        # Apply damage
        damage_absorbed = min(damageEvent.amount * absorption, self.currentStrength)
        self.currentStrength -= damage_absorbed
        
        # Trigger hit flash
        self.hitFlashIntensity = 1.0
        self.hitFlashTime = current_time
        
        # Check for shield break
        if self.currentStrength <= 0:
            self.currentStrength = 0
            self.state = ShieldState.BROKEN
            self.isRecharging = False
            self.breakCount += 1
            self.visualIntensity = 0.0
            return damageEvent.amount - damage_absorbed
        
        # Update visual intensity based on strength
        self.visualIntensity = self.currentStrength / self.maxStrength
        
        # Remaining damage passes through
        return damageEvent.amount - damage_absorbed
    
    def _CalculateAbsorption(self) -> float:
        """Calculate damage absorption based on curve type"""
        strength_ratio = self.currentStrength / self.maxStrength
        
        if self.absorptionCurve == "linear":
            return strength_ratio
        elif self.absorptionCurve == "exponential":
            return strength_ratio ** 2
        elif self.absorptionCurve == "logarithmic":
            return 1.0 - (1.0 - strength_ratio) ** 0.5
        elif self.absorptionCurve == "step":
            return 1.0 if strength_ratio > 0.5 else 0.5
        else:
            return strength_ratio  # Default to linear
    
    def Update(self, dt: float):
        """
        Update shield state (call each frame).
        dt: delta time in seconds
        """
        current_time = time.time()
        
        # Update hit flash
        if self.hitFlashIntensity > 0:
            self.hitFlashIntensity = max(0.0, self.hitFlashIntensity - dt * 8.0)  # Fade out
        
        # Handle recharge
        if self.state == ShieldState.BROKEN:
            # Check if recharge delay has passed
            time_since_hit = current_time - self.lastHitTime
            if time_since_hit >= self.rechargeDelay:
                self.StartRecharge()
        elif self.state == ShieldState.RECHARGING or self.isRecharging:
            # Recharge shield
            if self.currentStrength < self.maxStrength:
                self.currentStrength = min(
                    self.maxStrength,
                    self.currentStrength + self.rechargeRate * dt
                )
                self.visualIntensity = self.currentStrength / self.maxStrength
            else:
                # Fully recharged
                self.currentStrength = self.maxStrength
                self.state = ShieldState.ACTIVE
                self.isRecharging = False
                self.visualIntensity = 1.0
        else:
            # Active state - check if we should start recharging
            time_since_hit = current_time - self.lastHitTime
            if time_since_hit >= self.rechargeDelay and self.currentStrength < self.maxStrength:
                self.StartRecharge()
    
    def StartRecharge(self):
        """Start shield recharge"""
        if self.currentStrength < self.maxStrength:
            self.state = ShieldState.RECHARGING
            self.isRecharging = True
    
    def ForceBreak(self):
        """Force shield to break (for testing or special effects)"""
        self.currentStrength = 0
        self.state = ShieldState.BROKEN
        self.isRecharging = False
        self.visualIntensity = 0.0
        self.breakCount += 1
    
    def GetState(self) -> dict:
        """Get current state as dictionary for UI binding"""
        return {
            "current": self.currentStrength,
            "max": self.maxStrength,
            "percentage": (self.currentStrength / self.maxStrength) * 100.0,
            "state": self.state.value,
            "isRecharging": self.isRecharging,
            "rechargeRate": self.rechargeRate,
            "visualIntensity": self.visualIntensity,
            "hitFlashIntensity": self.hitFlashIntensity
        }

@dataclass
class ArmorSlot:
    """Runtime state for a single armor slot"""
    slot: str  # front, left, right, rear, top, bottom
    maxHp: float
    currentHp: float
    damageReduction: dict = field(default_factory=dict)  # {damageType: reduction}
    
    def __post_init__(self):
        """Initialize armor slot"""
        if self.currentHp == 0:
            self.currentHp = self.maxHp
    
    def ApplyDamage(self, damageEvent: DamageEvent) -> float:
        """
        Apply damage to armor slot.
        Returns remaining damage after reduction.
        """
        reduction = self.damageReduction.get(damageEvent.damageType, 0.0)
        damage_after_reduction = damageEvent.amount * (1.0 - reduction)
        
        damage_taken = min(damage_after_reduction, self.currentHp)
        self.currentHp -= damage_taken
        
        return damage_after_reduction - damage_taken
    
    def GetState(self) -> dict:
        """Get current state as dictionary for UI binding"""
        return {
            "slot": self.slot,
            "hp": self.currentHp,
            "maxHp": self.maxHp,
            "percentage": (self.currentHp / self.maxHp) * 100.0 if self.maxHp > 0 else 0.0
        }

@dataclass
class ArmorInstance:
    """Runtime state for armor plating system"""
    profileId: str
    slots: List[ArmorSlot]
    
    def ApplyDamage(self, damageEvent: DamageEvent, hitDirection: tuple) -> float:
        """
        Apply damage to armor based on hit direction.
        Returns remaining damage after all reductions.
        """
        # Determine which slot was hit based on direction
        slot = self._GetSlotFromDirection(hitDirection)
        
        if slot:
            remaining = slot.ApplyDamage(damageEvent)
            return remaining
        else:
            # No specific slot, apply to all or first available
            if self.slots:
                remaining = self.slots[0].ApplyDamage(damageEvent)
                return remaining
        
        return damageEvent.amount
    
    def _GetSlotFromDirection(self, direction: tuple) -> Optional[ArmorSlot]:
        """Determine armor slot from hit direction vector"""
        if not direction or len(direction) < 2:
            return None
        
        x, y = direction[0], direction[1]
        
        # Simple directional mapping (can be enhanced with 3D)
        if abs(y) > abs(x):
            if y > 0:
                slot_name = "front"
            else:
                slot_name = "rear"
        else:
            if x > 0:
                slot_name = "right"
            else:
                slot_name = "left"
        
        # Find matching slot
        for slot in self.slots:
            if slot.slot == slot_name:
                return slot
        
        return None
    
    def GetState(self) -> dict:
        """Get current state as dictionary for UI binding"""
        return {
            "slots": [slot.GetState() for slot in self.slots]
        }

def CreateShieldInstance(profile: dict) -> ShieldInstance:
    """Create ShieldInstance from profile dictionary"""
    return ShieldInstance(
        profileId=profile['id'],
        maxStrength=profile['maxStrength'],
        currentStrength=profile['maxStrength'],
        rechargeRate=profile.get('rechargeRate', 6.0),
        rechargeDelay=profile.get('rechargeDelay', 2.5),
        absorptionCurve=profile.get('absorptionCurve', 'linear')
    )

def CreateArmorInstance(profile: dict) -> ArmorInstance:
    """Create ArmorInstance from profile dictionary"""
    slots = []
    for slot_data in profile['slots']:
        slot = ArmorSlot(
            slot=slot_data['slot'],
            maxHp=slot_data['maxHp'],
            currentHp=slot_data['maxHp'],
            damageReduction=slot_data.get('damageReduction', {})
        )
        slots.append(slot)
    
    return ArmorInstance(
        profileId=profile['id'],
        slots=slots
    )

# Example usage
if __name__ == "__main__":
    # Load profile
    with open('shield_armor_example.json', 'r') as f:
        registry = json.load(f)
    
    shield_profile = registry['shields'][0]
    shield = CreateShieldInstance(shield_profile)
    
    # Simulate damage
    damage = DamageEvent(amount=30.0, damageType="laser")
    remaining = shield.ApplyDamage(damage)
    print(f"Shield absorbed {30.0 - remaining} damage, {remaining} passed through")
    print(f"Shield state: {shield.GetState()}")
    
    # Update over time
    shield.Update(0.016)  # ~60 FPS
    print(f"After update: {shield.GetState()}")


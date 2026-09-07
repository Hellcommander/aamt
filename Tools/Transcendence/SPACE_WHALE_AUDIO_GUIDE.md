# Space Whale Audio System Guide

## Overview

The Space Whale uses **plausible vacuum communication** through multiple channels: EM signals, plasma oscillations, nebular acoustic waves, and mechanical vibrations. All sounds are rendered as audio for player perception while maintaining scientific plausibility.

## Communication Channels

### 1. EM (Electromagnetic) - Primary Channel
**Range**: Long  
**Fidelity**: High  
**Environment**: Vacuum (always available)

**Use Cases**:
- Idle whale songs
- Alert calls
- Song Pulse ability
- Drone spawn notifications

**Characteristics**:
- Broadband sweeps and harmonics
- Rendered as whale songs in audio UI
- Clear, reliable long-range communication
- Frequency range: 15-70 Hz (rendered as audio)

### 2. Plasma - Secondary Channel
**Range**: Medium  
**Fidelity**: Medium  
**Environment**: Ionized regions (nebula, plasma fields)

**Use Cases**:
- Bio-Core active state
- Orbit Field aura
- Swallow ability
- Feeding Surge
- Mating calls

**Characteristics**:
- Plasma oscillations and magnetosonic waves
- Complex harmonic series
- Visual aurora effects
- Frequency range: 20-80 Hz

### 3. Acoustic - Local Channel
**Range**: Short  
**Fidelity**: High  
**Environment**: Nebular gas/dust clouds only

**Use Cases**:
- Breathing rhythm
- Ramming impacts
- Local communication

**Characteristics**:
- True pressure waves through medium
- Muffled, low-frequency booms
- Heavy low-pass filtering (nebula attenuation)
- Frequency range: 8-15 Hz

### 4. Mechanical - Contact Channel
**Range**: Very Short  
**Fidelity**: High  
**Environment**: Requires contact (hull, debris, tethered objects)

**Use Cases**:
- Ramming impacts
- Hull vibrations
- Nearby ship contact

**Characteristics**:
- Hull vibrations and mechanical coupling
- Tactile rumble (controller/visual)
- High-frequency impact transients
- Frequency range: 60-120 Hz

## Sound Definitions

### Idle Sounds
- **sw_idle_em**: Long-range EM chirps during idle (3-8s, looping)
- **sw_breathing_acoustic**: Nebular breathing rhythm (2-4s, looping, nebula only)

### Ability Sounds
- **sw_song_pulse_em**: High-intensity EM burst for shockwave (0.5-1.5s)
- **sw_swallow_plasma**: Plasma harmonics during ingestion (1-2s)
- **sw_drone_spawn_em**: Quick EM chirp on spawn (0.2-0.5s)

### System Sounds
- **sw_bio_core_active_plasma**: Plasma oscillations when Bio-Core active (2-5s, looping)
- **sw_orbit_field_plasma**: Magnetosonic waves from Orbit Field (4-10s, looping)
- **sw_regeneration_plasma**: Subtle plasma flow during healing (3-6s, looping)

### Impact Sounds
- **sw_ramming_mechanical**: Hull vibration on ram impact (0.3-1.0s)

### Alert/Special Sounds
- **sw_alert_em**: High-frequency EM alert for threats (1-2s)
- **sw_mating_call_plasma**: Complex plasma harmonics for mating (5-12s)

## Procedural Generation

### Deterministic Seeds
All whale songs use **deterministic seeds** for consistency:
- Seed source: Ship ID or timestamp
- Same seed = same song pattern
- Enables replay and recognition

### Generation Parameters
- **Base Frequency**: 15-60 Hz (configurable per sound)
- **Harmonic Series**: [1, 2, 3, 5, 7] (natural harmonics)
- **Sweep Patterns**: slow, rapid, oscillating, spiral, complex
- **Duration Range**: 2-10 seconds (configurable)
- **Intensity Variation**: ±20% (natural variation)

## Integration with Game Systems

### Bio-Core System
- **Active State**: Plasma oscillations scale with energy level
- **Low Energy**: Quieter, slower oscillations
- **High Energy**: Louder, faster oscillations

### Orbit Field
- **Active**: Continuous plasma waves
- **Strength**: Scales with field strength
- **Range**: 500 unit radius

### Song Pulse
- **Trigger**: On ability activation
- **Channel**: EM burst
- **Effect**: Shockwave audio expansion

### Swallow System
- **Windup**: Subtle plasma build-up
- **Ingestion**: Imploding plasma harmonics
- **Digestion**: Gentle plasma flow

### Regeneration
- **Active**: Subtle plasma flow on damaged segments
- **Intensity**: Scales with regen rate
- **Duration**: While healing

## Decoding System

### Player Tools

#### EM Sensor (Device)
- **Function**: Decode EM signals into text messages
- **Output**: Quest hints, warnings, whale communication
- **Range**: Long (matches EM range)

#### Plasma Analyzer (Device)
- **Function**: Analyze plasma harmonics for patterns
- **Output**: Quest hints, territorial warnings, mating calls
- **Range**: Medium (matches plasma range)

### Signal Patterns
- **Idle Pattern**: Slow, rhythmic (safe)
- **Alert Pattern**: Rapid, high-frequency (threat)
- **Mating Pattern**: Complex harmonics (special event)
- **Feeding Pattern**: Imploding harmonics (consumption)

## Implementation in Transcendence

### XML Integration

```xml
<Sound UNID="&sfxSpaceWhaleIdleEM;">
    <SoundDesc
        file="Resources/Audio/sw_idle_em.ogg"
        volume="40"
        loop="true"
        spatial="true"
        attenuation="inverse_square"
    />
</Sound>

<Sound UNID="&sfxSpaceWhaleSongPulseEM;">
    <SoundDesc
        file="Resources/Audio/sw_song_pulse_em.ogg"
        volume="90"
        loop="false"
        spatial="true"
        attenuation="inverse_square"
        doppler="true"
    />
</Sound>
```

### Script Integration

```lisp
; Play idle EM sound
(objPlaySound gSource &sfxSpaceWhaleIdleEM;)

; Play Song Pulse with shockwave effect
(objPlaySound gSource &sfxSpaceWhaleSongPulseEM;)
(sysCreateEffect &efShockwave; gSource (objGetPos gSource))

; Play plasma sound if in ionized medium
(if (swIsInIonizedMedium gSource)
    (objPlaySound gSource &sfxSpaceWhaleBioCorePlasma;)
)
```

## Environment Detection

### Vacuum (Default)
- **Available Channels**: EM, Mechanical (contact only)
- **Primary**: EM signals
- **Rendering**: Clear whale songs

### Nebula (Gas/Dust)
- **Available Channels**: All (EM, Plasma, Acoustic, Mechanical)
- **Primary**: Acoustic for local, EM for long-range
- **Rendering**: Muffled acoustic + clear EM

### Ionized Region (Plasma Field)
- **Available Channels**: EM, Plasma, Mechanical
- **Primary**: Plasma oscillations
- **Rendering**: Harmonic aurora with audio

## Audio Settings

### Format
- **Container**: OGG Vorbis
- **Sample Rate**: 44.1 kHz
- **Bit Depth**: 16-bit
- **Channels**: Stereo
- **Compression**: High quality

### Spatial Audio
- **3D Positioning**: Enabled
- **Attenuation**: Inverse square (EM), Linear (Plasma), Exponential (Acoustic)
- **Doppler**: Enabled for moving sources
- **Reverb**: Channel-specific (space_echo, plasma_chamber, nebula_muffled)

## Best Practices

### Realism vs. Clarity
- **Always provide audio mapping**: Even EM signals render as sound
- **Visual indicators**: Plasma sounds show aurora effects
- **Tactile feedback**: Mechanical sounds trigger rumble
- **Clear telegraphing**: Different patterns for different events

### Performance
- **Looping sounds**: Use for ambient/continuous effects
- **One-shot sounds**: Use for events/abilities
- **Spatial culling**: Disable sounds beyond range
- **Channel prioritization**: EM > Plasma > Acoustic > Mechanical

### Player Experience
- **Volume balance**: EM (40%), Plasma (50%), Acoustic (30%), Mechanical (80%)
- **Frequency range**: Keep in audible range (20-20kHz) even if "rendered" from lower frequencies
- **Pattern recognition**: Consistent patterns help players learn whale behavior
- **Quest integration**: Use decoding tools for gameplay hooks

## Files

- `space_whale_audio_registry.json` - Audio configuration
- `space_whale_audio_generator.py` - Procedural audio generator
- `SpaceWhaleAudioGenerator.ps1` - Generator script
- `SPACE_WHALE_AUDIO_GUIDE.md` - This guide

## Next Steps

1. **Generate audio files** using `SpaceWhaleAudioGenerator.ps1`
2. **Integrate sounds** into `SpaceWhaleShip.xml`
3. **Add environment detection** for channel selection
4. **Implement decoding tools** (EM Sensor, Plasma Analyzer)
5. **Test in-game** and tune volumes/patterns

## Conclusion

The Space Whale audio system provides **plausible vacuum communication** while maintaining **clear player feedback**. Multiple channels allow for environmental variation and gameplay depth, while procedural generation ensures consistent, recognizable whale songs.


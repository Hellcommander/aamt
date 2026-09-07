import numpy as np
import wave
import sys
import json
import os
from scipy import signal
import soundfile as sf

def generate_sound(sound_name, sound_type, description, duration, frequency, volume, output_path, format_type):
    sample_rate = 44100
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    
    # Generate base tone
    if 'low' in description.lower() or 'deep' in description.lower() or 'roar' in description.lower():
        freq = frequency * 0.5
    elif 'high' in description.lower() or 'sharp' in description.lower():
        freq = frequency * 2.0
    else:
        freq = frequency
    
    # Generate sound based on type
    if sound_type == 'Impact' or 'impact' in description.lower():
        # Sharp attack with quick decay
        wave_data = np.sin(2 * np.pi * freq * t) * np.exp(-t * 10)
        # Add noise for impact
        noise = np.random.normal(0, 0.1, len(t)) * np.exp(-t * 15)
        wave_data = wave_data + noise
    elif sound_type == 'Charge' or 'charge' in description.lower() or 'building' in description.lower():
        # Rising pitch
        freq_sweep = np.linspace(freq * 0.5, freq * 1.5, len(t))
        wave_data = np.sin(2 * np.pi * freq_sweep * t) * (1 - np.exp(-t * 2))
    elif sound_type == 'Magic' or 'magic' in description.lower() or 'ethereal' in description.lower():
        # Multiple harmonics with modulation
        wave_data = (np.sin(2 * np.pi * freq * t) + 
                    0.5 * np.sin(2 * np.pi * freq * 2 * t) +
                    0.3 * np.sin(2 * np.pi * freq * 3 * t)) * np.sin(2 * np.pi * 2 * t)
    elif sound_type == 'Mechanical' or 'mechanical' in description.lower():
        # Square wave with harmonics
        wave_data = signal.square(2 * np.pi * freq * t, duty=0.5) * 0.5
        wave_data += 0.3 * np.sin(2 * np.pi * freq * 2 * t)
    elif sound_type == 'Roar' or 'roar' in description.lower():
        # Low frequency with noise
        wave_data = np.sin(2 * np.pi * freq * 0.3 * t) * (1 - np.exp(-t * 0.5))
        noise = np.random.normal(0, 0.2, len(t)) * np.exp(-t * 1)
        wave_data = wave_data + noise
    elif sound_type == 'Whoosh' or 'whoosh' in description.lower():
        # White noise with frequency sweep
        noise = np.random.normal(0, 0.3, len(t))
        freq_sweep = np.linspace(freq * 2, freq * 0.5, len(t))
        wave_data = noise * np.sin(2 * np.pi * freq_sweep * t)
    else:
        # Default: simple sine wave with envelope
        wave_data = np.sin(2 * np.pi * freq * t) * (1 - np.exp(-t * 2)) * np.exp(-t * 1)
    
    # Apply volume
    wave_data = wave_data * volume
    
    # Normalize
    max_val = np.max(np.abs(wave_data))
    if max_val > 0:
        wave_data = wave_data / max_val * 0.95
    
    # Convert to 16-bit PCM
    wave_data = (wave_data * 32767).astype(np.int16)
    
    # Save as WAV or OGG
    if format_type == 'wav':
        with wave.open(output_path, 'wb') as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(wave_data.tobytes())
    else:  # OGG
        try:
            # Convert to float32 for soundfile
            wave_data_float = wave_data.astype(np.float32) / 32767.0
            sf.write(output_path, wave_data_float, sample_rate)
        except:
            # Fallback to WAV if OGG not supported
            with wave.open(output_path.replace('.ogg', '.wav'), 'wb') as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(wave_data.tobytes())
            print(f"Note: OGG not available, saved as WAV instead")

if __name__ == '__main__':
    if len(sys.argv) < 9:
        print("Usage: generate_sound.py <name> <type> <description> <duration> <frequency> <volume> <output> <format>")
        sys.exit(1)
    
    generate_sound(
        sys.argv[1], sys.argv[2], sys.argv[3],
        float(sys.argv[4]), int(sys.argv[5]), float(sys.argv[6]),
        sys.argv[7], sys.argv[8]
    )

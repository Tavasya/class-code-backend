import numpy as np
import wave
import struct

# Create a simple test tone for pronunciation testing
duration = 2.0  # seconds
sample_rate = 16000  # 16kHz as required by Azure Speech
frequency = 440  # A4 note

# Generate a simple sine wave
t = np.linspace(0, duration, int(sample_rate * duration), False)
wave_data = np.sin(frequency * 2 * np.pi * t)

# Add some variation to make it more speech-like
wave_data = wave_data * 0.3 + np.sin(frequency * 1.5 * 2 * np.pi * t) * 0.2

# Convert to 16-bit integers
wave_data = (wave_data * 32767).astype(np.int16)

# Save as WAV file
with wave.open('test_audio.wav', 'w') as wav_file:
    wav_file.setnchannels(1)  # mono
    wav_file.setsampwidth(2)  # 16-bit
    wav_file.setframerate(sample_rate)
    wav_file.writeframes(wave_data.tobytes())

print('✅ Created test_audio.wav for pronunciation testing') 
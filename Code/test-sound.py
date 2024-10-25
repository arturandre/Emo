import numpy as np
import sounddevice as sd

# Set the sample rate and duration
sample_rate = 48000  # Matches the pcm5102A's supported rate
duration = 5  # Duration of the tone in seconds
frequency = 440  # Frequency of the tone (A4)

# Generate a stereo signal with a left-right alternating tone
t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
left_channel = 0.5 * np.sin(2 * np.pi * frequency * t)  # Tone in the left channel
right_channel = np.zeros_like(left_channel)  # Silence in the right channel

# Interleave left and right channels
stereo_signal = np.vstack([left_channel, right_channel]).T

# Play alternating tone in the left channel for the specified duration
print("Playing tone in the left channel")
sd.play(stereo_signal, samplerate=sample_rate)
sd.wait()

# Now switch to the right channel
left_channel = np.zeros_like(t)  # Silence in the left channel
right_channel = 0.5 * np.sin(2 * np.pi * frequency * t)  # Tone in the right channel

stereo_signal = np.vstack([left_channel, right_channel]).T

print("Playing tone in the right channel")
sd.play(stereo_signal, samplerate=sample_rate)
sd.wait()

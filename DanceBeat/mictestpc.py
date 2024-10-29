print("Here")
import sounddevice as sd
import soundfile as sf
import numpy as np

# Parameters
SAMPLE_RATE = 44100  # Sampling rate (44.1 kHz is CD quality)
CHANNELS = 1  # Mono recording
DURATION = 10  # Duration of the recording in seconds
OUTPUT_FILE = "output.wav"  # Output file name

def record_audio(filename, duration, samplerate, channels):
    print("Recording...")
    # Record audio from the microphone
    audio_data = sd.rec(int(duration * samplerate), samplerate=samplerate, channels=channels, dtype='float32')
    
    # Wait until the recording is finished
    sd.wait()

    print("Recording finished, saving the file...")
    # Save the audio data as a .wav file
    sf.write(filename, audio_data, samplerate)
    print(f"File saved as {filename}")

print("here?")
record_audio(OUTPUT_FILE, DURATION, SAMPLE_RATE, CHANNELS)

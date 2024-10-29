import sounddevice as sd
import numpy as np
from scipy.signal import find_peaks
from collections import deque
import time

# Parameters
SAMPLE_RATE = 44100  # Sampling rate for the microphone
WINDOW_DURATION = 5  # Duration of the analysis window in seconds
DETECTION_THRESHOLD = 1.5  # Threshold multiplier for peak detection
BUFFER_SIZE = int(SAMPLE_RATE * WINDOW_DURATION)  # Number of samples in a 5-second window

# Data structure to store beats detected over time
beat_times = deque(maxlen=30)  # Keep last 30 beat times to calculate average BPM

def calculate_bpm(beat_intervals):
    """Calculate BPM from a list of beat intervals (in seconds)."""
    if len(beat_intervals) < 2:
        return 0
    avg_interval = np.mean(beat_intervals)
    bpm = 60 / avg_interval  # Convert interval to BPM
    return int(bpm)

def process_audio(indata, frames, time, status):
    """Callback function to process audio in real time."""
    # Convert audio to mono and analyze for peaks
    audio_data = indata[:, 0]  # Use the first channel (mono)
    
    # Normalize audio to prevent issues with quiet sounds
    audio_data = audio_data / np.max(np.abs(audio_data))
    
    # Use a low-pass filter by downsampling to focus on beats
    low_freq_audio = audio_data[::10]  # Downsample by factor of 10
    
    # Detect peaks in the audio signal
    peaks, _ = find_peaks(low_freq_audio, height=np.mean(low_freq_audio) * DETECTION_THRESHOLD, distance=1000)
    
    # Calculate beat intervals and update BPM
    current_time = time.inputBufferAdcTime  # Get current time in seconds
    for peak in peaks:
        beat_times.append(current_time + peak / SAMPLE_RATE)  # Append peak time in seconds
    
    # Calculate intervals between beats and estimate BPM
    beat_intervals = np.diff(beat_times)
    bpm = calculate_bpm(beat_intervals)
    print(f"Estimated BPM: {bpm}")

# Main program to start recording from the microphone and estimate BPM
print("Starting BPM estimation... Speak into the microphone or play some music.")
with sd.InputStream(callback=process_audio, channels=1, samplerate=SAMPLE_RATE, blocksize=BUFFER_SIZE):
    while True:
        time.sleep(1)  # Keep the main thread alive

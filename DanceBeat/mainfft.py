import sounddevice as sd
import soundfile as sf
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import find_peaks, butter, lfilter
from scipy.ndimage import gaussian_filter1d
from collections import deque
import time

# Parameters
SAMPLE_RATE = 44100  # Sampling rate for the microphone
WINDOW_DURATION = 5  # Duration of the analysis window in seconds
BUFFER_SIZE = int(SAMPLE_RATE * WINDOW_DURATION)  # Number of samples in a 5-second window
LOW_FREQ_LIMIT = 20  # Low-frequency limit in Hz
HIGH_FREQ_LIMIT = 150  # High-frequency limit in Hz
MIN_BEAT_INTERVAL = 0.3  # Minimum interval (seconds) between two consecutive beats to avoid duplicates
AMPLIFICATION_FACTOR = 10  # Amplify the signal by this factor
HIGH_PASS_CUTOFF = 50  # High-pass filter cutoff frequency in Hz
NOISE_THRESHOLD = 0.02  # Noise threshold: ignore signals below this level
GAUSSIAN_SIGMA = 1  # Sigma for Gaussian smoothing
OUTPUT_FILE = "recorded_audio.wav"  # File where the audio is saved

# Data structure to store beat times
beat_times = deque(maxlen=30)  # Keep last 30 beat times for BPM calculation

# To store all the recorded audio data for saving later
audio_buffer = []

# Record the start time
start_time = time.time()

def calculate_bpm(beat_intervals):
    """Calculate BPM from a list of beat intervals (in seconds)."""
    if len(beat_intervals) < 2:
        return 0
    avg_interval = np.mean(beat_intervals)  # Average interval in seconds
    
    if avg_interval == 0:  # Avoid division by zero
        return 0
    
    bpm = 60 / avg_interval  # Convert interval to BPM
    return int(bpm)

def butter_highpass(cutoff, fs, order=5):
    """Create a high-pass filter."""
    nyq = 0.5 * fs  # Nyquist frequency
    normal_cutoff = cutoff / nyq
    b, a = butter(order, normal_cutoff, btype='high', analog=False)
    return b, a

def apply_highpass_filter(data, cutoff, fs, order=5):
    """Apply a high-pass filter to the data."""
    b, a = butter_highpass(cutoff, fs, order=order)
    y = lfilter(b, a, data)
    return y

def process_audio(indata, frames, time_info, status):
    """Callback function to process audio in real-time using FFT."""
    global audio_buffer
    # Flatten to mono by taking only the first channel
    audio_data = indata[:, 0]
    
    # Append audio data to the buffer for saving later
    audio_buffer.append(audio_data.copy())

    # Apply Gaussian smoothing
    audio_data = gaussian_filter1d(audio_data, sigma=GAUSSIAN_SIGMA)

    # Apply amplification to the audio signal
    audio_data *= AMPLIFICATION_FACTOR

    # Apply high-pass filter to remove low-frequency noise
    audio_data = apply_highpass_filter(audio_data, HIGH_PASS_CUTOFF, SAMPLE_RATE)

    # Apply noise gate: ignore signals below the noise threshold
    if np.max(np.abs(audio_data)) < NOISE_THRESHOLD:
        print("Low noise level detected, ignoring...")
        return  # Ignore this frame if the signal is too weak

    # Normalize audio to a range of -1.0 to 1.0
    audio_data = audio_data / np.max(np.abs(audio_data) + 1e-7)  # Avoid division by zero

    # Apply FFT to the audio window
    fft_result = np.fft.rfft(audio_data)
    fft_freq = np.fft.rfftfreq(len(audio_data), 1 / SAMPLE_RATE)

    # Focus on the low-frequency range (20-150 Hz) where drum beats are prominent
    low_freq_indices = np.where((fft_freq >= LOW_FREQ_LIMIT) & (fft_freq <= HIGH_FREQ_LIMIT))
    low_freq_magnitudes = np.abs(fft_result[low_freq_indices])
    
    # Adjusted threshold and peak detection parameters
    threshold = np.mean(low_freq_magnitudes) * 1.1  # Further lowered threshold for sensitivity
    peaks, _ = find_peaks(low_freq_magnitudes, height=threshold, distance=30)  # Reduced distance to 30

    # Track beat times based on detected peaks, using `time.time()` relative to `start_time`
    current_time = time.time() - start_time  # Get current time in seconds relative to start
    for peak in peaks:
        if len(beat_times) > 0 and current_time - beat_times[-1] < MIN_BEAT_INTERVAL:
            # Ignore duplicate beats detected too close together
            continue
        
        beat_times.append(current_time)
        print(f"Detected beat at: {current_time} seconds")  # Debug: print each detected beat time
    
    # Calculate intervals between beats and estimate BPM
    beat_intervals = np.diff(list(beat_times))  # Convert deque to list for diff
    
    # Filter out zero intervals
    beat_intervals = beat_intervals[beat_intervals > 0]
    
    print(f"Beat intervals (seconds): {beat_intervals}")  # Debug: print intervals
    bpm = calculate_bpm(beat_intervals)
    print(f"Estimated BPM: {bpm}")

def save_audio(filename, audio_data, samplerate):
    """Save the recorded audio data to a .wav file."""
    print("Saving recorded audio...")
    audio_data = np.concatenate(audio_data)  # Combine all chunks
    sf.write(filename, audio_data, samplerate)
    print(f"Audio saved as {filename}")
    return audio_data  # Return data for plotting

def plot_audio_waveform(audio_data, samplerate):
    """Plot the waveform of the recorded audio data."""
    plt.figure(figsize=(10, 4))
    time_axis = np.linspace(0, len(audio_data) / samplerate, num=len(audio_data))
    plt.plot(time_axis, audio_data, color='blue')
    plt.xlabel('Time (s)')
    plt.ylabel('Amplitude')
    plt.title('Recorded Audio Waveform')
    plt.grid()
    plt.show()

# Main program to start recording from the microphone and estimate BPM
print("Starting BPM estimation... Play some music with a strong beat.")
try:
    with sd.InputStream(callback=process_audio, channels=1, samplerate=SAMPLE_RATE, blocksize=BUFFER_SIZE):
        while True:
            time.sleep(1)  # Keep the main thread alive

except KeyboardInterrupt:
    # Save the recorded audio when the user stops the program
    audio_data = save_audio(OUTPUT_FILE, audio_buffer, SAMPLE_RATE)
    plot_audio_waveform(audio_data, SAMPLE_RATE)  # Plot the saved audio data

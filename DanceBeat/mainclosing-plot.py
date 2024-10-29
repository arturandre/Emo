import sounddevice as sd
import soundfile as sf
import numpy as np
from scipy.signal import find_peaks
from scipy.ndimage import gaussian_filter1d
import matplotlib.pyplot as plt
import time

# Parameters
SAMPLE_RATE = 44100  # Sampling rate for the microphone
WINDOW_DURATION = 5  # Duration of the analysis window in seconds
BUFFER_SIZE = int(SAMPLE_RATE * WINDOW_DURATION)  # Number of samples in a 5-second window
OUTPUT_FILE = "recorded_audio.wav"  # File where the audio is saved
CLOSING_STRUCTURE_SIZE = 300  # Reduced size for the closing operation
THRESHOLD = 0.1  # Threshold to zero out background noise (adjust as needed)
GAUSSIAN_SIGMA = 2  # Smoothing factor for Gaussian filter

# To store all the recorded audio data for saving later
audio_buffer = []

def apply_threshold(signal, threshold):
    """Apply a threshold to the signal, zeroing out values below the threshold."""
    return np.where(np.abs(signal) > threshold, signal, 0)

def apply_gaussian_smoothing(signal, sigma):
    """Apply Gaussian smoothing to the signal."""
    smoothed_signal = gaussian_filter1d(signal, sigma=sigma)
    return smoothed_signal

def process_audio(indata, frames, time_info, status):
    """Callback function to process audio in real-time."""
    global audio_buffer
    # Flatten to mono by taking only the first channel
    audio_data = indata[:, 0]

    # Append audio data to the buffer for saving later
    audio_buffer.append(audio_data.copy())

def save_audio(filename, audio_data, samplerate):
    """Save the recorded audio data to a .wav file."""
    print("Saving recorded audio...")
    audio_data = np.concatenate(audio_data)  # Combine all chunks
    sf.write(filename, audio_data, samplerate)
    print(f"Audio saved as {filename}")
    return audio_data  # Return data for further processing

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

def find_local_maxima(signal, samplerate):
    """Find local maxima in the closed signal to detect beats."""
    # Use scipy find_peaks to detect the peaks (local maxima)
    peaks, _ = find_peaks(signal, distance=samplerate / 2)  # Ensure peaks are separated by at least half a second
    return peaks

def calculate_bpm(peaks, samplerate):
    """Calculate the BPM based on peak intervals."""
    if len(peaks) < 2:
        return 0
    intervals = np.diff(peaks) / samplerate  # Convert peak distances to seconds
    avg_interval = np.mean(intervals)
    bpm = 60 / avg_interval if avg_interval != 0 else 0
    return int(bpm)

# Main program to start recording from the microphone
print("Starting recording... Press Ctrl+C to stop.")
try:
    with sd.InputStream(callback=process_audio, channels=1, samplerate=SAMPLE_RATE, blocksize=BUFFER_SIZE):
        while True:
            time.sleep(1)  # Keep the main thread alive

except KeyboardInterrupt:
    # Save the recorded audio when the user stops the program
    audio_data = save_audio(OUTPUT_FILE, audio_buffer, SAMPLE_RATE)
    
    # Plot the recorded audio waveform
    plot_audio_waveform(audio_data, SAMPLE_RATE)

    # Apply threshold to remove background noise
    thresholded_signal = apply_threshold(audio_data, THRESHOLD)
    
    # Apply Gaussian smoothing to smooth the waveform
    smoothed_signal = apply_gaussian_smoothing(thresholded_signal, GAUSSIAN_SIGMA)
    
    # Plot the smoothed signal
    plt.figure(figsize=(10, 4))
    time_axis = np.linspace(0, len(smoothed_signal) / SAMPLE_RATE, num=len(smoothed_signal))
    plt.plot(time_axis, smoothed_signal, color='green')
    plt.xlabel('Time (s)')
    plt.ylabel('Amplitude')
    plt.title('Smoothed Signal After Gaussian Filter')
    plt.grid()
    plt.show()

    # Find local maxima (beats)
    peaks = find_local_maxima(smoothed_signal, SAMPLE_RATE)
    
    # Calculate BPM
    bpm = calculate_bpm(peaks, SAMPLE_RATE)
    
    print(f"Detected peaks at sample indices: {peaks}")
    print(f"Estimated BPM: {bpm}")

    # Plot the waveform with detected peaks
    plt.figure(figsize=(10, 4))
    plt.plot(time_axis, audio_data, label="Original Signal")
    plt.plot(time_axis, smoothed_signal, label="Smoothed Signal", alpha=0.6)
    plt.scatter(time_axis[peaks], smoothed_signal[peaks], color='red', label='Detected Peaks')
    plt.xlabel('Time (s)')
    plt.ylabel('Amplitude')
    plt.title('Waveform with Detected Beats')
    plt.legend()
    plt.grid()
    plt.show()

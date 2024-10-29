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
    try:
        # Flatten to mono by taking only the first channel
        audio_data = indata[:, 0]
        print(f"Received {len(audio_data)} frames")  # Debugging: Check if audio is being received

        # Append audio data to the buffer for saving later
        audio_buffer.append(audio_data.copy())
    except Exception as e:
        print(f"Error during audio processing: {e}")

def find_local_maxima(signal, samplerate):
    """Find local maxima in the closed signal to detect beats."""
    try:
        peaks, _ = find_peaks(signal, distance=samplerate / 2)  # Ensure peaks are separated by at least half a second
        return peaks
    except Exception as e:
        print(f"Error during peak detection: {e}")
        return []

def calculate_bpm(peaks, samplerate):
    """Calculate the BPM based on peak intervals."""
    try:
        if len(peaks) < 2:
            return 0
        intervals = np.diff(peaks) / samplerate  # Convert peak distances to seconds
        avg_interval = np.mean(intervals)
        bpm = 60 / avg_interval if avg_interval != 0 else 0
        return int(bpm)
    except Exception as e:
        print(f"Error during BPM calculation: {e}")
        return 0

def process_window(audio_data, samplerate):
    """Process a 5-second window of audio data to estimate BPM."""
    try:
        # Apply threshold to remove background noise
        thresholded_signal = apply_threshold(audio_data, THRESHOLD)
        
        # Apply Gaussian smoothing to smooth the waveform
        smoothed_signal = apply_gaussian_smoothing(thresholded_signal, GAUSSIAN_SIGMA)
        
        # Find local maxima (beats)
        peaks = find_local_maxima(smoothed_signal, samplerate)
        
        # Calculate BPM
        bpm = calculate_bpm(peaks, samplerate)
        
        return bpm, peaks, smoothed_signal
    except Exception as e:
        print(f"Error during window processing: {e}")
        return 0, [], audio_data

# Main program to start recording from the microphone
print("Starting BPM estimation from a 5-second window... Press Ctrl+C to stop.")

try:
    with sd.InputStream(callback=process_audio, channels=1, samplerate=SAMPLE_RATE, blocksize=BUFFER_SIZE):
        while True:
            time.sleep(WINDOW_DURATION)  # Wait for the window duration (5 seconds)

            if len(audio_buffer) == 0:
                print("No audio data received yet.")
                continue

            # Concatenate and take only the last 5 seconds of audio (current window)
            audio_data = np.concatenate(audio_buffer)[-BUFFER_SIZE:]

            print(f"Processing {len(audio_data)} samples in the current window.")  # Debugging: Ensure audio is being processed

            # Estimate BPM from the current window
            bpm, peaks, smoothed_signal = process_window(audio_data, SAMPLE_RATE)

            print(f"Estimated BPM: {bpm}")
            
            # Plot the waveform with detected peaks
            time_axis = np.linspace(0, len(audio_data) / SAMPLE_RATE, num=len(audio_data))
            plt.figure(figsize=(10, 4))
            plt.plot(time_axis, audio_data, label="Original Signal")
            plt.plot(time_axis, smoothed_signal, label="Smoothed Signal", alpha=0.6)
            plt.scatter(time_axis[peaks], smoothed_signal[peaks], color='red', label='Detected Peaks')
            plt.xlabel('Time (s)')
            plt.ylabel('Amplitude')
            plt.title(f'Waveform with Detected Beats (BPM: {bpm})')
            plt.legend()
            plt.grid()
            plt.show()

except KeyboardInterrupt:
    # Handle when the user stops the program
    print("Stopping BPM estimation.")
except Exception as e:
    # Catch any other unexpected exceptions
    print(f"An error occurred: {e}")

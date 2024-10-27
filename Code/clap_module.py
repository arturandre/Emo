import numpy as np
import sounddevice as sd
from scipy.ndimage import gaussian_filter1d
import scipy.signal
import time

class ClapDetector:
    def __init__(self,
                 sample_rate=48000,
                 threshold=0.1,
                 min_clap_duration=0.08,
                 max_double_clap_gap=1.0,
                 word_length=4,
                 gaussian_sigma=4):
        # Parameters
        self.sample_rate = sample_rate
        self.threshold = threshold
        self.gaussian_sigma = gaussian_sigma
        self.min_clap_duration = min_clap_duration
        self.max_double_clap_gap = max_double_clap_gap
        self.word_length = word_length
        self.first_clap_maximum = float("-inf")
        self.second_clap_maximum = float("-inf")

        # Circular buffer to store recent audio samples
        self.buffer_size = int(sample_rate * 1)  # Store 1 second of audio
        self.audio_buffer = np.zeros(self.buffer_size)

        # Global state for clap detection
        self.listening_for_word = False
        self.current_word = []
        self.waiting_for_second_clap = False
        self.first_clap_time = None
        self.word_event_callback = None  # To hold the callback for when a word is completed

    # def audio_callback(self, indata, frames, time, status):
    #     """ Callback function to continuously capture audio """
    #     self.audio_buffer = np.roll(self.audio_buffer, -frames, axis=0)
    #     self.audio_buffer[-frames:] = indata[:, 0]  # Mono channel

    def audio_callback(self, indata, frames, time_info, status):
        """Callback function to continuously capture audio."""
        # Ensure we handle the case where frames might exceed the buffer size
        frames_to_use = min(frames, self.buffer_size)

        # Shift the buffer left by the number of frames
        self.audio_buffer[:-frames_to_use] = self.audio_buffer[frames_to_use:]

        # Append the new audio data to the end of the buffer
        self.audio_buffer[-frames_to_use:] = indata[:frames_to_use, 0]  # Mono channel

    


    def set_word_event_callback(self, callback):
        """ Set the callback function to trigger when a word is completed """
        self.word_event_callback = callback

    def start_detection(self):
        """ Start the clap detection loop """
        stream = sd.InputStream(
            callback=self.audio_callback, channels=1, samplerate=self.sample_rate)
        stream.start()

        print("Listening for claps...")

        try:
            while True:
                if self.detect_claps(self.audio_buffer):
                    print("Waiting for the next symbol...")
                # Continuously check if the double clap window has passed
                self.check_for_double_clap_timeout()
        except KeyboardInterrupt:
            print("Stopping...")
        finally:
            stream.stop()
            stream.close()
    
    def apply_threshold(self, signal):
        """Apply a threshold to the signal, zeroing out values below the threshold."""
        return np.where(np.abs(signal) > self.threshold, signal, 0)

    def apply_gaussian_smoothing(self, signal):
        """Apply Gaussian smoothing to the signal."""
        return gaussian_filter1d(signal, sigma=self.gaussian_sigma)

    def find_local_maxima(self, signal):
        """Find local maxima in the signal to detect beats."""
        peaks, _ = scipy.signal.find_peaks(signal, distance=self.sample_rate / 2)
        return peaks

    def process_audio_window(self):
        """Process the current window of audio data to estimate BPM."""
        # Apply threshold and smoothing
        thresholded_signal = self.apply_threshold(self.audio_buffer)
        smoothed_signal = self.apply_gaussian_smoothing(thresholded_signal)

        # Detect peaks and calculate BPM
        peaks = self.find_local_maxima(smoothed_signal)

        return peaks, smoothed_signal

    def detect_claps(self, audio_data):
        """ Function to detect claps and build the word """

        #peaks, _ = scipy.signal.find_peaks(audio_data, height=self.threshold, distance=int(self.min_clap_duration * self.sample_rate))
        peaks, smoothed_signal = self.process_audio_window()

        if len(peaks) > 0:
            current_time = time.time()

            if not self.listening_for_word:
                # Wake-up logic (first single clap)
                print("Wake-up detected. Start listening for the word...")
                self.listening_for_word = True
                self.current_word = []  # Reset the current word
                return True

            if self.waiting_for_second_clap:
                # Check if a second clap comes in the double clap window
                self.second_clap_maximum = np.abs(smoothed_signal).max()

                delay = current_time - self.first_clap_time
                if (delay <= self.max_double_clap_gap):
                    if (self.first_clap_maximum == self.second_clap_maximum):
                        # Avoiding fake 'echoes'
                        print("Fake echo detected! Ignoring second clap.")
                    else:
                        print(f"Double Clap Detected!")
                        self.current_word.append('D')  # 'D' for double clap
                        self.waiting_for_second_clap = False
                        self.clear_audio_buffer()

                        # Check if the word is complete
                        if len(self.current_word) >= self.word_length:
                            self.print_word_and_reset()

                return True
            else:
                # First clap detected, now wait for potential second clap
                print(f"First Clap Detected, waiting for potential second clap...")
                self.first_clap_maximum = np.abs(smoothed_signal).max()
                self.first_clap_time = current_time
                self.waiting_for_second_clap = True
                self.clear_audio_buffer()
                return True

        return False

    def check_for_double_clap_timeout(self):
        """ Check if the window for a double clap has passed without a second clap """
        if self.waiting_for_second_clap:
            current_time = time.time()
            if current_time - self.first_clap_time > self.max_double_clap_gap:
                # Timeout for second clap, treat it as a single clap
                print(f"Confirmed Single Clap")
                self.current_word.append('S')  # 'S' for single clap
                self.waiting_for_second_clap = False
                self.clear_audio_buffer()

                # Check if the word is complete
                if len(self.current_word) >= self.word_length:
                    self.print_word_and_reset()

    def print_word_and_reset(self):
        """ Print the completed word and reset the system """
        word = ''.join(self.current_word[:self.word_length])
        print(f"Word completed: {word}")
        if self.word_event_callback:
            self.word_event_callback(word)
        self.listening_for_word = False  # Reset to wait for the next wake-up
        self.current_word = []  # Clear the word for the next cycle

    def clear_audio_buffer(self):
        """ Clear the audio buffer after processing a clap to avoid repeated detection """
        self.audio_buffer = np.zeros(self.buffer_size)


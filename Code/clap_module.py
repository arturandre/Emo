import numpy as np
import sounddevice as sd
import scipy.signal
import time

class ClapDetector:
    def __init__(self, sample_rate=48000, threshold=0.1, min_clap_duration=0.08, max_double_clap_gap=2.0, word_length=4):
        # Parameters
        self.sample_rate = sample_rate
        self.threshold = threshold
        self.min_clap_duration = min_clap_duration
        self.max_double_clap_gap = max_double_clap_gap
        self.word_length = word_length

        # Circular buffer to store recent audio samples
        self.buffer_size = int(sample_rate * 1)  # Store 1 second of audio
        self.audio_buffer = np.zeros(self.buffer_size)

        # Global state for clap detection
        self.listening_for_word = False
        self.current_word = []
        self.waiting_for_second_clap = False
        self.first_clap_time = None
        self.word_event_callback = None  # To hold the callback for when a word is completed

    def audio_callback(self, indata, frames, time, status):
        """ Callback function to continuously capture audio """
        self.audio_buffer = np.roll(self.audio_buffer, -frames, axis=0)
        self.audio_buffer[-frames:] = indata[:, 0]  # Mono channel

    def set_word_event_callback(self, callback):
        """ Set the callback function to trigger when a word is completed """
        self.word_event_callback = callback

    def start_detection(self):
        """ Start the clap detection loop """
        stream = sd.InputStream(callback=self.audio_callback, channels=1, samplerate=self.sample_rate)
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

    def detect_claps(self, audio_data):
        """ Function to detect claps and build the word """
        peaks, _ = scipy.signal.find_peaks(audio_data, height=self.threshold, distance=int(self.min_clap_duration * self.sample_rate))

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
                if current_time - self.first_clap_time <= self.max_double_clap_gap:
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


import numpy as np
import sounddevice as sd
import scipy.signal
import time
from scipy.ndimage import gaussian_filter1d
import matplotlib.pyplot as plt
from adafruit_servokit import ServoKit
from display_module import DisplayControl


# Initialize ServoKit instance
kit = ServoKit(channels=16)

import os
os.system("raspi-gpio set 18 a0")  # Set GPIO 18 to PCM_Clock

display = DisplayControl()

# Stop dancing when there's no music
stop_dancing = True

# Define robot poses (angles for right arm, left arm, and base)
poses = [
    {'right_arm': 45, 'left_arm': 0, 'base': 30},
    {'right_arm': 90, 'left_arm': 45, 'base': 45},
    {'right_arm': 0, 'left_arm': 90, 'base': 15},
    {'right_arm': 135, 'left_arm': 135, 'base': 60},
    {'right_arm': 180, 'left_arm': 180, 'base': 0}
]

class RobotDanceBPM:
    def __init__(self,
                 sample_rate=48000,
                 window_duration=5,
                 threshold=0.010,
                 lowpass_sigma=10,
                 highpass_freq=500,
                 max_to_mean_radio_threshold=10):
        # Audio processing parameters
        self.sample_rate = sample_rate
        self.window_duration = window_duration
        self.threshold = threshold
        self.lowpass_sigma = lowpass_sigma
        self.highpass_freq = highpass_freq
        self.max_to_mean_radio_threshold = max_to_mean_radio_threshold
        self.wait_samples = int(window_duration*sample_rate//4)

        # Circular buffer for audio samples
        self.buffer_size = int(sample_rate * window_duration)
        self.audio_buffer = np.zeros(self.buffer_size)

        # Robot pose control
        self.current_pose = poses[0]
        self.current_pose_index = 0
        self.next_sequence = np.random.permutation(poses)
        self.new_samples = 0

    def audio_callback(self, indata, frames, time_info, status):
        """Callback function to continuously capture audio."""
        # Ensure we handle the case where frames might exceed the buffer size
        frames_to_use = min(frames, self.buffer_size)
        self.new_samples += frames_to_use

        # Shift the buffer left by the number of frames
        self.audio_buffer[:-frames_to_use] = self.audio_buffer[frames_to_use:]

        # Append the new audio data to the end of the buffer
        self.audio_buffer[-frames_to_use:] = indata[:frames_to_use, 0]  # Mono channel

    def apply_threshold(self, signal):
        """Apply a threshold to the signal, zeroing out values below the threshold."""
        return np.where(np.abs(signal) > self.threshold, signal, 0)

    def highpass_filter(self, signal):
        """Apply a high-pass filter to remove motor noise."""
        sos = scipy.signal.butter(4, self.highpass_freq, btype='highpass', fs=self.sample_rate, output='sos')
        return scipy.signal.sosfilt(sos, signal)

    def lowpass_smooth(self, signal):
        """Apply Gaussian smoothing as a low-pass filter to remove high-frequency noise."""
        return gaussian_filter1d(signal, sigma=self.lowpass_sigma)

    def bandpass_filter(self, signal):
        """Apply both high-pass and low-pass filters to create a band-pass effect."""
        filtered_signal = self.highpass_filter(signal)
        smoothed_signal = self.lowpass_smooth(filtered_signal)
        return smoothed_signal

    def find_local_maxima(self, signal):
        """Find local maxima in the signal to detect beats."""
        peaks, _ = scipy.signal.find_peaks(signal, distance=self.sample_rate / 2)
        return peaks

    def calculate_bpm(self, peaks):
        """Calculate the BPM based on peak intervals."""
        if len(peaks) < 2:
            return 0
        intervals = np.diff(peaks) / self.sample_rate  # Convert peak distances to seconds
        avg_interval = np.mean(intervals)
        bpm = 60 / avg_interval if avg_interval != 0 else 0
        return int(bpm)

    def process_audio_window(self, current_audio):
        """Process the current window of audio data to estimate BPM."""
        # Apply threshold and smoothing
        #filtered_signal = self.highpass_filter(self.audio_buffer)
        thresholded_signal = self.apply_threshold(current_audio)
        bandpassed_signal = self.bandpass_filter(thresholded_signal)
        #smoothed_signal = self.apply_gaussian_smoothing(thresholded_signal)

        # Detect peaks and calculate BPM
        peaks = self.find_local_maxima(bandpassed_signal)
        bpm = self.calculate_bpm(peaks)

        return bpm, peaks, bandpassed_signal

    def move_to_pose(self, pose, interval):
        """Move the robot to the specified pose."""
        #print(f"Moving to pose: Right Arm: {pose['right_arm']}°, Left Arm: {pose['left_arm']}°, Base: {pose['base']}°")
        o_right_arm_pose = self.current_pose['right_arm']
        o_left_arm_pose = self.current_pose['left_arm']
        o_base_pose = self.current_pose['base']
        d_right_arm_pose = pose['right_arm']
        d_left_arm_pose = pose['left_arm']
        d_base_pose = pose['base']
        tinterval = int(interval*100)
        for i in range(tinterval):
            t_left = (tinterval-i)/tinterval
            t_done = i/tinterval
            r_pose = int((t_left)*o_right_arm_pose + t_done*d_right_arm_pose)
            l_pose = int((t_left)*o_left_arm_pose + t_done*d_left_arm_pose)
            b_pose = int((t_left)*o_base_pose + t_done*d_base_pose)
            #print(f"{t_left:.2f} {t_done:.2f}",
            #      o_right_arm_pose, d_right_arm_pose, r_pose, l_pose, b_pose)
            kit.servo[0].angle = r_pose  # Right arm
            kit.servo[1].angle = l_pose   # Left arm
            kit.servo[2].angle = b_pose # Base
            time.sleep(0.002)
        self.current_pose = pose

    def dance_to_bpm(self, bpm):
        global stop_dancing
        """Control robot movement based on BPM."""
        interval = 60 / bpm  # Time interval between moves (in seconds)
        print(f"Dancing at {bpm} BPM. Moving every {interval:.2f} seconds")

        self.current_pose_index = 0  # Start from the first pose
        while True:
            if stop_dancing:
                break
            # Move to the current pose
            self.move_to_pose(self.next_sequence[self.current_pose_index], interval)
            #self.move_to_pose(self.current_pose, interval)
            
            # Wait based on the BPM
            #time.sleep(interval)

            # Cycle to the next pose
            #self.current_pose_index = np.random.choice(len(poses)) 
            #self.current_pose = np.random.choice(poses)
            self.current_pose_index += 1 
            #self.current_pose_index %= len(poses)
            if self.current_pose_index == len(poses):
                self.next_sequence = np.random.permutation(poses)
                break

    def start_bpm_detection_and_dancing(self):
        global stop_dancing
        """Start the BPM detection and make the robot dance to the rhythm."""
        stream = sd.InputStream(
            callback=self.audio_callback, channels=1, samplerate=self.sample_rate)
        stream.start()

        print("Listening for music and estimating BPM... Press Ctrl+C to stop.")

        try:
            while True:
                stop_dancing = False
                #time.sleep(self.window_duration)  # Wait for the duration of the window (5 seconds)
                if self.new_samples > self.wait_samples:
                    print(f"self.new_samples: {self.new_samples}")
                    self.new_samples = 0
                    # Estimate BPM from the current window
                    current_audio = self.audio_buffer[-self.wait_samples:].copy()
                    bpm, peaks, bandpassed_signal = self.process_audio_window(current_audio)

                    abs_audio = np.abs(current_audio)
                    abs_baudio = np.abs(bandpassed_signal)
                    print(
                    f"signal max: {abs_audio.max():4f}\n",
                    f"signal median: {np.mean(abs_audio):4f}\n",
                    f"signal min: {abs_audio.min():4f}\n",
                    )
                    print(
                    f"b_signal max: {abs_baudio.max():4f}\n",
                    f"b_signal median: {np.mean(abs_baudio):4f}\n",
                    f"b_signal min: {abs_baudio.min():4f}\n",
                    )

                    #max_to_mean_radio_threshold = abs_audio.max()/abs_audio.mean()
                    #max_to_mean_radio_threshold = abs_baudio.max()/np.median(abs_baudio)
                    max_to_mean_radio_threshold = np.mean(abs_audio)/np.mean(abs_baudio)
                    self.threshold = abs_audio.max()*0.5
                    print(f"audio_mean/audio_max: {np.mean(abs_audio)/abs_audio.max()}")
                    print(f"baudio_mean/baudio_max: {np.mean(abs_baudio)/abs_baudio.max()}")
                    print(f"max_to_mean_radio_threshold: {max_to_mean_radio_threshold}")
                    print(f"Current threshold: {self.threshold}")
                    if (np.mean(abs_audio)/abs_audio.max()) < 0.1:
                        print("\nStop dancing\n")
                        stop_dancing = True
                        display.show('neutral', -1, stop_now=True)
                        continue
                    
                    if bpm > 0:
                        print(f"Estimated BPM: {bpm}")
                        display.show('happy', -1, stop_now=True)
                        self.dance_to_bpm(bpm)
                    else:
                        print("No BPM detected, adjusting...")
                    
        except KeyboardInterrupt:
            print("Stopping BPM detection and robot dance.")
        finally:
            stream.stop()
            stream.close()

# Main program to start the BPM estimation and robot dancing
if __name__ == "__main__":
    robot_dance_bpm = RobotDanceBPM(max_to_mean_radio_threshold=10)
    robot_dance_bpm.start_bpm_detection_and_dancing()

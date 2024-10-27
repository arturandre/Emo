import time

import numpy as np
from adafruit_servokit import ServoKit
from display_module import DisplayControl
from mediapipe.tasks import python
from mediapipe.tasks.python import audio
from mediapipe.tasks.python.audio.core import audio_record
from mediapipe.tasks.python.components import containers
import threading

# Initialize ServoKit and DisplayControl instances
kit = ServoKit(channels=16)
display = DisplayControl()

# Define robot poses (angles for right arm, left arm, and base)
poses = [
    {'right_arm': 45, 'left_arm': 0, 'base': 30},
    {'right_arm': 90, 'left_arm': 45, 'base': 45},
    {'right_arm': 0, 'left_arm': 90, 'base': 15},
    {'right_arm': 135, 'left_arm': 135, 'base': 60},
    {'right_arm': 180, 'left_arm': 180, 'base': 0}
]

# Global variable to stop dancing
stop_dancing_limit = 30
stop_dancing = stop_dancing_limit
last_face = None

class RobotDanceWithMusicDetection:
    def __init__(self, model_path='yamnet.tflite', score_threshold=0.4):
        self.score_threshold = score_threshold

        # MediaPipe audio classifier initialization for music detection
        base_options = python.BaseOptions(model_asset_path=model_path)
        options = audio.AudioClassifierOptions(
            base_options=base_options,
            running_mode=audio.RunningMode.AUDIO_STREAM,
            max_results=10,
            score_threshold=score_threshold,
            result_callback=self.music_callback
        )
        self.classifier = audio.AudioClassifier.create_from_options(options)

        # Audio configuration
        self.buffer_size = 15600  # Buffer size for audio data
        self.sample_rate = 16000   # Sample rate of the microphone
        self.audio_format = containers.AudioDataFormat(1, self.sample_rate)
        self.record = audio_record.AudioRecord(1, self.sample_rate, self.buffer_size)
        self.audio_data = containers.AudioData(self.buffer_size, self.audio_format)

        # Robot pose control
        self.current_pose = poses[0]
        self.current_pose_index = 0
        self.next_sequence = poses

    def music_callback(self, result, timestamp_ms):
        """Callback function to handle classification results for music detection."""
        global stop_dancing
        music_detected = False

        # Print top ten predictions and their classification scores
        print("Top predictions:")
        for category in result.classifications[0].categories[:10]:
            print(f"{category.category_name}: {category.score:.2f}")
            if category.category_name.lower() == "music" and category.score > self.score_threshold:
                music_detected = True
                print("music_detected")

        if not music_detected:
            stop_dancing += 1
        else:
            stop_dancing = 0

    def normalize_audio(self, data):
        """Normalize the audio data to a consistent range."""
        max_amplitude = np.max(np.abs(data))
        if max_amplitude > 0:
            return data / max_amplitude  # Scale audio data to be within [-1, 1]
        return data

    def start_audio_stream(self):
        """Continuously stream audio to MediaPipe AudioClassifier for music detection."""
        self.record.start_recording()

        while True:
            # Load audio data from microphone
            data = self.record.read(self.buffer_size)
            normalized_data = self.normalize_audio(data)
            self.audio_data.load_from_array(normalized_data)
            self.classifier.classify_async(self.audio_data, time.time_ns() // 1_000_000)

            time.sleep(0.1)  # Sleep briefly to prevent excessive CPU usage

    def move_to_pose(self, pose, interval):
        global stop_dancing
        global stop_dancing_limit
        """Move the robot to the specified pose."""
        o_right_arm_pose = self.current_pose['right_arm']
        o_left_arm_pose = self.current_pose['left_arm']
        o_base_pose = self.current_pose['base']
        d_right_arm_pose = pose['right_arm']
        d_left_arm_pose = pose['left_arm']
        d_base_pose = pose['base']
        tinterval = int(interval * 100)

        for i in range(tinterval):
            t_left = (tinterval - i) / tinterval
            t_done = i / tinterval
            kit.servo[0].angle = int((t_left) * o_right_arm_pose + t_done * d_right_arm_pose)
            kit.servo[1].angle = int((t_left) * o_left_arm_pose + t_done * d_left_arm_pose)
            kit.servo[2].angle = int((t_left) * o_base_pose + t_done * d_base_pose)
            time.sleep(0.002)
        
        self.current_pose = pose

    def dance_to_music(self):
        """Control robot movement based on detected music."""
        global stop_dancing
        interval = 0.5  # Default interval between moves when music is detected

        self.current_pose_index = 0
        while stop_dancing < stop_dancing_limit:
            self.move_to_pose(self.next_sequence[self.current_pose_index], interval)
            self.current_pose_index = (self.current_pose_index + 1) % len(poses)
            if self.current_pose_index == 0:
                self.next_sequence = poses

    def start_detection_and_dancing(self):
        global stop_dancing
        global stop_dancing_limit
        global last_face
        """Start music detection using MediaPipe and make the robot dance if music is detected."""
        print("Listening for music... Press Ctrl+C to stop.")

        # Start audio streaming in a separate thread
        
        threading.Thread(target=self.start_audio_stream, daemon=True).start()

        try:
            while True:
                if stop_dancing < stop_dancing_limit:
                    if last_face != 'happy':
                        display.show('happy', -1, stop_now=True)
                        last_face = 'happy'
                    print("Music detected; starting dance.")
                    self.dance_to_music()
                else:
                    if last_face != 'neutral':
                        display.show('neutral', -1, stop_now=True)
                        last_face = 'neutral'
                    print("No music detected; pausing dance.")
                
                time.sleep(1)

        except KeyboardInterrupt:
            print("Stopping music detection and robot dance.")
            self.record.stop_recording()

# Main program to start the music detection and robot dancing
if __name__ == "__main__":
    robot_dance = RobotDanceWithMusicDetection(model_path='yamnet.tflite', score_threshold=0.4)
    robot_dance.start_detection_and_dancing()

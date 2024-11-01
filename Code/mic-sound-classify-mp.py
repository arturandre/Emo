import numpy as np
import sounddevice as sd
import time
from adafruit_servokit import ServoKit
from mediapipe.tasks import python
from mediapipe.tasks.python.audio.core import audio_record
from mediapipe.tasks.python.components import containers
from mediapipe.tasks.python import audio

# Initialize ServoKit instance
kit = ServoKit(channels=16)

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

class RobotDanceMP:
    def __init__(self, model_path='yamnet.tflite',
                 buffer_size=15600, sample_rate=16000, score_threshold=0.5):
        self.sample_rate = sample_rate
        self.buffer_size = buffer_size
        self.score_threshold = score_threshold

        # Initialize MediaPipe audio classifier
        base_options = python.BaseOptions(model_asset_path=model_path)
        options = audio.AudioClassifierOptions(
            base_options=base_options, 
            running_mode=audio.RunningMode.AUDIO_STREAM,
            max_results=10,  # Retrieve top 10 results
            score_threshold=score_threshold,
            result_callback=self.music_callback
        )
        self.classifier = audio.AudioClassifier.create_from_options(options)

        # Initialize audio recording parameters
        audio_format = containers.AudioDataFormat(1, sample_rate)
        self.record = audio_record.AudioRecord(1, sample_rate, buffer_size)
        self.audio_data = containers.AudioData(buffer_size, audio_format)
        
        # Robot pose control
        self.current_pose = poses[0]
        self.current_pose_index = 0
        self.next_sequence = np.random.permutation(poses)

        # Dance state
        self.dance_bpm = 120  # Default BPM
        self.stop_dancing = True

    def music_callback(self, result, timestamp_ms):
        """Callback function to handle classification results."""
        print("Top 10 classification results:")
        for i, category in enumerate(result.classifications[0].categories[:10]):
            print(f"{i+1}. {category.category_name}: {category.score:.2f}")
            if category.category_name == "music" and category.score > self.score_threshold:
                self.stop_dancing = False
                return
        self.stop_dancing = True

    def move_to_pose(self, pose, interval):
        """Move the robot to the specified pose with smooth transition."""
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
            r_pose = int((t_left) * o_right_arm_pose + t_done * d_right_arm_pose)
            l_pose = int((t_left) * o_left_arm_pose + t_done * d_left_arm_pose)
            b_pose = int((t_left) * o_base_pose + t_done * d_base_pose)
            kit.servo[0].angle = r_pose  # Right arm
            kit.servo[1].angle = l_pose  # Left arm
            kit.servo[2].angle = b_pose  # Base
            time.sleep(0.002)
        self.current_pose = pose

    def dance_to_bpm(self, bpm):
        """Control robot movement based on BPM."""
        interval = 60 / bpm  # Time interval between moves (in seconds)
        print(f"Dancing at {bpm} BPM. Moving every {interval:.2f} seconds")

        self.current_pose_index = 0  # Start from the first pose
        while not self.stop_dancing:
            # Move to the current pose
            self.move_to_pose(self.next_sequence[self.current_pose_index], interval)

            # Cycle to the next pose
            self.current_pose_index += 1 
            if self.current_pose_index == len(poses):
                self.next_sequence = np.random.permutation(poses)
                self.current_pose_index = 0

    def normalize_audio(self, data):
        """Normalize the audio data to a consistent range."""
        max_amplitude = np.max(np.abs(data))
        if max_amplitude > 0:
            return data / max_amplitude  # Scale audio data to be within [-1, 1]
        return data

    def start_music_detection_and_dancing(self):
        """Start the music detection and make the robot dance when music is detected."""
        # Start audio recording in the background
        self.record.start_recording()
        print("Listening for music and starting to dance if music is detected...")

        try:
            while True:
                # Read audio data from the buffer and process with MediaPipe
                #data = self.record.read(self.buffer_size)
                #self.audio_data.load_from_array(data)
                data = self.record.read(self.buffer_size)
                normalized_data = self.normalize_audio(data)
                self.audio_data.load_from_array(normalized_data)
                
                self.classifier.classify_async(self.audio_data, time.time_ns() // 1_000_000)

                # If music detected, dance to the beat
                if not self.stop_dancing:
                    self.dance_to_bpm(self.dance_bpm)
                else:
                    print("Pausing dance; no music detected.")

                time.sleep(1)  # Adjust sleep to manage detection frequency

        except KeyboardInterrupt:
            print("Stopping music detection and robot dance.")
        finally:
            self.record.stop_recording()

# Main program to start the music detection and robot dancing
if __name__ == "__main__":
    robot_dance_mp = RobotDanceMP(model_path='yamnet.tflite', score_threshold=0.5)
    robot_dance_mp.start_music_detection_and_dancing()

import argparse
import threading
import psutil  # For setting CPU affinity
from camera_module import CameraModule
from clap_module import ClapDetector
from adafruit_servokit import ServoKit
from display_module import DisplayControl  # Importing the updated display module


# Initialize the ServoKit instance for 16 channels
try:
    kit = ServoKit(channels=16)
except ValueError: # The motors were not detected.
    print("Motor driver not detected, is it connected?")
    kit = None

import os
os.system("raspi-gpio set 18 a0")  # Set GPIO 18 to PCM_Clock


# Initialize the DisplayControl instance
display = DisplayControl()






# Function to display 'neutral' when idle and 'happy' when a word is detected
def display_neutral():
    display.show('neutral', -1)  # Show 'neutral' indefinitely

def display_happy_and_return_to_neutral():
    # Show the 'happy' face, interrupt any current animation, then return to 'neutral'
    display.show('happy', 1, stop_now=True)  # Show 'happy' face once
    display_neutral()  # Go back to 'neutral' afterward

# Define the callback function that will be triggered when a word is detected
def on_word_completed(word):
    print(f"Word Detected: {word}")

    # Show happy face when any word is detected
    display_happy_and_return_to_neutral()

    # Control the right arm based on the detected word
    if word == "SSSS":
        print("Rotating right arm clockwise.")
        if kit is not None:
            kit.continuous_servo[1].throttle = 1  # Clockwise rotation
        else:
            print("Tried clockwise rotation, but the servo driver was not detected!")

    elif word == "SSSD":
        print("Rotating right arm counter-clockwise.")
        if kit is not None:
            kit.continuous_servo[1].throttle = -1  # Counter-clockwise rotation
        else:
            print("Tried counter-clockwise rotation, but the servo driver was not detected!")

    elif word == "SSDD":
        print("Stopping right arm.")
        if kit is not None:
            kit.continuous_servo[1].throttle = 0.1  # Stop rotation
        else:
            print("Tried stopping right arm, but the servo driver was not detected!")

    elif word == "DSSS":
        print("Rotating left arm counter-clockwise.")
        if kit is not None:
            kit.continuous_servo[2].throttle = -1  # Counter-clockwise rotation
        else:
            print("Tried counter-clockwise rotation, but the servo driver was not detected!")

    elif word == "DSSD":
        print("Rotating left arm clockwise.")
        if kit is not None:
            kit.continuous_servo[2].throttle = 1  # Clockwise rotation
        else:
            print("Tried clockwise rotation, but the servo driver was not detected!")

    elif word == "DSDD":
        print("Stopping left arm.")
        if kit is not None:
            kit.continuous_servo[2].throttle = 0.1  # Stop left arm
        else:
            print("Tried stopping left arm, but the servo driver was not detected!")

    elif word == "DDDS":
        print("Rotating both arms clockwise.")
        if kit is not None:
            kit.continuous_servo[1].throttle = 1  # Rotate right clockwise
            kit.continuous_servo[2].throttle = -1  # Rotate left counter-clockwise
        else:
            print("Tried rotating both arms, but the servo driver was not detected!")

    elif word == "DDSD":
        print("Rotating both arms.")
        if kit is not None:
            kit.continuous_servo[1].throttle = 1  # Rotate both clockwise
            kit.continuous_servo[2].throttle = 1  # Rotate both clockwise
        else:
            print("Tried rotating both arms, but the servo driver was not detected!")

    elif word == "DDDD":
        print("Stopping both arms.")
        if kit is not None:
            kit.continuous_servo[1].throttle = 0.1  # Stop right arm
            kit.continuous_servo[2].throttle = 0.1  # Stop left arm
        else:
            print("Tried stopping both arms, but the servo driver was not detected!")


# Initialize the CameraModule
def start_camera_module(args):
    def arm_callback(state):
        print(f"Arm state detected: {state}")
    
    camera_module = CameraModule(
        callback=arm_callback,
        video_source=args.video_source,
        show_gui=args.show_gui,
        libcamera=args.libcamera,
        use_mpipe=args.mpipe
    )
    camera_module.start()

# Initialize the ClapDetector and start detection
def start_clap_detection():
    clap_detector = ClapDetector()
    clap_detector.set_word_event_callback(on_word_completed)
    clap_detector.start_detection()

# Set CPU affinity for a thread or process
def set_cpu_affinity(thread, cores):
    # Get the thread's process ID
    pid = threading.get_native_id()
    process = psutil.Process(pid)
    process.cpu_affinity(cores)

# Initialize the CameraModule and start detection
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run arm and clap detection.")
    parser.add_argument("--video_source", type=int, default=0, help="Video source, default is 0 (webcam).")
    parser.add_argument("--show_gui", action="store_true", help="Display GUI for feedback.")
    parser.add_argument("--libcamera", action="store_true", help="Use libcamera for Raspberry Pi.")
    parser.add_argument("--mpipe", action="store_true", help="Use MediaPipe for arm detection.")

    args = parser.parse_args()

    def arm_callback(state):
        print(f"Arm state detected: {state}")

    camera_module = CameraModule(
        callback=arm_callback,
        video_source=args.video_source,
        show_gui=args.show_gui,
        libcamera=args.libcamera,
        use_mpipe=args.mpipe
    )

    # Start the display with 'neutral' face initially
    display_neutral()

    # Create threads for camera and clap detection
    camera_thread = threading.Thread(target=start_camera_module, args=(args,))
    clap_thread = threading.Thread(target=start_clap_detection)
    
    # Start both threads
    camera_thread.start()
    clap_thread.start()

    # Set CPU affinity: reserve core 0 for clap detection and cores 1, 2, 3 for the rest
    set_cpu_affinity(clap_thread, [0])  # Reserve core 0 for clap detection
    set_cpu_affinity(camera_thread, [1, 2, 3])  # Allow camera module to use cores 1, 2, and 3

    
    # Wait for both threads to complete (if needed)
    camera_thread.join()
    clap_thread.join()
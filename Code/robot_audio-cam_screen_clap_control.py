import argparse
import threading
from time import sleep
import numpy as np
import psutil  # For setting CPU affinity
from camera_module import CameraModule
from clap_module import ClapDetector
from adafruit_servokit import ServoKit
from display_module import DisplayControl
# Function to display 'neutral' when idle and 'happy' when a word is detected
from sound_module import SoundModule  # Updated import to use the SoundModule class
import os


# Back of the robot
#                 o   
#Left arm - 1 # <( )> # Right arm - 0
#                ____


# Initialize the ServoKit instance for 16 channels
try:
    kit = ServoKit(channels=16)
except ValueError:  # The motors were not detected.
    print("Motor driver not detected, is it connected?")
    kit = None

sound_module = SoundModule()  # Singleton instance

# Don't use it directly, use the accessors
_ignore_camera = False

def set_ignore_camera():
    global _ignore_camera
    _ignore_camera = True
    print("Ignoring camera")

def reset_ignore_camera():
    global _ignore_camera
    _ignore_camera = False
    print("Reading camera")

left_arm_state = 'down'
right_arm_state = 'down'
rng = np.random.default_rng()
f_chance = 0.01
interacting_lock = threading.Lock()

ra = 10 # right arm index in motor driver
la = 9  # left arm index in motor driver
bb = 11 # base arm index in motor driver

if kit is not None:
    kit.servo[bb].angle = 30

# Initialize the DisplayControl instance
display = DisplayControl()

import os
os.system("raspi-gpio set 18 a0")  # Set GPIO 18 to PCM_Clock


def move_body(side):
    errors = []
    if side not in ['left', 'right']:
        errors.append(f"side expected to be a string 'left' or 'right', but found: {side}")
    if len(errors) > 0:
        raise Exception("\n".join(errors))
    if side == 'left':
        kit.servo[bb].angle = 15
    elif side == 'right':
        kit.servo[bb].angle = 45
    print(f"Moving base {side}")

def move_arm(arm_side, up_down):
    global left_arm_state
    global right_arm_state
    errors = []
    if arm_side not in ['left', 'right']:
        errors.append(f"arm_side expected to be a string 'left' or 'right', but found: {arm_side}")
    if up_down not in ['up', 'down']:
        raise Exception(f"up_down expected to be a string 'up' or 'down', but found: {up_down}")
    changed_state = False
    if arm_side == 'left':
        arm_index = la
        changed_state = changed_state or (up_down != left_arm_state)
        left_arm_state = up_down
        if up_down == 'up':
            kit.servo[arm_index].angle = 0
        elif up_down == 'down':
            kit.servo[arm_index].angle = 180
    if arm_side == 'right':
        arm_index = ra
        changed_state = changed_state or (up_down != right_arm_state)
        right_arm_state = up_down
        if up_down == 'up':
            kit.servo[arm_index].angle = 180
        elif up_down == 'down':
            kit.servo[arm_index].angle = 0
    
    if changed_state:
        print(f"Moving {arm_side} arm {up_down}")

# Function to display 'neutral' when idle and 'happy' when a word is detected
# def display_neutral():
#     display.show('neutral', -1)  # Show 'neutral' indefinitely

# def display_face_and_return_to_neutral(face):
#     # Show the 'happy' face, interrupt any current animation, then return to 'neutral'
#     with interacting_lock:
#         display.show(face, 1, stop_now=True)  # Show 'dizzy' face once
#         display_neutral()  # Go back to 'neutral' afterward

def on_waiting_second_clap():
    set_ignore_camera()
    print("on_waiting_second_clap")
    sound_module.speak_ping()
    print("on_waiting_second_clap after speak")

def on_clap_detected(symbol):
    reset_ignore_camera()
    print(f"on_clap_detected: {symbol}")
    sound_module.speak_pong()
    print("on_clap_detected after speak")
    if symbol == 'S': # Single clap detected
        pass
    elif symbol == 'D': # Double clap detected
        pass
    else:
        raise Exception(f"Unexpected clap symbol detected: {symbol}")

# Define the callback function that will be triggered when a word is detected
def on_word_completed(word):
    global left_arm_state
    global right_arm_state
    global sound_module

    valid_word = True
    print(f"Word Detected: {word}")
    print(f"right_arm_state: {right_arm_state}")
    print(f"left_arm_state: {left_arm_state}")

    # Control the right arm based on the detected word
    if word == "SSSS":
        print("Rotating right arm clockwise.")
        if kit is not None:
            #move_arm('right', 'down' if right_arm_state == 'up' else 'up')
            if (left_arm_state == 'up') and (right_arm_state == 'up'):
                sound_module.speak_dancing_time()
                set_ignore_camera()
                for _ in range(10):
                    move_arm('right', 'down')
                    move_arm('left', 'up')
                    sleep(0.5)
                    move_arm('right', 'up')
                    move_arm('left', 'down')
                    sleep(0.5)
                reset_ignore_camera()
            elif (left_arm_state == 'down') and (right_arm_state == 'down'):
                sound_module.speak_danger()
        else:
            print("Tried clockwise rotation, but the servo driver was not detected!")

    elif word == "SSSD":
        print("Rotating right arm counter-clockwise.")
        if kit is not None:
            move_arm('right', 'down' if right_arm_state == 'up' else 'up')
        else:
            print("Tried counter-clockwise rotation, but the servo driver was not detected!")

    elif word == "SSDS":
        print("Rat sequence!")
        display.display_face_and_return_to_neutral('rat')

    elif word == "SSDD":
        print("Stopping right arm.")
        if kit is not None:
            move_arm('right', 'down' if right_arm_state == 'up' else 'up')
        else:
            print("Tried stopping right arm, but the servo driver was not detected!")

    elif word == "DSSS":
        print("Rotating left arm counter-clockwise.")
        if kit is not None:
            move_arm('left', 'down' if left_arm_state == 'up' else 'up')
        else:
            print("Tried counter-clockwise rotation, but the servo driver was not detected!")

    elif word == "DSSD":
        print("Rotating left arm clockwise.")
        if kit is not None:
            move_arm('left', 'down' if left_arm_state == 'up' else 'up')
        else:
            print("Tried clockwise rotation, but the servo driver was not detected!")

    elif word == "DSDD":
        print("Stopping left arm.")
        if kit is not None:
            move_arm('left', 'down' if left_arm_state == 'up' else 'up')
        else:
            print("Tried stopping left arm, but the servo driver was not detected!")

    elif word == "DDDS":
        print("Rotating both arms clockwise.")
        if kit is not None:
            move_arm('right', 'down' if right_arm_state == 'up' else 'up')
            move_arm('left', 'down' if left_arm_state == 'up' else 'up')
        else:
            print("Tried rotating both arms, but the servo driver was not detected!")

    elif word == "DDSD":
        print("Rotating both arms.")
        if kit is not None:
            move_arm('right', 'down' if right_arm_state == 'up' else 'up')
            move_arm('left', 'down' if left_arm_state == 'up' else 'up')
        else:
            print("Tried rotating both arms, but the servo driver was not detected!")

    elif word == "DDDD":
        print("Stopping both arms.")
        if kit is not None:
            move_arm('right', 'down' if right_arm_state == 'up' else 'up')
            move_arm('left', 'down' if left_arm_state == 'up' else 'up')
        else:
            print("Tried stopping both arms, but the servo driver was not detected!")
    else:
        valid_word = False
    
    
    if valid_word:
        #sound_module.play_clip('ohyeah')
        sound_module.speak_oh_yeah()
        display.display_face_and_return_to_neutral('happy')
    else:
        #sound_module.play_clip('ohno')
        sound_module.speak_oh_no()
        display.display_face_and_return_to_neutral('dizzy')


def fart():
    global f_chance
    global rng
    global sound_module
    
    while True:
        if rng.random() < f_chance:
            move_body("left")
            sleep(0.5)
            move_body("right")
            sound_module.play_clip('fart')
            display.display_face_and_return_to_neutral('excited')
        else:
            print("Accumulating gases...")
        sleep(1.0)


# Initialize the CameraModule
def start_camera_module(args):
    def hand_callback(hand_state):
        global _ignore_camera
        if _ignore_camera:
            return
        if hand_state is None:
            pass
        elif hand_state == "open_hand":
            print("open_hand")
        elif hand_state == "closed_hand":
            print("closed_hand")
        else:
            raise Exception(f"Unexpected hand state: {hand_state}")

    def pose_callback(arm_state):
        global _ignore_camera
        if _ignore_camera:
            return

        if arm_state is None:
            pass # No arm detected
        elif arm_state == 'right_arm_up': # Reflected
            move_arm('left', 'up')
            move_arm('right', 'down')
        elif arm_state == 'left_arm_up': # Reflected
            move_arm('left', 'down')
            move_arm('right', 'up')
        elif arm_state == 'both_arms_up':
            move_arm('left', 'up')
            move_arm('right', 'up')
        elif arm_state == 'both_arms_down':
            move_arm('left', 'down')
            move_arm('right', 'down')
        else:
            raise Exception(f"Unexpected arm state: {arm_state}")
    
    camera_module = CameraModule(
        callback=pose_callback,
        hand_callback=hand_callback,
        video_source=args.video_source,
        show_gui=args.show_gui,
        libcamera=args.libcamera,
        vid=args.vid,
        use_mpipe=args.mpipe
    )
    camera_module.start()



# Initialize the ClapDetector and start detection
def start_clap_detection():
    clap_detector = ClapDetector(max_double_clap_gap=1.0)
    clap_detector.set_word_event_callback(on_word_completed)
    clap_detector.set_waiting_second_clap_event_callback(on_waiting_second_clap)
    clap_detector.set_clap_completed_event_callback(on_clap_detected)
    clap_detector.start_detection()

# Set CPU affinity for a thread or process
def set_cpu_affinity(thread, cores):
    pid = threading.get_native_id()
    process = psutil.Process(pid)
    process.cpu_affinity(cores)

# Initialize the CameraModule and start detection
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run arm and clap detection.")
    parser.add_argument("--video_source", type=int, default=0, help="Video source, default is 0 (webcam).")
    parser.add_argument("--show_gui", action="store_true", help="Display GUI for feedback.")
    parser.add_argument("--libcamera", action="store_true", help="Use libcamera-still for Raspberry Pi.")
    parser.add_argument("--vid", action="store_true", help="Use libcamera-vid for Raspberry Pi.")
    parser.add_argument("--mpipe", action="store_true", help="Use MediaPipe for arm detection.")

    args = parser.parse_args()

    sound_module.load_audio_clips()  # Preload audio clips into memory

    # Start the display with 'neutral' face initially
    #display.display_neutral()

    # Create threads for camera and clap detection
    camera_thread = threading.Thread(target=start_camera_module, args=(args,))
    clap_thread = threading.Thread(target=start_clap_detection)
    #fart_thread = threading.Thread(target=fart)

    # Start both threads
    camera_thread.start()
    clap_thread.start()
    #fart_thread.start()

    # Set CPU affinity: reserve core 0 for clap detection and cores 1, 2, 3 for the rest
    set_cpu_affinity(camera_thread, [2,3])
    set_cpu_affinity(clap_thread, [0,1])
    #set_cpu_affinity(fart_thread, [1, 2])

    display.display_face_and_return_to_neutral('rat')

   
    # Wait for both threads to complete (if needed)
    camera_thread.join()
    clap_thread.join()
    #fart_thread.join()

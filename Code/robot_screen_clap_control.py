from clap_module import ClapDetector
from adafruit_servokit import ServoKit
from display_module import DisplayControl  # Importing the updated display module

# Initialize the ServoKit instance for 16 channels
kit = ServoKit(channels=16)

# Initialize the DisplayControl instance
display = DisplayControl()


import os
os.system("raspi-gpio set 18 a0")  # Set GPIO 18 to PCM_Clock




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
        kit.continuous_servo[1].throttle = 1  # Clockwise rotation
    elif word == "SSSD":
        print("Rotating right arm counter-clockwise.")
        kit.continuous_servo[1].throttle = -1  # Counter-clockwise rotation
    elif word == "SSDD":
        print("Stopping right arm.")
        kit.continuous_servo[1].throttle = 0.1  # Stop rotation
    elif word == "DSSS":
        print("Rotating left arm counter-clockwise.")
        kit.continuous_servo[2].throttle = -1  # Counter-clockwise rotation
    elif word == "DSSD":
        print("Rotating left arm clockwise.")
        kit.continuous_servo[2].throttle = 1  # Clockwise rotation
    elif word == "DSDD":
        print("Stopping left arm.")
        kit.continuous_servo[2].throttle = 0.1  # Stop left arm
    elif word == "DDDS":
        print("Rotating both arms clockwise.")
        kit.continuous_servo[1].throttle = 1  # Rotate right clockwise
        kit.continuous_servo[2].throttle = -1  # Rotate left counter-clockwise
    elif word == "DDSD":
        print("Rotating both arms.")
        kit.continuous_servo[1].throttle = 1  # Rotate both clockwise
        kit.continuous_servo[2].throttle = 1  # Rotate both clockwise
    elif word == "DDDD":
        print("Stopping both arms.")
        kit.continuous_servo[1].throttle = 0.1  # Stop right arm
        kit.continuous_servo[2].throttle = 0.1  # Stop left arm

# Create a ClapDetector instance
detector = ClapDetector()

# Set the callback function
detector.set_word_event_callback(on_word_completed)

# Start the display with 'neutral' face initially
display_neutral()

# Start detecting claps
detector.start_detection()

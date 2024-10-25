from clap_module import ClapDetector
from adafruit_servokit import ServoKit
from time import sleep


import RPi.GPIO as GPIO

# Call this at the end of the display code or before running the microphone code
GPIO.cleanup()


# Initialize the ServoKit instance for 16 channels
kit = ServoKit(channels=16)

# Define the callback function that will be triggered when a word is detected
def on_word_completed(word):
    print(f"Word Detected: {word}")

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
        kit.continuous_servo[2].throttle = 1  # clockwise rotation
    elif word == "DSDD":
        print("Stoping left arm.")
        kit.continuous_servo[2].throttle = 0.1  # Stop left arm
    elif word == "DDDS":
        print("Rotating both arms clockwise.")
        kit.continuous_servo[1].throttle = 1  # Counter-clockwise rotation
        kit.continuous_servo[2].throttle = -1  # Counter-clockwise rotation
    elif word == "DDSD":
        print("Rotating both arms.")
        kit.continuous_servo[1].throttle = 1  # Counter-clockwise rotation
        kit.continuous_servo[2].throttle = 1  # Counter-clockwise rotation
    elif word == "DDDD":
        print("Stopping both arms.")
        kit.continuous_servo[1].throttle = 0.1  # Counter-clockwise rotation
        kit.continuous_servo[2].throttle = 0.1  # Counter-clockwise rotation


# Create a ClapDetector instance
detector = ClapDetector()

# Set the callback function
detector.set_word_event_callback(on_word_completed)

# Start detecting claps
detector.start_detection()


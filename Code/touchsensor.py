import time

from adafruit_servokit import ServoKit
import multiprocessing

import importlib.util
try:
    importlib.util.find_spec('RPi.GPIO')
    import RPi.GPIO as GPIO
except ImportError:
    """
    import FakeRPi.GPIO as GPIO
    OR
    import FakeRPi.RPiO as RPiO
    """
	
    import FakeRPi.GPIO as GPIO

touch_pin = 17
vibration_pin = 22

# Set up pins
GPIO.setmode(GPIO.BCM)
GPIO.setup(touch_pin, GPIO.IN)
GPIO.setup(vibration_pin, GPIO.IN)

def check_sensor():
    previous_state = 1
    current_state = 0
    while True:
        if (GPIO.input(touch_pin) == GPIO.HIGH):
            print("TOUCH, I REMEMBER TOUCH")
        if GPIO.input(vibration_pin) == 1:
            print("SHAKINGGGG")
        time.sleep(0.05)

if __name__ == '__main__':
    p1 = multiprocessing.Process(target=check_sensor, name='p1')
    p1.start()
    while True:
        time.sleep(0.5)

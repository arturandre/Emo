from time import sleep
from adafruit_servokit import ServoKit

kit = ServoKit(channels=16)

# Tests with standard servos
# print("Tests with standard servos")
# print("angle 180")
# kit.servo[0].angle = 180
# sleep(3)
# print("angle 0")
# kit.servo[0].angle = 0
# sleep(3)
# Tests with continuous servos
print("Tests with continuous servos")
print("angle 180")
#for i in range(180):
kit.continuous_servo[1].throttle = 0.1
kit.continuous_servo[2].throttle = 0.1
kit.servo[0].angle = 0


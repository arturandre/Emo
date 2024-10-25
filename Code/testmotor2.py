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

import time
from board import SCL, SDA
from adafruit_servokit import ServoKit
import multiprocessing


import os

import os
import sys 
import time
import logging
import spidev as SPI
sys.path.append("..")
from lib import LCD_2inch

from random import randint

touch_pin = 17
vibration_pin = 22



# Set up pins
GPIO.setmode(GPIO.BCM)
GPIO.setup(touch_pin, GPIO.IN)
GPIO.setup(vibration_pin, GPIO.IN)

# Raspberry Pi pin configuration for LCD:
RST = 27
DC = 25
BL = 18
bus = 0 
device = 0 

kit=ServoKit(channels=16)

#Declare Servos
servoR = kit.servo[5]#Reference at 0
servoL = kit.servo[11]#Reference at 180
servoB = kit.servo[13]#Reference at 90


q = multiprocessing.Queue()
event = multiprocessing.Event()

def servoMed():
    servoR.angle = 90
    servoL.angle = 90
    servoB.angle = 90

def servoDown():
    servoR.angle = 0
    servoL.angle = 180
    servoB.angle = 90

def baserotate(reference,change,timedelay):
    for i in range(reference,reference+change,1):
        servoB.angle = i
        time.sleep(timedelay)
    for j in range(reference+change, reference-change,-1):
        servoB.angle = j
        time.sleep(timedelay)
    for k in range(reference-change, reference,1):
        servoB.angle = k
        time.sleep(timedelay)
def HandDownToUp(start,end,timedelay):
	for i,j in zip(range(0+start,end,1),range((180-start),(180-end),-1)):
		servoR.angle = i
		servoL.angle = j
		time.sleep(timedelay)

def HandUpToDown(start,end,timedelay):
	for i,j in zip(range(0+start,end,-1),range((180-start),(180-end),1)):
		servoR.angle = i
		servoL.angle = j
		time.sleep(timedelay)

def rotate(start,end,timedelay):
    if start<end:
        HandDownToUp(start,end,timedelay)
        HandUpToDown(end,start,timedelay)
    else:
        HandUpToDown(end,start,timedelay)
        HandDownToUp(start,end,timedelay)

def happy():
    servoMed()
    for n in range(5):
        for i in range(0, 120):
            if i <= 30:
                servoR.angle = 90 + i #at 120
                servoL.angle = 90 - i #at 60
                servoB.angle = 90 - i
            if (i > 30 and i <=90):
                servoR.angle = 150 - i #at 60
                servoL.angle = i + 30 #at 120
                servoB.angle = i + 30
            if i>90:
                servoR.angle = i - 30 #at 90
                servoL.angle = 210 - i #at 90
                servoB.angle = 210 - i
            time.sleep(0.004)
def angry():
    for i in range(5):
        baserotate(90,randint(0,30),0.01)
def angry2():
    servoMed()
    for i in range(90):
        servoR.angle = 90-i
        servoL.angle = i+90
        servoB.angle = 90 - randint(-12,12)
        time.sleep(0.02)

def sad():
    servoDown()
    for i in range(0,60):
        if i<=15:
            servoB.angle = 90 - i
        if (i>15 and i<=45):
            servoB.angle = 60+i
        if(i>45):
            servoB.angle = 150 - i
        time.sleep(0.09)

def excited():
    servoDown()
    for i in range(0,120):
        if i<=30:
            servoB.angle = 90 - i #at 60
        if (i>30 and i<=90):
            servoB.angle = i + 30 #at 120
        if(i>90):
            servoB.angle = 210 - i
        time.sleep(0.01)

def blink():
    servoR.angle = 0
    servoL.angle = 180
    servoB.angle = 90

def bootup():
    show('bootup3',1)
    for i in range(1):
        p2 = multiprocessing.Process(target=show,args=('blink2',3))
        p3 = multiprocessing.Process(target=rotate,args=(0,150,0.005))
        p4 = multiprocessing.Process(target=baserotate,args=(90,45,0.01))
        p2.start()
        p3.start()
        p4.start()
        p4.join()
        p2.join()
        p3.join()

if __name__ == '__main__':
    bootup()
    while True:
        p6 = multiprocessing.Process(target=baserotate,args=(90,60,0.02),name='p6')
        p6.start()
        p6.join()

import time
from board import SCL, SDA
import busio
#from adafruit_servokit import ServoKit
import multiprocessing

import RPi.GPIO as GPIO
import os

import os
import sys 
import time
import logging
import spidev as SPI
sys.path.append("..")
from lib import LCD_2inch
from PIL import Image,ImageDraw,ImageFont

from random import randint

#touch_pin = 17
#vibration_pin = 22



# Set up pins
GPIO.setmode(GPIO.BCM)
#GPIO.setup(touch_pin, GPIO.IN)
#GPIO.setup(vibration_pin, GPIO.IN)

# Raspberry Pi pin configuration for LCD:
RST = 27
DC = 25
BL = 18
bus = 0 
device = 0 # CS -> GPIO8 = CE0_N 

frame_count = {
  'player': 10,
  'cabana': 4,
  'slime': 10, 'blink':39, 'happy':60, 'sad':47,
  'dizzy':67,'excited':24,'neutral':61,'happy2':20,
  'angry':20,'happy3':26,'bootup3':124,'blink2':20}

emotion = ['angry','sad','excited']

normal = ['neutral','blink2']

disp = LCD_2inch.LCD_2inch()
disp.Init()

def show(emotion,count):
    i = 0
    while (count < 0) or (i < count):
        if count > 0:
             i += 1
        try:
            for i in range(frame_count[emotion]):
                image = Image.open('/home/pi/Emo/Code/emotions/'+emotion+'/frame'+str(i)+'.png')
                disp.ShowImage(image)
        except IOError as e:
            logging.info(e)
        except KeyboardInterrupt:
            disp.module_exit()
            GPIO.cleanup()
            logging.info("quit:")
            exit()

if __name__ == '__main__':
    show('neutral',-1)

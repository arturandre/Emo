import threading
import logging
from lib import LCD_2inch
from PIL import Image
import time

# Frame counts for various emotions or animations
frame_count = {
  'player': 10, 'cabana': 4, 'slime': 10, 'blink': 39, 'happy': 45,
  'sad': 47, 'dizzy': 67, 'excited': 24, 'neutral': 61, 'happy2': 20,
  'angry': 20, 'happy3': 26, 'bootup3': 124, 'blink2': 20
}

class DisplayControl:
    def __init__(self):
        """Initialize the LCD display and variables for controlling animations"""
        self.disp = LCD_2inch.LCD_2inch()
        self.disp.Init()
        self.image_dir = '/home/pi/Emo/Code/emotions/'
        self.current_emotion = None
        self.animation_thread = None
        self.stop_animation_flag = False
    
    def show(self, emotion, count=-1, stop_now=False):
        """
        Display the emotion animation on the LCD screen in a separate thread.

        :param emotion: Emotion name (string)
        :param count: How many times to loop through the frames (-1 for infinite)
        """
        # Stop the current animation if one is running
        if self.animation_thread and self.animation_thread.is_alive():
            self.stop_animation(stop_now=stop_now)

        # Start a new animation in a background thread
        self.stop_animation_flag = False
        self.stop_now_animation_flag = False
        self.current_emotion = emotion
        self.animation_thread = threading.Thread(target=self._play_animation, args=(emotion, count))
        self.animation_thread.start()

    def stop_animation(self, stop_now=False):
        """Set the flag to stop the current animation and wait for the thread to finish"""
        if stop_now:
            self.stop_now_animation_flag = True
        else:
            self.stop_animation_flag = True
        if self.animation_thread:
            self.animation_thread.join()

    def _play_animation(self, emotion, count):
        """Private function to play an emotion animation frame by frame"""
        i = 0
        while (count < 0) or (i < count):
            if count > 0:
                i += 1
            try:
                for j in range(frame_count[emotion]):
                    if self.stop_now_animation_flag:
                        return  # Stop the animation if flagged
                    image = Image.open(f'{self.image_dir}{emotion}/frame{j}.png')
                    self.disp.ShowImage(image)
                if self.stop_animation_flag:
                    return  # Stop the animation if flagged
            except IOError as e:
                logging.error(f"Error showing emotion {emotion}: {e}")
            except KeyboardInterrupt:
                self.disp.module_exit()
                logging.info("Program interrupted, exiting.")
                exit()

    def clear(self):
        """Clear the display"""
        self.disp.clear()

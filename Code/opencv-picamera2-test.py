# This might help: https://docs.google.com/document/d/17K-mN-Tv4eGpvWZHRGH0Bb216cMyeg-sc98Mp9xlYLM/edit?usp=sharing


from picamera2 import Picamera2

picam2 = Picamera2()

#picam2.start_and_capture_file("test.jpg", show_preview=False)

start = picam2.start()
frame = picam2.capture_array() # This will be a numpy array
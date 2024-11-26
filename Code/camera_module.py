from time import sleep
import time
import cv2
import numpy as np
import subprocess
from queue import Queue
import threading
from tflite_runtime.interpreter import Interpreter

class CameraModule:
    def __init__(self,
                 callback=None,
                 video_source=0,
                 show_gui=False,
                 libcamera=False,
                 vid=False,
                 debug=False,
                 use_mpipe=False):
        """
        Initializes the camera module.
        
        Args:
            callback (function): A callback function to handle arm state changes.
            video_source (int or str): Video source (camera index or video file path).
            show_gui (bool): Whether to show the GUI for visual feedback.
            libcamera (bool): Whether to use libcamera on Raspberry Pi.
            debug (bool): Whether to enable debug mode.
            use_mpipe (bool): Whether to use MediaPipe for arm detection.
        """
        self.callback = callback
        self.video_source = video_source
        self.show_gui = show_gui
        self.libcamera = libcamera
        self.vid = vid
        self.debug = debug
        self.cap = None
        self.frame_width = 640
        self.frame_height = 480
        self.frame_size = int(self.frame_width * self.frame_height * 1.5)  # For YUV420 format in libcamera
        self.stop_signal = False
        self.shm_file = '/dev/shm/last_frame.jpg'
        self.frame_queue = Queue(maxsize=1)  # We only want the latest frame, so maxsize is set to 1

        # Initialize MoveNet TFLite model
        self.interpreter = Interpreter(model_path="/home/pi/Emo/Code/models/pose/movenet_singlepose_lightning_int8.tflite")
        self.interpreter.allocate_tensors()
        self.input_details = self.interpreter.get_input_details()
        self.output_details = self.interpreter.get_output_details()

    def resize_with_padding(self, frame, target_size=192):
        # Get the original dimensions
        h, w = frame.shape[:2]

        # Calculate the scaling factor
        scale = target_size / max(h, w)

        # Resize the frame to maintain aspect ratio
        new_w, new_h = int(w * scale), int(h * scale)
        resized_frame = cv2.resize(frame, (new_w, new_h))

        # Create a new square image with the target size and fill it with black (or other color if needed)
        padded_frame = np.zeros((target_size, target_size, 3), dtype=np.uint8)

        # Calculate padding
        pad_top = (target_size - new_h) // 2
        pad_bottom = target_size - new_h - pad_top
        pad_left = (target_size - new_w) // 2
        pad_right = target_size - new_w - pad_left

        # Place the resized image in the center of the padded frame
        padded_frame[pad_top:pad_top+new_h, pad_left:pad_left+new_w] = resized_frame

        return padded_frame

    def _detect_arm_state_movenet(self, frame):
        """Detect arm state using MoveNet TFLite model."""
        # Resize frame to model's expected input shape
        #frame_resized = cv2.resize(frame, (192, 192))
        frame_resized = self.resize_with_padding(frame, target_size=192) # Square images without losing aspect ratio
        input_data = np.expand_dims(frame_resized, axis=0).astype(np.int32)  # Adjust dtype if needed

        # Set the input tensor and run inference
        self.interpreter.set_tensor(self.input_details[0]['index'], input_data)
        self.interpreter.invoke()

        # Get keypoints and scale back to original frame dimensions
        keypoints = self.interpreter.get_tensor(self.output_details[0]['index'])
        height, width, _ = frame.shape
        keypoints[0, 0, :, 0] *= height  # y-coordinates
        keypoints[0, 0, :, 1] *= width   # x-coordinates

        # Extract relevant landmarks for arm position detection
        left_shoulder = keypoints[0, 0, 5]  # Adjust index based on model
        left_elbow = keypoints[0, 0, 7]
        left_wrist = keypoints[0, 0, 9]
        right_shoulder = keypoints[0, 0, 6]
        right_elbow = keypoints[0, 0, 8]
        right_wrist = keypoints[0, 0, 10]

        # Determine if arms are up based on wrist and shoulder y-coordinates
        left_up = left_wrist[0] < left_shoulder[0]
        right_up = right_wrist[0] < right_shoulder[0]

        if left_up and right_up:
            return "both_arms_up"
        elif right_up:
            return "right_arm_up"
        elif left_up:
            return "left_arm_up"
        else:
            return "both_arms_down"


    def start(self):
        """Start the camera module to detect raised arms."""
        if self.libcamera or self.vid:
            self._start_libcamera()
        else:
            from picamera2 import Picamera2
            self.picam2 = Picamera2()
            # No display nor preview
            # RGB888 = OpenCV BGR expected format
            picam2_config = self.picam2.create_still_configuration(
                main={"size": (320,240), "format": "RGB888"}, 
                queue=False # Only the current frame is available (no queue)
                )
            print(f"picam2_config: {picam2_config}")
            self.picam2.align_configuration(picam2_config)
            self.picam2.start()
        self._process_frames_from_queue()

    def _frame_reader_libcamera(self):
        """Reads frames from libcamera and puts the latest frame in the queue."""
        while not self.stop_signal:
            raw_frame = self.process.stdout.read(self.frame_size)
            if len(raw_frame) != self.frame_size:
                print("Incomplete frame received or stream ended.")
                break

            yuv_frame = np.frombuffer(raw_frame, dtype=np.uint8).reshape((int(self.frame_height * 1.5), self.frame_width))
            frame = cv2.cvtColor(yuv_frame, cv2.COLOR_YUV2BGR_I420)

            # If the queue is full, remove the oldest frame and insert the latest
            if not self.frame_queue.full():
                self.frame_queue.put(frame)
            else:
                self.frame_queue.get()  # Remove the old frame
                self.frame_queue.put(frame)  # Insert the new frame

    def _start_libcamera(self):
        """Start video capture using libcamera on Raspberry Pi."""
        if self.vid:
            libcamera_command = [
                'libcamera-vid',
                '--codec', 'yuv420',
                '--width', f'{self.frame_width}',
                '--height', f'{self.frame_height}',
                '--timeout', '0',
                '--framerate', '4',
                '--inline',
                '-o', '-'
            ]
            print(f'libcamera_command: {" ".join(libcamera_command)}')
        elif self.libcamera:
            libcamera_command = [
                'libcamera-still',
                '--width', f'{self.frame_width}',
                '--height', f'{self.frame_height}',
                '--timeout', '0',
                '--timelapse', '100',
                '-o', self.shm_file
            ]
            print(f'libcamera_command: {" ".join(libcamera_command)}')
        try:
            self.process = subprocess.Popen(libcamera_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if self.vid:
                frame_reader_thread = threading.Thread(target=self._frame_reader_libcamera)
                frame_reader_thread.start()
                print("Started libcamera-vid writing to PIPE.")
            elif self.libcamera:
                print("Started libcamera-still writing to shared memory.")
            else:
                print("Picam2")

            # Process frames as they are added to the queue
            self._process_frames_from_queue()

        except subprocess.CalledProcessError as e:
            print(f"An error occurred: {e}")

    def read_latest_frame(self):
        """Reads the latest frame from shared memory file."""
        try:
            # Read the latest frame from /dev/shm
            frame = None
            if self.vid:
                if not self.frame_queue.empty():
                    frame = self.frame_queue.get()
            elif self.libcamera:
                frame = cv2.imread(self.shm_file)
            else:
                frame = self.picam2.capture_array() # This will be a numpy array
            if frame is None:
                print("Failed to read frame.")
                return None
            return frame
        except Exception as e:
            print(f"Error reading frame: {e}")
            return None

    def _process_frames_from_queue(self):
        """Processes frames periodically, pulling only the latest one from /dev/shm."""
        while not self.stop_signal:
            start_time = time.time()

            frame = self.read_latest_frame()
            if frame is not None:
                frame = frame[:,:,:3]
                #frame = np.transpose(frame, [1,0,2])
                if frame is not None:
                    self._process_frame(frame)

            end_time = time.time()
            if self.debug:
                print(f"_process_frames_from_queue duration: {end_time - start_time}")
            time.sleep(0.1)  # Control processing rate

    def _process_frame(self, frame):
        """Process each frame, detect arm positions, and trigger callback."""

        #frame = frame.T
        frame = cv2.resize(frame, (192, 192))
        frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
        cv2.imwrite('/dev/shm/last_frame_debug.jpg', frame)
        

        arm_state = self._detect_arm_state_movenet(frame)

        if arm_state and self.callback:
            self.callback(arm_state)

        if self.show_gui:
            cv2.imshow("Arm Detection", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                self.stop()

  
    def stop(self):
        """Stop the camera and close resources."""
        self.stop_signal = True
        if self.cap:
            self.cap.release()
        cv2.destroyAllWindows()

# Ensure the camera only starts when run as a standalone script, not when imported as a module.
if __name__ == "__main__":
    def arm_callback(state):
        print(f"Arm state detected: {state}")

    # Example usage of the CameraModule
    camera_module = CameraModule(
        callback=arm_callback,
        video_source=0, show_gui=True, use_mpipe=False,
        libcamera=True,
        vid=False
        )
    camera_module.start()

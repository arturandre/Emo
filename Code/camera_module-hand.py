from time import sleep
import cv2
import mediapipe as mp
import numpy as np
import threading
from queue import Queue
import subprocess

# Initialize MediaPipe holistic model
mp_holistic = mp.solutions.holistic

# Load Haar Cascade for face detection
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

# Queue for storing frames
frame_queue = Queue(maxsize=1)

# Function to detect the face position
def detect_face(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.3, 5)
    if len(faces) > 0:
        x, y, w, h = faces[0]
        face_center = (x + w // 2, y + h // 2)
        return face_center, (x, y, w, h)
    return None, None

class CameraModule:
    def __init__(self, callback=None, video_source=0, show_gui=False, use_mpipe=False):
        """
        Initializes the camera module.
        
        Args:
            callback (function): A callback function to handle arm state changes.
            video_source (int or str): Video source (camera index or file path).
            show_gui (bool): Whether to show the GUI for visual feedback.
            use_mpipe (bool): Whether to use MediaPipe for arm detection.
        """
        self.callback = callback
        self.video_source = video_source
        self.show_gui = show_gui
        self.use_mpipe = use_mpipe
        self.holistic_model = None
        self.cap = None
        self.frame_width, self.frame_height = 320, 240
        self.stop_signal = False

        if self.use_mpipe:
            self.holistic_model = mp_holistic.Holistic(min_detection_confidence=0.5, min_tracking_confidence=0.5)

    def start(self):
        """Start the camera module to detect raised arms."""
        self.cap = cv2.VideoCapture(self.video_source)
        if not self.cap.isOpened():
            print("Failed to open the video source.")
            return

        # Start a thread for reading frames and putting them in the queue
        frame_reader_thread = threading.Thread(target=self._frame_reader)
        frame_reader_thread.start()

        # Process frames as they are added to the queue
        self._process_frames_from_queue()

    def _frame_reader(self):
        """Reads frames from OpenCV and adds them to the queue."""
        while self.cap.isOpened() and not self.stop_signal:
            ret, frame = self.cap.read()
            if not ret:
                break

            frame = cv2.resize(frame, (self.frame_width, self.frame_height))
            if not frame_queue.full():
                frame_queue.put(frame)
            else:
                frame_queue.get()
                frame_queue.put(frame)

    def _process_frames_from_queue(self):
        """Processes the latest frame from the queue."""
        while not self.stop_signal:
            if not frame_queue.empty():
                frame = frame_queue.get()
                self._process_frame(frame)
            sleep(0.1)

    def _process_frame(self, frame):
        """Process each frame, detect arm positions, and trigger callback."""
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        if self.use_mpipe:
            arm_state = self._detect_arm_state_mediapipe(frame, frame_rgb)
        else:
            arm_state = self._detect_arm_state_opencv(frame)

        if arm_state and self.callback:
            self.callback(arm_state)

        if self.show_gui:
            cv2.imshow("Arm Detection", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                self.stop()

    def _detect_arm_state_mediapipe(self, frame, frame_rgb):
        """Detect the state of arms using MediaPipe and the head position."""
        results = self.holistic_model.process(frame_rgb)
        face_center, face_box = detect_face(frame)

        if face_center and results.pose_landmarks:
            # Define the head height as the y-coordinate of the face center detected by Haar cascade
            head_y = face_center[1]
            left_wrist = results.pose_landmarks.landmark[mp_holistic.PoseLandmark.LEFT_WRIST]
            right_wrist = results.pose_landmarks.landmark[mp_holistic.PoseLandmark.RIGHT_WRIST]

            # Convert normalized y-coordinates to pixel values for comparison
            left_wrist_y = int(left_wrist.y * self.frame_height)
            right_wrist_y = int(right_wrist.y * self.frame_height)

            # Determine if hands are raised above the detected head
            if left_wrist_y < head_y and right_wrist_y < head_y:
                return "both_arms_up"
            elif right_wrist_y < head_y:
                return "right_arm_up"
            elif left_wrist_y < head_y:
                return "left_arm_up"
            else:
                return "both_arms_down"
        return None

    def _detect_arm_state_opencv(self, frame):
        """Detect the state of arms using OpenCV face detection."""
        face_center, face_box = detect_face(frame)

        if face_center:
            # Here, check_left_right_arms_up can contain logic to determine arm position based on the frame
            left_wrist_up, right_wrist_up, watershed_result, markers, markers_vis = check_left_right_arms_up(
                frame, face_center, show=self.show_gui
            )

            if self.show_gui:
                cv2.imshow("Watershed Result", watershed_result)
                cv2.imshow("Markers", markers_vis)

            if left_wrist_up and right_wrist_up:
                return "both_arms_up"
            elif right_wrist_up:
                return "right_arm_up"
            elif left_wrist_up:
                return "left_arm_up"
            else:
                return "both_arms_down"

    def stop(self):
        """Stop the camera and close resources."""
        self.stop_signal = True
        if self.cap:
            self.cap.release()
        if self.holistic_model:
            self.holistic_model.close()
        cv2.destroyAllWindows()

# Main script to run the module
if __name__ == "__main__":
    def arm_callback(state):
        print(f"Arm state detected: {state}")

    camera_module = CameraModule(callback=arm_callback, video_source=0, show_gui=True, use_mpipe=True)
    camera_module.start()

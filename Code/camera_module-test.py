from time import sleep
import cv2
import mediapipe as mp
import numpy as np
import subprocess
from queue import Queue
import threading

# Queue to store the latest frame
frame_queue = Queue(maxsize=1)  # We only want the latest frame, so maxsize is set to 1

# MediaPipe holistic model
mp_holistic = mp.solutions.holistic

# Load Haar Cascade for face detection
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
last_state = None
histeresys_markers1 = []
histeresys_markers2 = []
histeresys_size = 3
# last_state table:
# None -> Not initialized
# 0 -> Both arms down
# 1 -> Left arm up
# 2 -> Right arm up
# 3 -> Both arms up


def detect_face(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.3, 5)
    
    if len(faces) > 0:
        x, y, w, h = faces[0]
        face_center = (x + w // 2, y + h // 2)
        return face_center, (x, y, w, h)
    return None, None

def apply_histeresys(values, mask_values, histeresys_buffer, buffer_size):
    """
    values: the array of markers
    mask_values: Which markers are expected in values
    histeresys_buffer: list to store previous 'values'
    buffer_size: How many previous 'values' should be stored.
    """
    if len(histeresys_buffer) < buffer_size:
        # Buffer need to be filled before apply histeresys
        histeresys_buffer.append(values)
        return values
    else:
        del histeresys_buffer[0]
        histeresys_buffer.append(values)
        votes = np.zeros((list(values.shape)+[len(mask_values)]))
        for j, mask_type in enumerate(mask_values): # Bacground, face, torso
            for i in range(histeresys_size):
                votes[:,:,j] += (histeresys_buffer[i] == mask_type)
        # Get the indices of the most common mask type at each pixel
        most_common_indices = votes.argmax(axis=-1)

        # Replace the indices with the corresponding mask_values
        final_values = np.take(mask_values, most_common_indices)
    return final_values

def check_left_right_arms_up(frame, face_center, show=False):
    frame_copy = None
    markers = None
    markers_vis = None
    left_up = False
    right_up = False

    # Convert the frame to grayscale
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # Create markers for the Watershed algorithm
    markers = np.zeros(gray.shape, dtype=np.int32)
    

    border_thickness = 10
    # Step 1: Mark the borders of the image as background (Marker 1)
    markers[0:border_thickness, :] = 1  # Top border
    markers[-border_thickness:-1, :] = 1  # Bottom border
    markers[:, 0:border_thickness] = 1  # Left border
    markers[:, -border_thickness:-1] = 1  # Right border

    # Step 2: Mark the face region (Marker 2)
    face_radius = 10  # Radius for the face region
    cv2.circle(markers, face_center, face_radius, 2, -1)  # Marker 2 for the face seed

    # Step 3: Mark the torso region (Marker 3)
    torso_center = (face_center[0], face_center[1] + 100)  # Roughly 100 pixels below the face
    cv2.circle(markers, torso_center, 30, 3, -1)  # Marker 3 for the torso seed

    # Apply the Watershed algorithm
    
    markers_1 = cv2.watershed(frame, markers.copy())
    markers_1 = apply_histeresys(markers_1, [-1, 1,2,3], histeresys_markers1, histeresys_size)


    # Step 4: Find the bounding box around the torso region (Marker 3)
    torso_mask = (markers_1 == 3).astype(np.uint8)
    contours, _ = cv2.findContours(torso_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    face_mask = (markers_1 == 2).astype(np.uint8)
    contours_face, _ = cv2.findContours(face_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if show:
        frame_copy = frame.copy()
        frame_copy[markers_1 == -1] = [0, 0, 255]  # Mark boundaries in red
        #frame_copy[markers_1 == 1] = [128, 128, 0]  # Mark background region in dark blue
        frame_copy[markers_1 == 2] = [255, 0, 0]  # Mark face region in red
        frame_copy[markers_1 == 3] = [0, 255, 0]  # Mark torso region in green

    # return frame_copy, markers, markers_vis
    if len(contours) > 0:
        # Get the bounding box of the largest contour (the torso)
        x_torso, y_torso, w_torso, h_torso = cv2.boundingRect(contours[0])
        x_face, y_face, w_face, h_face = cv2.boundingRect(contours_face[0])
        markers[y_face:y_face+h_face,x_face-1] = 1
        markers[y_face:y_face+h_face,x_face+w_face+1] = 1


        # Step 5: Find the lateral points of the torso
        # These are the leftmost and rightmost x-coordinates in the torso region, along with their corresponding y-coordinates
        torso_pixels = np.where(torso_mask == 1)
        leftmost_point = (np.min(torso_pixels[1]), torso_pixels[0][np.argmin(torso_pixels[1])])  # (min_x, corresponding_y)
        rightmost_point = (np.max(torso_pixels[1]), torso_pixels[0][np.argmax(torso_pixels[1])])  # (max_x, corresponding_y)

        # Draw the bounding box around the torso on the original frame

        # Step 6: Add arm markers slightly to the left and right of the torso's lateral points
        arm_offset = 20  # Offset from the lateral points
        if leftmost_point[0] > arm_offset:  # Make sure we stay inside the image boundaries
            #markers[leftmost_point[1]+5:leftmost_point[1]+15, (leftmost_point[0] - arm_offset):leftmost_point[0]] = 4  # Left arm marker (Marker 4)
            #begin_left_arm = [leftmost_point[0]-arm_offset,leftmost_point[1]+arm_offset]
            begin_left_arm = [leftmost_point[0]-arm_offset,int(y_torso+(h_torso/2))]
            cv2.circle(markers, begin_left_arm, 10, 4, -1)
        if rightmost_point[0] + arm_offset < frame.shape[1]:
            #markers[rightmost_point[1]:rightmost_point[1]+5, rightmost_point[0]:(rightmost_point[0] + arm_offset)] = 5  # Right arm marker (Marker 5)
            #begin_right_arm = [rightmost_point[0]+arm_offset,rightmost_point[1]-arm_offset]
            begin_right_arm = [rightmost_point[0]+arm_offset,int(y_torso+(h_torso/2))]
            cv2.circle(markers, begin_right_arm, 10, 5, -1)


        # Step 7: Apply the Watershed algorithm again with the arm markers
        markers_2 = cv2.watershed(frame, markers.copy())
        markers_2 = apply_histeresys(markers_2, [-1,1,2,3, 4,5], histeresys_markers2, histeresys_size)
        
        if show:
            cv2.rectangle(
                frame_copy,
                (x_torso, y_torso),
                (x_torso + w_torso, y_torso + h_torso),
                (0, 255, 255), 2)  # Yellow box for the torso
            # Visualize the markers before Watershed
            markers_vis = np.zeros_like(frame)

            # Visualize the new markers for arms
            markers_vis[markers == 1] = [255, 255, 255]  # White for background
            markers_vis[markers == 2] = [255, 0, 0]  # Red for face
            markers_vis[markers == 3] = [0, 255, 0]  # Green for torso

            markers_vis[markers == 4] = [128, 0, 255]  # Blue for left arm seed
            markers_vis[markers == 5] = [0, 128, 128]  # Yellow for right arm seed

            frame_copy[markers_2 == 4] = [128, 0, 255]  # Mark left arm in blue
            frame_copy[markers_2 == 5] = [0, 128, 128]  # Mark right arm in yellow
        
        # Step 8: Find the highest arms points
        # Arms reversed (mirroring of the camera?)
        left_arm_mask = (markers_2 == 5).astype(np.uint8)
        right_arm_mask = (markers_2 == 4).astype(np.uint8)
        
        left_arm_pixels = np.where(left_arm_mask == 1)
        right_arm_pixels = np.where(right_arm_mask == 1)
        if len(left_arm_pixels[0]) > 0:
            topmost_left_point = np.min(left_arm_pixels[0])
        else:
            topmost_left_point = float('inf')

        if len(right_arm_pixels[0]) > 0:
            topmost_right_point = np.min(right_arm_pixels[0])
        else:
            topmost_right_point = float('inf')
        #topmost_left_point = (np.min(left_arm_pixels[0]), torso_pixels[0][np.argmin(torso_pixels[1])])  # (min_x, corresponding_y)
        #rightmost_point = (np.max(torso_pixels[1]), torso_pixels[0][np.argmax(torso_pixels[1])])  # (max_x, corresponding_y)

        # Step 6: Check if the face bounding box is inside the torso bounding box
        left_up = (topmost_left_point <= y_face)
        right_up = (topmost_left_point <= y_face)
        if show:
            if left_up and right_up:
                cv2.putText(frame_copy, "Both arms are UP", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            elif right_up:
                # The face is inside the torso bounding box: likely the arms are up
                cv2.putText(frame_copy, "Right arm is UP", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            elif left_up:
                cv2.putText(frame_copy, "Left arm is UP", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            else:
                cv2.putText(frame_copy, "Both arms are DOWN", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

    return left_up, right_up, frame_copy, markers, markers_vis


class CameraModule:
    def __init__(self,
                 callback=None,
                 video_source=0,
                 show_gui=False,
                 libcamera=False,
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
        self.debug = debug
        self.use_mpipe = use_mpipe
        self.holistic_model = None
        self.cap = None
        self.frame_width = 320
        self.frame_height = 240
        self.frame_size = int(self.frame_width * self.frame_height * 1.5)  # For YUV420 format in libcamera
        self.stop_signal = False

    def start(self):
        """Start the camera module to detect raised arms."""
        if self.use_mpipe:
            self.holistic_model = mp_holistic.Holistic(min_detection_confidence=0.5, min_tracking_confidence=0.5)
        
        if self.libcamera:
            self._start_libcamera()
        else:
            self._start_opencv_camera()

    def _start_libcamera(self):
        """Start video capture using libcamera on Raspberry Pi."""
        libcamera_command = [
            'libcamera-vid',
            '--codec', 'yuv420',
            '--width', f'{self.frame_width}',
            '--height', f'{self.frame_height}',
            '--timeout', '0',
            '--framerate', '2',
            '--inline',
            '-o', '-'
        ]
        try:
            self.process = subprocess.Popen(libcamera_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            print("libcamera started.")

            # Start a thread for reading frames and putting them in the queue
            frame_reader_thread = threading.Thread(target=self._frame_reader_libcamera)
            frame_reader_thread.start()

            # Process frames as they are added to the queue
            self._process_frames_from_queue()

        except subprocess.CalledProcessError as e:
            print(f"An error occurred: {e}")

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
            if not frame_queue.full():
                frame_queue.put(frame)
            else:
                frame_queue.get()  # Remove the old frame
                frame_queue.put(frame)  # Insert the new frame

    def _start_opencv_camera(self):
        """Start video capture using OpenCV."""
        self.cap = cv2.VideoCapture(self.video_source)
        if not self.cap.isOpened():
            print("Failed to open the video source.")
            return

        # Start a thread for reading frames and putting them in the queue
        frame_reader_thread = threading.Thread(target=self._frame_reader_opencv)
        frame_reader_thread.start()

        # Process frames as they are added to the queue
        self._process_frames_from_queue()

    def _frame_reader_opencv(self):
        """Reads frames from OpenCV and puts the latest frame in the queue."""
        while self.cap.isOpened() and not self.stop_signal:
            ret, frame = self.cap.read()
            if not ret:
                print(f"Stopping _frame_reader_opencv cap.isOpened: {self.cap.isOpened()},  stop_signal: {self.stop_signal}")
                break
            frame = cv2.resize(frame, (self.frame_width, self.frame_height))

            # If the queue is full, remove the oldest frame and insert the latest
            if not frame_queue.full():
                frame_queue.put(frame)
            else:
                frame_queue.get()  # Remove the old frame
                frame_queue.put(frame)  # Insert the new frame

    def _process_frames_from_queue(self):
        """Processes the latest frame from the queue."""
        while not self.stop_signal:
            if not frame_queue.empty():
                frame = frame_queue.get()
                self._process_frame(frame)
            sleep(0.5)

    def _process_frame(self, frame):
        """Process each frame, detect arm positions, and trigger callback."""

        #frame = frame.T
        frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
        cv2.imwrite("rotated.png", frame)
        raise Exception("Rotation saved to rotated.png")

        if self.use_mpipe:
            arm_state = self._detect_arm_state_mediapipe(frame)
        else:
            arm_state = self._detect_arm_state_opencv(frame)

        if arm_state and self.callback:
            self.callback(arm_state)

        if self.show_gui:
            cv2.imshow("Arm Detection", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                self.stop()

    def _detect_arm_state_mediapipe(self, frame):
        """Detect the state of arms using MediaPipe."""
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.holistic_model.process(frame_rgb)

        if results.pose_landmarks:
            left_wrist = results.pose_landmarks.landmark[mp_holistic.PoseLandmark.LEFT_WRIST]
            right_wrist = results.pose_landmarks.landmark[mp_holistic.PoseLandmark.RIGHT_WRIST]
            nose = results.pose_landmarks.landmark[mp_holistic.PoseLandmark.NOSE]

            if left_wrist.y < nose.y and right_wrist.y < nose.y:
                return "both_arms_up"
            elif right_wrist.y < nose.y:
                return "right_arm_up"
            elif left_wrist.y < nose.y:
                return "left_arm_up"
            else:
                return "both_arms_down"
        return None

    def _detect_arm_state_opencv(self, frame):
        """Detect the state of arms using OpenCV (your custom arm detection logic)."""
        face_center, face_box = detect_face(frame)

        if face_center:
            left_wrist_up, right_wrist_up,\
            watershed_result, markers, markers_vis =\
                check_left_right_arms_up(frame, face_center, show=self.show_gui)

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
        if self.libcamera:
            self.process.terminate()
        cv2.destroyAllWindows()

# Ensure the camera only starts when run as a standalone script, not when imported as a module.
if __name__ == "__main__":
    def arm_callback(state):
        print(f"Arm state detected: {state}")

    # Example usage of the CameraModule
    camera_module = CameraModule(callback=arm_callback, video_source=0, show_gui=True, use_mpipe=False, libcamera=True)
    camera_module.start()

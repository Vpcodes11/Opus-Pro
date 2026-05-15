import cv2
import numpy as np
import mediapipe as mp
from mediapipe.python.solutions import face_detection as mp_face_detection
from app.config import TARGET_WIDTH, TARGET_HEIGHT
import os

class FaceTracker:
    def __init__(self):
        self.face_detection = mp_face_detection.FaceDetection(
            model_selection=1, # 0 for close-range (within 2m), 1 for full-range (within 5m)
            min_detection_confidence=0.5
        )

    def get_dynamic_crop_coordinates(self, video_path, start_time, end_time, target_width=1080, target_height=1920):
        """
        Calculates dynamic crop coordinates for the duration of the clip.
        Returns a dictionary mapping timestamps to X-coordinates.
        """
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        src_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        src_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        # Calculate target crop width based on height
        crop_w = int(src_h * (target_width / target_height))
        
        # If the video is already vertical or too narrow, don't crop
        if crop_w >= src_w:
            cap.release()
            return None

        # Sample frames every 0.2 seconds for efficiency (2x speedup)
        sample_interval = 0.2 
        current_t = start_time
        raw_centers = []

        while current_t <= end_time:
            cap.set(cv2.CAP_PROP_POS_MSEC, current_t * 1000)
            ret, frame = cap.read()
            if not ret:
                break
            
            # Convert to RGB for MediaPipe
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.face_detection.process(rgb_frame)
            
            center_x = src_w / 2 # Default to center
            
            if results.detections:
                # Find the largest detection
                largest = max(results.detections, key=lambda d: d.location_data.relative_bounding_box.width * d.location_data.relative_bounding_box.height)
                bbox = largest.location_data.relative_bounding_box
                # MediaPipe returns relative coords (0.0 to 1.0)
                center_x = (bbox.xmin + bbox.width / 2) * src_w
            
            raw_centers.append(center_x)
            current_t += sample_interval

        cap.release()

        if not raw_centers:
            return None

        # --- Smoothing (Weighted Moving Average) ---
        smoothed_centers = []
        window_size = 5 # 0.5 seconds worth of data
        for i in range(len(raw_centers)):
            start_idx = max(0, i - window_size)
            end_idx = min(len(raw_centers), i + window_size + 1)
            window = raw_centers[start_idx:end_idx]
            smoothed_centers.append(np.mean(window))

        # Map back to timestamps
        coord_map = {}
        for i, center in enumerate(smoothed_centers):
            timestamp = start_time + (i * sample_interval)
            
            # Clamp center so the crop box stays within video bounds
            min_center = crop_w / 2
            max_center = src_w - (crop_w / 2)
            clamped_center = max(min_center, min(center, max_center))
            
            # Store the top-left X of the crop box
            top_left_x = int(clamped_center - (crop_w / 2))
            coord_map[round(timestamp, 2)] = top_left_x

        return {
            'crop_w': crop_w,
            'crop_h': src_h,
            'coords': coord_map
        }

tracker = FaceTracker()

import cv2
import mediapipe as mp
import numpy as np

class FaceTracker:
    def __init__(self):
        self.mp_face_detection = mp.solutions.face_detection
        self.face_detection = self.mp_face_detection.FaceDetection(
            model_selection=1, # 0 for short-range, 1 for long-range (podcasts)
            min_detection_confidence=0.5
        )

    def find_best_crop_x(self, video_path, start_time, end_time, target_width=1080, target_height=1920):
        """
        Samples frames from the video and finds the average center X of the face.
        Returns the X coordinate to center the 9:16 crop around.
        """
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        src_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        src_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        # Sample 5-10 frames evenly throughout the clip
        sample_times = np.linspace(start_time, end_time, 10)
        x_centers = []

        for t in sample_times:
            cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
            ret, frame = cap.read()
            if not ret:
                continue
            
            # Convert to RGB for MediaPipe
            results = self.face_detection.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            
            if results.detections:
                # Take the first (largest) face
                bbox = results.detections[0].location_data.relative_bounding_box
                center_x = (bbox.xmin + bbox.width / 2) * src_w
                x_centers.append(center_x)

        cap.release()

        if not x_centers:
            return src_w / 2 # Fallback to center
            
        # Use the median X to avoid jitter from background faces
        avg_x = np.median(x_centers)
        
        # Clamp X so the crop doesn't go out of bounds
        crop_w = int(src_h * (target_width / target_height))
        min_x = crop_w / 2
        max_x = src_w - (crop_w / 2)
        
        return max(min_x, min(avg_x, max_x))

# Singleton instance
tracker = FaceTracker()

import cv2
import numpy as np
import os

class FaceTracker:
    def __init__(self):
        # Load pre-trained face detection cascade from OpenCV
        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        self.face_cascade = cv2.CascadeClassifier(cascade_path)
        if self.face_cascade.empty():
            print("Warning: Could not load Haar Cascade. Face tracking may fail.")

    def find_best_crop_x(self, video_path, start_time, end_time, target_width=1080, target_height=1920):
        """
        Samples frames from the video and finds the average center X of the face using OpenCV.
        """
        cap = cv2.VideoCapture(video_path)
        src_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        src_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        # Sample 10 frames
        sample_times = np.linspace(start_time, end_time, 10)
        x_centers = []

        for t in sample_times:
            cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
            ret, frame = cap.read()
            if not ret:
                continue
            
            # Convert to grayscale for detection
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = self.face_cascade.detectMultiScale(gray, 1.3, 5)
            
            if len(faces) > 0:
                # Find the largest face by area
                largest_face = max(faces, key=lambda f: f[2] * f[3])
                (x, y, w, h) = largest_face
                center_x = x + w / 2
                x_centers.append(center_x)

        cap.release()

        if not x_centers:
            return src_w / 2 # Fallback
            
        # Use median to avoid outliers
        avg_x = np.median(x_centers)
        
        # Clamp
        crop_w = int(src_h * (target_width / target_height))
        if crop_w > src_w:
            return src_w / 2
            
        min_x = crop_w / 2
        max_x = src_w - (crop_w / 2)
        
        return max(min_x, min(avg_x, max_x))

tracker = FaceTracker()

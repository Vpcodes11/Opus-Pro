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

tracker = FaceTracker()

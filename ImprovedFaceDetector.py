# ImprovedFaceDetector.py
import cv2
import face_recognition
import numpy as np
import os
from PIL import Image, ImageEnhance

class ImprovedFaceDetector:
    def __init__(self, known_faces_dir="test_images", similarity_threshold=0.4):
        self.known_faces = []
        self.known_names = []
        self.similarity_threshold = similarity_threshold
        self.load_known_faces(known_faces_dir)

    def load_known_faces(self, directory):
        """Load and encode all known faces from the given directory."""
        if not os.path.exists(directory):
            print(f"⚠️ Directory '{directory}' not found. Creating it now...")
            os.makedirs(directory)
            print("Please add some face images inside the 'test_images' folder (e.g., riya.jpg).")
            return

        for filename in os.listdir(directory):
            if filename.lower().endswith(('.jpg', '.png', '.jpeg')):
                img_path = os.path.join(directory, filename)
                image = face_recognition.load_image_file(img_path)
                encodings = face_recognition.face_encodings(image)
                if len(encodings) > 0:
                    self.known_faces.append(encodings[0])
                    self.known_names.append(os.path.splitext(filename)[0])
                else:
                    print(f"⚠️ No face found in '{filename}' — skipped.")
        print(f"✅ Loaded {len(self.known_faces)} known faces from '{directory}'")

    def enhance_image(self, image):
        """Enhance brightness and contrast for better detection."""
        pil_image = Image.fromarray(image)
        enhancer = ImageEnhance.Contrast(pil_image)
        enhanced = enhancer.enhance(1.5)
        return np.array(enhanced)

    def detect_faces(self, image):
        """Detect and recognize faces in the input image."""
        enhanced = self.enhance_image(image)
        face_locations = face_recognition.face_locations(enhanced)
        face_encodings = face_recognition.face_encodings(enhanced, face_locations)

        face_names = []
        for face_encoding in face_encodings:
            matches = face_recognition.compare_faces(
                self.known_faces, face_encoding, tolerance=self.similarity_threshold
            )
            name = "Unknown"

            if len(self.known_faces) > 0:
                face_distances = face_recognition.face_distance(self.known_faces, face_encoding)
                best_match_index = np.argmin(face_distances)
                if matches[best_match_index]:
                    name = self.known_names[best_match_index]

            face_names.append(name)

        return face_locations, face_names

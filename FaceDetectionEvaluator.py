# FaceDetectionEvaluator.py
# FaceDetectionEvaluator.py
import cv2
import os
from sklearn.metrics import classification_report
from ImprovedFaceDetector import ImprovedFaceDetector

class FaceDetectionEvaluator:
    def __init__(self, detector, test_dir="evaluation_images"):
        self.detector = detector
        self.test_dir = test_dir

    def evaluate(self):
        y_true = []
        y_pred = []

        for filename in os.listdir(self.test_dir):
            if filename.lower().endswith(('.jpg', '.png', '.jpeg')):
                img_path = os.path.join(self.test_dir, filename)
                true_name = filename.split("_")[0]  # assumes 'riya_1.jpg' → 'riya'

                image = cv2.imread(img_path)
                if image is None:
                    print(f"⚠️ Skipping {filename} — could not read image.")
                    continue

                face_locations, face_names = self.detector.detect_faces(image)

                if face_names:
                    pred_name = face_names[0]  # take first detected
                else:
                    pred_name = "Unknown"

                y_true.append(true_name)
                y_pred.append(pred_name)

        # Print classification report
        print("\n📊 Face Recognition Evaluation Report:")
        print(classification_report(y_true, y_pred, zero_division=0))


from ImprovedFaceDetector import ImprovedFaceDetector
from FaceDetectionEvaluator import FaceDetectionEvaluator

# Initialize detector
detector = ImprovedFaceDetector(known_faces_dir="test_images", similarity_threshold=0.4)

# Evaluate on multiple test images
evaluator = FaceDetectionEvaluator(detector, test_dir="test_images")
evaluator.evaluate()
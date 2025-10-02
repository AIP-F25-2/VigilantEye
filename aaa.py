import os
import cv2

face_model = r"C:\Users\bhoom\OneDrive\Desktop\Riya\VigilantEye\VigilantEye\models\opencv_face_detector_uint8.pb"
face_proto = r"C:\Users\bhoom\OneDrive\Desktop\Riya\VigilantEye\VigilantEye\models\opencv_face_detector.pbtxt"

print(os.path.exists(face_model))  # should print True
print(os.path.exists(face_proto))  # should print True

net = cv2.dnn.readNet(face_model, face_proto)
print("Model loaded successfully!")

import cv2
import numpy as np
import os

class DemographicsAnalyzer:
    def __init__(self):
        # Load face detector
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))

        face_model = os.path.join(BASE_DIR, "models", "opencv_face_detector_uint8.pb")
        face_proto = os.path.join(BASE_DIR, "models", "opencv_face_detector.pbtxt")
        self.face_net = cv2.dnn.readNet(face_model, face_proto)

        # Load age and gender models
        age_proto = "models/age_deploy.prototxt"
        age_model = "models/age_net.caffemodel"
        gender_proto = "models/gender_deploy.prototxt"
        gender_model = "models/gender_net.caffemodel"

        self.age_net = cv2.dnn.readNet(age_model, age_proto)
        self.gender_net = cv2.dnn.readNet(gender_model, gender_proto)

        self.MODEL_MEAN_VALUES = (78.4263377603, 87.7689143744, 114.895847746)

        self.age_list = ['(0-2)', '(4-6)', '(8-12)', '(15-20)', 
                         '(25-32)', '(38-43)', '(48-53)', '(60-100)']
        self.gender_list = ['Male', 'Female']

    def analyze(self, image_path):
        frame = cv2.imread(image_path)
        h, w = frame.shape[:2]

        # Detect faces
        blob = cv2.dnn.blobFromImage(frame, 1.0, (300, 300), [104, 117, 123], swapRB=False)
        self.face_net.setInput(blob)
        detections = self.face_net.forward()

        results = []

        for i in range(detections.shape[2]):
            confidence = detections[0, 0, i, 2]
            if confidence > 0.7:
                box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
                (x1, y1, x2, y2) = box.astype(int)

                face = frame[y1:y2, x1:x2]
                if face.size == 0:
                    continue

                blob = cv2.dnn.blobFromImage(face, 1.0, (227, 227), self.MODEL_MEAN_VALUES, swapRB=False)

                # Gender prediction
                self.gender_net.setInput(blob)
                gender_preds = self.gender_net.forward()
                gender = self.gender_list[gender_preds[0].argmax()]

                # Age prediction
                self.age_net.setInput(blob)
                age_preds = self.age_net.forward()
                age = self.age_list[age_preds[0].argmax()]

                label = f"{gender}, {age}"
                results.append((x1, y1, x2, y2, label))

                # Draw box
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                # Put label BELOW the face
                cv2.putText(frame, label, (x1, y2 + 25), cv2.FONT_HERSHEY_SIMPLEX, 
                            0.8, (0, 255, 255), 2, cv2.LINE_AA)

        # Show final image with predictions
        cv2.imshow("Demographics", frame)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

        return results


# ---------- Run ----------
#analyzer = DemographicsAnalyzer()
#results = analyzer.analyze("person.jpg")

#print("Detected faces:")
#for res in results:
 #   print(res)

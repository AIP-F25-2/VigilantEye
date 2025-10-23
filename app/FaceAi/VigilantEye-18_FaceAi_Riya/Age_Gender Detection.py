import os, cv2, numpy as np

AGE_LIST = ['(0-2)','(4-6)','(8-12)','(15-20)','(25-32)','(38-43)','(48-53)','(60-100)']
GENDER_LIST = ['Male','Female']
MODEL_MEAN = (78.4263377603, 87.7689143744, 114.895847746)
AGE_INP_SIZE = (227, 227)

class DemographicsAnalyzer:
    def __init__(self, model_dir="models"):
        self.model_dir = model_dir
        # find face detector pb & pbtxt
        candidates = [
            ("opencv_face_detector_uint8.pb","opencv_face_detector.pbtxt"),
            ("opencv_face_detector.pb","opencv_face_detector.pbtxt"),
            ("opencv_face_detector_uint8.pb","opencv_face_detector.pbtxt")
        ]
        self.face_net = None
        for pb,txt in candidates:
            pbp = os.path.join(model_dir, pb); txtp = os.path.join(model_dir, txt)
            if os.path.exists(pbp) and os.path.exists(txtp):
                self.face_net = cv2.dnn.readNet(pbp, txtp)
                break

        # find age/gender Caffe pairs (try common names)
        def choose_pair(proto_names, model_names):
            for p in proto_names:
                for m in model_names:
                    ppath=os.path.join(model_dir,p); mpath=os.path.join(model_dir,m)
                    if os.path.exists(ppath) and os.path.exists(mpath):
                        return ppath, mpath
            return None, None

        age_proto, age_model = choose_pair(
            ["age_deploy.prototxt","deploy_age.prototxt","age_deploy.prototxt.txt"],
            ["age_net.caffemodel","age_net.caffemodel"]
        )
        gender_proto, gender_model = choose_pair(
            ["gender_deploy.prototxt","deploy_gender.prototxt","gender_deploy.prototxt.txt"],
            ["gender_net.caffemodel","gender_net.caffemodel"]
        )

        if age_proto and age_model:
            self.age_net = cv2.dnn.readNetFromCaffe(age_proto, age_model)
        else:
            self.age_net = None

        if gender_proto and gender_model:
            self.gender_net = cv2.dnn.readNetFromCaffe(gender_proto, gender_model)
        else:
            self.gender_net = None

        if self.face_net is None:
            # fallback to Haar cascade (less accurate)
            self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        else:
            self.face_cascade = None

    def analyze(self, image_path):
        img = cv2.imread(image_path)
        if img is None:
            raise FileNotFoundError(image_path)

        h, w = img.shape[:2]
        faces = []

        if self.face_net is not None:
            blob = cv2.dnn.blobFromImage(img, 1.0, (300,300), (104.0,177.0,123.0))
            self.face_net.setInput(blob)
            detections = self.face_net.forward()
            for i in range(detections.shape[2]):
                conf = float(detections[0,0,i,2])
                if conf > 0.5:
                    x1 = int(detections[0,0,i,3]*w)
                    y1 = int(detections[0,0,i,4]*h)
                    x2 = int(detections[0,0,i,5]*w)
                    y2 = int(detections[0,0,i,6]*h)
                    faces.append((max(0,x1), max(0,y1), min(w,x2)-max(0,x1), min(h,y2)-max(0,y1)))
        else:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            dets = self.face_cascade.detectMultiScale(gray, 1.3, 5)
            faces = [(x,y,w,h) for (x,y,w,h) in dets]

        results = []
        for (x,y,wf,hf) in faces:
            # add some margin
            pad = int(0.2 * min(wf,hf))
            x1 = max(0, x-pad); y1=max(0,y-pad)
            x2 = min(img.shape[1], x+wf+pad); y2=min(img.shape[0], y+hf+pad)
            face = img[y1:y2, x1:x2].copy()
            res = {"face_box":(x1,y1,x2-x1,y2-y1)}

            if self.gender_net is not None:
                blob = cv2.dnn.blobFromImage(face, 1.0, AGE_INP_SIZE, MODEL_MEAN, swapRB=False)
                self.gender_net.setInput(blob)
                g_preds = self.gender_net.forward()
                res["gender"] = GENDER_LIST[int(np.argmax(g_preds))]
                res["gender_score"] = float(np.max(g_preds))
            else:
                res["gender"] = None

            if self.age_net is not None:
                blob = cv2.dnn.blobFromImage(face, 1.0, AGE_INP_SIZE, MODEL_MEAN, swapRB=False)
                self.age_net.setInput(blob)
                a_preds = self.age_net.forward()
                res["age_group"] = AGE_LIST[int(np.argmax(a_preds))]
                res["age_score"] = float(np.max(a_preds))
            else:
                res["age_group"] = None

            # ethnicity/race: community models exist (DeepFace, others). Placeholder:
            res["ethnicity"] = None

            results.append(res)

        return results

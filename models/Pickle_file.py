import pickle
import cv2

#age_model = cv2.dnn.readNetFromCaffe("deploy_age.prototxt", "age_net.caffemodel")

AGE_MODEL_PATH = "age_net.caffemodel"
AGE_PROTO_PATH = "age_deploy.prototxt"

def load_age_model():
    return cv2.dnn.readNetFromCaffe(AGE_PROTO_PATH,AGE_MODEL_PATH)

age_net = load_age_model()

pickle.dump(age_net, open("age_model.pkl", "wb"))

# Load model
model = pickle.load(open("age_model.pkl", "rb"))

#model.save("age_model.h5")



# Example 1: Save Face Detector
#face_detector = ImprovedFaceDetector(similarity_threshold=0.35)
#with open("face_model.pkl", "wb") as f:
#    pickle.dump(face_detector, f)

# Example 2: Save Demographics Model
#demographics_model = DemographicsAnalyzer()   # assume you defined this class
#with open("demographics_model.pkl", "wb") as f:
#    pickle.dump(demographics_model, f)




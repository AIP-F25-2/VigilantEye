import pickle
import cv2


AGE_MODEL_PATH = "age_net.caffemodel"
AGE_PROTO_PATH = "age_deploy.prototxt"

def load_age_model():
    return cv2.dnn.readNetFromCaffe(AGE_PROTO_PATH,AGE_MODEL_PATH)

age_net = load_age_model()

pickle.dump(age_net, open("age_model.pkl", "wb"))

# Load model
model = pickle.load(open("age_model.pkl", "rb"))




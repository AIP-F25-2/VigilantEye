import cv2
import numpy as np

# paths to YOLO model (you must have these)
MODEL_CFG = "models/yolov3-tiny.cfg"
MODEL_WEIGHTS = "models/yolov3-tiny.weights"
CLASS_NAMES = "models/coco.names"

CONF_THRESH = 0.5
NMS_THRESH = 0.4

# load class names
with open(CLASS_NAMES, "r") as f:
    classes = [line.strip() for line in f.readlines()]

# load YOLO network
net = cv2.dnn.readNetFromDarknet(MODEL_CFG, MODEL_WEIGHTS)
net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)

def detect_holding(image_path, output_path="out.jpg"):
    image = cv2.imread(image_path)
    H, W = image.shape[:2]

    # create blob and run forward pass
    blob = cv2.dnn.blobFromImage(image, 1/255.0, (416, 416), swapRB=True, crop=False)
    net.setInput(blob)
    layer_names = net.getLayerNames()
    out_names = [layer_names[i - 1] for i in net.getUnconnectedOutLayers().flatten()]
    outputs = net.forward(out_names)

    boxes = []
    confidences = []
    class_ids = []

    for out in outputs:
        for detection in out:
            scores = detection[5:]
            class_id = np.argmax(scores)
            confidence = scores[class_id] * detection[4]
            if confidence > CONF_THRESH:
                cx, cy, w_box, h_box = detection[0:4]
                x = int((cx - w_box/2) * W)
                y = int((cy - h_box/2) * H)
                w = int(w_box * W)
                h = int(h_box * H)
                boxes.append([x, y, w, h])
                confidences.append(float(confidence))
                class_ids.append(class_id)

    # Non-Maximum Suppression
    idxs = cv2.dnn.NMSBoxes(boxes, confidences, CONF_THRESH, NMS_THRESH)

    persons = []
    objects = []
    if len(idxs) > 0:
        for i in idxs.flatten():
            x, y, w, h = boxes[i]
            label = classes[class_ids[i]]
            # draw box
            color = (0,255,0) if label == "person" else (255,0,0)
            cv2.rectangle(image, (x, y), (x + w, y + h), color, 2)
            cv2.putText(image, f"{label} {confidences[i]:.2f}", (x, y - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

            if label == "person":
                persons.append((x, y, x + w, y + h))
            else:
                objects.append((x, y, x + w, y + h, label))

    # detect holding by overlap
    for (px1, py1, px2, py2) in persons:
        for (ox1, oy1, ox2, oy2, olabel) in objects:
            # simple overlap check
            overlap_x = max(0, min(px2, ox2) - max(px1, ox1))
            overlap_y = max(0, min(py2, oy2) - max(py1, oy1))
            if overlap_x * overlap_y > 0:
                cv2.putText(image, f"HOLDING {olabel}", (px1, py1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,0,255), 2)
                cv2.rectangle(image, (px1, py1), (px2, py2), (0,0,255), 3)

    cv2.imwrite(output_path, image)
    print("Saved:", output_path)

# Example usage:
if __name__ == "__main__":
    detect_holding("uploads/test1.jpg", "outputs/test1_out.jpg")

"""
Comprehensive Named Entity Recognition (NER) System using OpenCV
This system can detect entities in both images and text using multiple approaches:
1. Visual entity detection (faces, objects, text regions)
2. OCR-based text extraction and NER
3. Text-based NER using spaCy
4. YOLO-based object detection for specific entities
"""

import cv2
import numpy as np
import spacy
import pytesseract
from pathlib import Path
import os
import json
from typing import List, Dict, Tuple, Any
import requests
import zipfile

class ComprehensiveNER:
    def __init__(self):
        """Initialize the NER system with all required models and configurations"""
        self.setup_models()
        self.setup_ocr()
        self.setup_spacy()
        
    def setup_models(self):
        """Setup OpenCV models for face and object detection"""
        # Face detection using Haar cascades
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        self.profile_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_profileface.xml')
        
        # Eye detection
        self.eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')
        
        # Smile detection
        self.smile_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_smile.xml')
        
        # YOLO setup (if available)
        self.yolo_net = None
        self.yolo_classes = []
        self.setup_yolo()
        
    def setup_yolo(self):
        """Setup YOLO model for advanced object detection"""
        try:
            # Check if YOLO files exist
            yolo_cfg = "models/yolov3-tiny.cfg"
            yolo_weights = "models/yolov3-tiny.weights"
            yolo_names = "models/coco.names"
            
            if os.path.exists(yolo_cfg) and os.path.exists(yolo_weights) and os.path.exists(yolo_names):
                self.yolo_net = cv2.dnn.readNetFromDarknet(yolo_cfg, yolo_weights)
                self.yolo_net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
                self.yolo_net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
                
                with open(yolo_names, "r") as f:
                    self.yolo_classes = [line.strip() for line in f.readlines()]
                print("YOLO model loaded successfully")
            else:
                print("YOLO model files not found. Using basic OpenCV detection only.")
        except Exception as e:
            print(f"Error setting up YOLO: {e}")
            
    def setup_ocr(self):
        """Setup OCR configuration"""
        # Configure tesseract (you may need to adjust the path based on your system)
        # For macOS with Homebrew: pytesseract.pytesseract.tesseract_cmd = '/opt/homebrew/bin/tesseract'
        # For Windows: pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        pass
        
    def setup_spacy(self):
        """Setup spaCy model for text-based NER"""
        try:
            self.nlp = spacy.load("en_core_web_sm")
            print("spaCy model loaded successfully")
        except OSError:
            print("spaCy model not found. Please install with: python -m spacy download en_core_web_sm")
            self.nlp = None
            
    def detect_faces(self, image: np.ndarray) -> List[Dict]:
        """Detect faces in the image"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Detect faces
        faces = self.face_cascade.detectMultiScale(gray, 1.1, 4)
        profiles = self.profile_cascade.detectMultiScale(gray, 1.1, 4)
        
        entities = []
        
        # Process frontal faces
        for (x, y, w, h) in faces:
            entities.append({
                'type': 'PERSON',
                'subtype': 'FACE_FRONTAL',
                'bbox': (x, y, x+w, y+h),
                'confidence': 0.8,
                'text': 'Face (Frontal)'
            })
            
        # Process profile faces
        for (x, y, w, h) in profiles:
            entities.append({
                'type': 'PERSON',
                'subtype': 'FACE_PROFILE',
                'bbox': (x, y, x+w, y+h),
                'confidence': 0.7,
                'text': 'Face (Profile)'
            })
            
        return entities
        
    def detect_eyes(self, image: np.ndarray) -> List[Dict]:
        """Detect eyes in the image"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        eyes = self.eye_cascade.detectMultiScale(gray, 1.1, 4)
        
        entities = []
        for (x, y, w, h) in eyes:
            entities.append({
                'type': 'BODY_PART',
                'subtype': 'EYE',
                'bbox': (x, y, x+w, y+h),
                'confidence': 0.6,
                'text': 'Eye'
            })
            
        return entities
        
    def detect_smiles(self, image: np.ndarray) -> List[Dict]:
        """Detect smiles in the image"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        smiles = self.smile_cascade.detectMultiScale(gray, 1.1, 4)
        
        entities = []
        for (x, y, w, h) in smiles:
            entities.append({
                'type': 'EXPRESSION',
                'subtype': 'SMILE',
                'bbox': (x, y, x+w, y+h),
                'confidence': 0.5,
                'text': 'Smile'
            })
            
        return entities
        
    def detect_text_regions(self, image: np.ndarray) -> List[Dict]:
        """Detect text regions in the image using MSER"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Create MSER object
        mser = cv2.MSER_create()
        regions, _ = mser.detectRegions(gray)
        
        entities = []
        for region in regions:
            # Get bounding box for the region
            x, y, w, h = cv2.boundingRect(region.reshape(-1, 1, 2))
            
            # Filter out very small regions
            if w > 20 and h > 10:
                entities.append({
                    'type': 'TEXT_REGION',
                    'subtype': 'POTENTIAL_TEXT',
                    'bbox': (x, y, x+w, y+h),
                    'confidence': 0.6,
                    'text': 'Text Region'
                })
                
        return entities
        
    def extract_text_with_ocr(self, image: np.ndarray) -> str:
        """Extract text from image using OCR"""
        try:
            # Preprocess image for better OCR
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Apply threshold to get a binary image
            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # Use pytesseract to extract text
            text = pytesseract.image_to_string(thresh)
            return text.strip()
        except Exception as e:
            print(f"OCR Error: {e}")
            return ""
            
    def extract_entities_from_text(self, text: str) -> List[Dict]:
        """Extract named entities from text using spaCy"""
        if not self.nlp or not text.strip():
            return []
            
        doc = self.nlp(text)
        entities = []
        
        for ent in doc.ents:
            entities.append({
                'type': ent.label_,
                'subtype': 'TEXT_ENTITY',
                'bbox': None,  # No bounding box for text entities
                'confidence': 0.9,
                'text': ent.text,
                'start': ent.start_char,
                'end': ent.end_char
            })
            
        return entities
        
    def detect_objects_yolo(self, image: np.ndarray) -> List[Dict]:
        """Detect objects using YOLO if available"""
        if not self.yolo_net:
            return []
            
        entities = []
        H, W = image.shape[:2]
        
        # Create blob and run forward pass
        blob = cv2.dnn.blobFromImage(image, 1/255.0, (416, 416), swapRB=True, crop=False)
        self.yolo_net.setInput(blob)
        layer_names = self.yolo_net.getLayerNames()
        out_names = [layer_names[i - 1] for i in self.yolo_net.getUnconnectedOutLayers().flatten()]
        outputs = self.yolo_net.forward(out_names)
        
        boxes = []
        confidences = []
        class_ids = []
        
        CONF_THRESH = 0.5
        NMS_THRESH = 0.4
        
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
        
        if len(idxs) > 0:
            for i in idxs.flatten():
                x, y, w, h = boxes[i]
                label = self.yolo_classes[class_ids[i]]
                confidence = confidences[i]
                
                entities.append({
                    'type': 'OBJECT',
                    'subtype': label.upper(),
                    'bbox': (x, y, x+w, y+h),
                    'confidence': confidence,
                    'text': label
                })
                
        return entities
        
    def detect_all_entities(self, image_path: str) -> Dict[str, Any]:
        """Detect all types of entities in an image"""
        if not os.path.exists(image_path):
            return {"error": f"Image file not found: {image_path}"}
            
        # Load image
        image = cv2.imread(image_path)
        if image is None:
            return {"error": f"Could not load image: {image_path}"}
            
        results = {
            'image_path': image_path,
            'entities': [],
            'extracted_text': '',
            'text_entities': []
        }
        
        # Detect visual entities
        print("Detecting faces...")
        faces = self.detect_faces(image)
        results['entities'].extend(faces)
        
        print("Detecting eyes...")
        eyes = self.detect_eyes(image)
        results['entities'].extend(eyes)
        
        print("Detecting smiles...")
        smiles = self.detect_smiles(image)
        results['entities'].extend(smiles)
        
        print("Detecting text regions...")
        text_regions = self.detect_text_regions(image)
        results['entities'].extend(text_regions)
        
        print("Detecting objects with YOLO...")
        objects = self.detect_objects_yolo(image)
        results['entities'].extend(objects)
        
        # Extract text and perform NER
        print("Extracting text with OCR...")
        extracted_text = self.extract_text_with_ocr(image)
        results['extracted_text'] = extracted_text
        
        if extracted_text:
            print("Performing text-based NER...")
            text_entities = self.extract_entities_from_text(extracted_text)
            results['text_entities'] = text_entities
        
        return results
        
    def visualize_entities(self, image_path: str, output_path: str = None) -> str:
        """Visualize detected entities on the image"""
        results = self.detect_all_entities(image_path)
        
        if 'error' in results:
            return results['error']
            
        # Load image
        image = cv2.imread(image_path)
        
        # Define colors for different entity types
        colors = {
            'PERSON': (0, 255, 0),      # Green
            'BODY_PART': (255, 0, 0),   # Blue
            'EXPRESSION': (0, 0, 255),  # Red
            'TEXT_REGION': (255, 255, 0), # Cyan
            'OBJECT': (255, 0, 255),    # Magenta
        }
        
        # Draw bounding boxes and labels
        for entity in results['entities']:
            if entity['bbox']:
                x1, y1, x2, y2 = entity['bbox']
                entity_type = entity['type']
                color = colors.get(entity_type, (128, 128, 128))
                
                # Draw rectangle
                cv2.rectangle(image, (x1, y1), (x2, y2), color, 2)
                
                # Draw label
                label = f"{entity['text']} ({entity['confidence']:.2f})"
                cv2.putText(image, label, (x1, y1-10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        
        # Save or display result
        if output_path is None:
            output_path = image_path.replace('.', '_ner_result.')
            
        cv2.imwrite(output_path, image)
        print(f"Visualization saved to: {output_path}")
        
        return output_path
        
    def save_results_json(self, results: Dict, output_path: str):
        """Save detection results to JSON file"""
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"Results saved to: {output_path}")

def main():
    """Example usage of the Comprehensive NER System"""
    # Initialize the NER system
    ner = ComprehensiveNER()
    
    # Example image path (you can change this to your image)
    image_path = "uploads/test_image.jpg"
    
    if not os.path.exists(image_path):
        print(f"Please place an image at {image_path} to test the system")
        return
    
    print("Starting comprehensive NER detection...")
    
    # Detect all entities
    results = ner.detect_all_entities(image_path)
    
    # Print results
    print("\n=== DETECTION RESULTS ===")
    print(f"Image: {results['image_path']}")
    print(f"Total entities detected: {len(results['entities'])}")
    
    if results['extracted_text']:
        print(f"\nExtracted text: {results['extracted_text']}")
        print(f"Text entities: {len(results['text_entities'])}")
    
    print("\nVisual entities:")
    for entity in results['entities']:
        print(f"  - {entity['type']}: {entity['text']} (confidence: {entity['confidence']:.2f})")
    
    if results['text_entities']:
        print("\nText entities:")
        for entity in results['text_entities']:
            print(f"  - {entity['type']}: {entity['text']}")
    
    # Create visualization
    output_image = ner.visualize_entities(image_path)
    
    # Save results to JSON
    ner.save_results_json(results, "ner_results.json")
    
    print(f"\nVisualization saved to: {output_image}")
    print("Results saved to: ner_results.json")

if __name__ == "__main__":
    main()



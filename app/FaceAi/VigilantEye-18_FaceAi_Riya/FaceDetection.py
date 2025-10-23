# Improved Face Detection for Better Cross-Image Recognition
# Handles different angles, lighting, and expressions

import cv2
import numpy as np
import face_recognition
from PIL import Image, ImageEnhance
import matplotlib.pyplot as plt
import os
from datetime import datetime
import uuid
from sklearn.metrics.pairwise import cosine_similarity

class ImprovedFaceDetector:
    """Enhanced Face Detection with better cross-image recognition"""
    
    def __init__(self, similarity_threshold=0.4, use_multiple_encodings=True):
        # Lower threshold for better matching across different photos
        self.similarity_threshold = similarity_threshold
        self.use_multiple_encodings = use_multiple_encodings
        self.known_faces = {}  # {person_id: [list_of_encodings]}
        self.face_counter = 0
        
        print(f"   Enhanced Face Detector initialized")
        print(f"   Similarity threshold: {similarity_threshold}")
        print(f"   Multiple encodings per person: {use_multiple_encodings}")
    
    def preprocess_image(self, image):
        """Preprocess image to improve face detection accuracy"""
        # Convert to RGB if needed
        if len(image.shape) == 3 and image.shape[2] == 3:
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        else:
            rgb_image = image.copy()
        
        # Convert to PIL for enhancement
        pil_image = Image.fromarray(rgb_image)
        
        # Enhance contrast and brightness for better detection
        enhancer = ImageEnhance.Contrast(pil_image)
        enhanced = enhancer.enhance(1.2)
        
        enhancer = ImageEnhance.Brightness(enhanced)
        enhanced = enhancer.enhance(1.1)
        
        return np.array(enhanced)
    
    def detect_faces_multiple_methods(self, image):
        """
        Use multiple detection methods and models for better accuracy
        """
        preprocessed = self.preprocess_image(image)
        all_detections = []
        
        # Method 1: HOG model (faster, good for frontal faces)
        try:
            locations_hog = face_recognition.face_locations(preprocessed, model="hog", number_of_times_to_upsample=1)
            if locations_hog:
                encodings_hog = face_recognition.face_encodings(preprocessed, locations_hog, model="large")
                all_detections.extend(zip(locations_hog, encodings_hog))
        except:
            pass
        
        # Method 2: CNN model (more accurate, better for various angles)
        try:
            locations_cnn = face_recognition.face_locations(preprocessed, model="cnn", number_of_times_to_upsample=1)
            if locations_cnn:
                encodings_cnn = face_recognition.face_encodings(preprocessed, locations_cnn, model="large")
                
                # Remove duplicates (faces detected by both methods)
                for loc_cnn, enc_cnn in zip(locations_cnn, encodings_cnn):
                    is_duplicate = False
                    for loc_hog, enc_hog in all_detections:
                        # Check if locations are similar (same face detected twice)
                        if self._locations_similar(loc_cnn, loc_hog):
                            is_duplicate = True
                            break
                    
                    if not is_duplicate:
                        all_detections.append((loc_cnn, enc_cnn))
        except:
            pass
        
        # If no faces found, try with different preprocessing
        if not all_detections:
            # Try with histogram equalization
            gray = cv2.cvtColor(preprocessed, cv2.COLOR_RGB2GRAY)
            equalized = cv2.equalizeHist(gray)
            equalized_rgb = cv2.cvtColor(equalized, cv2.COLOR_GRAY2RGB)
            
            try:
                locations_eq = face_recognition.face_locations(equalized_rgb, model="hog")
                if locations_eq:
                    encodings_eq = face_recognition.face_encodings(equalized_rgb, locations_eq, model="large")
                    all_detections.extend(zip(locations_eq, encodings_eq))
            except:
                pass
        
        print(f" Detected {len(all_detections)} faces using multiple methods")
        return all_detections
    
    def _locations_similar(self, loc1, loc2, threshold=30):
        """Check if two face locations are similar (same face detected twice)"""
        top1, right1, bottom1, left1 = loc1
        top2, right2, bottom2, left2 = loc2
        
        # Calculate center points
        center1 = ((left1 + right1) // 2, (top1 + bottom1) // 2)
        center2 = ((left2 + right2) // 2, (top2 + bottom2) // 2)
        
        # Check if centers are close
        distance = np.sqrt((center1[0] - center2[0])**2 + (center1[1] - center2[1])**2)
        return distance < threshold
    
    def advanced_face_comparison(self, unknown_encoding):
        """
        Advanced comparison using multiple techniques
        """
        if not self.known_faces:
            return None, 0.0
        
        best_match_id = None
        best_similarity = 0.0
        
        for person_id, encoding_list in self.known_faces.items():
            similarities = []
            
            for known_encoding in encoding_list:
                # Method 1: Face recognition library distance
                distance = face_recognition.face_distance([known_encoding], unknown_encoding)[0]
                similarity1 = 1 - distance
                
                # Method 2: Cosine similarity
                similarity2 = cosine_similarity([known_encoding], [unknown_encoding])[0][0]
                
                # Method 3: Euclidean distance based similarity
                euclidean_dist = np.linalg.norm(known_encoding - unknown_encoding)
                similarity3 = 1 / (1 + euclidean_dist)
                
                # Combine similarities (weighted average)
                combined_similarity = (similarity1 * 0.5 + similarity2 * 0.3 + similarity3 * 0.2)
                similarities.append(combined_similarity)
            
            # Take the maximum similarity for this person
            max_similarity = max(similarities)
            
            # Use threshold and keep track of best match
            if max_similarity > best_similarity and max_similarity >= self.similarity_threshold:
                best_similarity = max_similarity
                best_match_id = person_id
        
        return best_match_id, best_similarity
    
    def add_known_face(self, face_encoding, person_id=None):
        """Add a new face encoding to known faces"""
        if person_id is None:
            self.face_counter += 1
            person_id = f"person_{self.face_counter:03d}"
        
        if person_id not in self.known_faces:
            self.known_faces[person_id] = []
        
        self.known_faces[person_id].append(face_encoding)
        
        # Limit encodings per person to prevent memory issues
        if len(self.known_faces[person_id]) > 5:
            self.known_faces[person_id] = self.known_faces[person_id][-5:]
        
        print(f" Added encoding for: {person_id} (total encodings: {len(self.known_faces[person_id])})")
        return person_id
    
    def process_image(self, image_path_or_array, show_result=True):
        """
        Enhanced image processing with better recognition
        """
        # Load image
        if isinstance(image_path_or_array, str):
            if not os.path.exists(image_path_or_array):
                print(f" Image file not found: {image_path_or_array}")
                return [], None
            
            image = cv2.imread(image_path_or_array)
            if image is None:
                print(f" Could not load image: {image_path_or_array}")
                return [], None
            print(f" Processing image: {image_path_or_array}")
        else:
            image = image_path_or_array.copy()
            print(" Processing image array")
        
        # Detect faces with multiple methods
        face_detections = self.detect_faces_multiple_methods(image)
        
        if not face_detections:
            if show_result:
                self.show_image(image, "No Faces Detected")
            return [], image
        
        # Process each detected face
        results = []
        annotated_image = image.copy()
        
        for i, (face_location, face_encoding) in enumerate(face_detections):
            top, right, bottom, left = face_location
            
            # Advanced face comparison
            matched_id, similarity = self.advanced_face_comparison(face_encoding)
            
            if matched_id:
                # Known face - add this encoding to improve future recognition
                person_id = matched_id
                is_new = False
                color = (0, 255, 0)  # Green for known faces
                
                # Add this new encoding to improve recognition
                if self.use_multiple_encodings:
                    self.add_known_face(face_encoding, person_id)
                
                print(f" RECOGNIZED: {person_id} (similarity: {similarity:.3f})")
            else:
                # New face
                person_id = self.add_known_face(face_encoding)
                is_new = True
                similarity = 0.0
                color = (0, 0, 255)  # Red for new faces
                print(f" NEW PERSON: {person_id}")
            
            # Draw bounding box with thicker lines
            cv2.rectangle(annotated_image, (left, top), (right, bottom), color, 3)
            
            # Draw label with better formatting
            label = f"{person_id}"
            if not is_new:
                label += f" ({similarity:.2f})"
            
            # Add text background
            (text_width, text_height), baseline = cv2.getTextSize(
                label, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
            cv2.rectangle(annotated_image, 
                         (left, top - text_height - 15),
                         (left + text_width, top), 
                         color, -1)
            cv2.putText(annotated_image, label, (left, top - 8), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            # Add confidence indicator
            confidence_text = f"Conf: {similarity:.2f}" if not is_new else "NEW"
            cv2.putText(annotated_image, confidence_text, (left, bottom + 20), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            
            # Store result
            results.append({
                'person_id': person_id,
                'is_new_person': is_new,
                'similarity_score': similarity,
                'bounding_box': face_location,
                'face_encoding': face_encoding
            })
        
        # Display result
        if show_result:
            title = f"Enhanced Detection: {len(results)} faces"
            self.show_image(annotated_image, title)
        
        return results, annotated_image
    
    def show_image(self, image, title="Image"):
        """Display image in Jupyter notebook with better formatting"""
        plt.figure(figsize=(15, 10))
        
        # Convert BGR to RGB for matplotlib display
        if len(image.shape) == 3:
            display_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        else:
            display_image = image
            
        plt.imshow(display_image)
        plt.title(title, fontsize=18, fontweight='bold')
        plt.axis('off')
        plt.tight_layout()
        plt.show()
    
    def get_detailed_stats(self):
        """Print detailed statistics"""
        print(f"\n Enhanced Detection Statistics:")
        print(f"   Total unique persons: {len(self.known_faces)}")
        print(f"   Similarity threshold: {self.similarity_threshold}")
        
        for person_id, encodings in self.known_faces.items():
            print(f"    {person_id}: {len(encodings)} encoding(s)")
    
    def adjust_threshold(self, new_threshold):
        """Adjust similarity threshold for better matching"""
        old_threshold = self.similarity_threshold
        self.similarity_threshold = new_threshold
        print(f" Similarity threshold changed: {old_threshold} → {new_threshold}")
        print(" Lower values = more lenient matching")
        print(" Higher values = stricter matching")
    
    def reset_memory(self):
        """Clear all known faces"""
        self.known_faces = {}
        self.face_counter = 0
        print(" Memory cleared - all known faces removed")

# Enhanced Testing Functions

def test_trump_images():
    """Specific test for the Trump images you provided"""
    print(" Testing with Trump images...")
    
    # Initialize with lower threshold for better cross-image matching
    detector = ImprovedFaceDetector(similarity_threshold=0.35)
    
    # You'll need to save your images as files first
    print("\n To test with your images:")
    print("1. Save Image 1 as 'trump1.jpg'")  
    print("2. Save Image 2 as 'trump2.jpg'")
    print("3. Run the following commands:")
    print("")
    print("# First image")
    print("results1, img1 = detector.process_image('trump1.jpg')")
    print("")
    print("# Second image (should recognize as same person)")  
    print("results2, img2 = detector.process_image('trump2.jpg')")
    
    return detector

def test_recognition_accuracy(image1_path, image2_path):
    """Test recognition accuracy between two images"""
    print(" Testing Recognition Accuracy...")
    
    detector = ImprovedFaceDetector(similarity_threshold=0.3)
    
    print(f"\n=== Processing Image 1: {image1_path} ===")
    results1, _ = detector.process_image(image1_path)
    
    print(f"\n=== Processing Image 2: {image2_path} ===")
    results2, _ = detector.process_image(image2_path)
    
    print(f"\n Recognition Test Results:")
    if results1 and results2:
        if results1[0]['person_id'] == results2[0]['person_id']:
            print(" SUCCESS: Same person recognized in both images!")
            print(f"   Person ID: {results1[0]['person_id']}")
            print(f"   Similarity: {results2[0]['similarity_score']:.3f}")
        else:
            print(" FAILED: Detected as different persons")
            print(f"   Image 1: {results1[0]['person_id']}")
            print(f"   Image 2: {results2[0]['person_id']}")
    
    detector.get_detailed_stats()
    return detector

def quick_test_enhanced():
    """Quick test with enhanced features"""
    print(" Enhanced Face Detection Test")
    print("\n Key Improvements:")
    print("   Lower similarity threshold (0.4 instead of 0.6)")
    print("    Multiple detection methods (HOG + CNN)")
    print("    I mage preprocessing (contrast/brightness)")
    print("    Advanced comparison algorithms")
    print("    Multiple encodings per person")
    print("\n📝 Usage:")
    print("detector = ImprovedFaceDetector(similarity_threshold=0.35)")
    print("results, img = detector.process_image('your_image.jpg')")
    
    return ImprovedFaceDetector(similarity_threshold=0.35)

# Initialize
print(" Enhanced Face Detection loaded!")
print(" Specifically designed for better cross-image recognition")
print("Run: quick_test_enhanced() or test_trump_images() to get started")
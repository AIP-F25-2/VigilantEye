# Simple Ambiguity Detection - Just Give 2 Images
# Checks if two person images might be the same person

import cv2
import numpy as np
import matplotlib.pyplot as plt
from sklearn.metrics.pairwise import cosine_similarity

class SimpleAmbiguityChecker:
    """
    Simple ambiguity checker - just input 2 person images
    No bounding boxes needed, just cropped person images
    """
    
    def __init__(self, ambiguity_threshold=0.7):
        self.ambiguity_threshold = ambiguity_threshold
        print(f" Simple Ambiguity Checker initialized")
        print(f" Threshold: {ambiguity_threshold} (lower = more strict)")
    
    def check_ambiguity(self, image1, image2, show_result=True):
        """
        Main function - check if two images might be the same person
        
        Args:
            image1: First person image (can be file path or numpy array)
            image2: Second person image (can be file path or numpy array)
            show_result: Whether to display visual comparison
        
        Returns:
            is_ambiguous: Boolean (True if possibly same person)
            ambiguity_score: Float 0-1 (higher = more similar)
            details: Dictionary with breakdown
        """
        
        # Load images if paths provided
        img1 = self._load_image(image1)
        img2 = self._load_image(image2)
        
        if img1 is None or img2 is None:
            print(" Could not load images")
            return False, 0.0, {}
        
        print(" Analyzing images...")
        
        # Calculate various similarities
        similarities = {}
        
        # 1. Overall color similarity
        similarities['color'] = self._compare_colors(img1, img2)
        print(f"   Color similarity: {similarities['color']:.2f}")
        
        # 2. Clothing similarity (upper and lower body)
        similarities['clothing'] = self._compare_clothing(img1, img2)
        print(f"   Clothing similarity: {similarities['clothing']:.2f}")
        
        # 3. Body shape similarity
        similarities['body_shape'] = self._compare_body_shape(img1, img2)
        print(f"   Body shape similarity: {similarities['body_shape']:.2f}")
        
        # 4. Aspect ratio (height/width proportion)
        similarities['proportion'] = self._compare_proportions(img1, img2)
        print(f"   Body proportion similarity: {similarities['proportion']:.2f}")
        
        # 5. Texture/pattern similarity
        similarities['texture'] = self._compare_texture(img1, img2)
        print(f"   Texture similarity: {similarities['texture']:.2f}")
        
        # Calculate overall ambiguity score (weighted average)
        weights = {
            'color': 0.25,
            'clothing': 0.30,
            'body_shape': 0.25,
            'proportion': 0.10,
            'texture': 0.10
        }
        
        ambiguity_score = sum(similarities[key] * weights[key] for key in weights)
        
        # Determine if ambiguous
        is_ambiguous = ambiguity_score >= self.ambiguity_threshold
        
        # Generate reasons
        reasons = []
        if similarities['clothing'] > 0.8:
            reasons.append(f"Very similar clothing (score: {similarities['clothing']:.2f})")
        if similarities['color'] > 0.8:
            reasons.append(f"Very similar colors (score: {similarities['color']:.2f})")
        if similarities['body_shape'] > 0.75:
            reasons.append(f"Similar body shape (score: {similarities['body_shape']:.2f})")
        if similarities['proportion'] > 0.9:
            reasons.append(f"Similar body proportions")
        
        if not reasons:
            reasons.append("Multiple similarity factors detected")
        
        details = {
            'similarities': similarities,
            'reasons': reasons,
            'weights': weights
        }
        
        # Display results
        print(f"\n{'='*60}")
        print(f" AMBIGUITY ANALYSIS RESULT")
        print(f"{'='*60}")
        print(f"Ambiguous: {'YES ' if is_ambiguous else 'NO '}")
        print(f"Ambiguity Score: {ambiguity_score:.2f} / 1.00")
        print(f"\nReasons:")
        for reason in reasons:
            print(f"  • {reason}")
        print(f"{'='*60}")
        
        # Show visual comparison
        if show_result:
            self._visualize_comparison(img1, img2, is_ambiguous, 
                                      ambiguity_score, reasons)
        
        return is_ambiguous, ambiguity_score, details
    
    def _load_image(self, image_input):
        """Load image from path or return if already numpy array"""
        if isinstance(image_input, str):
            img = cv2.imread(image_input)
            if img is None:
                print(f" Could not load: {image_input}")
            return img
        else:
            return image_input
    
    def _compare_colors(self, img1, img2):
        """Compare overall color distribution"""
        try:
            # Resize for fair comparison
            img1_resized = cv2.resize(img1, (128, 256))
            img2_resized = cv2.resize(img2, (128, 256))
            
            # Convert to HSV
            hsv1 = cv2.cvtColor(img1_resized, cv2.COLOR_BGR2HSV)
            hsv2 = cv2.cvtColor(img2_resized, cv2.COLOR_BGR2HSV)
            
            # Calculate histograms
            hist1 = cv2.calcHist([hsv1], [0, 1, 2], None, [8, 8, 8], 
                                [0, 180, 0, 256, 0, 256])
            hist2 = cv2.calcHist([hsv2], [0, 1, 2], None, [8, 8, 8], 
                                [0, 180, 0, 256, 0, 256])
            
            # Normalize
            hist1 = hist1.flatten() / (hist1.sum() + 1e-7)
            hist2 = hist2.flatten() / (hist2.sum() + 1e-7)
            
            # Calculate similarity
            similarity = cosine_similarity([hist1], [hist2])[0][0]
            return max(0, similarity)
            
        except:
            return 0.0
    
    def _compare_clothing(self, img1, img2):
        """Compare clothing in upper and lower body regions"""
        try:
            h1, w1 = img1.shape[:2]
            h2, w2 = img2.shape[:2]
            
            # Extract upper body (30-60% of height)
            upper1 = img1[int(h1*0.3):int(h1*0.6), :]
            upper2 = img2[int(h2*0.3):int(h2*0.6), :]
            
            # Extract lower body (60-90% of height)
            lower1 = img1[int(h1*0.6):int(h1*0.9), :]
            lower2 = img2[int(h2*0.6):int(h2*0.9), :]
            
            # Compare dominant colors
            upper_sim = self._compare_dominant_color(upper1, upper2)
            lower_sim = self._compare_dominant_color(lower1, lower2)
            
            # Average
            clothing_similarity = (upper_sim + lower_sim) / 2
            return clothing_similarity
            
        except:
            return 0.0
    
    def _compare_dominant_color(self, region1, region2):
        """Compare dominant colors of two regions"""
        try:
            if region1.size == 0 or region2.size == 0:
                return 0.0
            
            # Get dominant color using mean
            color1 = cv2.mean(region1)[:3]
            color2 = cv2.mean(region2)[:3]
            
            # Calculate color distance
            color1 = np.array(color1)
            color2 = np.array(color2)
            
            distance = np.linalg.norm(color1 - color2)
            max_distance = 255 * np.sqrt(3)
            
            similarity = 1 - (distance / max_distance)
            return max(0, similarity)
            
        except:
            return 0.0
    
    def _compare_body_shape(self, img1, img2):
        """Compare body shape using HOG features"""
        try:
            # Resize to same size
            img1_resized = cv2.resize(img1, (64, 128))
            img2_resized = cv2.resize(img2, (64, 128))
            
            # Convert to grayscale
            gray1 = cv2.cvtColor(img1_resized, cv2.COLOR_BGR2GRAY)
            gray2 = cv2.cvtColor(img2_resized, cv2.COLOR_BGR2GRAY)
            
            # HOG descriptor
            hog = cv2.HOGDescriptor(
                _winSize=(64, 128),
                _blockSize=(16, 16),
                _blockStride=(8, 8),
                _cellSize=(8, 8),
                _nbins=9
            )
            
            # Compute HOG features
            hog1 = hog.compute(gray1).flatten()
            hog2 = hog.compute(gray2).flatten()
            
            # Normalize
            hog1 = hog1 / (np.linalg.norm(hog1) + 1e-7)
            hog2 = hog2 / (np.linalg.norm(hog2) + 1e-7)
            
            # Calculate similarity
            similarity = cosine_similarity([hog1], [hog2])[0][0]
            return max(0, similarity)
            
        except:
            return 0.0
    
    def _compare_proportions(self, img1, img2):
        """Compare body proportions (aspect ratio)"""
        try:
            h1, w1 = img1.shape[:2]
            h2, w2 = img2.shape[:2]
            
            ratio1 = h1 / w1
            ratio2 = h2 / w2
            
            # Calculate similarity (closer to 1 = more similar)
            ratio_diff = abs(ratio1 - ratio2)
            similarity = 1 - min(ratio_diff / 2.0, 1.0)
            
            return similarity
            
        except:
            return 0.0
    
    def _compare_texture(self, img1, img2):
        """Compare texture patterns"""
        try:
            # Resize
            img1_resized = cv2.resize(img1, (64, 128))
            img2_resized = cv2.resize(img2, (64, 128))
            
            # Convert to grayscale
            gray1 = cv2.cvtColor(img1_resized, cv2.COLOR_BGR2GRAY)
            gray2 = cv2.cvtColor(img2_resized, cv2.COLOR_BGR2GRAY)
            
            # Calculate texture using Laplacian variance
            laplacian1 = cv2.Laplacian(gray1, cv2.CV_64F)
            laplacian2 = cv2.Laplacian(gray2, cv2.CV_64F)
            
            texture1 = np.var(laplacian1)
            texture2 = np.var(laplacian2)
            
            # Normalize and compare
            max_texture = max(texture1, texture2) + 1e-7
            similarity = 1 - abs(texture1 - texture2) / max_texture
            
            return max(0, similarity)
            
        except:
            return 0.0
    
    def _visualize_comparison(self, img1, img2, is_ambiguous, score, reasons):
        """Visualize side-by-side comparison"""
        fig, axes = plt.subplots(1, 2, figsize=(14, 8))
        
        # Convert BGR to RGB
        img1_rgb = cv2.cvtColor(img1, cv2.COLOR_BGR2RGB)
        img2_rgb = cv2.cvtColor(img2, cv2.COLOR_BGR2RGB)
        
        # Display images
        axes[0].imshow(img1_rgb)
        axes[0].set_title("Person 1", fontsize=14, fontweight='bold')
        axes[0].axis('off')
        
        axes[1].imshow(img2_rgb)
        axes[1].set_title("Person 2", fontsize=14, fontweight='bold')
        axes[1].axis('off')
        
        # Add result text
        status = " AMBIGUOUS - Possibly Same Person" if is_ambiguous else " DIFFERENT - Not Same Person"
        color = 'red' if is_ambiguous else 'green'
        
        result_text = f"{status}\n\n"
        result_text += f"Ambiguity Score: {score:.2f}\n\n"
        result_text += "Reasons:\n"
        for reason in reasons:
            result_text += f"  • {reason}\n"
        
        fig.text(0.5, 0.02, result_text, ha='center', fontsize=11,
                bbox=dict(boxstyle='round', facecolor=color, alpha=0.3))
        
        plt.tight_layout()
        plt.subplots_adjust(bottom=0.25)
        plt.show()



def check_two_images(image1_path, image2_path):
    """
    Simple function - just provide 2 image paths
    
    Example:
        check_two_images('person1.jpg', 'person2.jpg')
    """
    checker = SimpleAmbiguityChecker(ambiguity_threshold=0.7)
    is_ambiguous, score, details = checker.check_ambiguity(image1_path, image2_path)
    
    if is_ambiguous:
        print("\n WARNING: These might be the same person!")
        print("   Recommended Action: Flag for human review")
    else:
        print("\n CLEAR: These are different persons")
    
    return is_ambiguous, score, details

def quick_test():
    """Quick test function"""
    print(" Simple Ambiguity Checker - Ready!")
    print("\n Usage:")
    print("check_two_images('image1.jpg', 'image2.jpg')")
    print("\nOr:")
    print("checker = SimpleAmbiguityChecker()")
    print("is_ambiguous, score, details = checker.check_ambiguity('img1.jpg', 'img2.jpg')")
    
    return SimpleAmbiguityChecker()

# Initialize
print(" Simple Ambiguity Checker loaded!")
print("Run: quick_test() to see usage")
print("\nQuick start: check_two_images('person1.jpg', 'person2.jpg')")
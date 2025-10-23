import cv2
import numpy as np
import matplotlib.pyplot as plt
from sklearn.metrics.pairwise import cosine_similarity

class SimpleAmbiguityChecker:
    """
    Improved ambiguity checker - now includes:
    - Face similarity (if faces detected)
    - Better clothing histogram comparison
    - Local Binary Pattern texture comparison
    """

    def __init__(self, ambiguity_threshold=0.7):
        self.ambiguity_threshold = ambiguity_threshold
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        print(f" Improved Ambiguity Checker initialized")
        print(f"   Threshold: {ambiguity_threshold} (lower = more strict)")

    def check_ambiguity(self, image1, image2, show_result=True):
        img1 = self._load_image(image1)
        img2 = self._load_image(image2)

        if img1 is None or img2 is None:
            print(" Could not load images")
            return False, 0.0, {}

        print(" Analyzing images...")

        similarities = {}

        # Face similarity
        similarities['face'] = self._compare_faces(img1, img2)
        print(f"   Face similarity: {similarities['face']:.2f}")

        # Color similarity
        similarities['color'] = self._compare_colors(img1, img2)
        print(f"   Color similarity: {similarities['color']:.2f}")

        # Clothing similarity
        similarities['clothing'] = self._compare_clothing_hist(img1, img2)
        print(f"   Clothing similarity: {similarities['clothing']:.2f}")

        # Body shape similarity
        similarities['body_shape'] = self._compare_body_shape(img1, img2)
        print(f"   Body shape similarity: {similarities['body_shape']:.2f}")

        # Aspect ratio
        similarities['proportion'] = self._compare_proportions(img1, img2)
        print(f"   Proportion similarity: {similarities['proportion']:.2f}")

        # Texture
        similarities['texture'] = self._compare_texture_lbp(img1, img2)
        print(f"   Texture similarity (LBP): {similarities['texture']:.2f}")

        # Adjusted weights (if face detected, give more weight to it)
        weights = {
            'face': 0.35 if similarities['face'] > 0 else 0.0,  # only if detected
            'color': 0.20,
            'clothing': 0.20,
            'body_shape': 0.15,
            'proportion': 0.05,
            'texture': 0.05
        }

        # Normalize weights if face not detected
        if weights['face'] == 0.0:
            total = sum(weights.values())
            for k in weights:
                weights[k] = weights[k] / total

        ambiguity_score = sum(similarities[key] * weights[key] for key in weights)

        is_ambiguous = ambiguity_score >= self.ambiguity_threshold

        reasons = []
        if similarities['face'] > 0.8:
            reasons.append(f"Faces look very similar (score: {similarities['face']:.2f})")
        if similarities['clothing'] > 0.8:
            reasons.append(f"Very similar clothing (score: {similarities['clothing']:.2f})")
        if similarities['color'] > 0.8:
            reasons.append(f"Very similar colors (score: {similarities['color']:.2f})")
        if similarities['body_shape'] > 0.75:
            reasons.append(f"Similar body shape (score: {similarities['body_shape']:.2f})")
        if similarities['proportion'] > 0.9:
            reasons.append("Similar body proportions")

        if not reasons:
            reasons.append("Multiple similarity factors detected")

        details = {
            'similarities': similarities,
            'reasons': reasons,
            'weights': weights
        }

        print(f"\n{'='*60}")
        print(f" IMPROVED AMBIGUITY ANALYSIS RESULT")
        print(f"{'='*60}")
        print(f"Ambiguous: {'YES ' if is_ambiguous else 'NO '}")
        print(f"Ambiguity Score: {ambiguity_score:.2f} / 1.00")
        print(f"\nReasons:")
        for reason in reasons:
            print(f"  • {reason}")
        print(f"{'='*60}")

        if show_result:
            self._visualize_comparison(img1, img2, is_ambiguous, ambiguity_score, reasons)

        return is_ambiguous, ambiguity_score, details

    def _load_image(self, image_input):
        if isinstance(image_input, str):
            img = cv2.imread(image_input)
            if img is None:
                print(f" Could not load: {image_input}")
            return img
        else:
            return image_input

    def _compare_faces(self, img1, img2):
        """Detect faces and compare using ORB feature matching"""
        try:
            gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
            gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)

            faces1 = self.face_cascade.detectMultiScale(gray1, 1.3, 5)
            faces2 = self.face_cascade.detectMultiScale(gray2, 1.3, 5)

            if len(faces1) == 0 or len(faces2) == 0:
                return 0.0

            x, y, w, h = faces1[0]
            face1 = gray1[y:y+h, x:x+w]
            x, y, w, h = faces2[0]
            face2 = gray2[y:y+h, x:x+w]

            orb = cv2.ORB_create()
            kp1, des1 = orb.detectAndCompute(face1, None)
            kp2, des2 = orb.detectAndCompute(face2, None)

            if des1 is None or des2 is None:
                return 0.0

            bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
            matches = bf.match(des1, des2)

            if len(matches) == 0:
                return 0.0

            good_matches = [m for m in matches if m.distance < 60]
            similarity = len(good_matches) / len(matches)
            return similarity
        except:
            return 0.0

    def _compare_colors(self, img1, img2):
        try:
            img1_resized = cv2.resize(img1, (128, 256))
            img2_resized = cv2.resize(img2, (128, 256))

            hsv1 = cv2.cvtColor(img1_resized, cv2.COLOR_BGR2HSV)
            hsv2 = cv2.cvtColor(img2_resized, cv2.COLOR_BGR2HSV)

            hist1 = cv2.calcHist([hsv1], [0, 1], None, [50, 60], [0, 180, 0, 256])
            hist2 = cv2.calcHist([hsv2], [0, 1], None, [50, 60], [0, 180, 0, 256])

            cv2.normalize(hist1, hist1, 0, 1, cv2.NORM_MINMAX)
            cv2.normalize(hist2, hist2, 0, 1, cv2.NORM_MINMAX)

            similarity = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)
            return max(0, similarity)
        except:
            return 0.0

    def _compare_clothing_hist(self, img1, img2):
        """Upper/lower body clothing histograms"""
        try:
            h1, w1 = img1.shape[:2]
            h2, w2 = img2.shape[:2]

            upper1 = img1[int(h1*0.3):int(h1*0.6), :]
            upper2 = img2[int(h2*0.3):int(h2*0.6), :]
            lower1 = img1[int(h1*0.6):int(h1*0.9), :]
            lower2 = img2[int(h2*0.6):int(h2*0.9), :]

            def hist_sim(a, b):
                hsv_a = cv2.cvtColor(a, cv2.COLOR_BGR2HSV)
                hsv_b = cv2.cvtColor(b, cv2.COLOR_BGR2HSV)
                hist_a = cv2.calcHist([hsv_a], [0], None, [32], [0, 180])
                hist_b = cv2.calcHist([hsv_b], [0], None, [32], [0, 180])
                cv2.normalize(hist_a, hist_a)
                cv2.normalize(hist_b, hist_b)
                return cv2.compareHist(hist_a, hist_b, cv2.HISTCMP_CORREL)

            upper_sim = hist_sim(upper1, upper2)
            lower_sim = hist_sim(lower1, lower2)

            return (upper_sim + lower_sim) / 2
        except:
            return 0.0

    def _compare_body_shape(self, img1, img2):
        try:
            img1_resized = cv2.resize(img1, (64, 128))
            img2_resized = cv2.resize(img2, (64, 128))

            gray1 = cv2.cvtColor(img1_resized, cv2.COLOR_BGR2GRAY)
            gray2 = cv2.cvtColor(img2_resized, cv2.COLOR_BGR2GRAY)

            hog = cv2.HOGDescriptor()
            hog1 = hog.compute(gray1).flatten()
            hog2 = hog.compute(gray2).flatten()

            hog1 = hog1 / (np.linalg.norm(hog1) + 1e-7)
            hog2 = hog2 / (np.linalg.norm(hog2) + 1e-7)

            return cosine_similarity([hog1], [hog2])[0][0]
        except:
            return 0.0

    def _compare_proportions(self, img1, img2):
        try:
            h1, w1 = img1.shape[:2]
            h2, w2 = img2.shape[:2]
            ratio1 = h1 / w1
            ratio2 = h2 / w2
            diff = abs(ratio1 - ratio2)
            return 1 - min(diff / 2.0, 1.0)
        except:
            return 0.0

    def _compare_texture_lbp(self, img1, img2):
        """Use Local Binary Pattern (LBP) for texture similarity"""
        try:
            def lbp_hist(img):
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                lbp = np.zeros_like(gray)
                for i in range(1, gray.shape[0]-1):
                    for j in range(1, gray.shape[1]-1):
                        center = gray[i,j]
                        code = 0
                        code |= (gray[i-1, j-1] > center) << 7
                        code |= (gray[i-1, j] > center) << 6
                        code |= (gray[i-1, j+1] > center) << 5
                        code |= (gray[i, j+1] > center) << 4
                        code |= (gray[i+1, j+1] > center) << 3
                        code |= (gray[i+1, j] > center) << 2
                        code |= (gray[i+1, j-1] > center) << 1
                        code |= (gray[i, j-1] > center) << 0
                        lbp[i,j] = code
                hist, _ = np.histogram(lbp.ravel(), bins=256, range=(0, 256))
                hist = hist.astype("float")
                hist /= (hist.sum() + 1e-7)
                return hist

            img1_resized = cv2.resize(img1, (64, 128))
            img2_resized = cv2.resize(img2, (64, 128))

            hist1 = lbp_hist(img1_resized)
            hist2 = lbp_hist(img2_resized)

            return cosine_similarity([hist1], [hist2])[0][0]
        except:
            return 0.0

    def _visualize_comparison(self, img1, img2, is_ambiguous, score, reasons):
        fig, axes = plt.subplots(1, 2, figsize=(14, 8))
        img1_rgb = cv2.cvtColor(img1, cv2.COLOR_BGR2RGB)
        img2_rgb = cv2.cvtColor(img2, cv2.COLOR_BGR2RGB)

        axes[0].imshow(img1_rgb)
        axes[0].set_title("Person 1", fontsize=14, fontweight='bold')
        axes[0].axis('off')

        axes[1].imshow(img2_rgb)
        axes[1].set_title("Person 2", fontsize=14, fontweight='bold')
        axes[1].axis('off')

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

# Quick test function
def quick_test():
    print(" Improved Ambiguity Checker - Ready!")
    return SimpleAmbiguityChecker()

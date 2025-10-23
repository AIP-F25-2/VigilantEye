"""
Simple test script to verify the NER system is working correctly
"""

import os
import sys
import cv2
import numpy as np

def test_imports():
    """Test if all required modules can be imported"""
    print("Testing imports...")
    
    try:
        import cv2
        print("✓ OpenCV imported successfully")
    except ImportError as e:
        print(f"✗ OpenCV import failed: {e}")
        return False
    
    try:
        import numpy as np
        print("✓ NumPy imported successfully")
    except ImportError as e:
        print(f"✗ NumPy import failed: {e}")
        return False
    
    try:
        import spacy
        print("✓ spaCy imported successfully")
    except ImportError as e:
        print(f"✗ spaCy import failed: {e}")
        return False
    
    try:
        import pytesseract
        print("✓ pytesseract imported successfully")
    except ImportError as e:
        print(f"✗ pytesseract import failed: {e}")
        return False
    
    return True

def test_opencv_functionality():
    """Test basic OpenCV functionality"""
    print("\nTesting OpenCV functionality...")
    
    try:
        # Test image creation
        img = np.ones((100, 100, 3), dtype=np.uint8) * 255
        print("✓ Image creation works")
        
        # Test face cascade loading
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        if face_cascade.empty():
            print("✗ Face cascade not loaded")
            return False
        print("✓ Face cascade loaded successfully")
        
        # Test basic operations
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        print("✓ Color conversion works")
        
        return True
    except Exception as e:
        print(f"✗ OpenCV functionality test failed: {e}")
        return False

def test_spacy_functionality():
    """Test spaCy functionality"""
    print("\nTesting spaCy functionality...")
    
    try:
        nlp = spacy.load("en_core_web_sm")
        print("✓ spaCy model loaded successfully")
        
        # Test basic NER
        doc = nlp("Apple Inc. was founded by Steve Jobs.")
        entities = [(ent.text, ent.label_) for ent in doc.ents]
        print(f"✓ NER test successful: {entities}")
        
        return True
    except OSError:
        print("✗ spaCy model not found. Install with: python -m spacy download en_core_web_sm")
        return False
    except Exception as e:
        print(f"✗ spaCy functionality test failed: {e}")
        return False

def test_ner_system():
    """Test the comprehensive NER system"""
    print("\nTesting Comprehensive NER System...")
    
    try:
        from comprehensive_ner_system import ComprehensiveNER
        
        # Initialize system
        ner = ComprehensiveNER()
        print("✓ NER system initialized successfully")
        
        # Create a test image
        test_img = np.ones((200, 300, 3), dtype=np.uint8) * 255
        cv2.putText(test_img, "Test Image", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
        
        # Save test image
        os.makedirs("uploads", exist_ok=True)
        test_path = "uploads/test_ner.jpg"
        cv2.imwrite(test_path, test_img)
        print("✓ Test image created")
        
        # Test entity detection
        results = ner.detect_all_entities(test_path)
        print(f"✓ Entity detection completed: {len(results['entities'])} entities found")
        
        # Test text extraction
        if results['extracted_text']:
            print(f"✓ Text extraction works: '{results['extracted_text']}'")
        
        # Clean up
        if os.path.exists(test_path):
            os.remove(test_path)
        
        return True
    except Exception as e:
        print(f"✗ NER system test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("Comprehensive NER System - Test Suite")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_opencv_functionality,
        test_spacy_functionality,
        test_ner_system
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 50)
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The NER system is ready to use.")
        print("\nTo run the demo:")
        print("python ner_demo.py")
    else:
        print("❌ Some tests failed. Please check the installation.")
        print("\nTo install missing dependencies:")
        print("python setup_ner.py")

if __name__ == "__main__":
    main()


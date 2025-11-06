"""
Demo script for the Comprehensive NER System
This script demonstrates how to use the NER system for various detection tasks
"""

import os
import sys
from comprehensive_ner_system import ComprehensiveNER

def create_test_image():
    """Create a simple test image with text for demonstration"""
    import cv2
    import numpy as np
    
    # Create a white image
    img = np.ones((400, 600, 3), dtype=np.uint8) * 255
    
    # Add some text
    cv2.putText(img, "Hello World!", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 0), 3)
    cv2.putText(img, "John Smith", (50, 200), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 0), 2)
    cv2.putText(img, "New York, USA", (50, 250), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
    cv2.putText(img, "January 15, 2024", (50, 300), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
    
    # Add a simple rectangle (simulating an object)
    cv2.rectangle(img, (400, 50), (550, 150), (0, 255, 0), -1)
    cv2.putText(img, "OBJECT", (420, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
    
    # Save the test image
    os.makedirs("uploads", exist_ok=True)
    cv2.imwrite("uploads/test_image.jpg", img)
    print("Created test image: uploads/test_image.jpg")
    return "uploads/test_image.jpg"

def demo_basic_detection():
    """Demonstrate basic entity detection"""
    print("=== BASIC ENTITY DETECTION DEMO ===")
    
    # Initialize NER system
    ner = ComprehensiveNER()
    
    # Create test image if it doesn't exist
    test_image = "uploads/test_image.jpg"
    if not os.path.exists(test_image):
        test_image = create_test_image()
    
    # Detect entities
    print(f"Analyzing image: {test_image}")
    results = ner.detect_all_entities(test_image)
    
    # Display results
    print(f"\nDetected {len(results['entities'])} visual entities:")
    for i, entity in enumerate(results['entities'], 1):
        print(f"{i}. {entity['type']} - {entity['text']} (confidence: {entity['confidence']:.2f})")
    
    if results['extracted_text']:
        print(f"\nExtracted text: '{results['extracted_text']}'")
        
        if results['text_entities']:
            print(f"Found {len(results['text_entities'])} text entities:")
            for i, entity in enumerate(results['text_entities'], 1):
                print(f"{i}. {entity['type']} - {entity['text']}")
    
    return results

def demo_visualization():
    """Demonstrate entity visualization"""
    print("\n=== ENTITY VISUALIZATION DEMO ===")
    
    ner = ComprehensiveNER()
    test_image = "uploads/test_image.jpg"
    
    if not os.path.exists(test_image):
        test_image = create_test_image()
    
    # Create visualization
    output_path = ner.visualize_entities(test_image, "uploads/ner_visualization.jpg")
    print(f"Visualization saved to: {output_path}")
    
    return output_path

def demo_text_ner():
    """Demonstrate text-based NER"""
    print("\n=== TEXT-BASED NER DEMO ===")
    
    ner = ComprehensiveNER()
    
    # Sample text with various entities
    sample_text = """
    Apple Inc. is a technology company founded by Steve Jobs in Cupertino, California.
    The company was established on April 1, 1976, and is now worth over $3 trillion.
    Tim Cook is the current CEO of Apple, succeeding Steve Jobs in 2011.
    Apple's headquarters are located at 1 Apple Park Way, Cupertino, CA 95014.
    """
    
    print(f"Analyzing text: {sample_text.strip()}")
    
    # Extract entities from text
    entities = ner.extract_entities_from_text(sample_text)
    
    print(f"\nFound {len(entities)} entities:")
    for i, entity in enumerate(entities, 1):
        print(f"{i}. {entity['type']} - {entity['text']} (confidence: {entity['confidence']:.2f})")
    
    return entities

def demo_custom_image(image_path):
    """Demonstrate NER on a custom image"""
    print(f"\n=== CUSTOM IMAGE ANALYSIS: {image_path} ===")
    
    if not os.path.exists(image_path):
        print(f"Error: Image file not found: {image_path}")
        return None
    
    ner = ComprehensiveNER()
    
    # Analyze the image
    results = ner.detect_all_entities(image_path)
    
    if 'error' in results:
        print(f"Error: {results['error']}")
        return None
    
    # Display results
    print(f"Image: {results['image_path']}")
    print(f"Visual entities detected: {len(results['entities'])}")
    
    for entity in results['entities']:
        print(f"  - {entity['type']}: {entity['text']} (confidence: {entity['confidence']:.2f})")
    
    if results['extracted_text']:
        print(f"\nExtracted text: {results['extracted_text']}")
        
        if results['text_entities']:
            print(f"Text entities: {len(results['text_entities'])}")
            for entity in results['text_entities']:
                print(f"  - {entity['type']}: {entity['text']}")
    
    # Create visualization
    output_path = ner.visualize_entities(image_path)
    print(f"\nVisualization saved to: {output_path}")
    
    # Save results
    ner.save_results_json(results, f"results_{os.path.basename(image_path)}.json")
    
    return results

def main():
    """Main demo function"""
    print("Comprehensive NER System Demo")
    print("=" * 50)
    
    # Check if custom image path is provided
    if len(sys.argv) > 1:
        custom_image = sys.argv[1]
        demo_custom_image(custom_image)
    else:
        # Run all demos
        demo_basic_detection()
        demo_visualization()
        demo_text_ner()
        
        print("\n" + "=" * 50)
        print("Demo completed!")
        print("\nTo analyze your own image, run:")
        print("python ner_demo.py path/to/your/image.jpg")
        print("\nTo install required dependencies, run:")
        print("pip install -r requirements_ner.txt")
        print("python -m spacy download en_core_web_sm")

if __name__ == "__main__":
    main()



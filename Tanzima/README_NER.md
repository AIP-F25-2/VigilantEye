# Comprehensive Named Entity Recognition (NER) System

A powerful NER system that combines OpenCV, spaCy, and OCR to detect entities in both images and text. This system can identify faces, objects, text regions, and perform text-based named entity recognition.

## Features

### Visual Entity Detection
- **Face Detection**: Detects frontal and profile faces using Haar cascades
- **Eye Detection**: Identifies eyes in images
- **Smile Detection**: Detects facial expressions (smiles)
- **Text Region Detection**: Finds potential text areas using MSER
- **Object Detection**: Uses YOLO for advanced object recognition (optional)

### Text-Based NER
- **OCR Integration**: Extracts text from images using Tesseract
- **spaCy NER**: Performs named entity recognition on extracted text
- **Entity Types**: Detects PERSON, ORG, GPE, DATE, MONEY, and more

### Visualization & Output
- **Bounding Box Visualization**: Draws colored boxes around detected entities
- **JSON Export**: Saves detection results in structured format
- **Confidence Scores**: Provides confidence levels for each detection

## Installation

### Quick Setup
```bash
python setup_ner.py
```

### Manual Installation

1. **Install Python dependencies:**
```bash
pip install -r requirements_ner.txt
```

2. **Install spaCy model:**
```bash
python -m spacy download en_core_web_sm
```

3. **Install Tesseract OCR:**
   - **macOS**: `brew install tesseract`
   - **Ubuntu**: `sudo apt-get install tesseract-ocr`
   - **Windows**: Download from [Tesseract Wiki](https://github.com/UB-Mannheim/tesseract/wiki)

4. **Download YOLO models (optional):**
   The system will automatically download YOLO models when first run, or you can run:
   ```bash
   python setup_ner.py
   ```

## Usage

### Basic Usage

```python
from comprehensive_ner_system import ComprehensiveNER

# Initialize the NER system
ner = ComprehensiveNER()

# Detect entities in an image
results = ner.detect_all_entities("path/to/image.jpg")

# Print results
print(f"Found {len(results['entities'])} entities")
for entity in results['entities']:
    print(f"- {entity['type']}: {entity['text']}")

# Create visualization
ner.visualize_entities("path/to/image.jpg", "output.jpg")
```

### Demo Script

Run the demo to see the system in action:

```bash
# Run with default test image
python ner_demo.py

# Run with your own image
python ner_demo.py path/to/your/image.jpg
```

### Text-Only NER

```python
from comprehensive_ner_system import ComprehensiveNER

ner = ComprehensiveNER()

# Extract entities from text
text = "Apple Inc. was founded by Steve Jobs in Cupertino, California."
entities = ner.extract_entities_from_text(text)

for entity in entities:
    print(f"{entity['type']}: {entity['text']}")
```

## Entity Types

### Visual Entities
- **PERSON**: Detected faces (frontal/profile)
- **BODY_PART**: Eyes, hands, etc.
- **EXPRESSION**: Smiles, emotions
- **TEXT_REGION**: Areas containing text
- **OBJECT**: Various objects (when YOLO is available)

### Text Entities (spaCy)
- **PERSON**: People's names
- **ORG**: Organizations, companies
- **GPE**: Countries, cities, states
- **DATE**: Dates and times
- **MONEY**: Monetary values
- **PERCENT**: Percentages
- **CARDINAL**: Numbers
- **ORDINAL**: Ordinal numbers
- **LOC**: Locations
- **EVENT**: Named events
- **FAC**: Buildings, airports, highways
- **LANGUAGE**: Languages
- **LAW**: Legal documents
- **NORP**: Nationalities, religious groups
- **PRODUCT**: Products, vehicles
- **WORK_OF_ART**: Books, songs, movies

## Configuration

### YOLO Model Setup
The system automatically looks for YOLO models in the `models/` directory:
- `yolov3-tiny.cfg`
- `yolov3-tiny.weights`
- `coco.names`

If these files are not found, the system will work without YOLO object detection.

### Tesseract Configuration
The system uses pytesseract for OCR. You may need to configure the path:

```python
# macOS with Homebrew
pytesseract.pytesseract.tesseract_cmd = '/opt/homebrew/bin/tesseract'

# Windows
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
```

## Output Format

### Detection Results
```json
{
  "image_path": "path/to/image.jpg",
  "entities": [
    {
      "type": "PERSON",
      "subtype": "FACE_FRONTAL",
      "bbox": [100, 50, 200, 150],
      "confidence": 0.85,
      "text": "Face (Frontal)"
    }
  ],
  "extracted_text": "Hello World!",
  "text_entities": [
    {
      "type": "PERSON",
      "subtype": "TEXT_ENTITY",
      "bbox": null,
      "confidence": 0.9,
      "text": "John Smith",
      "start": 0,
      "end": 10
    }
  ]
}
```

## Performance Tips

1. **Image Size**: Larger images take longer to process but may provide better accuracy
2. **YOLO Models**: YOLO provides better object detection but requires more computational resources
3. **OCR Accuracy**: Preprocessing images (contrast, noise reduction) can improve OCR results
4. **Batch Processing**: For multiple images, consider processing them in batches

## Troubleshooting

### Common Issues

1. **spaCy model not found**:
   ```bash
   python -m spacy download en_core_web_sm
   ```

2. **Tesseract not found**:
   - Install Tesseract OCR for your operating system
   - Configure the path in your code if needed

3. **YOLO models not loading**:
   - Run `python setup_ner.py` to download models
   - Check that model files are in the `models/` directory

4. **OpenCV errors**:
   - Ensure OpenCV is properly installed: `pip install opencv-python`
   - Check that you have the required system dependencies

### Performance Issues

- **Slow processing**: Reduce image size or disable YOLO if not needed
- **Memory issues**: Process images one at a time for large batches
- **Low accuracy**: Ensure good image quality and proper lighting

## Examples

See the `ner_demo.py` file for comprehensive examples of:
- Basic entity detection
- Visualization creation
- Text-based NER
- Custom image analysis

## License

This project is part of the VigilantEye system and follows the same licensing terms.


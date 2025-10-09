import spacy

# Load the spaCy English model (this downloads once)
nlp = spacy.load("en_core_web_sm")

def extract_entities(text):
    """
    Extract named entities from the given text using spaCy.
    Returns a list of (entity_text, entity_label) tuples.
    """
    doc = nlp(text)
    entities = [(ent.text, ent.label_) for ent in doc.ents]
    return entities
python Object_detection_opencv.py


from typing import List, Dict, Any
import logging
from transformers import pipeline

logger = logging.getLogger(__name__)

# Granular labels for document classification
DOCUMENT_LABELS = [
    "social security card",
    "voter card",
    "drivers license",
    "passport",
    "aadhaar card",
    "pan card",
    "credit card",
    "utility bill",
    "bank statement",
    "newspaper article",
    "magazine cover",
    "book cover",
    "academic textbook",
    "business invoice",
    "restaurant receipt",
    "handwritten note",
    "legal contract",
    "certificate",
    "map",
    "menu",
    "medical prescription",
    "newspaper",
    "magazine",
    "novel"
]

_model_cache = {}

def get_document_classifier():
    """Lazy load the classifier pipeline."""
    if "doc_classifier" in _model_cache:
        return _model_cache["doc_classifier"]

    logger.info("Loading CLIP model for granular document classification...")
    classifier = pipeline("zero-shot-image-classification", model="openai/clip-vit-base-patch32")
    _model_cache["doc_classifier"] = classifier
    return classifier

def classify_document(image_path: str, threshold: float = 0.3) -> List[Dict[str, Any]]:
    """
    Perform granular document classification using CLIP.
    """
    try:
        classifier = get_document_classifier()
        results = classifier(image_path, candidate_labels=DOCUMENT_LABELS)
        
        # Filter by threshold and take top results
        top_results = [r for r in results if r['score'] > threshold]
        
        # If nothing meets threshold, take the top one if it's somewhat decent
        if not top_results and results and results[0]['score'] > 0.15:
            top_results = [results[0]]
            
        return top_results
    except Exception as e:
        logger.error(f"Error in document classification: {e}")
        return []

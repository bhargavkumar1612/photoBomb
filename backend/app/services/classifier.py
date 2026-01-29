from typing import List, Dict, Any
try:
    from transformers import pipeline
    HAS_TRANSFORMERS = True
except ImportError:
    HAS_TRANSFORMERS = False

_model_cache = {}

# Labels (Expanded to absorb probability mass for people/screenshots)
CANDIDATE_LABELS = [
    # People
    "person", "man", "woman", "human", "child", "group of people", "selfie", "crowd",
    # Animals
    "animal", "dog", "cat", "bird", "wildlife", "pet", "horse",
    # Documents & Screenshots
    "document", "receipt", "invoice", "text", "paper", 
    "screenshot", "computer screen", "interface", "software",
    # Nature
    "nature", "beach", "mountain", "forest", "sunset", "sky", "tree", "flower", "outdoor",
    # Places / Architecture
    "city", "building", "architecture", "street", "house", "landmark", "room", "indoor",
    # Misc
    "food", "vehicle"
]

def get_scene_classifier():
    """Lazy load the classifier pipeline."""
    if "scene_classifier" in _model_cache:
        return _model_cache["scene_classifier"]

    if not HAS_TRANSFORMERS:
        raise ImportError("transformers library not installed")

    print("Loading CLIP model for scene classification...")
    # Use CPU by default or whatever is optimal. Transformers handles MPS/CUDA if available usually.
    classifier = pipeline("zero-shot-image-classification", model="openai/clip-vit-base-patch32")
    _model_cache["scene_classifier"] = classifier
    return classifier

def determine_category(label: str) -> str:
    """Map a label to a fixed category."""
    if label in ["person", "man", "woman", "human", "child", "group of people", "selfie", "crowd"]:
        return "people"
    elif label in ["animal", "dog", "cat", "bird", "wildlife", "pet", "horse"]:
        return "animals"
    elif label in [
        "document", "receipt", "invoice", "text", "paper", "screenshot", "computer screen", "interface", "software",
        "nature", "beach", "mountain", "forest", "sunset", "sky", "tree", "flower", "outdoor",
        "city", "building", "architecture", "street", "house", "landmark", "room", "indoor"
    ]:
        return "documents"
    return "general"

def classify_image(image_path: str, threshold: float = 0.4) -> List[Dict[str, Any]]:
    """
    Classify an image file using CLIP.
    Returns list of dicts: [{'label': str, 'score': float, 'category': str}]
    """
    try:
        classifier = get_scene_classifier()
        results = classifier(image_path, candidate_labels=CANDIDATE_LABELS)
        
        # 1. Sort by score
        results = sorted(results, key=lambda x: x['score'], reverse=True)
        
        # 2. Filter by threshold
        top_results = [r for r in results if r['score'] > threshold]
        
        # Fallback if nothing met threshold but we have a decent best guess
        if not top_results and results and results[0]['score'] > 0.25:
            top_results = [results[0]]
            
        final_results = []
        for res in top_results:
            cat = determine_category(res['label'])
            final_results.append({
                'label': res['label'],
                'score': res['score'],
                'category': cat
            })
            
        return final_results
    except Exception as e:
        print(f"Error classifying image: {e}")
        return []

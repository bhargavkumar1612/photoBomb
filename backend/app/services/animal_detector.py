from PIL import Image
from typing import List, Dict, Any, Tuple
import logging

logger = logging.getLogger(__name__)

# Singleton models to avoid reloading
_detr_processor = None
_detr_model = None
_clip_model = None
_clip_processor = None

def get_detr_model():
    global _detr_processor, _detr_model
    if _detr_model is None:
        logger.info("Loading DETR model for animal detection...")
        from transformers import DetrImageProcessor, DetrForObjectDetection
        _detr_processor = DetrImageProcessor.from_pretrained("facebook/detr-resnet-50", use_safetensors=False)
        _detr_model = DetrForObjectDetection.from_pretrained("facebook/detr-resnet-50", use_safetensors=False)
    return _detr_processor, _detr_model

def get_clip_model():
    global _clip_model, _clip_processor
    if _clip_model is None:
        logger.info("Loading CLIP model for animal embeddings...")
        from transformers import CLIPProcessor, CLIPModel
        _clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32", use_safetensors=False)
        _clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32", use_safetensors=False)
    return _clip_processor, _clip_model

ANIMAL_LABELS = {
    'cat', 'dog', 'horse', 'sheep', 'cow', 'elephant', 'bear', 'zebra', 'giraffe', 'bird'
}

def detect_animals(image_path: str, threshold: float = 0.7) -> List[Dict[str, Any]]:
    """
    Detect animals in an image and return bounding boxes and labels.
    """
    try:
        import torch
        processor, model = get_detr_model()
        image = Image.open(image_path).convert("RGB")
        inputs = processor(images=image, return_tensors="pt")
        outputs = model(**inputs)

        # convert outputs (bounding boxes and class logits) to COCO API
        # let's only keep detections with score > threshold
        target_sizes = torch.tensor([image.size[::-1]])
        results = processor.post_process_object_detection(outputs, target_sizes=target_sizes, threshold=threshold)[0]

        detections = []
        for score, label, box in zip(results["scores"], results["labels"], results["boxes"]):
            label_name = model.config.id2label[label.item()]
            if label_name in ANIMAL_LABELS:
                box = [round(i, 2) for i in box.tolist()]
                detections.append({
                    "label": label_name,
                    "confidence": round(score.item(), 3),
                    "box": box  # [xmin, ymin, xmax, ymax]
                })
        
        return detections
    except Exception as e:
        logger.error(f"Error in animal detection: {e}")
        return []

def get_animal_embedding(image_path: str, box: List[float]) -> List[float]:
    """
    Crop an animal from the image and get its CLIP embedding.
    """
    try:
        import torch
        processor, model = get_clip_model()
        image = Image.open(image_path).convert("RGB")
        
        # box is [xmin, ymin, xmax, ymax]
        crop = image.crop((box[0], box[1], box[2], box[3]))
        
        inputs = processor(images=crop, return_tensors="pt")
        with torch.no_grad():
            vision_outputs = model.vision_model(**inputs)
            image_features = model.visual_projection(vision_outputs.pooler_output)
        
        # Normalize and flatten to 1D list
        embedding = image_features[0] / image_features[0].norm(p=2, dim=-1, keepdim=True)
        return embedding.cpu().detach().numpy().flatten().tolist()
    except Exception as e:
        logger.error(f"Error getting animal embedding: {e}")
        return None

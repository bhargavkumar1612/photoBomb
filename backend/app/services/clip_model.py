from typing import Tuple
import logging
import gc
from app.core.config import settings

logger = logging.getLogger(__name__)

# Singleton models to avoid reloading
_clip_model = None
_clip_processor = None

def get_clip_model():
    """
    Load CLIP model for embeddings and classification.
    Uses singleton pattern to share model across different services.
    """
    global _clip_model, _clip_processor
    if _clip_model is None:
        logger.info("Loading CLIP model for shared use (Scene/Doc Classification)...")
        from transformers import CLIPProcessor, CLIPModel
        
        # Use safetensors for memory efficiency if available, otherwise fallback
        # Given the OOM issues, we explicitly prefer safetensors and aggressive GC
        token = settings.HF_TOKEN if settings.HF_TOKEN else None
        try:
            _clip_model = CLIPModel.from_pretrained(
                "openai/clip-vit-base-patch32", 
                use_safetensors=True,
                token=token
            )
            _clip_processor = CLIPProcessor.from_pretrained(
                "openai/clip-vit-base-patch32",
                use_safetensors=True,
                token=token
            )
        except Exception as e:
            logger.warning(f"Could not load safetensors, falling back to default: {e}")
            _clip_model = CLIPModel.from_pretrained(
                "openai/clip-vit-base-patch32",
                use_safetensors=False,
                token=token
            )
            _clip_processor = CLIPProcessor.from_pretrained(
                "openai/clip-vit-base-patch32",
                use_safetensors=False,
                token=token
            )
            
        # Force GC
        gc.collect()
        
    return _clip_processor, _clip_model

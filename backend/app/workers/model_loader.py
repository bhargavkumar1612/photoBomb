import logging
from celery.signals import worker_process_init
from app.services.animal_detector import get_detr_model, get_clip_model

logger = logging.getLogger(__name__)

@worker_process_init.connect
def preload_models(**kwargs):
    """
    Preload heavy AI models into memory when the worker process starts.
    This avoids the latency penalty on the first task execution.
    """
    logger.info("⚡ Preloading AI models into memory...")
    
    try:
        # Load DETR (Object Detection)
        get_detr_model()
        logger.info("✅ DETR model loaded.")
        
        # Load CLIP (Embeddings)
        get_clip_model()
        logger.info("✅ CLIP model loaded.")
        
    except Exception as e:
        logger.error(f"❌ Failed to preload models: {e}")

if __name__ == "__main__":
    # Allow running this script directly to pre-cache models during build
    logging.basicConfig(level=logging.INFO)
    preload_models()

"""
Script to pre-download AI models during Docker build.
This prevents runtime network timeouts and permission errors.
"""
import os
import sys

# Set cache directory to env var or default
cache_dir = os.environ.get("HF_HOME", "/app/model_cache")
os.makedirs(cache_dir, exist_ok=True)

print(f"Pre-loading models to {cache_dir}...")

try:
    # 1. HuggingFace Models (CLIP, DETR)
    from transformers import CLIPModel, CLIPProcessor, DetrImageProcessor, DetrForObjectDetection
    
    print("Downloading CLIP model (openai/clip-vit-base-patch32)...")
    CLIPModel.from_pretrained("openai/clip-vit-base-patch32", cache_dir=cache_dir)
    CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32", cache_dir=cache_dir)
    
    print("Downloading DETR model (facebook/detr-resnet-50)...")
    DetrImageProcessor.from_pretrained("facebook/detr-resnet-50", cache_dir=cache_dir)
    DetrForObjectDetection.from_pretrained("facebook/detr-resnet-50", cache_dir=cache_dir)

    # 2. Face Recognition Models (dlib)
    # These are usually downloaded by face_recognition at runtime to ~/.face_recognition_models
    # We will trigger the download by importing and accessing them, or manually downloading if needed.
    # face_recognition module checks for files in specific locations.
    print("Downloading face_recognition models...")
    import face_recognition_models
    # The library 'face_recognition_models' has the model files. 
    # Just importing 'face_recognition' usually checks their existence.
    # However, to be safe, we can inspect where they are.
    print(f"Face recognition models found at: {face_recognition_models.pose_predictor_model_location()}")

    print("✅ All models pre-loaded successfully.")

except Exception as e:
    print(f"❌ Error pre-loading models: {e}")
    sys.exit(1)

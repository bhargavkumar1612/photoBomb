from app.core.config import settings
from app.services.storage_interface import StorageInterface
from app.services.storage_providers.b2_native_service import B2NativeService
from app.services.storage_providers.s3_service import S3Service

_storage_instances = {}

def get_storage_service(provider: str = None) -> StorageInterface:
    """
    Get storage provider instance.
    If provider is not specified, uses the default from settings.
    """
    global _storage_instances
    
    if not provider:
        provider = settings.STORAGE_PROVIDER.lower()
    
    if provider in _storage_instances:
        return _storage_instances[provider]
        
    print(f"Initializing Storage Provider: {provider}")
    
    if provider == "s3":
        instance = S3Service()
    elif provider == "b2_native":
        instance = B2NativeService()
    else:
        # Fallback or Error
        print(f"Unknown storage provider '{provider}', defaulting to B2 Native")
        instance = B2NativeService()
        
    _storage_instances[provider] = instance
    return instance

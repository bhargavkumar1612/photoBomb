from typing import Protocol, Dict, Optional, Any, List

class StorageInterface(Protocol):
    """
    Abstract interface for storage providers (B2, S3/R2).
    Supports both synchronous and asynchronous operations where applicable,
    though purely async interface is preferred for new code.
    """

    def generate_presigned_upload_url(
        self,
        filename: str,
        user_id: str,
        upload_id: str
    ) -> Dict[str, Any]:
        """
        Generate URL for direct browser upload.
        Returns:
            {
                "upload_url": str,
                "authorization_token": str (optional, context dependent),
                "b2_key": str (legacy name, or key),
                "expires_at": str
            }
        """
        ...

    def generate_presigned_url(
        self, 
        key: str, 
        expires_in: int = 3600
    ) -> str:
        """Generate signed URL for GET access (download)."""
        ...

    def get_download_url_base(self) -> str:
        """Return base URL for downloads (legacy B2 compatibility)."""
        ...

    def get_download_authorization(self, prefix: str, valid_duration: int = 86400) -> str:
        """
        Legacy B2 prefix authorization. 
        For S3, this might return a dummy or throw NotImplemented if we refactor away from it.
        """
        ...

    def upload_file(
        self, 
        local_path: str, 
        key: str, 
        content_type: str = "application/octet-stream"
    ) -> Dict[str, Any]:
        """Upload local file to storage."""
        ...

    def upload_bytes(
        self,
        data_bytes: bytes,
        key: str,
        content_type: str = "application/octet-stream"
    ) -> Dict[str, Any]:
        """Upload bytes directly to storage."""
        ...

    def download_file_bytes(self, key: str) -> bytes:
        """Download file content as bytes."""
        ...

    def delete_file(self, key: str):
        """Delete file at key."""
        ...
        
    def list_files(self, prefix: str, max_files: int = 1000) -> List[Dict[str, Any]]:
        """List files with prefix."""
        ...

    def file_exists(self, key: str) -> bool:
        """Check if file exists in storage."""
        ...

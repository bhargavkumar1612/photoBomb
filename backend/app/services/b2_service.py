"""
Backblaze B2 storage integration.
Handles file uploads, downloads, and presigned URL generation.
"""
from b2sdk.v2 import B2Api, InMemoryAccountInfo
from b2sdk.v2.exception import B2Error
from typing import Optional, Dict
import hashlib
from datetime import datetime, timedelta

from app.core.config import settings


class B2Service:
    """Service for Backblaze B2 operations."""
    
    def __init__(self):
        """Initialize B2 API client."""
        self.info = InMemoryAccountInfo()
        self.api = B2Api(self.info)
        self._authorized = False
    
    def authorize(self):
        """Authorize with B2 (lazy initialization)."""
        if not self._authorized:
            self.api.authorize_account(
                "production",
                settings.B2_APPLICATION_KEY_ID,
                settings.B2_APPLICATION_KEY
            )
            self._authorized = True
    
    def get_bucket(self):
        """Get the configured B2 bucket."""
        self.authorize()
        return self.api.get_bucket_by_name(settings.B2_BUCKET_NAME)
    
    def generate_presigned_upload_url(
        self,
        filename: str,
        user_id: str,
        upload_id: str
    ) -> dict:
        """
        Generate presigned URL for direct browser upload.
        
        Returns dict with upload_url, authorization_token, b2_key, expires_at.
        """
        self.authorize()
        
        # Get bucket
        bucket = self.api.get_bucket_by_name(settings.B2_BUCKET_NAME)
        
        # Generate B2 key (path in bucket)
        b2_key = f"uploads/{user_id}/{upload_id}/original/{filename}"
        
        # Use raw HTTP API to get upload URL
        import requests
        
        # Get account auth token
        auth_token = self.info.get_account_auth_token()
        api_url = self.info.get_api_url()
        
        # Call b2_get_upload_url
        response = requests.post(
            f"{api_url}/b2api/v2/b2_get_upload_url",
            headers={"Authorization": auth_token},
            json={"bucketId": bucket.id_}
        )
        response.raise_for_status()
        upload_data = response.json()
        
        # Presigned URLs valid for 15 minutes
        expires_at = (datetime.utcnow() + timedelta(minutes=15)).isoformat() + 'Z'
        
        return {
            "upload_url": upload_data["uploadUrl"],
            "authorization_token": upload_data["authorizationToken"],
            "b2_key": b2_key,
            "expires_at": expires_at
        }
    
    def download_file_bytes(
        self,
        b2_key: str
    ) -> bytes:
        """
        Download file content from B2.
        
        Args:
            b2_key: Object key in B2 bucket
        
        Returns:
            File bytes
        """
        self.authorize()
        bucket = self.get_bucket()
        
        # Download file using B2's download API
        import requests
        
        # Get download URL
        download_url = f"{self.info.get_download_url()}/file/{bucket.name}/{b2_key}"
        
        # Get authorization token
        auth_token = self.info.get_account_auth_token()
        
        # Download the file
        response = requests.get(
            download_url,
            headers={"Authorization": auth_token}
        )
        response.raise_for_status()
        
        return response.content

    
    def upload_file(
        self,
        local_path: str,
        b2_key: str,
        content_type: str = "application/octet-stream"
    ) -> Dict[str, any]:
        """
        Upload a file directly to B2 (used by workers).
        
        Args:
            local_path: Path to local file
            b2_key: Destination key in B2
            content_type: MIME type
        
        Returns:
            B2 file info dict
        """
        self.authorize()
        bucket = self.get_bucket()
        
        # Use raw HTTP API to upload
        import requests
        import hashlib
        import os
        
        # Get upload URL
        auth_token = self.info.get_account_auth_token()
        api_url = self.info.get_api_url()
        
        response = requests.post(
            f"{api_url}/b2api/v2/b2_get_upload_url",
            headers={"Authorization": auth_token},
            json={"bucketId": bucket.id_}
        )
        response.raise_for_status()
        upload_data = response.json()
        
        # Read file and compute SHA1
        with open(local_path, 'rb') as f:
            file_bytes = f.read()
        
        file_sha1 = hashlib.sha1(file_bytes).hexdigest()
        file_size = len(file_bytes)
        
        # Upload file
        from urllib.parse import quote
        
        # B2 requires file names to be URL-encoded in the header
        encoded_b2_key = quote(b2_key, safe='/')
        
        upload_response = requests.post(
            upload_data["uploadUrl"],
            headers={
                "Authorization": upload_data["authorizationToken"],
                "X-Bz-File-Name": encoded_b2_key,
                "Content-Type": content_type,
                "Content-Length": str(file_size),
                "X-Bz-Content-Sha1": file_sha1
            },
            data=file_bytes
        )
        upload_response.raise_for_status()
        file_info = upload_response.json()
        
        return {
            "file_id": file_info["fileId"],
            "file_name": file_info["fileName"],
            "size": file_info["contentLength"],
            "content_type": file_info["contentType"],
            "upload_timestamp": file_info["uploadTimestamp"]
        }

    
    def delete_file(self, file_id: str, file_name: str):
        """
        Delete a file from B2.
        
        Args:
            file_id: B2 file ID
            file_name: B2 file name
        """
        self.authorize()
        self.api.delete_file_version(file_id, file_name)
    
    def get_file_info(self, file_id: str) -> Optional[Dict]:
        """
        Get file metadata from B2.
        
        Args:
            file_id: B2 file ID
        
        Returns:
            File info dict or None
        """
        self.authorize()
        try:
            file_version = self.api.get_file_info(file_id)
            return {
                "file_id": file_version.id_,
                "file_name": file_version.file_name,
                "size": file_version.size,
                "content_type": file_version.content_type
            }
        except B2Error:
            return None


# Singleton instance
b2_service = B2Service()

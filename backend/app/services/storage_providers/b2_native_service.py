from app.services.storage_interface import StorageInterface
from app.core.config import settings
from b2sdk.v2 import B2Api, InMemoryAccountInfo
from b2sdk.v2.exception import B2Error
from datetime import datetime, timedelta
from typing import Dict, Any, List
import requests

class B2NativeService:
    """
    Backblaze B2 Native Storage Provider (Legacy).
    """
    
    def __init__(self):
        self.info = InMemoryAccountInfo()
        self.api = B2Api(self.info)
        self._authorized = False
    
    def authorize(self):
        if not self._authorized:
            self.api.authorize_account(
                "production",
                settings.B2_APPLICATION_KEY_ID,
                settings.B2_APPLICATION_KEY
            )
            self._authorized = True
            
    def get_bucket(self):
        self.authorize()
        return self.api.get_bucket_by_name(settings.B2_BUCKET_NAME)

    def generate_presigned_upload_url(
        self,
        filename: str,
        user_id: str,
        upload_id: str
    ) -> Dict[str, Any]:
        self.authorize()
        bucket = self.get_bucket()
        b2_key = f"uploads/{user_id}/{upload_id}/original/{filename}"
        
        auth_token = self.info.get_account_auth_token()
        api_url = self.info.get_api_url()
        
        response = requests.post(
            f"{api_url}/b2api/v2/b2_get_upload_url",
            headers={"Authorization": auth_token},
            json={"bucketId": bucket.id_}
        )
        response.raise_for_status()
        upload_data = response.json()
        
        expires_at = (datetime.utcnow() + timedelta(minutes=15)).isoformat() + 'Z'
        
        return {
            "upload_url": upload_data["uploadUrl"],
            "authorization_token": upload_data["authorizationToken"],
            "b2_key": b2_key,
            "expires_at": expires_at
        }

    def generate_presigned_url(self, key: str, expires_in: int = 3600) -> str:
        # B2 Native doesn't have "Pre-signed GET URL" in the same way as S3.
        # It uses Authorize Download token + base URL.
        # We can simulate a per-file URL here.
        self.authorize()
        
        # Determine prefix or full match. Using full match logic.
        # Ideally we should authorize specific file name prefix like 'key'
        token = self.get_download_authorization(key, valid_duration=expires_in)
        
        download_url = self.info.get_download_url()
        bucket_name = settings.B2_BUCKET_NAME
        
        # B2 URL structure requires bucket name
        final_url = f"{download_url}/file/{bucket_name}/{key}?Authorization={token}"
        return final_url

    def get_download_url_base(self) -> str:
        self.authorize()
        return self.info.get_download_url()

    def get_download_authorization(self, prefix: str, valid_duration: int = 86400) -> str:
        """Legacy support for B2 batch auth."""
        self.authorize()
        bucket = self.get_bucket()
        auth_token = self.info.get_account_auth_token()
        api_url = self.info.get_api_url()
        
        response = requests.post(
            f"{api_url}/b2api/v2/b2_get_download_authorization",
            headers={"Authorization": auth_token},
            json={
                "bucketId": bucket.id_,
                "fileNamePrefix": prefix,
                "validDurationInSeconds": valid_duration
            }
        )
        response.raise_for_status()
        return response.json()['authorizationToken']

    def upload_file(self, local_path: str, key: str, content_type: str = "application/octet-stream") -> Dict[str, Any]:
        self.authorize()
        bucket = self.get_bucket()
        file_info = bucket.upload_local_file(
            local_file=local_path,
            file_name=key,
            content_type=content_type,
            # file_infos={}, # metadata
        )
        return {
            "file_id": file_info.id_,
            "file_name": file_info.file_name,
            "size": file_info.size,
            "content_type": file_info.content_type,
            "upload_timestamp": file_info.upload_timestamp
        }

    def upload_bytes(self, data_bytes: bytes, key: str, content_type: str = "application/octet-stream") -> Dict[str, Any]:
        self.authorize()
        bucket = self.get_bucket()
        file_info = bucket.upload_bytes(
            data_bytes=data_bytes,
            file_name=key,
            content_type=content_type
        )
        return {
            "file_id": file_info.id_,
            "size": file_info.size, # Note: UploadedBytes object might differ slightly in attributes
            "upload_timestamp": file_info.upload_timestamp
        }

    def download_file_bytes(self, key: str) -> bytes:
        self.authorize()
        # Using requests to download from download_url
        download_url = self.info.get_download_url()
        bucket_name = settings.B2_BUCKET_NAME
        auth_token = self.info.get_account_auth_token()
        
        url = f"{download_url}/file/{bucket_name}/{key}"
        response = requests.get(url, headers={"Authorization": auth_token})
        response.raise_for_status()
        return response.content

    def delete_file(self, key: str):
        self.authorize()
        bucket = self.get_bucket()
        # B2 needs file ID to delete version properly usually, but sdk might help by name
        # bucket.hide_file(key) # This is soft delete
        # To delete, we need to list versions and delete them.
        versions = bucket.list_file_versions(key)
        for version in versions:
            match = version # generator yields FileVersionInfo
            # access might be .file_name, .id_
            self.api.delete_file_version(match.id_, match.file_name)

    def list_files(self, prefix: str, max_files: int = 1000) -> List[Dict[str, Any]]:
        self.authorize()
        bucket = self.get_bucket()
        files = []
        for file_version, _ in bucket.ls(folder_to_list=prefix, recursive=True):
            files.append({
                "file_name": file_version.file_name,
                "file_id": file_version.id_,
                "size": file_version.size,
                "upload_timestamp": file_version.upload_timestamp
            })
            if len(files) >= max_files:
                break
        return files

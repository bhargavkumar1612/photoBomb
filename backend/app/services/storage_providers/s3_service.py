from app.services.storage_interface import StorageInterface
from app.core.config import settings
import aioboto3
import boto3
from botocore.config import Config
from datetime import datetime, timedelta
import os
from typing import Dict, Any, List

class S3Service:
    """
    S3 Compatible Storage Service (R2, AWS, MinIO).
    Implements StorageInterface.
    Uses aioboto3 for async operations where beneficial, or boto3 for sync compatibility.
    """
    
    def __init__(self):
        self.endpoint_url = settings.S3_ENDPOINT_URL
        self.access_key = settings.S3_ACCESS_KEY_ID
        self.secret_key = settings.S3_SECRET_ACCESS_KEY
        self.bucket_name = settings.S3_BUCKET_NAME
        self.region_name = settings.S3_REGION_NAME
        
        self.session = boto3.session.Session()
        # We start with sync client for simple URL signing which is local CPU bound anyway
        self.s3_client = self.session.client(
            's3',
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name=self.region_name,
            config=Config(signature_version='s3v4')
        )

    def generate_presigned_upload_url(
        self,
        filename: str,
        user_id: str,
        upload_id: str
    ) -> Dict[str, Any]:
        """
        Generate S3 Presigned POST URL.
        """
        key = f"{settings.STORAGE_PATH_PREFIX}/{user_id}/{upload_id}/original/{filename}"
        
        # Generate presigned POST parameters
        # Expires in 1 hour
        try:
            response = self.s3_client.generate_presigned_post(
                Bucket=self.bucket_name,
                Key=key,
                ExpiresIn=3600
            )
        except Exception as e:
            print(f"Error generating presigned upload: {e}")
            raise

        # S3 returns 'url' and 'fields'
        # We need to adapt this to our API response format expected by frontend/upload.py
        # Current 'upload.py' returns: presigned_url, authorization_token, b2_key
        
        # For S3, 'authorization_token' isn't a single header token like B2.
        # It's a set of form 'fields'.
        # However, our current 'upload.py' logic for `/presign` is designed for B2's API which returns `uploadUrl` and `authorizationToken`.
        # The frontend likely expects to PUT or POST to this URL with that Token.
        
        # If we use `/direct` endpoint (backend proxy), we don't use this method essentially.
        # If we use browser-direct upload, we need to return the fields.
        
        # Let's conform to the return dict, but maybe shove fields into 'authorization_token' as JSON string?
        # A bit hacky. ideally refactor API.
        # But wait, looking at `upload.py`:
        # `b2_key = f"{settings.STORAGE_PATH_PREFIX}/{user_id}/{upload_id}/original/{filename}"`
        # It returns `presigned_url` and `authorization_token`.
        
        return {
            "upload_url": response['url'],
            "authorization_token": str(response['fields']), # Placeholder, strictly specific to S3 direct form post
            "b2_key": key, # Generic key
            "expires_at": (datetime.utcnow() + timedelta(hours=1)).isoformat() + 'Z',
            "s3_fields": response['fields'] # Extra field for S3 aware clients
        }

    def generate_presigned_url(self, key: str, expires_in: int = 3600) -> str:
        """Generate GET URL."""
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': key},
                ExpiresIn=expires_in
            )
            return url
        except Exception as e:
            print(f"Error signing URL: {e}")
            return ""

    def get_download_url_base(self) -> str:
        # Not really applicable for S3 presigned URLs as they contain the base.
        # Can return endpoint.
        return self.endpoint_url

    def get_download_authorization(self, prefix: str, valid_duration: int = 86400) -> str:
        """
        S3 DOES NOT SUPPORT PREFIX TOKENS.
        We return a dummy token or potentially a pre-signed URL for the prefix if listing?
        The caller (sharing.py / albums.py) must be refactored to NOT use this token 
        and instead call `generate_presigned_url` for each file.
        """
        return "s3-does-not-support-prefix-tokens"

    def upload_file(self, local_path: str, key: str, content_type: str = "application/octet-stream") -> Dict[str, Any]:
        """Synchronous upload (via boto3)."""
        try:
            extra_args = {'ContentType': content_type}
            self.s3_client.upload_file(local_path, self.bucket_name, key, ExtraArgs=extra_args)
            
            # Retrieve basic info (or assume from local)
            size = os.path.getsize(local_path)
            
            return {
                "file_id": key, # S3 uses Key as ID
                "file_name": key.split('/')[-1],
                "size": size,
                "content_type": content_type,
                "upload_timestamp": int(datetime.utcnow().timestamp() * 1000)
            }
        except Exception as e:
            print(f"S3 Upload Error: {e}")
            raise

    def upload_bytes(self, data_bytes: bytes, key: str, content_type: str = "application/octet-stream") -> Dict[str, Any]:
        """Upload bytes."""
        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=data_bytes,
                ContentType=content_type
            )
            return {
                "file_id": key,
                "size": len(data_bytes),
                "upload_timestamp": int(datetime.now().timestamp() * 1000)
            }
        except Exception as e:
            print(f"S3 Bytes Upload Error: {e}")
            raise

    def download_file_bytes(self, key: str) -> bytes:
        """Download bytes."""
        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)
            return response['Body'].read()
        except Exception as e:
            print(f"S3 Download Error: {e}")
            raise

    def delete_file(self, key: str):
        """Delete object."""
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=key)
        except Exception as e:
            print(f"S3 Delete Error: {e}")
            # Don't raise if strict consistency isn't required, or raise?
            pass

    def list_files(self, prefix: str, max_files: int = 1000) -> List[Dict[str, Any]]:
        """List objects."""
        try:
            paginator = self.s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=self.bucket_name, Prefix=prefix, PaginationConfig={'MaxItems': max_files})
            
            files = []
            for page in pages:
                if 'Contents' in page:
                    for obj in page['Contents']:
                        files.append({
                            "file_name": obj['Key'].split('/')[-1],
                            "file_id": obj['Key'], # Key is ID
                            "size": obj['Size'],
                            "upload_timestamp": int(obj['LastModified'].timestamp() * 1000)
                        })
            return files
        except Exception as e:
            print(f"S3 List Error: {e}")
            return []

    def file_exists(self, key: str) -> bool:
        """Check if file exists in storage."""
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=key)
            return True
        except Exception:
            return False


import boto3
from botocore.config import Config
import requests
import os

def load_env():
    env_vars = {}
    try:
        with open('.env') as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    env_vars[key] = value.split('#')[0].strip()
    except Exception as e:
        print(f"Error reading .env: {e}")
    return env_vars

env = load_env()

endpoint_url = env.get('S3_ENDPOINT_URL')
access_key = env.get('S3_ACCESS_KEY_ID')
secret_key = env.get('S3_SECRET_ACCESS_KEY')
bucket_name = env.get('S3_BUCKET_NAME')
region_name = env.get('S3_REGION_NAME')

print(f"R2 Verification Script - Thumbnail Access")
print(f"Endpoint: {endpoint_url}")

try:
    session = boto3.session.Session()
    s3_client = session.client(
        's3',
        endpoint_url=endpoint_url,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=region_name,
        config=Config(signature_version='s3v4')
    )
    
    # 1. Upload Dummy Thumbnail
    print("\n1. Uploading dummy thumbnail...")
    test_key = "uploads/TEST_USER/TEST_PHOTO/thumbnails/thumb_512.jpg"
    with open("dummy_thumb.jpg", "wb") as f:
        f.write(b"fake image data " * 100)
        
    s3_client.upload_file(
        "dummy_thumb.jpg", 
        bucket_name, 
        test_key, 
        ExtraArgs={'ContentType': 'image/jpeg'}
    )
    print("Upload successful.")
    
    # 2. Generate Presigned URL
    print("\n2. Generating presigned URL...")
    url = s3_client.generate_presigned_url(
        'get_object',
        Params={'Bucket': bucket_name, 'Key': test_key},
        ExpiresIn=3600
    )
    print(f"URL: {url}")
    
    # 3. Access URL
    print("\n3. Testing access via requests...")
    resp = requests.get(url)
    print(f"Status Code: {resp.status_code}")
    print(f"Headers: {resp.headers}")
    
    if resp.status_code == 200:
        print("✅ SUCCESS: Thumbnail accessible.")
    else:
        print(f"❌ FAILED: {resp.text}")
        
    # Cleanup
    s3_client.delete_object(Bucket=bucket_name, Key=test_key)
    os.remove("dummy_thumb.jpg")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()

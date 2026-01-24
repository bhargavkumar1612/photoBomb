
from app.celery_app import celery_app
import sys

# Photo ID from user report
photo_id = "60184cc9-26a1-464d-a7ed-d7b4eb2ecfc6"
# Upload ID matches Photo ID in Direct Upload mode
upload_id = photo_id 

print(f"Triggering thumbnail generation for Photo: {photo_id}")

try:
    task = celery_app.send_task(
        'app.workers.thumbnail_worker.process_upload', 
        args=[upload_id, photo_id]
    )
    print(f"Task sent! Task ID: {task.id}")
except Exception as e:
    print(f"Error sending task: {e}")

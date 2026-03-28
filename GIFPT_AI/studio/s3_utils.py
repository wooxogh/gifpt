# studio/s3_utils.py

import os
import uuid
from pathlib import Path
import boto3

S3_BUCKET = os.environ.get("GIFPT_S3_BUCKET", "gifpt-demo")
S3_REGION = os.environ.get("GIFPT_S3_REGION", "us-east-1")

s3 = boto3.client("s3", region_name=S3_REGION)

def upload_to_s3(file_path: str) -> str:
    key = f"videos/{uuid.uuid4()}.mp4"

    s3.upload_file(
        file_path,
        S3_BUCKET,
        key,
        ExtraArgs={
            "ContentType": "video/mp4"
        }
    )

    return f"https://{S3_BUCKET}.s3.amazonaws.com/{key}"

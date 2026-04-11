# studio/s3_utils.py

import os

S3_BUCKET = os.environ.get("GIFPT_S3_BUCKET", "gifpt-demo")
S3_REGION = os.environ.get("GIFPT_S3_REGION", "us-east-1")

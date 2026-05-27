import os
import boto3
from botocore.config import Config

R2_ACCOUNT_ID = os.environ.get('R2_ACCOUNT_ID')
R2_ACCESS_KEY_ID = os.environ.get('R2_ACCESS_KEY_ID')
R2_SECRET_ACCESS_KEY = os.environ.get('R2_SECRET_ACCESS_KEY')
R2_BUCKET_NAME = os.environ.get('R2_BUCKET_NAME')
R2_PUBLIC_URL = os.environ.get('R2_PUBLIC_URL')

def get_r2_client():
    return boto3.client(
        's3',
        endpoint_url=f'https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com',
        aws_access_key_id=R2_ACCESS_KEY_ID,
        aws_secret_access_key=R2_SECRET_ACCESS_KEY,
        config=Config(signature_version='s3v4'),
        region_name='auto'
    )

def upload_fileobj(fileobj, filename):
    client = get_r2_client()
    client.upload_fileobj(fileobj, R2_BUCKET_NAME, f'id_proofs/{filename}')

def delete_file(filename):
    client = get_r2_client()
    client.delete_object(Bucket=R2_BUCKET_NAME, Key=f'id_proofs/{filename}')

def get_url(filename):
    if R2_PUBLIC_URL:
        return f'{R2_PUBLIC_URL}/id_proofs/{filename}'
    return None

def is_configured():
    return all([R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET_NAME])

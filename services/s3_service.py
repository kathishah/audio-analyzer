import boto3
from botocore.exceptions import NoCredentialsError
import os
import datetime

import logging

logger = logging.getLogger(__name__)

# AWS Configuration
AWS_REGION = os.getenv('AWS_REGION', 'us-west-1')  # Default to 'us-west-1' if not set
BUCKET_NAME = os.getenv('S3_BUCKET_NAME', 'crispvoice-audio-recordings')
COGNITO_IDENTITY_POOL_ID = os.getenv('COGNITO_IDENTITY_POOL_ID')  # Identity Pool ID

# Configure AWS Cognito Credentials Provider
cognito_client = boto3.client('cognito-identity', region_name=AWS_REGION)

def get_cognito_credentials(identity_pool_id: str) -> dict:
    """
    Get AWS credentials using Cognito Identity Pool.

    Args:
        identity_pool_id: Cognito Identity Pool ID.

    Returns:
        dict: Temporary AWS credentials.
    """
    try:
        identity_response = cognito_client.get_id(
            IdentityPoolId=identity_pool_id
        )
        identity_id = identity_response['IdentityId']

        credentials_response = cognito_client.get_credentials_for_identity(
            IdentityId=identity_id
        )
        return credentials_response['Credentials']
    except Exception as e:
        raise Exception(f"Failed to retrieve credentials from Cognito: {str(e)}")

# Fetch temporary credentials
cognito_credentials = get_cognito_credentials(COGNITO_IDENTITY_POOL_ID)

# Configure AWS S3 client with temporary credentials
s3_client = boto3.client(
    's3',
    region_name=AWS_REGION,
    aws_access_key_id=cognito_credentials['AccessKeyId'],
    aws_secret_access_key=cognito_credentials['SecretKey'],
    aws_session_token=cognito_credentials['SessionToken']
)

def generate_file_name() -> str:
    """
    Generate a unique file name based on the current timestamp.

    Returns:
        str: Generated file name.
    """
    now = datetime.datetime.utcnow()
    timestamp = now.isoformat()\
        .replace(':', '-')\
        .replace('.', '-')\
        .replace('T', '_')

    return f"recording_{timestamp}"

def upload_file_to_s3(file_path: str, content_type: str) -> str:
    """
    Upload a file to S3 with a generated filename.

    Args:
        file_path: Path to the file to upload.
        content_type: MIME type of the file.

    Returns:
        str: URL of the uploaded file.

    Raises:
        Exception: If the upload fails.
    """
    file_name = generate_file_name()
    try:
        with open(file_path, "rb") as f:
            s3_client.upload_fileobj(
                f,
                BUCKET_NAME,
                file_name,
                ExtraArgs={"ContentType": content_type}
            )
        s3_url = f"https://{BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{file_name}"
        return s3_url
    except NoCredentialsError:
        raise Exception("AWS credentials not found or expired.")
    except Exception as e:
        raise Exception(f"Failed to upload file to S3: {str(e)}")
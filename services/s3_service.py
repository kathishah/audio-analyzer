import boto3
from botocore.exceptions import NoCredentialsError, ClientError
import os
import datetime
from typing import Optional
import threading
import time

import logging

logger = logging.getLogger(__name__)

class S3ClientManager:
    _instance = None
    _instance_lock = threading.Lock()
    _refresh_lock = threading.Lock()
    _initialized = False

    def __init__(self):
        self.aws_region = os.getenv('AWS_REGION')
        self.bucket_name = os.getenv('S3_BUCKET_NAME')
        self.identity_pool_id = os.getenv('COGNITO_IDENTITY_POOL_ID')
        
        required_vars = {
            'AWS_REGION': self.aws_region,
            'S3_BUCKET_NAME': self.bucket_name,
            'COGNITO_IDENTITY_POOL_ID': self.identity_pool_id
        }
        missing_vars = [var for var, value in required_vars.items() if not value]
        
        if missing_vars:
            raise ValueError(f"Missing required AWS environment variables: {', '.join(missing_vars)}")
        
        self.cognito_client = boto3.client('cognito-identity', region_name=self.aws_region)
        self.s3_client = None
        self.credentials = None
        self.credentials_expiry = None
        self._refresh_credentials()
        self._initialized = True

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    try:
                        cls._instance = cls()
                    except ValueError as e:
                        logger.error(f"Failed to initialize S3ClientManager: {str(e)}")
                        raise
        return cls._instance

    @classmethod
    def is_initialized(cls) -> bool:
        """Check if the S3ClientManager is properly initialized"""
        return cls._instance is not None and cls._instance._initialized

    def _get_cognito_credentials(self) -> dict:
        """
        Get AWS credentials using Cognito Identity Pool.
        Returns:
            dict: Temporary AWS credentials.
        """
        try:
            identity_response = self.cognito_client.get_id(
                IdentityPoolId=self.identity_pool_id
            )
            identity_id = identity_response['IdentityId']

            credentials_response = self.cognito_client.get_credentials_for_identity(
                IdentityId=identity_id
            )
            return credentials_response['Credentials']
        except Exception as e:
            raise Exception(f"Failed to retrieve credentials from Cognito: {str(e)}")

    def _should_refresh_credentials(self) -> bool:
        """Check if credentials need to be refreshed"""
        expiry = self.credentials_expiry  # Read once to avoid race conditions
        return (
            self.credentials is None or
            expiry is None or
            datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=5) >= expiry
        )

    def _refresh_credentials(self):
        """Refresh AWS credentials if they're expired or about to expire"""
        # Quick check without the lock
        if not self._should_refresh_credentials():
            return

        # Take the lock and check again
        with self._refresh_lock:
            # Double-check under the lock
            if not self._should_refresh_credentials():
                return
            
            try:
                new_credentials = self._get_cognito_credentials()
                # Set all attributes atomically under the lock
                self.credentials = new_credentials
                self.credentials_expiry = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1)
                self.s3_client = boto3.client(
                    's3',
                    region_name=self.aws_region,
                    aws_access_key_id=new_credentials['AccessKeyId'],
                    aws_secret_access_key=new_credentials['SecretKey'],
                    aws_session_token=new_credentials['SessionToken']
                )
                logger.info("AWS credentials refreshed successfully")
            except Exception as e:
                logger.error(f"Failed to refresh credentials: {str(e)}")
                raise

    def get_token_status(self) -> dict:
        """
        Get the current token status.
        
        Returns:
            dict: Token status containing:
                - status: 'active' or 'expired'
                - expires_in_seconds: seconds until expiration (if active)
                - expiry_time: ISO formatted expiry time (if active)
        """
        if not self.credentials_expiry:
            return {
                "status": "expired",
                "expires_in_seconds": 0,
                "expiry_time": None
            }
            
        now = datetime.datetime.now(datetime.timezone.utc)
        if now >= self.credentials_expiry:
            return {
                "status": "expired",
                "expires_in_seconds": 0,
                "expiry_time": self.credentials_expiry.isoformat()
            }
            
        expires_in = (self.credentials_expiry - now).total_seconds()
        return {
            "status": "active",
            "expires_in_seconds": int(expires_in),
            "expiry_time": self.credentials_expiry.isoformat()
        }

    def force_refresh_token(self) -> dict:
        """
        Force a refresh of the token regardless of expiry status.
        
        Returns:
            dict: New token status
        """
        self._refresh_credentials()
        return self.get_token_status()
        
    def force_token_expiration(self) -> dict:
        """
        Force the current token to expire by setting expiry to now.
        
        Returns:
            dict: Token status after expiration
        """
        if self.credentials_expiry:
            self.credentials_expiry = datetime.datetime.now(datetime.timezone.utc)
        return self.get_token_status()

    def get_client(self):
        """Get a valid S3 client with fresh credentials"""
        self._refresh_credentials()
        return self.s3_client

def generate_file_name() -> str:
    """Generate a unique file name based on timestamp"""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"recording_{timestamp}.wav"

def upload_file_to_s3(file_path: str, content_type: str, max_retries: int = 1) -> str:
    """
    Upload a file to S3 with a generated filename.
    Args:
        file_path: Path to the file to upload.
        content_type: MIME type of the file.
        max_retries: Maximum number of retries for token expiration (default: 1).
    Returns:
        str: URL of the uploaded file.
    Raises:
        Exception: If the upload fails after retries.
    """
    s3_manager = S3ClientManager.get_instance()
    file_name = generate_file_name()
    retry_count = 0
    last_error = None

    while retry_count <= max_retries:
        try:
            with open(file_path, 'rb') as file:
                s3_client = s3_manager.get_client()
                s3_client.put_object(
                    Bucket=s3_manager.bucket_name,
                    Key=file_name,
                    Body=file,
                    ContentType=content_type
                )
                
                url = f"https://{s3_manager.bucket_name}.s3.{s3_manager.aws_region}.amazonaws.com/{file_name}"
                logger.info(f"Successfully uploaded file to S3: {url}")
                return url

        except ClientError as e:
            last_error = e
            if e.response['Error']['Code'] == 'ExpiredToken' and retry_count < max_retries:
                logger.warning(f"Token expired during upload (attempt {retry_count + 1}/{max_retries + 1}), refreshing credentials...")
                try:
                    s3_manager._refresh_credentials()
                    retry_count += 1
                    continue
                except Exception as refresh_error:
                    logger.error(f"Failed to refresh credentials: {str(refresh_error)}")
                    raise
            else:
                logger.error(f"AWS error uploading file: {str(e)}")
                raise Exception(f"Failed to upload file to S3: {str(e)}")
                
        except NoCredentialsError:
            raise Exception("Failed to upload file to S3: AWS credentials not found")
            
        except Exception as e:
            logger.error(f"Error uploading file: {str(e)}")
            raise Exception(f"Failed to upload file to S3: {str(e)}")

    if last_error:
        raise Exception(f"Failed to upload file to S3 after {max_retries + 1} attempts: {str(last_error)}")

__all__ = ['upload_file_to_s3']
import pytest
from unittest.mock import patch, MagicMock, call
import datetime
from botocore.exceptions import ClientError
import os
from services.s3_service import S3ClientManager, upload_file_to_s3

# Test environment configuration
TEST_ENV = {
    'AWS_REGION': 'us-west-1',
    'S3_BUCKET_NAME': 'test-bucket',
    'COGNITO_IDENTITY_POOL_ID': 'test-pool-id'
}

@pytest.fixture(scope='module', autouse=True)
def setup_test_env():
    """Set up test environment variables"""
    original_environ = dict(os.environ)
    os.environ.update(TEST_ENV)
    yield
    os.environ.clear()
    os.environ.update(original_environ)

@pytest.fixture
def mock_aws_clients():
    """Mock AWS clients for testing"""
    mock_cognito = MagicMock()
    mock_s3 = MagicMock()
    
    # Configure mock responses
    mock_cognito.get_id.return_value = {'IdentityId': 'test-id'}
    mock_cognito.get_credentials_for_identity.return_value = {
        'Credentials': {
            'AccessKeyId': 'test-key',
            'SecretKey': 'test-secret',
            'SessionToken': 'test-token'
        }
    }
    
    with patch('boto3.client') as mock_boto3:
        def get_client(service, **kwargs):
            if service == 'cognito-identity':
                return mock_cognito
            elif service == 's3':
                return mock_s3
        mock_boto3.side_effect = get_client
        yield mock_cognito, mock_s3

@pytest.fixture
def s3_manager(mock_aws_clients):
    """Create a test S3ClientManager instance with mocked AWS clients"""
    # Clear any existing instance
    S3ClientManager._instance = None
    
    # Create new instance
    manager = S3ClientManager.get_instance()
    
    # Reset mock call counts after initialization
    mock_cognito, _ = mock_aws_clients
    mock_cognito.get_id.reset_mock()
    mock_cognito.get_credentials_for_identity.reset_mock()
    
    yield manager
    
    # Clean up
    S3ClientManager._instance = None

def test_credential_refresh_on_expiry(s3_manager, mock_aws_clients):
    """Test that credentials are refreshed when they're about to expire"""
    mock_cognito, _ = mock_aws_clients
    
    # Set up initial credentials with an expiry time in the past
    s3_manager.credentials_expiry = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=5)
    
    # This should trigger a refresh
    s3_manager.get_client()
    
    # Verify that new credentials were fetched
    assert mock_cognito.get_id.call_count >= 1
    assert mock_cognito.get_credentials_for_identity.call_count >= 1

def test_credential_refresh_on_expired_token_error(s3_manager, mock_aws_clients):
    """Test that credentials are refreshed when an ExpiredToken error occurs"""
    mock_cognito, mock_s3 = mock_aws_clients
    
    # Configure S3 to fail first with ExpiredToken, then succeed
    error_response = {
        'Error': {
            'Code': 'ExpiredToken',
            'Message': 'The provided token has expired.'
        }
    }
    mock_s3.put_object.side_effect = [
        ClientError(error_response, 'PutObject'),  # First call fails
        None  # Second call succeeds
    ]
    
    # Set up expired credentials
    s3_manager.credentials_expiry = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=5)
    s3_manager.credentials = {
        'AccessKeyId': 'old-key',
        'SecretKey': 'old-secret',
        'SessionToken': 'old-token'
    }
    
    # Reset mock call counts before the test
    mock_cognito.get_id.reset_mock()
    mock_cognito.get_credentials_for_identity.reset_mock()
    
    # Attempt to upload a file (should trigger refresh)
    test_file = 'test.wav'
    with patch('builtins.open', create=True) as mock_open:
        mock_open.return_value.__enter__.return_value = 'file_content'
        upload_file_to_s3(test_file, 'audio/wav')
    
    # Verify that new credentials were fetched
    assert mock_cognito.get_id.call_count >= 1, "Cognito get_id should have been called"
    assert mock_cognito.get_credentials_for_identity.call_count >= 1, "Credentials should have been refreshed"
    assert mock_s3.put_object.call_count == 2, "S3 put_object should have been called twice"
    
    # Verify the sequence of calls
    mock_s3.put_object.assert_has_calls([
        call(Bucket='test-bucket', Key=mock_s3.put_object.call_args_list[0][1]['Key'], 
             Body='file_content', ContentType='audio/wav'),
        call(Bucket='test-bucket', Key=mock_s3.put_object.call_args_list[1][1]['Key'], 
             Body='file_content', ContentType='audio/wav')
    ])

def test_concurrent_credential_refresh(s3_manager, mock_aws_clients):
    """Test that concurrent credential refreshes are handled properly"""
    mock_cognito, _ = mock_aws_clients
    import threading
    import time
    
    # Use events to synchronize threads
    start_event = threading.Event()
    threads_ready = threading.Event()
    thread_count = 5
    threads_ready_count = 0
    ready_lock = threading.Lock()
    
    class CredentialRefreshTracker:
        def __init__(self):
            self.count = 0
            self.lock = threading.Lock()
        
        def get_credentials(self):
            with self.lock:
                self.count += 1
                # Simulate some work
                time.sleep(0.1)
                return {
                    'AccessKeyId': 'test-key',
                    'SecretKey': 'test-secret',
                    'SessionToken': 'test-token'
                }
    
    tracker = CredentialRefreshTracker()
    
    def thread_func():
        nonlocal threads_ready_count
        # Signal that this thread is ready
        with ready_lock:
            threads_ready_count += 1
            if threads_ready_count == thread_count:
                threads_ready.set()
        
        # Wait for the start signal
        threads_ready.wait()
        start_event.wait()
        
        # Force credentials to be expired
        s3_manager.credentials_expiry = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=5)
        
        # Try to refresh credentials
        s3_manager.get_client()
    
    # Replace the credential fetching with our tracked version
    s3_manager._get_cognito_credentials = tracker.get_credentials
    
    # Create and start threads
    threads = []
    for _ in range(thread_count):
        thread = threading.Thread(target=thread_func)
        thread.start()
        threads.append(thread)
    
    # Wait for all threads to be ready
    threads_ready.wait()
    # Start all threads simultaneously
    start_event.set()
    
    # Wait for all threads to complete
    for thread in threads:
        thread.join()
    
    # Verify that refresh was only called once
    assert tracker.count == 1, f"Expected 1 refresh, but got {tracker.count}"

def test_credentials_not_refreshed_if_valid(s3_manager, mock_aws_clients):
    """Test that credentials are not refreshed if they're still valid"""
    mock_cognito, _ = mock_aws_clients
    
    # Set valid credentials that won't expire for 30 minutes
    s3_manager.credentials_expiry = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=30)
    s3_manager.credentials = {
        'AccessKeyId': 'test-key',
        'SecretKey': 'test-secret',
        'SessionToken': 'test-token'
    }
    
    # Get client should not trigger a refresh
    s3_manager.get_client()
    
    # Verify no calls were made to Cognito
    mock_cognito.get_id.assert_not_called()
    mock_cognito.get_credentials_for_identity.assert_not_called()

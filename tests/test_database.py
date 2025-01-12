"""
Database service tests
"""

import os
import time
import uuid
from decimal import Decimal
import pytest
from sqlalchemy.orm import Session

from api.models import RecordingSession, Base
from db.base import DatabaseSetup
from services.db_service import recording_session_crud

# Test database URL - use environment variable or default to localhost since we're running outside Docker
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/test_audioanalyzer"
)

@pytest.fixture(scope="function")
def test_db():
    """Create a test database and tables, then drop them after the test."""
    # Create a test database service instance
    database_setup = DatabaseSetup(database_url=TEST_DATABASE_URL)
    database_setup.Base = Base
    database_setup.init_db()
    database_setup.create_tables()
    
    with database_setup.get_db() as db:
        yield db
        
    # Clean up
    if database_setup.engine:
        Base.metadata.drop_all(database_setup.engine)
        database_setup.engine.dispose()

def test_create_recording_session(test_db):
    """Test creating a new recording session."""
    session = RecordingSession(
        device_name="Test Device",
        ip_address="192.168.1.1",
        audio_format="wav"
    )
    
    created_session = recording_session_crud.create(test_db, model_obj=session)
    
    assert created_session.recording_session_id is not None
    assert created_session.device_name == "Test Device"
    assert created_session.ip_address == "192.168.1.1"
    assert created_session.audio_format == "wav"
    assert created_session.created_at is not None
    assert created_session.updated_at is not None

def test_update_recording_session(test_db):
    """Test updating a recording session."""
    # Create initial session
    initial_session = RecordingSession(
        device_name="Test Device",
        ip_address="192.168.1.1",
        audio_format="wav"
    )
    initial_session = recording_session_crud.create(test_db, model_obj=initial_session)
    
    initial_updated_at = initial_session.updated_at
    time.sleep(0.1)  # Add a small delay to ensure timestamps are different
    
    # Update the session
    initial_session.analysis_score = Decimal('0.95')
    initial_session.analysis_output = {
        'pesq_score': 0.95,
        'quality_category': 'good',
        'snr_db': 25.5,
        'sample_rate': 44100
    }
    initial_session.s3_location = 's3://bucket/test.wav'
    
    updated_session = recording_session_crud.update(test_db, model_obj=initial_session)
    
    assert updated_session.recording_session_id == initial_session.recording_session_id
    assert updated_session.analysis_score == Decimal('0.95')
    assert updated_session.analysis_output['pesq_score'] == 0.95
    assert updated_session.s3_location == 's3://bucket/test.wav'
    assert updated_session.updated_at > initial_updated_at

def test_retrieve_recording_session(test_db):
    """Test retrieving a recording session."""
    # Create a session
    initial_session = RecordingSession(
        device_name="Test Device",
        ip_address="192.168.1.1",
        audio_format="wav"
    )
    initial_session = recording_session_crud.create(test_db, model_obj=initial_session)
    
    # Retrieve the session
    retrieved_session = recording_session_crud.get_session(
        test_db,
        str(initial_session.recording_session_id)
    )
    
    assert retrieved_session is not None
    assert retrieved_session.recording_session_id == initial_session.recording_session_id
    assert retrieved_session.device_name == initial_session.device_name
    assert retrieved_session.ip_address == initial_session.ip_address
    assert retrieved_session.audio_format == initial_session.audio_format

def test_retrieve_nonexistent_session(test_db):
    """Test retrieving a non-existent recording session."""
    nonexistent_id = str(uuid.uuid4())
    retrieved_session = recording_session_crud.get_session(test_db, nonexistent_id)
    assert retrieved_session is None

def test_delete_recording_session(test_db):
    """Test deleting a recording session."""
    # Create a session
    session = RecordingSession(
        device_name="Test Device",
        ip_address="192.168.1.1",
        audio_format="wav"
    )
    created_session = recording_session_crud.create(test_db, model_obj=session)
    
    # Delete the session
    deleted_session = recording_session_crud.delete(test_db, id=created_session.recording_session_id)
    assert deleted_session.recording_session_id == created_session.recording_session_id
    
    # Verify it's gone
    retrieved_session = recording_session_crud.get_session(
        test_db,
        str(created_session.recording_session_id)
    )
    assert retrieved_session is None

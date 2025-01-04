import pytest
from services.db_service import recording_session_crud
from db.base import DatabaseSetup
from api.models import RecordingSession, Base, StartRecordingSessionRequest, UpdateRecordingSessionRequest
import json
import uuid
from datetime import datetime
import os
from decimal import Decimal
import time

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
    session_request = StartRecordingSessionRequest(
        device_name="Test Device",
        ip_address="192.168.1.1",
        audio_format="wav"
    )
    
    session = recording_session_crud.create(test_db, obj_in=session_request)
    
    assert session.recording_session_id is not None
    assert session.device_name == "Test Device"
    assert session.ip_address == "192.168.1.1"
    assert session.audio_format == "wav"
    assert session.created_at is not None
    assert session.updated_at is not None

def test_update_recording_session(test_db):
    """Test updating a recording session."""
    # Create initial session
    initial_session = recording_session_crud.create(
        test_db,
        obj_in=StartRecordingSessionRequest(
            device_name="Test Device",
            ip_address="192.168.1.1",
            audio_format="wav"
        )
    )
    
    initial_updated_at = initial_session.updated_at
    time.sleep(0.1)  # Add a small delay to ensure timestamps are different
    
    # Update the session
    update_request = UpdateRecordingSessionRequest(
        recording_session_id=initial_session.recording_session_id,
        analysis_score=Decimal('0.95'),
        status="completed",
        error_message=None
    )
    
    updated_session = recording_session_crud.update(
        test_db,
        db_obj=initial_session,
        obj_in=update_request
    )
    
    assert updated_session.recording_session_id == initial_session.recording_session_id
    assert updated_session.analysis_score == Decimal('0.95')
    assert updated_session.status == "completed"
    assert updated_session.error_message is None
    assert updated_session.updated_at > initial_updated_at

def test_retrieve_recording_session(test_db):
    """Test retrieving a recording session."""
    # Create a session
    initial_session = recording_session_crud.create(
        test_db,
        obj_in=StartRecordingSessionRequest(
            device_name="Test Device",
            ip_address="192.168.1.1",
            audio_format="wav"
        )
    )
    
    # Retrieve the session
    retrieved_session = recording_session_crud.get_by_recording_session_id(
        test_db,
        recording_session_id=initial_session.recording_session_id
    )
    
    assert retrieved_session is not None
    assert retrieved_session.recording_session_id == initial_session.recording_session_id
    assert retrieved_session.device_name == initial_session.device_name
    assert retrieved_session.ip_address == initial_session.ip_address
    assert retrieved_session.audio_format == initial_session.audio_format

import pytest
from services.db_service import DatabaseService, db_service as app_db_service
from api.models import RecordingSession, Base
import json
import uuid
from datetime import datetime

# Test database URL
TEST_DATABASE_URL = "postgresql://postgres:postgres@db:5432/test_audioanalyzer"

@pytest.fixture(scope="function")
def test_db():
    """Create a test database and tables, then drop them after the test."""
    # Create a test database service instance
    db_service = DatabaseService(database_url=TEST_DATABASE_URL)
    db_service.Base = Base  # Use the same Base instance as the models
    db_service.init_db()
    db_service.create_tables()
    
    with db_service.get_db() as db:
        yield db
        
    # Clean up
    if db_service.engine:
        db_service.Base.metadata.drop_all(db_service.engine)

def test_create_recording_session(test_db):
    """Test creating a new recording session."""
    session = RecordingSession(
        device_name="Test Device",
        ip_address="192.168.1.1",
        audio_format="wav"
    )
    
    test_db.add(session)
    test_db.commit()
    test_db.refresh(session)
    
    assert session.session_id is not None
    assert session.device_name == "Test Device"
    assert session.ip_address == "192.168.1.1"
    assert session.audio_format == "wav"
    assert session.created_at is not None
    assert session.updated_at is not None

def test_update_recording_session(test_db):
    """Test updating a recording session with all fields."""
    # Create initial session
    session = RecordingSession(
        device_name="Test Device",
        ip_address="192.168.1.1",
        audio_format="wav"
    )
    test_db.add(session)
    test_db.commit()
    
    # Update session with additional details
    session_id = session.session_id
    microphone_details = json.dumps({"brand": "Test Brand", "model": "Test Model"})
    speaker_details = json.dumps({"type": "Built-in", "channels": 2})
    analysis_output = {"snr": 35.5, "clarity_score": 0.85}
    
    session.microphone_details = microphone_details
    session.speaker_details = speaker_details
    session.s3_location = f"s3://test-bucket/{session_id}/audio.wav"
    session.analysis_output = analysis_output
    session.analysis_score = 92.50
    
    test_db.commit()
    test_db.refresh(session)
    
    # Verify all fields
    assert session.microphone_details == microphone_details
    assert session.speaker_details == speaker_details
    assert session.s3_location == f"s3://test-bucket/{session_id}/audio.wav"
    assert session.analysis_output == analysis_output
    assert float(session.analysis_score) == 92.50

def test_retrieve_recording_session(test_db):
    """Test retrieving a recording session."""
    # Create a session
    original_session = RecordingSession(
        device_name="Test Device",
        ip_address="192.168.1.1",
        audio_format="wav",
        microphone_details=json.dumps({"brand": "Test Brand"}),
        speaker_details=json.dumps({"type": "Built-in"}),
        s3_location="s3://test-bucket/test.wav",
        analysis_output={"snr": 35.5},
        analysis_score=88.75
    )
    test_db.add(original_session)
    test_db.commit()
    
    # Retrieve the session
    retrieved_session = test_db.query(RecordingSession).filter(
        RecordingSession.session_id == original_session.session_id
    ).first()
    
    # Verify all fields match
    assert retrieved_session.device_name == original_session.device_name
    assert retrieved_session.ip_address == original_session.ip_address
    assert retrieved_session.audio_format == original_session.audio_format
    assert retrieved_session.microphone_details == original_session.microphone_details
    assert retrieved_session.speaker_details == original_session.speaker_details
    assert retrieved_session.s3_location == original_session.s3_location
    assert retrieved_session.analysis_output == original_session.analysis_output
    assert float(retrieved_session.analysis_score) == float(original_session.analysis_score)

def test_invalid_analysis_score(test_db):
    """Test that analysis_score properly handles decimal precision."""
    session = RecordingSession(
        device_name="Test Device",
        ip_address="192.168.1.1",
        audio_format="wav",
        analysis_score=88.7654  # More than 2 decimal places
    )
    test_db.add(session)
    test_db.commit()
    test_db.refresh(session)
    
    # Should be rounded to 2 decimal places
    assert float(session.analysis_score) == 88.77  # Rounds to 2 decimal places

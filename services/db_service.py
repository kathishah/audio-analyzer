"""
Database service with CRUD operations
"""

from typing import TypeVar, Type, Optional, Dict, Any, Generic
from pydantic import BaseModel
from sqlalchemy.orm import Session
import logging
import uuid

logger = logging.getLogger(__name__)

# Generic type variables
ModelType = TypeVar("ModelType")
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)

class CRUDService(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """
    Generic CRUD operations service
    """
    def __init__(self, model: Type[ModelType]):
        self.model = model

    def create(self, db: Session, *, obj_in: CreateSchemaType) -> ModelType:
        """Create a new record"""
        obj_data = obj_in.model_dump()
        db_obj = self.model(**obj_data)
        db.add(db_obj)
        db.flush()
        return db_obj

    def get(self, db: Session, id: Any) -> Optional[ModelType]:
        """Get a record by ID"""
        return db.query(self.model).filter(self.model.id == id).first()

    def get_multi(self, db: Session, *, skip: int = 0, limit: int = 100) -> list[ModelType]:
        """Get multiple records"""
        return db.query(self.model).offset(skip).limit(limit).all()

    def update(self, db: Session, *, db_obj: ModelType, obj_in: UpdateSchemaType) -> ModelType:
        """Update a record"""
        obj_data = obj_in.model_dump(exclude_unset=True)
        for field, value in obj_data.items():
            setattr(db_obj, field, value)
        db.add(db_obj)
        db.flush()
        db.refresh(db_obj)  # Refresh to ensure we get the updated timestamp
        return db_obj

    def delete(self, db: Session, *, id: Any) -> ModelType:
        """Delete a record"""
        obj = db.query(self.model).get(id)
        db.delete(obj)
        db.flush()
        return obj

class CRUDServiceRecordingSession(CRUDService[
    'RecordingSession',
    'StartRecordingSessionRequest',
    'UpdateRecordingSessionRequest'
]):
    """CRUD operations for RecordingSession model"""
    
    def get_by_recording_session_id(self, db: Session, recording_session_id: Any) -> Optional['RecordingSession']:
        """
        Get a recording session by its ID
        
        Args:
            db: Database session
            recording_session_id: UUID of the recording session
            
        Returns:
            Optional[RecordingSession]: The recording session if found, None otherwise
            
        Raises:
            ValueError: If recording_session_id is invalid
        """
        try:
            if not isinstance(recording_session_id, uuid.UUID):
                recording_session_id = uuid.UUID(str(recording_session_id))
        except (TypeError, ValueError):
            raise ValueError(f"Invalid recording session ID: {recording_session_id}")
            
        return db.query(self.model).filter(
            self.model.recording_session_id == recording_session_id
        ).first()
    
    def create(self, db: Session, *, obj_in: 'StartRecordingSessionRequest') -> 'RecordingSession':
        """
        Create a new recording session
        
        Args:
            db: Database session
            obj_in: Recording session data
            
        Returns:
            RecordingSession: The created recording session
            
        Raises:
            ValueError: If input data is invalid
            sqlalchemy.exc.IntegrityError: If database constraints are violated
        """
        try:
            return super().create(db, obj_in=obj_in)
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to create recording session: {str(e)}")
            if "duplicate key" in str(e).lower():
                raise ValueError("A recording session with this ID already exists")
            raise
    
    def update(
        self, 
        db: Session, 
        *, 
        db_obj: 'RecordingSession', 
        obj_in: 'UpdateRecordingSessionRequest'
    ) -> 'RecordingSession':
        """
        Update a recording session
        
        Args:
            db: Database session
            db_obj: Existing recording session
            obj_in: Update data
            
        Returns:
            RecordingSession: The updated recording session
            
        Raises:
            ValueError: If input data is invalid
            sqlalchemy.exc.IntegrityError: If database constraints are violated
        """
        if db_obj.recording_session_id != obj_in.recording_session_id:
            raise ValueError("Recording session ID mismatch")
            
        try:
            return super().update(db, db_obj=db_obj, obj_in=obj_in)
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to update recording session: {str(e)}")
            raise

# Import models after CRUDService definition to avoid circular imports
from api.models import RecordingSession, StartRecordingSessionRequest, UpdateRecordingSessionRequest

# Create CRUD service instance
recording_session_crud = CRUDServiceRecordingSession(RecordingSession)

__all__ = [
    'CRUDService',
    'CRUDServiceRecordingSession',
    'recording_session_crud'
]

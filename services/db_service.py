"""
Database service with CRUD operations
"""

from typing import TypeVar, Type, Optional, Dict, Any, Generic
from sqlalchemy.orm import Session
import logging
import uuid

logger = logging.getLogger(__name__)

# Generic type variable
ModelType = TypeVar("ModelType")

class CRUDService(Generic[ModelType]):
    """
    Generic CRUD operations service
    """
    def __init__(self, model: Type[ModelType]):
        self.model = model

    def create(self, db: Session, *, model_obj: ModelType) -> ModelType:
        """
        Create a new record
        
        Args:
            db: Database session
            model_obj: Model instance to create
            
        Returns:
            ModelType: Created record
        """
        try:
            db.add(model_obj)
            db.flush()
            db.commit()  # Commit the transaction
            return model_obj
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to create record: {str(e)}")
            raise

    def get(self, db: Session, id: Any) -> Optional[ModelType]:
        """
        Get a record by ID
        
        Args:
            db: Database session
            id: Record ID
            
        Returns:
            Optional[ModelType]: Found record or None
        """
        return db.query(self.model).filter(self.model.id == id).first()

    def get_multi(self, db: Session, *, skip: int = 0, limit: int = 100) -> list[ModelType]:
        """
        Get multiple records
        
        Args:
            db: Database session
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            list[ModelType]: List of records
        """
        return db.query(self.model).offset(skip).limit(limit).all()

    def update(self, db: Session, *, model_obj: ModelType) -> ModelType:
        """
        Update a record
        
        Args:
            db: Database session
            model_obj: Model instance with updated values
            
        Returns:
            ModelType: Updated record
        """
        try:
            db.merge(model_obj)
            db.flush()
            db.commit()  # Commit the transaction
            return model_obj
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to update record: {str(e)}")
            raise

    def delete(self, db: Session, *, id: Any) -> ModelType:
        """
        Delete a record
        
        Args:
            db: Database session
            id: Record ID
            
        Returns:
            ModelType: Deleted record
        """
        try:
            obj = db.get(self.model, id)
            db.delete(obj)
            db.flush()
            db.commit()  # Commit the transaction
            return obj
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to delete record: {str(e)}")
            raise

class CRUDServiceRecordingSession(CRUDService['RecordingSession']):
    """
    CRUD operations for RecordingSession model
    """
    def get_session(self, db: Session, recording_session_id: str) -> Optional['RecordingSession']:
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
            # Validate UUID format
            session_uuid = uuid.UUID(recording_session_id)
            return db.query(RecordingSession).filter(
                RecordingSession.recording_session_id == str(session_uuid)
            ).first()
        except ValueError as e:
            logger.error(f"Invalid recording session ID format: {str(e)}")
            raise ValueError("Invalid recording session ID format") from e

# Import models after CRUDService definition to avoid circular imports
from api.models import RecordingSession

# Create CRUD service instance
recording_session_crud = CRUDServiceRecordingSession(RecordingSession)

__all__ = ['recording_session_crud']

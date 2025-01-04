"""
Database configuration and base setup
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from contextlib import contextmanager
import logging
import os

logger = logging.getLogger(__name__)

class DatabaseSetup:
    def __init__(self, database_url=None):
        url = database_url or os.getenv("DATABASE_URL", "postgresql://postgres:postgres@db:5432/audioanalyzer")
        # Handle Heroku's postgres:// URLs
        if url and url.startswith('postgres://'):
            url = url.replace('postgres://', 'postgresql://', 1)
        self.database_url = url
        self.engine = None
        self.SessionLocal = None
        self.Base = declarative_base()
        
    def init_db(self):
        """Initialize the database engine and session factory."""
        try:
            self.engine = create_engine(self.database_url)
            self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
            logger.info(f"Database initialized with URL: {self.database_url}")
        except Exception as e:
            logger.error(f"Failed to initialize database: {str(e)}")
            raise
    
    def create_tables(self):
        """Create all tables defined in the models."""
        try:
            self.Base.metadata.create_all(bind=self.engine)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create database tables: {str(e)}")
            raise
    
    @contextmanager
    def get_db(self):
        """Get a database session."""
        if not self.SessionLocal:
            raise RuntimeError("Database not initialized. Call init_db() first.")
        
        db = self.SessionLocal()
        try:
            yield db
        finally:
            db.close()
    
    def get_session(self):
        """Get a database session (for FastAPI dependency injection)."""
        if not self.SessionLocal:
            raise RuntimeError("Database not initialized. Call init_db() first.")
        
        db = self.SessionLocal()
        try:
            yield db
        finally:
            db.close()

# Create a default instance
db_setup = DatabaseSetup()

# Export Base instance for Alembic
Base = db_setup.Base

def init_database():
    """Initialize the database and create all tables."""
    try:
        db_setup.init_db()
        db_setup.create_tables()
        logger.info("Database initialization completed successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}")
        raise

__all__ = ['db_setup', 'init_database', 'Base']

"""
Main application entry point
"""

import os
import logging
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from db import init_database
from api.routers import router
from logging_config import setup_logging
from services.s3_service import S3ClientManager

# Load environment variables
load_dotenv()

# Initialize logging
setup_logging()
logger = logging.getLogger(__name__)

# Lifecycle manager for the FastAPI application
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for the FastAPI application"""
    try:
        # Initialize database
        init_database()
        
        # Initialize S3 client
        required_vars = ['AWS_REGION', 'S3_BUCKET_NAME', 'COGNITO_IDENTITY_POOL_ID']
        if all(os.getenv(var) for var in required_vars):
            try:
                s3_manager = S3ClientManager.get_instance()
                logger.info("S3 client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize S3 client: {str(e)}")
                raise
        else:
            missing_vars = [var for var in required_vars if not os.getenv(var)]
            logger.warning(f"S3 client not initialized. Missing environment variables: {missing_vars}")
        
        logger.info("Application startup completed successfully")
        yield
    except Exception as e:
        logger.error(f"Failed to initialize application: {str(e)}")
        raise

# Create FastAPI app
app = FastAPI(
    title="Audio Analyzer API",
    description="API for analyzing audio quality",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(router, prefix="/api/v1")

# Health check endpoint
@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

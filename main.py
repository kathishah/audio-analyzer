"""
FastAPI application for audio analysis
"""
from dotenv import load_dotenv, find_dotenv

# Load environment variables from .env file
# Attempt to load .env file
dotenv_path = find_dotenv()
load_dotenv(dotenv_path)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routers import router
from logging_config import setup_logging
from services.db_service import init_database
import logging
import os

# Initialize logging
setup_logging()
logger = logging.getLogger(__name__)

# Check if variables are being loaded
if dotenv_path:
    logger.info(f".env file loaded from: {dotenv_path}")
else:
    logger.error("No .env file found.")
logger.info(f"COGNITO_IDENTITY_POOL_ID: {os.getenv('COGNITO_IDENTITY_POOL_ID')}")

# Initialize FastAPI app
app = FastAPI(
    title="Audio Analyzer API",
    description="API for analyzing audio quality",
    version="1.0.0"
)

# Initialize database
init_database()

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
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

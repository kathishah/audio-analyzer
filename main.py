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

# Create FastAPI app
app = FastAPI(
    title="Audio Quality Analyzer API",
    description="API for analyzing audio quality using PESQ metrics",
    version="0.1.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Include routers
app.include_router(router, prefix="/api/v1")

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

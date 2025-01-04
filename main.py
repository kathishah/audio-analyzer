"""
Main application entry point
"""

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
from contextlib import asynccontextmanager

from db import init_database
from api.routers import router
from logging_config import setup_logging

# Initialize logging
setup_logging()
logger = logging.getLogger(__name__)

# Lifecycle manager for the FastAPI application
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for the FastAPI application"""
    try:
        init_database()
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
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

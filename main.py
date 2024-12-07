"""
FastAPI application for audio analysis
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routers import router

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

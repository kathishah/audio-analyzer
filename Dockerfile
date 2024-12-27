# Use an official Python runtime as a parent image
FROM python:3.11.6-slim-bullseye

# Set the working directory in the container
WORKDIR /app

# Install system dependencies for audio processing
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    libmagic1 \
    build-essential \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy the current directory contents into the container at /app
COPY . /app

# Upgrade pip and install build dependencies
RUN pip install --no-cache-dir --upgrade pip \
    setuptools \
    wheel \
    cython \
    numpy
    
# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Install gunicorn for production server
RUN pip install gunicorn

# Make port 8000 available to the world outside this container
EXPOSE 8000

# Define environment variable to ensure Python output is sent directly to terminal
ENV PYTHONUNBUFFERED=1

# Run the application using uvicorn for asgi server
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT}"]
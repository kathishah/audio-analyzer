#!/bin/bash

# Set the API URL
export API_URL="https://audio-analyzer-api-af6843ebf910.herokuapp.com"

# Run deployment tests
echo "Running deployment verification tests..."
pytest tests/test_deployment.py -v

# Check the exit status
if [ $? -eq 0 ]; then
    echo "✅ Deployment verification successful!"
else
    echo "❌ Deployment verification failed!"
    exit 1
fi

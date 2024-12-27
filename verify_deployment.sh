#!/bin/bash

# Default API URL
API_URL="http://localhost:8000"

# Parse arguments
for arg in "$@"; do
    case $arg in
        --env=prod)
            API_URL="https://audio-analyzer-api-af6843ebf910.herokuapp.com"
            shift # Remove --env=prod from arguments
            ;;
    esac
done

# Export the API URL
export API_URL

# Run deployment tests
echo "Running deployment verification tests against $API_URL..."
pytest --api-url=$API_URL tests/test_deployment.py -vvvvv

# Check the exit status
if [ $? -eq 0 ]; then
    echo "✅ Deployment verification successful!"
else
    echo "❌ Deployment verification failed!"
    exit 1
fi

# Audio Quality Analyzer

A Python library and command-line tool for analyzing audio quality using PESQ (Perceptual Evaluation of Speech Quality) metrics. This tool supports various audio formats including WebM, MP3, WAV, and more.

## Features

- Automatic audio format detection and conversion
- PESQ score calculation
- Signal-to-Noise Ratio (SNR) measurement
- Support for multiple audio formats (WebM, WAV, MP3, etc.)
- Detailed logging of the analysis process
- Support for both audio files and video files with audio streams

## Project Structure

```
audio-analyzer/
├── audio_analyzer/          # Main package directory
│   ├── __init__.py         # Package initialization
│   ├── analyzer.py         # Core analysis functionality
│   └── utils.py            # Utility functions
├── api/                    # API related files
│   ├── models.py           # API models
│   └── routers.py          # API routers
├── services/               # Service layer
│   └── s3_service.py       # S3 integration
├── tests/                  # Test directory
│   ├── __init__.py
│   ├── conftest.py         # Test configuration and fixtures
│   ├── test_analyzer.py    # Tests for analyzer module
│   ├── test_utils.py       # Tests for utilities
│   └── resources/          # Test resource files


Deployment related files
│   ├── Dockerfile          # Docker configuration
│   ├── docker-compose.yml  # Docker Compose configuration
│   ├── Procfile            # Process file for deployment
│   └── verify_deployment.sh # Deployment verification script
├── tests/                  # Test directory
│   ├── test_deployment.py  # Tests to be run after the docker based deployment
│   ├── test_performance.py # Performance (api latency) tests to be run after the docker based deployment
├── analyze_audio.py        # Command-line interface for running on local
├── requirements.txt        # Python dependencies
└── README.md              # This file
```

## Requirements

### System Dependencies

#### macOS
Install using Homebrew:
```bash
# Install Homebrew if not already installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install required packages
brew install ffmpeg      # Required for audio conversion
brew install libmagic    # Required for file type detection
brew cask install docker # Required for containerized deployment
```

#### Linux (Ubuntu/Debian)
```bash
sudo apt-get update
sudo apt-get install ffmpeg
sudo apt-get install libmagic1

#### Docker
Docker is required for containerized deployment.

- **Linux**:
  - Follow the instructions on [Docker's official website](https://docs.docker.com/engine/install/ubuntu/).
```

## Installation

1. Clone the repository:
```bash
git clone https://github.com/kathishah/audio-analyzer.git
cd audio-analyzer
```

2. Create and activate a virtual environment:
```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate
```

3. Install Python dependencies:
```bash
pip install -r requirements.txt
```
4. Environment: ensure the following environment variables are set in a .env file in the root directory of the project.

- `AWS_REGION`: The AWS region where your S3 bucket is located (e.g., `us-west-1`).
- `S3_BUCKET_NAME`: The name of your S3 bucket (e.g., `crispvoice-audio-recordings`).
- `COGNITO_IDENTITY_POOL_ID`: The Cognito Identity Pool ID used to fetch temporary AWS credentials.


5. Build the application:
```bash
docker-compose up --build -d
```
## Usage

### As a Command-Line Tool

Basic usage:
```bash
python3 analyze_audio.py path/to/your/audio.webm
```

With logging to file:
```bash
python3 analyze_audio.py path/to/your/audio.webm --log-file analysis.log
```

### As a Python Library

```python
from audio_analyzer import AudioAnalyzer

# Create analyzer instance
analyzer = AudioAnalyzer()

# Analyze audio file
results = analyzer.analyze_audio("path/to/audio.webm")

# Process results
if results:
    print(f"PESQ Score: {results['pesq_score']}")
    print(f"Quality Category: {results['quality_category']}")
    print(f"SNR (dB): {results['snr_db']}")
    print(f"Sample Rate: {results['sample_rate']}")
```

## Output Format

The analysis provides the following metrics:
- PESQ score (ranging from -0.5 to 4.5)
- Quality category:
  - Poor Quality (< 1.0)
  - Fair Quality (1.0 - 2.0)
  - Good Quality (2.0 - 3.0)
  - Excellent Quality (3.0 - 4.0)
  - Outstanding Quality (> 4.0)
- Signal-to-Noise Ratio (SNR) in dB
- Sample rate in Hz

## Testing

The project uses pytest for testing. To run the tests:

1. Install test dependencies:
```bash
pip install -r requirements.txt
```

2. Run tests:
```bash
# Run all tests. EXPECTS THAT Docker is running.
pytest

# Run all tests with coverage report verbosely. EXPECTS THAT Docker is running.
pytest --api-url="http://localhost:8000" --cov=audio_analyzer -vvvv 

# Run pre-deployment tests. No DOCKER expected
pytest tests/test_analyzer.py tests/test_utils.py --cov=audio_analyzer -vvvv

# Run post-deployment tests. EXPECTS THAT Docker is running. 
pytest tests/test_deployment.py tests/test_performance.py --api-url="http://localhost:8000" --cov=audio_analyzer -vvvv
```

### Test Structure

```
tests/
├── __init__.py
├── conftest.py           # Test configuration and fixtures
├── test_analyzer.py      # Tests for analyzer module
├── test_deployment.py    # Tests to be run after the docker based deployment
├── test_performance.py   # Performance (api latency) tests to be run after the docker based deployment
├── test_utils.py         # Tests for utilities
└── resources/            # Test resource files
```

The test suite includes:
- Unit tests for all core functionality
- Integration tests for audio processing
- Mock tests for external dependencies
- Fixtures for common test scenarios

### Environment Variables for S3 Upload Test

To run the S3 upload test in `test_deployment.py`, ensure the following environment variables are set:

- `AWS_REGION`: The AWS region where your S3 bucket is located (e.g., `us-west-1`).
- `S3_BUCKET_NAME`: The name of your S3 bucket (e.g., `crispvoice-audio-recordings`).
- `COGNITO_IDENTITY_POOL_ID`: The Cognito Identity Pool ID used to fetch temporary AWS credentials.

These environment variables are necessary for authenticating and interacting with AWS services during the test.

## Troubleshooting

### Common Issues

1. **FileNotFoundError: ffmpeg not found**
   - Make sure ffmpeg is installed: `brew install ffmpeg`
   - Verify installation: `ffmpeg -version`

2. **ImportError: failed to find libmagic**
   - Make sure libmagic is installed: `brew install libmagic`
   - If the error persists, try: `brew reinstall libmagic`

3. **Permission denied when creating log file**
   - Make sure you have write permissions in the directory
   - Try running without the log file first

4. **Unsupported audio format**
   - Check if the format is supported by ffmpeg: `ffmpeg -formats`
   - Ensure the file is not corrupted

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

MIT License

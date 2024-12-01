# Audio Quality Analyzer

A Python tool for analyzing audio quality using PESQ (Perceptual Evaluation of Speech Quality) metrics. This tool supports various audio formats including WebM, MP3, WAV, and more.

## Features

- Automatic audio format detection and conversion
- PESQ score calculation
- Signal-to-Noise Ratio (SNR) measurement
- Support for multiple audio formats (WebM, WAV, MP3, etc.)
- Detailed logging of the analysis process

## Requirements

### System Dependencies

#### macOS
Install using Homebrew:
```bash
# Install Homebrew if not already installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install required packages
brew install ffmpeg    # Required for audio conversion
brew install libmagic  # Required for file type detection
```

#### Linux (Ubuntu/Debian)
```bash
sudo apt-get update
sudo apt-get install ffmpeg
sudo apt-get install libmagic1
```

### Python Dependencies
- Python 3.x
- See requirements.txt for Python package dependencies

## Installation

1. Clone the repository:
```bash
git clone https://github.com/YOUR_USERNAME/audio-analyzer.git
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

## Usage

```bash
python3 calculate_sti.py path/to/your/audio.webm --log-file analysis.log
```

## Output

The tool provides:
- PESQ score (ranging from -0.5 to 4.5)
- Quality category (Poor to Outstanding)
- Signal-to-Noise Ratio (SNR) in dB
- Sample rate information

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
   - Try running without the log file first: `python3 calculate_sti.py path/to/your/audio.webm`

## License

MIT License

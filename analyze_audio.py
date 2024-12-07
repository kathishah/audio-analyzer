#!/usr/bin/env python3
"""
Command-line interface for audio analysis
"""

import argparse
import logging
import sys
from audio_analyzer import AudioAnalyzer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def main():
    """Main entry point for the audio analyzer"""
    parser = argparse.ArgumentParser(description='Analyze audio quality using PESQ metric')
    parser.add_argument('input_file', type=str, help='Path to the input audio file (WebM, WAV, etc.)')
    parser.add_argument('--log-file', type=str, help='Path to log file (optional)')
    args = parser.parse_args()
    
    # Add file handler if log file is specified
    if args.log_file:
        file_handler = logging.FileHandler(args.log_file)
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(file_handler)
    
    try:
        logger.info("Starting audio quality analysis")
        analyzer = AudioAnalyzer()
        results = analyzer.analyze_audio(args.input_file)
        
        if results:
            print("\nAudio Quality Analysis Results:")
            print("-" * 30)
            for key, value in results.items():
                print(f"{key}: {value}")
            logger.info("Analysis results displayed successfully")
            return 0
        else:
            logger.error("Analysis failed to produce results")
            return 1
            
    except Exception as e:
        logger.error(f"Error during analysis: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
"""
Test script for video processing functionality.

This script tests frame extraction and audio extraction without database.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.video_processor import VideoProcessingService
from src.utils.logger import setup_logging, get_logger

setup_logging()
logger = get_logger(__name__)


def test_video_processing(video_path: str, interval_ms: int = 30):
    """
    Test video processing on a sample video.
    
    Args:
        video_path: Path to test video file
        interval_ms: Frame extraction interval
    """
    logger.info(f"Testing video processing: {video_path}")
    logger.info(f"Frame interval: {interval_ms}ms")
    
    # Create processor
    processor = VideoProcessingService()
    
    # Generate test processing ID
    processing_id = processor._generate_processing_id(video_id=999, user_id=1)
    logger.info(f"Processing ID: {processing_id}")
    
    try:
        # Test frame extraction
        logger.info("\n" + "="*60)
        logger.info("STEP 1: Frame Extraction")
        logger.info("="*60)
        
        frames_result = processor.extract_frames(
            video_path=video_path,
            processing_id=processing_id,
            interval_ms=interval_ms
        )
        
        logger.info(f"\nFrames extracted: {frames_result['total_frames_extracted']}")
        logger.info(f"Frames directory: {frames_result['frames_directory']}")
        logger.info(f"Video FPS: {frames_result['video_fps']}")
        logger.info(f"Video duration: {frames_result['video_duration_sec']:.2f}s")
        logger.info(f"Video resolution: {frames_result['video_resolution']}")
        
        # Test audio extraction
        logger.info("\n" + "="*60)
        logger.info("STEP 2: Audio Extraction")
        logger.info("="*60)
        
        audio_result = processor.extract_audio(
            video_path=video_path,
            processing_id=processing_id
        )
        
        if audio_result.get('has_audio'):
            logger.info(f"\nAudio extracted: YES")
            logger.info(f"Audio file: {audio_result['audio_path']}")
            logger.info(f"Duration: {audio_result['duration_sec']:.2f}s")
            logger.info(f"Sample rate: {audio_result['sample_rate']}Hz")
            logger.info(f"Channels: {audio_result['channels']}")
            logger.info(f"File size: {audio_result['file_size_bytes']/1024/1024:.2f}MB")
        else:
            logger.info(f"\nAudio extracted: NO (video has no audio track)")
        
        # Summary
        logger.info("\n" + "="*60)
        logger.info("PROCESSING COMPLETED SUCCESSFULLY")
        logger.info("="*60)
        logger.info(f"\nProcessing ID: {processing_id}")
        logger.info(f"Frames: {frames_result['total_frames_extracted']}")
        logger.info(f"Audio: {'Yes' if audio_result.get('has_audio') else 'No'}")
        logger.info(f"\nCheck output:")
        logger.info(f"  Frames: storage/frames/{processing_id}/")
        logger.info(f"  Audio:  storage/audio/{processing_id}/")
        
        return True
        
    except Exception as e:
        logger.error(f"\nProcessing failed: {str(e)}", exc_info=True)
        return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test video processing")
    parser.add_argument(
        "video_path",
        help="Path to video file to process"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=30,
        help="Frame extraction interval in milliseconds (default: 30)"
    )
    
    args = parser.parse_args()
    
    # Check if video file exists
    if not Path(args.video_path).exists():
        logger.error(f"Video file not found: {args.video_path}")
        sys.exit(1)
    
    # Run test
    success = test_video_processing(args.video_path, args.interval)
    
    sys.exit(0 if success else 1)

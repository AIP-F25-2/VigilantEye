"""AI services for audio analysis."""

import json
from pathlib import Path
from typing import Dict, List, Optional

import librosa
import numpy as np

from src.config.ai_config import AIConfig
from src.utils.logger import get_logger

logger = get_logger(__name__)
ai_config = AIConfig()

# Try to import whisper (openai-whisper package)
try:
    import whisper
    WHISPER_LIB = "openai-whisper"
except ImportError:
    # Fallback to faster-whisper
    try:
        from faster_whisper import WhisperModel
        whisper = None
        WHISPER_LIB = "faster-whisper"
    except ImportError:
        whisper = None
        WHISPER_LIB = None
        logger.warning("Neither openai-whisper nor faster-whisper is available")

# Try to import panns_inference (optional, requires data files)
# Note: On Windows, wget is not available, so data files must be downloaded manually
# Run: python scripts/setup_panns_data.py to download required data files
try:
    from panns_inference import AudioTagging
    PANNS_AVAILABLE = True
except (ImportError, FileNotFoundError, Exception) as e:
    AudioTagging = None
    PANNS_AVAILABLE = False
    # Only log warning if it's not a FileNotFoundError (expected on first run)
    error_msg = str(e)
    if "class_labels_indices.csv" in error_msg or "wget" in error_msg.lower():
        logger.info(f"panns_inference data files not found. Audio classification will be disabled. "
                   f"Run 'python scripts/setup_panns_data.py' to enable audio classification. "
                   f"Error: {e}")
    else:
        logger.warning(f"panns_inference not available: {e}. Audio classification will be disabled.")


class AudioClassifier:
    """Classify sounds in audio using PANNs."""

    def __init__(self):
        """Initialize audio classifier."""
        if not PANNS_AVAILABLE or AudioTagging is None:
            self.model = None
            self.threshold = ai_config.audio_classification_threshold
            logger.warning("Audio classifier disabled - panns_inference not available")
            return
        
        try:
            self.model = AudioTagging(checkpoint_path=None, device=ai_config.ai_device)
            self.threshold = ai_config.audio_classification_threshold
            logger.info("Audio classifier initialized")
        except (FileNotFoundError, Exception) as e:
            self.model = None
            self.threshold = ai_config.audio_classification_threshold
            logger.warning(f"Audio classifier disabled - panns_inference initialization failed: {e}")

    def classify_audio(self, audio_path: str) -> Dict:
        """
        Classify sounds in audio file.
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            Dictionary with classification results
        """
        logger.info(f"Classifying audio: {audio_path}")
        
        # Check if model is available
        if self.model is None:
            logger.warning("Audio classifier not available - panns_inference not properly initialized")
            return {
                'all_sounds': [],
                'dominant_sounds': [],
                'total_detected': 0,
                'error': 'Audio classifier not available - panns_inference requires data files',
                'disabled': True
            }
        
        try:
            # Load audio
            audio, sr = librosa.load(audio_path, sr=32000, mono=True)
            
            # Classify
            (clipwise_output, embedding) = self.model.inference(audio)
            
            # Get labels and scores
            labels = self.model.labels
            scores = clipwise_output[0]
            
            # Filter by threshold
            detected_sounds = []
            for label, score in zip(labels, scores):
                if score >= self.threshold:
                    detected_sounds.append({
                        'label': label,
                        'confidence': float(score)
                    })
            
            # Sort by confidence
            detected_sounds.sort(key=lambda x: x['confidence'], reverse=True)
            
            # Get dominant sounds (top 5)
            dominant_sounds = [s['label'] for s in detected_sounds[:5]]
            
            result = {
                'all_sounds': detected_sounds,
                'dominant_sounds': dominant_sounds,
                'total_detected': len(detected_sounds)
            }
            
            logger.info(
                f"Audio classification completed: "
                f"{len(detected_sounds)} sounds detected, "
                f"dominant: {', '.join(dominant_sounds[:3])}"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Audio classification failed: {e}", exc_info=True)
            return {
                'all_sounds': [],
                'dominant_sounds': [],
                'total_detected': 0,
                'error': str(e)
            }


class SpeechToText:
    """Convert speech to text using Whisper."""

    def __init__(self):
        """Initialize speech-to-text model."""
        if WHISPER_LIB == "openai-whisper" and whisper:
            self.model = whisper.load_model(
                ai_config.whisper_model,
                device=ai_config.whisper_device
            )
            self.use_faster_whisper = False
        elif WHISPER_LIB == "faster-whisper":
            from faster_whisper import WhisperModel
            self.model = WhisperModel(
                ai_config.whisper_model,
                device=ai_config.whisper_device
            )
            self.use_faster_whisper = True
        else:
            raise ImportError("No Whisper library available. Install openai-whisper or faster-whisper")
        
        logger.info(f"Whisper model loaded: {ai_config.whisper_model} ({WHISPER_LIB})")

    def transcribe(self, audio_path: str) -> Dict:
        """
        Transcribe speech from audio file.
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            Dictionary with transcription results
        """
        logger.info(f"Transcribing audio: {audio_path}")
        
        try:
            if self.use_faster_whisper:
                # faster-whisper API
                segments, info = self.model.transcribe(
                    audio_path,
                    language=None,
                    task="transcribe"
                )
                transcription = " ".join([seg.text for seg in segments])
                language = info.language
                confidence = 1.0 - (info.no_speech_prob if hasattr(info, 'no_speech_prob') else 0.0)
            else:
                # openai-whisper API
                result = self.model.transcribe(
                    audio_path,
                    language=None,
                    task="transcribe"
                )
                transcription = result['text'].strip()
                language = result.get('language', 'unknown')
                segments = result.get('segments', [])
                if segments:
                    avg_confidence = np.mean([
                        seg.get('no_speech_prob', 0) 
                        for seg in segments
                    ])
                    confidence = 1.0 - avg_confidence
                else:
                    confidence = 0.0 if not transcription else 0.5
            
            result_dict = {
                'transcription': transcription,
                'language': language,
                'confidence': float(confidence),
                'has_speech': bool(transcription),
                'word_count': len(transcription.split()) if transcription else 0
            }
            
            logger.info(
                f"Transcription completed: {len(transcription)} chars, "
                f"language: {language}, confidence: {confidence:.2f}"
            )
            
            return result_dict
            
        except Exception as e:
            logger.error(f"Transcription failed: {e}", exc_info=True)
            return {
                'transcription': '',
                'language': 'unknown',
                'confidence': 0.0,
                'has_speech': False,
                'word_count': 0,
                'error': str(e)
            }


def process_audio_parallel(audio_path: str) -> Dict:
    """
    Process audio with both classification and transcription.
    
    This function is designed to be called in a thread.
    
    Args:
        audio_path: Path to audio file
        
    Returns:
        Combined results from both analyses
    """
    logger.info(f"Starting parallel audio processing: {audio_path}")
    
    try:
        # Initialize models
        classifier = AudioClassifier()
        transcriber = SpeechToText()
        
        # Run both analyses
        classification_result = classifier.classify_audio(audio_path)
        transcription_result = transcriber.transcribe(audio_path)
        
        # Combine results
        result = {
            'audio_path': audio_path,
            'classification': classification_result,
            'transcription': transcription_result,
            'status': 'completed'
        }
        
        logger.info(f"Audio processing completed: {audio_path}")
        return result
        
    except Exception as e:
        logger.error(f"Audio processing failed: {e}", exc_info=True)
        return {
            'audio_path': audio_path,
            'classification': {},
            'transcription': {},
            'status': 'failed',
            'error': str(e)
        }

"""AI services for audio analysis."""

import json
from pathlib import Path
from typing import Dict, List, Optional

import librosa
import numpy as np
import whisper
from panns_inference import AudioTagging

from src.config.ai_config import AIConfig
from src.utils.logger import get_logger

logger = get_logger(__name__)
ai_config = AIConfig()


class AudioClassifier:
    """Classify sounds in audio using PANNs."""

    def __init__(self):
        """Initialize audio classifier."""
        self.model = AudioTagging(checkpoint_path=None, device=ai_config.ai_device)
        self.threshold = ai_config.audio_classification_threshold
        logger.info("Audio classifier initialized")

    def classify_audio(self, audio_path: str) -> Dict:
        """
        Classify sounds in audio file.
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            Dictionary with classification results
        """
        logger.info(f"Classifying audio: {audio_path}")
        
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
        self.model = whisper.load_model(
            ai_config.whisper_model,
            device=ai_config.whisper_device
        )
        logger.info(f"Whisper model loaded: {ai_config.whisper_model}")

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
            # Transcribe
            result = self.model.transcribe(
                audio_path,
                language=None,  # Auto-detect
                task="transcribe"
            )
            
            transcription = result['text'].strip()
            language = result.get('language', 'unknown')
            
            # Calculate confidence (rough estimate from segments)
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

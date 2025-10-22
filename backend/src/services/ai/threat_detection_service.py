"""Threat and emergency detection using LLM."""

import json
import shutil
from pathlib import Path
from typing import Dict

import openai

from src.config.ai_config import AIConfig
from src.utils.logger import get_logger

logger = get_logger(__name__)
ai_config = AIConfig()

# Initialize OpenAI
openai.api_key = ai_config.openai_api_key


class ThreatDetectionService:
    """Detect threats and emergencies using LLM analysis."""

    def __init__(self):
        """Initialize threat detection service."""
        self.model = ai_config.threat_detection_model
        self.threshold = ai_config.threat_threshold
        self.evidence_path = Path(ai_config.evidence_storage_path)
        self.evidence_path.mkdir(parents=True, exist_ok=True)
        logger.info("Threat detection service initialized")

    def analyze_for_threats(
        self,
        image_description: str,
        objects: Dict,
        faces: Dict,
        persons: Dict = None,
        audio_analysis: Dict = None
    ) -> Dict:
        """
        Analyze scene for threats using LLM.
        
        Args:
            image_description: Natural language description of image
            objects: Object detection results
            faces: Face detection results
            audio_analysis: Optional audio analysis results
            
        Returns:
            Threat assessment results
        """
        logger.info("Analyzing for threats...")
        
        try:
            # Build context for LLM
            context = self._build_threat_context(
                image_description,
                objects,
                faces,
                persons,
                audio_analysis
            )
            
            # Call LLM for threat assessment
            threat_assessment = self._call_llm_for_threat_analysis(context)
            
            logger.info(
                f"Threat analysis completed: "
                f"is_threat={threat_assessment['is_threat']}, "
                f"level={threat_assessment['threat_level']}"
            )
            
            return threat_assessment
            
        except Exception as e:
            logger.error(f"Threat analysis failed: {e}", exc_info=True)
            return {
                'is_threat': False,
                'threat_level': 'SAFE',
                'threat_confidence': 0.0,
                'threat_types': [],
                'threat_description': 'Analysis failed',
                'is_emergency': False,
                'recommended_action': 'None',
                'priority_level': 0,
                'error': str(e)
            }

    def _build_threat_context(
        self,
        description: str,
        objects: Dict,
        faces: Dict,
        persons: Dict = None,
        audio: Dict = None
    ) -> str:
        """Build context string for LLM."""
        context_parts = []
        
        # Image description
        context_parts.append(f"Scene Description: {description}")
        
        # Objects
        if objects.get('objects'):
            obj_list = [obj['label'] for obj in objects['objects']]
            context_parts.append(f"Detected Objects: {', '.join(obj_list)}")
        
        if objects.get('people_count', 0) > 0:
            context_parts.append(f"People Count: {objects['people_count']}")
        
        # Faces
        if faces.get('faces'):
            emotions = [f['emotion'] for f in faces['faces'] if 'emotion' in f]
            if emotions:
                context_parts.append(f"Facial Expressions: {', '.join(emotions)}")
        
        # Persons (clothing/appearance analysis)
        if persons and persons.get('persons'):
            person_count = persons.get('person_count', 0)
            context_parts.append(f"Persons Detected: {person_count}")
            
            for i, person in enumerate(persons['persons'][:3], 1):  # Limit to 3 persons
                clothing_info = person.get('clothing_analysis', {})
                if clothing_info.get('clothing_signature'):
                    context_parts.append(f"Person {i} Clothing: {clothing_info['clothing_signature']}")
                
                face_info = person.get('face_analysis')
                if face_info:
                    context_parts.append(f"Person {i} Face: Age {face_info.get('estimated_age', 'unknown')}, Gender {face_info.get('gender', 'unknown')}")
        
        # Audio
        if audio:
            if audio.get('classification', {}).get('dominant_sounds'):
                sounds = audio['classification']['dominant_sounds']
                context_parts.append(f"Audio Sounds: {', '.join(sounds)}")
            
            if audio.get('transcription', {}).get('transcription'):
                text = audio['transcription']['transcription'][:200]
                context_parts.append(f"Audio Transcription: \"{text}\"")
        
        return "\n".join(context_parts)

    def _call_llm_for_threat_analysis(self, context: str) -> Dict:
        """Call LLM for threat assessment."""
        
        system_prompt = """You are a security AI analyzing surveillance footage for threats and emergencies.

Analyze the provided scene information and determine:
1. Is there a potential threat or emergency?
2. What is the threat level? (SAFE, LOW, MEDIUM, HIGH, CRITICAL)
3. What type of threat? (weapon, violence, fire, accident, medical, suspicious_behavior, etc.)
4. Is immediate emergency response needed?
5. What action should be taken?

Consider:
- Weapons or dangerous objects
- Violence or aggressive behavior
- Fire or smoke
- Medical emergencies
- Accidents or injuries
- Suspicious activities
- Distress signals in audio

Respond in JSON format with:
{
    "is_threat": boolean,
    "threat_level": "SAFE|LOW|MEDIUM|HIGH|CRITICAL",
    "threat_confidence": float (0-1),
    "threat_types": [list of threat types],
    "threat_description": "detailed description",
    "is_emergency": boolean,
    "emergency_type": "medical|fire|accident|violence|other",
    "recommended_action": "specific action to take",
    "priority_level": int (1-10, 10 highest)
}"""

        try:
            response = openai.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Analyze this scene:\n\n{context}"}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            
            # Validate and normalize
            result['is_threat'] = bool(result.get('is_threat', False))
            result['threat_level'] = result.get('threat_level', 'SAFE').upper()
            result['threat_confidence'] = float(result.get('threat_confidence', 0.0))
            result['is_emergency'] = bool(result.get('is_emergency', False))
            result['priority_level'] = int(result.get('priority_level', 0))
            
            return result
            
        except Exception as e:
            logger.error(f"LLM call failed: {e}", exc_info=True)
            return {
                'is_threat': False,
                'threat_level': 'SAFE',
                'threat_confidence': 0.0,
                'threat_types': [],
                'threat_description': f'LLM analysis failed: {str(e)}',
                'is_emergency': False,
                'recommended_action': 'Review manually',
                'priority_level': 0
            }

    def store_evidence(
        self,
        image_path: str,
        processing_id: str,
        frame_timestamp_ms: int,
        threat_assessment: Dict
    ) -> Dict:
        """
        Store image as evidence if threat detected.
        
        Args:
            image_path: Path to original image
            processing_id: Processing batch ID
            frame_timestamp_ms: Frame timestamp
            threat_assessment: Threat assessment results
            
        Returns:
            Evidence storage information
        """
        if not threat_assessment.get('is_threat'):
            return {'evidence_stored': False}
        
        try:
            # Create evidence directory
            evidence_dir = self.evidence_path / processing_id
            evidence_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate evidence filename
            threat_level = threat_assessment['threat_level'].lower()
            filename = f"evidence_{threat_level}_{frame_timestamp_ms}ms.jpg"
            evidence_path = evidence_dir / filename
            
            # Copy file
            shutil.copy2(image_path, evidence_path)
            
            # Save assessment
            assessment_path = evidence_dir / f"{filename}.json"
            with open(assessment_path, 'w') as f:
                json.dump({
                    'image_path': str(image_path),
                    'evidence_path': str(evidence_path),
                    'frame_timestamp_ms': frame_timestamp_ms,
                    'threat_assessment': threat_assessment
                }, f, indent=2)
            
            logger.info(f"Evidence stored: {evidence_path}")
            
            return {
                'evidence_stored': True,
                'evidence_path': str(evidence_path),
                'evidence_filename': filename
            }
            
        except Exception as e:
            logger.error(f"Failed to store evidence: {e}", exc_info=True)
            return {
                'evidence_stored': False,
                'error': str(e)
            }


def detect_threats_in_frame(
    image_path: str,
    frame_timestamp_ms: int,
    image_analysis: Dict,
    face_analysis: Dict,
    person_analysis: Dict = None,
    audio_analysis: Dict = None,
    processing_id: str = None
) -> Dict:
    """
    Detect threats in a frame with all available data.
    
    This function is designed to be called in a thread.
    
    Args:
        image_path: Path to image file
        frame_timestamp_ms: Frame timestamp
        image_analysis: Image analysis results
        face_analysis: Face analysis results
        audio_analysis: Optional audio analysis
        processing_id: Processing batch ID
        
    Returns:
        Threat detection results with evidence storage
    """
    logger.info(f"Detecting threats in frame: {image_path}")
    
    try:
        service = ThreatDetectionService()
        
        # Analyze for threats
        threat_assessment = service.analyze_for_threats(
            image_description=image_analysis.get('combined_description', ''),
            objects=image_analysis.get('objects', {}),
            faces=face_analysis,
            persons=person_analysis,
            audio_analysis=audio_analysis
        )
        
        # Store evidence if threat detected
        evidence_info = {}
        if threat_assessment['is_threat'] and processing_id:
            evidence_info = service.store_evidence(
                image_path,
                processing_id,
                frame_timestamp_ms,
                threat_assessment
            )
        
        result = {
            'image_path': image_path,
            'frame_timestamp_ms': frame_timestamp_ms,
            'threat_assessment': threat_assessment,
            'evidence_info': evidence_info,
            'status': 'completed'
        }
        
        logger.info(
            f"Threat detection completed: "
            f"threat={threat_assessment['is_threat']}, "
            f"level={threat_assessment['threat_level']}"
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Threat detection failed: {e}", exc_info=True)
        return {
            'image_path': image_path,
            'frame_timestamp_ms': frame_timestamp_ms,
            'status': 'failed',
            'error': str(e)
        }

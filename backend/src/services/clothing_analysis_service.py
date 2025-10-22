"""Clothing analysis service for person identification and evidence collection."""

import json
import shutil
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.person_embeddings import PersonEmbedding, PersonAppearance, PersonMatch, PersonType
from src.services.ai.clothing_recognition_service import ClothingRecognitionService
from src.services.ai.person_vector_db_manager import PersonVectorDBManager
from src.services.ai.face_recognition_service import FaceRecognitionService
from src.services.ai.vector_db_manager import VectorDBManager
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ClothingAnalysisService:
    """Service for analyzing clothing and appearance to identify persons."""

    def __init__(self, session: AsyncSession):
        """Initialize clothing analysis service."""
        self.session = session
        self.clothing_service = ClothingRecognitionService()
        self.face_service = FaceRecognitionService()
        self.person_vector_db = PersonVectorDBManager()
        self.face_vector_db = VectorDBManager()

    async def analyze_person_in_image(
        self,
        image_path: str,
        video_id: int,
        frame_timestamp_ms: int,
        processing_id: str,
        evidence_folder: Path
    ) -> Dict:
        """
        Analyze person in image for identification and evidence collection.
        
        Args:
            image_path: Path to image file
            video_id: Video ID
            frame_timestamp_ms: Frame timestamp
            processing_id: Processing batch ID
            evidence_folder: Evidence folder path
            
        Returns:
            Analysis results with person identification
        """
        logger.info(f"Analyzing person in image: {image_path}")
        
        try:
            # Detect person regions
            person_regions = self.clothing_service.detect_person_regions(image_path)
            
            if not person_regions:
                return {
                    'image_path': image_path,
                    'frame_timestamp_ms': frame_timestamp_ms,
                    'person_count': 0,
                    'persons': [],
                    'status': 'no_persons_detected'
                }
            
            analyzed_persons = []
            
            for person_region in person_regions:
                # Analyze clothing and appearance
                clothing_analysis = self.clothing_service.analyze_clothing(
                    image_path, person_region['bounding_box']
                )
                
                # Try face detection in person region
                face_analysis = await self._analyze_face_in_person_region(
                    image_path, person_region['bounding_box']
                )
                
                # Determine person identification method
                person_id_result = await self._identify_person(
                    clothing_analysis, face_analysis, video_id, frame_timestamp_ms
                )
                
                # Save person image and create appearance record
                appearance_data = await self._save_person_appearance(
                    image_path,
                    person_region,
                    clothing_analysis,
                    face_analysis,
                    person_id_result,
                    video_id,
                    frame_timestamp_ms,
                    processing_id,
                    evidence_folder
                )
                
                analyzed_persons.append({
                    'person_region': person_region,
                    'clothing_analysis': clothing_analysis,
                    'face_analysis': face_analysis,
                    'person_identification': person_id_result,
                    'appearance_data': appearance_data
                })
            
            return {
                'image_path': image_path,
                'frame_timestamp_ms': frame_timestamp_ms,
                'person_count': len(analyzed_persons),
                'persons': analyzed_persons,
                'status': 'completed'
            }
            
        except Exception as e:
            logger.error(f"Person analysis failed: {e}", exc_info=True)
            return {
                'image_path': image_path,
                'frame_timestamp_ms': frame_timestamp_ms,
                'person_count': 0,
                'persons': [],
                'status': 'failed',
                'error': str(e)
            }

    async def _analyze_face_in_person_region(
        self,
        image_path: str,
        person_box: Dict
    ) -> Optional[Dict]:
        """Analyze face within person region."""
        try:
            # Detect faces in the person region
            faces = self.face_service.detect_faces(image_path)
            
            if not faces:
                return None
            
            # Find faces that overlap with person region
            person_x = person_box['x']
            person_y = person_box['y']
            person_w = person_box['width']
            person_h = person_box['height']
            
            overlapping_faces = []
            for face in faces:
                face_x = face['bounding_box']['x']
                face_y = face['bounding_box']['y']
                face_w = face['bounding_box']['width']
                face_h = face['bounding_box']['height']
                
                # Check if face overlaps with person region
                if (face_x < person_x + person_w and face_x + face_w > person_x and
                    face_y < person_y + person_h and face_y + face_h > person_y):
                    overlapping_faces.append(face)
            
            if not overlapping_faces:
                return None
            
            # Use the largest overlapping face
            best_face = max(overlapping_faces, key=lambda f: f['confidence'])
            
            # Process the face
            face_result = self.face_service.process_face(image_path, best_face)
            
            return face_result
            
        except Exception as e:
            logger.error(f"Face analysis in person region failed: {e}")
            return None

    async def _identify_person(
        self,
        clothing_analysis: Dict,
        face_analysis: Optional[Dict],
        video_id: int,
        frame_timestamp_ms: int
    ) -> Dict:
        """Identify person using face and/or clothing analysis."""
        try:
            person_id = None
            identification_method = PersonType.CLOTHING_BASED
            confidence = 0.0
            match_similarity = 0.0
            
            # Try face-based identification first
            if face_analysis and face_analysis.get('embedding') is not None:
                face_embedding = np.array(face_analysis['embedding'])
                
                # Search for similar faces
                similar_faces = self.face_vector_db.search_similar_faces(
                    face_embedding, n_results=1
                )
                
                if similar_faces:
                    match = similar_faces[0]
                    person_id = match['face_id']
                    identification_method = PersonType.FACE_BASED
                    confidence = match['similarity']
                    match_similarity = match['similarity']
                    
                    logger.info(f"Face-based match found: {person_id} (similarity: {confidence:.3f})")
            
            # If no face match or no face detected, try clothing-based identification
            if person_id is None and clothing_analysis.get('clothing_signature'):
                clothing_signature = clothing_analysis['clothing_signature']
                
                # Search for persons with similar clothing
                similar_persons = self.person_vector_db.search_by_clothing_signature(
                    clothing_signature, n_results=1
                )
                
                if similar_persons:
                    match = similar_persons[0]
                    person_id = match['person_id']
                    identification_method = PersonType.CLOTHING_BASED
                    confidence = 0.8  # Default confidence for clothing match
                    match_similarity = 0.8
                    
                    logger.info(f"Clothing-based match found: {person_id}")
            
            # If still no match, create new person
            if person_id is None:
                person_id = f"person_{uuid.uuid4().hex[:12]}"
                identification_method = PersonType.CLOTHING_BASED
                confidence = 0.5  # New person confidence
                
                logger.info(f"Created new person: {person_id}")
            
            return {
                'person_id': person_id,
                'identification_method': identification_method.value,
                'confidence': confidence,
                'match_similarity': match_similarity,
                'is_new_person': person_id.startswith('person_') and len(person_id) > 20
            }
            
        except Exception as e:
            logger.error(f"Person identification failed: {e}")
            return {
                'person_id': f"person_{uuid.uuid4().hex[:12]}",
                'identification_method': PersonType.CLOTHING_BASED.value,
                'confidence': 0.0,
                'match_similarity': 0.0,
                'is_new_person': True,
                'error': str(e)
            }

    async def _save_person_appearance(
        self,
        image_path: str,
        person_region: Dict,
        clothing_analysis: Dict,
        face_analysis: Optional[Dict],
        person_id_result: Dict,
        video_id: int,
        frame_timestamp_ms: int,
        processing_id: str,
        evidence_folder: Path
    ) -> Dict:
        """Save person appearance data and images."""
        try:
            # Create person image filename
            person_filename = f"person_{person_id_result['person_id']}_{frame_timestamp_ms}ms.jpg"
            person_image_path = evidence_folder / person_filename
            
            # Crop and save person image
            await self._crop_and_save_person_image(
                image_path, person_region['bounding_box'], person_image_path
            )
            
            # Create thumbnail
            thumbnail_filename = f"thumb_{person_filename}"
            thumbnail_path = evidence_folder / thumbnail_filename
            await self._create_thumbnail(person_image_path, thumbnail_path)
            
            # Prepare appearance metadata
            appearance_metadata = {
                'clothing_analysis': clothing_analysis,
                'face_analysis': face_analysis,
                'person_identification': person_id_result,
                'processing_id': processing_id
            }
            
            # Create appearance record
            appearance = PersonAppearance(
                person_id=person_id_result['person_id'],
                video_id=video_id,
                frame_timestamp_ms=frame_timestamp_ms,
                processing_id=processing_id,
                bounding_box_x=person_region['bounding_box']['x'],
                bounding_box_y=person_region['bounding_box']['y'],
                bounding_box_width=person_region['bounding_box']['width'],
                bounding_box_height=person_region['bounding_box']['height'],
                detection_confidence=person_region['confidence'],
                face_detected=face_analysis is not None,
                face_confidence=face_analysis.get('confidence') if face_analysis else None,
                clothing_signature=clothing_analysis.get('clothing_signature'),
                clothing_confidence=0.8,  # Default clothing confidence
                appearance_metadata=appearance_metadata,
                image_path=str(person_image_path),
                thumbnail_path=str(thumbnail_path)
            )
            
            self.session.add(appearance)
            await self.session.flush()
            
            # Update or create person embedding record
            await self._update_person_embedding(
                person_id_result, clothing_analysis, face_analysis, video_id, frame_timestamp_ms
            )
            
            return {
                'appearance_id': appearance.id,
                'person_image_path': str(person_image_path),
                'thumbnail_path': str(thumbnail_path),
                'person_id': person_id_result['person_id']
            }
            
        except Exception as e:
            logger.error(f"Failed to save person appearance: {e}")
            return {'error': str(e)}

    async def _crop_and_save_person_image(
        self,
        image_path: str,
        bounding_box: Dict,
        output_path: Path
    ) -> None:
        """Crop person region and save image."""
        try:
            # Load image
            image = cv2.imread(image_path)
            
            # Extract coordinates
            x = bounding_box['x']
            y = bounding_box['y']
            w = bounding_box['width']
            h = bounding_box['height']
            
            # Add padding
            padding = 20
            x = max(0, x - padding)
            y = max(0, y - padding)
            w = w + 2 * padding
            h = h + 2 * padding
            
            # Ensure coordinates are within image bounds
            x = min(x, image.shape[1] - 1)
            y = min(y, image.shape[0] - 1)
            w = min(w, image.shape[1] - x)
            h = min(h, image.shape[0] - y)
            
            # Crop person region
            person_crop = image[y:y+h, x:x+w]
            
            # Save cropped image
            cv2.imwrite(str(output_path), person_crop)
            
        except Exception as e:
            logger.error(f"Failed to crop and save person image: {e}")

    async def _create_thumbnail(self, image_path: Path, thumbnail_path: Path) -> None:
        """Create thumbnail of person image."""
        try:
            # Load image
            image = cv2.imread(str(image_path))
            
            # Resize to thumbnail size (150x150)
            thumbnail = cv2.resize(image, (150, 150))
            
            # Save thumbnail
            cv2.imwrite(str(thumbnail_path), thumbnail)
            
        except Exception as e:
            logger.error(f"Failed to create thumbnail: {e}")

    async def _update_person_embedding(
        self,
        person_id_result: Dict,
        clothing_analysis: Dict,
        face_analysis: Optional[Dict],
        video_id: int,
        frame_timestamp_ms: int
    ) -> None:
        """Update or create person embedding record."""
        try:
            person_id = person_id_result['person_id']
            
            # Check if person embedding exists
            existing_person = await self.session.execute(
                select(PersonEmbedding).where(PersonEmbedding.person_id == person_id)
            )
            existing_person = existing_person.scalar_one_or_none()
            
            if existing_person:
                # Update existing person
                existing_person.last_seen_video_id = video_id
                existing_person.last_seen_timestamp_ms = frame_timestamp_ms
                existing_person.total_appearances += 1
                
                # Update appearance metadata
                if clothing_analysis:
                    existing_person.appearance_metadata = clothing_analysis
                    if clothing_analysis.get('clothing_signature'):
                        existing_person.clothing_signature = clothing_analysis['clothing_signature']
                
                await self.session.commit()
            else:
                # Create new person embedding
                person_embedding = PersonEmbedding(
                    person_id=person_id,
                    person_type=PersonType(person_id_result['identification_method']),
                    clothing_signature=clothing_analysis.get('clothing_signature'),
                    clothing_confidence=person_id_result['confidence'],
                    appearance_metadata=clothing_analysis,
                    first_seen_video_id=video_id,
                    first_seen_timestamp_ms=frame_timestamp_ms,
                    last_seen_video_id=video_id,
                    last_seen_timestamp_ms=frame_timestamp_ms,
                    total_appearances=1,
                    unique_videos=1
                )
                
                # Add face information if available
                if face_analysis:
                    person_embedding.face_id = face_analysis.get('face_id')
                    person_embedding.face_embedding = json.dumps(face_analysis.get('embedding'))
                    person_embedding.face_confidence = face_analysis.get('confidence')
                    person_embedding.estimated_age = face_analysis.get('estimated_age')
                    person_embedding.age_range = face_analysis.get('age_range')
                    person_embedding.gender = face_analysis.get('gender')
                    person_embedding.gender_confidence = face_analysis.get('gender_confidence')
                    person_embedding.ethnicity = face_analysis.get('ethnicity')
                
                # Add clothing information
                if clothing_analysis:
                    person_embedding.dominant_clothing_type = clothing_analysis.get('clothing_types', {}).get('dominant_type')
                    person_embedding.dominant_color = clothing_analysis.get('colors', {}).get('dominant_color')
                    person_embedding.dominant_texture = clothing_analysis.get('textures', {}).get('dominant_texture')
                
                self.session.add(person_embedding)
                await self.session.commit()
                
                # Add to vector database
                if clothing_analysis.get('clothing_signature'):
                    clothing_embedding = self._generate_clothing_embedding(clothing_analysis)
                    if clothing_embedding is not None:
                        self.person_vector_db.add_person_embedding(
                            person_id,
                            PersonType.CLOTHING_BASED,
                            clothing_embedding,
                            clothing_analysis
                        )
                
                if face_analysis and face_analysis.get('embedding'):
                    face_embedding = np.array(face_analysis['embedding'])
                    self.person_vector_db.add_person_embedding(
                        person_id,
                        PersonType.FACE_BASED,
                        face_embedding,
                        face_analysis
                    )
            
        except Exception as e:
            logger.error(f"Failed to update person embedding: {e}")

    def _generate_clothing_embedding(self, clothing_analysis: Dict) -> Optional[np.ndarray]:
        """Generate embedding vector from clothing analysis."""
        try:
            # Create a feature vector from clothing analysis
            features = []
            
            # Add clothing type probabilities
            clothing_types = clothing_analysis.get('clothing_types', {})
            for category in self.clothing_service.clothing_categories:
                features.append(clothing_types.get(category, 0.0))
            
            # Add color information
            colors = clothing_analysis.get('colors', {})
            color_dist = colors.get('color_distribution', {})
            features.extend([
                color_dist.get('brightness', 0.0) / 255.0,
                color_dist.get('saturation', 0.0) / 255.0,
                1.0 if color_dist.get('is_dark', False) else 0.0,
                1.0 if color_dist.get('is_bright', False) else 0.0,
                1.0 if color_dist.get('is_colorful', False) else 0.0
            ])
            
            # Add texture information
            textures = clothing_analysis.get('textures', {})
            for pattern in self.clothing_service.texture_patterns:
                features.append(textures.get(pattern, 0.0))
            
            # Convert to numpy array
            embedding = np.array(features, dtype=np.float32)
            
            # Normalize
            embedding = embedding / (np.linalg.norm(embedding) + 1e-8)
            
            return embedding
            
        except Exception as e:
            logger.error(f"Failed to generate clothing embedding: {e}")
            return None

    async def find_related_persons_for_ticket(
        self,
        ticket_id: int,
        person_id: str,
        evidence_folder: Path
    ) -> List[Dict]:
        """
        Find all related persons for a ticket based on clothing/appearance matching.
        
        Args:
            ticket_id: Ticket ID
            person_id: Person ID from threat detection
            evidence_folder: Evidence folder path
            
        Returns:
            List of related person appearances
        """
        try:
            logger.info(f"Finding related persons for ticket {ticket_id}, person {person_id}")
            
            # Get person embedding
            person_embedding = await self.session.execute(
                select(PersonEmbedding).where(PersonEmbedding.person_id == person_id)
            )
            person_embedding = person_embedding.scalar_one_or_none()
            
            if not person_embedding:
                logger.warning(f"Person embedding not found: {person_id}")
                return []
            
            # Search for similar persons
            related_persons = []
            
            # Search by clothing signature if available
            if person_embedding.clothing_signature:
                similar_persons = self.person_vector_db.search_by_clothing_signature(
                    person_embedding.clothing_signature, n_results=20
                )
                
                for match in similar_persons:
                    if match['person_id'] != person_id:
                        # Get all appearances of this person
                        appearances = await self.session.execute(
                            select(PersonAppearance)
                            .where(PersonAppearance.person_id == match['person_id'])
                            .order_by(PersonAppearance.frame_timestamp_ms)
                        )
                        appearances = appearances.scalars().all()
                        
                        for appearance in appearances:
                            related_persons.append({
                                'person_id': appearance.person_id,
                                'video_id': appearance.video_id,
                                'frame_timestamp_ms': appearance.frame_timestamp_ms,
                                'image_path': appearance.image_path,
                                'thumbnail_path': appearance.thumbnail_path,
                                'clothing_signature': appearance.clothing_signature,
                                'match_type': 'clothing_signature',
                                'match_confidence': 0.8
                            })
            
            # Copy related person images to evidence folder
            evidence_persons = []
            for person in related_persons[:10]:  # Limit to 10 related persons
                try:
                    # Copy person image to evidence folder
                    source_path = Path(person['image_path'])
                    if source_path.exists():
                        evidence_filename = f"related_person_{person['person_id']}_{person['frame_timestamp_ms']}ms.jpg"
                        evidence_path = evidence_folder / evidence_filename
                        
                        shutil.copy2(source_path, evidence_path)
                        
                        evidence_persons.append({
                            'person_id': person['person_id'],
                            'video_id': person['video_id'],
                            'frame_timestamp_ms': person['frame_timestamp_ms'],
                            'evidence_filename': evidence_filename,
                            'evidence_path': str(evidence_path),
                            'match_type': person['match_type'],
                            'match_confidence': person['match_confidence']
                        })
                        
                except Exception as e:
                    logger.error(f"Failed to copy person image: {e}")
            
            logger.info(f"Found {len(evidence_persons)} related persons for ticket {ticket_id}")
            return evidence_persons
            
        except Exception as e:
            logger.error(f"Failed to find related persons: {e}")
            return []


# Import statement for SQLAlchemy
from sqlalchemy import select

"""Vector database manager for face embeddings."""

import json
import uuid
from pathlib import Path
from typing import Dict, List, Optional

import chromadb
import numpy as np

from src.config.ai_config import AIConfig
from src.utils.logger import get_logger

logger = get_logger(__name__)
ai_config = AIConfig()


class VectorDBManager:
    """Manage face embeddings in vector database."""

    def __init__(self):
        """Initialize vector database."""
        self.db_path = Path(ai_config.vector_db_path)
        self.db_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize ChromaDB
        self.client = chromadb.PersistentClient(path=str(self.db_path))
        
        # Create or get collection
        self.collection = self.client.get_or_create_collection(
            name="face_embeddings",
            metadata={"description": "Face recognition embeddings"}
        )
        
        logger.info(f"Vector DB initialized at: {self.db_path}")

    def add_face_embedding(
        self,
        face_id: str,
        embedding: np.ndarray,
        metadata: Dict
    ) -> str:
        """
        Add face embedding to vector database.
        
        Args:
            face_id: Unique face identifier
            embedding: Face embedding vector
            metadata: Face metadata (age, gender, etc.)
            
        Returns:
            Vector ID in database
        """
        try:
            vector_id = f"vec_{face_id}"
            
            self.collection.add(
                embeddings=[embedding.tolist()],
                metadatas=[metadata],
                ids=[vector_id]
            )
            
            logger.debug(f"Added face embedding: {face_id}")
            return vector_id
            
        except Exception as e:
            logger.error(f"Failed to add embedding: {e}")
            return None

    def search_similar_faces(
        self,
        query_embedding: np.ndarray,
        n_results: int = 5,
        threshold: float = None
    ) -> List[Dict]:
        """
        Search for similar faces in database.
        
        Args:
            query_embedding: Query face embedding
            n_results: Number of results to return
            threshold: Similarity threshold (0-1)
            
        Returns:
            List of similar faces with distances
        """
        if threshold is None:
            threshold = ai_config.face_recognition_threshold
        
        try:
            results = self.collection.query(
                query_embeddings=[query_embedding.tolist()],
                n_results=n_results
            )
            
            matches = []
            
            if results['ids'] and len(results['ids']) > 0:
                for i in range(len(results['ids'][0])):
                    vector_id = results['ids'][0][i]
                    distance = results['distances'][0][i]
                    metadata = results['metadatas'][0][i]
                    
                    # Convert distance to similarity (0-1, higher is more similar)
                    similarity = 1.0 / (1.0 + distance)
                    
                    if similarity >= threshold:
                        matches.append({
                            'vector_id': vector_id,
                            'face_id': vector_id.replace('vec_', ''),
                            'similarity': float(similarity),
                            'distance': float(distance),
                            'metadata': metadata
                        })
            
            logger.info(f"Found {len(matches)} similar faces above threshold {threshold}")
            return matches
            
        except Exception as e:
            logger.error(f"Face search failed: {e}")
            return []

    def get_face_by_id(self, face_id: str) -> Optional[Dict]:
        """Get face embedding and metadata by ID."""
        try:
            vector_id = f"vec_{face_id}"
            result = self.collection.get(ids=[vector_id])
            
            if result['ids']:
                return {
                    'vector_id': result['ids'][0],
                    'embedding': result['embeddings'][0],
                    'metadata': result['metadatas'][0]
                }
            return None
            
        except Exception as e:
            logger.error(f"Failed to get face: {e}")
            return None

    def update_face_metadata(self, face_id: str, metadata: Dict) -> bool:
        """Update metadata for a face."""
        try:
            vector_id = f"vec_{face_id}"
            self.collection.update(
                ids=[vector_id],
                metadatas=[metadata]
            )
            logger.debug(f"Updated metadata for: {face_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update metadata: {e}")
            return False

    def delete_face(self, face_id: str) -> bool:
        """Delete face from database."""
        try:
            vector_id = f"vec_{face_id}"
            self.collection.delete(ids=[vector_id])
            logger.debug(f"Deleted face: {face_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete face: {e}")
            return False

    def get_stats(self) -> Dict:
        """Get database statistics."""
        try:
            count = self.collection.count()
            return {
                'total_faces': count,
                'collection_name': self.collection.name,
                'db_path': str(self.db_path)
            }
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {'error': str(e)}


def find_or_create_face_id(
    embedding: np.ndarray,
    metadata: Dict,
    db_manager: VectorDBManager = None
) -> Dict:
    """
    Find existing face or create new face ID.
    
    Args:
        embedding: Face embedding vector
        metadata: Face metadata
        db_manager: Optional existing DB manager
        
    Returns:
        Dictionary with face_id and is_new flag
    """
    if db_manager is None:
        db_manager = VectorDBManager()
    
    # Search for similar faces
    similar_faces = db_manager.search_similar_faces(
        embedding,
        n_results=1,
        threshold=ai_config.face_recognition_threshold
    )
    
    if similar_faces:
        # Found matching face
        match = similar_faces[0]
        face_id = match['face_id']
        
        logger.info(
            f"Matched existing face: {face_id} "
            f"(similarity: {match['similarity']:.3f})"
        )
        
        return {
            'face_id': face_id,
            'is_new': False,
            'match_similarity': match['similarity'],
            'vector_id': match['vector_id']
        }
    else:
        # Create new face
        face_id = f"face_{uuid.uuid4().hex[:12]}"
        vector_id = db_manager.add_face_embedding(face_id, embedding, metadata)
        
        logger.info(f"Created new face: {face_id}")
        
        return {
            'face_id': face_id,
            'is_new': True,
            'vector_id': vector_id
        }

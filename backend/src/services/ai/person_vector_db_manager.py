"""Person embeddings vector database manager."""

import json
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import chromadb
import numpy as np

from src.config.ai_config import AIConfig
from src.models.person_embeddings import PersonType
from src.utils.logger import get_logger

logger = get_logger(__name__)
ai_config = AIConfig()


class PersonVectorDBManager:
    """Manage person embeddings in vector database for both face and clothing-based identification."""

    def __init__(self):
        """Initialize person vector database."""
        self.db_path = Path(ai_config.vector_db_path) / "person_embeddings"
        self.db_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize ChromaDB
        self.client = chromadb.PersistentClient(path=str(self.db_path))
        
        # Create or get collections
        self.face_collection = self.client.get_or_create_collection(
            name="face_embeddings",
            metadata={"description": "Face-based person embeddings"}
        )
        
        self.clothing_collection = self.client.get_or_create_collection(
            name="clothing_embeddings",
            metadata={"description": "Clothing-based person embeddings"}
        )
        
        self.combined_collection = self.client.get_or_create_collection(
            name="combined_embeddings",
            metadata={"description": "Combined face and clothing embeddings"}
        )
        
        logger.info(f"Person Vector DB initialized at: {self.db_path}")

    def add_person_embedding(
        self,
        person_id: str,
        embedding_type: PersonType,
        embedding: np.ndarray,
        metadata: Dict
    ) -> str:
        """
        Add person embedding to appropriate collection.
        
        Args:
            person_id: Unique person identifier
            embedding_type: Type of embedding (FACE_BASED, CLOTHING_BASED, COMBINED)
            embedding: Embedding vector
            metadata: Person metadata
            
        Returns:
            Vector ID in database
        """
        try:
            vector_id = f"{embedding_type.value}_{person_id}"
            
            # Choose appropriate collection
            collection = self._get_collection(embedding_type)
            
            # Add to collection
            collection.add(
                embeddings=[embedding.tolist()],
                metadatas=[metadata],
                ids=[vector_id]
            )
            
            logger.debug(f"Added {embedding_type.value} embedding: {person_id}")
            return vector_id
            
        except Exception as e:
            logger.error(f"Failed to add person embedding: {e}")
            return None

    def search_similar_persons(
        self,
        query_embedding: np.ndarray,
        embedding_type: PersonType,
        n_results: int = 5,
        threshold: float = None
    ) -> List[Dict]:
        """
        Search for similar persons in database.
        
        Args:
            query_embedding: Query embedding vector
            embedding_type: Type of embedding to search
            n_results: Number of results to return
            threshold: Similarity threshold (0-1)
            
        Returns:
            List of similar persons with distances
        """
        if threshold is None:
            threshold = self._get_threshold(embedding_type)
        
        try:
            collection = self._get_collection(embedding_type)
            
            results = collection.query(
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
                        # Extract person_id from vector_id
                        person_id = vector_id.replace(f"{embedding_type.value}_", "")
                        
                        matches.append({
                            'vector_id': vector_id,
                            'person_id': person_id,
                            'similarity': float(similarity),
                            'distance': float(distance),
                            'metadata': metadata,
                            'embedding_type': embedding_type.value
                        })
            
            logger.info(f"Found {len(matches)} similar persons above threshold {threshold}")
            return matches
            
        except Exception as e:
            logger.error(f"Person search failed: {e}")
            return []

    def search_by_clothing_signature(
        self,
        clothing_signature: str,
        n_results: int = 10
    ) -> List[Dict]:
        """
        Search for persons by clothing signature.
        
        Args:
            clothing_signature: Clothing signature to search for
            n_results: Number of results to return
            
        Returns:
            List of persons with similar clothing
        """
        try:
            # Search in clothing collection using metadata
            results = self.clothing_collection.get(
                where={"clothing_signature": clothing_signature},
                limit=n_results
            )
            
            matches = []
            if results['ids']:
                for i, vector_id in enumerate(results['ids']):
                    person_id = vector_id.replace("CLOTHING_BASED_", "")
                    metadata = results['metadatas'][i]
                    
                    matches.append({
                        'vector_id': vector_id,
                        'person_id': person_id,
                        'clothing_signature': clothing_signature,
                        'metadata': metadata,
                        'embedding_type': 'CLOTHING_BASED'
                    })
            
            logger.info(f"Found {len(matches)} persons with clothing signature: {clothing_signature}")
            return matches
            
        except Exception as e:
            logger.error(f"Clothing signature search failed: {e}")
            return []

    def find_or_create_person_id(
        self,
        embedding: np.ndarray,
        embedding_type: PersonType,
        metadata: Dict,
        threshold: float = None
    ) -> Dict:
        """
        Find existing person or create new person ID.
        
        Args:
            embedding: Person embedding vector
            embedding_type: Type of embedding
            metadata: Person metadata
            threshold: Similarity threshold
            
        Returns:
            Dictionary with person_id and is_new flag
        """
        if threshold is None:
            threshold = self._get_threshold(embedding_type)
        
        # Search for similar persons
        similar_persons = self.search_similar_persons(
            embedding,
            embedding_type,
            n_results=1,
            threshold=threshold
        )
        
        if similar_persons:
            # Found matching person
            match = similar_persons[0]
            person_id = match['person_id']
            
            logger.info(
                f"Matched existing person: {person_id} "
                f"(similarity: {match['similarity']:.3f})"
            )
            
            return {
                'person_id': person_id,
                'is_new': False,
                'match_similarity': match['similarity'],
                'vector_id': match['vector_id'],
                'embedding_type': embedding_type.value
            }
        else:
            # Create new person
            person_id = f"person_{uuid.uuid4().hex[:12]}"
            vector_id = self.add_person_embedding(person_id, embedding_type, embedding, metadata)
            
            logger.info(f"Created new person: {person_id}")
            
            return {
                'person_id': person_id,
                'is_new': True,
                'vector_id': vector_id,
                'embedding_type': embedding_type.value
            }

    def get_person_by_id(self, person_id: str, embedding_type: PersonType) -> Optional[Dict]:
        """Get person embedding and metadata by ID."""
        try:
            vector_id = f"{embedding_type.value}_{person_id}"
            collection = self._get_collection(embedding_type)
            
            result = collection.get(ids=[vector_id])
            
            if result['ids']:
                return {
                    'vector_id': result['ids'][0],
                    'embedding': result['embeddings'][0],
                    'metadata': result['metadatas'][0],
                    'embedding_type': embedding_type.value
                }
            return None
            
        except Exception as e:
            logger.error(f"Failed to get person: {e}")
            return None

    def update_person_metadata(self, person_id: str, embedding_type: PersonType, metadata: Dict) -> bool:
        """Update metadata for a person."""
        try:
            vector_id = f"{embedding_type.value}_{person_id}"
            collection = self._get_collection(embedding_type)
            
            collection.update(
                ids=[vector_id],
                metadatas=[metadata]
            )
            logger.debug(f"Updated metadata for: {person_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update metadata: {e}")
            return False

    def delete_person(self, person_id: str, embedding_type: PersonType) -> bool:
        """Delete person from database."""
        try:
            vector_id = f"{embedding_type.value}_{person_id}"
            collection = self._get_collection(embedding_type)
            
            collection.delete(ids=[vector_id])
            logger.debug(f"Deleted person: {person_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete person: {e}")
            return False

    def get_all_persons_by_type(self, embedding_type: PersonType) -> List[Dict]:
        """Get all persons of a specific type."""
        try:
            collection = self._get_collection(embedding_type)
            results = collection.get()
            
            persons = []
            if results['ids']:
                for i, vector_id in enumerate(results['ids']):
                    person_id = vector_id.replace(f"{embedding_type.value}_", "")
                    persons.append({
                        'vector_id': vector_id,
                        'person_id': person_id,
                        'embedding': results['embeddings'][i],
                        'metadata': results['metadatas'][i],
                        'embedding_type': embedding_type.value
                    })
            
            return persons
            
        except Exception as e:
            logger.error(f"Failed to get persons by type: {e}")
            return []

    def get_stats(self) -> Dict:
        """Get database statistics."""
        try:
            face_count = self.face_collection.count()
            clothing_count = self.clothing_collection.count()
            combined_count = self.combined_collection.count()
            
            return {
                'total_persons': face_count + clothing_count + combined_count,
                'face_based_persons': face_count,
                'clothing_based_persons': clothing_count,
                'combined_persons': combined_count,
                'db_path': str(self.db_path)
            }
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {'error': str(e)}

    def _get_collection(self, embedding_type: PersonType):
        """Get appropriate collection based on embedding type."""
        if embedding_type == PersonType.FACE_BASED:
            return self.face_collection
        elif embedding_type == PersonType.CLOTHING_BASED:
            return self.clothing_collection
        elif embedding_type == PersonType.COMBINED:
            return self.combined_collection
        else:
            raise ValueError(f"Unknown embedding type: {embedding_type}")

    def _get_threshold(self, embedding_type: PersonType) -> float:
        """Get similarity threshold based on embedding type."""
        if embedding_type == PersonType.FACE_BASED:
            return ai_config.face_recognition_threshold
        elif embedding_type == PersonType.CLOTHING_BASED:
            return 0.7  # Lower threshold for clothing matching
        elif embedding_type == PersonType.COMBINED:
            return 0.8  # Higher threshold for combined matching
        else:
            return 0.5


def find_or_create_person_id(
    embedding: np.ndarray,
    embedding_type: PersonType,
    metadata: Dict,
    db_manager: PersonVectorDBManager = None
) -> Dict:
    """
    Find existing person or create new person ID.
    
    Args:
        embedding: Person embedding vector
        embedding_type: Type of embedding
        metadata: Person metadata
        db_manager: Optional existing DB manager
        
    Returns:
        Dictionary with person_id and is_new flag
    """
    if db_manager is None:
        db_manager = PersonVectorDBManager()
    
    return db_manager.find_or_create_person_id(embedding, embedding_type, metadata)


def search_similar_persons(
    query_embedding: np.ndarray,
    embedding_type: PersonType,
    db_manager: PersonVectorDBManager = None,
    n_results: int = 5,
    threshold: float = None
) -> List[Dict]:
    """
    Search for similar persons in database.
    
    Args:
        query_embedding: Query embedding vector
        embedding_type: Type of embedding to search
        db_manager: Optional existing DB manager
        n_results: Number of results to return
        threshold: Similarity threshold
        
    Returns:
        List of similar persons
    """
    if db_manager is None:
        db_manager = PersonVectorDBManager()
    
    return db_manager.search_similar_persons(
        query_embedding, embedding_type, n_results, threshold
    )

import chromadb
from chromadb.config import Settings
from typing import List, Tuple

class FaceVectorDB:
    def __init__(self, persist_directory: str = "./chroma_db"):
        self.client = chromadb.Client(Settings(persist_directory=persist_directory))
        self.collection = self.client.get_or_create_collection("face_vectors")

    def add_face_vector(self, face_id: str, vector: List[float]):
        """
        Store a face vector with its associated ID.
        """
        self.collection.add(ids=[face_id], embeddings=[vector])

    def compare_and_retrieve(self, vector1: List[float], vector2: List[float], threshold: float = 0.8) -> Tuple[str, str, float]:
        """
        Compare two face vectors and retrieve their IDs and similarity score.
        Returns (id1, id2, similarity_score)
        """
        # Find the closest stored vector to vector1 and vector2
        result1 = self.collection.query(query_embeddings=[vector1], n_results=1)
        result2 = self.collection.query(query_embeddings=[vector2], n_results=1)
        id1 = result1["ids"][0][0] if result1["ids"] else None
        id2 = result2["ids"][0][0] if result2["ids"] else None
        # Compute cosine similarity
        from numpy import dot
        from numpy.linalg import norm
        similarity = dot(vector1, vector2) / (norm(vector1) * norm(vector2))
        return id1, id2, similarity

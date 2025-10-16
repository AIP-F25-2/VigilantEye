import numpy as np
from sklearn.neighbors import NearestNeighbors
from app.db.session import SessionLocal
from app.db.models import FaceVector, Artifact
from app.logger import logger

class VectorIndex:
    def __init__(self):
        self.vectors = None
        self.ids = []
        self.nn = None
        self.rebuild()

    def rebuild(self):
        db = SessionLocal()
        try:
            rows = db.query(FaceVector).all()
            if not rows:
                self.vectors = None
                self.ids = []
                self.nn = None
                return
            mats = []
            ids = []
            for r in rows:
                try:
                    vec = np.frombuffer(r.vector, dtype=np.float32)
                    mats.append(vec)
                    ids.append((r.id, r.person_id, r.artifact_id))
                except Exception:
                    logger.exception("Failed to decode vector")
            if mats:
                self.vectors = np.vstack(mats)
                self.ids = ids
                self.nn = NearestNeighbors(n_neighbors=5, algorithm="auto").fit(self.vectors)
        finally:
            db.close()

    def query(self, vector: np.ndarray, top_k=5):
        if self.nn is None:
            return []
        dists, idxs = self.nn.kneighbors([vector], n_neighbors=top_k)
        results = []
        for d, idx in zip(dists[0], idxs[0]):
            meta = self.ids[idx]
            results.append({"face_vector_id": meta[0], "person_id": meta[1], "artifact_id": meta[2], "distance": float(d)})
        return results

vector_index = VectorIndex()

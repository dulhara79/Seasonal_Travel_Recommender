# vector_memory.py
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np

class VectorMemory:
    def __init__(self, dim_model='all-MiniLM-L6-v2'):
        self.model = SentenceTransformer(dim_model)
        self.embeddings = []
        self.metadatas = []
        self.index = None

    def _encode(self, text):
        return np.array(self.model.encode(text)).astype('float32')

    def add_document(self, doc):
        vec = self._encode(doc["text"])
        self.embeddings.append(vec)
        self.metadatas.append(doc)
        self._rebuild_index()

    def _rebuild_index(self):
        if not self.embeddings:
            return
        dim = self.embeddings[0].shape[0]
        self.index = faiss.IndexFlatL2(dim)
        self.index.add(np.stack(self.embeddings))

    def query(self, text, top_k=3):
        if not self.embeddings:
            return []
        vec = self._encode(text)
        D, I = self.index.search(np.array([vec]), top_k)
        return [self.metadatas[i] for i in I[0] if i < len(self.metadatas)]

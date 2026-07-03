import faiss
import numpy as np


class VectorStore:

    def __init__(self):
        self.index = None
        self.chunks = []

    def build(self, embeddings, chunks):

        embeddings = np.array(
            embeddings,
            dtype="float32"
        )

        dimension = embeddings.shape[1]

        self.index = faiss.IndexFlatL2(
            dimension
        )

        self.index.add(embeddings)

        self.chunks = chunks

    def search(self, query_embedding, k=5):

        k = min(k, len(self.chunks))

        query_embedding = np.array(
            [query_embedding],
            dtype="float32"
        )

        distances, indices = self.index.search(
            query_embedding,
            k
        )

        return [
            self.chunks[i]
            for i in indices[0]
            if i < len(self.chunks)
        ]
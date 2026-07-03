from app.services.chunker import chunk_text
from app.services.embedding_service import (
    embed_texts,
    model
)
from app.services.vector_store import VectorStore


def build_rag_index(text: str):

    chunks = chunk_text(text)

    embeddings = embed_texts(chunks)

    store = VectorStore()

    store.build(
        embeddings,
        chunks
    )

    return store


def search_rag(
    store,
    query: str
):

    query_embedding = model.encode(
        query
    )

    return store.search(
        query_embedding,
        k=5
    )
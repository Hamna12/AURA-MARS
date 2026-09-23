"""
AURA Mars — Retrieval Layer (Phase 2)

Embeds a user question and queries ChromaDB for the top-k most
relevant document chunks, returning them with similarity scores.
"""

from typing import List

import chromadb

from src.config import (
    CHROMA_DB_PATH,
    CHROMA_COLLECTION_NAME,
    OLLAMA_EMBED_MODEL,
    RETRIEVAL_TOP_K,
)
from src.models import RetrievedChunk



from src.utils import get_ollama_client

def get_collection() -> chromadb.Collection:
    """
    Get the ChromaDB collection for AURA Mars documents.

    Returns
    -------
    chromadb.Collection
        The document collection.

    Raises
    ------
    ValueError
        If the collection does not exist (no documents ingested yet).
    """
    client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    try:
        return client.get_collection(
            name=CHROMA_COLLECTION_NAME,
        )
    except Exception as e:
        raise ValueError(
            f"Collection '{CHROMA_COLLECTION_NAME}' not found: {e}. "
            "Run the ingestion pipeline first: python -m src.ingest"
        )


def _embed_query(question: str) -> List[float]:
    """Embed a query string using Ollama."""
    client = get_ollama_client()
    try:
        response = client.embed(model=OLLAMA_EMBED_MODEL, input=question)
        return response["embeddings"][0]
    except Exception as e:
        raise RuntimeError(f"Ollama embedding failed: {e}. Is Ollama running?")


def retrieve(
    question: str,
    top_k: int = RETRIEVAL_TOP_K,
) -> List[RetrievedChunk]:
    """
    Retrieve the most relevant document chunks for a given question.

    Parameters
    ----------
    question : str
        The user's natural-language question.
    top_k : int
        Number of chunks to retrieve.

    Returns
    -------
    List[RetrievedChunk]
        Chunks ranked by relevance, with similarity distances.
    """
    try:
        collection = get_collection()
        query_embedding = _embed_query(question)

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances", "embeddings"],
        )

        chunks = []
        if results and results["documents"] and len(results["documents"]) > 0:
            for i in range(len(results["documents"][0])):
                chunk = RetrievedChunk(
                    text=results["documents"][0][i],
                    metadata=results["metadatas"][0][i] if results["metadatas"] else {},
                    distance=results["distances"][0][i] if results["distances"] else 1.0,
                    embedding=results["embeddings"][0][i] if results.get("embeddings") else None
                )
                chunks.append(chunk)

        return chunks
    except Exception as e:
        print(f"Error during retrieval: {e}")
        return []


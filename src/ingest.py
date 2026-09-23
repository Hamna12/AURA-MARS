"""
AURA Mars — Document Ingestion (Phase 1)

Extracts text from PDFs, chunks it, generates embeddings via Ollama,
and stores everything in ChromaDB.

Usage (CLI):
    python -m src.ingest
"""

import os
import json
import hashlib
from pathlib import Path
from typing import List, Dict, Optional

import fitz  # PyMuPDF
import chromadb

from src.config import (
    RAW_PDFS_DIR,
    PROCESSED_DIR,
    CHROMA_DB_PATH,
    CHROMA_COLLECTION_NAME,
    OLLAMA_EMBED_MODEL,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
)
from src.models import Chunk, IngestReport
from src.utils import get_ollama_client



# ---------------------------------------------------------------------------
# Text Extraction
# ---------------------------------------------------------------------------

def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extract all text from a PDF file using PyMuPDF.

    Parameters
    ----------
    pdf_path : str
        Path to the PDF file.

    Returns
    -------
    str
        Concatenated text from all pages.
    """
    doc = fitz.open(pdf_path)
    text_parts = []
    for page in doc:
        text_parts.append(page.get_text())
    doc.close()
    return "\n".join(text_parts)


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------

def chunk_text(
    text: str,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> List[str]:
    """
    Split text into overlapping chunks of approximately `chunk_size` words.

    Uses word-level splitting rather than character-level to better
    approximate token boundaries.

    Parameters
    ----------
    text : str
        The full document text.
    chunk_size : int
        Approximate number of words per chunk.
    overlap : int
        Number of overlapping words between consecutive chunks.

    Returns
    -------
    List[str]
        List of text chunks.
    """
    words = text.split()
    if not words:
        return []

    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        start += chunk_size - overlap

    return chunks


# ---------------------------------------------------------------------------
# Embedding
# ---------------------------------------------------------------------------

def generate_embedding(text: str) -> List[float]:
    """
    Generate an embedding vector for the given text using Ollama.

    Parameters
    ----------
    text : str
        Text to embed.

    Returns
    -------
    List[float]
        Embedding vector.
    """
    try:
        client = get_ollama_client()
        response = client.embed(model=OLLAMA_EMBED_MODEL, input=text)
        return response["embeddings"][0]
    except Exception as e:
        raise RuntimeError(
            f"Failed to generate embedding via local Ollama for text chunk (model: {OLLAMA_EMBED_MODEL}): {e}. "
            "Please make sure Ollama is running and the model is downloaded."
        )



# ---------------------------------------------------------------------------
# Citation Metadata Helpers
# ---------------------------------------------------------------------------

def _derive_title_from_filename(source_name: str) -> str:
    """
    Derive a human-readable title from a PDF filename stem.

    Ingested papers (data/raw_pdfs/*.pdf) do not carry structured citation
    metadata, so this is the safe fallback used when no explicit `title`
    is supplied at ingestion time. It never fabricates information — it
    only reformats the filename that is already the source of truth.
    """
    return source_name.replace("_", " ").replace("-", " ").strip()


# ---------------------------------------------------------------------------
# ChromaDB Storage
# ---------------------------------------------------------------------------

def _get_or_create_collection() -> chromadb.Collection:
    """Get or create the ChromaDB collection for AURA Mars documents."""
    client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    return client.get_or_create_collection(
        name=CHROMA_COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def _chunk_id(source: str, index: int) -> str:
    """Generate a deterministic ID for a chunk based on source and index."""
    raw = f"{source}::chunk_{index}"
    return hashlib.md5(raw.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Ingestion Pipeline
# ---------------------------------------------------------------------------

def ingest_pdf(
    pdf_path: str,
    metadata: Optional[Dict[str, str]] = None,
) -> int:
    """
    Ingest a single PDF: extract → chunk → embed → store in ChromaDB.

    Parameters
    ----------
    pdf_path : str
        Path to the PDF file.
    metadata : dict, optional
        Additional metadata to attach to each chunk (e.g. region_tag, source_type).

    Returns
    -------
    int
        Number of chunks created.
    """
    metadata = metadata or {}
    source_name = Path(pdf_path).stem
    source_type = metadata.get("source_type", "general")
    region_tag = metadata.get("region_tag", "")

    # Optional citation metadata. Never fabricated — falls back to a
    # filename-derived title and empty strings when not supplied.
    title = metadata.get("title") or _derive_title_from_filename(source_name)
    year = metadata.get("year", "")
    authors = metadata.get("authors", "")
    url = metadata.get("url", "")
    pdf_url = metadata.get("pdf_url", "")
    doi = metadata.get("doi", "")

    # Extract text
    text = extract_text_from_pdf(pdf_path)
    if not text.strip():
        return 0

    # Chunk
    chunks = chunk_text(text)
    if not chunks:
        return 0

    # Embed and store
    collection = _get_or_create_collection()
    ids = []
    embeddings = []
    documents = []
    metadatas = []

    for i, chunk_text_content in enumerate(chunks):
        chunk_id = _chunk_id(source_name, i)
        embedding = generate_embedding(chunk_text_content)

        ids.append(chunk_id)
        embeddings.append(embedding)
        documents.append(chunk_text_content)
        metadatas.append({
            "source": source_name,
            "source_type": source_type,
            "region_tag": region_tag,
            "chunk_index": str(i),
            "page": "",  # PyMuPDF concatenates all pages; per-page tracking is a future enhancement
            "title": title,
            "year": year,
            "authors": authors,
            "url": url,
            "pdf_url": pdf_url,
            "doi": doi,
        })

    collection.upsert(
        ids=ids,
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas,
    )

    # Save processed chunks as JSON for inspection
    processed_path = PROCESSED_DIR / f"{source_name}_chunks.json"
    with open(processed_path, "w", encoding="utf-8") as f:
        json.dump(
            [{"id": ids[i], "text": documents[i], "metadata": metadatas[i]}
             for i in range(len(ids))],
            f, indent=2,
        )

    return len(chunks)


def ingest_all(data_dir: str = str(RAW_PDFS_DIR)) -> IngestReport:
    """
    Ingest all PDF files in the given directory.

    Parameters
    ----------
    data_dir : str
        Directory containing PDF files.

    Returns
    -------
    IngestReport
        Summary of the ingestion run.
    """
    report = IngestReport()
    data_path = Path(data_dir)

    if not data_path.exists():
        report.errors.append(f"Directory not found: {data_dir}")
        return report

    pdf_files = list(data_path.glob("*.pdf"))
    if not pdf_files:
        report.errors.append(f"No PDF files found in: {data_dir}")
        return report

    for pdf_file in pdf_files:
        try:
            count = ingest_pdf(str(pdf_file))
            report.files_processed += 1
            report.chunks_created += count
            print(f"  [OK] {pdf_file.name}: {count} chunks")
        except Exception as e:
            report.errors.append(f"{pdf_file.name}: {e}")
            print(f"  [ERR] {pdf_file.name}: {e}")


    return report


# ---------------------------------------------------------------------------
# CLI Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("AURA Mars — Document Ingestion")
    print(f"Source directory: {RAW_PDFS_DIR}")
    print(f"ChromaDB path:   {CHROMA_DB_PATH}")
    print()
    report = ingest_all()
    print()
    print(f"Files processed: {report.files_processed}")
    print(f"Chunks created:  {report.chunks_created}")
    if report.errors:
        print(f"Errors ({len(report.errors)}):")
        for err in report.errors:
            print(f"  - {err}")

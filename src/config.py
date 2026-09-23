"""
AURA Mars — Centralised Configuration

Single source of truth for all tunable parameters.
No magic numbers should appear anywhere else in the codebase.
Override any value via environment variables or a .env file.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# This docstring/README have always described .env as the override
# mechanism, but nothing actually loaded one — os.getenv() only sees
# real process environment variables, never a .env file on disk, unless
# something reads it in first. Without this call, a .env file at the
# project root was silently inert. find_dotenv-style discovery isn't
# needed here: PROJECT_ROOT below is already the authoritative project
# root, so we point load_dotenv() at PROJECT_ROOT/.env directly.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_PDFS_DIR = DATA_DIR / "raw_pdfs"
PROCESSED_DIR = DATA_DIR / "processed"
REGION_METADATA_PATH = DATA_DIR / "region_metadata.json"
CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", str(PROJECT_ROOT / "chroma_db"))

# ---------------------------------------------------------------------------
# Ollama
# ---------------------------------------------------------------------------
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_LLM_MODEL = os.getenv("OLLAMA_LLM_MODEL", "gemma3:4b")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")

# ---------------------------------------------------------------------------
# ChromaDB
# ---------------------------------------------------------------------------
CHROMA_COLLECTION_NAME = os.getenv("CHROMA_COLLECTION_NAME", "aura_mars_docs")

# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------
RETRIEVAL_TOP_K = int(os.getenv("RETRIEVAL_TOP_K", "5"))

# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "400"))      # approximate token count per chunk
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "50"))  # overlap between consecutive chunks

# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------
# N independent runs for consistency scoring. Lowered from 4 -> 2: the
# structured 8-section prompt (see src/prompts.py) produces much longer
# output per run than the original 3-line format, so 4 runs on CPU-only
# Ollama could take 5-7+ minutes per question. 2 runs still gives a valid
# (if less statistically robust) pairwise consistency comparison. Override
# via GENERATION_RUNS env var if you have GPU inference and want more runs.
GENERATION_RUNS = int(os.getenv("GENERATION_RUNS", "2"))

# ---------------------------------------------------------------------------
# Confidence Scoring Weights (Section 6)
# ---------------------------------------------------------------------------

# Evidence Confidence sub-weights (must sum to 1.0)
WEIGHT_SOURCE_AGREEMENT = 0.35
WEIGHT_RETRIEVAL_MATCH = 0.30
WEIGHT_SOURCE_COUNT = 0.20
WEIGHT_SOURCE_QUALITY = 0.15

# Final Fusion weights (must sum to 1.0)
WEIGHT_EVIDENCE = 0.60
WEIGHT_CONSISTENCY = 0.40

# Confidence tier thresholds
CONFIDENCE_HIGH_THRESHOLD = 70    # >= 70% → "High"
CONFIDENCE_MEDIUM_THRESHOLD = 40  # >= 40% → "Medium", below → "Low"

# ---------------------------------------------------------------------------
# Source Quality Scores (by source type)
# ---------------------------------------------------------------------------
SOURCE_QUALITY_MAP = {
    "peer-reviewed": 1.0,
    "nasa-dataset": 1.0,
    "nasa-report": 0.85,
    "preprint": 0.6,
    "general": 0.6,
}

# Maximum sources for normalisation in source count score
SOURCE_COUNT_NORMALISER = 5

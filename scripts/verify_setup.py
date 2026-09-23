"""
AURA Mars — Setup Verification Script (Phase 0)

Verifies that all prerequisites are met:
    1. Python version
    2. All packages importable
    3. Ollama is reachable
    4. Required models are available
    5. ChromaDB initialises correctly
    6. All src modules import cleanly

Usage:
    python scripts/verify_setup.py
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def check_python_version():
    """Check Python 3.10+ is being used."""
    print("1. Python version...", end=" ")
    v = sys.version_info
    if v.major >= 3 and v.minor >= 10:
        print(f"[OK] {v.major}.{v.minor}.{v.micro}")
        return True
    else:
        print(f"[ERR] Python 3.10+ required, found {v.major}.{v.minor}.{v.micro}")
        return False


def check_packages():
    """Check all required packages are importable."""
    print("2. Required packages...", end=" ")
    packages = [
        "streamlit", "chromadb", "pandas", "numpy", "plotly",
        "fitz", "requests", "ollama", "sklearn",
    ]
    missing = []
    for pkg in packages:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)

    if not missing:
        print(f"[OK] All {len(packages)} packages importable")
        return True
    else:
        print(f"[ERR] Missing: {', '.join(missing)}")
        print("  Run: pip install -r requirements.txt")
        return False


def check_ollama():
    """Check Ollama is reachable and required models are pulled."""
    print("3. Ollama connection...", end=" ")
    try:
        import ollama
        from src.config import OLLAMA_HOST, OLLAMA_LLM_MODEL, OLLAMA_EMBED_MODEL

        client = ollama.Client(host=OLLAMA_HOST)
        models = client.list()
        model_names = [m.get("name", m.get("model", "")) for m in models.get("models", [])]

        print(f"[OK] Connected to {OLLAMA_HOST}")

        # Check for required models
        print(f"   Checking for {OLLAMA_LLM_MODEL}...", end=" ")
        if any(OLLAMA_LLM_MODEL in name for name in model_names):
            print("[OK]")
        else:
            print(f"[ERR] Run: ollama pull {OLLAMA_LLM_MODEL}")

        print(f"   Checking for {OLLAMA_EMBED_MODEL}...", end=" ")
        if any(OLLAMA_EMBED_MODEL in name for name in model_names):
            print("[OK]")
        else:
            print(f"[ERR] Run: ollama pull {OLLAMA_EMBED_MODEL}")

        return True
    except Exception as e:
        print(f"[ERR] Could not connect: {e}")
        print("  Make sure Ollama is running: ollama serve")
        return False


def check_chromadb():
    """Check ChromaDB initialises correctly."""
    print("4. ChromaDB...", end=" ")
    try:
        import chromadb
        from src.config import CHROMA_DB_PATH

        client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
        # Try creating a test collection
        client.get_or_create_collection("_setup_test")
        client.delete_collection("_setup_test")
        print(f"[OK] Persistent storage at {CHROMA_DB_PATH}")
        return True
    except Exception as e:
        print(f"[ERR] {e}")
        return False


def check_src_imports():
    """Check all src modules import cleanly."""
    print("5. Source modules...", end=" ")
    modules = [
        "src.config",
        "src.models",
        "src.prompts",
        "src.utils",
        "src.ingest",
        "src.retrieval",
        "src.confidence",
        "src.generation",
        "src.pipeline",
        "src.comparison",
    ]
    errors = []
    for mod in modules:
        try:
            __import__(mod)
        except Exception as e:
            errors.append(f"{mod}: {e}")

    if not errors:
        print(f"[OK] All {len(modules)} modules imported")
        return True
    else:
        print(f"[ERR] {len(errors)} import error(s):")
        for err in errors:
            print(f"  - {err}")
        return False


def check_data_dirs():
    """Check data directories exist."""
    print("6. Data directories...", end=" ")
    from src.config import RAW_PDFS_DIR, PROCESSED_DIR

    dirs = [RAW_PDFS_DIR, PROCESSED_DIR]
    all_ok = True
    for d in dirs:
        if not d.exists():
            print(f"\n   [ERR] Missing: {d}")
            all_ok = False

    if all_ok:
        print("[OK]")
    return all_ok


if __name__ == "__main__":
    print("=" * 50)
    print("AURA Mars -- Setup Verification")
    print("=" * 50)
    print()

    results = [
        check_python_version(),
        check_packages(),
        check_ollama(),
        check_chromadb(),
        check_src_imports(),
        check_data_dirs(),
    ]

    print()
    print("=" * 50)
    passed = sum(results)
    total = len(results)
    if passed == total:
        print(f"[SUCCESS] All {total} checks passed. You're ready to go!")
    else:
        print(f"[WARNING] {passed}/{total} checks passed. Fix the issues above.")
    print("=" * 50)


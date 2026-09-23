"""
AURA Mars — Demo Pipeline Script

Runs a hardcoded question through the full pipeline for quick testing.
Useful for verifying the entire system works end-to-end without the UI.

Usage:
    python scripts/demo_pipeline.py
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.pipeline import run_pipeline
from src.utils import format_confidence_display



def main():
    print("=" * 60)
    print("AURA Mars — Demo Pipeline")
    print("=" * 60)
    print()

    # Default demo question
    question = (
        "What evidence exists for subsurface water ice in Arcadia Planitia, "
        "and how accessible would it be for future missions?"
    )

    # Allow custom question via command line
    if len(sys.argv) > 1:
        question = " ".join(sys.argv[1:])

    print(f"Question: {question}")
    print()
    print("Running pipeline...")
    print("  (This may take 1-2 minutes: retrieval + 4 generation runs + verification)")
    print()

    try:
        result = run_pipeline(question)
    except Exception as e:
        print(f"[ERR] Pipeline failed: {e}")
        print()
        print("Troubleshooting:")
        print("  1. Is Ollama running? -> ollama serve")
        print("  2. Are models pulled? -> ollama pull gemma3:4b && ollama pull nomic-embed-text")
        print("  3. Are documents ingested? -> python scripts/ingest_cli.py --dir data/raw_pdfs/")
        sys.exit(1)

    # Display results
    print("=" * 60)
    print("RESULTS")
    print("=" * 60)
    print()

    print(f"CLAIM:")
    print(f"   {result.claim}")
    print()

    print(f"SOURCES:")
    for src in result.sources:
        print(f"   - {src}")
    print()

    print(f"CONFIDENCE:")
    conf = result.confidence
    print(f"   Final:              {format_confidence_display(conf.final_confidence)} ({conf.label})")
    print(f"   Evidence:           {format_confidence_display(conf.evidence_confidence)}")
    print(f"   Gen. Consistency:   {format_confidence_display(conf.generation_consistency)}")
    print(f"   |-- Source Agreement:   {format_confidence_display(conf.source_agreement)}")
    print(f"   |-- Retrieval Match:    {format_confidence_display(conf.retrieval_match_strength)}")
    print(f"   |-- Source Count:       {format_confidence_display(conf.source_count_score)}")
    print(f"   +-- Source Quality:     {format_confidence_display(conf.source_quality_score)}")
    print()

    if result.score_explanation:
        print(f"EXPLANATION: {result.score_explanation}")
        print()

    print(f"UNKNOWNS:")
    print(f"   {result.unknowns if result.unknowns else 'None identified'}")
    print()

    print(f"VERIFICATION:")
    if result.verification.verified:
        print("   All claims verified against source passages.")
    else:
        print("   [WARNING] Unsupported claims:")
        for claim in result.verification.unsupported_claims:
            print(f"   - {claim}")
    print()

    print(f"RETRIEVED CHUNKS: {len(result.retrieved_chunks)}")
    print(f"GENERATION RUNS:  {len(result.raw_answers)}")
    print()
    print("=" * 60)


if __name__ == "__main__":
    main()

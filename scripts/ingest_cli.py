"""
AURA Mars — Ingestion CLI Wrapper

Command-line interface for ingesting PDF documents.

Usage:
    python scripts/ingest_cli.py --dir data/raw_pdfs/
    python scripts/ingest_cli.py --dir data/raw_pdfs/ --source-type peer-reviewed --region jezero_crater
"""

import sys
import os
import argparse

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.ingest import ingest_all, ingest_pdf


def main():
    parser = argparse.ArgumentParser(
        description="AURA Mars — Ingest PDF documents into the vector database.",
    )
    parser.add_argument(
        "--dir",
        type=str,
        default="data/raw_pdfs/",
        help="Directory containing PDF files to ingest (default: data/raw_pdfs/)",
    )
    parser.add_argument(
        "--file",
        type=str,
        default=None,
        help="Ingest a single PDF file instead of a directory.",
    )
    parser.add_argument(
        "--source-type",
        type=str,
        default="general",
        choices=["peer-reviewed", "nasa-dataset", "nasa-report", "preprint", "general"],
        help="Source type for metadata tagging (default: general)",
    )
    parser.add_argument(
        "--region",
        type=str,
        default="",
        help="Region tag for metadata (e.g. jezero_crater, arcadia_planitia)",
    )

    args = parser.parse_args()

    print("AURA Mars — Document Ingestion")
    print("=" * 40)

    if args.file:
        # Single file mode
        print(f"File:        {args.file}")
        print(f"Source type:  {args.source_type}")
        print(f"Region tag:   {args.region}")
        print()

        metadata = {
            "source_type": args.source_type,
            "region_tag": args.region,
        }
        try:
            count = ingest_pdf(args.file, metadata=metadata)
            print(f"[OK] Ingested {count} chunks from {args.file}")
        except Exception as e:
            print(f"[ERR] Error: {e}")
            sys.exit(1)
    else:
        # Directory mode
        print(f"Directory:   {args.dir}")
        print()

        report = ingest_all(args.dir)
        print()
        print(f"Files processed: {report.files_processed}")
        print(f"Chunks created:  {report.chunks_created}")
        if report.errors:
            print(f"Errors ({len(report.errors)}):")
            for err in report.errors:
                print(f"  - {err}")


if __name__ == "__main__":
    main()

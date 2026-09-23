"""
AURA Mars — Source Metadata Enrichment CLI

Looks up real citation metadata (year, authors, canonical URL, open-access
PDF URL, DOI) for already-ingested papers via the free Semantic Scholar
API, and writes it into the existing ChromaDB collection + the on-disk
data/processed/*_chunks.json dumps.

This is the ONLY part of AURA Mars that calls an external network API —
retrieval, generation, and scoring remain 100% local. Run this once after
ingestion (or re-run any time; it skips sources that already have a URL
unless --force is passed).

Never invents a link: a source is only updated if Semantic Scholar
returns a high-confidence title match (see src/metadata_enrichment.py).
Sources with no confident match are left untouched — the UI already
handles that gracefully ("Source link unavailable in current metadata.").

Usage:
    python scripts/enrich_metadata.py
    python scripts/enrich_metadata.py --limit 5      # test on a few sources first
    python scripts/enrich_metadata.py --force         # re-check sources that already have a URL
"""

import argparse
import json
import sys
import os
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.config import CHROMA_DB_PATH, CHROMA_COLLECTION_NAME, PROCESSED_DIR
from src.ingest import _derive_title_from_filename
from src.metadata_enrichment import enrich_title


def _get_collection():
    import chromadb
    client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    try:
        return client.get_collection(name=CHROMA_COLLECTION_NAME)
    except Exception as e:
        print(f"[ERR] Collection '{CHROMA_COLLECTION_NAME}' not found: {e}")
        print("      Run ingestion first: python scripts/ingest_cli.py --dir data/raw_pdfs/")
        sys.exit(1)


def _group_by_source(collection) -> Dict[str, Dict]:
    """Return {source_name: {"ids": [...], "metadatas": [...]}} for every chunk."""
    all_items = collection.get(include=["metadatas"])
    grouped: Dict[str, Dict] = {}
    for chunk_id, meta in zip(all_items["ids"], all_items["metadatas"]):
        source = meta.get("source", "unknown")
        grouped.setdefault(source, {"ids": [], "metadatas": []})
        grouped[source]["ids"].append(chunk_id)
        grouped[source]["metadatas"].append(meta)
    return grouped


def _update_processed_json(source: str, enriched: Dict[str, str]) -> None:
    """Best-effort sync of the on-disk processed chunk dump, if present."""
    processed_path = PROCESSED_DIR / f"{source}_chunks.json"
    if not processed_path.exists():
        return
    try:
        with open(processed_path, "r", encoding="utf-8") as f:
            records = json.load(f)
        for record in records:
            record.setdefault("metadata", {}).update(enriched)
        with open(processed_path, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2)
    except Exception as e:
        print(f"  [WARN] Could not update {processed_path.name}: {e}")


def main():
    parser = argparse.ArgumentParser(description="Enrich source metadata via Semantic Scholar.")
    parser.add_argument("--limit", type=int, default=None, help="Only process the first N sources (for testing).")
    parser.add_argument("--force", action="store_true", help="Re-check sources that already have a URL.")
    args = parser.parse_args()

    print("AURA Mars — Source Metadata Enrichment")
    print("=" * 50)
    print("This step calls the Semantic Scholar API over the network.")
    print("Retrieval, generation, and scoring are unaffected — they stay local.")
    print("=" * 50)
    print()

    collection = _get_collection()
    grouped = _group_by_source(collection)
    sources = sorted(grouped.keys())
    if args.limit:
        sources = sources[: args.limit]

    matched, skipped, unmatched = 0, 0, 0

    for i, source in enumerate(sources, 1):
        ids: List[str] = grouped[source]["ids"]
        metadatas: List[dict] = grouped[source]["metadatas"]
        existing_url = metadatas[0].get("url", "") if metadatas else ""

        if existing_url and not args.force:
            print(f"[{i}/{len(sources)}] SKIP  (already has URL): {source}")
            skipped += 1
            continue

        query_title = metadatas[0].get("title") or _derive_title_from_filename(source)
        print(f"[{i}/{len(sources)}] Looking up: {query_title[:70]}")

        result = enrich_title(query_title)
        if result is None:
            print(f"           NO CONFIDENT MATCH — leaving metadata unchanged.")
            unmatched += 1
            continue

        updated_metadatas = []
        for meta in metadatas:
            new_meta = dict(meta)
            new_meta.update(result)
            updated_metadatas.append(new_meta)

        collection.update(ids=ids, metadatas=updated_metadatas)
        _update_processed_json(source, result)

        print(f"           MATCHED — url={'yes' if result['url'] else 'no'}, "
              f"pdf_url={'yes' if result['pdf_url'] else 'no'}, year={result['year'] or '?'}")
        matched += 1

    print()
    print("=" * 50)
    print(f"Sources processed: {len(sources)}")
    print(f"  Matched:   {matched}")
    print(f"  Skipped:   {skipped} (already had a URL — use --force to re-check)")
    print(f"  No match:  {unmatched} (left unchanged, no link fabricated)")
    print("=" * 50)


if __name__ == "__main__":
    main()

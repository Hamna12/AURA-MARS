"""
fetch_arxiv.py
Automatically fetches real Mars-related papers from arXiv (free, no API key needed)
and saves them as PDFs into data/raw_pdfs/ so ingest.py can process them.

Usage:
    python fetch_arxiv.py

You can edit SEARCH_QUERIES below to target your chosen candidate regions/topics.
"""

import os
import time
import requests
import xml.etree.ElementTree as ET

# ---- CONFIG ----
OUTPUT_DIR = "data/raw_pdfs"
MAX_RESULTS_PER_QUERY = 10

# Broad coverage across major Mars research areas.
# Add/remove categories as your project scope evolves — you don't need to run
# all of these at once. Comment out sections you don't need yet.
SEARCH_QUERIES = [
    # Terrain, geology & landing sites
    "Mars habitat site selection",
    "Mars terrain safety landing site",
    "Mars surface geology mapping",

    # Water & ice history
    "Mars subsurface water ice",
    "Mars ancient water history geomorphology",

    # Atmosphere & climate
    "Mars atmosphere climate dust storms",
    "Mars weather modeling",

    # Radiation & human health
    "Mars radiation shielding habitat",
    "Mars human health spaceflight radiation",

    # In-situ resource utilization (ISRU)
    "Mars in-situ resource utilization",
    "Mars regolith construction materials",

    # Mission architecture & planning
    "Mars mission human exploration architecture",
    "Mars surface operations mission planning",

    # Robotics & autonomy
    "Mars rover autonomous navigation",
    "Mars robotics human-robot teaming",

    # Communication & autonomy under delay
    "Mars communication delay autonomy",

    # Astrobiology
    "Mars astrobiology habitability",
]

# arXiv category filter — restricts results to Earth & Planetary Astrophysics,
# which cuts out a lot of irrelevant physics/math noise. Remove this filter
# (set to None) if a query returns too few results.
ARXIV_CATEGORY = "astro-ph.EP"

ARXIV_API_URL = "http://export.arxiv.org/api/query"
ATOM_NS = "{http://www.w3.org/2005/Atom}"


def sanitize_filename(title: str) -> str:
    keep = "".join(c if c.isalnum() or c in (" ", "-", "_") else "" for c in title)
    return keep.strip().replace(" ", "_")[:120]


def search_arxiv(query: str, max_results: int = 8, category: str = None):
    search_terms = f"all:{query}"
    if category:
        search_terms = f"({search_terms}) AND cat:{category}"

    params = {
        "search_query": search_terms,
        "start": 0,
        "max_results": max_results,
        "sortBy": "relevance",
        "sortOrder": "descending",
    }
    resp = requests.get(ARXIV_API_URL, params=params, timeout=30)
    resp.raise_for_status()
    root = ET.fromstring(resp.text)

    papers = []
    for entry in root.findall(f"{ATOM_NS}entry"):
        title = entry.find(f"{ATOM_NS}title").text.strip().replace("\n", " ")
        pdf_url = None
        for link in entry.findall(f"{ATOM_NS}link"):
            if link.attrib.get("title") == "pdf":
                pdf_url = link.attrib.get("href")
        if pdf_url:
            papers.append({"title": title, "pdf_url": pdf_url})
    return papers


def download_pdf(url: str, filepath: str):
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    with open(filepath, "wb") as f:
        f.write(resp.content)


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    total_downloaded = 0

    for query in SEARCH_QUERIES:
        print(f"\nSearching arXiv for: '{query}'")
        try:
            papers = search_arxiv(query, MAX_RESULTS_PER_QUERY, category=ARXIV_CATEGORY)
        except Exception as e:
            print(f"  Search failed: {e}")
            continue

        print(f"  Found {len(papers)} candidate papers")

        for paper in papers:
            filename = sanitize_filename(paper["title"]) + ".pdf"
            filepath = os.path.join(OUTPUT_DIR, filename)

            if os.path.exists(filepath):
                print(f"  Skipping (already downloaded): {paper['title'][:70]}")
                continue

            try:
                download_pdf(paper["pdf_url"], filepath)
                print(f"  Downloaded: {paper['title'][:70]}")
                total_downloaded += 1
                time.sleep(1)  # be polite to arXiv's servers
            except Exception as e:
                print(f"  Failed to download '{paper['title'][:50]}': {e}")

    print(f"\nDone. {total_downloaded} new PDFs saved to {OUTPUT_DIR}/")
    print("Next step: run your ingest.py to chunk, embed, and store these in ChromaDB.")


if __name__ == "__main__":
    main()
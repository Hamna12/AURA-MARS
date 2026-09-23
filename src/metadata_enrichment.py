"""
AURA Mars — Source Metadata Enrichment (optional, network-dependent)

Looks up real citation metadata (year, authors, canonical URL, open-access
PDF URL, DOI) for ingested papers.

Two sources, tried in order:
  1. arXiv's own API — the corpus was largely built by src/fetch_arxiv.py,
     which downloads PDFs directly from arXiv's astro-ph.EP category. For
     those papers, arXiv is the authoritative, reliable, unthrottled
     source — no API key, no meaningful rate limiting for our volume.
  2. Semantic Scholar — fallback for papers not on arXiv (broader journal
     coverage). Free, no API key, but aggressively rate-limited on
     unauthenticated traffic, so it's used only when arXiv has no match.

This is intentionally NOT part of the core query pipeline (retrieval /
generation / scoring stay 100% local, per the project's architecture).
It is an opt-in, one-time (or periodically re-run) enrichment step,
triggered explicitly via scripts/enrich_metadata.py.

Never fabricates a link: a lookup is only accepted as a match if the
returned paper's title is a close match (see TITLE_MATCH_THRESHOLD) to
the title we searched for. Anything below that threshold, or any API
failure, results in no metadata — never a best-guess wrong paper.
"""

import time
import xml.etree.ElementTree as ET
from difflib import SequenceMatcher
from typing import Dict, List, Optional

import requests

# ---------------------------------------------------------------------------
# arXiv (primary source for this corpus)
# ---------------------------------------------------------------------------
ARXIV_API_URL = "http://export.arxiv.org/api/query"
ATOM_NS = "{http://www.w3.org/2005/Atom}"
ARXIV_REQUEST_TIMEOUT_SECONDS = 15
ARXIV_MIN_SECONDS_BETWEEN_REQUESTS = 3.0  # arXiv's own recommended throttle

# ---------------------------------------------------------------------------
# Semantic Scholar (fallback for non-arXiv papers)
# ---------------------------------------------------------------------------
SEMANTIC_SCHOLAR_SEARCH_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
SEMANTIC_SCHOLAR_FIELDS = "title,year,authors,externalIds,openAccessPdf,url"
SEMANTIC_SCHOLAR_REQUEST_TIMEOUT_SECONDS = 15
SEMANTIC_SCHOLAR_MIN_SECONDS_BETWEEN_REQUESTS = 3.1

# How closely a returned title must match our query title (0.0-1.0, via
# difflib.SequenceMatcher) to be accepted as a real match. Deliberately
# strict: a wrong-but-plausible match is worse than no link.
TITLE_MATCH_THRESHOLD = 0.82


def _title_similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


def _best_match(title: str, candidates: List[Dict[str, str]]) -> Optional[Dict[str, str]]:
    best, best_score = None, 0.0
    for candidate in candidates:
        score = _title_similarity(title, candidate.get("title", ""))
        if score > best_score:
            best_score, best = score, candidate
    if best is None or best_score < TITLE_MATCH_THRESHOLD:
        return None
    return best


# ---------------------------------------------------------------------------
# arXiv lookup
# ---------------------------------------------------------------------------

def _query_arxiv(search_query: str, max_results: int = 3) -> List[Dict[str, str]]:
    """Query arXiv's Atom API and return parsed candidate entries."""
    try:
        response = requests.get(
            ARXIV_API_URL,
            params={"search_query": search_query, "start": 0, "max_results": max_results},
            timeout=ARXIV_REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        root = ET.fromstring(response.text)
    except Exception as e:
        print(f"  [WARN] arXiv query failed ({search_query[:60]}...): {e}")
        return []

    candidates = []
    for entry in root.findall(f"{ATOM_NS}entry"):
        title_el = entry.find(f"{ATOM_NS}title")
        if title_el is None or not title_el.text:
            continue
        entry_title = title_el.text.strip().replace("\n", " ")

        pdf_url, abs_url = "", ""
        for link in entry.findall(f"{ATOM_NS}link"):
            if link.attrib.get("title") == "pdf":
                pdf_url = link.attrib.get("href", "")
            if link.attrib.get("rel") == "alternate":
                abs_url = link.attrib.get("href", "")

        published_el = entry.find(f"{ATOM_NS}published")
        year = ""
        if published_el is not None and published_el.text:
            year = published_el.text.strip()[:4]

        authors = [
            a.find(f"{ATOM_NS}name").text.strip()
            for a in entry.findall(f"{ATOM_NS}author")
            if a.find(f"{ATOM_NS}name") is not None and a.find(f"{ATOM_NS}name").text
        ]
        authors_str = ", ".join(authors[:6]) + (" et al." if len(authors) > 6 else "")

        candidates.append({
            "title": entry_title,
            "year": year,
            "authors": authors_str,
            "url": abs_url,
            "pdf_url": pdf_url,
            "doi": "",
        })
    return candidates


def search_arxiv(title: str) -> Optional[Dict[str, str]]:
    """
    Look up a paper's metadata by title via arXiv's own API.

    Tries an exact-phrase title search first (high precision, matches
    fetch_arxiv.py's own download method). Falls back to a looser
    all-fields search if the phrase search finds nothing, still gated by
    TITLE_MATCH_THRESHOLD to avoid false positives.
    """
    candidates = _query_arxiv(f'ti:"{title}"', max_results=3)
    if not candidates:
        candidates = _query_arxiv(f"all:{title}", max_results=5)
    return _best_match(title, candidates)


# ---------------------------------------------------------------------------
# Semantic Scholar lookup (fallback)
# ---------------------------------------------------------------------------

def _extract_s2_authors(paper: dict) -> str:
    authors = paper.get("authors") or []
    names = [a.get("name", "") for a in authors if a.get("name")]
    return ", ".join(names[:6]) + (" et al." if len(names) > 6 else "")


def search_semantic_scholar(title: str) -> Optional[Dict[str, str]]:
    """Look up a paper's metadata by title via the Semantic Scholar API."""
    data = None
    for attempt in range(2):  # one retry on rate-limit, then give up gracefully
        try:
            response = requests.get(
                SEMANTIC_SCHOLAR_SEARCH_URL,
                params={"query": title, "fields": SEMANTIC_SCHOLAR_FIELDS, "limit": 3},
                timeout=SEMANTIC_SCHOLAR_REQUEST_TIMEOUT_SECONDS,
            )
            if response.status_code == 429 and attempt == 0:
                print(f"  [WARN] Semantic Scholar rate limited, backing off 20s...")
                time.sleep(20)
                continue
            response.raise_for_status()
            data = response.json()
            break
        except Exception as e:
            print(f"  [WARN] Semantic Scholar lookup failed for '{title[:60]}...': {e}")
            return None

    if data is None:
        return None

    raw_candidates = data.get("data") or []
    candidates = [
        {
            "title": c.get("title", ""),
            "year": str(c.get("year", "") or ""),
            "authors": _extract_s2_authors(c),
            "url": c.get("url", "") or "",
            "pdf_url": (c.get("openAccessPdf") or {}).get("url", "") or "",
            "doi": (c.get("externalIds") or {}).get("DOI", "") or "",
        }
        for c in raw_candidates
    ]
    return _best_match(title, candidates)


# ---------------------------------------------------------------------------
# Combined lookup
# ---------------------------------------------------------------------------

def enrich_title(title: str, throttle: bool = True) -> Optional[Dict[str, str]]:
    """
    Look up a paper's metadata, trying arXiv first (reliable, matches this
    corpus's actual provenance) and falling back to Semantic Scholar for
    papers arXiv doesn't have. Includes built-in request throttling for
    batch use (see scripts/enrich_metadata.py).

    Returns
    -------
    dict or None
        {title, year, authors, url, pdf_url, doi} from whichever source
        found a confident match, else None.
    """
    result = search_arxiv(title)
    if throttle:
        time.sleep(ARXIV_MIN_SECONDS_BETWEEN_REQUESTS)
    if result is not None:
        return result

    result = search_semantic_scholar(title)
    if throttle:
        time.sleep(SEMANTIC_SCHOLAR_MIN_SECONDS_BETWEEN_REQUESTS)
    return result

#!/usr/bin/env python3
"""
Multi-Source Academic Literature Search Bridge
══════════════════════════════════════════════

Calls literature-search skill scripts as subprocesses to query
OpenAlex + CrossRef APIs, then normalises, merges, and deduplicates
results into the unified format consumed by auto-academic-workflow.

Usage (internal, called by search_and_render.py):
    from search_sources import multi_source_search
    papers = multi_source_search(queries=["transformer attention", "attention mechanism"],
                                  limit=15, year_range="2024-2026")

Output format (list of dict):
    {
        "title": str,
        "abstract": str,
        "venue": str,
        "year": int,
        "url": str,
        "authors": [str],
        "externalIds": {"DOI": str},
        "source": "openalex" | "crossref",
        "citationCount": int,
        "peer_reviewed": bool,
    }
"""

import json
import os
import re
import subprocess
import sys
import time


# ── Path resolution ──────────────────────────────────────────────
def _skill_scripts_root():
    """Resolve the literature-search scripts directory."""
    candidates = [
        os.path.join(os.environ.get("USERPROFILE", ""), ".agents", "skills", "literature-search", "scripts"),
        os.path.join(os.environ.get("HOME", ""), ".agents", "skills", "literature-search", "scripts"),
        os.path.join(os.path.dirname(__file__), "..", "..", "..", ".agents", "skills", "literature-search", "scripts"),
    ]
    for p in candidates:
        if p and os.path.isdir(p):
            return p
    raise FileNotFoundError(
        "literature-search skill scripts not found. "
        "Install with: npx skills add lingzhi227/agent-research-skills@literature-search -g -y"
    )


SCRIPTS = _skill_scripts_root()
OA_SCRIPT = os.path.join(SCRIPTS, "search_openalex.py")
CR_SCRIPT = os.path.join(SCRIPTS, "search_crossref.py")


def _run_script(script_path, args, timeout=90):
    """Run a literature-search script and return parsed JSONL lines."""
    cmd = [sys.executable, script_path] + args
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout,
            encoding="utf-8", errors="replace",
        )
    except subprocess.TimeoutExpired:
        print(f"   ⚠ Timeout: {os.path.basename(script_path)}", file=sys.stderr)
        return []
    except FileNotFoundError:
        print(f"   ⚠ Python not found. Is python3 on PATH?", file=sys.stderr)
        return []

    if result.returncode != 0 and result.stderr:
        err = result.stderr.strip()
        if "No results found" in err:
            return []
        print(f"   ⚠ {os.path.basename(script_path)} error: {err[:200]}", file=sys.stderr)

    # Parse JSONL from stdout
    papers = []
    for line in result.stdout.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        try:
            papers.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return papers


# ── Normalisation ─────────────────────────────────────────────────

def _normalize_openalex(paper):
    """OpenAlex JSONL → auto-academic-workflow format."""
    authors = paper.get("authors", [])
    if isinstance(authors, str):
        authors = [a.strip() for a in authors.split(",") if a.strip()]

    doi = paper.get("doi", "")
    if doi.startswith("https://doi.org/"):
        doi = doi[16:]

    url = paper.get("pdf_url") or paper.get("url") or ""
    if url.startswith("https://openalex.org/"):
        url = f"https://doi.org/{doi}" if doi else url

    venue = (paper.get("venue") or paper.get("venue_normalized") or "").strip()
    # DOI-based venue fallback: infer publisher/conference from DOI prefix
    if not venue and doi:
        venue = _doi_to_venue(doi)
    if not venue and url:
        venue = _url_to_venue(url)

    return {
        "title": (paper.get("title") or "").strip(),
        "abstract": (paper.get("abstract") or "").strip(),
        "venue": venue,
        "year": paper.get("year"),
        "url": url,
        "authors": authors,
        "externalIds": {"DOI": doi} if doi else {},
        "source": "openalex",
        "citationCount": paper.get("citationCount", 0),
        "peer_reviewed": paper.get("peer_reviewed", False),
        "arxiv_id": paper.get("arxiv_id", ""),
    }


def _normalize_crossref(paper):
    """CrossRef JSONL → auto-academic-workflow format."""
    authors_str = paper.get("authors", "")
    if isinstance(authors_str, str):
        # CrossRef format: "Family, Given and Family, Given"
        authors = [
            a.strip() for a in authors_str.split(" and ") if a.strip()
        ]
    else:
        authors = authors_str if isinstance(authors_str, list) else []

    doi = paper.get("doi", "")
    url = paper.get("URL") or paper.get("url") or f"https://doi.org/{doi}" if doi else ""

    venue = paper.get("journal") or paper.get("booktitle") or paper.get("container-title") or ""
    # DOI-based venue fallback
    if not venue and doi:
        venue = _doi_to_venue(doi)
    if not venue and url:
        venue = _url_to_venue(url)

    return {
        "title": (paper.get("title") or "").strip(),
        "abstract": (paper.get("abstract") or "").strip(),
        "venue": venue,
        "year": paper.get("year"),
        "url": url,
        "authors": authors,
        "externalIds": {"DOI": doi} if doi else {},
        "source": "crossref",
        "citationCount": paper.get("cited_by", 0) or paper.get("is-referenced-by-count", 0),
        "peer_reviewed": paper.get("type") in ("article", "inproceedings", "incollection"),
        "arxiv_id": "",
    }


# ── DOI/URL → Venue Inference ────────────────────────────────────

# DOI prefix → publisher / conference hint
DOI_VENUE_HINTS = {
    "10.1109/": "IEEE",
    "10.1145/": "ACM",
    "10.18653/v1/": "ACL Anthology",
    "10.1609/": "AAAI",
    "10.1007/": "Springer",
    "10.1016/": "Elsevier",
    "10.3390/": "MDPI",
    "10.48550/": "arXiv",
    "10.20944/": "Preprints.org",
    "10.21203/": "Research Square",
    "10.2139/": "SSRN",
    "10.30574/": "IJSRA",
    "10.54097/": "HSET",
    "10.71443/": "E-Publishing",
    "10.65215/": "Langtaosha",
}

URL_VENUE_HINTS = {
    "arxiv.org": "arXiv (Cornell University)",
    "ieeexplore.ieee.org": "IEEE",
    "dl.acm.org": "ACM",
    "aclanthology.org": "ACL Anthology",
    "proceedings.mlr.press": "PMLR",
    "papers.nips.cc": "NeurIPS",
    "openreview.net": "OpenReview",
    "mdpi.com": "MDPI",
    "sciencedirect.com": "Elsevier",
    "springer.com": "Springer",
    "ssrn.com": "SSRN",
    "preprints.org": "Preprints.org",
    "researchsquare.com": "Research Square",
}


def _doi_to_venue(doi):
    """Infer venue from DOI: first check for specific conference, then publisher."""
    doi_lower = doi.lower()
    # Check for specific conference names embedded in DOI path
    CONF_IN_DOI = {
        "icassp": "ICASSP", "interspeech": "INTERSPEECH",
        "aaai": "AAAI", "ijcai": "IJCAI", "acl": "ACL",
        "emnlp": "EMNLP", "naacl": "NAACL", "eacl": "EACL",
        "coling": "COLING", "neurips": "NeurIPS", "nips": "NeurIPS",
        "icml": "ICML", "iclr": "ICLR", "cvpr": "CVPR", "iccv": "ICCV",
        "icra": "ICRA", "iros": "IROS", "bibm": "BIBM",
        "miccai": "MICCAI", "www": "WWW", "kdd": "KDD",
        "mm ": "ACM Multimedia", "sigir": "SIGIR",
    }
    for slug, label in CONF_IN_DOI.items():
        if slug in doi_lower:
            return label
    # Fallback: publisher-level
    for prefix, label in DOI_VENUE_HINTS.items():
        if doi_lower.startswith(prefix.lower()):
            return label
    return ""


def _url_to_venue(url):
    """Infer venue from URL domain."""
    url_lower = url.lower()
    for domain, label in URL_VENUE_HINTS.items():
        if domain in url_lower:
            return label
    return ""


# ── Merge & Deduplicate ──────────────────────────────────────────

def _paper_key(paper):
    """Generate a canonical dedup key from DOI or normalised title."""
    doi = (paper.get("externalIds") or {}).get("DOI", "")
    if doi and doi.startswith("10."):
        return f"doi:{doi.lower()}"
    title = (paper.get("title") or "").lower().strip()
    # Remove punctuation and extra whitespace
    title = re.sub(r"[^\w\s]", "", title)
    title = re.sub(r"\s+", " ", title).strip()
    return f"title:{title[:120]}"


def _pick_best(kept, candidate):
    """Choose the better paper when merging duplicates."""
    # Prefer OpenAlex (better metadata) over CrossRef
    if kept.get("source") == "openalex":
        return kept
    if candidate.get("source") == "openalex":
        return candidate
    # Prefer the one with more authors / longer abstract
    k_score = len(kept.get("abstract", "")) + len(kept.get("authors", [])) * 10
    c_score = len(candidate.get("abstract", "")) + len(candidate.get("authors", [])) * 10
    return candidate if c_score > k_score else kept


def merge_and_dedup(oa_papers, cr_papers):
    """Merge OpenAlex and CrossRef results, deduplicate by DOI/title."""
    merged = {}
    for raw in oa_papers:
        p = _normalize_openalex(raw)
        key = _paper_key(p)
        if key in merged:
            merged[key] = _pick_best(merged[key], p)
        else:
            merged[key] = p

    for raw in cr_papers:
        p = _normalize_crossref(raw)
        key = _paper_key(p)
        if key in merged:
            merged[key] = _pick_best(merged[key], p)
        else:
            merged[key] = p

    return list(merged.values())


# ── Multi-Source Search ──────────────────────────────────────────

def search_openalex(query, max_results=20, year_range=None, min_citations=0):
    """Query OpenAlex via literature-search script."""
    args = ["--query", query, "--max-results", str(max_results)]
    if year_range:
        args += ["--year-range", year_range]
    if min_citations > 0:
        args += ["--min-citations", str(min_citations)]
    args += ["--sort", "cited_by_count:desc"]
    return _run_script(OA_SCRIPT, args, timeout=90)


def search_crossref(query, rows=10):
    """Query CrossRef via literature-search script."""
    args = ["--query", query, "--rows", str(rows), "--timeout", "30"]
    return _run_script(CR_SCRIPT, args, timeout=60)


def multi_source_search(queries, limit=15, year_range=None, min_citations=0,
                         use_crossref=True):
    """
    Run multi-source search across OpenAlex + CrossRef.

    Args:
        queries: list of search query strings
        limit: max papers to return
        year_range: "YYYY-YYYY" filter
        min_citations: minimum citation count
        use_crossref: also query CrossRef (supplemental)

    Returns:
        list of paper dicts in auto-academic-workflow format
    """
    all_oa, all_cr = [], []

    # Distribute queries across sources
    for q in queries:
        print(f'🔍 OpenAlex: "{q[:60]}..."', file=sys.stderr)
        oa_results = search_openalex(
            q, max_results=max(limit, 30), year_range=year_range,
            min_citations=min_citations,
        )
        all_oa.extend(oa_results)
        print(f"   → {len(oa_results)} results", file=sys.stderr)
        time.sleep(0.3)  # Be polite

    if use_crossref and queries:
        for q in queries[:2]:  # Only query CrossRef with top 2 queries to save time
            print(f'🔍 CrossRef: "{q[:60]}..."', file=sys.stderr)
            cr_results = search_crossref(q, rows=min(limit, 20))
            all_cr.extend(cr_results)
            print(f"   → {len(cr_results)} results", file=sys.stderr)
            time.sleep(0.3)

    papers = merge_and_dedup(all_oa, all_cr)
    print(f"📊 Merged: {len(all_oa)} OA + {len(all_cr)} CR → {len(papers)} unique",
          file=sys.stderr)
    return papers


# ═══════════════════════════════════════════════════════════════════
#  CLI (for standalone testing)
# ═══════════════════════════════════════════════════════════════════

def _cli():
    import argparse
    parser = argparse.ArgumentParser(description="Multi-source academic search")
    parser.add_argument("--query", required=True, help="Search query")
    parser.add_argument("--limit", type=int, default=15, help="Max papers")
    parser.add_argument("--year-range", help="YYYY-YYYY")
    parser.add_argument("--min-citations", type=int, default=0)
    parser.add_argument("--no-crossref", action="store_true", help="Skip CrossRef")
    parser.add_argument("-o", "--output", help="Output JSON file")
    args = parser.parse_args()

    papers = multi_source_search(
        queries=[args.query],
        limit=args.limit,
        year_range=args.year_range,
        min_citations=args.min_citations,
        use_crossref=not args.no_crossref,
    )

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(papers, f, ensure_ascii=False, indent=2)
        print(f"Saved {len(papers)} papers → {args.output}", file=sys.stderr)
    else:
        for p in papers:
            print(json.dumps(p, ensure_ascii=False))

    return papers


if __name__ == "__main__":
    _cli()

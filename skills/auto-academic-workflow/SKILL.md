---
name: auto-academic-workflow
description: |
  Fully automated academic research tool. Searches top conferences/journals via
  multi-source search (OpenAlex + CrossRef, delegated to literature-search skill),
  auto-tags papers by architecture and modality, validates DOIs, estimates compute
  (VRAM), detects GitHub repositories, translates abstracts to Chinese, and renders
  an interactive HTML knowledge graph on the desktop.
  
  Use when the user asks to search for papers by research direction, topic, or
  keywords, especially for:
  (1) "search papers on X", "find literature about Y", "literature review"
  (2) "auto academic workflow", "文献图谱", "文献检索", "文献搜索"
  (3) Any request mentioning paper search, literature graph, academic survey
  with a research direction and time range.
  (4) "顶会文献", "顶刊论文", "学术前沿"

  Features: multi-source search (OpenAlex + CrossRef), accurate architecture/modality
  tagging, compute (VRAM) estimation, GitHub repo detection, DOI validation, Chinese
  paper summaries, semantic paper-to-paper edges in Canvas force graph.

  Dependencies: requires literature-search skill (lingzhi227/agent-research-skills@literature-search)
  for multi-source search. Install with:
    npx skills add lingzhi227/agent-research-skills@literature-search -g -y
---

# Auto Academic Workflow

## Overview

Given a research direction and time range, this skill:
1. Searches **OpenAlex + CrossRef** APIs (via literature-search skill bridge)
2. Auto-tags papers by **architecture** (Mamba/Transformer/GCN/CNN/LLM...) and **modality** (Text/Audio/Video/Physiological)
3. **Validates DOIs** and marks paper links as verified ⚠️ or confirmed ✅
4. Renders an **interactive HTML dashboard** on the Desktop with zero external dependencies

## Quick Start

Call the main script:

```bash
python scripts/search_and_render.py '<json_params>'
```

Where `json_params` is a JSON string:

```json
{
  "research_direction": "Multimodal Depression Detection",
  "time_range": "2024-2026",
  "keywords": "mamba transformer",
  "limit": 15
}
```

### Parameters

| Parameter | Required | Description | Example |
|-----------|:--------:|-------------|---------|
| `research_direction` | ✅ | Core research topic | `"Multimodal Depression Detection"` |
| `time_range` | ✅ | Year range | `"2024-2026"`, `"2024-"`, `"最近两年"` |
| `keywords` | ❌ | Extra technical terms, space-separated | `"mamba ssm gcn"` |
| `limit` | ❌ | Number of papers (default 15, max 30) | `15` |
| `mode` | ❌ | `"new"` (replace all) or `"append"` (add to existing) | `"append"` |

### Mode: Append (增量添加)

Set `"mode": "append"` to add new papers to the existing collection without
losing previously searched papers. Papers are deduplicated by title.

```json
{"research_direction":"depression mamba","time_range":"2024-2026","mode":"append","limit":10}
```

The cache is saved to `~/Desktop/literature_papers.json`.

## Workflow

### Step 1: Build Queries
Combines `research_direction` + each `keyword` into multiple search queries for broader coverage.

### Step 2: Search
Fetches papers from **Semantic Scholar API** (real published papers with validated metadata).
Includes 3 retries with exponential backoff for rate limits.

### Step 3: Filter & Rank
- Papers are deduplicated by title
- Sorted by venue prestige (CCF-A > CCF-B > other) then by year (newest first)
- Top venues recognized: CVPR, NeurIPS, ICML, ACL, Information Fusion, IEEE TAC, ICASSP, etc.

### Step 4: Auto-Tag & Enrich
Each paper is automatically enriched:
- **Architecture**: Mamba/SSM, Transformer, GCN, CNN, LSTM/RNN, Diffusion, LLM, MLP, Unspecified
  - Uses precise detection rules: `"mamba"`, `"selective scan"` → Mamba/SSM; `"transformer"`, `"self-attention"` → Transformer
  - Generic `"attention"` alone does NOT trigger Transformer — avoids false positives
- **Modality**: Text, Audio, Video, Physiological, Unspecified
- **Venue rank**: 🏆 CCF-A/Top, ⭐ CCF-B, 📄 Other
- **DOI validity**: ✅ (starts with `10.`) or ⚠️ (unverified)
- **Compute estimate**: VRAM/GPU recommendation per architecture
- **GitHub repo**: Detected from abstract or URL (shows link or "暂无")
- **Chinese summary**: Auto-generated from title, authors, venue, architecture, and modality tags

### Step 5: Render Dashboard
Outputs a single self-contained HTML file to `~/Desktop/Literature_Graph.html` with:

- **🌐 Graph View**: Pure Canvas force-directed physics engine
  - Drag nodes to reposition
  - Hover for floating tooltip with paper details
  - Click to open detail panel
  - Double-click to open paper URL
  - Scroll to zoom in/out
- **📋 Table View**: Sortable paper list with all metadata
- **🔍 Filters**: Search by title/author/keyword, filter by architecture, modality, venue rank
- **📝 Detail Panel**: Full abstract, authors, venue, DOI status, paper links
- **Zero dependencies**: No CDN, no external JS — works on any network

## Architecture Detection

The script detects these architectures from title + abstract keywords:

| Architecture | Detection Keywords |
|-------------|-------------------|
| Mamba/SSM | mamba, state space model, ssm, selective scan |
| Transformer | transformer, attention, bert, vit |
| GCN | graph, gcn, gat, graph neural |
| CNN | cnn, convolutional, resnet |
| LSTM/RNN | lstm, rnn, gru, recurrent |
| Diffusion | diffusion, ddpm |
| LLM | llm, large language model, gpt, pretrained language |

## DOI Validation

DOIs are validated from Semantic Scholar's `externalIds.DOI` field:
- ✅ **Verified**: DOI exists and starts with `10.` (standard DOI format) — clickable link to doi.org
- ⚠️ **Unverified**: DOI missing or malformed

⚠️ **Important**: Only papers with verified DOIs are guaranteed to have matching content.
The Semantic Scholar API returns real published paper metadata, ensuring DOI accuracy.

## Compute Requirements

Estimated VRAM/GPU based on detected architecture:

| Architecture | VRAM Estimate | Recommended GPU |
|-------------|---------------|-----------------|
| Mamba/SSM | 24GB | RTX 4090 |
| Transformer | 12-24GB | RTX 4080/4090 |
| GCN | 8-12GB | RTX 3070/4070 |
| CNN | 8-16GB | RTX 3070/4080 |
| LSTM/RNN | 4-8GB | RTX 3060+ |
| Diffusion | 16-24GB | RTX 4090 |
| LLM | 24-80GB | A100 (多卡) |
| MLP | 4-8GB | RTX 3060+ |
| Unspecified | 8-16GB | RTX 3070+ |

## GitHub Repository Detection

Checks paper abstract and metadata for:
- Explicit `github.com/...` URLs
- "Code is available at", "open source", "released at"
- If found, displays the link; otherwise shows "暂无"

## Venue Ranking

See `references/venues.md` for the full venue ranking list used for sorting and filtering.

## Output

Single HTML file at the user's Desktop:
```
~/Desktop/Literature_Graph.html
```

Open with any modern browser — no internet connection required after generation.

## Limitations

- OpenAlex text search coverage may be incomplete for very niche topics
- Architecture/modality detection is keyword-based and may miss novel approaches
- Max 30 new papers per run (append can accumulate up to 60)

## Delete & Save

- **🗑️ Delete**: Click the delete button in the detail panel or table view to remove unwanted papers
- **💾 Save Changes**: After deleting, click the green Save button to download updated JSON
- Replace `~/Desktop/literature_papers.json` with the downloaded file, then re-run the skill with `mode: "new"` to reload

## Data Source

Uses **multi-source search** via the `literature-search` skill bridge (`search_sources.py`):
- **OpenAlex** (primary): broadest coverage, free, no API key — via `literature-search/scripts/search_openalex.py`
- **CrossRef** (supplemental): DOI-based lookup, BibTeX support — via `literature-search/scripts/search_crossref.py`

All returned papers have verified DOIs (`10.xxx` format). Papers without valid DOIs are automatically excluded.
Results from both sources are merged and deduplicated by DOI/title.

### Search Pipeline

```
search_and_render.py  →  search_sources.py  →  literature-search skill
     (main)               (bridge)              ├─ search_openalex.py
                                                └─ search_crossref.py
```

## Quick Reference

```bash
# New search (15 papers)
python scripts/search_and_render.py '{"research_direction":"multimodal depression detection","time_range":"2024-2026","limit":15,"mode":"new"}'

# Append (add 10 more)
python scripts/search_and_render.py '{"research_direction":"depression mamba","time_range":"2024-2026","limit":10,"mode":"append"}'

# Reload from cache (after deleting papers)
python scripts/search_and_render.py '{"mode":"reload","time_range":"2024-2026"}'
```

## Files

| File | Location |
|------|----------|
| HTML Graph | `~/Desktop/Literature_Graph.html` |
| Paper Cache | `~/Desktop/literature_papers.json` |

## Architecture

```
scripts/
├── search_and_render.py   # Main engine: orchestrate search → enrich → render
├── search_sources.py      # Multi-source search bridge (calls literature-search scripts)
references/
└── venues.md              # Venue ranking reference

external:
  ~/.agents/skills/literature-search/scripts/
  ├── search_openalex.py   # OpenAlex API search
  ├── search_crossref.py   # CrossRef API search + BibTeX
  └── download_arxiv_source.py  # arXiv source download (optional)
```

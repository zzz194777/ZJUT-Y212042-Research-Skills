"""
Auto Academic Workflow — Core Engine v5
Multi-source search via literature-search skill (OpenAlex + CrossRef),
auto-tags papers, renders Canvas dashboard.
Supports delete & incremental add via persistent JSON cache.
"""

import sys, json, os, time, ssl, datetime
import urllib.request, urllib.parse

# Multi-source search bridge (delegates to literature-search skill scripts)
from search_sources import multi_source_search


USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

# ═══════════════════════════════════════════════════════════════
#  CCF-Aware Venue Ranking (stars + CCF tier)
#  👑 5★ = CCF-A 会议/期刊  |  🏆 4★ = CCF-B  |  ⭐ 3★ = CCF-C / TOP SCI Q1
#  📄 2★ = SCI / EI indexed    |  📝 1★ = arXiv / unverified
# ═══════════════════════════════════════════════════════════════

VENUE_RANK = {
    # ═══ CCF-A 会议 (5★) ═══
    "cvpr": 5, "iccv": 5, "eccv": 5,  # 计算机视觉
    "neurips": 5, "nips": 5, "icml": 5, "iclr": 5, "colt": 5,  # 机器学习
    "aaai": 5, "ijcai": 5,  # 人工智能
    "acl": 5,  # 自然语言处理
    "sigir": 5, "www": 5, "kdd": 5,  # 数据挖掘/信息检索
    "acm multimedia": 5, "acm mm": 5, "mm ": 5,  # 多媒体
    "sigmod": 5, "vldb": 5,  # 数据库
    "siggraph": 5,  # 图形学
    "osdi": 5, "sosp": 5,  # 系统
    "ieee symposium on security": 5, "ccs": 5,  # 安全
    "mobicom": 5, "sigcomm": 5,  # 网络

    # ═══ CCF-A 期刊 (5★) ═══
    "ieee transactions on pattern analysis": 5,  # TPAMI
    "ieee t-pami": 5, "tpami": 5,
    "international journal of computer vision": 5,  # IJCV
    "ijcv": 5,
    "journal of machine learning research": 5,  # JMLR
    "jmlr": 5,
    "artificial intelligence": 5,  # AI Journal
    "acm computing surveys": 5,
    "ieee transactions on information theory": 5,

    # ═══ CCF-B 会议 (4★) ═══
    "emnlp": 4, "naacl": 4, "coling": 4, "eacl": 4,  # NLP
    "aistats": 4, "uai": 4,  # ML
    "aamas": 4,  # Multi-agent
    "ecai": 4, "kr": 4,  # AI
    "icra": 4, "iros": 4,  # Robotics
    "icassp": 4,  # Signal processing
    "interspeech": 4,  # Speech
    "bibm": 4,  # Bioinformatics
    "miccai": 4,  # Medical imaging
    "iswc": 4, "ubicomp": 4,  # Ubiquitous
    "wsdm": 4, "cikm": 4,  # Data mining
    "icdm": 4,  # Data mining

    # ═══ CCF-B 期刊 (4★) ═══
    "ieee transactions on affective computing": 4,
    "taffc": 4,
    "ieee transactions on multimedia": 4,
    "ieee t-mm": 4, "tmm": 4,
    "ieee transactions on knowledge and data engineering": 4,  # TKDE
    "ieee tkde": 4, "tkde": 4,
    "ieee transactions on neural networks": 4,  # TNNLS
    "tnnls": 4,
    "machine learning": 4,  # ML Journal
    "neural networks": 4,  # Neural Networks journal
    "pattern recognition": 4,
    "transactions of the association for computational linguistics": 4,  # TACL
    "tacl": 4,
    "ieee transactions on image processing": 4,
    "ieee transactions on signal processing": 4,
    "neurocomputing": 4,
    "knowledge-based systems": 4,
    "information sciences": 4,
    "expert systems with applications": 4,
    "journal of biomedical and health informatics": 4,
    "jbhi": 4,
    "engineering applications of artificial intelligence": 4,

    # ═══ CCF-C 会议/期刊 (3★) ═══
    "acii": 3, "affective computing and intelligent interaction": 3,
    "icmi": 3, "international conference on multimodal interaction": 3,
    "eacl": 3,  # also CCF-C in some years
    "acml": 3, "iconip": 3,
    "cognitive computation": 3,
    "journal of affective disorders": 3,
    "biomedical signal processing and control": 3,
    "computers in biology and medicine": 3,
    "artificial intelligence in medicine": 3,
    "cognitive systems research": 3,
    "applied soft computing": 3,
    "soft computing": 3,
    "ieee access": 3,

    # ═══ SCI Q1 非 CCF 顶刊 (3★) ═══
    "information fusion": 3,
    "ieee journal of biomedical and health informatics": 3,
    "medical image analysis": 3,
    "ieee transactions on medical imaging": 3,

    # ═══ 其他 SCI/EI (2★) ═══
    "scientific reports": 2,
    "frontiers in": 2,
    "plos one": 2,
    "sensors": 2,
    "applied sciences": 2,
    "electronics": 2,
    "ieice transactions": 2,
    "springer": 2,

    # ═══ Publisher-level fallback (when specific venue unknown) ═══
    "acl anthology": 3, "aclanthology": 3,
    "ieee": 2, "acm": 2, "elsevier": 2, "springer": 2, "mdpi": 2,

    # ═══ 知名预印本 (2★) ═══
    "arxiv": 2,
    "ssrn": 2,
    "preprints.org": 1,
    "research square": 1,
    "researchgate": 1,
    "techrxiv": 1,
    "biorxiv": 1,
    "medrxiv": 1,

    # ═══ Other volume/publisher fallbacks ═══
    "ijsra": 1, "hset": 1, "langtaosha": 1, "e-publishing": 1,
}

ARCH_COLORS = {
    "Mamba/SSM": "#e74c3c", "Transformer": "#f39c12", "GCN": "#9b59b6",
    "CNN": "#2ecc71", "LSTM/RNN": "#1abc9c", "Diffusion": "#e67e22",
    "LLM": "#3498db", "Other": "#95a5a6",
}

MODALITY_ICONS = {"Text":"📝","Audio":"🎙️","Video":"🎬","Physiological":"🧠","Multimodal":"🔀","Unspecified":"❓"}
STAR_ICONS = {5:"👑", 4:"🏆", 3:"⭐", 2:"📄", 1:"📝"}
CCF_LABELS = {5:"CCF-A", 4:"CCF-B", 3:"CCF-C / SCI Q1", 2:"SCI/EI", 1:"未评级"}

# CCF tier override: some venues have special tier
_CCF_TIER = {5:"A", 4:"B", 3:"C", 2:"", 1:""}


def venue_rank(v):
    """Return venue star rating (1-5) based on CCF tier + SCI level."""
    if not v: return 1
    lv = v.lower()
    best = 1
    for k, s in VENUE_RANK.items():
        if k in lv and s > best:
            best = s
    return best


def venue_ccf(v):
    """Return CCF tier label ('A', 'B', 'C', '') for a venue."""
    if not v: return ""
    lv = v.lower()
    best_star = 1
    for k, s in VENUE_RANK.items():
        if k in lv and s > best_star:
            best_star = s
    return _CCF_TIER.get(best_star, "") if best_star >= 3 else ""


# ── Note: inline search functions removed ──
# Multi-source search now delegated to search_sources.py
# which calls literature-search skill scripts (OpenAlex + CrossRef).


def build_queries(direction, keywords_str):
    """Build search queries: one precise (quoted) + one broad."""
    queries = []
    # Precise: quote the entire direction
    queries.append(direction)
    # Broad: direction without quotes, plus keywords
    if keywords_str:
        queries.append(f"{direction} {keywords_str}")
    else:
        queries.append(f"{direction} neural network")
    return queries


def auto_tag(paper):
    """Accurate architecture/modality tagging with confidence scoring."""
    title = (paper.get("title") or "").lower()
    abstract = (paper.get("abstract") or "").lower()
    text = f"{title} {abstract}"

    # ── Architecture detection with stronger signals ──
    archs = []
    # Mamba: require explicit mention (not just "state space" which could be generic)
    if any(kw in text for kw in ("mamba", "selective scan", "structured state space")):
        archs.append("Mamba/SSM")
    # Transformer: require "transformer" explicitly or BERT/ViT model names
    if any(kw in text for kw in ("transformer", "self-attention", "multi-head attention",
        "bert ", "roberta", "vit ", "vision transformer", "swin transformer")):
        archs.append("Transformer")
    # GCN: require "graph" + "network" or "convolution"
    if any(kw in text for kw in ("graph convolution", "graph neural", "gcn", "gat ",
        "graph attention network", "graph-based")):
        archs.append("GCN")
    # CNN: explicit CNN or specific CNN architectures
    if any(kw in text for kw in ("cnn ", "convolutional neural", "resnet", "resnet-",
        "vgg", "densenet", "efficientnet", "inception")):
        archs.append("CNN")
    # LSTM/RNN
    if any(kw in text for kw in ("lstm", "bilstm", "bi-lstm", "gru ", "rnn ",
        "recurrent neural", "sequential model")):
        archs.append("LSTM/RNN")
    # Diffusion
    if any(kw in text for kw in ("diffusion model", "denoising diffusion", "ddpm", "stable diffusion")):
        archs.append("Diffusion")
    # LLM
    if any(kw in text for kw in ("llm", "large language model", "gpt-", "llama",
        "chatgpt", "pretrained language model", "foundation model")):
        archs.append("LLM")

    # More conservative: don't tag Transformer just because of generic "attention"
    if not archs:
        if any(kw in text for kw in ("mlp", "linear layer", "feedforward", "fully connected")):
            archs.append("MLP")
        else:
            archs.append("Unspecified")

    # ── Modality detection ──
    modals = []
    if any(kw in text for kw in ("text", "transcript", "linguistic", "nlp ",
        "language model", "dialogue", "conversation", "interview transcript", "questionnaire")):
        modals.append("Text")
    if any(kw in text for kw in ("audio", "speech", "acoustic", "voice", "vocal",
        "mel-spectrogram", "prosodic", "mfcc")):
        modals.append("Audio")
    if any(kw in text for kw in ("video", "visual", "facial", "face",
        "facial expression", "frame-level", "image")):
        modals.append("Video")
    if any(kw in text for kw in ("eeg", "fmri", "brain signal", "physiological",
        "ecg", "ppg", "heart rate", "gsr", "electrodermal")):
        modals.append("Physiological")
    if not modals:
        modals.append("Unspecified")

    return {
        "architectures": archs,
        "modalities": modals,
        "venue_stars": venue_rank(paper.get("venue", "")),
        "venue_ccf": venue_ccf(paper.get("venue", "")),
        "year": paper.get("year"),
    }


def estimate_compute(archs):
    """Estimate VRAM / GPU requirements based on architecture."""
    if not archs or archs == ["Unspecified"]:
        return "8-16GB VRAM (RTX 3070+)"
    primary = archs[0]
    estimates = {
        "Mamba/SSM": "24GB VRAM (RTX 4090)",
        "Transformer": "12-24GB VRAM (RTX 4080/4090)",
        "GCN": "8-12GB VRAM (RTX 3070/4070)",
        "CNN": "8-16GB VRAM (RTX 3070/4080)",
        "LSTM/RNN": "4-8GB VRAM (RTX 3060+)",
        "Diffusion": "16-24GB VRAM (RTX 4090)",
        "LLM": "24-80GB VRAM (A100 40G/80G, 多卡)",
        "MLP": "4-8GB VRAM (RTX 3060+)",
    }
    return estimates.get(primary, "8-16GB VRAM (RTX 3070+)")


def detect_github(paper, timeout=5):
    """Multi-strategy GitHub repository detection.

    Strategy order:
      1. Scan abstract/title for github.com URLs (instant)
      2. Check paper landing page for github links (with timeout)
      3. For arXiv papers, check arXiv abstract page

    Returns (url, method) tuple: ("https://github.com/...", "abstract"|"landing"|"arxiv"|"")
    """
    import re
    abstract = (paper.get("abstract") or "")
    title = (paper.get("title") or "")

    # ── Strategy 1: Scan text for github.com ──
    text = f"{title} {abstract}"
    gh_match = re.search(r'github\.com/[\w.\-]+/[\w.\-]+', text, re.IGNORECASE)
    if gh_match:
        repo = gh_match.group(0).rstrip(".),;'\"")
        return (f"https://{repo}", "abstract")

    # "Code available at" pattern
    code_match = re.search(r'code\s+(?:is\s+)?available\s+at\s+(https?://[^\s,.)]+)', text, re.IGNORECASE)
    if code_match:
        return (code_match.group(1).rstrip(".),;"), "abstract")

    # ── Strategy 2: Fetch paper landing page ──
    url = paper.get("url", "")
    if not url:
        doi = (paper.get("externalIds") or {}).get("DOI", "")
        if doi and doi.startswith("10."):
            url = f"https://doi.org/{doi}"
    if url:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            ctx = ssl.create_default_context()
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
                page = resp.read().decode("utf-8", errors="replace")[:50000]
            gh_find = re.findall(r'github\.com/[\w.\-]+/[\w.\-]+', page, re.IGNORECASE)
            if gh_find:
                # Pick the most likely repo (not a fork indicator)
                for repo in gh_find:
                    repo_clean = repo.rstrip("/').,;\"")
                    if repo_clean.count("/") >= 2:  # github.com/user/repo
                        return (f"https://{repo_clean}", "landing")
                return (f"https://{gh_find[0]}", "landing")
        except Exception:
            pass

    # ── Strategy 3: arXiv page for papers with arxiv_id ──
    arxiv_id = paper.get("arxiv_id", "")
    if not arxiv_id:
        # Try to extract from URL
        if url and "arxiv.org" in url:
            m = re.search(r'arxiv\.org/(?:abs|pdf)/([\d.]+)', url)
            if m:
                arxiv_id = m.group(1)
    if arxiv_id:
        try:
            abs_url = f"https://arxiv.org/abs/{arxiv_id}"
            req = urllib.request.Request(abs_url, headers={"User-Agent": USER_AGENT})
            ctx = ssl.create_default_context()
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
                page = resp.read().decode("utf-8", errors="replace")[:50000]
            gh_find = re.findall(r'github\.com/[\w.\-]+/[\w.\-]+', page, re.IGNORECASE)
            if gh_find:
                for repo in gh_find:
                    repo_clean = repo.rstrip("/').,;\"")
                    if repo_clean.count("/") >= 2:
                        return (f"https://{repo_clean}", "arxiv")
                return (f"https://{gh_find[0]}", "arxiv")
        except Exception:
            pass

    return ("", "")


def generate_cn_abstract(paper, tags):
    """Generate a Chinese summary from structured metadata.

    Attempts machine translation via deep_translator; gracefully falls
    back to a structured Chinese template if the library is unavailable.
    """
    title = paper.get("title") or ""
    venue = paper.get("venue") or ""
    year = paper.get("year") or ""
    arch_str = "、".join(tags["architectures"]) if tags["architectures"] else "深度学习"
    modal_str = "+".join(tags["modalities"]) if tags["modalities"] else "多模态"
    authors = paper.get("authors") or []
    author_str = "、".join(authors[:3])
    if len(authors) > 3:
        author_str += " 等"

    en_abstract = (paper.get("abstract") or "").strip()
    cn_abstract = ""
    if en_abstract and len(en_abstract) > 30:
        try:
            from deep_translator import GoogleTranslator
            snippet = en_abstract[:1200]
            cn_abstract = GoogleTranslator(source='auto', target='zh-CN').translate(snippet)
        except Exception:
            cn_abstract = _structured_cn_summary(title, arch_str, modal_str, en_abstract)
    elif en_abstract:
        cn_abstract = _structured_cn_summary(title, arch_str, modal_str, en_abstract)

    parts = [
        f"📌 论文标题: {title}",
    ]
    if author_str:
        parts.append(f"✍️ 作者: {author_str}")
    if venue:
        parts.append(f"📍 发表: {venue} ({year})" if year else f"📍 发表: {venue}")
    parts.append(f"🧠 核心架构: {arch_str}")
    parts.append(f"🎭 涉及模态: {modal_str}")
    if cn_abstract:
        parts.append(f"\n🇨🇳 中文摘要:\n{cn_abstract}")
    else:
        parts.append(f"\n📄 英文摘要: {en_abstract[:300]}...")
    return "\n".join(parts)


def _structured_cn_summary(title, arch_str, modal_str, en_abstract):
    """Generate a structured Chinese summary from paper metadata."""
    first_sentence = en_abstract.split(".")[0][:200].strip() if en_abstract else ""
    return (
        f"本文提出了基于{arch_str}的方法，融合{modal_str}模态信息。"
        f"{first_sentence}" if first_sentence else ""
    )


# ═══════════════════════════════════════════════════════════════
#  RENDER: Pure Canvas Dashboard (zero dependencies)
# ═══════════════════════════════════════════════════════════════

def render_dashboard(papers, direction, out_path):
    """Render interactive dashboard with all metadata."""
    papers_data = []
    for i, p in enumerate(papers):
        tags = auto_tag(p)
        star = tags["venue_stars"]
        color = ARCH_COLORS.get(tags["architectures"][0], "#95a5a6") if tags["architectures"] else "#95a5a6"
        tf = p["title"] or "Untitled"
        doi = (p.get("externalIds") or {}).get("DOI", "")
        url = p.get("url", "")
        doi_valid = bool(doi and doi.startswith("10."))
        url_valid = bool(url and url.startswith("http"))
        gh_url, gh_method = detect_github(p)
        compute = estimate_compute(tags["architectures"])
        cn_abstract = generate_cn_abstract(p, tags)
        ccf_tier = tags.get("venue_ccf", "")
        ccf_label = f"CCF-{ccf_tier}" if ccf_tier else ""
        papers_data.append({
            "id": i + 1, "title_full": tf,
            "title_short": tf if len(tf) <= 48 else tf[:45] + "…",
            "abs_full": p.get("abstract") or "No abstract.",
            "cn_abstract": cn_abstract,
            "venue": p.get("venue") or "Publication venue unknown",
            "year": p.get("year"),
            "authors": ", ".join((p.get("authors") or [])[:5]),
            "archs": tags["architectures"], "modals": tags["modalities"],
            "stars": star, "color": color,
            "doi": doi, "url": url,
            "doi_valid": doi_valid, "url_valid": url_valid,
            "github": gh_url, "gh_method": gh_method,
            "compute": compute,
            "source": p.get("source", "openalex"),
            "citationCount": p.get("citationCount", 0),
            "ccf_tier": ccf_tier, "ccf_label": ccf_label,
        })

    total = len(papers_data)
    years = sorted(set(int(p["year"] or 0) for p in papers_data if p["year"]), reverse=True)
    all_archs = sorted(set(a for p in papers_data for a in p["archs"]))
    all_modals = sorted(set(m for p in papers_data for m in p["modals"]))
    top_count = sum(1 for p in papers_data if p["stars"]>=2)
    arch_opts = "".join(f'<option value="{a}">{a}</option>' for a in all_archs)
    modal_opts = "".join(f'<option value="{m}">{m}</option>' for m in all_modals)
    papers_json = json.dumps(papers_data, ensure_ascii=False)

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>📚 Literature Graph — {direction}</title>
<style>
:root{{--bg:#0d1117;--card:#161b22;--border:#30363d;--text:#c9d1d9;--muted:#8b949e;--accent:#58a6ff;--gold:#f1c40f;--red:#e74c3c;--orange:#f39c12}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:var(--bg);color:var(--text);height:100vh;overflow:hidden;display:flex;flex-direction:column}}
::-webkit-scrollbar{{width:6px}}::-webkit-scrollbar-track{{background:var(--bg)}}::-webkit-scrollbar-thumb{{background:var(--border);border-radius:3px}}

#toolbar{{background:var(--card);border-bottom:1px solid var(--border);padding:10px 20px;display:flex;align-items:center;gap:12px;flex-shrink:0;z-index:100;flex-wrap:wrap}}
#toolbar h1{{font-size:18px;font-weight:700;white-space:nowrap}}
#toolbar h1 span{{color:var(--gold)}}
#toolbar .stats{{display:flex;gap:12px;font-size:13px;color:var(--muted)}}
#toolbar .stats b{{color:var(--accent)}}
#toolbar input{{background:var(--bg);border:1px solid var(--border);border-radius:6px;padding:6px 12px;color:var(--text);font-size:13px;width:200px;outline:none}}
#toolbar input:focus{{border-color:var(--accent)}}
#toolbar select{{background:var(--bg);border:1px solid var(--border);border-radius:6px;padding:6px 10px;color:var(--text);font-size:13px;outline:none;cursor:pointer}}
#toolbar button{{background:var(--border);border:none;color:var(--text);padding:6px 14px;border-radius:6px;font-size:13px;cursor:pointer;white-space:nowrap}}
#toolbar button:hover{{background:#484f58}}
#toolbar button.active{{background:var(--accent);color:#fff}}

#main{{display:flex;flex:1;overflow:hidden}}
#graph-panel{{flex:1;position:relative;min-width:0}}
#graph-panel canvas{{display:block;width:100%;height:100%;cursor:grab}}
#graph-panel canvas:active{{cursor:grabbing}}
#side-panel{{width:0;background:var(--card);border-left:1px solid var(--border);overflow-y:auto;transition:width .3s;flex-shrink:0}}
#side-panel.open{{width:420px}}
#side-panel .inner{{padding:20px;display:none}}
#side-panel.open .inner{{display:block}}
#side-panel h3{{font-size:17px;margin-bottom:12px;color:var(--gold);line-height:1.4}}
#side-panel .meta{{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:14px}}
#side-panel .tag{{padding:3px 10px;border-radius:20px;font-size:12px;font-weight:600}}
#side-panel .tag.arch{{background:rgba(88,166,255,.15);color:#58a6ff}}
#side-panel .tag.modal{{background:rgba(46,204,113,.15);color:#2ecc71}}
#side-panel .tag.venue{{background:rgba(241,196,15,.15);color:#f1c40f}}
#side-panel p{{font-size:13px;line-height:1.7;color:var(--muted);margin-bottom:10px}}
#side-panel .abstract-box{{background:var(--bg);border-radius:8px;padding:14px;margin:14px 0;font-size:13px;line-height:1.7;border-left:3px solid var(--accent)}}
#side-panel .links{{display:flex;gap:10px;margin-top:16px}}
#side-panel .links a,.links button{{display:inline-block;padding:8px 18px;border-radius:6px;font-size:13px;text-decoration:none;cursor:pointer;background:var(--accent);color:#fff;border:none}}
#side-panel .links a:hover,.links button:hover{{opacity:.85}}
#side-panel .links .secondary{{background:var(--border)}}

#table-panel{{display:none;flex:1;overflow-y:auto;padding:0}}
#table-panel.show{{display:block}}
#table-panel table{{width:100%;border-collapse:collapse;font-size:13px}}
#table-panel th{{position:sticky;top:0;background:var(--card);text-align:left;padding:12px 16px;border-bottom:2px solid var(--border);color:var(--muted);font-weight:600;z-index:10}}
#table-panel td{{padding:10px 16px;border-bottom:1px solid var(--border);vertical-align:top}}
#table-panel tr{{cursor:pointer;transition:background .15s}}
#table-panel tr:hover{{background:rgba(88,166,255,.06)}}
#table-panel .t-title{{font-weight:600;color:var(--text);margin-bottom:3px}}
#table-panel .t-venue{{font-size:12px;color:var(--muted)}}
#table-panel .t-arch{{font-size:11px}}
#table-panel .star-cell{{font-size:14px;white-space:nowrap}}

.tooltip{{position:fixed;pointer-events:none;background:var(--card);border:1px solid var(--border);border-radius:8px;padding:10px 14px;max-width:350px;font-size:13px;z-index:999;display:none;box-shadow:0 4px 20px rgba(0,0,0,.5);line-height:1.5}}
.tooltip b{{color:var(--gold)}}
.tooltip .tt-meta{{color:var(--muted);font-size:12px;margin-top:4px}}
.fps{{position:absolute;bottom:8px;right:8px;color:var(--muted);font-size:11px;pointer-events:none}}
</style>
</head>
<body>

<div id="toolbar">
  <h1>📚 <span>{direction}</span></h1>
  <div class="stats">
    <span>📄 <b>{total}</b> 篇</span>
    <span>🏆 顶会/顶刊 <b>{top_count}</b></span>
    <span>📅 {years[0] if years else '?'}{'−'+str(years[-1]) if len(years)>1 else ''}</span>
  </div>
  <input type="text" id="search-input" placeholder="🔍 搜索论文/作者/关键词…" oninput="applyFilter()">
  <select id="arch-filter" onchange="applyFilter()">
    <option value="">🏗️ 全部架构</option>
    {arch_opts}
  </select>
  <select id="modal-filter" onchange="applyFilter()">
    <option value="">🎭 全部模态</option>
    {modal_opts}
  </select>
  <select id="star-filter" onchange="applyFilter()">
    <option value="">🏅 全部等级</option>
    <option value="5">👑 TAFFC/IF/ACM MM/CVPR (SCI Q1, CCF-A/B)</option>
    <option value="4">🏆 T-MM/JBHI/ACL/AAAI/NeurIPS (SCI Q1, CCF-A)</option>
    <option value="3">⭐ ACII/ICMI/BIBM/ICASSP (CCF-B/C)</option>
    <option value="2">📄 普通 SCI 期刊</option>
    <option value="1">📝 预印本/其他</option>
  </select>
  <button id="btn-graph" class="active" onclick="switchView('graph')">🌐 图谱</button>
  <button id="btn-table" onclick="switchView('table')">📋 表格</button>
  <button id="btn-save" onclick="saveChanges()" style="background:#2ecc71;color:#000" title="删除论文后，点击此处下载更新后的JSON">💾 保存更改</button>
  <span id="del-count" style="font-size:12px;color:var(--red);display:none"></span>
</div>

<div id="main">
  <div id="graph-panel">
    <canvas id="gc"></canvas>
    <div class="fps" id="fps-label"></div>
    <div class="legend" style="position:absolute;bottom:32px;left:12px;color:var(--muted);font-size:11px;pointer-events:none;line-height:1.8">
      <div><span style="display:inline-block;width:20px;height:3px;vertical-align:middle;margin-right:6px;background:#e74c3c;border-radius:2px"></span>同架构 (Mamba/Transformer…)</div>
      <div><span style="display:inline-block;width:20px;height:3px;vertical-align:middle;margin-right:6px;background:#f1c40f;border-radius:2px"></span>同期刊/会议</div>
      <div><span style="display:inline-block;width:20px;height:2px;vertical-align:middle;margin-right:6px;background:#2ecc71;border-radius:2px;border-top:2px dashed #2ecc71"></span>同模态</div>
    </div>
  </div>
  <div id="side-panel"><div class="inner" id="side-content"></div></div>
  <div id="table-panel">
    <table><thead><tr><th>#</th><th>标题</th><th>渠道</th><th>CCF</th><th>架构</th><th>模态</th><th>算力</th><th>GitHub</th><th>等级</th><th>年</th><th></th></tr></thead>
    <tbody id="table-body"></tbody></table>
  </div>
</div>
<div class="tooltip" id="tooltip"></div>

<script>
// ═══════════════════════════════════════════════════════
//  Pure Canvas Force-Directed Graph Engine
// ═══════════════════════════════════════════════════════
const PAPERS = {papers_json};
const CENTER = {{x:0,y:0}};
let nodes=[], edges=[], ctx, canvas, W, H, hovered=null, selected=null;
let dragging=null, dragStart={{x:0,y:0}};
let paused=false, showFPS=false;

const REPULSION=25000, ATTRACTION=0.0015, CENTERING_FORCE=0.001, DAMPING=0.82, MAX_VEL=3;
const NODE_R=18, CENTER_R=28, FONT_SIZE=12;
const ARCH_COLORS={json.dumps(ARCH_COLORS, ensure_ascii=False)};

function hexToRGBA(h,a){{let r=parseInt(h.slice(1,3),16),g=parseInt(h.slice(3,5),16),b=parseInt(h.slice(5,7),16);return`rgba(${{r}},${{g}},${{b}},${{a}})`;}}

function buildGraph() {{
  nodes = [{{id:0,x:0,y:0,vx:0,vy:0,radius:CENTER_R,color:'#f1c40f',label:'{direction[:30]}',visible:true,stars:3,isCenter:true}}];
  edges = [];
  let paperNodes = [];

  // Create paper nodes
  PAPERS.forEach((p,i)=>{{
    let angle = (i/PAPERS.length)*Math.PI*2 + 0.5;
    let dist = 320 + i*15 + Math.random()*60;
    let node = {{
      id:p.id, x:Math.cos(angle)*dist, y:Math.sin(angle)*dist, vx:0, vy:0,
      radius:NODE_R, color:p.color, label:p.title_short, visible:true,
      stars:p.stars, paper:p, _origIdx:i
    }};
    nodes.push(node);
    paperNodes.push(node);
  }});

  // Build semantic edges between papers
  for (let i=0;i<paperNodes.length;i++) {{
    for (let j=i+1;j<paperNodes.length;j++) {{
      let a=paperNodes[i].paper, b=paperNodes[j].paper;
      let score=0, sharedArch=null, sharedVenue=false, sharedYear=false;

      // Architecture match
      for (let arch of a.archs) {{
        if (b.archs.includes(arch)) {{ score+=3; sharedArch=arch; break; }}
      }}
      // Modality match
      let modalMatch=0;
      for (let m of a.modals) {{ if (b.modals.includes(m)) modalMatch++; }}
      score+=modalMatch;
      // Same venue
      if (a.venue&&b.venue&&a.venue===b.venue) {{ score+=2; sharedVenue=true; }}
      // Same year
      if (a.year&&b.year&&a.year===b.year) {{ score+=1; sharedYear=true; }}

      if (score>=2) {{
        // Edge color: arch shared=architecture color, venue shared=gold, modal shared=green
        let eColor=sharedArch?ARCH_COLORS[sharedArch]||'#58a6ff':(sharedVenue?'#f1c40f':'#2ecc71');
        let eWidth=Math.min(score*0.6,4);
        edges.push({{
          from:a.id, to:b.id, visible:true,
          color:eColor, width:eWidth, score:score,
          sharedArch:sharedArch, sharedVenue:sharedVenue
        }});
      }}
    }}
  }}

  // Limit edges per node: keep top 4 strongest
  let nodeEdges={{}};
  edges.forEach(e=>{{
    if(!nodeEdges[e.from]) nodeEdges[e.from]=[];
    if(!nodeEdges[e.to]) nodeEdges[e.to]=[];
    nodeEdges[e.from].push(e);
    nodeEdges[e.to].push(e);
  }});
  let filtered=[];
  edges.forEach(e=>{{
    let fromCnt=nodeEdges[e.from]?nodeEdges[e.from].filter(function(x){{return filtered.indexOf(x)>=0||x===e}}).length:0;
    let toCnt=nodeEdges[e.to]?nodeEdges[e.to].filter(function(x){{return filtered.indexOf(x)>=0||x===e}}).length:0;
    if (fromCnt<4&&toCnt<4) filtered.push(e);
  }});
  edges=filtered;
}}

function initCanvas() {{
  canvas = document.getElementById('gc');
  ctx = canvas.getContext('2d');
  onResize();
  buildGraph();
  CENTER.x=W/2; CENTER.y=H/2;
  // Place center node
  nodes[0].x=CENTER.x; nodes[0].y=CENTER.y;
  requestAnimationFrame(loop);
}}

function onResize() {{
  let panel = document.getElementById('graph-panel');
  let r = panel.getBoundingClientRect();
  W = r.width; H = r.height;
  canvas.width = W * (window.devicePixelRatio||1);
  canvas.height = H * (window.devicePixelRatio||1);
  canvas.style.width = W+'px'; canvas.style.height = H+'px';
  ctx.setTransform((window.devicePixelRatio||1),0,0,(window.devicePixelRatio||1),0,0);
  if (nodes.length>0) {{ CENTER.x=W/2; CENTER.y=H/2; nodes[0].x=CENTER.x; nodes[0].y=CENTER.y; }}
}}

function starIcon(n) {{ return ['','📝','📄','⭐','🏆','👑'][n] || '📝'; }}

// ═══ Physics ═══
let lastTime=0, frameCount=0, fpsTime=0;
function loop(ts) {{
  if (!paused) simulate();
  draw();
  // FPS
  frameCount++;
  if (ts-fpsTime>1000) {{ document.getElementById('fps-label').textContent = frameCount+' fps'; frameCount=0; fpsTime=ts; }}
  requestAnimationFrame(loop);
}}

function simulate() {{
  let visible = nodes.filter(n=>n.visible);
  let vEdges = edges.filter(e=>e.visible);
  // Repulsion
  for (let i=0;i<visible.length;i++) for (let j=i+1;j<visible.length;j++) {{
    let a=visible[i],b=visible[j];
    let dx=a.x-b.x, dy=a.y-b.y;
    let d=Math.sqrt(dx*dx+dy*dy)+0.01;
    let force=REPULSION/(d*d);
    let fx=(dx/d)*force, fy=(dy/d)*force;
    a.vx+=fx; a.vy+=fy; b.vx-=fx; b.vy-=fy;
  }}
  // Attraction along edges
  for (let e of vEdges) {{
    let s=nodes.find(n=>n.id===e.from), t=nodes.find(n=>n.id===e.to);
    if (!s||!t||!s.visible||!t.visible) continue;
    let dx=t.x-s.x, dy=t.y-s.y, d=Math.sqrt(dx*dx+dy*dy)+0.01;
    let force=ATTRACTION*d;
    s.vx+=dx*force; s.vy+=dy*force;
    t.vx-=dx*force; t.vy-=dy*force;
  }}
  // Center node gravity + paper node centering
  for (let n of visible) {{
    if (n.id===0) {{
      n.vx+=(CENTER.x-n.x)*CENTERING_FORCE*3;
      n.vy+=(CENTER.y-n.y)*CENTERING_FORCE*3;
    }} else {{
      n.vx+=(CENTER.x-n.x)*CENTERING_FORCE;
      n.vy+=(CENTER.y-n.y)*CENTERING_FORCE;
    }}
    // Damping
    n.vx*=DAMPING; n.vy*=DAMPING;
    if (Math.abs(n.vx)<0.01) n.vx=0;
    if (Math.abs(n.vy)<0.01) n.vy=0;
    // Max velocity
    let spd=Math.sqrt(n.vx*n.vx+n.vy*n.vy);
    if (spd>MAX_VEL) {{ n.vx=(n.vx/spd)*MAX_VEL; n.vy=(n.vy/spd)*MAX_VEL; }}
    // Apply
    n.x+=n.vx; n.y+=n.vy;
    // Bounds
    n.x=Math.max(NODE_R,Math.min(W-NODE_R,n.x));
    n.y=Math.max(NODE_R,Math.min(H-NODE_R,n.y));
  }}
}}

// ═══ Drawing ═══
function draw() {{
  ctx.clearRect(0,0,W,H);

  // Edges (semantic connections between papers)
  edges.forEach(e=>{{
    if (!e.visible) return;
    let s=nodes.find(n=>n.id===e.from), t=nodes.find(n=>n.id===e.to);
    if (!s||!t||!s.visible||!t.visible) return;
    let edgeColor = e.color||'#58a6ff';
    let edgeW = e.width||1.5;
    // Draw curved edge for same-architecture pairs, straight for others
    if (e.sharedArch) {{
      let mx=(s.x+t.x)/2, my=(s.y+t.y)/2;
      let dx=t.x-s.x, dy=t.y-s.y, len=Math.sqrt(dx*dx+dy*dy);
      let perpX=-dy/len*20, perpY=dx/len*20;
      ctx.beginPath(); ctx.moveTo(s.x,s.y);
      ctx.quadraticCurveTo(mx+perpX, my+perpY, t.x, t.y);
      ctx.strokeStyle=hexToRGBA(edgeColor,0.5); ctx.lineWidth=edgeW; ctx.stroke();
    }} else {{
      ctx.beginPath(); ctx.moveTo(s.x,s.y); ctx.lineTo(t.x,t.y);
      ctx.strokeStyle=hexToRGBA(edgeColor,0.3); ctx.lineWidth=edgeW; ctx.stroke();
    }}
    // Dash for modality-only connections
    if (!e.sharedArch&&!e.sharedVenue) {{
      ctx.setLineDash([4,4]);
      ctx.beginPath(); ctx.moveTo(s.x,s.y); ctx.lineTo(t.x,t.y);
      ctx.strokeStyle=hexToRGBA(edgeColor,0.25); ctx.lineWidth=1; ctx.stroke();
      ctx.setLineDash([]);
    }}
  }});

  // Nodes (paper nodes first, center on top)
  let paperNodes = nodes.filter(n=>n.id!==0&&n.visible);
  paperNodes.forEach(n=>drawNode(n));
  // Center node
  let cn = nodes.find(n=>n.id===0);
  if (cn&&cn.visible) {{
    ctx.beginPath(); ctx.arc(cn.x,cn.y,cn.radius,0,Math.PI*2);
    ctx.fillStyle=cn.color; ctx.fill();
    ctx.strokeStyle='#fff'; ctx.lineWidth=2; ctx.stroke();
    ctx.fillStyle='#fff'; ctx.font='bold 14px sans-serif'; ctx.textAlign='center';
    ctx.fillText(cn.label,cn.x,cn.y-32);
  }}
}}

function drawNode(n) {{
  let isHover = (hovered===n), isSel = (selected===n);
  let r = n.radius + (isHover||isSel?4:0);

  // Glow for selected
  if (isSel) {{
    ctx.beginPath(); ctx.arc(n.x,n.y,r+6,0,Math.PI*2);
    ctx.fillStyle=hexToRGBA(n.color,0.25); ctx.fill();
  }}

  // Main circle
  ctx.beginPath(); ctx.arc(n.x,n.y,r,0,Math.PI*2);
  let grad = ctx.createRadialGradient(n.x-3,n.y-4,0,n.x,n.y,r);
  grad.addColorStop(0,'white'); grad.addColorStop(0.15,n.color); grad.addColorStop(1,hexToRGBA(n.color,0.6));
  ctx.fillStyle=grad; ctx.fill();

  // Border for stars
  if (n.stars>=5) {{ ctx.strokeStyle='#f1c40f'; ctx.lineWidth=4; ctx.stroke(); }}
  else if (n.stars>=4) {{ ctx.strokeStyle='#f1c40f'; ctx.lineWidth=3; ctx.stroke(); }}
  else if (n.stars>=3) {{ ctx.strokeStyle='#ccc'; ctx.lineWidth=2; ctx.stroke(); }}

  // Icon inside
  ctx.fillStyle='#fff'; ctx.font='11px sans-serif'; ctx.textAlign='center'; ctx.textBaseline='middle';
  let icons={{5:'👑',4:'🏆',3:'⭐',2:'📄',1:'📝'}};
  ctx.fillText(icons[n.stars]||'', n.x, n.y);

  // Label below
  ctx.fillStyle='var(--muted)' in document.documentElement.style?'#8b949e':'#aaa';
  ctx.font='10px sans-serif'; ctx.textAlign='center';
  let lbl = n.label;
  if (lbl.length>28) lbl = lbl.slice(0,26)+'…';
  ctx.fillText(lbl, n.x, n.y+n.radius+14);
}}

// ═══ Mouse Interaction ═══
function getNodeAt(mx,my) {{
  for (let n of nodes) {{
    if (!n.visible) continue;
    let dx=mx-n.x, dy=my-n.y;
    if (dx*dx+dy*dy < (n.radius+8)*(n.radius+8)) return n;
  }}
  return null;
}}

function initEvents() {{
  canvas = document.getElementById('gc');
  canvas.addEventListener('mousemove', function(e) {{
  let r=canvas.getBoundingClientRect();
  let mx=e.clientX-r.left, my=e.clientY-r.top;
  let n = getNodeAt(mx,my);
  let tt = document.getElementById('tooltip');
  let pp = document.getElementById('graph-panel');

  if (dragging) {{
    dragging.x=mx; dragging.y=my;
    canvas.style.cursor='grabbing'; tt.style.display='none';
    return;
  }}

  if (n && n.id!==0) {{
    canvas.style.cursor='pointer';
    if (hovered!==n) {{ hovered=n; }}
    tt.style.display='block';
    tt.style.left=(e.clientX+16)+'px'; tt.style.top=(e.clientY-10)+'px';
    let ccfColorMap = {{A:'#e74c3c',B:'#f39c12',C:'#3498db'}};
    let ccfTag = n.paper.ccf_tier ? '<span style="background:'+ccfColorMap[n.paper.ccf_tier]+';color:#fff;font-size:10px;padding:1px 4px;border-radius:3px;margin-left:4px">CCF-'+n.paper.ccf_tier+'</span>' : '';
    let ghTag = n.paper.github ? '<br>🔗 GitHub: <a href="'+n.paper.github+'" target="_blank" style="color:#2ecc71">'+n.paper.github.replace('https://github.com/','.../').substring(0,25)+'</a>' : '<br>🔗 GitHub: 暂无';
    tt.innerHTML='<b>'+n.paper.title_full+'</b><div class="tt-meta">📍 '+n.paper.venue+' ('+(n.paper.year||'?')+') '+starIcon(n.stars)+ccfTag+'<br>🏗️ '+n.paper.archs.join(', ')+'<br>🎭 '+n.paper.modals.join(', ')+'<br>'+(n.paper.doi_valid?'📎 DOI ✅':'')+(n.paper.url_valid?' 🔗 URL ✅':'')+ghTag+'</div>';
  }} else {{
    canvas.style.cursor = n && n.id===0 ? 'pointer' : 'default';
    hovered=null;
    tt.style.display='none';
  }}
}});

canvas.addEventListener('mousedown', function(e) {{
  let r=canvas.getBoundingClientRect();
  let mx=e.clientX-r.left, my=e.clientY-r.top;
  let n = getNodeAt(mx,my);
  if (n) {{
    dragging=n;
    dragStart={{x:n.x-mx, y:n.y-my}};
    if (n.id!==0) showDetail(n.paper);
  }}
}});

window.addEventListener('mouseup', function() {{
  if (dragging) {{ dragging.vx=0; dragging.vy=0; }}
  dragging=null;
  canvas.style.cursor='default';
}});

canvas.addEventListener('dblclick', function(e) {{
  let r=canvas.getBoundingClientRect();
  let n=getNodeAt(e.clientX-r.left, e.clientY-r.top);
  if (n&&n.id!==0&&n.paper.url) window.open(n.paper.url,'_blank');
}});

canvas.addEventListener('wheel', function(e) {{
  e.preventDefault();
  // Simple scroll to nudge all nodes toward/away from center
  let factor = e.deltaY>0 ? 1.05 : 0.95;
  nodes.forEach(n=>{{
    if (n.id===0||!n.visible) return;
    n.x=CENTER.x+(n.x-CENTER.x)*factor;
    n.y=CENTER.y+(n.y-CENTER.y)*factor;
  }});
}}, {{passive:false}});
}}

// ═══ Detail Panel ═══
function showDetail(paper) {{
  let panel=document.getElementById('side-panel');
  let content=document.getElementById('side-content');
  selected=nodes.find(n=>n.paper===paper)||null;
  _currentPaperId = paper.id;
  panel.classList.add('open');
  content.innerHTML=`
    <h3>${{paper.title_full}}</h3>
    <div class="meta">
      <span class="tag venue">📍 ${{paper.venue}}${{paper.year?' ('+paper.year+')':''}} ${{starIcon(paper.stars)}}</span>
      ${{paper.archs.map(a=>'<span class="tag arch">🏗️ '+a+'</span>').join('')}}
      ${{paper.modals.map(m=>'<span class="tag modal">🎭 '+m+'</span>').join('')}}
    </div>
    <p><b>✍️ 作者:</b> ${{paper.authors}}</p>
    <p><b>💻 算力需求:</b> ${{paper.compute}}</p>
    ${{paper.ccf_tier?'<p><b>🏅 CCF分区:</b> <span style="background:'+['','#e74c3c','#f39c12','#3498db'][{{'A':1,'B':2,'C':3}}.get(paper.ccf_tier,0)]+';color:#fff;padding:2px 8px;border-radius:4px;font-weight:bold">CCF-'+paper.ccf_tier+'</span></p>':''}}
    <p><b>🔗 GitHub:</b> ${{paper.github?'<a href="'+paper.github+'" target="_blank" style="color:#58a6ff">'+(paper.gh_method?'['+paper.gh_method+'] ':'')+paper.github.replace('https://github.com/','')+'</a>':'暂无'}}</p>
    <div class="abstract-box"><b>🇨🇳 中文简介</b><br><br>${{paper.cn_abstract.split('\\n').map(function(l){{return '<p style="margin:4px 0;font-size:13px">'+l+'</p>'}}).join('')}}</div>
    <div class="abstract-box" style="border-left-color:#f39c12"><b>📄 英文摘要</b><br><br>${{paper.abs_full}}</div>
    <div class="links">
      ${{paper.url_valid?'<a href="'+paper.url+'" target="_blank">🔗 原文链接 ✅</a>':(paper.url?'<a href="'+paper.url+'" target="_blank" class="secondary">🔗 原文链接 ⚠️</a>':'')}}
      ${{paper.doi_valid?'<a href="https://doi.org/'+paper.doi+'" target="_blank" class="secondary">📎 DOI ✅</a>':(paper.doi?'<span class="tag" style="background:rgba(231,76,60,0.15);color:#e74c3c;font-size:12px">📎 DOI未验证</span>':'')}}
      <button onclick="document.getElementById(\'side-panel\').classList.remove(\'open\');selected=null">✕ 关闭</button>
      <button onclick="deleteCurrentPaper()" style="background:#e74c3c">🗑️ 删除此论文</button>
    </div>
  `;
}}

// ═══ Filtering ═══
function applyFilter() {{
  let q = (document.getElementById('search-input').value||'').toLowerCase();
  let arch = document.getElementById('arch-filter').value;
  let modal = document.getElementById('modal-filter').value;
  let star = parseInt(document.getElementById('star-filter').value)||0;

  nodes.forEach(n=>{{
    if (n.id===0) {{ n.visible=true; return; }}
    let p=n.paper;
    let ok=true;
    if (q && !p.title_full.toLowerCase().includes(q) && !p.authors.toLowerCase().includes(q) && !p.venue.toLowerCase().includes(q) && !p.abs_full.toLowerCase().includes(q)) ok=false;
    if (arch && !p.archs.includes(arch)) ok=false;
    if (modal && !p.modals.includes(modal)) ok=false;
    if (star && p.stars!==star) ok=false;
    n.visible=ok;
  }});
  edges.forEach(e=>{{
    let t=nodes.find(n=>n.id===e.to);
    e.visible = t ? t.visible : true;
  }});
}}

// ═══ Table View ═══
function populateTable() {{
  let q = (document.getElementById('search-input').value||'').toLowerCase();
  let arch = document.getElementById('arch-filter').value;
  let modal = document.getElementById('modal-filter').value;
  let star = parseInt(document.getElementById('star-filter').value)||0;
  let filtered=PAPERS.filter(p=>{{
    if (q && !p.title_full.toLowerCase().includes(q) && !p.authors.toLowerCase().includes(q) && !p.venue.toLowerCase().includes(q) && !p.abs_full.toLowerCase().includes(q)) return false;
    if (arch && !p.archs.includes(arch)) return false;
    if (modal && !p.modals.includes(modal)) return false;
    if (star && p.stars!==star) return false;
    return true;
  }});
  let tbody=document.getElementById('table-body');
  tbody.innerHTML=filtered.map((p,i)=>`
    <tr onclick="showDetail(PAPERS.find(function(x){{return x.id===${{p.id}}}}))" style="${{i%2?'background:rgba(255,255,255,0.02)':''}}">
      <td>${{i+1}}</td>
      <td><div class="t-title">${{p.title_full}}</div><div class="t-venue">${{p.authors}}</div></td>
      <td><div class="t-venue">${{p.venue}}${{p.year?' ('+p.year+')':''}}</div></td>
      <td>${{p.ccf_tier?'<span style="background:'+(p.ccf_tier==='A'?'#e74c3c':p.ccf_tier==='B'?'#f39c12':'#3498db')+';color:#fff;padding:1px 5px;border-radius:3px;font-size:11px;font-weight:bold">CCF-'+p.ccf_tier+'</span>':'<span style="color:#888;font-size:11px">—</span>'}}</td>
      <td>${{p.archs.map(a=>'<span style="color:'+(ARCH_COLORS[a]||'#888')+'">●</span> '+a).join('<br>')}}</td>
      <td>${{p.modals.join(', ')}}</td>
      <td style="font-size:11px;color:var(--muted)">${{p.compute}}</td>
      <td>${{p.github?'<a href="'+p.github+'" target="_blank" style="color:#2ecc71" title="'+p.gh_method+'检出">✅</a>':'<span style="color:#888">—</span>'}}</td>
      <td class="star-cell">${{starIcon(p.stars)}}</td>
      <td>${{p.year||'?'}}</td>
      <td><button onclick="event.stopPropagation();deletePaperById(${{p.id}})" style="background:none;border:none;cursor:pointer;font-size:16px" title="删除">🗑️</button></td>
    </tr>
  `).join('');
}}

// ═══ View Switch ═══
function switchView(view) {{
  let gp=document.getElementById('graph-panel'), tp=document.getElementById('table-panel');
  if (view==='graph') {{
    gp.style.display=''; tp.classList.remove('show');
    document.getElementById('btn-graph').classList.add('active');
    document.getElementById('btn-table').classList.remove('active');
    onResize();
  }} else {{
    gp.style.display='none'; tp.classList.add('show');
    document.getElementById('btn-table').classList.add('active');
    document.getElementById('btn-graph').classList.remove('active');
    populateTable();
  }}
}}

// ═══ Delete & Save ═══
let deletedIds = [];
let _currentPaperId = null;

function deleteCurrentPaper() {{
  if (!_currentPaperId) return;
  deletePaperById(_currentPaperId);
  document.getElementById('side-panel').classList.remove('open');
  _currentPaperId = null;
}}

function deletePaperById(pid) {{
  if (deletedIds.includes(pid)) return;
  deletedIds.push(pid);
  nodes.forEach(n => {{ if (n.id === pid) {{ n.visible = false; }} }});
  edges.forEach(e => {{ if (e.from === pid || e.to === pid) {{ e.visible = false; }} }});
  updateDelCount();
}}

function updateDelCount() {{
  let el = document.getElementById('del-count');
  if (deletedIds.length > 0) {{
    el.style.display = 'inline';
    el.textContent = '已删除: ' + deletedIds.length + ' 篇';
  }} else {{
    el.style.display = 'none';
  }}
}}

function saveChanges() {{
  let remaining = PAPERS.filter(p => !deletedIds.includes(p.id));
  if (remaining.length === PAPERS.length) {{
    alert('没有删除任何论文。');
    return;
  }}
  // Save both the updated cache and deleted IDs for reload
  let output = {{ papers: remaining, deleted_ids: deletedIds }};
  let json = JSON.stringify(output, null, 2);
  let blob = new Blob([json], {{type:'application/json'}});
  let a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'literature_papers.json';
  a.click();
  URL.revokeObjectURL(a.href);
  let delList = PAPERS.filter(p=>deletedIds.includes(p.id)).map(p=>p.id+': '+p.title_short).join('\\n');
  alert('已下载 JSON 文件。请告诉我:\\n"刷新图谱并删除这些论文：[\\n'+delList+'\\n]"');
}}

// ═══ Init ═══
window.addEventListener('DOMContentLoaded', ()=>{{
  initCanvas();
  initEvents();
  window.addEventListener('resize', onResize);
}});
</script>
</body>
</html>'''

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    return True


# ═══════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════

def main():
    try:
        params = json.loads(sys.argv[1])
    except (IndexError, json.JSONDecodeError) as e:
        print(json.dumps({"status":"error","message":f"Invalid JSON: {e}"}))
        sys.exit(1)

    direction = params.get("research_direction", "Multimodal Depression Detection")
    time_range = params.get("time_range", "2024-2026")
    keywords = params.get("keywords", "")
    mode = params.get("mode", "new")  # "new", "append", or "reload"
    delete_ids = params.get("delete_ids", [])  # paper IDs to remove on reload
    limit = min(int(params.get("limit", 15)), 30)

    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    cache_path = os.path.join(desktop, "literature_papers.json")

    # ── reload mode: just load cache and re-render ──
    if mode == "reload":
        if not os.path.exists(cache_path):
            # Check for the new format cache file
            cache_path2 = os.path.join(desktop, "literature_papers.json")
            if not os.path.exists(cache_path2):
                print(json.dumps({"status":"error","message":"No cache found."}))
                sys.exit(1)
        with open(cache_path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        # Handle both old format (list) and new format ({{papers, deleted_ids}})
        if isinstance(raw, dict) and "papers" in raw:
            all_papers_list = raw["papers"]
            if "deleted_ids" in raw:
                delete_ids = raw["deleted_ids"]
        else:
            all_papers_list = raw
        if delete_ids:
            all_papers_list = [p for p in all_papers_list if p.get("_id") not in delete_ids]
            print(f"🗑️ Removed {len(delete_ids)} papers, {len(all_papers_list)} remaining")
        print(f"📂 Loaded {len(all_papers_list)} papers from cache")
        out_path = os.path.join(desktop, "Literature_Graph.html")
        # Save cleaned cache
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(all_papers_list, f, ensure_ascii=False, indent=2)
        render_dashboard(all_papers_list, direction, out_path)
        print(json.dumps({
            "status":"success",
            "message": f"🎉 图谱刷新完成！共 {len(all_papers_list)} 篇 → {out_path}",
            "paper_count": len(all_papers_list), "output_path": out_path
        }, ensure_ascii=False))
        return

    # Load existing papers if in append mode
    existing_papers = []
    if mode == "append" and os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                existing_papers = json.load(f)
            print(f"📂 Loaded {len(existing_papers)} existing papers from cache")
        except Exception:
            existing_papers = []

    print(f"🔬 Direction: {direction}")
    print(f"📅 Time range: {time_range}")
    print(f"🔑 Keywords: {keywords or '(none)'}")
    print(f"📊 Target: up to {limit} new papers (mode: {mode})")
    print("─"*50)

    # ── Multi-source search (OpenAlex + CrossRef via literature-search skill) ──
    queries = build_queries(direction, keywords)
    existing_keys = {(p["title"] or "").lower() for p in existing_papers}
    
    raw_papers = multi_source_search(
        queries=queries,
        limit=limit * 2,
        year_range=time_range,
        use_crossref=True,
    )
    print(f"   → {len(raw_papers)} raw results from OpenAlex + CrossRef")
    
    # Filter: valid DOI required, skip existing, dedup by title
    all_papers = {}
    for r in raw_papers:
        doi = (r.get("externalIds") or {}).get("DOI", "")
        if not doi or not doi.startswith("10."):
            continue
        key = (r["title"] or "").lower()
        if key in existing_keys:
            continue
        if key not in all_papers:
            all_papers[key] = r
    
    papers = list(all_papers.values())
    print(f"   → {len(papers)} papers after DOI filter + dedup")

    # Relevance scoring (keyword match + citation bonus)
    RELEVANCE_KW = ["depression", "multimodal", "detection", "recognition",
        "diagnosis", "deep learning", "audio", "video", "text", "speech",
        "facial", "mamba", "transformer", "fusion", "emotion", "neural",
        "mental health", "sentiment", "mood", "anxiety", "cnn", "lstm"]
    def rel_score(p):
        tl = (p["title"] + " " + p.get("abstract","")).lower()
        kw_score = sum(1 for kw in RELEVANCE_KW if kw in tl)
        cit_bonus = min(p.get("citationCount", 0) / 50, 3)  # up to +3 for highly cited
        return kw_score + cit_bonus
    papers = [p for p in papers if rel_score(p) >= 2]
    papers.sort(key=lambda p: (
        -rel_score(p),
        -venue_rank(p.get("venue","")),
        -(int(p.get("year", 0) or 0)),
        -(int(p.get("citationCount", 0) or 0)),
    ))
    papers = papers[:limit]

    if not papers and mode == "new":
        print(json.dumps({"status":"error","message":"No papers found."}))
        sys.exit(1)

    # Merge with existing in append mode
    if mode == "append":
        # Assign new IDs starting from max existing
        max_id = max((p.get("_id", 0) for p in existing_papers), default=0)
        for p in papers:
            max_id += 1
            p["_id"] = max_id
        all_papers_list = existing_papers + papers
        print(f"\n📄 Existing: {len(existing_papers)} + New: {len(papers)} = {len(all_papers_list)} total")
    else:
        for i, p in enumerate(papers):
            p["_id"] = i + 1
        all_papers_list = papers
        print(f"\n📄 Total unique papers: {len(papers)}")

    if not all_papers_list:
        print(json.dumps({"status":"error","message":"No papers found."}))
        sys.exit(1)

    for p in all_papers_list:
        tags = auto_tag(p)
        print(f"   {'⭐'*tags['venue_stars']} {p['title'][:60]}… [{p.get('year','?')}]")

    print("\n🔗 Rendering Canvas dashboard ...")
    out_path = os.path.join(desktop, "Literature_Graph.html")

    # Save to cache for future append/delete operations
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(all_papers_list, f, ensure_ascii=False, indent=2)
    print(f"💾 Cache saved: {cache_path} ({len(all_papers_list)} papers)")

    render_dashboard(all_papers_list, direction, out_path)

    print(f"\n✅ Done! → {out_path}")
    print(json.dumps({
        "status":"success",
        "message": f"🎉 图谱已生成！共 {len(all_papers_list)} 篇文献 → {out_path}",
        "paper_count": len(all_papers_list), "output_path": out_path
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()

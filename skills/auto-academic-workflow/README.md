# 📚 Auto Academic Workflow

> 给定研究方向 + 时间范围 → 自动搜索文献 → 智能标签化 → 评估算力需求 → 渲染交互式知识图谱  
> **全流程无人值守，零外部依赖**

[![Python](https://img.shields.io/badge/python-3.8%2B-blue)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

---

## 🎯 一句话定位

面向 AI 研究者的**全自动文献调研工具**。告诉它研究方向和年份，它帮你搜论文、贴标签、估算力、画图谱，最后在桌面生成一个炫酷的交互式 HTML 仪表盘。

---

## 📸 效果预览

生成的 `Literature_Graph.html` 是一个自包含的单文件网页，包含：

- **🌐 图谱视图** — Canvas 力导向图，节点代表论文，边代表语义关联（同架构 🔴 / 同期刊 🟡 / 同模态 🟢）
- **📋 表格视图** — 可排序、可过滤的论文列表，含全部元数据
- **🔍 多维过滤** — 按标题/作者/关键词搜索，按架构、模态、CCF 等级过滤
- **📝 详情面板** — 完整摘要、作者列表、DOI 链接、GitHub 仓库、中文翻译
- **🗑️ 删除 & 保存** — 在页面上删除不想要的论文，下载更新后的 JSON

> 界面采用深色主题，支持拖拽节点、缩放、双击跳转论文原文。

---

## 🔧 核心功能 Pipeline

```
研究方向 + 关键词
      │
      ▼
┌─────────────────────────────┐
│ Step 1: 构建多组查询          │
│ 研究方向 × 每个关键词          │
│ 精确查询 + 泛化查询           │
└──────────────┬──────────────┘
               ▼
┌─────────────────────────────┐
│ Step 2: 多源搜索             │
│ OpenAlex (主) + CrossRef (辅)│
│ 通过 literature-search 桥接   │
│ 3次指数退避重试 + 90s超时     │
└──────────────┬──────────────┘
               ▼
┌─────────────────────────────┐
│ Step 3: 规范化 + 合并 + 去重  │
│ 统一格式 (OA + CR → 统一schema)│
│ DOI优先 → 标题去重             │
│ 择优保留 (信息量排序)          │
└──────────────┬──────────────┘
               ▼
┌─────────────────────────────┐
│ Step 4: DOI验证 + 过滤        │
│ ✅ 10.xxx 格式 = 确认         │
│ ⚠️ 无DOI/异常格式 = 排除      │
│ 排除已存在论文 (append模式)    │
└──────────────┬──────────────┘
               ▼
┌─────────────────────────────┐
│ Step 5: 智能标签 + 丰富       │
│ • 架构识别 (8种)              │
│ • 模态识别 (5种)              │
│ • CCF 等级排序 (1-5★)        │
│ • VRAM 算力估算               │
│ • GitHub 仓库检测 (3级策略)   │
│ • 中文摘要生成                │
└──────────────┬──────────────┘
               ▼
┌─────────────────────────────┐
│ Step 6: 交互式 HTML 渲染      │
│ Canvas 力导向物理引擎         │
│ → Desktop/Literature_Graph.html│
│ 零 CDN · 纯前端 · 离线可用    │
└─────────────────────────────┘
```

---
  整体流程（6 步 Pipeline）

  用户自然语言输入
        │
        ▼
  ┌─────────────────────────────────────────────────┐
  │  OpenClaw 平台 加载 auto-academic-workflow Skill │
  │  (匹配触发词: "搜索论文" / "文献检索" / etc.)      │
  └──────────────────────┬──────────────────────────┘
                         │ 传入 JSON 参数
                         ▼
                search_and_render.py  (主引擎)
                         │
       ┌─────────────────┼─────────────────┐
       │ Step 1          │ Step 2           │ Step 3-5        │ Step 6
       │ build_queries() │ 多源搜索          │ 标注+丰富        │ 渲染
       │ 构造查询字符串    │ ↓                │ ↓               │ ↓
       │                 │ search_sources   │ auto_tag()      │ render_
       │                 │ .py (桥接层)      │ estimate_       │ dashboard()
       │                 │ ↓                │ compute()       │ ↓
       │                 │ subprocess 调用   │ detect_github() │ Desktop/
       │                 │ ↓                │ generate_cn_    │ Literature_
       │                 │ literature-search │ abstract()      │ Graph.html
       │                 │ Skill (外部依赖)  │                 │ (自包含HTML)
       │                 │ ↓                │                 │
       │                 │ OpenAlex API     │                 │
       │                 │ CrossRef API     │                 │
       └─────────────────┴──────────────────┴─────────────────┘

  ---
  调用的其他 Skill

  本 Skill 依赖 1 个外部 Skill：

  ┌───────────────────┬─────────────────────────────┬───────────────────────┐
  │   被调用 Skill    │          调用方式           │         作用          │
  ├───────────────────┼─────────────────────────────┼───────────────────────┤
  │ literature-search │ subprocess.run() 子进程调用 │ 提供底层 API 搜索能力 │
  └───────────────────┴─────────────────────────────┴───────────────────────┘

  具体调用路径：

  search_sources.py
      │
      ├── subprocess: python search_openalex.py --query "..." --max-results 30
      │       └── 调用 OpenAlex REST API (免费, 无需 API Key)
      │       └── 返回 JSONL (每行一篇论文)
      │
      └── subprocess: python search_crossref.py --query "..." --rows 10
              └── 调用 CrossRef REST API (免费, 无需 API Key)
              └── 返回 JSONL

  关键实现细节（在 search_sources.py 中）：

  1. 路径解析 — _skill_scripts_root() 自动查找 ~/.agents/skills/literature-search/scripts/ 目录
  2. 子进程调用 — subprocess.run(cmd, capture_output=True, timeout=90) 执行外部 Python 脚本，捕获 stdout
  3. JSONL 解析 — 逐行解析 stdout 中的 JSON 行
  4. 归一化合并 — OpenAlex 和 CrossRef 各自有 _normalize_*() 函数，统一为相同 schema
  5. 去重 — 按 DOI 优先、标题兜底的方式去重，重复时优先保留 OpenAlex（元数据更丰富）

  ---
  数据流向总结

  OpenAlex API ──┐
                 ├──→ literature-search skill ──→ search_sources.py ──→ search_and_render.py ──→ HTML
  CrossRef API ──┘     (外部 Skill, 子进程调用)      (桥接层, 归一化去重)    (主引擎, 标注渲染)      (桌面输出)

  不经过 OpenClaw Skill 系统调用 — literature-search 是通过 Python subprocess 直接以命令行方式调用的，而非通过 OpenClaw
  的 Skill 间通信机制。这是一种松耦合的集成方式：只要目标脚本在预期路径下存在并接受 CLI 参数、输出 JSONL，就能正常工作。


标签生成全部在 auto_tag() 函数中完成（search_and_render.py:189-254），采用纯规则匹配，不依赖任何 AI/ML 模型。

  ---
  输入

  从论文元数据中提取两个字段拼接为检测文本：

  text = title.lower() + " " + abstract.lower()

  ---
  三类标签的生成逻辑

  1. 架构标签（Architecture）— 8 种 + Unspecified

  按优先级依次匹配，命中即追加（一篇论文可有多个架构）：

  ┌─────────────┬───────────────────────────────────────────────────────────────────┬───────────────────────────────┐
  │    架构     │                            触发关键词                             │          防误判设计           │
  ├─────────────┼───────────────────────────────────────────────────────────────────┼───────────────────────────────┤
  │ Mamba/SSM   │ mamba, selective scan, structured state space                     │ 不接受单独的 state space      │
  ├─────────────┼───────────────────────────────────────────────────────────────────┼───────────────────────────────┤
  │ Transformer │ transformer, self-attention, multi-head attention, bert , vit ,   │ 单独的 attention              │
  │             │ vision transformer                                                │ 不触发（太泛化）              │
  ├─────────────┼───────────────────────────────────────────────────────────────────┼───────────────────────────────┤
  │ GCN         │ graph convolution, graph neural, gcn, gat , graph attention       │ 需要 graph + 具体方法名       │
  │             │ network                                                           │                               │
  ├─────────────┼───────────────────────────────────────────────────────────────────┼───────────────────────────────┤
  │ CNN         │ cnn , convolutional neural, resnet, vgg, densenet, efficientnet   │ 需要完整 CNN 架构名           │
  ├─────────────┼───────────────────────────────────────────────────────────────────┼───────────────────────────────┤
  │ LSTM/RNN    │ lstm, bilstm, gru , rnn , recurrent neural                        │ —                             │
  ├─────────────┼───────────────────────────────────────────────────────────────────┼───────────────────────────────┤
  │ Diffusion   │ diffusion model, denoising diffusion, ddpm, stable diffusion      │ —                             │
  ├─────────────┼───────────────────────────────────────────────────────────────────┼───────────────────────────────┤
  │ LLM         │ llm, large language model, gpt-, llama, chatgpt, foundation model │ —                             │
  ├─────────────┼───────────────────────────────────────────────────────────────────┼───────────────────────────────┤
  │ MLP         │ mlp, linear layer, feedforward, fully connected                   │ 仅在前 7 类均未命中时才检测   │
  ├─────────────┼───────────────────────────────────────────────────────────────────┼───────────────────────────────┤
  │ Unspecified │ 以上均不匹配                                                      │ 兜底                          │
  └─────────────┴───────────────────────────────────────────────────────────────────┴───────────────────────────────┘

  2. 模态标签（Modality）— 5 种

  同样命中即追加，可多选（如同时含 text 和 audio → ["Text", "Audio"]）：

  ┌───────────────┬──────────────────────────────────────────────────────────────────────────────────────────────────┐
  │     模态      │                                            触发关键词                                            │
  ├───────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ Text          │ text, transcript, linguistic, nlp , language model, dialogue, conversation, interview            │
  │               │ transcript, questionnaire                                                                        │
  ├───────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ Audio         │ audio, speech, acoustic, voice, vocal, mel-spectrogram, prosodic, mfcc                           │
  ├───────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ Video         │ video, visual, facial, face, facial expression, frame-level, image                               │
  ├───────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ Physiological │ eeg, fmri, brain signal, physiological, ecg, ppg, heart rate, gsr, electrodermal                 │
  ├───────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ Unspecified   │ 以上均不匹配                                                                                     │
  └───────────────┴──────────────────────────────────────────────────────────────────────────────────────────────────┘

  3. 期刊等级标签（Venue Rank）— 1~5 星

  venue_stars = venue_rank(paper["venue"])   # 1-5
  venue_ccf   = venue_ccf(paper["venue"])    # "A" / "B" / "C" / ""

  匹配逻辑：遍历 VENUE_RANK 字典（~110 个条目），对 venue 字段做子串包含匹配，取最高星级。核心映射：

  ┌──────┬─────────────────────────────────────────────────────────────────┐
  │ 等级 │                              来源                               │
  ├──────┼─────────────────────────────────────────────────────────────────┤
  │  5★ │ CCF-A 会议/期刊：CVPR, NeurIPS, ICML, AAAI, ACL, TPAMI, JMLR... │
  ├──────┼─────────────────────────────────────────────────────────────────┤
  │  4★ │ CCF-B：EMNLP, ICASSP, AISTATS, TACL, TMM...                     │
  ├──────┼─────────────────────────────────────────────────────────────────┤
  │  3★ │ CCF-C / SCI Q1：ACII, ICMI, Information Fusion...               │
  ├──────┼─────────────────────────────────────────────────────────────────┤
  │  2★ │ SCI/EI / arXiv                                                  │
  ├──────┼─────────────────────────────────────────────────────────────────┤
  │  1★ │ 未评级 / 预印本                                                 │
  └──────┴─────────────────────────────────────────────────────────────────┘

  ---
  汇总返回

  return {
      "architectures": ["Mamba/SSM", "Transformer"],  # 可多个
      "modalities":    ["Audio", "Video"],             # 可多个
      "venue_stars":   5,                              # 1-5
      "venue_ccf":     "A",                            # "A"/"B"/"C"/""
      "year":          2024,
  }


## 🏗️ 项目结构

```
auto-academic-workflow/
├── SKILL.md                      # AI Agent 技能描述文件
├── README.md                     # 本文件
├── scripts/
│   ├── search_and_render.py      # 主引擎 (1210行)
│   │   ├── build_queries()       #   查询构造
│   │   ├── auto_tag()            #   架构/模态/CCF 标签
│   │   ├── estimate_compute()    #   VRAM 估算
│   │   ├── detect_github()       #   GitHub 仓库检测
│   │   ├── generate_cn_abstract()#   中文摘要生成
│   │   ├── render_dashboard()    #   HTML 图谱渲染
│   │   └── main()                #   主流程编排
│   └── search_sources.py         # 多源搜索桥接 (384行)
│       ├── search_openalex()     #   OpenAlex API 子进程调用
│       ├── search_crossref()     #   CrossRef API 子进程调用
│       ├── _normalize_openalex() #   OA → 统一格式
│       ├── _normalize_crossref() #   CR → 统一格式
│       ├── _doi_to_venue()       #   DOI 前缀→期刊推断
│       ├── _url_to_venue()       #   URL 域名→期刊推断
│       ├── merge_and_dedup()     #   合并去重
│       └── multi_source_search() #   统一入口
└── references/
    └── venues.md                  # 顶会/期刊分级参考

外部依赖 (literature-search skill):
  ~\.agents\skills\literature-search\scripts\
  ├── search_openalex.py          # OpenAlex API 搜索 (221行)
  ├── search_crossref.py          # CrossRef API 搜索 (259行)
  └── download_arxiv_source.py    # arXiv 源码下载 (232行, 可选)
```

你输入: research_direction + keywords + time_range
                       │
                       ▼
┌──────────────────────────────────────────────────┐
│  search_and_render.py (主引擎, 1210行)             │
│                                                    │
│  def main()                                        │
│    ├─ build_queries()       → 生成 2 组搜索词       │
│    ├─ multi_source_search() → 调用 search_sources   │
│    ├─ DOI 过滤 + 去重 + 排序                        │
│    ├─ auto_tag()             → 逐篇打标签            │
│    ├─ detect_github()       → 逐篇检仓库            │
│    ├─ estimate_compute()    → 逐篇估算力            │
│    ├─ generate_cn_abstract()→ 逐篇翻中文            │
│    └─ render_dashboard()    → 生成 HTML             │
│                                                    │
│  import search_sources ←───┐                       │
└────────────────────────────┼──────────────────────┘
                             │
┌────────────────────────────┼──────────────────────┐
│  search_sources.py (桥接层, 384行)                  │
│                                                    │
│  def multi_source_search(queries, limit, ...)       │
│    ├─ search_openalex()    ──── subprocess ───────┐ │
│    ├─ search_crossref()    ──── subprocess ───┐   │ │
│    ├─ _normalize_openalex()  (统一 OA 格式)     │   │ │
│    ├─ _normalize_crossref()  (统一 CR 格式)     │   │ │
│    ├─ _doi_to_venue()       (DOI前缀→期刊名)    │   │ │
│    ├─ _url_to_venue()       (URL域名→期刊名)    │   │ │
│    ├─ merge_and_dedup()      (按DOI/标题去重)    │   │ │
│    └─ _pick_best()          (择优保留)          │   │ │
│                                                    │   │ │
│  返回: 统一格式的 paper dict 列表                   │   │ │
└────────────────────────────────────────────────────┘   │ │
                             │                          │ │
              ┌──────────────┼──────────────┐           │ │
              ▼              ▼              ▼           │ │
┌───────────────────────────────────────────────────┐  │ │
│  literature-search/scripts/ (底层, ~712行)          │  │ │
│                                                     │  │ │
│  search_openalex.py  (221行) ←──── HTTP ──── OpenAlex API │
│    argparse + urllib + JSONL 输出                    │◄─┘ │
│    处理 --query --max-results --year-range --sort    │     │
│                                                     │     │
│  search_crossref.py  (259行) ←──── HTTP ──── CrossRef API │
│    argparse + urllib + JSONL 输出                    │◄────┘
│    处理 --query --rows --bibtex --timeout            │
│                                                     │
│  download_arxiv_source.py (232行, 可选)              │
│    arXiv PDF/源码下载                                │
└───────────────────────────────────────────────────┘
🔴 search_and_render.py — 主引擎 (1210行)
这是整个 Skill 的核心大脑，每篇论文经过它 6 大处理环节：

build_queries(direction, keywords) → 构造搜索词
复制
输入: ("Multimodal Depression Detection", "mamba ssm")
输出: ["Multimodal Depression Detection",            # 精确查询
       "Multimodal Depression Detection mamba ssm"] # 泛化查询
没有 keywords 时，第二组自动追加 " neural network" 作为泛化

auto_tag(paper) → 架构+模态+CCF 标签
它是怎么工作的？

复制
paper.title + paper.abstract → 全小写 → 关键词匹配

架构匹配 (8类):
  "mamba" / "selective scan"               → Mamba/SSM
  "transformer" / "self-attention" / "bert" → Transformer
  "graph convolution" / "gcn" / "gat"       → GCN
  "cnn" / "convolutional neural" / "resnet" → CNN
  "lstm" / "bilstm" / "gru" / "rnn"         → LSTM/RNN
  "diffusion model" / "ddpm"                → Diffusion
  "llm" / "gpt-" / "llama" / "chatgpt"      → LLM
  "mlp" / "feedforward"                     → MLP (fallback)
  以上均无                                    → Unspecified

模态匹配 (5类):
  "text" / "transcript" / "linguistic" / "dialogue" → Text
  "audio" / "speech" / "acoustic" / "mfcc"          → Audio
  "video" / "visual" / "facial" / "face"            → Video
  "eeg" / "fmri" / "ecg" / "ppg" / "gsr"           → Physiological
  以上均无                                            → Unspecified

CCF 等级:
  paper.venue → venue_rank() → VENUE_RANK 字典匹配 → 1-5★
防误判 example：论文写了 "attention mechanism" 但没提 "transformer" → 不会标 Transformer，只有 "self-attention" 命中时才标。

estimate_compute(archs) → VRAM 估算
复制
取第一个架构标签 → 查字典映射
Mamba/SSM    → "24GB VRAM (RTX 4090)"
Transformer → "12-24GB VRAM (RTX 4080/4090)"
LLM         → "24-80GB VRAM (A100 40G/80G, 多卡)"
detect_github(paper) → GitHub 仓库检测 (三级策略)
复制
Strategy 1 (0ms): 正则搜 title + abstract 里的 github.com/... 
  命中 → 直接返回
  未命中 ↓

Strategy 2 (~5s): HTTP GET 论文 landing page (doi.org 或原文 URL)
  正则搜页面 html 里的 github.com/user/repo 
  命中 → 返回 (标注来源 "landing")
  未命中 ↓

Strategy 3 (~5s): 有 arxiv_id → HTTP GET arxiv.org/abs/{id}
  搜 arxiv 页面上的 GitHub 链接
  命中 → 返回 (标注来源 "arxiv")
  未命中 → 返回 ("", "")
generate_cn_abstract(paper, tags) → 中文翻译
复制
尝试 import deep_translator → GoogleTranslator 翻译英文摘要(前1200字符)
  ├─ 成功 → 中文翻译结果
  └─ 失败 (库未安装/网络不通) → _structured_cn_summary()
        模板拼接: "本文提出了基于{架构}的方法，
                    融合{模态}模态信息。{摘要首句}"
render_dashboard(papers, direction, out_path) → 生成 HTML
复制
for 每篇论文:
    调用 auto_tag()、detect_github()、estimate_compute()、generate_cn_abstract()
    → 组装 papers_data (dict 列表)
    → 计算统计 (total, years, all_archs, all_modals, top_count)
    → 构造 filter 下拉选项
    → 内嵌全部 papers_data 为 JS 变量 PAPERS
    → 内嵌 ~600行 JS (Canvas 物理引擎 + 交互逻辑)
    → 用 Python f-string 拼出一个完整 HTML
    → 写入 ~/Desktop/Literature_Graph.html
main() → 主流程编排
复制
1. 解析命令行 JSON 参数
2. 判断 mode: "new" / "append" / "reload"
3. append 模式: 读取本地缓存 ~/Desktop/literature_papers.json
4. reload 模式: 跳过搜索, 直接从缓存渲染
5. 新搜索模式:
   a. build_queries → 构造搜索词
   b. multi_source_search → 多源搜索 (OpenAlex + CrossRef)
   c. DOI 过滤 (必须有 10.xxx 格式 DOI)
   d. 按标题去重 + 排除已有论文
   e. rel_score() 相关性打分 + 排序 (关键词匹配 + 引用量加分)
   f. 限制数量取 top limit
6. append 模式: 新论文追加到已有列表
7. 保存到 ~/Desktop/literature_papers.json 缓存
8. render_dashboard → 生成 HTML
9. 输出 JSON 结果 (供 AI Agent 解析)
🟠 search_sources.py — 桥接层 (384行)
它的核心职责：把 literature-search 的裸 JSONL 输出，转换成 auto-academic-workflow 的统一格式。

multi_source_search(queries, limit, year_range, use_crossref=True)
复制
for 每个 query:
    ├─ subprocess.run([python, search_openalex.py, --query q, --max-results 30, ...])
    │   → 解析 JSONL stdout → all_oa[]
    └─ subprocess.run([python, search_crossref.py, --query q, --rows 20])
        → 解析 JSONL stdout → all_cr[]

→ merge_and_dedup(all_oa, all_cr)
  → 返回统一格式 paper list
_normalize_openalex(paper) / _normalize_crossref(paper)
两个源输出格式完全不同，需要各自规范化为：

复制
{
    "title": str,         # 标题
    "abstract": str,      # 摘要
    "venue": str,         # 期刊/会议 (可能是 "OpenAlex", 会被 _doi_to_venue 修正)
    "year": int,          # 年份
    "url": str,           # 链接 (优先 pdf_url, 否则 doi.org)
    "authors": [str],     # 作者列表
    "externalIds": {"DOI": str},  # DOI
    "source": "openalex"|"crossref",
    "citationCount": int,
    "peer_reviewed": bool,
}
_doi_to_venue(doi) / _url_to_venue(url) — 聪明的venue推断
很多论文的 venue 字段在 OpenAlex 中返回空或 "OpenAlex"，它从 DOI 前缀和 URL 域名反推：

DOI 前缀	推断
10.1109/	IEEE
10.1145/	ACM
10.18653/v1/	ACL Anthology
10.1609/	AAAI
10.1007/	Springer
10.48550/	arXiv
甚至还能从 DOI 路径中检出具体会议名：icassp → "ICASSP", neurips → "NeurIPS"

merge_and_dedup(oa_papers, cr_papers) + _pick_best()
复制
去重策略: DOI 优先, 没有 DOI 则用清洗后的标题
择优策略: OpenAlex 元数据质量更高, 优先保留 OpenAlex 版本
         若两个都是 CrossRef, 选摘要更长+作者更多的
🔵 search_openalex.py — OpenAlex 搜索 (221行)
独立可运行的 CLI 脚本，纯标准库：

复制
python search_openalex.py \
  --query "depression detection mamba" \
  --max-results 20 \
  --year-range 2024-2026 \
  --min-citations 5 \
  --sort cited_by_count:desc \
  -o results.jsonl
流程：

复制
urllib → GET api.openalex.org/works?search=...&per_page
...(truncated)...

**总代码量: ~1,594 行 Python (主引擎) + ~712 行 Python (依赖脚本) = ~2,300 行**

---

## 📦 安装

### 前置条件

- Python 3.8+
- 无需 `pip install` — 全部使用标准库
- 需要安装 `literature-search` 依赖 skill:

```bash
npx skills add lingzhi227/agent-research-skills@literature-search -g -y
```

### 验证安装

```bash
python scripts/search_sources.py --query "transformer" --limit 3
```

---

## 🚀 使用

### 基本用法

```bash
# 新搜索 (15篇)
python scripts/search_and_render.py '{"research_direction":"Multimodal Depression Detection","time_range":"2024-2026","limit":15}'

# 指定关键词
python scripts/search_and_render.py '{"research_direction":"depression detection","time_range":"2024-2026","keywords":"mamba ssm gcn","limit":20}'

# 增量添加 (追加拿不到的新论文)
python scripts/search_and_render.py '{"research_direction":"mamba depression","time_range":"2024-2026","mode":"append","limit":10}'

# 从缓存重新渲染 (删除论文后)
python scripts/search_and_render.py '{"mode":"reload","time_range":"2024-2026"}'
```

### 参数说明

| 参数 | 必填 | 说明 | 示例 |
|------|:--:|------|------|
| `research_direction` | ✅ | 核心研究方向 | `"Multimodal Depression Detection"` |
| `time_range` | ✅ | 年份范围 | `"2024-2026"`, `"2024-"`, `"最近两年"` |
| `keywords` | ❌ | 补充技术关键词，空格分隔 | `"mamba ssm gcn"` |
| `limit` | ❌ | 论文数量 (默认15, 最大30) | `20` |
| `mode` | ❌ | `"new"` (替换) / `"append"` (增量) / `"reload"` (从缓存重新渲染) | `"append"` |

### 输出文件

| 文件 | 位置 |
|------|------|
| 📊 交互图谱 | `~/Desktop/Literature_Graph.html` |
| 💾 论文缓存 | `~/Desktop/literature_papers.json` |

---

## 🧠 技术细节

### 架构检测 (8 种)

| 架构 | 检测关键词 | 置信度 |
|------|-----------|:------:|
| **Mamba/SSM** | `mamba`, `selective scan`, `structured state space` | 高 |
| **Transformer** | `transformer`, `self-attention`, `multi-head attention`, `bert`, `vit` | 高 |
| **GCN** | `graph convolution`, `graph neural`, `gcn`, `gat` | 高 |
| **CNN** | `cnn`, `convolutional neural`, `resnet`, `vgg`, `densenet`, `efficientnet` | 高 |
| **LSTM/RNN** | `lstm`, `bilstm`, `gru`, `rnn`, `recurrent neural` | 高 |
| **Diffusion** | `diffusion model`, `denoising diffusion`, `ddpm`, `stable diffusion` | 高 |
| **LLM** | `llm`, `large language model`, `gpt-`, `llama`, `chatgpt`, `foundation model` | 高 |
| **MLP** | `mlp`, `linear layer`, `feedforward`, `fully connected` | 中 |
| Unspecified | 以上均未匹配 | — |

> ⚠️ **防误判机制**: 单独的 `attention` 不会触发 Transformer 标签，必须出现 `transformer` 或具体模型名 (BERT/ViT 等)。

### 模态检测 (5 种)

| 模态 | 检测关键词 |
|------|-----------|
| 📝 Text | `text`, `transcript`, `linguistic`, `nlp`, `language model`, `dialogue` |
| 🎙️ Audio | `audio`, `speech`, `acoustic`, `voice`, `vocal`, `mel-spectrogram`, `mfcc` |
| 🎬 Video | `video`, `visual`, `facial`, `face`, `facial expression`, `image` |
| 🧠 Physiological | `eeg`, `fmri`, `brain signal`, `ecg`, `ppg`, `gsr`, `electrodermal` |
| ❓ Unspecified | 以上均未匹配 |

### CCF 等级排序 (1-5★)

| 等级 | 标签 | 示例 |
|:----:|------|------|
| 👑 5★ | CCF-A 会议/期刊 | CVPR, NeurIPS, AAAI, ACL, KDD, TPAMI, JMLR |
| 🏆 4★ | CCF-B 会议/期刊 | EMNLP, ICASSP, AISTATS, TACL, TMM |
| ⭐ 3★ | CCF-C / SCI Q1 | ACII, ICMI, Information Fusion |
| 📄 2★ | SCI/EI / arXiv | Scientific Reports, Frontiers in, arXiv |
| 📝 1★ | 未评级 / 预印本 | Research Square, Preprints.org |

> 超过 80 个会议/期刊的等级映射，详见 `references/venues.md`

### VRAM 算力估算

| 架构 | VRAM 估算 | 推荐 GPU |
|------|----------|---------|
| Mamba/SSM | 24GB | RTX 4090 |
| Transformer | 12-24GB | RTX 4080/4090 |
| GCN | 8-12GB | RTX 3070/4070 |
| CNN | 8-16GB | RTX 3070/4080 |
| LSTM/RNN | 4-8GB | RTX 3060+ |
| Diffusion | 16-24GB | RTX 4090 |
| LLM | 24-80GB | A100 40G/80G (多卡) |
| MLP | 4-8GB | RTX 3060+ |

### GitHub 仓库检测 (三级策略)

```
Strategy 1: 摘要/标题文本正则匹配 github.com/... (最快)
    ↓ 未命中
Strategy 2: HTTP 请求论文 Landing Page (doi.org / 原文URL)
    ↓ 5s 超时
Strategy 3: arXiv 论文 → 请求 arxiv.org/abs/{id} (提取 code 链接)
    ↓ 均未命中
输出: "暂无"
```

### Canvas 力导向图引擎

- **自研纯 Canvas 物理引擎**，无 d3.js / ECharts / vis.js 依赖
- 斥力 (25000) + 引力 (0.0015) + 向心力 (0.001) + 阻尼 (0.82)
- 节点颜色 = 架构类型，光环 = CCF 等级
- 边: 同架构 🔴 (曲线，架构色) / 同期刊 🟡 (直线，金色) / 同模态 🟢 (虚线，绿色)
- 每个节点最多 4 条边（避免视觉混乱）
- 滚轮缩放（向/离中心点缩放）
- 支持拖拽节点 + 悬浮 tooltip + 点击详情 + 双击打开原文

---

## ⚠️ 已知问题与不足

### 功能层面

| 问题 | 严重程度 | 说明 |
|------|:--------:|------|
| **仅限 DOI 论文** | 🔴 高 | 只保留 `10.xxx` 格式的 DOI 论文。arXiv 预印本 (无 DOI 或非标准 DOI) 会被 `arxiv_id` 检测绕过，但如果 OpenAlex 未收录 arXiv 版，则会丢失。建议增加 arXiv 直搜作为第三数据源 |
| **关键词匹配 = 漏判** | 🟡 中 | 架构/模态检测依赖关键词匹配，无法理解语义。例如 "we propose a novel alternative to transformer" 可能被误判为 Transformer。对缩写 (如 SSM) 有防误判，但无法覆盖所有边缘情况 |
| **VRAM 估算粗糙** | 🟡 中 | 只按架构大类估算，不考虑模型规模、batch size、精度 (FP32/FP16/INT8)。LLM 标签下 7B 和 405B 模型都显示 24-80GB |
| **中文翻译质量不稳定** | 🟡 中 | 依赖 `deep_translator` (GoogleTranslate)，如库不可用则退化为模板拼接 "本文提出了基于{架构}的方法，融合{模态}模态信息"。模板摘要信息量有限 |
| **GitHub 检测耗时** | 🟡 中 | Strategy 2/3 需要 HTTP 请求论文页面，每篇论文 5s 超时，30 篇论文最坏情况需 2.5 分钟额外耗时 |
| **无 PDF 全文分析** | 🟡 中 | 仅分析标题+摘要，不下载/解析 PDF 全文。一些重要细节 (如准确参数量、训练数据) 在源码/pdf 中才能找到 |

### 搜索层面

| 问题 | 严重程度 | 说明 |
|------|:--------:|------|
| **OpenAlex 覆盖率有限** | 🔴 高 | 某些细分领域 (如情感计算、多模态融合) 的期刊覆盖率不如 Semantic Scholar。已通过 CrossRef 补充，但仍有遗漏 |
| **子进程调用开销** | 🟡 中 | 每次搜索通过 `subprocess.run` 调用 literature-search 脚本，启动 Python 解释器的开销在 Windows 上尤为明显 |
| **无 Semantic Scholar 集成** | 🟡 中 | Semantic Scholar 在某些 CS 领域覆盖更好 (引用计数更准、作者消歧更好)，但目前需要额外安装 `deep-research` 子技能 |
| **单次最多 30 篇** | 🟡 中 | `limit` 参数硬上限 30。通过 append 模式可累积到 60+，但无法一次性大量搜索 |
| **搜索结果缓存缺失** | 🟢 低 | 每次搜索重新请求 API，没有中间缓存。频繁搜索浪费 API 配额和时间 |

### 工程技术

| 问题 | 严重程度 | 说明 |
|------|:--------:|------|
| **无单元测试** | 🔴 高 | 全部逻辑在一个 1210 行的文件中，没有 test/ 目录，核心函数 (`auto_tag`, `venue_rank`, `merge_and_dedup`) 无独立测试覆盖 |
| **同步阻塞架构** | 🔴 高 | 整个 pipeline 是串行阻塞的：搜索→等待→合并→等待→GitHub检测→等待→渲染。若用 `asyncio` + 并发的 HTTP 请求，速度可提升 3-5x |
| **错误处理不够细粒度** | 🟡 中 | 网络异常时静默失败 (`except Exception: pass`)，用户不知道是哪一步出错。应区分超时/DNS 解析/API 限流并分别处理 |
| **Windows 路径硬编码** | 🟡 中 | `search_sources.py` 中的 skill 路径解析优先查找 `USERPROFILE/.agents/skills`，在 macOS/Linux 上路径逻辑类似但未充分测试 |
| **单文件 1210 行** | 🟡 中 | `search_and_render.py` 承载了搜索编排、标签、渲染、主流程四层职责，应拆分为独立模块 |
| **HTML 内嵌 ~600 行 JS** | 🟢 低 | 力导向图和 UI 逻辑全部内嵌在 HTML 中，不易维护和测试，可考虑拆分独立的 JS 模板文件 |
| **无配置文件** | 🟢 低 | VENUE_RANK、ARCH_COLORS、RELEVANCE_KW 等硬编码在代码中，无法通过 config 文件自定义 |

### Canvas 交互

| 问题 | 严重程度 | 说明 |
|------|:--------:|------|
| **无触屏支持** | 🟢 低 | 力导向图仅支持鼠标交互，无 touch 事件，在平板上体验不佳 |
| **图谱初始布局不理想** | 🟢 低 | 初始布局为环形分布+随机偏移，物理模拟需要几秒才能稳定。没有预计算布局算法 |
| **删除后无法撤销** | 🟢 低 | 点击删除立即生效，无确认对话框和撤销机制 |

---

## 🔮 未来改进方向

### 短期待办

- [ ] 拆分 `search_and_render.py` 为独立模块 (search/enrich/render)
- [ ] 增加 Semantic Scholar 作为第三数据源
- [ ] 支持 `asyncio` + `aiohttp` 并发搜索和 GitHub 检测
- [ ] 增加 arXiv 直搜，解决无 DOI 论文丢失问题
- [ ] 增加 LLM 驱动的架构/模态识别 (替代纯关键词匹配)
- [ ] 添加 `pytest` 单元测试覆盖核心函数

### 中期待办

- [ ] 配置文件 (`config.yaml`) 支持自定义 venue 等级、关键词、颜色
- [ ] PDF 全文下载 + 文本提取 (通过 `download_arxiv_source.py`)
- [ ] 支持用户自定义标签体系
- [ ] Web 版部署 (Flask/FastAPI)，不再依赖本地 Python
- [ ] 支持从 Zotero / Mendeley 导入已有文献库

### 长尾

- [ ] 论文间引用关系图 (而非语义相似度边)
- [ ] 类似 Connected Papers 的拓扑排序布局
- [ ] 自动生成文献综述 Markdown 草稿
- [ ] 多语言扩展 (日/韩/法等)

---

## 🤝 依赖关系

```
auto-academic-workflow (本仓库)
    │
    ├── 直接依赖: literature-search
    │   ├── search_openalex.py    (OpenAlex API)
    │   └── search_crossref.py    (CrossRef API)
    │
    ├── 可选依赖: deep-translator  (pip install deep-translator)
    │   └── 用于 Google Translate 中文摘要
    │
    └── 数据源:
        ├── api.openalex.org       (免费, 无需 API Key)
        ├── api.crossref.org       (免费, 无需 API Key)
        └── doi.org                (DOI 验证)
```

---

## 📄 License

MIT

---

## 👤 作者

lingzhi227

---

*Made with ❤️ for AI researchers who are tired of manual literature surveys.*

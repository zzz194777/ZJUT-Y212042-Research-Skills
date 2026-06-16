# OpenClaw Research Skill 期末报告

---

## 1. Skill 基本信息

| 项目 | 内容 |
|------|------|
| **Skill 名称** | auto-academic-workflow |
| **小组编号** | 17 |
| **小组成员** | 吴彦翰，沈佳昊，焦秋宇 |
| **所属科研场景** | 文献调研与知识图谱构建 — 面向 AI/ML 研究者的自动化文献检索、标注与可视化 |
| **GitHub 路径** | `skills/auto-academic-workflow/` |

---

## 2. 这个 Skill 解决什么科研问题？

### 问题定位

本 skill 面向 **AI/ML 领域文献调研** 场景。

### 2.1 这个问题出现在科研流程的哪个环节？

出现在科研流程的最前端 —— **文献调研与选题论证阶段**。在确定研究方向、撰写 related work、评估技术路线可行性时，研究者需要快速了解某一方向上的顶会/顶刊论文分布、主流架构、常用模态和开源代码情况。

### 2.2 研究生平时为什么会遇到这个问题？

- 关键词检索返回大量论文，需逐篇打开阅读摘要来判断是否相关，耗时巨大
- 不同学术搜索引擎（Google Scholar / Semantic Scholar / arXiv / DBLP）覆盖范围不同，单一数据源容易漏掉重要论文
- 需要手动判断论文的会议等级（CCF-A/B/C？SCI 几区？），才能决定优先阅读哪些
- 想快速了解一个领域用了哪些模型架构（Mamba？Transformer？GCN？）、处理哪些数据模态（文本？语音？视频？生理信号？），这些信息隐藏在摘要中，需要人工一一提取

### 2.3 如果没有这个 skill，通常需要人工做哪些重复性工作？

| 人工步骤 | 耗时估计 | 本 Skill 自动化 |
|----------|:-------:|:--------------:|
| 在 Google Scholar / arXiv / DBLP 分别检索同一关键词 | 10-15 min | ✅ 双源 API 聚合 |
| 逐篇点开论文，阅读摘要判断相关性 | 30-60 min | ✅ 关键词相关性评分 |
| 手动标注每篇论文使用的模型架构 | 10-15 min | ✅ 8 类架构自动检测 |
| 手动标注每篇论文处理的数据模态 | 5-10 min | ✅ 5 类模态自动检测 |
| 查询每篇论文的会议/期刊等级 | 10-15 min | ✅ CCF 5 级自动匹配 |
| 判断哪些论文有开源代码 | 5-10 min | ✅ 三级 GitHub 检测策略 |
| 翻译英文摘要为中文 | 15-20 min | ✅ Google Translate 批量机翻 |
| 整理成表格或思维导图 | 10-20 min | ✅ 交互式 HTML 知识图谱 |
| **合计** | **~2-3 小时** | **~30-60 秒** |

### 2.4 这个问题是否有明确的输入材料和输出目标？

**输入**（明确的自然语言描述）：
- 研究方向（如 "Multimodal Depression Detection"）
- 时间范围（如 "2024-2026"）
- 可选补充关键词（如 "mamba ssm gcn"）
- 返回论文数量上限（默认 15，最大 30）

**输出**（确定位置的文件）：
- `~/Desktop/Literature_Graph.html` — 自包含交互式知识图谱
- `~/Desktop/literature_papers.json` — 结构化论文缓存

---

## 3. 它和普通 ChatGPT 问答有什么区别？

| 对比项 | 普通 ChatGPT 问答 | 本 Skill（auto-academic-workflow） |
|--------|------------------|--------------------------------------|
| **任务目标** | 临时回答一个问题 | 固化一个完整的文献调研工作流 |
| **输入材料** | 用户随意描述 | 明确要求研究方向 + 时间范围 + 可选关键词（结构化 JSON） |
| **分析流程** | 不固定，取决于提问方式 | 固定 6 步 Pipeline：构造查询 → 多源搜索 → 归一化去重 → DOI 验证 → 智能标注 → 渲染图谱 |
| **数据来源** | 只依赖模型训练数据（可能有幻觉） | 实时调用 OpenAlex + CrossRef API，每篇论文带可验证 DOI |
| **输出格式** | 不稳定，每次可能不同 | 固定结构：HTML 知识图谱 + JSON 缓存，格式完全确定 |
| **可复用性** | 依赖用户提问能力（换个问法可能答案不同） | 任何同学只需传入研究方向即可复用，输出格式一致 |
| **可验证性** | 较弱，无法判断论文是否真实存在 | 每篇论文有 DOI 链接，可直接点击验证；星级评定可对照 CCF 推荐列表复查 |
| **外部依赖** | 无 | 依赖 `literature-search` skill（OpenAlex + CrossRef 桥接），松耦合 subprocess 调用 |
| **可扩展性** | 无 | 支持增量追加（append 模式）、缓存重渲染（reload 模式）、论文删除 |

### 关键区别说明

本 skill 的价值不在于"让大模型回答得更漂亮"，而在于：

1. **将文献调研这一高频科研任务转化为标准化、可复用、可检查的自动化流程**
2. **输出带有可验证证据**：每篇论文的 DOI 链接可直接点击确认，CCF 等级可对照 CCF 官方推荐列表复查，架构标注可对照摘要原文验证
3. **不是一次性对话**：生成的 JSON 缓存支持增量追加和多轮迭代，图谱可反复重渲染
4. **松耦合设计**：主引擎与文献搜索 skill 通过 subprocess + JSONL 管道通信，可独立升级替换

---

## 4. 它的输出怎么验证？

### 4.1 输出中的结论是否能对应输入材料中的证据？

✅ 可以。每篇论文的每条标注都有明确的证据来源：

| 标注维度 | 证据来源 | 验证方式 |
|----------|----------|----------|
| 论文是否存在 | OpenAlex / CrossRef API 返回的原始数据 | 点击 DOI 链接直接访问原文 |
| 架构标注 | 论文标题 + 摘要中的关键词匹配 | 对照摘要原文逐词复查 |
| 模态标注 | 论文标题 + 摘要中的关键词匹配 | 对照摘要原文逐词复查 |
| CCF 等级 | `VENUE_RANK` 字典（~110 个会议/期刊条目）的子串匹配 | 对照 CCF 2022 推荐列表复查 |
| 引用数 | OpenAlex API 返回的 `cited_by_count` | 可在 OpenAlex 官网验证 |
| GitHub 仓库 | 摘要/标题正则 + DOI 落地页 HTTP 请求 + arXiv 页面解析 | 点击 GitHub 链接访问 |
| DOI 合法性 | DOI 是否以 `10.` 开头 | 标准 DOI 格式规则 |

### 4.2 是否标明了证据来源？

✅ 是的。在 `search_and_render.py` 中，每篇论文保留了 `source: "openalex"` 或 `"crossref"` 标签。生成的 HTML 图谱中：
- 点击论文节点 → 详情面板展示完整元数据（含 DOI 链接、GitHub 链接、来源）
- 表格视图可排序、可过滤，所有列可见

### 4.3 是否区分了"确定结论"和"不确定推测"？

✅ 是的。置信度通过以下方式体现：

| 结论类型 | 置信度 | 标识方式 |
|----------|:------:|----------|
| DOI 验证通过（`10.xxx`） | **高** | ✅ 绿色标识 |
| 架构标注命中精确关键词（如 `mamba`） | **高** | 关键词匹配 |
| 架构标注命中宽松关键词（如 `mlp`） | **中** | 仅在 7 类强特征均未命中时触发 |
| 期刊等级匹配 CCF-A（如 `CVPR`） | **高** | 5★ 星级 + "A" 标签 |
| 期刊等级匹配 arXiv | **低** | 2★ 星级 + 未评级标签 |
| GitHub 检测命中（摘要含 `github.com/...`） | **高** | 直接展示链接 |
| GitHub 检测未命中 | **不确定** | 显示"暂无" |
| 中文翻译（机器翻译） | **中** | 标注为 Google Translate 机翻 |

### 4.4 是否提供了 demo input 和 demo output？

✅ 是的。见 `examples/input/` 和 `examples/output/` 目录，以及第 7 节 Demo 展示。

### 4.5 是否可以由其他同学根据原始材料复查？

✅ 完全可以。其他同学可以：
1. 使用 `examples/input/` 中的相同 JSON 参数重新运行脚本
2. 对比生成的 HTML 图谱和 JSON 缓存与 `examples/output/` 中的参考输出
3. 通过 DOI 链接逐一验证论文真实性
4. 对照 CCF 推荐列表检查期刊等级标注
5. 阅读摘要原文检查架构/模态标签

---

## 5. 输入、输出和工作流程

### 5.1 输入材料

本 skill 接受一个 **JSON 参数字符串**作为输入：

```json
{
  "research_direction": "Multimodal Depression Detection",
  "time_range": "2024-2026",
  "keywords": "mamba ssm gcn",
  "limit": 15,
  "mode": "new"
}
```

| 参数 | 必填 | 说明 | 示例 |
|------|:--:|------|------|
| `research_direction` | ✅ | 核心研究方向（英文） | `"Multimodal Depression Detection"` |
| `time_range` | ✅ | 年份范围 | `"2024-2026"`, `"2024-"`, `"最近两年"` |
| `keywords` | ❌ | 补充技术关键词，空格分隔 | `"mamba ssm gcn"` |
| `limit` | ❌ | 返回论文数上限（默认 15，最大 30） | `15` |
| `mode` | ❌ | 工作模式：`"new"` / `"append"` / `"reload"` | `"new"` |

### 5.2 输出结果

| 输出文件 | 位置 | 格式 | 说明 |
|----------|------|------|------|
| **交互式知识图谱** | `~/Desktop/Literature_Graph.html` | 自包含 HTML | Canvas 力导向图 + 表格视图 + 筛选/搜索 + 详情面板 |
| **论文缓存** | `~/Desktop/literature_papers.json` | JSON | 结构化论文数据，支持增量追加和重渲染 |

图谱包含的每条论文记录结构：

```json
{
  "_id": 1,
  "title": "Mamba-Based Multimodal Depression Detection...",
  "abstract": "Depression is a prevalent mental health...",
  "venue": "IEEE Transactions on Affective Computing",
  "year": 2024,
  "url": "https://doi.org/10.1109/TAFFC.2024.xxxxxxx",
  "authors": ["Zhang, San", "Li, Si"],
  "externalIds": {"DOI": "10.1109/TAFFC.2024.xxxxxxx"},
  "source": "openalex",
  "citationCount": 15,
  "architectures": ["Mamba/SSM", "Transformer"],
  "modalities": ["Audio", "Video", "Text"],
  "venue_stars": 4,
  "venue_ccf": "B",
  "compute": "24GB VRAM (RTX 4090)",
  "github": "https://github.com/xxx/mamba-depression",
  "cn_abstract": "抑郁症是一种普遍的心理健康问题..."
}
```

### 5.3 工作流程（6 步 Pipeline）

```
Step 1: 构建多组查询
  ├── 精确查询：研究方向原样
  ├── 泛化查询：研究方向 × 每个关键词
  └── 兜底查询：研究方向 + "neural network"

Step 2: 多源搜索（search_sources.py 桥接层）
  ├── 对每个查询 → subprocess 调用 literature-search skill
  │   ├── search_openalex.py → OpenAlex REST API（主数据源）
  │   └── search_crossref.py → CrossRef REST API（补充数据源）
  ├── 指数退避重试（3 次）+ 90s 超时
  └── 返回 JSONL 格式原始结果

Step 3: 规范化 + 合并 + 去重
  ├── _normalize_openalex()  /  _normalize_crossref()  → 统一 schema
  ├── merge_and_dedup()：DOI 优先 → 标题兜底
  └── _pick_best()：重复时择优保留（OpenAlex > CrossRef）

Step 4: DOI 验证 + 相关性过滤
  ├── 仅保留 DOI 以 "10." 开头的论文
  ├── append 模式下排除已缓存论文（标题去重）
  ├── 相关性评分：关键词匹配分 + 引用数加分（最多 +3）
  └── 排序：相关性 > CCF 等级 > 年份 > 引用数

Step 5: 智能标签 + 丰富（auto_tag）
  ├── 架构识别：8 类规则匹配（Mamba/SSM, Transformer, GCN, CNN, LSTM/RNN, Diffusion, LLM, MLP）
  ├── 模态识别：5 类规则匹配（Text, Audio, Video, Physiological, Unspecified）
  ├── CCF 等级：VENUE_RANK 字典（~110 条目）子串匹配，1-5★
  ├── 算力估算：estimate_compute() 按主架构推荐 GPU/VRAM
  ├── GitHub 检测：detect_github() 三级策略（摘要匹配 → 落地页请求 → arXiv 页面）
  └── 中文摘要：generate_cn_abstract() 使用 deep_translator 机翻

Step 6: 交互式 HTML 渲染（render_dashboard）
  ├── 自包含单文件 HTML（零 CDN / 零外部 JS）
  ├── Canvas 力导向图：自研物理引擎（斥力 + 引力 + 向心力 + 阻尼）
  ├── 表格视图：可排序、可过滤
  ├── 筛选器：按架构 / 模态 / CCF 等级
  ├── 详情面板：完整元数据 + 删除按钮
  └── 保存按钮：下载更新后的 JSON 缓存
```

---

## 6. 本组特色设计

### 6.1 多源 API 聚合 + 三级去重

不同于单一数据源的文献搜索，本 skill 通过 `search_sources.py` 桥接层同时调用 **OpenAlex**（覆盖面最广的免费学术 API）和 **CrossRef**（DOI 精确检索），在归一化后进行 DOI 优先 + 标题兜底的两级去重，确保高召回率的同时避免重复。

### 6.2 基于规则的高精度标注引擎

所有论文标注（架构、模态、CCF 等级）采用 **纯规则匹配**，不依赖任何 AI/ML 模型。优势：
- **确定性**：相同输入永远产生相同输出，完全可复现
- **零成本**：无需 GPU 推理或 API 调用费用
- **可审计**：每个标签对应具体关键词，可逐条复查
- **保守策略**：如泛化的 `attention` 不会触发 Transformer 标签，避免过度标注

### 6.3 自包含 Canvas 力导向图

生成的 HTML 知识图谱 **完全不依赖外部 CDN 或 JS 框架**（如 D3.js、ECharts、vis.js）。力导向图物理引擎使用纯原生 JavaScript + Canvas 2D API 手写实现，包括：
- 节点间斥力模拟（Coulomb's law）
- 边引力模拟（Hooke's law）
- 中心引力（防止漂移）
- 速度阻尼（收敛稳定）
- 滚轮缩放交互
- 节点拖拽
- 边类型着色（同架构 🔴 曲线 / 同期刊 🟡 直线 / 同模态 🟢 虚线）

### 6.4 增量缓存机制

支持三种工作模式：
- **new**：全新检索，替换所有缓存
- **append**：增量追加，自动与已有论文去重合并
- **reload**：从缓存重渲染，支持删除论文后重新生成图谱

这使得文献调研成为一个 **可迭代的过程** —— 可以先用广泛关键词搜索，再用追加模式补充特定技术方向的论文。

### 6.5 三级 GitHub 仓库检测策略

```
Strategy 1: 摘要/标题正则匹配 "github.com/..."（最快，0 延迟）
    ↓ 未命中
Strategy 2: HTTP 请求论文 Landing Page（DOI 或出版社页面），扫描 GitHub 链接
    ↓ 5s 超时
Strategy 3: arXiv 论文 → 请求 arxiv.org/abs/{id} 页面，提取 "Code" 链接
    ↓ 均未命中
输出: "暂无"
```

### 6.6 领域针对性

本 skill 专门面向 **AI/ML 研究领域**，内置了：
- 8 种主流架构的检测规则
- 5 种常见数据模态的检测规则
- ~110 个 AI/ML 相关顶会/顶刊的 CCF 等级映射
- 按架构的 GPU/VRAM 估算表（含具体 GPU 型号推荐）

---

## 7. Demo 展示

### 7.1 Demo 输入

详见 `examples/input/` 目录，包含以下测试用例：

| 文件 | 场景 | 参数 |
|------|------|------|
| `input_depression_mamba.json` | Mamba + 抑郁检测 | `research_direction`: "Mamba Depression Detection", `time_range`: "2024-2026", `limit`: 15 |
| `input_multimodal_emotion.json` | 多模态情感计算 | `research_direction`: "Multimodal Emotion Recognition", `time_range`: "2024-2026", `keywords`: "transformer fusion", `limit`: 10 |
| `input_eeg_gcn.json` | EEG + 图神经网络 | `research_direction`: "EEG-based Emotion Recognition GCN", `time_range`: "2023-2026", `limit`: 15 |
| `input_append.json` | 增量追加模式 | `mode`: "append", 向已有缓存追加新论文 |

### 7.2 Demo 输出

详见 `examples/output/` 目录：

| 文件 | 说明 |
|------|------|
| `literature_papers_depression.json` | 抑郁检测方向的结构化论文缓存（15 篇） |
| `output_summary.md` | 运行结果摘要（论文列表 + 标签统计 + 日志输出） |
| 截图 | `screenshot_graph.png` — 知识图谱界面截图 |
| 截图 | `screenshot_table.png` — 表格视图截图 |

**实际运行日志示例**：

```
🔬 Direction: Mamba Depression Detection
📅 Time range: 2024-2026
🔑 Keywords: (none)
📊 Target: up to 15 new papers (mode: new)
──────────────────────────────────────────────────
🔍 OpenAlex: "Mamba Depression Detection"...
   → 28 results
🔍 OpenAlex: "Mamba Depression Detection neural network"...
   → 32 results
🔍 CrossRef: "Mamba Depression Detection"...
   → 8 results
📊 Merged: 60 OA + 8 CR → 45 unique
   → 38 papers after DOI filter + dedup
   ⭐⭐⭐⭐ Mamba State-Space Models for Affective Computing… [2025]
   ⭐⭐⭐⭐⭐ Multimodal Depression Detection with Selective Scan… [2024]
   ⭐⭐⭐⭐ EEG-Based Depression Recognition via Mamba… [2025]
   ...
📄 Total unique papers: 15

🔗 Rendering Canvas dashboard ...
💾 Cache saved: C:\Users\...\Desktop\literature_papers.json (15 papers)

✅ Done! → C:\Users\...\Desktop\Literature_Graph.html
```

### 7.3 Demo 结果分析

#### Skill 是否正确理解了任务？

✅ 是的。输入参数被正确解析，查询构造合理（精确查询 + 泛化查询），搜索结果与研究方向高度相关。

#### 输出是否结构清楚？

✅ 是的。HTML 图谱包含三种视图（图谱 / 表格 / 详情面板），层级分明。JSON 缓存包含完整的结构化元数据，格式统一。

#### 结论是否有证据？

✅ 是的。
- 每篇论文的 DOI 可点击跳转到原文
- CCF 等级标注可对照 CCF 2022 推荐列表复查（如 "IEEE Transactions on Affective Computing" → CCF-B → 4★）
- 架构标注可通过摘要原文逐词验证（如摘要含 "Mamba" 和 "selective scan" → Mamba/SSM）

#### 是否存在不可靠或需要人工检查的地方？

⚠️ 存在以下需要人工确认的情况：
1. **架构标注的边界情况**：如果论文使用了 Mamba 的变体但在摘要中使用了非标准术语，可能被漏标为 "Unspecified"
2. **CCF 等级的边缘情况**：部分会议名称拼写变体可能未覆盖（如 "CVPR Workshop" 被识别为 CVPR 5★ 但 workshop 论文质量可能较低）
3. **机器翻译质量**：中文摘要由 Google Translate 生成，专业术语翻译可能不够准确
4. **引用数时效性**：OpenAlex 的引用计数可能滞后于最新引用

---

## 8. 局限性和改进方向

### 8.1 当前局限性

| 局限 | 影响 | 严重程度 |
|------|------|:------:|
| **纯英文检索**：OpenAlex 和 CrossRef API 不支持中文查询 | 无法检索 CNKI/万方等中文数据库中的论文 | 中 |
| **关键词标注漏标**：基于规则的标注可能遗漏使用非标准术语描述的架构 | 部分论文的架构被标注为 "Unspecified" | 中 |
| **CCF 等级以偏概全**：会议 workshop / poster 论文与正会论文同等对待 | 可能高估部分 workshop 论文的等级 | 低 |
| **无全文分析**：仅基于标题和摘要进行标注 | 论文方法部分涉及的技术可能未被覆盖 | 中 |
| **静态图谱**：生成的 HTML 是静态快照，不支持多用户协作 | 不适合团队文献调研场景 | 低 |
| **翻译质量**：依赖 Google Translate，专业术语翻译可能不准确 | 中文摘要仅供参考 | 低 |
| **无 PDF 下载**：仅提供 DOI 链接跳转，不下载 PDF 全文 | 离线阅读不便 | 低 |

### 8.2 改进方向

1. **引入大模型增强标注**：对规则无法确定的论文，使用轻量级 LLM（如 GPT-4o-mini）分析摘要进行增强标注，显著提高 "Unspecified" 论文的召回率
2. **接入中文数据库**：集成 CNKI、万方等中文数据库 API，支持中英文混合文献调研
3. **PDF 全文解析**：下载开源论文 PDF，解析 methods 章节进行更精准的架构和模态识别
4. **论文间引用关系图**：通过 OpenAlex 的引用关系数据，在图谱中展示论文间的引用/被引用边
5. **实时协作**：将图谱升级为 WebSocket 实时同步的 Web 应用，支持多人协作标注和讨论
6. **多轮增量搜索**：支持在一次会话中多次以不同关键词追加搜索，自动合并去重
7. **自动生成 Related Work 段落**：基于检索结果，利用 LLM 生成 LaTeX 格式的 related work 初稿
8. **证据矩阵导出**：将标注结论和证据来源导出为 Excel/CSV 格式，方便导师或合作者审查

---

## 9. GitHub 提交说明

### 9.1 本组提交文件

```
skills/auto-academic-workflow/
├── SKILL.md                          # OpenClaw Skill 定义文件（元数据 + 文档）
├── skill_card.md                     # 本文件（期末报告）
├── README.md                         # 项目 README（功能说明 + 使用指南）
├── scripts/
│   ├── search_and_render.py          # 主引擎（1210 行）— 全流程编排
│   └── search_sources.py             # 多源搜索桥接层（384 行）— API 聚合
├── references/
│   └── venues.md                     # 顶会/期刊分级参考文档
├── examples/
│   ├── input/
│   │   ├── input_depression_mamba.json
│   │   ├── input_multimodal_emotion.json
│   │   ├── input_eeg_gcn.json
│   │   └── input_append.json
│   └── output/
│       ├── literature_papers_depression.json
│       └── output_summary.md
└── tests/
    └── (待添加)
```

### 9.2 Pull Request 链接

（待提交 PR 后填写）

---

## 10. 总结

本组构建的 `auto-academic-workflow` skill 面向 AI/ML 研究者的文献调研场景，解决了从"关键词输入"到"结构化知识图谱"的全流程自动化需求。相比普通 ChatGPT 问答，本 skill 具有以下核心优势：

1. **不是"问一个问题"，而是"固化一个流程"**：固定的 6 步 Pipeline（构造查询 → 多源搜索 → 归一化去重 → DOI 验证 → 智能标注 → 渲染图谱），每位同学只需传入研究方向即可获得格式一致的输出
2. **输出可验证**：每篇论文携带可点击 DOI 链接，CCF 等级可对照官方列表复查，架构/模态标签可对照摘要原文验证，消除了大模型幻觉风险
3. **真数据源**：实时调用 OpenAlex + CrossRef 学术 API，返回的是真实发表的论文，而非模型"编造"的文献
4. **专业领域知识内嵌**：~110 个 AI/ML 顶会/顶刊的 CCF 等级映射、8 类架构检测规则、5 类模态检测规则，使工具具备领域专业性

后续可进一步扩展：引入大模型增强标注、接入中文数据库、支持 PDF 全文解析、增加论文间引用关系图、升级为实时协作 Web 应用，以及自动生成 LaTeX related work 初稿。

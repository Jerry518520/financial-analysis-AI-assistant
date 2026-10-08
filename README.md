# AI财报分析助手 (Financial Report AI Assistant)

<p align="center">
  <img alt="Python Version" src="https://img.shields.io/badge/python-3.11%2B-blue">
  <img alt="Framework" src="https://img.shields.io/badge/Backend-FastAPI-green">
  <img alt="Framework" src="https://img.shields.io/badge/Frontend-HTML%20%2B%20Tailwind%20%2B%20ECharts-red">
  <img alt="Deploy" src="https://img.shields.io/badge/Docker-Ready-blue">
  <img alt="GPU" src="https://img.shields.io/badge/GPU-CUDA_12.6-green">
  <img alt="License" src="https://img.shields.io/badge/license-MIT-lightgrey">
</p>

利用大语言模型（LLM）帮助非金融专业人士读懂上市公司 PDF 财报。上传财报，用自然语言提问、计算指标、生成摘要、看能力雷达图。

---

## 效果预览

<p align="center">
  <img alt="贵州茅台 2025 年年度报告分析结果" src="docs/assets/main.png" width="92%">
</p>

> 真实运行结果：上传**贵州茅台 2025 年年度报告**（143 页 PDF）后，系统输出综合能力评级（73 分 / B 级）、四维能力雷达图（盈利能力 A / 经营增长 C / 债务风险 T / 资产质量 C）与核心财务数据表。表中每个数字都标注了来源页码，由 RAG 检索链路自动给出。

---

## 项目规模与关键实现

| 维度 | 实现 |
|---|---|
| Agent 工作流 | LangGraph 闭环：规划 → 工具调用 → 反思 → 重试，最多 **5 轮**迭代收敛 |
| 工具层 | 封装 **19 个**财务计算工具 |
| 文档解析 | LlamaParse 混合解析，攻克中文财报 PDF **无边框表格** |
| 检索 | BGE-M3 + FAISS，核心指标语义检索（Top-K）+ BM25 混合 |
| 部署 | Docker Compose 一键启动，GPU / CPU 依赖分离 + 健康检查 |

> ⚠️ 当前状态：检索与工具调用链路已完整跑通并通过集成测试，但尚未建立系统性的检索质量评测基线。
> 这是下一步工作。我认为「能跑通 Demo」不等于「效果可控」。

---

## Agent 工作流

```
用户提问
   ↓
任务规划
   ↓
工具调用（19 个财务工具）
   ↓
结果反思 ── 未收敛则回到「任务规划」重试，最多 5 轮
   ↓
生成分析 + 引用溯源 + 能力雷达图
```

- **状态管理**：上下文按需裁剪，避免多轮工具调用后上下文膨胀。
- **失败处理**：LLM 调用失败按退避策略重试；工具执行异常时回退到已有结果，而不是用幻觉填充。
- **集成测试**：`tests/` 下含 `integration_test.py` / `integration_agent_test.py` / `integration_test_full.py`。

---

## 技术栈概览

| 层 | 技术 |
|---|---|
| Agent | LangGraph · LangChain · ReAct · Function Calling |
| 解析与检索 | LlamaParse · BGE-M3 · FAISS |
| 后端 | Python 异步 · FastAPI · Uvicorn |
| 前端 | HTML + Tailwind + ECharts |
| 部署 | Docker Compose，CUDA 12.6 |

---

## 核心功能

- **智能PDF解析**: PyMuPDF + LlamaParse 混合解析，支持无边框表格。可在界面上选择解析引擎：`自动` / `强制 LlamaParse` / `仅 PyMuPDF（离线）`
- **RAG问答**: 基于 FAISS + BGE-M3 向量检索，精准回答财务数据问题
- **AI Agent**: LangGraph ReAct 循环，自动规划、调用工具、反思重试
- **21种财务指标**: 增长率、利润率、ROE、EPS、PE、资产负债率、流动比率、速动比率、资产/存货周转率、股息率、趋势分析、同比分析、行业对比等（完整清单见 `src/financial_report_ai_assistant/core/agent.py` 的 `get_tools()`）
- **能力雷达图**: 按国资委企业绩效标准的 4 维度加权评分（盈利能力 30% / 资产质量 20% / 债务风险 20% / 经营增长 30%），带 7 个行业基准库与 Altman Z-Score 风险分区
- **一键摘要**: 结构化财报核心摘要
- **精准溯源**: 每个回答标注来源页码，可渲染原文页面高亮

---

## 硬件要求

| 场景 | GPU 要求 | 说明 |
|------|----------|------|
| **Docker 部署** | **必需** | 需要 NVIDIA 显卡 + 已装驱动 + `nvidia-container-toolkit`。`docker-compose.yml` 里写死了 GPU 预留，**无 GPU 的机器会在创建容器阶段直接失败** |
| **本地开发** | 推荐，非必需 | 无 GPU 时自动回退 CPU（`rag_service.get_device()`），embedding 明显变慢，其余功能不受影响 |
| 显存 | >= 4GB | BGE-M3 模型约 2GB，加上推理开销 |
| 磁盘 | >= 15GB | Docker 镜像 + torch CUDA wheel（约 850MB） |

> 想在无 GPU 的机器上跑？两条路：① 用下方「本地开发」路径（推荐）；② 把 `docker-compose.yml` 里 backend 服务的整个 `deploy:` 块注释掉再 `docker compose up --build`（embedding 走 CPU，慢但能跑）。

---

## 第一次使用（Docker 部署）

### 第 1 步：安装前置软件

| 软件 | 说明 | 下载 |
|------|------|------|
| Docker Desktop | 容器运行环境 | [下载](https://www.docker.com/products/docker-desktop/) |
| NVIDIA 驱动 + nvidia-container-toolkit | GPU 支持（Docker 部署必需） | [官方指引](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html) |
| Git | 版本控制（可选） | [下载](https://git-scm.com) |

> 没有 Git？直接在 GitHub 页面点 "Code" → "Download ZIP"，解压即可。

**安装后确保 Docker Desktop 已启动**（任务栏能看到 Docker 图标）。可先运行 `nvidia-smi` 确认驱动正常。

### 第 2 步：获取代码

```bash
git clone https://github.com/Jerry518520/financial-analysis-AI-assistant
cd financial-analysis-AI-assistant
```

或下载 ZIP 解压后，用终端进入项目目录。

### 第 3 步：配置 API Key

复制环境变量模板：

```bash
cp env.template .env   # Windows CMD 用: copy env.template .env
```

编辑 `.env` 文件，填入你的 API Key：

```env
DEEPSEEK_API_KEY=sk-你的key        # 必填
LLAMA_CLOUD_API_KEY=llx-你的key    # 可选，不填则降级为纯 PyMuPDF 解析
```

**获取方式**：
- DeepSeek API Key: https://platform.deepseek.com/
- LlamaCloud API Key: https://cloud.llamaindex.ai/ （免费，用于增强表格解析）

> **可选配置**：`FORCE_LLAMA_PARSE=true` 可强制所有表格页走 LlamaParse（默认先尝试 PyMuPDF，失败再用 LlamaParse）。该变量已通过 `docker-compose.yml` 显式传入容器，写进 `.env` 即可生效。
>
> 界面上的「解析引擎」下拉框是同一件事的运行时开关，优先级高于 `.env`：
> - `自动`：PyMuPDF 优先，质量不佳时才用 LlamaParse（默认）
> - `强制 LlamaParse`：所有表格/图表页都走 LlamaParse，需要 API Key
> - `仅 PyMuPDF`：完全离线，不调用 LlamaParse

### 第 4 步：（可选）预下载加速

首次构建需要下载约 850MB 的 PyTorch CUDA 包，Docker 内下载较慢（30-60 分钟）。

**想加速？** 双击运行 `download_wheels.bat`，把 wheel 提前拉到 `docker/wheels/`。

```bash
# 双击这个文件即可：
download_wheels.bat

# 或者用命令行（等价）：
poetry run poe download-wheels
python scripts/download_docker_wheels.py
```

> 不运行也能构建，只是慢。这个步骤完全可选。

### 第 5 步：构建并启动

```bash
docker compose up --build
```

首次构建时间参考：
- **有预下载**: 5-10 分钟
- **无预下载**: 30-60 分钟（取决于网速）
- **后续构建**: 2-5 分钟（有缓存）

> 后台运行加 `-d`：`docker compose up --build -d`

### 第 6 步：访问应用

只有一个服务：后端同时提供界面和 API。

| 地址 | 说明 |
|------|------|
| http://localhost:8000 | **应用界面**。前端是纯静态页面 `frontend/index.html`（Tailwind + ECharts），由 FastAPI `GET /` 直接伺服，无需额外容器 |
| http://localhost:8000/docs | 后端 API 文档（Swagger UI） |
| http://localhost:8000/health | 健康检查（排查启动问题先看它） |

### 停止应用

```bash
docker compose down
```

---

## 更新到最新版本

```bash
git pull
docker compose up --build -d
```

> ⚠️ **必须加 `--build`**，否则 `docker compose up` 会使用旧镜像，代码修复不会生效。

### 遇到数据异常？清除缓存重来

如果更新后计算结果仍不正确，可能是旧缓存导致的。清除缓存后重新上传 PDF：

```bash
docker compose down
rm -rf cache_data faiss_index     # Windows CMD: rmdir /s /q cache_data faiss_index
docker compose up --build -d
```

> 缓存有两种：PDF 解析结果（`cache_data/parsed_*_{hash}.md`，按解析引擎分别缓存）和财务数据缓存（进程内）。换解析引擎后请重新上传以刷新对应缓存。

---

## 本地开发（可选）

需要 Python 3.11 及以上（3.13 亦可，`pyproject.toml` 声明 `>=3.11,<3.15`），推荐有 NVIDIA GPU。

### 一键启动（Windows）

双击 `start.bat`。它做五件事：

1. 定位解释器（优先 `.venv\Scripts\python.exe`，找不到才问 poetry）
2. 缺 `.env` 时从 `env.template` 复制一份
3. 检查 `.env` 里是否还是模板占位 key，是则停住提醒你改
4. 拉起后端（新开一个控制台窗口），轮询 `/health` 直到就绪
5. 打开浏览器

停止服务：双击 `stop.bat`，按端口 8000 关掉监听进程。

> **首次使用必须先改 `.env`**：把 `DEEPSEEK_API_KEY=sk-your-deepseek-api-key` 换成真实 key，否则服务能起来、页面能打开，但所有 AI 问答都会 401。
>
> **本机有 HTTP 代理时**（`HTTP_PROXY` 非空的场景）：`start.bat` 已对 `127.0.0.1` 设置 `NO_PROXY`，同时等待循环里的 `curl` 显式带 `--noproxy '*'`。手动敲命令排查时也要加这个参数，否则浏览器 / curl 会把 localhost 请求发给代理，表现为 502 或「目标计算机积极拒绝」。

命令行等价方式：

```bash
# 1. 安装依赖
poetry install

# 2. 安装 CUDA 版 torch（poetry 默认装的是 CPU 版）
poetry run poe install-cuda-torch

# 3. 配置 .env（同上）

# 4. 启动服务（后端自带前端，浏览器打开 http://127.0.0.1:8000）
poetry run poe start
```

### 运行测试

```bash
poetry run poe test          # 全部测试
poetry run poe test-cov      # 带覆盖率
pytest tests/services/test_financial_calculator.py -v   # 单个文件
```

> `tests/` 下的 `integration_test.py`、`integration_test_full.py`、`integration_agent_test.py` 是**手动脚本不是单元测试**：它们要求本机已启动后端、项目根有 `example_report.pdf`、并有真实 DeepSeek API Key。pytest 已配置为只收集 `test_*.py`，不会误跑它们；需要时手动执行，例如 `python tests/integration_agent_test.py`。
>
> 其余测试用 `tests/conftest.py` 注入的假 Key 即可离线运行；`tests/services/test_rag_service.py` 首次运行需要能加载 BGE-M3 模型。

### 可用 poe 任务

| 命令 | 作用 |
|------|------|
| `poe start` | 启动 FastAPI 后端 |
| `poe test` / `poe test-cov` | 跑测试 |
| `poe install-cuda-torch` | 把 CPU 版 torch 换成 CUDA 版 |
| `poe export-docker-reqs` | 重新生成 `requirements-docker.txt` |
| `poe download-wheels` | 预下载 torch CUDA wheel（等价于 `download_wheels.bat`） |

---

## 项目结构

```
financial-report-ai-assistant/
├── src/                          # 后端源码
│   └── financial_report_ai_assistant/
│       ├── api/                  # FastAPI 路由（main.py / analysis.py / utils.py）
│       ├── core/                 # Agent 核心逻辑（LangGraph ReAct + 21 个工具）
│       └── services/             # PDF解析、RAG、计算、数据缓存
├── frontend/
│   └── index.html                # 前端（纯静态 HTML，由后端 GET / 伺服，端口 8000）
├── tests/                        # pytest 单测（api / core / services）+ 手动集成脚本
├── docs/                         # 开发过程文档（agents、issues、TDD 题目）
├── scripts/                      # 工具脚本（CUDA torch、wheel 预下载、依赖导出）
├── docker/wheels/                # 预下载的 wheel 文件（git 忽略）
├── Dockerfile                    # 应用镜像（后端 + 前端静态文件）
├── docker-compose.yml            # 编排配置（单服务）
├── download_wheels.bat           # 预下载加速脚本
├── start.bat                     # Windows 一键启动（本地开发用）
├── env.template                  # 环境变量模板
├── pyproject.toml                # Poetry 依赖定义
├── poetry.lock                   # 锁定版本
├── requirements-docker.txt       # Docker 构建依赖
└── .env                          # API Key（不提交到 git）
```

---

## API 一览

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/` | 内置 HTML 前端（返回 `frontend/index.html`） |
| GET | `/health` | 健康检查 |
| POST | `/upload?parser=auto\|llamaparse\|pymupdf` | 上传并解析 PDF，**单文件上限 100MB**（超限返回 413） |
| POST | `/preview-chunks` | 预览切块效果（调试用） |
| POST | `/chat` | 问答主接口 |
| POST | `/chat_debug` | 同 `/chat`，额外返回 `contexts` 数组，供 RAGAS 评测 |
| GET | `/highlight` | 按页码渲染 PDF 页面 PNG（前端溯源高亮） |
| POST | `/analyze/summary` | 生成结构化财报摘要（`focus`: general/financial/risk/business） |
| GET | `/analyze/industries` | 返回可选行业列表 |
| POST | `/analyze/radar` | 生成能力雷达图评分数据 |

完整交互文档见 http://localhost:8000/docs。

---

## 环境变量

| 变量 | 必填 | 默认 | 说明 |
|------|------|------|------|
| `DEEPSEEK_API_KEY` | 是 | — | DeepSeek API Key |
| `LLAMA_CLOUD_API_KEY` | 否 | — | 表格/图表增强解析；不填则降级为纯 PyMuPDF |
| `FORCE_LLAMA_PARSE` | 否 | `false` | 强制所有表格页走 LlamaParse。Docker 下由 compose 显式传入，写 `.env` 即可生效 |
| `HF_ENDPOINT` / `HF_HUB_URL` | 否 | `https://hf-mirror.com` | HuggingFace 镜像源（代码内置默认值，可被环境变量覆盖） |
| `FAISS_INDEX_PATH` | 否 | `<项目根>/faiss_index` | 向量索引目录；Docker 内为 `/app/faiss_index` |

> `env.template` 里还有 `MIMO_*` / `KIMI_*` 等条目，标注为「实验性（后端尚未实现）」，当前代码不使用，界面上也没有对应入口。

---

## 常见问题

**Q: 构建时卡在下载 torch 很久？**

A: 双击运行 `download_wheels.bat` 预下载，再构建。或者耐心等，最终会完成。

**Q: 启动时报 "could not select device driver nvidia"？**

A: Docker 部署必须有 NVIDIA GPU + 驱动 + `nvidia-container-toolkit`。没有就改用「本地开发」路径，或把 `docker-compose.yml` 里 backend 的 `deploy:` 块注释掉。

**Q: 启动后报 CUDA 不可用？**

A: 只是警告不是错误——代码会自动回退 CPU，功能正常但向量化变慢。想用 GPU 就运行 `nvidia-smi` 检查驱动是否正常。

**Q: 页面打不开 / 容器显示 unhealthy？**

A: 先看 `docker compose logs backend`。健康检查走的是 `/health`；若你改过 compose，请确保没有把它改回 `/`（`/` 依赖 `frontend/index.html`，缺文件会 404 导致健康检查永不通过）。前端页面由后端直接伺服，前端和后端之间不存在跨容器调用，所以「前端连不上后端」这类问题在新架构下不会发生——页面能打开就说明后端活着。

**Q: 上传大财报失败？**

A: 单文件上限 100MB，超限会返回 413。

**Q: 解析引擎该选哪个？**

A: 默认「自动」即可（PyMuPDF 优先，识别到无边框表格时才调 LlamaParse）。表格乱码严重时选「强制 LlamaParse」（需 API Key）；没有外网或想省额度选「仅 PyMuPDF」。换引擎后建议重新上传一次文件，避免命中旧解析缓存。

**Q: 怎么跑测试？**

A: `poetry run poe test`。详见上文「运行测试」。

**Q: 如何查看日志？**

A: `docker compose logs -f` 查看实时日志，`docker compose logs backend` 只看后端。

---

## 技术栈

| 层 | 技术 |
|---|------|
| 前端 | 原生 HTML + Tailwind + ECharts（`frontend/index.html`，由 FastAPI `GET /` 伺服，同源调用无需配置） |
| 后端 | FastAPI + Uvicorn |
| AI Agent | LangGraph (ReAct) + DeepSeek 原生 Function Calling |
| 向量数据库 | FAISS |
| Embedding | BAAI/bge-m3（sentence-transformers，自动 CUDA/CPU 切换） |
| PDF解析 | PyMuPDF + LlamaParse（可切换/强制/禁用） |
| LLM | DeepSeek API |
| 容器化 | Docker + Docker Compose |
| 依赖管理 | Poetry |
| 测试 | pytest + pytest-asyncio + pytest-cov；RAGAS（评测用，`/chat_debug` 供数） |

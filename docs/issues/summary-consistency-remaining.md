# Issue: 核心概要数据一致性未达100%

## 状态: Open
## 优先级: Medium
## 创建日期: 2026-06-05

---

## 问题描述

TDD测试中，核心概要（`/analyze/summary`）与对话问答（`/chat`）的数据一致性为 **87.0% (20/23)**，未达到100%目标。

### 当前不一致项（3个）

| # | Sheet | 字段 | 对话返回值 | 概要表现 | 根因 |
|---|-------|------|-----------|----------|------|
| 1 | Sheet1 (中兴通讯) | EPS | 1.17元/股 | 概要中偶发缺失 | LLM非确定性，EPS非计算字段 |
| 2 | Sheet2 (600212) | EPS | -0.0305元/股 | 概要中偶发缺失 | 同上 |
| 3 | Sheet2 (600212) | 速动比率 | 0.82 | 概要中偶发缺失 | RAG上下文中存货数据偶发缺失 |

---

## 根因分析

### 问题1&2: EPS缺失

EPS（每股收益）是**直接从财报提取**的字段，不是通过`_compute_summary_ratios()`计算得出的。当前的后处理注入机制（`_inject_missing_data`）只覆盖计算字段（毛利率、净利率、资产负债率、流动比率、速动比率），无法注入EPS。

**当前保障链路：**
1. ✅ Prompt硬化（编号字段清单）→ 仅覆盖提取阶段的10个计算字段
2. ✅ 提取重试（`_extract_with_retry`）→ 仅覆盖提取阶段
3. ✅ 后处理注入（`_inject_missing_data`）→ 仅覆盖`computed_data_str`中的字段
4. ❌ **EPS不在任何保障链路中** → 依赖LLM在摘要生成时自行引用

### 问题3: 速动比率缺失

速动比率 = (流动资产 - 存货) / 流动负债。Sheet 2的RAG上下文中，存货数据有时未被检索到，导致LLM提取时`存货`字段为null，下游无法计算速动比率。

**当前保障链路：**
1. ✅ Prompt硬化 → 会要求提取存货字段
2. ✅ 提取重试 → 会尝试补全存货字段
3. ❌ **RAG上下文中确实没有存货数据时** → 重试也无法凭空提取
4. ✅ 后处理注入 → 如果computed_data_str中没有速动比率，也无法注入

---

## 修复方案

### 方案A: 扩展注入逻辑覆盖所有指标（推荐，低风险）

将EPS、ROE等非计算字段也纳入`computed_data_str`，使注入机制能覆盖。

**修改文件:** `src/financial_report_ai_assistant/api/analysis.py`

```python
# 在 _compute_summary_ratios() 中，将非计算字段也加入结果
# 从 raw_data 中直接提取的字段（非计算得出）
DIRECT_FIELDS = {
    "EPS": "基本每股收益",  # 从财报直接提取
}

# 在 generate_report_summary() 中，将这些字段也加入 computed_data_str
if raw_data.get("基本每股收益"):
    computed["EPS"] = f"{raw_data['基本每股收益']}元/股"
```

**优点:** 零新依赖，改动小
**缺点:** 需要手动维护字段列表

### 方案B: 引入instructor库强制结构化输出（彻底解决）

使用`instructor`库 + Pydantic模型强制LLM返回包含所有字段的结构化数据。

**修改文件:** 
- `src/financial_report_ai_assistant/api/analysis.py`
- `requirements.txt` (新增 `instructor`)

```python
import instructor
from pydantic import BaseModel, Field
from typing import Optional

class ExtractedFinancials(BaseModel):
    营业收入: Optional[float] = Field(None)
    营业成本: Optional[float] = Field(None)
    净利润: Optional[float] = Field(None)
    上期营业收入: Optional[float] = Field(None)
    上期净利润: Optional[float] = Field(None)
    总资产: Optional[float] = Field(None)
    负债总额: Optional[float] = Field(None)
    流动资产: Optional[float] = Field(None)
    流动负债: Optional[float] = Field(None)
    存货: Optional[float] = Field(None)
    基本每股收益: Optional[float] = Field(None)  # 新增
    加权平均净资产收益率: Optional[float] = Field(None)  # 新增
```

**优点:** 100%保证字段存在（Pydantic默认值），自动重试
**缺点:** 新增依赖，需测试DeepSeek兼容性

### 方案C: 扩大RAG检索覆盖存货数据

针对Sheet 2速动比率缺失问题，在RAG检索阶段增加存货相关查询。

**修改文件:** `src/financial_report_ai_assistant/api/analysis.py`

```python
# 在 FOCUS_QUERIES["general"] 中增加
"存货 存货跌价准备 流动资产",
```

**优点:** 从源头解决数据缺失
**缺点:** 增加检索成本，不解决EPS问题

### 方案D: 摘要后处理验证+LLM补全

摘要生成后，检查是否包含所有关键指标，缺失则用LLM补充一段。

**优点:** 最灵活
**缺点:** 增加一次LLM调用，延迟+成本

---

## 推荐实施路径

1. **短期（立即）:** 方案A — 扩展`computed_data_str`覆盖EPS/ROE等直接字段
2. **中期（下次迭代）:** 方案C — 扩大RAG检索覆盖存货数据
3. **长期（架构优化）:** 方案B — 引入instructor库统一结构化输出

---

## 验收标准

运行 `python run_full_tdd_tests.py`，概要一致性 ≥ 95% (当前87.0%)

---

## 相关文件

- `src/financial_report_ai_assistant/api/analysis.py` — 摘要生成主逻辑
- `run_full_tdd_tests.py` — TDD测试脚本
- `memory/tdd-results-2026-06-05.md` — 测试结果记录

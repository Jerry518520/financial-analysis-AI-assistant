# Issue: 核心概要数据一致性未达100%

## 状态: Open
## 优先级: Medium
## 创建日期: 2026-06-05
## 最后更新: 2026-06-05

---

## 问题描述

TDD测试中，核心概要（`/analyze/summary`）与对话问答（`/chat`）的数据一致性为 **91.3% (21/23)**，未达到100%目标。

### 当前不一致项（2个）

| # | Sheet | 字段 | 对话返回值 | 概要表现 | 根因 |
|---|-------|------|-----------|----------|------|
| 1 | Sheet2 (600212) | 流动比率 | 1.20 | 概要中缺失 | `_inject_missing_data` 字符串误匹配 |
| 2 | Sheet2 (600212) | 速动比率 | 0.82 | 概要中缺失 | 同上 |

### 已修复的不一致项（本次迭代）

| # | Sheet | 字段 | 修复前 | 修复后 | 修复方式 |
|---|-------|------|--------|--------|----------|
| 1 | Sheet1 | 总资产 | ❌ 缺失 | ✅ 100% | 统一数据路径 + 缓存 |
| 2 | Sheet1 | EPS | ❌ 偶发缺失 | ✅ 100% | `_compute_all_metrics` 直接字段 |
| 3 | Sheet1 | 流动比率 | ❌ 偶发缺失 | ✅ 100% | 统一缓存 + 注入 |
| 4 | Sheet1 | 速动比率 | ❌ 偶发缺失 | ✅ 100% | 统一缓存 + 注入 |
| 5 | Sheet2 | 总资产 | ❌ 缺失 | ✅ 100% | 统一数据路径 + 缓存 |
| 6 | Sheet2 | EPS | ❌ 偶发缺失 | ✅ 100% | `_compute_all_metrics` 直接字段 |
| 7 | Sheet2 | 流动比率 | ❌ 缺失 | ❌ 仍缺失 | 注入函数误匹配bug |

---

## 根因分析

### 问题1&2: Sheet 2 流动比率/速动比率缺失

**根本原因：`_inject_missing_data` 的字符串匹配有缺陷。**

当前注入逻辑：
```python
# 检查摘要中是否包含该数值
if value_clean not in summary.replace(",", "").replace(" ", ""):
    missing.append((key, value))
```

问题：`value_clean = "1.20"` 这个数字太短、太常见，可能出现在摘要文本的其他上下文中（如"第1.20节"、"增长1.20倍"、页码等），导致函数误以为该指标已包含在摘要中，跳过注入。

**实际执行流程：**
1. ✅ 缓存中有流动比率 = 1.20
2. ✅ LLM生成摘要时未包含流动比率
3. ❌ `_inject_missing_data` 检查 "1.20" 是否在摘要中 → 在文本其他地方找到了 "1.20" → 误判为已包含
4. ❌ 不触发注入 → 摘要中缺失流动比率

---

## 修复方案

### 方案A: 双重匹配 — 指标名称+数值同时检查（推荐，最小改动）

修改 `_inject_missing_data`，要求**指标名称和数值同时出现**才算真正包含：

```python
def _inject_missing_data(summary: str, computed_data_str: str) -> str:
    """后处理：检查摘要是否包含所有已计算的数据，缺失则补充。"""
    # ...
    for key, value in computed_items:
        value_clean = value.replace(",", "").replace(" ", "")
        # 【修复】必须同时包含指标名称和数值，才算真正包含
        if key not in summary or value_clean not in summary:
            missing.append((key, value))
    # ...
```

**优点:** 改动极小（1行代码），立即生效
**缺点:** 如果LLM用不同名称展示指标（如"流动资金比率"而非"流动比率"），仍可能误判

### 方案B: 模板注入 — 不依赖后处理，直接在prompt中强制表格行

在摘要生成模板中，用 Jinja/Python 直接生成表格行，不依赖LLM：

```python
# 在 data_section 中直接生成 Markdown 表格行
table_rows = []
for k, v in computed_metrics.items():
    table_rows.append(f"| {k} | {v} | - | - |")
forced_table = "\n".join(table_rows)
```

**优点:** 100%保证所有指标出现在表格中
**缺点:** 表格格式由代码控制，不够灵活

### 方案C: 引入instructor库强制结构化输出（彻底解决）

使用`instructor`库 + Pydantic模型强制LLM返回包含所有字段的结构化数据。

**优点:** 根本解决LLM遗漏问题
**缺点:** 新增依赖，需测试DeepSeek兼容性

---

## 推荐实施路径

1. **立即:** 方案A — 修改 `_inject_missing_data` 为双重匹配
2. **短期:** 方案B — 模板注入作为兜底保障
3. **长期:** 方案C — 引入instructor库

---

## 验收标准

运行 `python run_full_tdd_tests.py`：
- 问答通过率 = 100%（当前已达标）
- 概要一致性 ≥ 95%（当前91.3%，目标：23/23 = 100%）

---

## 相关文件

- `src/financial_report_ai_assistant/api/analysis.py` — `_inject_missing_data` 函数（L172-L210）
- `src/financial_report_ai_assistant/services/financial_data_store.py` — 统一缓存模块
- `run_full_tdd_tests.py` — TDD测试脚本
- `memory/tdd-results-2026-06-05.md` — 测试结果记录

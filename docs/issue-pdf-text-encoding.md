# [BUG] PyMuPDF get_text() 对 Type0 子集字体中文解码为乱码，导致 RAG 检索全面失效

## Parent issue

#1 (关键财务指标数据提取遗漏) — 本 issue 定位了 Issue 1 的根因

## What happened

上传中兴通讯 2025 年年度报告摘要 PDF 后，查询"基本每股收益""资产总额"等指标，系统回答"未找到"。每次上传该 PDF 后查询均复现。

经排查，`document_parser.py` 使用 PyMuPDF 的 `page.get_text()` 提取文字，但该方法对 PDF 中 Type0 子集字体（如 `MLJNAR+SimSun`）的中文字符解码为乱码（如 `ÿÿÿÿÿÿ` 代替"基本每股收益"）。数字和英文字母正常提取。

**对比验证：** 使用 `page.get_text("html")` 提取时，中文字符通过 HTML 实体（如 `&#x6bcf;&#x80a1;&#x6536;&#x76ca;`）正确保留，可完美还原为"基本每股收益"。

**实际提取结果对比：**

| 提取方式 | 资产总额 | 基本每股收益 |
|---------|---------|------------|
| `get_text()` (当前) | 乱码 `ʲ����` | 乱码 `ÿÿÿÿÿÿ` |
| `get_text("html")` (修复后) | 资产总额 217,739.4 | 基本每股收益 1.17 |

## What I expected

系统应能正确提取 PDF 中的中文文字，包括使用 Type0 子集字体（SimSun 等）的中文财务报告，使 RAG 检索能匹配到"基本每股收益""资产总额"等关键词。

## Steps to reproduce

1. 上传"中兴通讯：2025年年度报告摘要.PDF"
2. 等待文档处理完成
3. 提问"基本每股收益是多少？"或"资产总额是多少？"
4. 系统回答"未找到"或给出错误数据

## Root cause

`document_parser.py` 中所有文字提取均使用 `page.get_text()`（plain text 模式）。PyMuPDF 的 plain text 模式在处理 Type0 子集字体（Identity-H 编码 + 自定义 CMap）时，无法正确将字符码映射到 Unicode，导致中文字符输出为乱码。

该问题影响所有使用类似字体嵌入方式的中文 PDF 财报，不限于中兴通讯。

## Suggested fix

将 `document_parser.py` 中的 `page.get_text()` 调用改为 `page.get_text("html")`，然后解析 HTML 输出提取纯文本（HTML 实体形式保留了正确的 Unicode codepoint）。

或者评估 `pdfplumber`/`pdfminer.six` 等替代库对 Type0 字体的解码支持。

## Additional context

- 数字（133,895.5、217,739.4）和百分比正常提取，仅中文字符乱码
- 该 PDF 使用的字体：SimSun（Type0, Identity-H, 子集嵌入）、TimesNewRomanPSMT
- 此问题也是 Issue #1（关键财务指标数据提取遗漏）的根本原因
- **Blocked by:** None — 可立即开始修复
- **Blocks:** #1（本 issue 修复后 Issue 1 应随之解决）

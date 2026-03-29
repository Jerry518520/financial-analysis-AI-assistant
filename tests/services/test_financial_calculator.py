"""
财务计算模块单元测试
覆盖 financial_calculator.py 中全部 20 个函数的正常、边界和异常场景。
"""

import pytest
from financial_report_ai_assistant.services.financial_calculator import (
    calculate_growth_rate,
    calculate_margin,
    calculate_roe,
    format_percentage,
    calculate_debt_ratio,
    calculate_current_ratio,
    calculate_quick_ratio,
    calculate_eps,
    calculate_pe,
    calculate_turnover,
    calculate_inventory_turnover,
    calculate_dividend_yield,
    analyze_trend,
    analyze_yoy,
    compare_to_industry,
    generate_chart_data,
    calculate_avg,
    calculate_max,
    calculate_min,
    calculate_variance,
)


# ============================================================
# 1. calculate_growth_rate - 同比增长率
# ============================================================
class TestCalculateGrowthRate:
    def test_positive_growth(self):
        """本期 > 上期，正增长"""
        assert calculate_growth_rate(1200, 1000) == 0.2

    def test_negative_growth(self):
        """本期 < 上期，负增长"""
        assert calculate_growth_rate(800, 1000) == -0.2

    def test_zero_growth(self):
        """本期 = 上期，零增长"""
        assert calculate_growth_rate(1000, 1000) == 0.0

    def test_previous_zero(self):
        """上期为0，应返回错误提示"""
        assert calculate_growth_rate(100, 0) == "无法计算（分母为0）"

    def test_both_zero(self):
        """本期和上期均为0"""
        assert calculate_growth_rate(0, 0) == "无法计算（分母为0）"

    def test_negative_previous(self):
        """上期为负数（如亏损转盈利）"""
        result = calculate_growth_rate(500, -200)
        assert isinstance(result, float)

    def test_negative_both(self):
        """本期和上期均为负数"""
        result = calculate_growth_rate(-100, -200)
        assert isinstance(result, float)


# ============================================================
# 2. calculate_margin - 利润率
# ============================================================
class TestCalculateMargin:
    def test_normal_margin(self):
        assert calculate_margin(300, 1000) == 0.3

    def test_loss_margin(self):
        """亏损情况，利润为负"""
        result = calculate_margin(-200, 1000)
        assert result == -0.2

    def test_revenue_zero(self):
        assert calculate_margin(100, 0) == "无法计算（营收为0）"

    def test_both_zero(self):
        assert calculate_margin(0, 0) == "无法计算（营收为0）"


# ============================================================
# 3. calculate_roe - 净资产收益率
# ============================================================
class TestCalculateROE:
    def test_normal_roe(self):
        assert calculate_roe(150, 1000) == 0.15

    def test_negative_equity(self):
        """净资产为负"""
        result = calculate_roe(100, -500)
        assert isinstance(result, float)

    def test_equity_zero(self):
        assert calculate_roe(100, 0) == "无法计算（净资产为0）"


# ============================================================
# 4. format_percentage - 格式化百分比
# ============================================================
class TestFormatPercentage:
    def test_positive(self):
        assert format_percentage(0.25) == "25.00%"

    def test_negative(self):
        assert format_percentage(-0.15) == "-15.00%"

    def test_zero(self):
        assert format_percentage(0) == "0.00%"

    def test_string_passthrough(self):
        """字符串应原样返回"""
        assert format_percentage("无法计算") == "无法计算"


# ============================================================
# 5. calculate_debt_ratio - 资产负债率
# ============================================================
class TestCalculateDebtRatio:
    def test_normal(self):
        assert calculate_debt_ratio(600, 1000) == 0.6

    def test_over_100_percent(self):
        """资不抵债，负债率 > 100%"""
        result = calculate_debt_ratio(1200, 1000)
        assert result == 1.2

    def test_assets_zero(self):
        assert calculate_debt_ratio(100, 0) == "无法计算（总资产为0）"


# ============================================================
# 6. calculate_current_ratio - 流动比率
# ============================================================
class TestCalculateCurrentRatio:
    def test_normal(self):
        assert calculate_current_ratio(200, 100) == 2.0

    def test_below_one(self):
        """流动性差，流动比率 < 1"""
        assert calculate_current_ratio(80, 100) == 0.8

    def test_liabilities_zero(self):
        assert calculate_current_ratio(100, 0) == "无法计算（流动负债为0）"


# ============================================================
# 7. calculate_quick_ratio - 速动比率
# ============================================================
class TestCalculateQuickRatio:
    def test_normal(self):
        assert calculate_quick_ratio(200, 50, 100) == 1.5

    def test_inventory_exceeds_assets(self):
        """存货 > 流动资产，速动比率为负"""
        result = calculate_quick_ratio(50, 100, 100)
        assert result == -0.5

    def test_liabilities_zero(self):
        assert calculate_quick_ratio(100, 50, 0) == "无法计算（流动负债为0）"


# ============================================================
# 8. calculate_eps - 每股收益
# ============================================================
class TestCalculateEPS:
    def test_normal(self):
        assert calculate_eps(5000, 1000) == 5.0

    def test_loss(self):
        assert calculate_eps(-2000, 1000) == -2.0

    def test_shares_zero(self):
        assert calculate_eps(100, 0) == "无法计算（股本为0）"


# ============================================================
# 9. calculate_pe - 市盈率
# ============================================================
class TestCalculatePE:
    def test_normal(self):
        assert calculate_pe(30, 2) == 15.0

    def test_negative_eps(self):
        """亏损企业的市盈率为负"""
        result = calculate_pe(10, -2)
        assert result == -5.0

    def test_eps_zero(self):
        assert calculate_pe(10, 0) == "无法计算（EPS为0）"


# ============================================================
# 10. calculate_turnover - 资产周转率
# ============================================================
class TestCalculateTurnover:
    def test_normal(self):
        assert calculate_turnover(5000, 10000) == 0.5

    def test_assets_zero(self):
        assert calculate_turnover(100, 0) == "无法计算（总资产为0）"


# ============================================================
# 11. calculate_inventory_turnover - 存货周转率
# ============================================================
class TestCalculateInventoryTurnover:
    def test_normal(self):
        assert calculate_inventory_turnover(3000, 500) == 6.0

    def test_inventory_zero(self):
        assert calculate_inventory_turnover(100, 0) == "无法计算（存货为0）"

    def test_negative_cogs(self):
        """营业成本为负"""
        result = calculate_inventory_turnover(-100, 500)
        assert isinstance(result, float)


# ============================================================
# 12. calculate_dividend_yield - 股息率
# ============================================================
class TestCalculateDividendYield:
    def test_normal(self):
        assert calculate_dividend_yield(2, 50) == 0.04

    def test_price_zero(self):
        assert calculate_dividend_yield(2, 0) == "无法计算（股价为0）"

    def test_negative_dividend(self):
        """负股息"""
        result = calculate_dividend_yield(-1, 50)
        assert isinstance(result, float)


# ============================================================
# 13. analyze_trend - 趋势分析
# ============================================================
class TestAnalyzeTrend:
    def test_rising_trend(self):
        result = analyze_trend([100, 120, 150])
        assert result["趋势方向"] == "上升"
        assert result["首年数值"] == 100
        assert result["末年数值"] == 150
        assert result["总年数"] == 3

    def test_declining_trend(self):
        result = analyze_trend([150, 120, 100])
        assert result["趋势方向"] == "下降"

    def test_flat_trend(self):
        result = analyze_trend([100, 100, 100])
        assert result["趋势方向"] == "持平"

    def test_single_value(self):
        """少于2个数据点"""
        result = analyze_trend([100])
        assert result["趋势"] == "数据不足"

    def test_empty_list(self):
        result = analyze_trend([])
        assert result["趋势"] == "数据不足"

    def test_with_none_values(self):
        """包含 None 值，应被过滤掉，保留 0"""
        result = analyze_trend([100, None, 150])
        assert result["趋势方向"] == "上升"
        assert result["首年数值"] == 100
        assert result["末年数值"] == 150

    def test_with_zeros(self):
        """包含 0，现在是合法值，保留参与计算"""
        result = analyze_trend([100, 0, 200])
        assert result["趋势方向"] == "上升"
        assert result["总年数"] == 3  # 3个数据点，0 被保留
        # first=100, last=200, years=2
        assert result["年均增长率(CAGR)"] == round((200/100) ** (1/2) - 1, 4)

    def test_all_zeros(self):
        """全为 0：first=0, last=0, CAGR 无法计算"""
        result = analyze_trend([0, 0])
        assert result["趋势方向"] == "持平"
        assert result["年均增长率(CAGR)"] == 0

    def test_zero_first_nonzero_last(self):
        """首年为 0，末年非 0，CAGR 无法计算"""
        result = analyze_trend([0, 100])
        assert result["趋势方向"] == "上升"
        assert result["年均增长率(CAGR)"] == "无法计算（首年数值为0）"

    def test_cagr_calculation(self):
        """验证 CAGR 计算：(150/100)^(1/1) - 1 = 0.5（只有2个数据点，years=1）"""
        result = analyze_trend([100, 150])
        assert result["年均增长率(CAGR)"] == 0.5


# ============================================================
# 14. analyze_yoy - 同比分析
# ============================================================
class TestAnalyzeYoY:
    def test_growth(self):
        result = analyze_yoy(1200, 1000)
        assert result["增长类型"] == "增长"
        assert result["同比增长率"] == 0.2
        assert result["绝对变化量"] == 200

    def test_decline(self):
        result = analyze_yoy(800, 1000)
        assert result["增长类型"] == "下降"

    def test_flat(self):
        result = analyze_yoy(1000, 1000)
        assert result["增长类型"] == "持平"

    def test_previous_zero(self):
        result = analyze_yoy(100, 0)
        assert result["变化"] == "无法计算"

    def test_negative_previous(self):
        """上期为负（亏损转盈利）"""
        result = analyze_yoy(100, -50)
        assert result["增长类型"] == "增长"


# ============================================================
# 15. compare_to_industry - 行业对比
# ============================================================
class TestCompareToIndustry:
    def test_above_industry(self):
        result = compare_to_industry(15, 10)
        assert result["评价"] == "高于行业"
        assert result["相对行业"] == 1.5
        assert result["绝对差异"] == 5

    def test_below_industry(self):
        result = compare_to_industry(8, 10)
        assert result["评价"] == "低于行业"
        assert result["相对差异"] == "-20.00%"

    def test_equal_industry(self):
        result = compare_to_industry(10, 10)
        assert result["评价"] == "与行业持平"

    def test_industry_avg_zero(self):
        result = compare_to_industry(10, 0)
        assert result["对比结果"] == "无法计算"

    def test_negative_values(self):
        """公司和行业均为负"""
        result = compare_to_industry(-5, -10)
        assert result["相对行业"] == 0.5


# ============================================================
# 16. generate_chart_data - 图表数据生成
# ============================================================
class TestGenerateChartData:
    def test_normal(self):
        result = generate_chart_data([2021, 2022, 2023], [100, 120, 150])
        assert result["x"] == [2021, 2022, 2023]
        assert result["y"] == [100, 120, 150]
        assert result["metric"] == "指标"
        assert len(result["data_points"]) == 3

    def test_custom_metric_name(self):
        result = generate_chart_data([2021], [100], metric_name="营收")
        assert result["metric"] == "营收"

    def test_mismatched_lengths(self):
        """年份和数值长度不匹配"""
        result = generate_chart_data([2021, 2022], [100])
        assert "error" in result

    def test_empty_lists(self):
        """空列表也是匹配的"""
        result = generate_chart_data([], [])
        assert result["x"] == []
        assert result["y"] == []


# ============================================================
# 17. calculate_avg - 平均值
# ============================================================
class TestCalculateAvg:
    def test_normal(self):
        assert calculate_avg([10, 20, 30]) == 20.0

    def test_with_none(self):
        """包含 None 值应被过滤"""
        assert calculate_avg([10, None, 30]) == 20.0

    def test_empty_list(self):
        assert calculate_avg([]) == "无有效数据"

    def test_all_none(self):
        assert calculate_avg([None, None]) == "无有效数据"

    def test_single_value(self):
        assert calculate_avg([42]) == 42.0

    def test_negative_values(self):
        assert calculate_avg([-10, 10]) == 0.0


# ============================================================
# 18. calculate_max - 最大值
# ============================================================
class TestCalculateMax:
    def test_normal(self):
        assert calculate_max([10, 30, 20]) == 30

    def test_with_none(self):
        assert calculate_max([None, 10, 30]) == 30

    def test_empty_list(self):
        assert calculate_max([]) == "无有效数据"

    def test_all_none(self):
        assert calculate_max([None, None]) == "无有效数据"

    def test_negative_values(self):
        assert calculate_max([-10, -5, -20]) == -5


# ============================================================
# 19. calculate_min - 最小值
# ============================================================
class TestCalculateMin:
    def test_normal(self):
        assert calculate_min([10, 30, 20]) == 10

    def test_with_none(self):
        assert calculate_min([None, 30, 10]) == 10

    def test_empty_list(self):
        assert calculate_min([]) == "无有效数据"

    def test_all_none(self):
        assert calculate_min([None, None]) == "无有效数据"

    def test_negative_values(self):
        assert calculate_min([-5, -10, -20]) == -20


# ============================================================
# 20. calculate_variance - 方差
# ============================================================
class TestCalculateVariance:
    def test_normal(self):
        result = calculate_variance([2, 4, 4, 4, 5, 5, 7, 9])
        assert isinstance(result, float)
        assert result > 0

    def test_zero_variance(self):
        """所有值相同，方差为0"""
        assert calculate_variance([5, 5, 5]) == 0.0

    def test_single_value(self):
        """单个值，数据不足"""
        assert calculate_variance([5]) == "数据不足"

    def test_empty_list(self):
        assert calculate_variance([]) == "数据不足"

    def test_two_values(self):
        """两个值的方差"""
        # 方差 = ((1-2)^2 + (3-2)^2) / 2 = 1.0
        assert calculate_variance([1, 3]) == 1.0

    def test_with_none(self):
        """None 应被过滤"""
        result = calculate_variance([1, None, 3])
        assert result == 1.0

    def test_all_none(self):
        """过滤后不足2个"""
        assert calculate_variance([None, None]) == "数据不足"

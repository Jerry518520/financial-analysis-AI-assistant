from typing import Union

def calculate_growth_rate(current_value: float, previous_value: float) -> Union[float, str]:
    """
    计算同比增长率或环比增长率。
    公式: (本期 - 上期) / |上期|
    """
    if previous_value == 0:
        return "无法计算（分母为0）"
    
    growth = (current_value - previous_value) / abs(previous_value)
    return round(growth, 4)

def calculate_margin(profit: float, revenue: float) -> Union[float, str]:
    """
    计算利润率（毛利率、净利率等）。
    公式: 利润 / 营收
    """
    if revenue == 0:
        return "无法计算（营收为0）"
    
    margin = profit / revenue
    return round(margin, 4)

def calculate_roe(net_income: float, equity: float, beginning_equity: float = None) -> Union[float, str]:
    """
    计算净资产收益率 (ROE)。
    优先使用平均净资产口径: 净利润 / ((期初净资产 + 期末净资产) / 2)
    如果没有期初数据，回退到简化口径: 净利润 / 期末净资产
    """
    if beginning_equity is not None and beginning_equity > 0:
        avg_equity = (beginning_equity + equity) / 2
        if avg_equity == 0:
            return "无法计算（平均净资产为0）"
        roe = net_income / avg_equity
    else:
        if equity == 0:
            return "无法计算（净资产为0）"
        roe = net_income / equity
    return round(roe, 4)

def format_percentage(value: Union[float, str]) -> str:
    """
    将小数格式化为百分比字符串。
    """
    if isinstance(value, str):
        return value
    return f"{value * 100:.2f}%"

def calculate_debt_ratio(total_liabilities: float, total_assets: float) -> Union[float, str]:
    """
    计算资产负债率。
    公式: 负债 / 资产
    """
    if total_assets == 0:
        return "无法计算（总资产为0）"
    debt_ratio = total_liabilities / total_assets
    return round(debt_ratio, 4)

def calculate_current_ratio(current_assets: float, current_liabilities: float) -> Union[float, str]:
    """
    计算流动比率。
    公式: 流动资产 / 流动负债
    """
    if current_liabilities == 0:
        return "无法计算（流动负债为0）"
    current_ratio = current_assets / current_liabilities
    return round(current_ratio, 2)

def calculate_quick_ratio(current_assets: float, inventory: float, current_liabilities: float) -> Union[float, str]:
    """
    计算速动比率。
    公式: (流动资产 - 存货) / 流动负债
    """
    if current_liabilities == 0:
        return "无法计算（流动负债为0）"
    quick_ratio = (current_assets - inventory) / current_liabilities
    return round(quick_ratio, 2)

def calculate_eps(net_income: float, shares_outstanding: float) -> Union[float, str]:
    """
    计算每股收益 (EPS)。
    公式: 净利润 / 股本
    """
    if shares_outstanding == 0:
        return "无法计算（股本为0）"
    eps = net_income / shares_outstanding
    return round(eps, 2)

def calculate_pe(price_per_share: float, eps: float) -> Union[float, str]:
    """
    计算市盈率 (PE)。
    公式: 股价 / 每股收益
    """
    if eps == 0:
        return "无法计算（EPS为0）"
    pe = price_per_share / eps
    return round(pe, 2)

def calculate_turnover(revenue: float, total_assets: float, beginning_total_assets: float = None) -> Union[float, str]:
    """
    计算资产周转率。
    优先使用平均总资产法: 营收 / ((期初总资产 + 期末总资产) / 2)
    无期初数据时回退到简化口径: 营收 / 期末总资产
    """
    if beginning_total_assets is not None and beginning_total_assets > 0:
        avg_assets = (beginning_total_assets + total_assets) / 2
        if avg_assets == 0:
            return "无法计算（平均总资产为0）"
        turnover = revenue / avg_assets
    else:
        if total_assets == 0:
            return "无法计算（总资产为0）"
        turnover = revenue / total_assets
    return round(turnover, 2)

def calculate_inventory_turnover(cogs: float, inventory: float, beginning_inventory: float = None) -> Union[float, str]:
    """
    计算存货周转率。
    优先使用平均存货法: 营业成本 / ((期初存货 + 期末存货) / 2)
    无期初数据时回退到简化口径: 营业成本 / 期末存货
    """
    if beginning_inventory is not None and beginning_inventory > 0:
        avg_inventory = (beginning_inventory + inventory) / 2
        if avg_inventory == 0:
            return "无法计算（平均存货为0）"
        turnover = cogs / avg_inventory
    else:
        if inventory == 0:
            return "无法计算（存货为0）"
        turnover = cogs / inventory
    return round(turnover, 2)

def calculate_receivables_turnover(revenue: float, receivables: float, beginning_receivables: float = None) -> Union[float, str]:
    """
    计算应收账款周转率。
    优先使用平均应收账款法: 营业收入 / ((期初应收账款 + 期末应收账款) / 2)
    无期初数据时回退到简化口径: 营业收入 / 期末应收账款
    """
    if beginning_receivables is not None and beginning_receivables > 0:
        avg_receivables = (beginning_receivables + receivables) / 2
        if avg_receivables == 0:
            return "无法计算（平均应收账款为0）"
        turnover = revenue / avg_receivables
    else:
        if receivables == 0:
            return "无法计算（应收账款为0）"
        turnover = revenue / receivables
    return round(turnover, 2)


def calculate_dividend_yield(dividend_per_share: float, price_per_share: float) -> Union[float, str]:
    """
    计算股息率。
    公式: 每股股息 / 股价
    """
    if price_per_share == 0:
        return "无法计算（股价为0）"
    yield_rate = dividend_per_share / price_per_share
    return round(yield_rate, 4)

def analyze_trend(values: list) -> dict:
    """
    分析趋势（支持多年数据）。
    输入: [2021年, 2022年, 2023年] 格式的数值列表
    输出: 趋势分析结果
    """
    if len(values) < 2:
        return {"趋势": "数据不足", "年均增长率": "需要至少2年数据"}
    
    # 只过滤 None，保留 0（0 是合法的财务数据，如某年利润为零）
    valid_values = [v for v in values if v is not None]
    if len(valid_values) < 2:
        return {"趋势": "数据不足", "年均增长率": "有效数据不足"}
    
    first = valid_values[0]
    last = valid_values[-1]
    years = len(valid_values) - 1
    
    # first 为 0 时 CAGR 无法计算（除零），用总变化量替代
    if first == 0:
        cagr = 0 if last == 0 else None
    else:
        cagr = (last / first) ** (1 / years) - 1 if years > 0 else 0
    
    trend_direction = "上升" if last > first else "下降" if last < first else "持平"
    
    result = {
        "首年数值": first,
        "末年数值": last,
        "趋势方向": trend_direction,
        "总年数": years + 1,
    }
    
    if cagr is not None:
        result["年均增长率(CAGR)"] = round(cagr, 4)
    else:
        result["年均增长率(CAGR)"] = "无法计算（首年数值为0）"
    
    result["总变化幅度"] = round((last - first) / abs(first) * 100, 2) if first != 0 else (round(last * 100, 2) if last != 0 else 0)
    
    return result

def analyze_yoy(current: float, previous: float) -> dict:
    """
    同比分析。
    输入: 本期值和上期值
    输出: 同比分析结果
    """
    if previous == 0:
        return {"变化": "无法计算", "同比增长率": "上期数据为0"}
    
    yoy_growth = (current - previous) / abs(previous)
    absolute_change = current - previous
    
    return {
        "本期数值": current,
        "上期数值": previous,
        "同比增长率": round(yoy_growth, 4),
        "绝对变化量": round(absolute_change, 2),
        "增长类型": "增长" if yoy_growth > 0 else "下降" if yoy_growth < 0 else "持平"
    }

def compare_to_industry(value: float, industry_avg: float) -> dict:
    """
    与行业平均水平对比。
    输入: 公司数值和行业平均值
    输出: 对比结果
    """
    if industry_avg == 0:
        return {"对比结果": "无法计算", "差异": "行业平均值为0"}

    ratio = value / industry_avg
    difference = value - industry_avg
    percentage_diff = (value - industry_avg) / abs(industry_avg) * 100

    return {
        "公司数值": value,
        "行业平均": industry_avg,
        "相对行业": round(ratio, 2),
        "绝对差异": round(difference, 2),
        "相对差异": f"{percentage_diff:+.2f}%",
        "评价": "高于行业" if ratio > 1 else "低于行业" if ratio < 1 else "与行业持平"
    }


# ==================== 行业基准数据库（SASAC 五档参考值） ====================
# 基于国资委《企业绩效评价标准值》的五档评分体系：
#   优秀值 → 100分, 良好值 → 80分, 平均值 → 60分, 较低值 → 40分, 较差值 → 20分
# 相邻档位之间做线性插值。
# 数据来源：公开市场数据近似参考值，非权威数据源。如需精确数据，请接入 Wind/国泰安等专业数据源。

# 五档参考值结构: (较差, 较低, 平均, 良好, 优秀)
# 对应分数:       (20,   40,   60,   80,   100)

def _v(poor, low, avg, good, excellent):
    """辅助函数：构造五档参考值元组。"""
    return (poor, low, avg, good, excellent)

INDUSTRY_BENCHMARKS = {
    "制造业": {
        "毛利率":            _v(0.12, 0.18, 0.25, 0.32, 0.40),
        "净利率":            _v(0.02, 0.05, 0.08, 0.12, 0.18),
        "ROE":               _v(0.03, 0.06, 0.10, 0.15, 0.22),
        "营业利润率":         _v(0.03, 0.06, 0.10, 0.15, 0.22),
        "成本费用利润率":      _v(0.04, 0.08, 0.12, 0.18, 0.25),
        "资产负债率":         _v(0.75, 0.65, 0.50, 0.40, 0.30),  # 反向：越低越好
        "流动比率":           _v(0.80, 1.10, 1.50, 2.00, 2.50),
        "速动比率":           _v(0.50, 0.70, 1.00, 1.40, 1.80),
        "利息保障倍数":       _v(1.5, 3.0, 5.0, 8.0, 12.0),
        "现金流动负债比":      _v(0.08, 0.15, 0.25, 0.35, 0.45),
        "资产周转率":          _v(0.40, 0.60, 0.80, 1.00, 1.30),
        "存货周转率":          _v(2.0, 3.0, 4.0, 6.0, 8.0),
        "应收账款周转率":      _v(3.0, 5.0, 6.0, 9.0, 15.0),
        "现金回收率":          _v(0.04, 0.07, 0.10, 0.14, 0.20),
        "营收增长率":          _v(-0.05, 0.02, 0.08, 0.15, 0.25),
        "净利润增长率":        _v(-0.10, 0.00, 0.08, 0.18, 0.30),
        "总资产增长率":        _v(0.00, 0.05, 0.10, 0.18, 0.28),
        "资本保值增值率":      _v(0.95, 1.02, 1.10, 1.18, 1.30),
    },
    "科技/互联网": {
        "毛利率":            _v(0.25, 0.35, 0.45, 0.55, 0.70),
        "净利率":            _v(0.03, 0.08, 0.15, 0.22, 0.30),
        "ROE":               _v(0.04, 0.08, 0.12, 0.18, 0.25),
        "营业利润率":         _v(0.05, 0.10, 0.18, 0.25, 0.35),
        "成本费用利润率":      _v(0.06, 0.12, 0.20, 0.28, 0.40),
        "资产负债率":         _v(0.65, 0.55, 0.40, 0.30, 0.20),
        "流动比率":           _v(1.00, 1.50, 2.00, 2.50, 3.50),
        "速动比率":           _v(0.80, 1.20, 1.80, 2.30, 3.00),
        "利息保障倍数":       _v(3.0, 5.0, 8.0, 12.0, 20.0),
        "现金流动负债比":      _v(0.10, 0.18, 0.30, 0.42, 0.55),
        "资产周转率":          _v(0.30, 0.45, 0.60, 0.80, 1.10),
        "存货周转率":          _v(5.0, 8.0, 10.0, 15.0, 25.0),
        "应收账款周转率":      _v(4.0, 6.0, 8.0, 12.0, 20.0),
        "现金回收率":          _v(0.05, 0.08, 0.12, 0.18, 0.25),
        "营收增长率":          _v(0.00, 0.08, 0.15, 0.25, 0.40),
        "净利润增长率":        _v(-0.05, 0.05, 0.15, 0.30, 0.50),
        "总资产增长率":        _v(0.02, 0.08, 0.15, 0.25, 0.40),
        "资本保值增值率":      _v(0.98, 1.05, 1.15, 1.25, 1.40),
    },
    "金融业": {
        "毛利率":            None,  # 金融业不适用
        "净利率":            _v(0.10, 0.20, 0.30, 0.38, 0.45),
        "ROE":               _v(0.04, 0.07, 0.11, 0.15, 0.20),
        "营业利润率":         _v(0.15, 0.25, 0.35, 0.42, 0.50),
        "成本费用利润率":      None,
        "资产负债率":         _v(0.95, 0.92, 0.90, 0.87, 0.82),  # 金融业特殊，负债率天然高
        "流动比率":           None,
        "速动比率":           None,
        "利息保障倍数":       None,
        "现金流动负债比":      None,
        "资产周转率":          _v(0.01, 0.02, 0.03, 0.05, 0.08),
        "存货周转率":          None,
        "应收账款周转率":      None,
        "现金回收率":          None,
        "营收增长率":          _v(-0.02, 0.03, 0.08, 0.14, 0.22),
        "净利润增长率":        _v(-0.05, 0.00, 0.06, 0.12, 0.20),
        "总资产增长率":        _v(0.03, 0.06, 0.10, 0.16, 0.25),
        "资本保值增值率":      _v(0.97, 1.03, 1.08, 1.14, 1.22),
    },
    "零售/消费品": {
        "毛利率":            _v(0.15, 0.22, 0.30, 0.38, 0.48),
        "净利率":            _v(0.01, 0.03, 0.05, 0.08, 0.12),
        "ROE":               _v(0.04, 0.08, 0.12, 0.17, 0.24),
        "营业利润率":         _v(0.02, 0.04, 0.06, 0.10, 0.15),
        "成本费用利润率":      _v(0.02, 0.04, 0.07, 0.11, 0.16),
        "资产负债率":         _v(0.75, 0.65, 0.55, 0.45, 0.35),
        "流动比率":           _v(0.70, 1.00, 1.30, 1.70, 2.20),
        "速动比率":           _v(0.35, 0.55, 0.80, 1.10, 1.50),
        "利息保障倍数":       _v(2.0, 3.0, 4.0, 6.0, 10.0),
        "现金流动负债比":      _v(0.08, 0.13, 0.20, 0.28, 0.38),
        "资产周转率":          _v(0.60, 0.90, 1.20, 1.50, 2.00),
        "存货周转率":          _v(3.0, 4.5, 6.0, 8.0, 12.0),
        "应收账款周转率":      _v(5.0, 8.0, 10.0, 14.0, 20.0),
        "现金回收率":          _v(0.03, 0.05, 0.08, 0.12, 0.18),
        "营收增长率":          _v(-0.03, 0.03, 0.10, 0.18, 0.28),
        "净利润增长率":        _v(-0.08, 0.02, 0.10, 0.20, 0.35),
        "总资产增长率":        _v(0.00, 0.05, 0.10, 0.18, 0.28),
        "资本保值增值率":      _v(0.95, 1.02, 1.10, 1.18, 1.30),
    },
    "能源": {
        "毛利率":            _v(0.08, 0.14, 0.20, 0.28, 0.38),
        "净利率":            _v(0.01, 0.03, 0.06, 0.10, 0.16),
        "ROE":               _v(0.02, 0.05, 0.09, 0.14, 0.20),
        "营业利润率":         _v(0.02, 0.05, 0.08, 0.13, 0.20),
        "成本费用利润率":      _v(0.03, 0.06, 0.10, 0.15, 0.22),
        "资产负债率":         _v(0.75, 0.65, 0.55, 0.45, 0.35),
        "流动比率":           _v(0.60, 0.90, 1.20, 1.60, 2.00),
        "速动比率":           _v(0.40, 0.65, 0.90, 1.20, 1.60),
        "利息保障倍数":       _v(1.5, 2.5, 4.0, 6.0, 10.0),
        "现金流动负债比":      _v(0.08, 0.13, 0.20, 0.28, 0.38),
        "资产周转率":          _v(0.35, 0.50, 0.70, 0.90, 1.20),
        "存货周转率":          _v(4.0, 6.0, 8.0, 11.0, 16.0),
        "应收账款周转率":      _v(2.5, 4.0, 5.0, 7.0, 12.0),
        "现金回收率":          _v(0.04, 0.07, 0.10, 0.14, 0.20),
        "营收增长率":          _v(-0.08, -0.02, 0.05, 0.12, 0.20),
        "净利润增长率":        _v(-0.15, -0.05, 0.05, 0.15, 0.28),
        "总资产增长率":        _v(-0.02, 0.03, 0.08, 0.14, 0.22),
        "资本保值增值率":      _v(0.93, 0.98, 1.06, 1.14, 1.25),
    },
    "医药": {
        "毛利率":            _v(0.30, 0.42, 0.55, 0.65, 0.78),
        "净利率":            _v(0.03, 0.07, 0.12, 0.18, 0.25),
        "ROE":               _v(0.04, 0.08, 0.13, 0.19, 0.26),
        "营业利润率":         _v(0.05, 0.10, 0.15, 0.22, 0.30),
        "成本费用利润率":      _v(0.06, 0.11, 0.18, 0.25, 0.35),
        "资产负债率":         _v(0.60, 0.50, 0.35, 0.25, 0.18),
        "流动比率":           _v(1.20, 1.70, 2.20, 2.80, 3.50),
        "速动比率":           _v(0.80, 1.30, 1.80, 2.30, 3.00),
        "利息保障倍数":       _v(3.0, 5.0, 8.0, 12.0, 20.0),
        "现金流动负债比":      _v(0.10, 0.18, 0.30, 0.42, 0.55),
        "资产周转率":          _v(0.25, 0.38, 0.50, 0.65, 0.85),
        "存货周转率":          _v(1.5, 2.5, 3.5, 5.0, 7.0),
        "应收账款周转率":      _v(2.5, 4.0, 5.0, 7.0, 10.0),
        "现金回收率":          _v(0.05, 0.08, 0.12, 0.17, 0.24),
        "营收增长率":          _v(0.00, 0.06, 0.12, 0.20, 0.32),
        "净利润增长率":        _v(-0.05, 0.05, 0.15, 0.25, 0.40),
        "总资产增长率":        _v(0.02, 0.06, 0.12, 0.20, 0.32),
        "资本保值增值率":      _v(0.97, 1.04, 1.12, 1.22, 1.35),
    },
    "房地产": {
        "毛利率":            _v(0.10, 0.16, 0.22, 0.30, 0.40),
        "净利率":            _v(0.02, 0.05, 0.08, 0.12, 0.18),
        "ROE":               _v(0.03, 0.06, 0.10, 0.15, 0.22),
        "营业利润率":         _v(0.03, 0.06, 0.10, 0.15, 0.22),
        "成本费用利润率":      _v(0.04, 0.08, 0.12, 0.17, 0.24),
        "资产负债率":         _v(0.82, 0.75, 0.70, 0.60, 0.50),  # 房地产负债率天然高
        "流动比率":           _v(0.80, 1.00, 1.30, 1.60, 2.00),
        "速动比率":           _v(0.25, 0.38, 0.50, 0.70, 1.00),
        "利息保障倍数":       _v(1.2, 2.0, 3.0, 5.0, 8.0),
        "现金流动负债比":      _v(0.03, 0.06, 0.10, 0.16, 0.25),
        "资产周转率":          _v(0.10, 0.18, 0.25, 0.35, 0.50),
        "存货周转率":          _v(0.20, 0.35, 0.50, 0.80, 1.20),
        "应收账款周转率":      _v(4.0, 6.0, 8.0, 12.0, 18.0),
        "现金回收率":          _v(0.02, 0.03, 0.05, 0.08, 0.12),
        "营收增长率":          _v(-0.10, -0.03, 0.05, 0.12, 0.22),
        "净利润增长率":        _v(-0.15, -0.05, 0.05, 0.15, 0.28),
        "总资产增长率":        _v(-0.03, 0.02, 0.08, 0.15, 0.25),
        "资本保值增值率":      _v(0.93, 0.98, 1.05, 1.12, 1.22),
    },
}


def get_industry_benchmark(industry: str, metric: str) -> tuple | None:
    """查询行业五档参考值。返回 (较差, 较低, 平均, 良好, 优秀) 元组，或 None。
    注意：数据为近似参考值，非权威数据源，仅供方向性对比。"""
    industry_data = INDUSTRY_BENCHMARKS.get(industry)
    if not industry_data:
        return None
    return industry_data.get(metric)


def list_industries() -> list:
    """返回所有可用行业列表"""
    return list(INDUSTRY_BENCHMARKS.keys())


def list_industry_metrics(industry: str) -> dict:
    """返回某行业的所有基准指标"""
    return INDUSTRY_BENCHMARKS.get(industry, {})

def generate_chart_data(years: list, values: list, metric_name: str = "指标") -> dict:
    """
    生成图表数据（用于前端可视化）。
    输入: 年份列表和数值列表
    输出: 可用于图表的数据
    """
    if len(years) != len(values):
        return {"error": "年份和数值数量不匹配"}
    
    chart_data = {
        "x": years,
        "y": values,
        "metric": metric_name,
        "labels": [f"{y}" for y in years],
        "data_points": [{"x": y, "value": v} for y, v in zip(years, values)]
    }
    
    return chart_data

def calculate_avg(values: list) -> Union[float, str]:
    """
    计算平均值。
    """
    valid = [v for v in values if v is not None]
    if not valid:
        return "无有效数据"
    return round(sum(valid) / len(valid), 2)

def calculate_max(values: list) -> Union[float, str]:
    """
    计算最大值。
    """
    valid = [v for v in values if v is not None]
    if not valid:
        return "无有效数据"
    return max(valid)

def calculate_min(values: list) -> Union[float, str]:
    """
    计算最小值。
    """
    valid = [v for v in values if v is not None]
    if not valid:
        return "无有效数据"
    return min(valid)

def calculate_variance(values: list) -> Union[float, str]:
    """
    计算方差（衡量波动性）。
    """
    valid = [v for v in values if v is not None]
    if len(valid) < 2:
        return "数据不足"
    
    avg = sum(valid) / len(valid)
    variance = sum((x - avg) ** 2 for x in valid) / len(valid)
    return round(variance, 4)


# ==================== 能力雷达图评分系统 ====================
# 参考：国资委企业绩效评价标准 + CFA 财务分析框架 + Altman Z-Score

DIMENSION_DEFINITIONS = {
    "盈利能力": {
        "metrics": ["毛利率", "净利率", "ROE", "营业利润率", "成本费用利润率"],
        "inverted": set(),
        "weight": 0.30,
    },
    "资产质量": {
        "metrics": ["资产周转率", "存货周转率", "应收账款周转率", "现金回收率"],
        "inverted": set(),
        "weight": 0.20,
    },
    "债务风险": {
        "metrics": ["资产负债率", "流动比率", "速动比率", "利息保障倍数", "现金流动负债比"],
        "inverted": {"资产负债率"},
        "weight": 0.20,
    },
    "经营增长": {
        "metrics": ["营收增长率", "净利润增长率", "总资产增长率", "资本保值增值率"],
        "inverted": set(),
        "weight": 0.30,
    },
}

# SASAC 五档评级
GRADE_THRESHOLDS = [
    (85, "优秀", "A"),
    (70, "良好", "B"),
    (50, "平均", "C"),
    (30, "较低", "D"),
    (0,  "较差", "E"),
]


def score_to_grade(score: float) -> str:
    """将 0-100 分转换为 SASAC 五档评级。"""
    for threshold, label, letter in GRADE_THRESHOLDS:
        if score >= threshold:
            return letter
    return "E"


def score_to_label(score: float) -> str:
    """将 0-100 分转换为中文评级标签。"""
    for threshold, label, letter in GRADE_THRESHOLDS:
        if score >= threshold:
            return label
    return "较差"


def score_metric(company_value: float, benchmark_levels: tuple, inverted: bool = False) -> float:
    """SASAC 五档插值评分法。

    benchmark_levels: (较差值, 较低值, 平均值, 良好值, 优秀值)
    对应分数:          (20,     40,     60,     80,     100)

    在相邻档位之间做线性插值。
    反向指标（如资产负债率）：值越低分数越高。
    """
    SCORES = (20, 40, 60, 80, 100)

    if benchmark_levels is None or company_value is None:
        return 50.0

    poor, low, avg, good, excellent = benchmark_levels
    levels = [poor, low, avg, good, excellent]

    # 反向指标：值越低越好，翻转比较方向
    if inverted:
        levels = levels[::-1]  # 翻转档位顺序

    # 确定公司值落在哪两个档位之间
    # 正向：值越高分越高 → levels 从小到大
    # 反向：翻转后 levels 从小到大（实际是原值从大到小）
    if company_value <= levels[0]:
        return 20.0
    if company_value >= levels[4]:
        return 100.0

    # 找到所在区间，线性插值
    for i in range(4):
        if levels[i] <= company_value <= levels[i + 1]:
            if levels[i + 1] == levels[i]:
                return float(SCORES[i])
            ratio = (company_value - levels[i]) / (levels[i + 1] - levels[i])
            return round(SCORES[i] + ratio * (SCORES[i + 1] - SCORES[i]), 1)

    return 50.0  # 兜底


def score_dimension(metrics: dict, benchmarks: dict, inverted_metrics: set = None) -> tuple:
    """评分一个能力维度。

    benchmarks: {指标名: (较差, 较低, 平均, 良好, 优秀)} 五档参考值
    Returns: (dimension_score, detail_list)
    """
    if inverted_metrics is None:
        inverted_metrics = set()

    detail = []
    scores = []

    for name, company_val in metrics.items():
        if company_val is None:
            continue
        benchmark_levels = benchmarks.get(name)
        if benchmark_levels is None:
            continue
        inverted = name in inverted_metrics
        s = score_metric(company_val, benchmark_levels, inverted)
        scores.append(s)
        # 展示用：取平均值（第3档）作为参考值显示
        avg_val = benchmark_levels[2] if isinstance(benchmark_levels, tuple) and len(benchmark_levels) == 5 else benchmark_levels
        detail.append({
            "name": name,
            "company": company_val,
            "benchmark": avg_val,
            "score": s,
        })

    if not scores:
        return 50.0, detail

    return round(sum(scores) / len(scores), 1), detail


def compute_altman_z_score(metrics: dict) -> dict | None:
    """计算 Altman Z-Score 破产风险指标（适用于上市制造业）。

    Z = 1.2*X1 + 1.4*X2 + 3.3*X3 + 0.6*X4 + 1.0*X5
    X1 = 营运资本 / 总资产
    X2 = 留存收益 / 总资产
    X3 = 息税前利润 / 总资产
    X4 = 权益市值 / 负债总额
    X5 = 营业收入 / 总资产

    返回 None 表示数据不足无法计算。
    """
    required = ["营运资本比", "留存收益比", "EBIT资产比", "权益负债比", "资产周转率"]
    vals = {}
    for k in required:
        v = metrics.get(k)
        if v is None:
            return None
        vals[k] = v

    z = (1.2 * vals["营运资本比"]
         + 1.4 * vals["留存收益比"]
         + 3.3 * vals["EBIT资产比"]
         + 0.6 * vals["权益负债比"]
         + 1.0 * vals["资产周转率"])

    z = round(z, 2)
    if z > 2.99:
        zone = "安全"
    elif z > 1.81:
        zone = "灰色"
    else:
        zone = "危险"

    return {"z_score": z, "zone": zone}


def compute_radar_scores(company_metrics: dict, industry: str) -> dict:
    """计算能力雷达图的各维度评分和综合评分（加权）。

    参考国资委企业绩效评价标准，4 维度加权：
    - 盈利能力 30%
    - 资产质量 20%
    - 债务风险 20%
    - 经营增长 30%

    company_metrics: {"毛利率": 0.25, "净利率": 0.08, ...}
    industry: 行业名称，如"制造业"
    """
    benchmarks = INDUSTRY_BENCHMARKS.get(industry, {})

    dimensions = []
    for dim_name, dim_def in DIMENSION_DEFINITIONS.items():
        dim_metrics = {
            k: company_metrics.get(k)
            for k in dim_def["metrics"]
        }
        dim_benchmarks = {
            k: benchmarks.get(k)
            for k in dim_def["metrics"]
        }
        dim_score, detail = score_dimension(dim_metrics, dim_benchmarks, dim_def["inverted"])

        dimensions.append({
            "name": dim_name,
            "weight": dim_def["weight"],
            "score": dim_score,
            "grade": score_to_grade(dim_score),
            "label": score_to_label(dim_score),
            "detail": detail,
        })

    # 加权综合评分
    weighted_sum = 0.0
    total_weight = 0.0
    for d in dimensions:
        weighted_sum += d["score"] * d["weight"]
        total_weight += d["weight"]
    composite = round(weighted_sum / total_weight, 1) if total_weight > 0 else 50.0

    # Altman Z-Score（附加参考）
    z_score = compute_altman_z_score(company_metrics)

    return {
        "dimensions": dimensions,
        "composite_score": composite,
        "composite_grade": score_to_grade(composite),
        "composite_label": score_to_label(composite),
        "industry": industry,
        "z_score": z_score,
    }

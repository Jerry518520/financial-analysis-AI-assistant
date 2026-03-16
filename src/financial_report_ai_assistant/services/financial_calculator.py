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

def calculate_roe(net_income: float, equity: float) -> Union[float, str]:
    """
    计算净资产收益率 (ROE)。
    公式: 净利润 / 净资产
    """
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

def calculate_turnover(revenue: float, total_assets: float) -> Union[float, str]:
    """
    计算资产周转率。
    公式: 营收 / 总资产
    """
    if total_assets == 0:
        return "无法计算（总资产为0）"
    turnover = revenue / total_assets
    return round(turnover, 2)

def calculate_inventory_turnover(cogs: float, inventory: float) -> Union[float, str]:
    """
    计算存货周转率。
    公式: 营业成本 / 存货
    """
    if inventory == 0:
        return "无法计算（存货为0）"
    turnover = cogs / inventory
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
    
    valid_values = [v for v in values if v is not None and v != 0]
    if len(valid_values) < 2:
        return {"趋势": "数据不足", "年均增长率": "有效数据不足"}
    
    first = valid_values[0]
    last = valid_values[-1]
    years = len(valid_values) - 1
    
    cagr = (last / first) ** (1 / years) - 1 if years > 0 else 0
    
    trend_direction = "上升" if last > first else "下降" if last < first else "持平"
    
    return {
        "首年数值": first,
        "末年数值": last,
        "趋势方向": trend_direction,
        "年均增长率(CAGR)": round(cagr, 4),
        "总变化幅度": round((last - first) / abs(first) * 100, 2) if first != 0 else 0
    }

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

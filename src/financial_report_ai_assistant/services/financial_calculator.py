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

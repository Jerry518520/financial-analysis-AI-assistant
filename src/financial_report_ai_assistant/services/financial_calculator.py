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

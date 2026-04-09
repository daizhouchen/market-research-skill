"""
趋势分析器

分析 Google Trends 时间序列数据，输出趋势方向、增长率、加速度、季节性和机会关键词。
使用 numpy 进行线性回归和统计计算，不依赖 ML 库。
"""

import numpy as np
from datetime import datetime
from typing import Any
from collections import defaultdict


def analyze_trend(data: list[dict[str, Any]], rising_queries: list[dict[str, Any]] | None = None) -> dict:
    """
    分析趋势数据。

    Args:
        data: 时间序列数据，每条记录包含 {date: str, value: float}。
              date 格式为 'YYYY-MM-DD' 或 'YYYY-MM'。
        rising_queries: 上升查询列表，每条包含 {query: str, growth: float}。
                        growth 为百分比增长率。

    Returns:
        分析结果字典，包含 direction, growth_rate, acceleration, seasonality, opportunity_keywords。
    """
    if not data:
        return _empty_result()

    # 解析数据
    dates, values = _parse_data(data)
    if len(values) < 2:
        return _empty_result()

    values = np.array(values, dtype=float)
    n = len(values)

    # 趋势方向：线性回归
    direction, slope = _compute_direction(values)

    # 增长率：最后3个月均值 / 最初3个月均值 - 1
    growth_rate = _compute_growth_rate(values)

    # 加速度：比较前半段和后半段的斜率
    acceleration = _compute_acceleration(values)

    # 季节性分析
    seasonality = _compute_seasonality(dates, values)

    # 机会关键词
    opportunity_keywords = _filter_opportunity_keywords(rising_queries)

    return {
        "direction": direction,
        "growth_rate": round(growth_rate, 4),
        "acceleration": round(acceleration, 4),
        "seasonality": seasonality,
        "opportunity_keywords": opportunity_keywords,
    }


def _empty_result() -> dict:
    """返回空数据时的默认结果。"""
    return {
        "direction": "stable",
        "growth_rate": 0.0,
        "acceleration": 0.0,
        "seasonality": {"exists": False, "peak_months": [], "trough_months": []},
        "opportunity_keywords": [],
    }


def _parse_data(data: list[dict]) -> tuple[list[datetime], list[float]]:
    """解析日期和数值，跳过无效记录。"""
    dates = []
    values = []
    for item in data:
        try:
            date_str = str(item.get("date", ""))
            value = float(item.get("value", 0))
            # 尝试多种日期格式
            for fmt in ("%Y-%m-%d", "%Y-%m", "%Y/%m/%d", "%Y/%m"):
                try:
                    dt = datetime.strptime(date_str, fmt)
                    dates.append(dt)
                    values.append(value)
                    break
                except ValueError:
                    continue
        except (TypeError, ValueError):
            continue
    return dates, values


def _compute_direction(values: np.ndarray) -> tuple[str, float]:
    """
    通过线性回归计算趋势方向。

    返回 (方向字符串, 斜率)。
    斜率 > 均值的 5% 判定为增长，< -5% 判定为下降，否则稳定。
    """
    n = len(values)
    x = np.arange(n, dtype=float)
    # 最小二乘线性回归: y = slope * x + intercept
    x_mean = x.mean()
    y_mean = values.mean()
    slope = np.sum((x - x_mean) * (values - y_mean)) / np.sum((x - x_mean) ** 2) if np.sum((x - x_mean) ** 2) > 0 else 0.0

    # 用斜率相对于均值的比例判断方向
    if y_mean == 0:
        direction = "stable"
    else:
        relative_change = (slope * n) / y_mean  # 整个周期的相对变化
        if relative_change > 0.1:
            direction = "growing"
        elif relative_change < -0.1:
            direction = "declining"
        else:
            direction = "stable"

    return direction, float(slope)


def _compute_growth_rate(values: np.ndarray) -> float:
    """
    计算增长率：最后3个月均值 / 最初3个月均值 - 1。
    如果数据不足3个点，取所有可用数据。
    """
    n = len(values)
    window = min(3, n // 2) if n >= 2 else 1

    first_avg = values[:window].mean()
    last_avg = values[-window:].mean()

    if first_avg == 0:
        return 0.0 if last_avg == 0 else float("inf")

    return float(last_avg / first_avg - 1)


def _compute_acceleration(values: np.ndarray) -> float:
    """
    计算加速度：比较后半段和前半段的回归斜率之差。
    正值表示加速增长，负值表示减速。
    """
    n = len(values)
    if n < 4:
        return 0.0

    mid = n // 2
    first_half = values[:mid]
    second_half = values[mid:]

    slope_first = _linear_slope(first_half)
    slope_second = _linear_slope(second_half)

    return float(slope_second - slope_first)


def _linear_slope(values: np.ndarray) -> float:
    """计算一组数据的线性回归斜率。"""
    n = len(values)
    if n < 2:
        return 0.0
    x = np.arange(n, dtype=float)
    x_mean = x.mean()
    y_mean = values.mean()
    denominator = np.sum((x - x_mean) ** 2)
    if denominator == 0:
        return 0.0
    return float(np.sum((x - x_mean) * (values - y_mean)) / denominator)


def _compute_seasonality(dates: list[datetime], values: np.ndarray) -> dict:
    """
    季节性分析：按月聚合，如果月度变异系数 > 0.3 则认为存在季节性。
    """
    if len(dates) < 12:
        return {"exists": False, "peak_months": [], "trough_months": []}

    monthly_values = defaultdict(list)
    for dt, val in zip(dates, values):
        monthly_values[dt.month].append(val)

    # 计算每月均值
    monthly_avg = {}
    for month, vals in monthly_values.items():
        monthly_avg[month] = np.mean(vals)

    if not monthly_avg:
        return {"exists": False, "peak_months": [], "trough_months": []}

    avg_values = np.array(list(monthly_avg.values()))
    overall_mean = avg_values.mean()

    if overall_mean == 0:
        return {"exists": False, "peak_months": [], "trough_months": []}

    # 变异系数 (CV)
    cv = float(avg_values.std() / overall_mean)
    exists = cv > 0.3

    if not exists:
        return {"exists": False, "peak_months": [], "trough_months": []}

    # 找出峰值月和低谷月（高于/低于均值一个标准差）
    std = avg_values.std()
    peak_months = sorted([m for m, v in monthly_avg.items() if v > overall_mean + std * 0.5])
    trough_months = sorted([m for m, v in monthly_avg.items() if v < overall_mean - std * 0.5])

    return {
        "exists": True,
        "peak_months": peak_months,
        "trough_months": trough_months,
    }


def _filter_opportunity_keywords(rising_queries: list[dict] | None) -> list[dict]:
    """
    筛选增长率超过 100% 的上升查询作为机会关键词。
    """
    if not rising_queries:
        return []

    opportunities = []
    for query in rising_queries:
        try:
            growth = float(query.get("growth", 0))
            keyword = str(query.get("query", ""))
            if growth > 100 and keyword:
                opportunities.append({"query": keyword, "growth": growth})
        except (TypeError, ValueError):
            continue

    # 按增长率降序排列
    opportunities.sort(key=lambda x: x["growth"], reverse=True)
    return opportunities


# ============================================================
# 独立运行示例
# ============================================================
if __name__ == "__main__":
    # 模拟12个月的趋势数据
    sample_data = [
        {"date": "2025-01", "value": 30},
        {"date": "2025-02", "value": 35},
        {"date": "2025-03", "value": 28},
        {"date": "2025-04", "value": 45},
        {"date": "2025-05", "value": 50},
        {"date": "2025-06", "value": 42},
        {"date": "2025-07", "value": 55},
        {"date": "2025-08", "value": 60},
        {"date": "2025-09", "value": 48},
        {"date": "2025-10", "value": 65},
        {"date": "2025-11", "value": 70},
        {"date": "2025-12", "value": 75},
    ]

    sample_rising = [
        {"query": "智能家居控制", "growth": 250},
        {"query": "AI 助手", "growth": 180},
        {"query": "普通搜索", "growth": 50},
    ]

    result = analyze_trend(sample_data, sample_rising)

    print("=== 趋势分析结果 ===")
    print(f"方向: {result['direction']}")
    print(f"增长率: {result['growth_rate']:.2%}")
    print(f"加速度: {result['acceleration']:.4f}")
    print(f"季节性: {result['seasonality']}")
    print(f"机会关键词: {result['opportunity_keywords']}")

"""
价格分析器

分析产品价格分布，识别甜点价位、价格空白和价格与评分的关联。
"""

import numpy as np
from typing import Any


def analyze_pricing(products: list[dict[str, Any]], num_buckets: int = 10) -> dict:
    """
    分析产品价格数据。

    Args:
        products: 产品列表，每条记录包含:
                  - price: float, 价格（必需）
                  - rating: float, 评分（可选）
                  - name: str, 产品名称（可选）
        num_buckets: 价格分段数量，默认 10。

    Returns:
        分析结果字典，包含 price_range, distribution, sweet_spot, gaps, premium_correlation。
    """
    if not products:
        return _empty_result()

    # 提取有效价格
    prices = []
    ratings = []
    price_rating_pairs = []

    for p in products:
        price = _safe_float(p.get("price"))
        if price is None or price <= 0:
            continue
        prices.append(price)

        rating = _safe_float(p.get("rating"))
        if rating is not None and rating > 0:
            ratings.append(rating)
            price_rating_pairs.append((price, rating))

    if not prices:
        return _empty_result()

    prices_arr = np.array(prices)

    # 价格范围
    price_range = _compute_price_range(prices_arr)

    # 价格分布
    distribution = _compute_distribution(prices_arr, ratings, price_rating_pairs, num_buckets)

    # 甜点价位（最密集的价格段）
    sweet_spot = _find_sweet_spot(distribution)

    # 价格空白
    gaps = _find_price_gaps(distribution)

    # 价格与评分的相关性
    premium_correlation = _compute_premium_correlation(price_rating_pairs)

    return {
        "price_range": price_range,
        "distribution": distribution,
        "sweet_spot": sweet_spot,
        "gaps": gaps,
        "premium_correlation": premium_correlation,
    }


def _empty_result() -> dict:
    """返回空数据时的默认结果。"""
    return {
        "price_range": {"min": 0, "max": 0, "median": 0, "mean": 0},
        "distribution": [],
        "sweet_spot": None,
        "gaps": [],
        "premium_correlation": {"coefficient": 0.0, "interpretation": "数据不足"},
    }


def _compute_price_range(prices: np.ndarray) -> dict:
    """计算价格范围统计量。"""
    return {
        "min": round(float(prices.min()), 2),
        "max": round(float(prices.max()), 2),
        "median": round(float(np.median(prices)), 2),
        "mean": round(float(prices.mean()), 2),
    }


def _compute_distribution(
    prices: np.ndarray,
    ratings: list[float],
    price_rating_pairs: list[tuple[float, float]],
    num_buckets: int,
) -> list[dict]:
    """
    计算价格分布：将价格范围分为若干桶，统计每桶的产品数和平均评分。
    """
    p_min, p_max = float(prices.min()), float(prices.max())

    if p_max == p_min:
        return [{
            "bucket": f"{p_min:.0f}",
            "low": p_min,
            "high": p_max,
            "count": len(prices),
            "avg_rating": round(float(np.mean(ratings)), 2) if ratings else None,
        }]

    bucket_width = (p_max - p_min) / num_buckets
    distribution = []

    for i in range(num_buckets):
        low = p_min + i * bucket_width
        high = low + bucket_width
        # 最后一个桶包含右边界
        if i == num_buckets - 1:
            mask = (prices >= low) & (prices <= high)
        else:
            mask = (prices >= low) & (prices < high)

        count = int(mask.sum())

        # 计算该桶内的平均评分
        bucket_ratings = [r for p, r in price_rating_pairs if (low <= p < high) or (i == num_buckets - 1 and p == high)]
        avg_rating = round(float(np.mean(bucket_ratings)), 2) if bucket_ratings else None

        distribution.append({
            "bucket": f"{low:.0f}-{high:.0f}",
            "low": round(low, 2),
            "high": round(high, 2),
            "count": count,
            "avg_rating": avg_rating,
        })

    return distribution


def _find_sweet_spot(distribution: list[dict]) -> dict | None:
    """
    找到甜点价位：产品数量最多的价格段。
    如果有多个并列，取价格较低的那个。
    """
    if not distribution:
        return None

    max_count = max(d["count"] for d in distribution)
    if max_count == 0:
        return None

    # 取数量最多且价格最低的段
    for d in distribution:
        if d["count"] == max_count:
            return {
                "bucket": d["bucket"],
                "low": d["low"],
                "high": d["high"],
                "count": d["count"],
                "avg_rating": d["avg_rating"],
            }

    return None


def _find_price_gaps(distribution: list[dict]) -> list[dict]:
    """
    找到价格空白：没有产品的价格段。
    """
    return [
        {"bucket": d["bucket"], "low": d["low"], "high": d["high"]}
        for d in distribution
        if d["count"] == 0
    ]


def _compute_premium_correlation(pairs: list[tuple[float, float]]) -> dict:
    """
    计算价格与评分的皮尔逊相关系数。

    正相关说明高价产品评分更高（溢价合理），
    负相关说明高价产品不一定好（溢价不合理）。
    """
    if len(pairs) < 3:
        return {"coefficient": 0.0, "interpretation": "数据不足（需至少3个有评分的产品）"}

    prices = np.array([p for p, _ in pairs])
    ratings = np.array([r for _, r in pairs])

    # 检查标准差
    if prices.std() == 0 or ratings.std() == 0:
        return {"coefficient": 0.0, "interpretation": "价格或评分无变化，无法计算相关性"}

    # 皮尔逊相关系数
    correlation = float(np.corrcoef(prices, ratings)[0, 1])

    if np.isnan(correlation):
        return {"coefficient": 0.0, "interpretation": "计算异常"}

    # 解读
    if correlation > 0.5:
        interpretation = "强正相关：高价产品评分普遍更高，溢价较合理"
    elif correlation > 0.2:
        interpretation = "弱正相关：价格与评分有一定正向关系"
    elif correlation > -0.2:
        interpretation = "无显著相关：价格与评分无明显关系"
    elif correlation > -0.5:
        interpretation = "弱负相关：高价产品评分反而偏低"
    else:
        interpretation = "强负相关：高价产品评分明显更低，溢价不合理"

    return {
        "coefficient": round(correlation, 4),
        "interpretation": interpretation,
    }


def _safe_float(value: Any) -> float | None:
    """安全地将值转换为浮点数，失败返回 None。"""
    if value is None:
        return None
    try:
        result = float(value)
        return result if np.isfinite(result) else None
    except (TypeError, ValueError):
        return None


# ============================================================
# 独立运行示例
# ============================================================
if __name__ == "__main__":
    sample_products = [
        {"name": "入门款A", "price": 99, "rating": 3.8},
        {"name": "入门款B", "price": 129, "rating": 4.0},
        {"name": "入门款C", "price": 149, "rating": 4.1},
        {"name": "中端款A", "price": 299, "rating": 4.3},
        {"name": "中端款B", "price": 349, "rating": 4.5},
        {"name": "中端款C", "price": 299, "rating": 4.2},
        {"name": "中端款D", "price": 279, "rating": 4.4},
        {"name": "高端款A", "price": 599, "rating": 4.7},
        {"name": "高端款B", "price": 699, "rating": 4.8},
        {"name": "旗舰款", "price": 999, "rating": 4.9},
    ]

    result = analyze_pricing(sample_products)

    print("=== 价格分析结果 ===")
    print(f"价格范围: {result['price_range']}")

    print("\n价格分布:")
    for d in result['distribution']:
        bar = "#" * d['count']
        rating_str = f"  评分={d['avg_rating']}" if d['avg_rating'] else ""
        print(f"  {d['bucket']:>12s}: {d['count']:2d} {bar}{rating_str}")

    print(f"\n甜点价位: {result['sweet_spot']}")
    print(f"价格空白: {result['gaps']}")
    print(f"溢价相关性: {result['premium_correlation']}")

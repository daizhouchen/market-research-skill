"""
竞争对手分析器

分析多来源的产品列表，输出竞品矩阵、定位图、市场空白和集中度。
"""

import numpy as np
from collections import defaultdict, Counter
from typing import Any


def analyze_competitors(products: list[dict[str, Any]]) -> dict:
    """
    分析竞品数据。

    Args:
        products: 产品列表，每条记录包含:
                  - name: str, 产品名称（必需）
                  - brand: str, 品牌（可选）
                  - price: float, 价格（可选）
                  - rating: float, 评分（可选）
                  - features: list[str], 功能特性列表（可选）
                  - sales: int, 销量（可选）
                  - source: str, 数据来源（可选）

    Returns:
        分析结果字典，包含 competitor_matrix, positioning_map, market_gaps, concentration。
    """
    if not products:
        return _empty_result()

    # 过滤无效产品
    valid_products = [p for p in products if p.get("name")]
    if not valid_products:
        return _empty_result()

    competitor_matrix = _build_competitor_matrix(valid_products)
    positioning_map = _build_positioning_map(valid_products)
    market_gaps = _find_market_gaps(valid_products)
    concentration = _compute_concentration(valid_products)

    return {
        "competitor_matrix": competitor_matrix,
        "positioning_map": positioning_map,
        "market_gaps": market_gaps,
        "concentration": concentration,
    }


def _empty_result() -> dict:
    """返回空数据时的默认结果。"""
    return {
        "competitor_matrix": {"features": [], "products": []},
        "positioning_map": [],
        "market_gaps": {"empty_price_segments": [], "empty_feature_combinations": []},
        "concentration": {"top3_share": 0.0, "top3_brands": [], "hhi": 0.0},
    }


def _build_competitor_matrix(products: list[dict]) -> dict:
    """
    构建功能 x 产品的竞品对比矩阵。

    Returns:
        {
            "features": [feature_name, ...],
            "products": [
                {"name": str, "brand": str, "price": float, "rating": float,
                 "feature_support": {feature: bool, ...}},
                ...
            ]
        }
    """
    # 收集所有出现的功能
    feature_counter = Counter()
    for p in products:
        features = p.get("features", [])
        if isinstance(features, list):
            for f in features:
                if isinstance(f, str) and f.strip():
                    feature_counter[f.strip()] += 1

    # 取出现次数最多的前20个特性（避免矩阵太大）
    top_features = [f for f, _ in feature_counter.most_common(20)]

    # 构建矩阵
    matrix_products = []
    seen_names = set()
    for p in products:
        name = str(p.get("name", "")).strip()
        if not name or name in seen_names:
            continue
        seen_names.add(name)

        product_features = set()
        for f in (p.get("features") or []):
            if isinstance(f, str):
                product_features.add(f.strip())

        feature_support = {f: (f in product_features) for f in top_features}

        matrix_products.append({
            "name": name,
            "brand": str(p.get("brand", "")),
            "price": _safe_float(p.get("price")),
            "rating": _safe_float(p.get("rating")),
            "feature_support": feature_support,
        })

    return {
        "features": top_features,
        "products": matrix_products,
    }


def _build_positioning_map(products: list[dict]) -> list[dict]:
    """
    构建价格-评分定位散点图数据。
    只包含同时有价格和评分的产品。
    """
    positioning = []
    for p in products:
        price = _safe_float(p.get("price"))
        rating = _safe_float(p.get("rating"))
        if price is not None and price > 0 and rating is not None and rating > 0:
            positioning.append({
                "name": str(p.get("name", "")),
                "brand": str(p.get("brand", "")),
                "price": price,
                "rating": rating,
            })
    return positioning


def _find_market_gaps(products: list[dict]) -> dict:
    """
    发现市场空白：空白价格段和空白功能组合。
    """
    # --- 价格段空白 ---
    prices = [_safe_float(p.get("price")) for p in products]
    prices = [pr for pr in prices if pr is not None and pr > 0]

    empty_price_segments = []
    if len(prices) >= 3:
        prices_arr = np.array(sorted(prices))
        p_min, p_max = prices_arr.min(), prices_arr.max()

        if p_max > p_min:
            # 将价格范围分为10段
            num_buckets = 10
            bucket_width = (p_max - p_min) / num_buckets

            for i in range(num_buckets):
                low = p_min + i * bucket_width
                high = low + bucket_width
                count = np.sum((prices_arr >= low) & (prices_arr < high))
                if count == 0:
                    empty_price_segments.append({
                        "range": f"{low:.0f}-{high:.0f}",
                        "low": round(float(low), 2),
                        "high": round(float(high), 2),
                    })

    # --- 功能组合空白 ---
    # 找出高频两两功能组合中没有产品覆盖的
    feature_sets = []
    all_features = Counter()
    for p in products:
        feats = [f.strip() for f in (p.get("features") or []) if isinstance(f, str) and f.strip()]
        feature_sets.append(set(feats))
        all_features.update(feats)

    # 取 TOP 8 高频功能
    top_feats = [f for f, _ in all_features.most_common(8)]
    empty_combos = []

    if len(top_feats) >= 2:
        for i in range(len(top_feats)):
            for j in range(i + 1, len(top_feats)):
                f1, f2 = top_feats[i], top_feats[j]
                has_combo = any(f1 in fs and f2 in fs for fs in feature_sets)
                if not has_combo:
                    empty_combos.append([f1, f2])

    return {
        "empty_price_segments": empty_price_segments,
        "empty_feature_combinations": empty_combos[:10],  # 最多返回10个
    }


def _compute_concentration(products: list[dict]) -> dict:
    """
    计算市场集中度：TOP3 品牌市场份额（基于销量或产品数量）。
    """
    brand_sales = defaultdict(float)

    for p in products:
        brand = str(p.get("brand", "")).strip() or "未知品牌"
        sales = _safe_float(p.get("sales"))
        if sales is not None and sales > 0:
            brand_sales[brand] += sales
        else:
            # 没有销量数据时按产品数计
            brand_sales[brand] += 1

    if not brand_sales:
        return {"top3_share": 0.0, "top3_brands": [], "hhi": 0.0}

    total = sum(brand_sales.values())
    sorted_brands = sorted(brand_sales.items(), key=lambda x: x[1], reverse=True)

    top3 = sorted_brands[:3]
    top3_sales = sum(s for _, s in top3)
    top3_share = top3_sales / total if total > 0 else 0.0

    # HHI 指数（赫芬达尔指数）
    shares = [(s / total * 100) for _, s in sorted_brands] if total > 0 else []
    hhi = sum(s ** 2 for s in shares)

    top3_brands = [
        {"brand": brand, "share": round(sales / total * 100, 1) if total > 0 else 0}
        for brand, sales in top3
    ]

    return {
        "top3_share": round(top3_share * 100, 1),
        "top3_brands": top3_brands,
        "hhi": round(hhi, 1),
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
        {"name": "产品A", "brand": "品牌X", "price": 299, "rating": 4.5,
         "features": ["蓝牙", "防水", "降噪"], "sales": 5000},
        {"name": "产品B", "brand": "品牌X", "price": 199, "rating": 4.2,
         "features": ["蓝牙", "轻便"], "sales": 8000},
        {"name": "产品C", "brand": "品牌Y", "price": 499, "rating": 4.8,
         "features": ["蓝牙", "防水", "降噪", "无线充电"], "sales": 3000},
        {"name": "产品D", "brand": "品牌Z", "price": 159, "rating": 3.9,
         "features": ["蓝牙", "轻便"], "sales": 12000},
        {"name": "产品E", "brand": "品牌W", "price": 399, "rating": 4.6,
         "features": ["蓝牙", "降噪", "无线充电", "长续航"], "sales": 4000},
        {"name": "产品F", "brand": "品牌Y", "price": 599, "rating": 4.7,
         "features": ["蓝牙", "防水", "降噪", "无线充电", "长续航"], "sales": 2000},
    ]

    result = analyze_competitors(sample_products)

    print("=== 竞品分析结果 ===")
    print(f"\n功能矩阵 - 功能列: {result['competitor_matrix']['features']}")
    for p in result['competitor_matrix']['products']:
        supported = [f for f, v in p['feature_support'].items() if v]
        print(f"  {p['name']} ({p['brand']}): {supported}")

    print(f"\n定位图数据点: {len(result['positioning_map'])} 个产品")
    for pt in result['positioning_map']:
        print(f"  {pt['name']}: 价格={pt['price']}, 评分={pt['rating']}")

    print(f"\n市场空白 - 价格段: {result['market_gaps']['empty_price_segments']}")
    print(f"市场空白 - 功能组合: {result['market_gaps']['empty_feature_combinations']}")

    print(f"\n市场集中度: TOP3 份额={result['concentration']['top3_share']}%")
    for b in result['concentration']['top3_brands']:
        print(f"  {b['brand']}: {b['share']}%")
    print(f"HHI 指数: {result['concentration']['hhi']}")

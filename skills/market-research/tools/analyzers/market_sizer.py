"""
市场规模估算器

提供自上而下（Top-Down）和自下而上（Bottom-Up）两种方法估算市场规模，
并通过三角验证得出可信区间。同时支持判断市场生命周期阶段。
"""

import math
import re
from typing import Any


# ============================================================
# 辅助工具
# ============================================================

def _safe_float(value: Any, default: float = 0.0) -> float:
    """安全地将值转换为浮点数，失败时返回默认值。"""
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def _extract_numbers_from_text(text: str) -> list[float]:
    """
    从文本中提取数值（支持 B/M/K/亿/万 等单位）。
    例如 "$4.5B" -> 4_500_000_000, "300亿" -> 30_000_000_000
    """
    results: list[float] = []
    # 英文单位: $4.5B, 300M, 12K
    en_pattern = r'[\$€£¥]?\s*(\d+(?:\.\d+)?)\s*([BMKbmk](?:illion|illion)?)\b'
    for match in re.finditer(en_pattern, text):
        num = float(match.group(1))
        unit = match.group(2)[0].upper()
        multiplier = {'B': 1e9, 'M': 1e6, 'K': 1e3}.get(unit, 1)
        results.append(num * multiplier)

    # 中文单位: 300亿, 4500万
    zh_pattern = r'(\d+(?:\.\d+)?)\s*(万亿|亿|万)'
    for match in re.finditer(zh_pattern, text):
        num = float(match.group(1))
        unit = match.group(2)
        multiplier = {'万亿': 1e12, '亿': 1e8, '万': 1e4}.get(unit, 1)
        results.append(num * multiplier)

    return results


def _extract_cagr(text: str) -> float | None:
    """从文本中提取年复合增长率（CAGR），返回小数形式。"""
    pattern = r'CAGR[^0-9]*(\d+(?:\.\d+)?)\s*%'
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        return float(match.group(1)) / 100.0
    # 也匹配中文"年复合增长率"
    zh_pattern = r'(?:年复合增长率|复合年增长率|CAGR)[^\d]*(\d+(?:\.\d+)?)\s*%'
    match = re.search(zh_pattern, text)
    if match:
        return float(match.group(1)) / 100.0
    return None


def _weighted_average(values: list[float], weights: list[float] | None = None) -> float:
    """加权平均，若无权重则等权。"""
    if not values:
        return 0.0
    if weights is None or len(weights) != len(values):
        return sum(values) / len(values)
    total_weight = sum(weights)
    if total_weight == 0:
        return sum(values) / len(values)
    return sum(v * w for v, w in zip(values, weights)) / total_weight


# ============================================================
# 自上而下估算
# ============================================================

def estimate_tam_top_down(
    market_reports: list[dict],
    target_segment: str,
    target_region: str,
) -> dict:
    """
    自上而下法估算 TAM/SAM/SOM。

    从市场报告数据中提取总市场规模，再按细分占比和地区占比逐步缩减。

    参数:
        market_reports: 市场报告列表，每项包含:
            - title (str): 报告标题
            - text (str): 报告正文或摘要
            - source (str): 来源名称
            - year (int, 可选): 报告年份
            - segment_share (float, 可选): 目标细分在总市场中的占比 (0-1)
            - region_share (float, 可选): 目标地区在总市场中的占比 (0-1)
        target_segment: 目标细分市场名称
        target_region: 目标地区名称

    返回:
        {tam, sam, som, cagr, confidence, sources, assumptions}
    """
    if not market_reports:
        return {
            "tam": 0,
            "sam": 0,
            "som": 0,
            "cagr": None,
            "confidence": 0.0,
            "sources": [],
            "assumptions": ["无可用市场报告数据"],
        }

    tam_estimates: list[float] = []
    cagr_estimates: list[float] = []
    sources: list[str] = []
    segment_shares: list[float] = []
    region_shares: list[float] = []
    assumptions: list[str] = []

    for report in market_reports:
        text = report.get("text", "") or ""
        title = report.get("title", "") or ""
        source = report.get("source", "未知来源")
        combined_text = f"{title} {text}"

        # 提取市场规模数字
        numbers = _extract_numbers_from_text(combined_text)
        if numbers:
            # 取最大值作为 TAM 估计（市场报告通常先提总规模）
            tam_estimates.append(max(numbers))
            sources.append(source)

        # 提取 CAGR
        cagr = _extract_cagr(combined_text)
        if cagr is not None:
            cagr_estimates.append(cagr)

        # 收集占比数据
        seg_share = _safe_float(report.get("segment_share"), default=-1)
        if 0 < seg_share <= 1:
            segment_shares.append(seg_share)

        reg_share = _safe_float(report.get("region_share"), default=-1)
        if 0 < reg_share <= 1:
            region_shares.append(reg_share)

    # 计算 TAM
    if not tam_estimates:
        return {
            "tam": 0,
            "sam": 0,
            "som": 0,
            "cagr": None,
            "confidence": 0.0,
            "sources": sources,
            "assumptions": ["无法从报告中提取市场规模数字"],
        }

    tam = _weighted_average(tam_estimates)

    # 细分占比：使用报告中的数据，否则用保守默认值
    if segment_shares:
        avg_segment_share = _weighted_average(segment_shares)
        assumptions.append(f"细分市场 '{target_segment}' 占比取平均值: {avg_segment_share:.1%}")
    else:
        avg_segment_share = 0.15  # 保守默认值
        assumptions.append(f"细分市场 '{target_segment}' 占比使用默认值: 15%")

    # 地区占比
    if region_shares:
        avg_region_share = _weighted_average(region_shares)
        assumptions.append(f"地区 '{target_region}' 占比取平均值: {avg_region_share:.1%}")
    else:
        avg_region_share = 0.30  # 保守默认值
        assumptions.append(f"地区 '{target_region}' 占比使用默认值: 30%")

    # SAM = TAM × 细分占比 × 地区占比
    sam = tam * avg_segment_share * avg_region_share
    assumptions.append("SAM = TAM × 细分占比 × 地区占比")

    # SOM = SAM × 可触达比例（新进入者取 1-5%）
    som_ratio = 0.03
    som = sam * som_ratio
    assumptions.append(f"SOM 按 SAM 的 {som_ratio:.0%} 估算（新进入者保守估计）")

    # CAGR
    avg_cagr = _weighted_average(cagr_estimates) if cagr_estimates else None

    # 置信度：根据数据源数量和一致性
    confidence = _calculate_confidence(tam_estimates)

    return {
        "tam": round(tam, 2),
        "sam": round(sam, 2),
        "som": round(som, 2),
        "cagr": round(avg_cagr, 4) if avg_cagr is not None else None,
        "confidence": round(confidence, 2),
        "sources": list(set(sources)),
        "assumptions": assumptions,
    }


def _calculate_confidence(estimates: list[float]) -> float:
    """
    根据估算值的数量和一致性计算置信度 (0-1)。
    数据源越多、估计越一致，置信度越高。
    """
    if not estimates:
        return 0.0
    if len(estimates) == 1:
        return 0.3  # 只有一个数据源，信心有限

    # 数据源数量分（最多 0.4 分）
    count_score = min(len(estimates) / 5, 1.0) * 0.4

    # 一致性分（最多 0.6 分）：用变异系数衡量
    mean = sum(estimates) / len(estimates)
    if mean == 0:
        return count_score
    variance = sum((x - mean) ** 2 for x in estimates) / len(estimates)
    cv = math.sqrt(variance) / abs(mean)  # 变异系数
    # cv 越小越一致; cv=0 → 满分, cv>=1 → 0 分
    consistency_score = max(0, 1 - cv) * 0.6

    return count_score + consistency_score


# ============================================================
# 自下而上估算
# ============================================================

def estimate_tam_bottom_up(
    search_volume: int,
    conversion_rate: float,
    avg_price: float,
    competitors: list[dict],
) -> dict:
    """
    自下而上法估算 TAM/SAM/SOM。

    从搜索量推算潜在用户基数，结合竞品数据交叉验证。

    参数:
        search_volume: 月搜索量
        conversion_rate: 搜索到购买的转化率 (0-1)
        avg_price: 平均客单价
        competitors: 竞品列表，每项包含:
            - name (str): 竞品名称
            - downloads (int, 可选): 下载量/用户数
            - revenue (float, 可选): 年营收
            - market_share (float, 可选): 市场份额 (0-1)

    返回:
        {tam, sam, som, cagr, confidence, sources, assumptions}
    """
    assumptions: list[str] = []
    sources: list[str] = []

    # ---- 方法 1: 从搜索量推算 ----
    # 搜索量通常只覆盖实际需求的 30-60%（许多人不搜索）
    search_coverage = 0.4
    annual_searches = max(search_volume, 0) * 12
    estimated_demand = annual_searches / search_coverage
    safe_conversion = max(0.0, min(conversion_rate, 1.0))
    safe_price = max(avg_price, 0.0)

    search_based_tam = estimated_demand * safe_conversion * safe_price
    assumptions.append(f"月搜索量 {search_volume:,}，假设搜索覆盖率 {search_coverage:.0%}")
    assumptions.append(f"转化率 {safe_conversion:.2%}，均价 {safe_price:,.2f}")

    # ---- 方法 2: 从竞品数据反推 ----
    competitor_based_tams: list[float] = []

    for comp in competitors:
        name = comp.get("name", "未知")
        revenue = _safe_float(comp.get("revenue"))
        market_share = _safe_float(comp.get("market_share"))
        downloads = _safe_float(comp.get("downloads"))

        # 如果有营收和份额，直接反推总市场
        if revenue > 0 and 0 < market_share <= 1:
            implied_tam = revenue / market_share
            competitor_based_tams.append(implied_tam)
            sources.append(f"{name} (营收/份额)")
            assumptions.append(f"{name}: 营收 {revenue:,.0f} / 份额 {market_share:.1%} → TAM {implied_tam:,.0f}")

        # 如果有下载量，用平均价格估算
        elif downloads > 0 and safe_price > 0:
            # 假设下载到付费转化率 5%
            download_conversion = 0.05
            implied_revenue = downloads * download_conversion * safe_price
            if 0 < market_share <= 1:
                implied_tam = implied_revenue / market_share
            else:
                # 没有份额信息，假设该竞品占 10%
                implied_tam = implied_revenue / 0.10
                assumptions.append(f"{name}: 无市场份额数据，假设占比 10%")
            competitor_based_tams.append(implied_tam)
            sources.append(f"{name} (下载量)")

    # 综合两种方法
    all_estimates = [search_based_tam] if search_based_tam > 0 else []
    all_estimates.extend(competitor_based_tams)

    if not all_estimates:
        return {
            "tam": 0,
            "sam": 0,
            "som": 0,
            "cagr": None,
            "confidence": 0.0,
            "sources": sources,
            "assumptions": assumptions + ["数据不足，无法估算"],
        }

    tam = _weighted_average(all_estimates)

    # SAM: 自下而上时，搜索量本身就是可触达市场的近似
    sam = search_based_tam if search_based_tam > 0 else tam * 0.3
    assumptions.append("SAM 基于搜索量直接推算的市场规模")

    # SOM: 新进入者预期能获取的份额
    total_competitors = max(len(competitors), 1)
    fair_share = 1.0 / (total_competitors + 1)  # +1 是自己
    penetration = min(fair_share, 0.05)  # 上限 5%
    som = sam * penetration
    assumptions.append(f"SOM: SAM × {penetration:.1%}（{total_competitors} 个竞品的公平份额，上限 5%）")

    confidence = _calculate_confidence(all_estimates)

    return {
        "tam": round(tam, 2),
        "sam": round(sam, 2),
        "som": round(som, 2),
        "cagr": None,  # 自下而上法通常无法直接得出 CAGR
        "confidence": round(confidence, 2),
        "sources": sources,
        "assumptions": assumptions,
    }


# ============================================================
# 市场生命周期判断
# ============================================================

# 阶段定义
_STAGES = {
    "emerging": "萌芽期",
    "growth": "成长期",
    "mature": "成熟期",
    "decline": "衰退期",
}


def determine_lifecycle_stage(
    trend_data: dict,
    product_count: int,
    funding_data: dict,
    price_trend: str,
) -> dict:
    """
    判断市场所处生命周期阶段。

    通过多个信号综合打分来判断：趋势增长率、产品数量、融资情况、价格走势。

    参数:
        trend_data: 趋势数据，包含:
            - growth_rate (float): 近期增长率 (如 0.2 表示 20%)
            - search_trend (str): "rising" / "stable" / "declining"
            - volatility (float, 可选): 波动率
        product_count: 市场中的产品/玩家数量
        funding_data: 融资数据，包含:
            - total_funding (float): 总融资额
            - deal_count (int): 融资笔数
            - avg_round_size (float, 可选): 平均单笔融资额
            - trend (str, 可选): "increasing" / "stable" / "decreasing"
        price_trend: 价格趋势 "rising" / "stable" / "declining"

    返回:
        {stage, stage_cn, evidence, confidence}
    """
    # 各阶段的得分
    scores = {"emerging": 0.0, "growth": 0.0, "mature": 0.0, "decline": 0.0}
    evidence: list[str] = []

    # ---- 信号 1: 增长率 ----
    growth_rate = _safe_float(trend_data.get("growth_rate") if trend_data else None)
    if growth_rate > 0.5:
        scores["emerging"] += 2
        scores["growth"] += 1
        evidence.append(f"高增长率 ({growth_rate:.0%}) → 倾向萌芽/成长期")
    elif growth_rate > 0.15:
        scores["growth"] += 2
        evidence.append(f"中高增长率 ({growth_rate:.0%}) → 倾向成长期")
    elif growth_rate > 0.02:
        scores["mature"] += 2
        evidence.append(f"低增长率 ({growth_rate:.0%}) → 倾向成熟期")
    elif growth_rate <= 0:
        scores["decline"] += 2
        evidence.append(f"负增长 ({growth_rate:.0%}) → 倾向衰退期")
    else:
        scores["mature"] += 1
        evidence.append(f"微弱增长 ({growth_rate:.0%}) → 可能成熟期")

    # ---- 信号 2: 搜索趋势 ----
    search_trend = (trend_data.get("search_trend", "") if trend_data else "").lower()
    if search_trend == "rising":
        scores["emerging"] += 1
        scores["growth"] += 1
        evidence.append("搜索趋势上升")
    elif search_trend == "declining":
        scores["mature"] += 1
        scores["decline"] += 1
        evidence.append("搜索趋势下降")

    # ---- 信号 3: 产品/玩家数量 ----
    safe_product_count = max(product_count, 0)
    if safe_product_count <= 3:
        scores["emerging"] += 2
        evidence.append(f"仅 {safe_product_count} 个产品 → 市场早期")
    elif safe_product_count <= 10:
        scores["growth"] += 2
        evidence.append(f"{safe_product_count} 个产品 → 竞争加剧，成长期特征")
    elif safe_product_count <= 30:
        scores["mature"] += 2
        evidence.append(f"{safe_product_count} 个产品 → 市场饱和，成熟期特征")
    else:
        scores["mature"] += 1
        scores["decline"] += 1
        evidence.append(f"{safe_product_count} 个产品 → 过度拥挤")

    # ---- 信号 4: 融资情况 ----
    deal_count = int(_safe_float(funding_data.get("deal_count") if funding_data else None))
    funding_trend = (funding_data.get("trend", "") if funding_data else "").lower()

    if deal_count > 0:
        if funding_trend == "increasing":
            scores["growth"] += 2
            evidence.append("融资活跃且增长 → 成长期信号")
        elif funding_trend == "decreasing":
            scores["mature"] += 1
            scores["decline"] += 1
            evidence.append("融资活跃度下降")
        else:
            scores["growth"] += 1
            evidence.append("融资活跃但趋势不明")
    else:
        # 无融资可能是太早期或太晚期
        scores["emerging"] += 0.5
        scores["decline"] += 0.5

    # ---- 信号 5: 价格趋势 ----
    safe_price_trend = (price_trend or "").lower()
    if safe_price_trend == "rising":
        scores["emerging"] += 1
        scores["growth"] += 1
        evidence.append("价格上升 → 需求旺盛")
    elif safe_price_trend == "declining":
        scores["mature"] += 1
        scores["decline"] += 1
        evidence.append("价格下降 → 竞争加剧或需求萎缩")
    elif safe_price_trend == "stable":
        scores["mature"] += 1
        evidence.append("价格稳定 → 成熟期特征")

    # 找出得分最高的阶段
    max_score = max(scores.values())
    if max_score == 0:
        stage = "mature"  # 默认
        confidence = 0.2
    else:
        stage = max(scores, key=lambda k: scores[k])
        total_score = sum(scores.values())
        confidence = scores[stage] / total_score if total_score > 0 else 0.2

    return {
        "stage": stage,
        "stage_cn": _STAGES.get(stage, stage),
        "evidence": evidence,
        "confidence": round(confidence, 2),
        "scores": {k: round(v, 2) for k, v in scores.items()},
    }


# ============================================================
# 三角验证
# ============================================================

def triangulate(top_down: dict, bottom_up: dict) -> dict:
    """
    三角验证自上而下和自下而上两个估算结果。

    比较两种方法的 TAM/SAM/SOM，给出范围区间和一致性评估。

    参数:
        top_down: estimate_tam_top_down 的输出
        bottom_up: estimate_tam_bottom_up 的输出

    返回:
        {
            tam_range, sam_range, som_range,
            tam_midpoint, sam_midpoint, som_midpoint,
            consistency, combined_confidence, notes
        }
    """
    notes: list[str] = []

    td_tam = _safe_float(top_down.get("tam"))
    bu_tam = _safe_float(bottom_up.get("tam"))
    td_sam = _safe_float(top_down.get("sam"))
    bu_sam = _safe_float(bottom_up.get("sam"))
    td_som = _safe_float(top_down.get("som"))
    bu_som = _safe_float(bottom_up.get("som"))

    def _make_range(val_a: float, val_b: float) -> dict:
        """生成范围区间和中点。"""
        if val_a == 0 and val_b == 0:
            return {"low": 0, "high": 0, "midpoint": 0}
        low = min(val_a, val_b)
        high = max(val_a, val_b)
        midpoint = (val_a + val_b) / 2
        return {
            "low": round(low, 2),
            "high": round(high, 2),
            "midpoint": round(midpoint, 2),
        }

    tam_range = _make_range(td_tam, bu_tam)
    sam_range = _make_range(td_sam, bu_sam)
    som_range = _make_range(td_som, bu_som)

    # 一致性评估：两个估计的比值越接近 1 越一致
    def _ratio_consistency(a: float, b: float) -> float:
        """两个值的一致性得分 (0-1)，比值越接近1分数越高。"""
        if a == 0 and b == 0:
            return 1.0
        if a == 0 or b == 0:
            return 0.0
        ratio = max(a, b) / min(a, b)
        # ratio=1 → 1.0, ratio=2 → 0.5, ratio=5 → 0.2, ratio≥10 → ≈0
        return max(0.0, 1.0 - (ratio - 1) / 9)

    tam_consistency = _ratio_consistency(td_tam, bu_tam)
    sam_consistency = _ratio_consistency(td_sam, bu_sam)
    overall_consistency = (tam_consistency * 0.6 + sam_consistency * 0.4)

    if overall_consistency > 0.7:
        notes.append("两种方法结果高度一致，估算可信度较高")
    elif overall_consistency > 0.4:
        notes.append("两种方法结果存在一定差异，建议进一步验证")
    else:
        notes.append("两种方法结果差异较大，需审视假设前提")
        # 分析差异方向
        if td_tam > bu_tam * 2:
            notes.append("自上而下估计显著高于自下而上，可能存在细分市场划分过大的问题")
        elif bu_tam > td_tam * 2:
            notes.append("自下而上估计显著高于自上而下，可能高估了搜索量到需求的转化")

    # 综合置信度
    td_conf = _safe_float(top_down.get("confidence"))
    bu_conf = _safe_float(bottom_up.get("confidence"))
    # 两种方法的置信度加权平均，一致性好时给予加成
    combined_confidence = (td_conf + bu_conf) / 2 * (0.7 + 0.3 * overall_consistency)

    # 合并 CAGR
    cagr = top_down.get("cagr") or bottom_up.get("cagr")

    return {
        "tam_range": tam_range,
        "sam_range": sam_range,
        "som_range": som_range,
        "tam_midpoint": tam_range["midpoint"],
        "sam_midpoint": sam_range["midpoint"],
        "som_midpoint": som_range["midpoint"],
        "cagr": cagr,
        "consistency": round(overall_consistency, 2),
        "combined_confidence": round(combined_confidence, 2),
        "notes": notes,
        "all_sources": list(set(
            (top_down.get("sources") or []) + (bottom_up.get("sources") or [])
        )),
        "all_assumptions": (
            (top_down.get("assumptions") or []) + (bottom_up.get("assumptions") or [])
        ),
    }


# ============================================================
# 测试示例
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("市场规模估算器 — 测试示例")
    print("=" * 60)

    # 测试自上而下
    reports = [
        {
            "title": "Global Smart Home Market Report 2025",
            "text": "The global smart home market was valued at $80.21B in 2024 "
                    "and is projected to reach $338.28B by 2030, growing at a CAGR of 27.1%.",
            "source": "Grand View Research",
            "segment_share": 0.12,
            "region_share": 0.35,
        },
        {
            "title": "智能家居市场分析报告",
            "text": "全球智能家居市场规模约850亿美元，年复合增长率25.3%。",
            "source": "中商产业研究院",
            "segment_share": 0.10,
            "region_share": 0.30,
        },
    ]

    td_result = estimate_tam_top_down(reports, "智能照明", "中国")
    print("\n--- 自上而下法 ---")
    for k, v in td_result.items():
        print(f"  {k}: {v}")

    # 测试自下而上
    competitors = [
        {"name": "Philips Hue", "revenue": 1_200_000_000, "market_share": 0.15},
        {"name": "Yeelight", "downloads": 5_000_000, "market_share": 0.08},
        {"name": "LIFX", "revenue": 200_000_000, "market_share": 0.03},
    ]

    bu_result = estimate_tam_bottom_up(
        search_volume=120_000,
        conversion_rate=0.03,
        avg_price=299.0,
        competitors=competitors,
    )
    print("\n--- 自下而上法 ---")
    for k, v in bu_result.items():
        print(f"  {k}: {v}")

    # 测试三角验证
    tri_result = triangulate(td_result, bu_result)
    print("\n--- 三角验证 ---")
    for k, v in tri_result.items():
        print(f"  {k}: {v}")

    # 测试生命周期判断
    lifecycle = determine_lifecycle_stage(
        trend_data={"growth_rate": 0.27, "search_trend": "rising"},
        product_count=15,
        funding_data={"deal_count": 45, "trend": "increasing", "total_funding": 5e9},
        price_trend="declining",
    )
    print("\n--- 生命周期判断 ---")
    for k, v in lifecycle.items():
        print(f"  {k}: {v}")

    # 边界测试：空数据
    print("\n--- 边界测试：空数据 ---")
    empty_td = estimate_tam_top_down([], "any", "any")
    print(f"  空报告列表: confidence={empty_td['confidence']}, tam={empty_td['tam']}")

    empty_bu = estimate_tam_bottom_up(0, 0.0, 0.0, [])
    print(f"  零输入: confidence={empty_bu['confidence']}, tam={empty_bu['tam']}")

    empty_tri = triangulate(empty_td, empty_bu)
    print(f"  空三角验证: consistency={empty_tri['consistency']}")

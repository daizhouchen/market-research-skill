"""
技术创新追踪器

追踪和评估技术创新态势：技术壁垒评估、采纳曲线定位、
Porter 五力分析、蓝海战略画布、评论增速分析。
"""

import math
import re
from collections import Counter, defaultdict
from typing import Any


# ============================================================
# 辅助工具
# ============================================================

def _safe_float(value: Any, default: float = 0.0) -> float:
    """安全浮点转换。"""
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    """安全整数转换。"""
    try:
        return int(_safe_float(value, float(default)))
    except (ValueError, TypeError, OverflowError):
        return default


def _clamp(value: float, low: float, high: float) -> float:
    """将值限制在 [low, high] 范围内。"""
    return max(low, min(high, value))


def _simple_sentiment(text: str) -> float:
    """简单情感评分 (-1 到 1)。"""
    positive = {
        "breakthrough", "innovative", "revolutionary", "advanced", "cutting-edge",
        "promising", "exciting", "efficient", "powerful", "robust",
        "突破", "创新", "革命性", "领先", "前沿", "高效", "强大",
    }
    negative = {
        "difficult", "complex", "expensive", "limited", "immature", "unstable",
        "risky", "slow", "fragile", "unreliable",
        "困难", "复杂", "昂贵", "有限", "不成熟", "不稳定", "风险",
    }
    text_lower = text.lower()
    pos = sum(1 for w in positive if w in text_lower)
    neg = sum(1 for w in negative if w in text_lower)
    total = pos + neg
    if total == 0:
        return 0.0
    return (pos - neg) / total


# ============================================================
# 技术壁垒评估
# ============================================================

# 壁垒相关关键词
_HIGH_BARRIER_KEYWORDS = {
    "patent", "proprietary", "exclusive", "trade secret", "years of research",
    "deep learning", "specialized hardware", "custom silicon", "FDA approved",
    "专利", "独有", "自研", "核心技术", "多年积累", "定制芯片", "审批",
}
_LOW_BARRIER_KEYWORDS = {
    "open source", "commodity", "off-the-shelf", "easily replicated", "tutorial",
    "no-code", "plug and play", "wrapper", "API",
    "开源", "通用", "现成", "易复制", "教程", "低门槛", "API封装",
}
_MOAT_KEYWORDS = {
    "network effect", "switching cost", "data advantage", "brand",
    "ecosystem", "lock-in", "regulatory",
    "网络效应", "转换成本", "数据优势", "品牌", "生态", "锁定", "牌照",
}


def assess_tech_barriers(
    texts: list[str],
    patent_data: list[dict],
) -> dict:
    """
    评估技术壁垒高低。

    综合分析技术讨论文本和专利数据，判断进入壁垒。

    参数:
        texts: 技术讨论/评论文本列表
        patent_data: 专利数据列表，每项包含:
            - title (str): 专利标题
            - holder (str): 持有者
            - year (int, 可选): 申请年份
            - citations (int, 可选): 引用次数

    返回:
        {barrier_level, key_technologies, moats, open_source_alternatives}
    """
    if not texts and not patent_data:
        return {
            "barrier_level": 3,
            "key_technologies": [],
            "moats": [],
            "open_source_alternatives": [],
            "evidence": ["数据不足，默认中等壁垒"],
        }

    barrier_score = 0.0
    evidence: list[str] = []
    key_technologies: list[str] = []
    moats: list[str] = []
    open_source_alts: list[str] = []

    # ---- 分析文本 ----
    high_barrier_hits = 0
    low_barrier_hits = 0
    moat_hits: dict[str, int] = defaultdict(int)

    for text in (texts or []):
        if not text or not isinstance(text, str):
            continue
        text_lower = text.lower()

        for kw in _HIGH_BARRIER_KEYWORDS:
            if kw in text_lower:
                high_barrier_hits += 1

        for kw in _LOW_BARRIER_KEYWORDS:
            if kw in text_lower:
                low_barrier_hits += 1
                # 记录开源替代方案
                if kw in ("open source", "开源"):
                    # 尝试提取紧随其后的名称
                    pattern = re.compile(
                        rf'{re.escape(kw)}\s+(?:alternative|solution|project|项目|方案|替代)?\s*[:\-]?\s*(\w[\w\s\-]{{2,30}})',
                        re.IGNORECASE,
                    )
                    match = pattern.search(text)
                    if match:
                        open_source_alts.append(match.group(1).strip())

        for kw in _MOAT_KEYWORDS:
            if kw in text_lower:
                moat_hits[kw] += 1

    # 文本信号得分
    if high_barrier_hits + low_barrier_hits > 0:
        text_ratio = high_barrier_hits / (high_barrier_hits + low_barrier_hits)
        barrier_score += text_ratio * 2  # 最多 +2
        if text_ratio > 0.6:
            evidence.append(f"技术讨论中高壁垒关键词占比 {text_ratio:.0%}")
        elif text_ratio < 0.4:
            evidence.append(f"技术讨论中低壁垒关键词占比 {1 - text_ratio:.0%}")

    # 护城河
    for moat_kw, count in moat_hits.items():
        if count >= 2:
            moats.append(moat_kw)
            barrier_score += 0.3
            evidence.append(f"识别到护城河: {moat_kw} (提及 {count} 次)")

    # ---- 分析专利数据 ----
    if patent_data:
        patent_count = len(patent_data)
        total_citations = sum(_safe_int(p.get("citations")) for p in patent_data)

        # 专利数量信号
        if patent_count >= 50:
            barrier_score += 1.5
            evidence.append(f"大量专利 ({patent_count} 件) → 高壁垒")
        elif patent_count >= 10:
            barrier_score += 0.8
            evidence.append(f"中等专利数量 ({patent_count} 件)")
        elif patent_count > 0:
            barrier_score += 0.3
            evidence.append(f"少量专利 ({patent_count} 件)")

        # 引用量信号
        avg_citations = total_citations / patent_count if patent_count > 0 else 0
        if avg_citations > 20:
            barrier_score += 0.5
            evidence.append(f"高引用率专利 (平均 {avg_citations:.1f} 次引用)")

        # 提取关键技术领域
        tech_words: Counter = Counter()
        for patent in patent_data:
            title = (patent.get("title") or "").lower()
            # 提取名词性词组
            words = re.findall(r'[a-zA-Z]{3,}', title)
            zh_words = re.findall(r'[\u4e00-\u9fff]{2,4}', patent.get("title", ""))
            tech_words.update(words + zh_words)

        # 过滤通用词
        generic = {"method", "system", "device", "apparatus", "using", "based", "for", "and", "with"}
        key_technologies = [
            word for word, _ in tech_words.most_common(15)
            if word not in generic
        ][:8]
    else:
        evidence.append("无专利数据")

    # 最终壁垒等级 (1-5)
    barrier_level = _clamp(round(barrier_score + 1.5), 1, 5)  # 基础值 1.5，确保无数据时为 3

    return {
        "barrier_level": int(barrier_level),
        "key_technologies": key_technologies,
        "moats": moats,
        "open_source_alternatives": list(set(open_source_alts)),
        "evidence": evidence,
    }


# ============================================================
# 技术采纳曲线定位
# ============================================================

_ADOPTION_STAGES = {
    "innovators": "创新者阶段",
    "early_adopters": "早期采用者阶段",
    "early_majority": "早期主流阶段",
    "late_majority": "晚期主流阶段",
    "laggards": "落后者阶段",
}


def position_on_adoption_curve(
    trend_data: dict,
    user_profile: dict,
    media_coverage: dict,
) -> dict:
    """
    判断技术在采纳生命周期中的位置（Rogers 扩散曲线）。

    参数:
        trend_data: 趋势数据:
            - growth_rate (float): 增长率
            - penetration_rate (float): 市场渗透率 (0-1)
            - search_trend (str): "rising"/"stable"/"declining"
        user_profile: 用户画像数据:
            - tech_savvy_ratio (float): 技术爱好者占比 (0-1)
            - enterprise_ratio (float): 企业用户占比 (0-1)
            - age_distribution (dict, 可选): 年龄分布
        media_coverage: 媒体覆盖数据:
            - mainstream_mentions (int): 主流媒体提及次数
            - tech_blog_mentions (int): 科技博客提及次数
            - sentiment (float): 媒体情感 (-1 到 1)

    返回:
        {stage, stage_cn, evidence, chasm_risk, recommendation}
    """
    scores = {stage: 0.0 for stage in _ADOPTION_STAGES}
    evidence: list[str] = []

    # ---- 信号 1: 市场渗透率 ----
    penetration = _safe_float((trend_data or {}).get("penetration_rate"))
    if penetration < 0.025:
        scores["innovators"] += 3
        evidence.append(f"渗透率极低 ({penetration:.1%}) → 创新者阶段")
    elif penetration < 0.16:
        scores["early_adopters"] += 3
        evidence.append(f"渗透率 {penetration:.1%} → 早期采用者阶段")
    elif penetration < 0.50:
        scores["early_majority"] += 3
        evidence.append(f"渗透率 {penetration:.1%} → 早期主流阶段")
    elif penetration < 0.84:
        scores["late_majority"] += 3
        evidence.append(f"渗透率 {penetration:.1%} → 晚期主流阶段")
    else:
        scores["laggards"] += 3
        evidence.append(f"渗透率 {penetration:.1%} → 落后者阶段")

    # ---- 信号 2: 增长率 ----
    growth = _safe_float((trend_data or {}).get("growth_rate"))
    if growth > 1.0:
        scores["innovators"] += 1
        scores["early_adopters"] += 2
        evidence.append(f"爆发式增长 ({growth:.0%})")
    elif growth > 0.3:
        scores["early_adopters"] += 1
        scores["early_majority"] += 2
        evidence.append(f"快速增长 ({growth:.0%})")
    elif growth > 0.05:
        scores["early_majority"] += 1
        scores["late_majority"] += 1
        evidence.append(f"稳定增长 ({growth:.0%})")
    elif growth > -0.05:
        scores["late_majority"] += 2
        evidence.append(f"增长停滞 ({growth:.0%})")
    else:
        scores["laggards"] += 2
        evidence.append(f"负增长 ({growth:.0%})")

    # ---- 信号 3: 用户画像 ----
    tech_ratio = _safe_float((user_profile or {}).get("tech_savvy_ratio"))
    enterprise_ratio = _safe_float((user_profile or {}).get("enterprise_ratio"))

    if tech_ratio > 0.6:
        scores["innovators"] += 1
        scores["early_adopters"] += 1
        evidence.append(f"技术爱好者占比高 ({tech_ratio:.0%})")
    elif tech_ratio < 0.2:
        scores["late_majority"] += 1
        scores["laggards"] += 1
        evidence.append(f"技术爱好者占比低 ({tech_ratio:.0%}) → 已进入主流")

    if enterprise_ratio > 0.5:
        scores["early_majority"] += 1
        scores["late_majority"] += 1
        evidence.append(f"企业用户占比高 ({enterprise_ratio:.0%}) → 已被主流接受")

    # ---- 信号 4: 媒体覆盖 ----
    mainstream = _safe_int((media_coverage or {}).get("mainstream_mentions"))
    tech_blogs = _safe_int((media_coverage or {}).get("tech_blog_mentions"))
    media_sent = _safe_float((media_coverage or {}).get("sentiment"))

    if tech_blogs > 0 and mainstream == 0:
        scores["innovators"] += 1
        evidence.append("仅科技博客关注，主流媒体尚未报道")
    elif mainstream > 0 and mainstream < tech_blogs:
        scores["early_adopters"] += 1
        evidence.append("主流媒体开始关注")
    elif mainstream >= tech_blogs and mainstream > 0:
        scores["early_majority"] += 1
        evidence.append("主流媒体广泛报道")

    if media_sent > 0.5:
        evidence.append("媒体报道积极乐观")
    elif media_sent < -0.3:
        evidence.append("媒体报道偏负面，可能处于幻灭低谷期")
        scores["early_adopters"] += 0.5  # Gartner 幻灭低谷通常在早期采用后

    # 确定阶段
    stage = max(scores, key=lambda k: scores[k])

    # ---- 鸿沟风险评估 ----
    # 鸿沟出现在 early_adopters → early_majority 之间
    chasm_risk = 0.0
    chasm_evidence: list[str] = []

    if stage in ("early_adopters", "innovators"):
        # 检查是否有鸿沟迹象
        if tech_ratio > 0.5 and enterprise_ratio < 0.2:
            chasm_risk += 0.3
            chasm_evidence.append("技术用户多但企业采纳低")
        if mainstream == 0 and tech_blogs > 0:
            chasm_risk += 0.2
            chasm_evidence.append("主流媒体无报道")
        if media_sent < 0:
            chasm_risk += 0.2
            chasm_evidence.append("媒体情感偏负面")
        if growth > 0.5:
            chasm_risk -= 0.1  # 高增长降低鸿沟风险
        chasm_risk = _clamp(chasm_risk, 0, 1)

    # 建议
    recommendations = {
        "innovators": "关注技术验证和早期用户反馈，建立核心社区",
        "early_adopters": "寻找灯塔客户，打造标杆案例，准备跨越鸿沟",
        "early_majority": "标准化产品，优化用户体验，扩大销售渠道",
        "late_majority": "压缩成本，简化使用流程，提供成熟的解决方案",
        "laggards": "维护存量客户，考虑产品转型或退出策略",
    }

    return {
        "stage": stage,
        "stage_cn": _ADOPTION_STAGES[stage],
        "evidence": evidence,
        "chasm_risk": round(chasm_risk, 2),
        "chasm_evidence": chasm_evidence,
        "recommendation": recommendations[stage],
        "scores": {k: round(v, 2) for k, v in scores.items()},
    }


# ============================================================
# Porter 五力分析
# ============================================================

def build_porter_five_forces(
    competition_data: dict,
    market_data: dict,
) -> dict:
    """
    构建 Porter 五力模型分析。

    每一力评分 1-5 (1=低, 5=高)。

    参数:
        competition_data: 竞争数据:
            - num_competitors (int): 竞争者数量
            - market_concentration (float): 市场集中度 (HHI, 0-10000)
            - competitor_similarity (float): 竞品同质化程度 (0-1)
            - exit_barriers (str): "low"/"medium"/"high"
        market_data: 市场数据:
            - growth_rate (float): 市场增长率
            - capital_requirement (float): 进入所需资本（相对值 1-10）
            - regulation_level (str): "low"/"medium"/"high"
            - substitute_count (int): 替代品数量
            - substitute_quality (float): 替代品质量 (0-1)
            - buyer_concentration (float): 买家集中度 (0-1)
            - switching_cost (str): "low"/"medium"/"high"
            - supplier_concentration (float): 供应商集中度 (0-1)
            - input_uniqueness (str): "low"/"medium"/"high"

    返回:
        {rivalry, new_entrants, substitutes, buyer_power, supplier_power,
         overall_score, interpretation, details}
    """
    comp = competition_data or {}
    mkt = market_data or {}

    details: dict[str, list[str]] = defaultdict(list)

    # ---- 1. 现有竞争者的竞争强度 (rivalry) ----
    rivalry = 3.0

    num_comp = _safe_int(comp.get("num_competitors"), 5)
    if num_comp > 20:
        rivalry += 1
        details["rivalry"].append(f"竞争者众多 ({num_comp})")
    elif num_comp < 5:
        rivalry -= 1
        details["rivalry"].append(f"竞争者较少 ({num_comp})")

    hhi = _safe_float(comp.get("market_concentration"), 1500)
    if hhi < 1000:
        rivalry += 0.5
        details["rivalry"].append("市场分散 (HHI<1000)")
    elif hhi > 2500:
        rivalry -= 0.5
        details["rivalry"].append("市场集中 (HHI>2500)")

    similarity = _safe_float(comp.get("competitor_similarity"), 0.5)
    if similarity > 0.7:
        rivalry += 0.5
        details["rivalry"].append(f"产品同质化严重 ({similarity:.0%})")

    growth = _safe_float(mkt.get("growth_rate"), 0.05)
    if growth < 0.02:
        rivalry += 0.5
        details["rivalry"].append("低增长市场，竞争加剧")
    elif growth > 0.2:
        rivalry -= 0.5
        details["rivalry"].append("高增长市场，竞争压力较小")

    exit_barriers = (comp.get("exit_barriers") or "medium").lower()
    if exit_barriers == "high":
        rivalry += 0.5
        details["rivalry"].append("退出壁垒高")

    rivalry = _clamp(round(rivalry), 1, 5)

    # ---- 2. 新进入者的威胁 (new_entrants) ----
    new_entrants = 3.0

    capital_req = _safe_float(mkt.get("capital_requirement"), 5)
    if capital_req >= 8:
        new_entrants -= 1
        details["new_entrants"].append("资本要求高，进入门槛高")
    elif capital_req <= 3:
        new_entrants += 1
        details["new_entrants"].append("资本要求低，容易进入")

    regulation = (mkt.get("regulation_level") or "medium").lower()
    if regulation == "high":
        new_entrants -= 1
        details["new_entrants"].append("监管严格，新玩家难以进入")
    elif regulation == "low":
        new_entrants += 0.5
        details["new_entrants"].append("监管宽松")

    if growth > 0.15:
        new_entrants += 0.5
        details["new_entrants"].append("高增长吸引新进入者")

    new_entrants = _clamp(round(new_entrants), 1, 5)

    # ---- 3. 替代品的威胁 (substitutes) ----
    substitutes = 3.0

    sub_count = _safe_int(mkt.get("substitute_count"), 3)
    if sub_count > 5:
        substitutes += 1
        details["substitutes"].append(f"替代品多 ({sub_count} 种)")
    elif sub_count <= 1:
        substitutes -= 1
        details["substitutes"].append("替代品少")

    sub_quality = _safe_float(mkt.get("substitute_quality"), 0.5)
    if sub_quality > 0.7:
        substitutes += 1
        details["substitutes"].append("替代品质量高")
    elif sub_quality < 0.3:
        substitutes -= 1
        details["substitutes"].append("替代品质量低")

    substitutes = _clamp(round(substitutes), 1, 5)

    # ---- 4. 买家议价能力 (buyer_power) ----
    buyer_power = 3.0

    buyer_conc = _safe_float(mkt.get("buyer_concentration"), 0.3)
    if buyer_conc > 0.5:
        buyer_power += 1
        details["buyer_power"].append("买家集中度高，议价能力强")
    elif buyer_conc < 0.1:
        buyer_power -= 1
        details["buyer_power"].append("买家分散，议价能力弱")

    switching = (mkt.get("switching_cost") or "medium").lower()
    if switching == "low":
        buyer_power += 0.5
        details["buyer_power"].append("转换成本低，买家容易更换")
    elif switching == "high":
        buyer_power -= 0.5
        details["buyer_power"].append("转换成本高，买家粘性强")

    buyer_power = _clamp(round(buyer_power), 1, 5)

    # ---- 5. 供应商议价能力 (supplier_power) ----
    supplier_power = 3.0

    supplier_conc = _safe_float(mkt.get("supplier_concentration"), 0.3)
    if supplier_conc > 0.5:
        supplier_power += 1
        details["supplier_power"].append("供应商集中度高")
    elif supplier_conc < 0.1:
        supplier_power -= 1
        details["supplier_power"].append("供应商分散")

    input_unique = (mkt.get("input_uniqueness") or "medium").lower()
    if input_unique == "high":
        supplier_power += 1
        details["supplier_power"].append("供应商提供独特/专有资源")
    elif input_unique == "low":
        supplier_power -= 0.5
        details["supplier_power"].append("供应商资源通用性强")

    supplier_power = _clamp(round(supplier_power), 1, 5)

    # ---- 综合评估 ----
    forces = {
        "rivalry": int(rivalry),
        "new_entrants": int(new_entrants),
        "substitutes": int(substitutes),
        "buyer_power": int(buyer_power),
        "supplier_power": int(supplier_power),
    }
    overall_score = round(sum(forces.values()) / 5, 1)

    if overall_score >= 4:
        interpretation = "行业竞争极为激烈，利润空间有限，需要强大的差异化优势"
    elif overall_score >= 3:
        interpretation = "行业竞争较为激烈，需要明确的竞争策略和持续创新"
    elif overall_score >= 2:
        interpretation = "行业竞争适中，有一定的盈利空间，关注主要威胁来源"
    else:
        interpretation = "行业竞争压力小，有较好的盈利环境"

    return {
        **forces,
        "overall_score": overall_score,
        "interpretation": interpretation,
        "details": dict(details),
    }


# ============================================================
# 蓝海战略画布
# ============================================================

def build_strategy_canvas(
    competitors: list[dict],
    dimensions: list[str],
) -> dict:
    """
    构建蓝海战略画布。

    在各竞争维度上对比竞品评分，识别消除/减少/提升/创造方向。

    参数:
        competitors: 竞品列表，每项包含:
            - name (str): 竞品名称
            - scores (dict): {dimension: score(1-10)} 各维度评分
            - is_self (bool, 可选): 是否为自身产品
        dimensions: 分析维度列表，如 ["价格", "功能丰富度", "易用性", "售后"]

    返回:
        {canvas_data, eliminate, reduce, raise, create, industry_average}
    """
    if not competitors or not dimensions:
        return {
            "canvas_data": {},
            "eliminate": [],
            "reduce": [],
            "raise": [],
            "create": [],
            "industry_average": {},
        }

    # 构建画布数据
    canvas_data: dict[str, dict[str, float]] = {}
    self_scores: dict[str, float] = {}
    other_scores: dict[str, list[float]] = defaultdict(list)

    for comp in competitors:
        name = comp.get("name", "未知")
        scores = comp.get("scores", {})
        is_self = comp.get("is_self", False)

        comp_row: dict[str, float] = {}
        for dim in dimensions:
            score = _safe_float(scores.get(dim), default=5.0)
            score = _clamp(score, 1, 10)
            comp_row[dim] = score

            if is_self:
                self_scores[dim] = score
            else:
                other_scores[dim].append(score)

        canvas_data[name] = comp_row

    # 计算行业平均值
    industry_average: dict[str, float] = {}
    for dim in dimensions:
        values = other_scores.get(dim, [])
        if values:
            industry_average[dim] = round(sum(values) / len(values), 1)
        else:
            # 如果没有非自身竞品，使用所有数据
            all_vals = [canvas_data[c].get(dim, 5) for c in canvas_data]
            industry_average[dim] = round(sum(all_vals) / max(len(all_vals), 1), 1)

    # ERRC 分析（消除-减少-提升-创造）
    eliminate: list[dict] = []
    reduce: list[dict] = []
    raise_list: list[dict] = []
    create: list[dict] = []

    for dim in dimensions:
        avg = industry_average.get(dim, 5)
        my_score = self_scores.get(dim)

        # 所有竞品在该维度的标准差
        all_scores = [canvas_data[c].get(dim, 5) for c in canvas_data]
        mean_all = sum(all_scores) / max(len(all_scores), 1)
        variance = sum((s - mean_all) ** 2 for s in all_scores) / max(len(all_scores), 1)
        std_dev = math.sqrt(variance)

        entry = {
            "dimension": dim,
            "industry_average": avg,
            "std_dev": round(std_dev, 2),
        }

        if my_score is not None:
            entry["self_score"] = my_score

        # 维度分类逻辑
        if avg <= 3 and std_dev < 1.5:
            # 行业都不重视且差异小 → 可考虑消除
            eliminate.append({**entry, "reason": "行业整体评分低且差异小，可能是非核心维度"})
        elif my_score is not None and my_score > avg + 1.5 and avg < 6:
            # 自己远高于行业但行业不高 → 可考虑减少投入
            reduce.append({**entry, "reason": f"自身评分 ({my_score}) 远高于行业 ({avg})，可适当减少投入"})
        elif avg >= 7 and (my_score is None or my_score < avg):
            # 行业标准高但自己不够 → 需要提升
            raise_list.append({**entry, "reason": f"行业标准较高 ({avg})，需要提升以保持竞争力"})

    # 创造：找出所有竞品都低分（<4）的维度 → 机会
    for dim in dimensions:
        all_vals = [canvas_data[c].get(dim, 5) for c in canvas_data]
        if all_vals and max(all_vals) < 4:
            create.append({
                "dimension": dim,
                "max_score": max(all_vals),
                "reason": "所有竞品在此维度评分均低，可能是蓝海机会",
            })

    return {
        "canvas_data": canvas_data,
        "eliminate": eliminate,
        "reduce": reduce,
        "raise": raise_list,
        "create": create,
        "industry_average": industry_average,
    }


# ============================================================
# 评论增速分析
# ============================================================

def analyze_review_velocity(reviews: list[dict]) -> dict:
    """
    追踪评论数量的时间变化率。

    分析整体及各产品的评论增速和加速度。

    参数:
        reviews: 评论列表，每项包含:
            - product (str): 产品名称
            - date (str): 评论日期，格式 "YYYY-MM-DD" 或 "YYYY-MM"
            - text (str, 可选): 评论文本

    返回:
        {overall_velocity, by_product, trend, monthly_counts}
    """
    if not reviews:
        return {
            "overall_velocity": 0.0,
            "by_product": [],
            "trend": "unknown",
            "monthly_counts": {},
        }

    # 按月统计评论数
    monthly_total: Counter = Counter()
    monthly_by_product: dict[str, Counter] = defaultdict(Counter)

    for review in reviews:
        if not isinstance(review, dict):
            continue
        date_str = review.get("date", "")
        product = review.get("product", "unknown")

        # 提取年月
        month_match = re.match(r'(\d{4})-(\d{2})', str(date_str))
        if not month_match:
            continue
        month_key = f"{month_match.group(1)}-{month_match.group(2)}"

        monthly_total[month_key] += 1
        monthly_by_product[product][month_key] += 1

    if not monthly_total:
        return {
            "overall_velocity": 0.0,
            "by_product": [],
            "trend": "unknown",
            "monthly_counts": {},
        }

    # 排序月份
    sorted_months = sorted(monthly_total.keys())

    # 计算总体速度和加速度
    overall_velocity, overall_acceleration = _compute_velocity(
        sorted_months, monthly_total
    )

    # 各产品的速度
    by_product: list[dict] = []
    for product, counts in monthly_by_product.items():
        prod_months = sorted(counts.keys())
        vel, acc = _compute_velocity(prod_months, counts)
        by_product.append({
            "name": product,
            "velocity": round(vel, 2),
            "acceleration": round(acc, 2),
            "total_reviews": sum(counts.values()),
            "active_months": len(prod_months),
        })

    # 按速度降序
    by_product.sort(key=lambda x: x["velocity"], reverse=True)

    # 判断整体趋势
    if overall_acceleration > 0.5:
        trend = "accelerating"
    elif overall_acceleration < -0.5:
        trend = "decelerating"
    elif overall_velocity > 1.0:
        trend = "growing"
    elif overall_velocity < -1.0:
        trend = "shrinking"
    else:
        trend = "stable"

    return {
        "overall_velocity": round(overall_velocity, 2),
        "overall_acceleration": round(overall_acceleration, 2),
        "by_product": by_product,
        "trend": trend,
        "monthly_counts": dict(monthly_total),
    }


def _compute_velocity(
    sorted_months: list[str],
    counts: dict[str, int] | Counter,
) -> tuple[float, float]:
    """
    计算评论增速（velocity）和加速度（acceleration）。

    velocity: 近期月平均评论数的变化率
    acceleration: velocity 的变化率

    返回:
        (velocity, acceleration)
    """
    if len(sorted_months) < 2:
        total = sum(counts.get(m, 0) for m in sorted_months)
        return (float(total), 0.0)

    values = [counts.get(m, 0) for m in sorted_months]

    # 速度：最近 3 个月均值 vs 之前 3 个月均值
    recent_window = min(3, len(values))
    earlier_window = min(3, len(values) - recent_window)

    recent_avg = sum(values[-recent_window:]) / recent_window
    if earlier_window > 0:
        earlier_avg = sum(values[-(recent_window + earlier_window):-recent_window]) / earlier_window
    else:
        earlier_avg = recent_avg

    if earlier_avg == 0:
        velocity = float(recent_avg)
    else:
        velocity = (recent_avg - earlier_avg) / earlier_avg * 100  # 百分比变化

    # 加速度：月间增量的变化趋势
    if len(values) >= 3:
        deltas = [values[i] - values[i - 1] for i in range(1, len(values))]
        if len(deltas) >= 2:
            recent_delta = sum(deltas[-2:]) / 2
            earlier_delta = sum(deltas[:-2]) / max(len(deltas) - 2, 1)
            acceleration = recent_delta - earlier_delta
        else:
            acceleration = deltas[-1] if deltas else 0.0
    else:
        acceleration = 0.0

    return (velocity, acceleration)


# ============================================================
# 测试示例
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("技术创新追踪器 — 测试示例")
    print("=" * 60)

    # 测试技术壁垒评估
    tech_texts = [
        "The company holds several patents on their proprietary neural engine.",
        "Years of research went into developing this custom silicon chip.",
        "There are open source alternatives like TensorFlow and PyTorch.",
        "The network effect makes it hard for new entrants to compete.",
        "这项技术有很深的专利壁垒，核心算法是自研的。",
    ]
    patents = [
        {"title": "Neural Network Optimization Method", "holder": "TechCorp", "citations": 45},
        {"title": "Custom Silicon Architecture for AI", "holder": "TechCorp", "citations": 32},
        {"title": "Data Processing Pipeline", "holder": "TechCorp", "citations": 12},
    ]

    barriers = assess_tech_barriers(tech_texts, patents)
    print("\n--- 技术壁垒评估 ---")
    for k, v in barriers.items():
        print(f"  {k}: {v}")

    # 测试采纳曲线
    adoption = position_on_adoption_curve(
        trend_data={"growth_rate": 0.8, "penetration_rate": 0.05, "search_trend": "rising"},
        user_profile={"tech_savvy_ratio": 0.7, "enterprise_ratio": 0.1},
        media_coverage={"mainstream_mentions": 5, "tech_blog_mentions": 150, "sentiment": 0.6},
    )
    print("\n--- 采纳曲线定位 ---")
    for k, v in adoption.items():
        print(f"  {k}: {v}")

    # 测试 Porter 五力
    porter = build_porter_five_forces(
        competition_data={
            "num_competitors": 25,
            "market_concentration": 800,
            "competitor_similarity": 0.7,
            "exit_barriers": "medium",
        },
        market_data={
            "growth_rate": 0.05,
            "capital_requirement": 3,
            "regulation_level": "low",
            "substitute_count": 4,
            "substitute_quality": 0.6,
            "buyer_concentration": 0.2,
            "switching_cost": "low",
            "supplier_concentration": 0.4,
            "input_uniqueness": "medium",
        },
    )
    print("\n--- Porter 五力分析 ---")
    for k, v in porter.items():
        print(f"  {k}: {v}")

    # 测试蓝海画布
    canvas = build_strategy_canvas(
        competitors=[
            {"name": "ProductA", "scores": {"价格": 3, "功能": 8, "易用性": 5, "客服": 4, "设计": 7}},
            {"name": "ProductB", "scores": {"价格": 7, "功能": 5, "易用性": 8, "客服": 3, "设计": 4}},
            {"name": "我们", "scores": {"价格": 5, "功能": 6, "易用性": 7, "客服": 8, "设计": 6}, "is_self": True},
        ],
        dimensions=["价格", "功能", "易用性", "客服", "设计"],
    )
    print("\n--- 蓝海画布 ---")
    print(f"  画布数据: {canvas['canvas_data']}")
    print(f"  行业平均: {canvas['industry_average']}")
    print(f"  消除: {canvas['eliminate']}")
    print(f"  减少: {canvas['reduce']}")
    print(f"  提升: {canvas['raise']}")
    print(f"  创造: {canvas['create']}")

    # 测试评论增速
    sample_reviews = [
        {"product": "AppX", "date": "2025-01", "text": "Great!"},
        {"product": "AppX", "date": "2025-02", "text": "Nice"},
        {"product": "AppX", "date": "2025-03", "text": "Good"},
        {"product": "AppX", "date": "2025-03", "text": "Love it"},
        {"product": "AppX", "date": "2025-04", "text": "Amazing"},
        {"product": "AppX", "date": "2025-04", "text": "Best"},
        {"product": "AppX", "date": "2025-04", "text": "Wow"},
        {"product": "AppY", "date": "2025-01", "text": "OK"},
        {"product": "AppY", "date": "2025-01", "text": "Fine"},
        {"product": "AppY", "date": "2025-02", "text": "Meh"},
        {"product": "AppY", "date": "2025-03", "text": "Decent"},
        {"product": "AppY", "date": "2025-04", "text": "OK"},
    ]
    velocity = analyze_review_velocity(sample_reviews)
    print("\n--- 评论增速 ---")
    for k, v in velocity.items():
        print(f"  {k}: {v}")

    # 边界测试
    print("\n--- 边界测试 ---")
    print(f"  空壁垒评估: barrier_level={assess_tech_barriers([], [])['barrier_level']}")
    print(f"  空采纳曲线: stage={position_on_adoption_curve({}, {}, {})['stage']}")
    print(f"  空五力分析: overall={build_porter_five_forces({}, {})['overall_score']}")
    print(f"  空画布: {build_strategy_canvas([], [])}")
    print(f"  空增速: trend={analyze_review_velocity([])['trend']}")

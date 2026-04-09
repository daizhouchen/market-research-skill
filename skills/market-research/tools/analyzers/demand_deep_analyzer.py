"""
用户需求深度分析器

从用户评论和反馈文本中提取深层需求洞察：
JTBD 分析、机会评分、迁移路径、价格敏感度、主题聚类和特征共现分析。
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


def _tokenize(text: str) -> list[str]:
    """
    简单分词：英文按空格/标点拆分并小写化，中文按字符拆分。
    返回去除停用词后的 token 列表。
    """
    # 先用正则拆分出中英文 token
    tokens: list[str] = []
    # 英文单词
    en_words = re.findall(r'[a-zA-Z]+(?:\'[a-zA-Z]+)?', text.lower())
    tokens.extend(en_words)
    # 中文：提取连续中文字符，每 2-4 字为一个 gram
    zh_chars = re.findall(r'[\u4e00-\u9fff]+', text)
    for seg in zh_chars:
        # 生成 bigram 和 trigram
        for n in (2, 3):
            for i in range(len(seg) - n + 1):
                tokens.append(seg[i:i + n])
    return tokens


# 英文停用词（简化集）
_STOP_WORDS_EN = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "shall",
    "should", "may", "might", "must", "can", "could", "i", "you", "he",
    "she", "it", "we", "they", "me", "him", "her", "us", "them", "my",
    "your", "his", "its", "our", "their", "this", "that", "these", "those",
    "and", "but", "or", "nor", "not", "so", "yet", "for", "in", "on",
    "at", "to", "of", "by", "with", "from", "up", "about", "into",
    "through", "during", "before", "after", "above", "below", "between",
    "out", "off", "over", "under", "again", "further", "then", "once",
    "here", "there", "when", "where", "why", "how", "all", "each",
    "every", "both", "few", "more", "most", "other", "some", "such",
    "no", "only", "own", "same", "than", "too", "very", "just",
}

# 中文停用词
_STOP_WORDS_ZH = {
    "的", "了", "在", "是", "我", "有", "和", "就", "不", "人",
    "都", "一", "一个", "上", "也", "很", "到", "说", "要", "去",
    "你", "会", "着", "没有", "看", "好", "自己", "这", "他", "她",
    "吗", "吧", "啊", "呢", "哦", "嗯", "那", "还", "但", "而",
    "把", "被", "让", "给", "用", "比", "从", "对", "做", "个",
}


def _remove_stop_words(tokens: list[str]) -> list[str]:
    """移除停用词。"""
    return [t for t in tokens if t not in _STOP_WORDS_EN and t not in _STOP_WORDS_ZH and len(t) > 1]


def _simple_sentiment(text: str) -> float:
    """
    简单情感评分 (-1 到 1)。
    基于正负面关键词计数。
    """
    positive = {
        "good", "great", "love", "excellent", "amazing", "best", "perfect",
        "awesome", "fantastic", "wonderful", "nice", "happy", "easy",
        "好", "不错", "喜欢", "满意", "棒", "优秀", "方便", "推荐", "值得",
    }
    negative = {
        "bad", "terrible", "awful", "worst", "hate", "poor", "horrible",
        "disappointing", "broken", "slow", "expensive", "difficult", "annoying",
        "差", "烂", "失望", "难用", "贵", "垃圾", "退货", "后悔", "问题",
    }

    words = set(re.findall(r'[a-zA-Z]+', text.lower()))
    zh_chars = set(re.findall(r'[\u4e00-\u9fff]{1,4}', text))
    all_tokens = words | zh_chars

    pos_count = len(all_tokens & positive)
    neg_count = len(all_tokens & negative)
    total = pos_count + neg_count
    if total == 0:
        return 0.0
    return (pos_count - neg_count) / total


# ============================================================
# JTBD 提取
# ============================================================

# JTBD 识别模式
_JTBD_PATTERNS_EN = [
    # "When I ... I want to ... so that I can ..."
    re.compile(
        r'when\s+(?:I|i|we)\s+(.+?),?\s*(?:I|i|we)\s+(?:want|need|wish)\s+(?:to\s+)?(.+?)'
        r'(?:\s*(?:so\s+(?:that\s+)?|because)\s*(.+?))?[.\n]',
        re.IGNORECASE,
    ),
    # "I need ... for/to ..."
    re.compile(
        r'(?:I|i|we)\s+(?:need|want)\s+(.+?)\s+(?:for|to|so)\s+(.+?)[.\n]',
        re.IGNORECASE,
    ),
    # "I wish ... could/would ..."
    re.compile(
        r'(?:I|i|we)\s+wish\s+(.+?)\s+(?:could|would)\s+(.+?)[.\n]',
        re.IGNORECASE,
    ),
]

_JTBD_PATTERNS_ZH = [
    # "当我...的时候，我想/需要...这样就能..."
    re.compile(r'当[我我们](.+?)(?:的时候|时)，?[我我们](?:想要?|需要|希望)(.+?)(?:这样[我就]就?能?(.+?))?[。\n]'),
    # "我需要...来/以便..."
    re.compile(r'[我我们](?:需要|想要)(.+?)(?:来|以便|用于)(.+?)[。\n]'),
    # "要是...就好了"
    re.compile(r'(?:要是|如果)[能有]?(.+?)就好了'),
]

# 任务类型关键词
_FUNCTIONAL_KEYWORDS = {
    "use", "do", "make", "create", "build", "find", "get", "manage", "track",
    "用", "做", "创建", "管理", "找", "完成", "处理", "操作", "设置",
}
_EMOTIONAL_KEYWORDS = {
    "feel", "enjoy", "relax", "stress", "worry", "confident", "comfortable",
    "感觉", "享受", "放松", "焦虑", "安心", "舒适", "开心", "满足",
}
_SOCIAL_KEYWORDS = {
    "look", "impress", "share", "show", "status", "professional", "cool",
    "面子", "炫耀", "分享", "展示", "专业", "身份", "格调", "档次",
}


def _classify_jtbd_type(text: str) -> str:
    """根据关键词判断 JTBD 任务类型。"""
    text_lower = text.lower()
    scores = {"functional": 0, "emotional": 0, "social": 0}

    for word in _FUNCTIONAL_KEYWORDS:
        if word in text_lower:
            scores["functional"] += 1
    for word in _EMOTIONAL_KEYWORDS:
        if word in text_lower:
            scores["emotional"] += 1
    for word in _SOCIAL_KEYWORDS:
        if word in text_lower:
            scores["social"] += 1

    if max(scores.values()) == 0:
        return "functional"  # 默认功能性
    return max(scores, key=lambda k: scores[k])


def _estimate_frequency(text: str) -> str:
    """从文本中估计行为频率。"""
    high_freq = {"daily", "everyday", "always", "constantly", "每天", "经常", "一直", "频繁", "总是"}
    med_freq = {"weekly", "often", "regularly", "每周", "定期", "时常"}
    low_freq = {"rarely", "sometimes", "occasionally", "偶尔", "有时", "很少"}

    text_lower = text.lower()
    for word in high_freq:
        if word in text_lower:
            return "high"
    for word in med_freq:
        if word in text_lower:
            return "medium"
    for word in low_freq:
        if word in text_lower:
            return "low"
    return "unknown"


def extract_jtbd(texts: list[str]) -> list[dict]:
    """
    从用户文本中提取 Jobs-to-be-Done。

    识别"当我...我想要...这样我就能..."模式，分类为功能/情感/社交任务。

    参数:
        texts: 用户评论/反馈文本列表

    返回:
        [{situation, motivation, outcome, type, frequency}]
    """
    if not texts:
        return []

    jobs: list[dict] = []
    seen: set[str] = set()  # 去重

    for text in texts:
        if not text or not isinstance(text, str):
            continue

        # 尝试英文模式
        for pattern in _JTBD_PATTERNS_EN:
            for match in pattern.finditer(text):
                groups = match.groups()
                situation = (groups[0] if len(groups) > 0 else "").strip()
                motivation = (groups[1] if len(groups) > 1 else "").strip()
                outcome = (groups[2] if len(groups) > 2 and groups[2] else "").strip()

                # 去重键
                key = f"{situation[:30]}|{motivation[:30]}"
                if key in seen or not motivation:
                    continue
                seen.add(key)

                combined = f"{situation} {motivation} {outcome}"
                jobs.append({
                    "situation": situation,
                    "motivation": motivation,
                    "outcome": outcome,
                    "type": _classify_jtbd_type(combined),
                    "frequency": _estimate_frequency(text),
                })

        # 尝试中文模式
        for pattern in _JTBD_PATTERNS_ZH:
            for match in pattern.finditer(text):
                groups = match.groups()
                situation = (groups[0] if len(groups) > 0 else "").strip()
                motivation = (groups[1] if len(groups) > 1 else "").strip()
                outcome = (groups[2] if len(groups) > 2 and groups[2] else "").strip()

                key = f"{situation[:30]}|{motivation[:30]}"
                if key in seen or not motivation:
                    continue
                seen.add(key)

                combined = f"{situation} {motivation} {outcome}"
                jobs.append({
                    "situation": situation,
                    "motivation": motivation,
                    "outcome": outcome,
                    "type": _classify_jtbd_type(combined),
                    "frequency": _estimate_frequency(text),
                })

    return jobs


# ============================================================
# 机会评分
# ============================================================

def calculate_opportunity_score(
    jtbd_list: list[dict],
    satisfaction_data: dict,
) -> list[dict]:
    """
    计算机会分数 = 重要性 - 满足度。

    分数越高表示未满足需求越大，市场机会越大。

    参数:
        jtbd_list: extract_jtbd 的输出列表
        satisfaction_data: 满足度数据，键为 motivation 文本，值为 dict:
            - importance (float): 重要性 0-10
            - satisfaction (float): 当前满足度 0-10

    返回:
        按机会分数降序排列的列表:
        [{motivation, type, importance, satisfaction, opportunity_score, priority}]
    """
    if not jtbd_list:
        return []

    results: list[dict] = []

    for job in jtbd_list:
        motivation = job.get("motivation", "")
        job_type = job.get("type", "functional")

        # 查找满足度数据：精确匹配或模糊匹配
        sat_info = satisfaction_data.get(motivation, {}) if satisfaction_data else {}

        if not sat_info:
            # 尝试模糊匹配（子串匹配）
            for key, val in (satisfaction_data or {}).items():
                if key in motivation or motivation in key:
                    sat_info = val
                    break

        importance = _safe_float(sat_info.get("importance"), default=5.0)
        satisfaction = _safe_float(sat_info.get("satisfaction"), default=5.0)

        # Ulwick ODI 公式: opportunity = importance + max(importance - satisfaction, 0)
        gap = max(importance - satisfaction, 0)
        opportunity_score = importance + gap

        # 优先级标签
        if opportunity_score >= 15:
            priority = "critical"
        elif opportunity_score >= 12:
            priority = "high"
        elif opportunity_score >= 8:
            priority = "medium"
        else:
            priority = "low"

        results.append({
            "motivation": motivation,
            "situation": job.get("situation", ""),
            "type": job_type,
            "importance": importance,
            "satisfaction": satisfaction,
            "opportunity_score": round(opportunity_score, 2),
            "priority": priority,
        })

    # 按机会分数降序排列
    results.sort(key=lambda x: x["opportunity_score"], reverse=True)
    return results


# ============================================================
# 迁移路径分析
# ============================================================

# 迁移模式
_MIGRATION_PATTERNS_EN = [
    re.compile(r'(?:switched|moved|migrated|changed)\s+from\s+(.+?)\s+to\s+(.+?)[\s,.\n]', re.IGNORECASE),
    re.compile(r'(?:replaced|ditched|dropped|left)\s+(.+?)\s+(?:for|with)\s+(.+?)[\s,.\n]', re.IGNORECASE),
    re.compile(r'(?:used\s+to\s+use|was\s+using|previously\s+used)\s+(.+?)[\s,]+(?:now|but\s+now|switched\s+to)\s+(.+?)[\s,.\n]', re.IGNORECASE),
]

_MIGRATION_PATTERNS_ZH = [
    re.compile(r'从(.+?)(?:换到|转到|切换到|迁移到|改用)了?(.+?)[\s,。\n]'),
    re.compile(r'(?:之前|以前|原来)用(?:的是)?(.+?)(?:，?现在|，?后来)(?:用|换成了?)(.+?)[\s,。\n]'),
    re.compile(r'抛弃了?(.+?)(?:，?选择了?|，?改用了?)(.+?)[\s,。\n]'),
]


def analyze_migration_paths(texts: list[str]) -> dict:
    """
    从用户评论中提取产品迁移路径。

    分析"从X换到Y"类评论，统计迁移流向和原因。

    参数:
        texts: 用户评论文本列表

    返回:
        {
            migrations: [{from_product, to_product, reason, count}],
            net_flow: {product_name: net_migration_count},
            top_gainers: [str],
            top_losers: [str],
        }
    """
    if not texts:
        return {"migrations": [], "net_flow": {}, "top_gainers": [], "top_losers": []}

    # 统计迁移：(from, to) -> {count, reasons}
    migration_counts: dict[tuple[str, str], dict] = defaultdict(
        lambda: {"count": 0, "reasons": []}
    )

    for text in texts:
        if not text or not isinstance(text, str):
            continue

        all_patterns = _MIGRATION_PATTERNS_EN + _MIGRATION_PATTERNS_ZH
        for pattern in all_patterns:
            for match in pattern.finditer(text):
                from_product = match.group(1).strip().rstrip(",.")
                to_product = match.group(2).strip().rstrip(",.")

                # 过滤掉太长或太短的匹配（可能是误匹配）
                if len(from_product) > 50 or len(to_product) > 50:
                    continue
                if len(from_product) < 2 or len(to_product) < 2:
                    continue

                key = (from_product.lower(), to_product.lower())
                migration_counts[key]["count"] += 1

                # 提取原因：匹配点后面的文本片段
                # 在匹配结束位置后取一段作为 reason
                end_pos = match.end()
                reason_text = text[end_pos:end_pos + 100].strip()
                # 清理：取到句号或换行
                reason_end = re.search(r'[.。\n]', reason_text)
                if reason_end:
                    reason_text = reason_text[:reason_end.start()].strip()
                if reason_text and len(reason_text) > 5:
                    migration_counts[key]["reasons"].append(reason_text)

    # 构建迁移列表
    migrations: list[dict] = []
    for (from_p, to_p), data in migration_counts.items():
        # 取最常见的原因
        reason = ""
        if data["reasons"]:
            reason_counter = Counter(data["reasons"])
            reason = reason_counter.most_common(1)[0][0]

        migrations.append({
            "from_product": from_p,
            "to_product": to_p,
            "reason": reason,
            "count": data["count"],
        })

    # 按迁移次数降序
    migrations.sort(key=lambda x: x["count"], reverse=True)

    # 计算净流入/流出
    net_flow: dict[str, int] = defaultdict(int)
    for m in migrations:
        net_flow[m["to_product"]] += m["count"]
        net_flow[m["from_product"]] -= m["count"]

    # 排序得出赢家和输家
    sorted_flow = sorted(net_flow.items(), key=lambda x: x[1], reverse=True)
    top_gainers = [name for name, flow in sorted_flow if flow > 0][:5]
    top_losers = [name for name, flow in sorted_flow if flow < 0][:5]

    return {
        "migrations": migrations,
        "net_flow": dict(net_flow),
        "top_gainers": top_gainers,
        "top_losers": top_losers,
    }


# ============================================================
# 价格敏感度分析
# ============================================================

_PRICE_PATTERNS = [
    re.compile(r'(?:costs?|priced?\s+at|pay|paid|worth|costs?\s+about)\s*[\$€£¥]?\s*(\d+(?:\.\d+)?)', re.IGNORECASE),
    re.compile(r'[\$€£¥]\s*(\d+(?:\.\d+)?)'),
    re.compile(r'(\d+(?:\.\d+)?)\s*(?:元|块|刀|美元|美金|rmb)', re.IGNORECASE),
]

_EXPENSIVE_WORDS = {
    "expensive", "overpriced", "costly", "pricey", "too much", "rip off",
    "贵", "太贵", "不值", "价格高", "性价比低", "坑", "割韭菜",
}
_CHEAP_WORDS = {
    "cheap", "affordable", "bargain", "value", "worth it", "reasonable",
    "便宜", "划算", "性价比高", "值", "实惠", "白菜价",
}
_WILLING_WORDS = {
    "would pay", "willing to pay", "worth", "shut up and take my money",
    "愿意付", "值这个价", "物有所值",
}


def analyze_price_sensitivity(
    texts: list[str],
    prices: list[float],
) -> dict:
    """
    分析价格敏感度。

    提取价格相关评论的情感，识别价格锚点和付费意愿。

    参数:
        texts: 用户评论文本列表
        prices: 产品价格列表（用于参考区间）

    返回:
        {anchors, segments, elasticity_estimate, willingness_range}
    """
    if not texts:
        return {
            "anchors": [],
            "segments": {},
            "elasticity_estimate": None,
            "willingness_range": {"low": 0, "high": 0},
        }

    mentioned_prices: list[float] = []
    sentiment_by_price: list[tuple[float, float]] = []  # (price, sentiment)
    expensive_count = 0
    cheap_count = 0
    willing_to_pay: list[float] = []

    for text in texts:
        if not text or not isinstance(text, str):
            continue
        text_lower = text.lower()

        # 提取提到的价格
        for pattern in _PRICE_PATTERNS:
            for match in pattern.finditer(text):
                try:
                    price_val = float(match.group(1))
                    if 0 < price_val < 1e8:  # 合理范围
                        mentioned_prices.append(price_val)
                        sentiment = _simple_sentiment(text)
                        sentiment_by_price.append((price_val, sentiment))
                except (ValueError, IndexError):
                    pass

        # 统计贵/便宜评价
        for word in _EXPENSIVE_WORDS:
            if word in text_lower:
                expensive_count += 1
                break
        for word in _CHEAP_WORDS:
            if word in text_lower:
                cheap_count += 1
                break

        # 提取付费意愿
        for word in _WILLING_WORDS:
            if word in text_lower:
                for pattern in _PRICE_PATTERNS:
                    for match in pattern.finditer(text):
                        try:
                            willing_to_pay.append(float(match.group(1)))
                        except (ValueError, IndexError):
                            pass
                break

    # 计算价格锚点（用户心中的参考价格）
    anchors: list[dict] = []
    if mentioned_prices:
        price_counter = Counter(round(p, -1) for p in mentioned_prices)  # 按十位取整聚合
        for price, count in price_counter.most_common(5):
            anchors.append({"price": price, "mentions": count})

    # 用户分群
    total_price_opinions = expensive_count + cheap_count
    segments = {
        "price_sensitive": {
            "ratio": expensive_count / max(total_price_opinions, 1),
            "count": expensive_count,
            "description": "认为价格偏高的用户",
        },
        "value_seekers": {
            "ratio": cheap_count / max(total_price_opinions, 1),
            "count": cheap_count,
            "description": "认为性价比高的用户",
        },
        "neutral": {
            "ratio": max(0, len(texts) - total_price_opinions) / max(len(texts), 1),
            "count": max(0, len(texts) - total_price_opinions),
            "description": "未提及价格的用户",
        },
    }

    # 弹性估算：价格与情感的相关性
    elasticity_estimate = _estimate_price_elasticity(sentiment_by_price, prices)

    # 付费意愿区间
    if willing_to_pay:
        willingness_range = {
            "low": round(min(willing_to_pay), 2),
            "high": round(max(willing_to_pay), 2),
            "median": round(sorted(willing_to_pay)[len(willing_to_pay) // 2], 2),
        }
    elif mentioned_prices:
        # 用提到的价格区间作为近似
        sorted_prices = sorted(mentioned_prices)
        p25_idx = max(0, len(sorted_prices) // 4 - 1)
        p75_idx = min(len(sorted_prices) - 1, len(sorted_prices) * 3 // 4)
        willingness_range = {
            "low": round(sorted_prices[p25_idx], 2),
            "high": round(sorted_prices[p75_idx], 2),
            "median": round(sorted_prices[len(sorted_prices) // 2], 2),
        }
    else:
        willingness_range = {"low": 0, "high": 0, "median": 0}

    return {
        "anchors": anchors,
        "segments": segments,
        "elasticity_estimate": elasticity_estimate,
        "willingness_range": willingness_range,
    }


def _estimate_price_elasticity(
    sentiment_by_price: list[tuple[float, float]],
    reference_prices: list[float],
) -> float | None:
    """
    简单线性相关估算价格弹性。
    如果价格越高情感越负面 → 弹性高（敏感）。
    返回 -1 到 1 的相关系数，None 表示数据不足。
    """
    if len(sentiment_by_price) < 3:
        return None

    prices = [p for p, _ in sentiment_by_price]
    sentiments = [s for _, s in sentiment_by_price]

    n = len(prices)
    mean_p = sum(prices) / n
    mean_s = sum(sentiments) / n

    # Pearson 相关系数
    cov = sum((p - mean_p) * (s - mean_s) for p, s in zip(prices, sentiments)) / n
    std_p = math.sqrt(sum((p - mean_p) ** 2 for p in prices) / n)
    std_s = math.sqrt(sum((s - mean_s) ** 2 for s in sentiments) / n)

    if std_p == 0 or std_s == 0:
        return None

    correlation = cov / (std_p * std_s)
    return round(correlation, 3)


# ============================================================
# 主题聚类
# ============================================================

def cluster_topics(texts: list[str], n_topics: int = 8) -> list[dict]:
    """
    从评论文本中提取并聚类主题。

    使用词频共现进行简单聚类，不依赖 ML 库。

    参数:
        texts: 评论文本列表
        n_topics: 目标主题数量

    返回:
        [{topic, keywords, sentiment, frequency, trend}]
    """
    if not texts:
        return []

    n_topics = max(1, min(n_topics, 20))

    # 步骤 1: 提取所有文本的 token
    doc_tokens: list[list[str]] = []
    for text in texts:
        if not text or not isinstance(text, str):
            continue
        tokens = _remove_stop_words(_tokenize(text))
        if tokens:
            doc_tokens.append(tokens)

    if not doc_tokens:
        return []

    # 步骤 2: 统计词频（文档频率）
    doc_freq: Counter = Counter()
    word_freq: Counter = Counter()
    for tokens in doc_tokens:
        unique_tokens = set(tokens)
        for t in unique_tokens:
            doc_freq[t] += 1
        for t in tokens:
            word_freq[t] += 1

    # 过滤：只保留出现在至少 2 个文档中且频率不超过 80% 文档的词
    num_docs = len(doc_tokens)
    min_df = max(2, num_docs * 0.02)
    max_df = num_docs * 0.8
    valid_words = {
        w for w, df in doc_freq.items()
        if min_df <= df <= max_df
    }

    if not valid_words:
        # 放宽条件
        valid_words = {w for w, df in doc_freq.items() if df >= 1}

    if not valid_words:
        return []

    # 步骤 3: 构建共现矩阵（窗口大小=整个文档）
    cooccurrence: dict[str, Counter] = defaultdict(Counter)
    for tokens in doc_tokens:
        filtered = [t for t in tokens if t in valid_words]
        unique = set(filtered)
        for w1 in unique:
            for w2 in unique:
                if w1 != w2:
                    cooccurrence[w1][w2] += 1

    # 步骤 4: 贪心聚类 — 每次选一个种子词，将与它共现最多的词归入同一主题
    used_words: set[str] = set()
    topics: list[dict] = []

    # 按词频排序，频率最高的词作为种子
    sorted_words = sorted(valid_words, key=lambda w: word_freq[w], reverse=True)

    for seed in sorted_words:
        if seed in used_words:
            continue
        if len(topics) >= n_topics:
            break

        # 找与种子共现最多的词
        cluster_words = [seed]
        used_words.add(seed)

        candidates = sorted(
            cooccurrence[seed].items(),
            key=lambda x: x[1],
            reverse=True,
        )
        for word, count in candidates:
            if word in used_words:
                continue
            if len(cluster_words) >= 6:  # 每个主题最多 6 个关键词
                break
            cluster_words.append(word)
            used_words.add(word)

        if len(cluster_words) < 2:
            used_words.discard(seed)
            continue

        # 计算主题的情感和频率
        topic_texts = [
            text for text, tokens in zip(texts, doc_tokens)
            if text and any(w in text.lower() for w in cluster_words[:3])
        ]

        avg_sentiment = 0.0
        if topic_texts:
            sentiments = [_simple_sentiment(t) for t in topic_texts]
            avg_sentiment = sum(sentiments) / len(sentiments)

        frequency = len(topic_texts)

        # 趋势：简单地比较前半和后半的频率
        half = len(texts) // 2
        first_half_count = sum(
            1 for text in texts[:half]
            if text and any(w in text.lower() for w in cluster_words[:3])
        )
        second_half_count = sum(
            1 for text in texts[half:]
            if text and any(w in text.lower() for w in cluster_words[:3])
        )

        if second_half_count > first_half_count * 1.3:
            trend = "rising"
        elif first_half_count > second_half_count * 1.3:
            trend = "declining"
        else:
            trend = "stable"

        # 主题名称：取前 2 个关键词拼接
        topic_name = " + ".join(cluster_words[:2])

        topics.append({
            "topic": topic_name,
            "keywords": cluster_words,
            "sentiment": round(avg_sentiment, 3),
            "frequency": frequency,
            "trend": trend,
        })

    # 按频率降序排列
    topics.sort(key=lambda x: x["frequency"], reverse=True)
    return topics


# ============================================================
# 特征共现分析
# ============================================================

def analyze_feature_cooccurrence(texts: list[str]) -> dict:
    """
    构建特征共现矩阵，识别必备组合和差异化组合。

    参数:
        texts: 用户评论文本列表

    返回:
        {
            matrix: {feature: {feature: cooccurrence_count}},
            must_have_pairs: [(feat_a, feat_b, rate)],  # 共现率 > 70%
            differentiator_pairs: [(feat_a, feat_b, rate)],  # 共现率 < 20% 但各自频率高
        }
    """
    if not texts:
        return {"matrix": {}, "must_have_pairs": [], "differentiator_pairs": []}

    # 提取特征词（高频名词短语作为特征）
    all_doc_features: list[set[str]] = []
    feature_counter: Counter = Counter()

    for text in texts:
        if not text or not isinstance(text, str):
            continue
        tokens = _remove_stop_words(_tokenize(text))
        features = set(tokens)
        all_doc_features.append(features)
        for f in features:
            feature_counter[f] += 1

    if not all_doc_features:
        return {"matrix": {}, "must_have_pairs": [], "differentiator_pairs": []}

    num_docs = len(all_doc_features)

    # 只保留出现频率在 5%-60% 之间的特征（太普遍或太稀少的无分析价值）
    min_count = max(2, num_docs * 0.05)
    max_count = num_docs * 0.6
    top_features = [
        f for f, c in feature_counter.most_common(100)
        if min_count <= c <= max_count
    ]

    if len(top_features) < 2:
        # 放宽条件
        top_features = [f for f, _ in feature_counter.most_common(30) if feature_counter[f] >= 2]

    if len(top_features) < 2:
        return {"matrix": {}, "must_have_pairs": [], "differentiator_pairs": []}

    # 构建共现矩阵
    matrix: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    feature_set = set(top_features)

    for doc_features in all_doc_features:
        present = doc_features & feature_set
        for f1 in present:
            for f2 in present:
                if f1 != f2:
                    matrix[f1][f2] += 1

    # 计算共现率并分类
    must_have_pairs: list[tuple[str, str, float]] = []
    differentiator_pairs: list[tuple[str, str, float]] = []
    seen_pairs: set[tuple[str, str]] = set()

    for f1 in top_features:
        count_f1 = feature_counter[f1]
        for f2 in top_features:
            if f1 >= f2:  # 避免重复和自身
                continue
            pair_key = (f1, f2)
            if pair_key in seen_pairs:
                continue
            seen_pairs.add(pair_key)

            cooccur = matrix[f1].get(f2, 0)
            count_f2 = feature_counter[f2]
            min_count_pair = min(count_f1, count_f2)

            if min_count_pair == 0:
                continue

            # 共现率 = 共现次数 / min(各自出现次数)
            rate = cooccur / min_count_pair

            if rate > 0.7:
                must_have_pairs.append((f1, f2, round(rate, 3)))
            elif rate < 0.2 and count_f1 >= num_docs * 0.1 and count_f2 >= num_docs * 0.1:
                # 各自高频但很少一起出现 → 差异化特征
                differentiator_pairs.append((f1, f2, round(rate, 3)))

    # 排序
    must_have_pairs.sort(key=lambda x: x[2], reverse=True)
    differentiator_pairs.sort(key=lambda x: x[2])

    # 转换矩阵为普通 dict
    plain_matrix = {k: dict(v) for k, v in matrix.items()}

    return {
        "matrix": plain_matrix,
        "must_have_pairs": must_have_pairs[:20],
        "differentiator_pairs": differentiator_pairs[:20],
    }


# ============================================================
# 测试示例
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("用户需求深度分析器 — 测试示例")
    print("=" * 60)

    # 测试 JTBD 提取
    sample_texts = [
        "When I work from home, I want to block distracting websites so that I can stay focused.",
        "When I commute on the subway, I need offline access to my playlists so that I can enjoy music.",
        "I wish the app could sync across all my devices.",
        "当我出差的时候，我想要快速找到附近的餐厅这样我就能节省时间。",
        "我需要一个自动记账工具来管理每月开支。",
        "要是能一键导出PDF就好了",
    ]

    jobs = extract_jtbd(sample_texts)
    print("\n--- JTBD 提取 ---")
    for j in jobs:
        print(f"  [{j['type']}] {j['situation']} → {j['motivation']} → {j['outcome']}")

    # 测试机会评分
    satisfaction = {
        "block distracting websites": {"importance": 9, "satisfaction": 3},
        "offline access to my playlists": {"importance": 8, "satisfaction": 6},
        "sync across all my devices": {"importance": 7, "satisfaction": 7},
    }
    scores = calculate_opportunity_score(jobs, satisfaction)
    print("\n--- 机会评分 ---")
    for s in scores[:5]:
        print(f"  [{s['priority']}] {s['motivation']}: score={s['opportunity_score']}")

    # 测试迁移路径
    migration_texts = [
        "I switched from Evernote to Notion because of better collaboration features.",
        "Moved from Slack to Teams since our company uses Microsoft 365.",
        "从印象笔记换到了Notion，主要是数据库功能太强了。",
        "之前用Trello，现在用Notion管理项目。",
        "Replaced Todoist with TickTick for the calendar integration.",
        "I switched from Evernote to Notion for the database feature.",
    ]
    migrations = analyze_migration_paths(migration_texts)
    print("\n--- 迁移路径 ---")
    for m in migrations["migrations"]:
        print(f"  {m['from_product']} → {m['to_product']} (x{m['count']})")
    print(f"  净流入: {migrations['net_flow']}")

    # 测试价格敏感度
    price_texts = [
        "At $9.99/month it's a great deal.",
        "The $29.99 plan is way too expensive for what you get.",
        "I would pay $15 for this feature.",
        "Worth every penny at $49.",
        "这个99元的定价还是挺合理的。",
        "199元太贵了，不值这个价。",
    ]
    price_result = analyze_price_sensitivity(price_texts, [9.99, 29.99, 49.0])
    print("\n--- 价格敏感度 ---")
    print(f"  锚点: {price_result['anchors']}")
    print(f"  付费意愿区间: {price_result['willingness_range']}")
    print(f"  弹性: {price_result['elasticity_estimate']}")

    # 测试主题聚类
    topic_texts = [
        "The battery life is amazing, lasts all day with heavy use.",
        "Battery drains too fast when using GPS navigation.",
        "Camera quality is excellent in daylight but poor in low light.",
        "Night mode on the camera needs improvement.",
        "The screen is bright and colorful, great for watching videos.",
        "Display resolution could be better for the price.",
        "Battery and screen are the best features of this phone.",
        "I love the camera features but the battery could be better.",
    ]
    topics = cluster_topics(topic_texts, n_topics=4)
    print("\n--- 主题聚类 ---")
    for t in topics:
        print(f"  [{t['trend']}] {t['topic']}: freq={t['frequency']}, sent={t['sentiment']}")

    # 测试特征共现
    feature_texts = [
        "Great battery life and excellent camera quality.",
        "The battery and camera are the best features.",
        "I love the screen and battery performance.",
        "Camera and screen are both impressive.",
        "Fast charging and long battery life.",
        "Battery life is good but camera is average.",
        "The screen quality and fast charging are nice.",
        "Screen brightness and camera zoom are great.",
    ]
    cooccurrence = analyze_feature_cooccurrence(feature_texts)
    print("\n--- 特征共现 ---")
    print(f"  必备组合: {cooccurrence['must_have_pairs'][:5]}")
    print(f"  差异化组合: {cooccurrence['differentiator_pairs'][:5]}")

    # 边界测试
    print("\n--- 边界测试 ---")
    print(f"  空 JTBD: {extract_jtbd([])}")
    print(f"  空机会评分: {calculate_opportunity_score([], {})}")
    print(f"  空迁移路径: {analyze_migration_paths([])}")
    print(f"  空价格分析: {analyze_price_sensitivity([], [])}")
    print(f"  空主题聚类: {cluster_topics([])}")
    print(f"  空特征共现: {analyze_feature_cooccurrence([])}")

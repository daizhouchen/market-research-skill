"""
情感分析器

基于关键词词典方法对文本列表进行情感分析，支持中英文。
提取正面/负面关键词、未满足需求和代表性评论。
"""

import re
from collections import Counter, defaultdict
from typing import Any


# ============================================================
# 预定义情感词典
# ============================================================

POSITIVE_WORDS_EN = {
    "good", "great", "excellent", "amazing", "awesome", "fantastic", "love",
    "perfect", "best", "wonderful", "beautiful", "nice", "brilliant", "superb",
    "outstanding", "impressive", "recommend", "reliable", "comfortable",
    "efficient", "fast", "easy", "convenient", "smooth", "quality", "value",
    "durable", "intuitive", "responsive", "satisfied", "happy", "pleased",
    "elegant", "powerful", "innovative", "premium", "solid", "sturdy",
}

NEGATIVE_WORDS_EN = {
    "bad", "terrible", "awful", "horrible", "worst", "poor", "hate",
    "disappointing", "broken", "defective", "slow", "expensive", "cheap",
    "useless", "waste", "difficult", "complicated", "annoying", "frustrating",
    "unreliable", "fragile", "flimsy", "noisy", "ugly", "bulky", "heavy",
    "overpriced", "laggy", "buggy", "crash", "fail", "issue", "problem",
    "complaint", "refund", "return", "regret", "uncomfortable", "unstable",
}

POSITIVE_WORDS_ZH = {
    "好", "不错", "优秀", "很棒", "喜欢", "推荐", "满意", "方便",
    "舒适", "耐用", "性价比", "惊喜", "值得", "完美", "流畅",
    "精致", "高端", "出色", "强大", "省心", "好用", "漂亮",
    "超赞", "靠谱", "给力", "实用", "贴心", "高效", "稳定",
    "清晰", "轻便", "安静", "划算", "好评", "五星",
}

NEGATIVE_WORDS_ZH = {
    "差", "烂", "垃圾", "失望", "难用", "退货", "退款", "问题",
    "故障", "卡顿", "太贵", "廉价", "噪音", "异味", "做工差",
    "不值", "后悔", "投诉", "差评", "骗人", "坑", "吐槽",
    "不好用", "鸡肋", "槽点", "坏了", "慢", "太重", "发热",
    "掉漆", "生锈", "漏水", "不稳定", "闪退", "死机", "断连",
}

# 未满足需求的模式（中英文）
UNMET_NEED_PATTERNS = [
    # 英文
    r"(?:i\s+)?wish\s+(?:it\s+)?(?:had|could|would|was|were|there\s+was)",
    r"(?:i\s+)?hope\s+(?:they|it|this)\s+(?:will|would|could|can)",
    r"(?:i\s+)?want\s+(?:it\s+to|this\s+to|a|an|the|more)",
    r"would\s+be\s+(?:nice|great|better)\s+if",
    r"(?:should|need\s+to|needs\s+to)\s+(?:add|have|include|support|improve)",
    r"why\s+(?:doesn't|can't|isn't|won't|no)",
    r"missing\s+(?:feature|option|function)",
    r"lack(?:s|ing)\s+",
    # 中文
    r"要是.{2,20}就好了",
    r"希望.{2,30}(?:能|可以|会)",
    r"为什么没有",
    r"如果能.{2,20}就",
    r"缺少.{2,15}功能",
    r"(?:应该|需要)(?:加上|增加|支持|改进)",
    r"什么时候(?:能|才能|可以)",
    r"期待.{2,15}(?:功能|版本|更新)",
]


def analyze_sentiment(reviews: list[dict[str, Any]]) -> dict:
    """
    分析评论列表的情感。

    Args:
        reviews: 评论列表，每条包含:
                 - text: str, 评论文本（必需）
                 - source: str, 来源（可选）
                 - rating: float, 评分（可选，1-5）

    Returns:
        分析结果字典。
    """
    if not reviews:
        return _empty_result()

    positive_texts = []
    negative_texts = []
    neutral_texts = []
    all_positive_words = Counter()
    all_negative_words = Counter()
    unmet_needs = []

    for review in reviews:
        text = str(review.get("text", "")).strip()
        if not text:
            continue

        rating = review.get("rating")
        sentiment, pos_words, neg_words = _classify_text(text, rating)

        if sentiment == "positive":
            positive_texts.append(text)
        elif sentiment == "negative":
            negative_texts.append(text)
        else:
            neutral_texts.append(text)

        all_positive_words.update(pos_words)
        all_negative_words.update(neg_words)

        # 提取未满足需求
        needs = _extract_unmet_needs(text)
        unmet_needs.extend(needs)

    total = len(positive_texts) + len(negative_texts) + len(neutral_texts)
    if total == 0:
        return _empty_result()

    # 去重未满足需求
    unique_needs = list(dict.fromkeys(unmet_needs))

    return {
        "overall": {
            "positive_pct": round(len(positive_texts) / total * 100, 1),
            "neutral_pct": round(len(neutral_texts) / total * 100, 1),
            "negative_pct": round(len(negative_texts) / total * 100, 1),
        },
        "top_positive_keywords": all_positive_words.most_common(20),
        "top_negative_keywords": all_negative_words.most_common(20),
        "unmet_needs": unique_needs[:20],
        "representative_quotes": {
            "positive": _select_representative(positive_texts, max_count=5),
            "negative": _select_representative(negative_texts, max_count=5),
        },
    }


def _empty_result() -> dict:
    """返回空数据时的默认结果。"""
    return {
        "overall": {"positive_pct": 0.0, "neutral_pct": 0.0, "negative_pct": 0.0},
        "top_positive_keywords": [],
        "top_negative_keywords": [],
        "unmet_needs": [],
        "representative_quotes": {"positive": [], "negative": []},
    }


def _classify_text(text: str, rating: float | None = None) -> tuple[str, list[str], list[str]]:
    """
    对单条文本进行情感分类。

    优先使用评分判断（如果有的话），否则用关键词计数。

    Returns:
        (sentiment, positive_words_found, negative_words_found)
    """
    text_lower = text.lower()
    words = set(re.findall(r"[a-zA-Z]+", text_lower))

    # 匹配英文词
    pos_en = [w for w in words if w in POSITIVE_WORDS_EN]
    neg_en = [w for w in words if w in NEGATIVE_WORDS_EN]

    # 匹配中文词
    pos_zh = [w for w in POSITIVE_WORDS_ZH if w in text]
    neg_zh = [w for w in NEGATIVE_WORDS_ZH if w in text]

    pos_words = pos_en + pos_zh
    neg_words = neg_en + neg_zh

    # 如果有评分，优先用评分
    if rating is not None:
        try:
            r = float(rating)
            if r >= 4.0:
                return "positive", pos_words, neg_words
            elif r <= 2.0:
                return "negative", pos_words, neg_words
            else:
                return "neutral", pos_words, neg_words
        except (TypeError, ValueError):
            pass

    # 关键词计数判断
    pos_count = len(pos_words)
    neg_count = len(neg_words)

    if pos_count > neg_count:
        return "positive", pos_words, neg_words
    elif neg_count > pos_count:
        return "negative", pos_words, neg_words
    elif pos_count == 0 and neg_count == 0:
        return "neutral", pos_words, neg_words
    else:
        return "neutral", pos_words, neg_words


def _extract_unmet_needs(text: str) -> list[str]:
    """
    从文本中提取未满足需求的句子片段。
    """
    needs = []
    text_lower = text.lower()

    for pattern in UNMET_NEED_PATTERNS:
        matches = re.finditer(pattern, text_lower if pattern.isascii() else text, re.IGNORECASE)
        for match in matches:
            # 提取匹配位置周围的上下文（前后各取一些字符）
            start = max(0, match.start() - 10)
            end = min(len(text), match.end() + 50)
            snippet = text[start:end].strip()
            # 清理截断
            if start > 0:
                snippet = "..." + snippet
            if end < len(text):
                snippet = snippet + "..."
            if len(snippet) > 10:
                needs.append(snippet)

    return needs


def _select_representative(texts: list[str], max_count: int = 5) -> list[str]:
    """
    选取代表性评论：优先选择中等长度的评论（不太短也不太长）。
    """
    if not texts:
        return []

    # 按长度排序，优先取中等长度的（50-300字符）
    scored = []
    for t in texts:
        length = len(t)
        if 50 <= length <= 300:
            score = 2  # 理想长度
        elif 20 <= length <= 500:
            score = 1
        else:
            score = 0
        scored.append((score, length, t))

    scored.sort(key=lambda x: (-x[0], x[1]))

    # 截断过长文本
    result = []
    for _, _, text in scored[:max_count]:
        if len(text) > 300:
            text = text[:297] + "..."
        result.append(text)

    return result


# ============================================================
# 独立运行示例
# ============================================================
if __name__ == "__main__":
    sample_reviews = [
        {"text": "This product is great! Love the quality and design.", "source": "amazon", "rating": 5},
        {"text": "Terrible experience, the item broke after 2 days. Waste of money.", "source": "amazon", "rating": 1},
        {"text": "产品不错，性价比很高，推荐购买", "source": "jd", "rating": 5},
        {"text": "做工差，退货了，太失望", "source": "jd", "rating": 1},
        {"text": "一般般吧，没什么特别的", "source": "taobao", "rating": 3},
        {"text": "I wish it had better battery life. Would be great if they could add wireless charging.", "source": "reddit"},
        {"text": "要是能支持蓝牙5.0就好了，为什么没有NFC功能", "source": "zhihu"},
        {"text": "Good product, easy to use, comfortable design", "source": "amazon", "rating": 4},
        {"text": "噪音太大，发热严重，后悔购买", "source": "jd", "rating": 2},
        {"text": "It's okay, nothing special but does the job", "source": "amazon", "rating": 3},
    ]

    result = analyze_sentiment(sample_reviews)

    print("=== 情感分析结果 ===")
    print(f"整体分布: 正面 {result['overall']['positive_pct']}% | "
          f"中性 {result['overall']['neutral_pct']}% | "
          f"负面 {result['overall']['negative_pct']}%")
    print(f"\nTOP 正面关键词: {result['top_positive_keywords'][:5]}")
    print(f"TOP 负面关键词（痛点）: {result['top_negative_keywords'][:5]}")
    print(f"\n未满足需求: {result['unmet_needs']}")
    print(f"\n代表性正面评论: {result['representative_quotes']['positive'][:2]}")
    print(f"代表性负面评论: {result['representative_quotes']['negative'][:2]}")

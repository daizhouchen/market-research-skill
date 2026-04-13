"""
Reddit 公开数据采集器 — 无需 API 密钥

方式：通过 Web Search 搜索 site:reddit.com 获取 Reddit 公开帖子内容。
Reddit 自 2024 年起锁定了 .json 公开接口，因此不再直接请求 Reddit API。

本模块为 SKILL 的阶段 4 提供辅助函数，由 Claude 在执行调研时调用 WebSearch
工具搜索 "site:reddit.com {keyword}" 获取数据，然后用本模块的辅助函数解析。

直接命令行使用时，会打印建议的搜索查询列表供手动搜索。

用法:
  python reddit_public.py --keyword "VR headset" --subreddits virtualreality oculus
"""

import argparse
import json
import sys
from typing import List


def generate_reddit_search_queries(keyword: str, subreddits: List[str] = None) -> List[str]:
    """生成用于 Web Search 的 Reddit 搜索查询。

    通过 site:reddit.com 限定搜索范围到 Reddit，获取公开帖子。

    Args:
        keyword: 调研关键词
        subreddits: 推荐搜索的 subreddit 列表

    Returns:
        搜索查询字符串列表
    """
    queries = [
        f'site:reddit.com "{keyword}" pain points complaints',
        f'site:reddit.com "{keyword}" what users want recommend',
        f'site:reddit.com "{keyword}" review experience',
    ]

    if subreddits:
        for sub in subreddits[:3]:
            queries.append(f'site:reddit.com/r/{sub} "{keyword}"')

    return queries


def suggest_subreddits(keyword: str) -> List[str]:
    """根据关键词推荐相关的 subreddits。

    Args:
        keyword: 调研关键词

    Returns:
        推荐的 subreddit 名称列表
    """
    # 通用关键词到 subreddit 的映射
    keyword_lower = keyword.lower()

    mapping = {
        "vr": ["virtualreality", "oculus", "ValveIndex", "PSVR"],
        "ar": ["augmentedreality", "ARglass", "smartglasses"],
        "ai": ["artificial", "MachineLearning", "ChatGPT"],
        "saas": ["SaaS", "startups", "Entrepreneur"],
        "smart watch": ["smartwatch", "WearOS", "AppleWatch"],
        "smartwatch": ["smartwatch", "WearOS", "AppleWatch"],
        "headphone": ["headphones", "audiophile"],
        "earbuds": ["headphones", "earbuds"],
        "fitness": ["fitness", "homegym", "bodyweightfitness"],
        "gaming": ["gaming", "pcgaming", "Games"],
        "phone": ["smartphones", "Android", "iphone"],
        "laptop": ["laptops", "SuggestALaptop"],
        "tablet": ["tablets", "ipad"],
        "camera": ["cameras", "photography"],
        "drone": ["drones", "dji"],
        "robot": ["robotics", "robots"],
        "ev": ["electricvehicles", "teslamotors"],
        "crypto": ["CryptoCurrency", "Bitcoin"],
    }

    suggestions = []
    for key, subs in mapping.items():
        if key in keyword_lower:
            suggestions.extend(subs)

    # 通用兜底
    if not suggestions:
        suggestions = ["technology", "gadgets", "Futurology"]

    return suggestions[:5]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Reddit 公开数据采集辅助（生成搜索查询）")
    parser.add_argument("--keyword", "-k", required=True, help="调研关键词")
    parser.add_argument("--subreddits", "-s", nargs="*", help="指定搜索的 subreddit")
    args = parser.parse_args()

    if not args.subreddits:
        args.subreddits = suggest_subreddits(args.keyword)
        print(f"推荐 subreddits: {args.subreddits}")

    queries = generate_reddit_search_queries(args.keyword, args.subreddits)
    print("\n建议的 Web Search 查询：")
    for i, q in enumerate(queries, 1):
        print(f"  {i}. {q}")

    print(f"\n说明：Reddit 自 2024 年起锁定了 .json 公开接口。")
    print(f"请使用 Web Search 工具执行以上查询来获取 Reddit 公开内容。")
    print(f"如需更高频率采集，请配置 Reddit API 密钥（references/api_setup_guide.md）。")

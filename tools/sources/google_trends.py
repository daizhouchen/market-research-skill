"""
Google Trends 数据源 - 使用 pytrends 库获取Google趋势数据

功能:
- 获取关键词的搜索趋势(时间序列)
- 获取按地区的兴趣分布
- 获取相关查询(上升中和热门)
- 自动处理429限流，支持重试
"""

import time
from typing import Any, Dict, List, Optional

try:
    from pytrends.request import TrendReq
except ImportError:
    TrendReq = None
    print("[警告] 缺少 pytrends 依赖，请运行: pip install pytrends")


# 默认重试配置
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 60
REQUEST_DELAY_SECONDS = 1.5


def fetch_trends(
    keyword: str,
    geo: str = "",
    timeframe: str = "today 12-m",
    max_retries: int = MAX_RETRIES,
) -> Dict[str, Any]:
    """获取Google Trends数据。

    Args:
        keyword: 搜索关键词
        geo: 地区代码(如 "SG", "US", 留空为全球)
        timeframe: 时间范围(如 "today 12-m", "today 3-m", "2024-01-01 2024-12-31")
        max_retries: 最大重试次数(遇到429限流时)

    Returns:
        {
            interest_over_time: [{date: str, value: int}, ...],
            interest_by_region: [{region: str, value: int}, ...],
            related_queries: {rising: [...], top: [...]}
        }
    """
    if TrendReq is None:
        return {
            "error": "pytrends 未安装，请运行: pip install pytrends",
            "interest_over_time": [],
            "interest_by_region": [],
            "related_queries": {"rising": [], "top": []},
        }

    result: Dict[str, Any] = {
        "interest_over_time": [],
        "interest_by_region": [],
        "related_queries": {"rising": [], "top": []},
    }

    for attempt in range(max_retries):
        try:
            pytrends = TrendReq(hl="en-US", tz=360)
            pytrends.build_payload([keyword], cat=0, timeframe=timeframe, geo=geo)

            # 获取时间序列趋势
            time.sleep(REQUEST_DELAY_SECONDS)
            result["interest_over_time"] = _fetch_interest_over_time(pytrends, keyword)

            # 获取地区分布
            time.sleep(REQUEST_DELAY_SECONDS)
            result["interest_by_region"] = _fetch_interest_by_region(pytrends, keyword)

            # 获取相关查询
            time.sleep(REQUEST_DELAY_SECONDS)
            result["related_queries"] = _fetch_related_queries(pytrends, keyword)

            return result

        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "Too Many Requests" in error_msg:
                if attempt < max_retries - 1:
                    wait_time = RETRY_DELAY_SECONDS * (attempt + 1)
                    print(f"[Google Trends] 触发限流(429)，等待 {wait_time}s 后重试 "
                          f"({attempt + 1}/{max_retries})...")
                    time.sleep(wait_time)
                    continue
                else:
                    result["error"] = f"多次重试后仍被限流: {error_msg}"
            else:
                result["error"] = f"请求失败: {error_msg}"
            return result

    return result


def _fetch_interest_over_time(pytrends: Any, keyword: str) -> List[Dict[str, Any]]:
    """获取时间序列趋势数据。

    Args:
        pytrends: TrendReq 实例(已构建payload)
        keyword: 搜索关键词

    Returns:
        [{date: str, value: int}, ...]
    """
    try:
        df = pytrends.interest_over_time()
        if df.empty:
            return []
        records = []
        for date, row in df.iterrows():
            records.append({
                "date": str(date.date()),
                "value": int(row.get(keyword, 0)),
            })
        return records
    except Exception as e:
        print(f"[Google Trends] 获取时间序列失败: {e}")
        return []


def _fetch_interest_by_region(pytrends: Any, keyword: str) -> List[Dict[str, Any]]:
    """获取地区兴趣分布数据。

    Args:
        pytrends: TrendReq 实例(已构建payload)
        keyword: 搜索关键词

    Returns:
        [{region: str, value: int}, ...]
    """
    try:
        df = pytrends.interest_by_region(resolution="COUNTRY", inc_low_vol=True)
        if df.empty:
            return []
        records = []
        for region, row in df.iterrows():
            value = int(row.get(keyword, 0))
            if value > 0:
                records.append({"region": region, "value": value})
        records.sort(key=lambda x: x["value"], reverse=True)
        return records
    except Exception as e:
        print(f"[Google Trends] 获取地区分布失败: {e}")
        return []


def _fetch_related_queries(pytrends: Any, keyword: str) -> Dict[str, List]:
    """获取相关查询数据。

    Args:
        pytrends: TrendReq 实例(已构建payload)
        keyword: 搜索关键词

    Returns:
        {rising: [{query: str, value: int}, ...], top: [{query: str, value: int}, ...]}
    """
    result: Dict[str, List] = {"rising": [], "top": []}
    try:
        related = pytrends.related_queries()
        kw_data = related.get(keyword, {})

        for category in ["rising", "top"]:
            df = kw_data.get(category)
            if df is not None and not df.empty:
                for _, row in df.iterrows():
                    result[category].append({
                        "query": str(row.get("query", "")),
                        "value": int(row.get("value", 0)),
                    })
    except Exception as e:
        print(f"[Google Trends] 获取相关查询失败: {e}")
    return result


if __name__ == "__main__":
    import json
    import sys

    keyword = sys.argv[1] if len(sys.argv) > 1 else "smart watch"
    geo = sys.argv[2] if len(sys.argv) > 2 else ""

    print(f"正在获取 Google Trends 数据: keyword={keyword}, geo={geo}")
    data = fetch_trends(keyword, geo=geo)
    print(json.dumps(data, ensure_ascii=False, indent=2))

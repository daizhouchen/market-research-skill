"""
Xquik public X data source.

Fetches public X search results for market research signals such as pain
phrases, launch reactions, competitor mentions, and creator conversations.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional

try:
    import requests
except ImportError:
    requests = None
    print("[警告] 缺少 requests 依赖，请运行: pip install requests")


XQUIK_SEARCH_URL = "https://xquik.com/api/v1/x/tweets/search"
XQUIK_API_CONTRACT = "2026-04-29"


def search_x_posts(
    query: str,
    api_key: Optional[str],
    limit: int = 50,
    exact_phrase: Optional[str] = None,
    from_user: Optional[str] = None,
    mentioning: Optional[str] = None,
    since_date: Optional[str] = None,
    until_date: Optional[str] = None,
    query_type: str = "Latest",
    cursor: Optional[str] = None,
) -> Dict[str, Any]:
    """Search public X posts through Xquik.

    Args:
        query: Search query.
        api_key: Xquik API key.
        limit: Maximum result count.
        exact_phrase: Exact phrase filter.
        from_user: Source account handle.
        mentioning: Mentioned account handle.
        since_date: Lower date bound in YYYY-MM-DD format.
        until_date: Upper date bound in YYYY-MM-DD format.
        query_type: Search type, usually Latest or Top.
        cursor: Pagination cursor.

    Returns:
        Normalized result dict with tweets, pagination, and metadata.
    """
    if requests is None:
        return _failed_result(query, "requests 未安装，请运行: pip install requests")

    if not api_key:
        return _failed_result(query, "缺少 Xquik api_key")

    params: Dict[str, Any] = {
        "q": query,
        "limit": max(1, min(limit, 100)),
        "queryType": query_type,
    }
    optional_params = {
        "exactPhrase": exact_phrase,
        "fromUser": from_user,
        "mentioning": mentioning,
        "sinceDate": since_date,
        "untilDate": until_date,
        "cursor": cursor,
    }
    params.update({
        name: value
        for name, value in optional_params.items()
        if value is not None and str(value).strip() != ""
    })

    headers = {
        "Accept": "application/json",
        "x-api-key": api_key,
        "xquik-api-contract": XQUIK_API_CONTRACT,
    }

    try:
        response = requests.get(
            XQUIK_SEARCH_URL,
            params=params,
            headers=headers,
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
    except requests.exceptions.Timeout:
        return _failed_result(query, "请求超时")
    except requests.exceptions.HTTPError as exc:
        status_code = exc.response.status_code if exc.response is not None else "unknown"
        return _failed_result(query, f"HTTP 错误: {status_code}")
    except requests.exceptions.RequestException as exc:
        return _failed_result(query, f"请求失败: {str(exc)}")
    except ValueError:
        return _failed_result(query, "响应不是有效 JSON")

    tweets = payload.get("tweets", [])
    if not isinstance(tweets, list):
        tweets = []

    return {
        "tweets": tweets,
        "has_more": bool(payload.get("has_more", False)),
        "next_cursor": str(payload.get("next_cursor", "")),
        "metadata": {
            "source": "xquik",
            "query": query,
            "total_results": len(tweets),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "status": "success",
        },
    }


def _failed_result(query: str, message: str) -> Dict[str, Any]:
    return {
        "error": message,
        "tweets": [],
        "has_more": False,
        "next_cursor": "",
        "metadata": {
            "source": "xquik",
            "query": query,
            "total_results": 0,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "status": "failed",
        },
    }

"""
SimilarWeb 数据源 - 获取网站流量排名和分析数据

功能:
- 获取网站的全球排名、国家排名和分类排名
- 使用 SimilarWeb API
"""

from typing import Any, Dict, Optional

try:
    import requests
except ImportError:
    requests = None
    print("[警告] 缺少 requests 依赖，请运行: pip install requests")

SIMILARWEB_API_BASE = "https://api.similarweb.com/v1"


def get_website_rank(
    domain: str,
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """获取网站流量排名信息。

    Args:
        domain: 网站域名(如 "example.com")
        api_key: SimilarWeb API 密钥

    Returns:
        {global_rank, country_rank, category_rank}
    """
    if requests is None:
        return {
            "error": "requests 未安装，请运行: pip install requests",
            "global_rank": None,
            "country_rank": None,
            "category_rank": None,
        }

    if not api_key:
        return {
            "error": "缺少 SimilarWeb API 密钥",
            "global_rank": None,
            "country_rank": None,
            "category_rank": None,
        }

    # 清理域名
    domain = domain.strip().lower()
    if domain.startswith("http://") or domain.startswith("https://"):
        domain = domain.split("//", 1)[1]
    if domain.startswith("www."):
        domain = domain[4:]
    domain = domain.rstrip("/")

    url = f"{SIMILARWEB_API_BASE}/website/{domain}/total-traffic-and-engagement/visits"
    params = {
        "api_key": api_key,
        "start_date": "2024-01",
        "end_date": "2024-12",
        "country": "world",
        "granularity": "monthly",
        "main_domain_only": "false",
    }

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        traffic_data = response.json()

        # 获取排名数据
        rank_url = f"{SIMILARWEB_API_BASE}/website/{domain}/global-rank/global-rank"
        rank_params = {"api_key": api_key}

        rank_response = requests.get(rank_url, params=rank_params, timeout=30)
        rank_data = {}
        if rank_response.status_code == 200:
            rank_data = rank_response.json()

        return {
            "global_rank": rank_data.get("global_rank", None),
            "country_rank": rank_data.get("country_rank", None),
            "category_rank": rank_data.get("category_rank", None),
            "domain": domain,
            "traffic_data": traffic_data,
        }

    except requests.exceptions.HTTPError as e:
        status = e.response.status_code if e.response is not None else "unknown"
        if status == 403:
            error_msg = "API密钥无效或权限不足"
        elif status == 404:
            error_msg = f"未找到域名数据: {domain}"
        elif status == 429:
            error_msg = "请求频率超限，请稍后重试"
        else:
            error_msg = f"HTTP错误 {status}"
        return {
            "error": error_msg,
            "global_rank": None,
            "country_rank": None,
            "category_rank": None,
        }
    except requests.exceptions.RequestException as e:
        return {
            "error": f"请求失败: {str(e)}",
            "global_rank": None,
            "country_rank": None,
            "category_rank": None,
        }
    except Exception as e:
        return {
            "error": f"未知错误: {str(e)}",
            "global_rank": None,
            "country_rank": None,
            "category_rank": None,
        }


def get_traffic_sources(
    domain: str,
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """获取网站流量来源分布(附加功能)。

    Args:
        domain: 网站域名
        api_key: SimilarWeb API 密钥

    Returns:
        流量来源信息字典
    """
    if requests is None or not api_key:
        return {"error": "依赖或凭证不满足"}

    domain = domain.strip().lower().lstrip("https://").lstrip("http://").lstrip("www.").rstrip("/")

    url = f"{SIMILARWEB_API_BASE}/website/{domain}/traffic-sources/overview"
    params = {
        "api_key": api_key,
        "start_date": "2024-01",
        "end_date": "2024-12",
        "country": "world",
        "granularity": "monthly",
    }

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": f"获取流量来源失败: {str(e)}"}


if __name__ == "__main__":
    import json
    import sys

    domain = sys.argv[1] if len(sys.argv) > 1 else "example.com"
    api_key = sys.argv[2] if len(sys.argv) > 2 else None

    print(f"正在查询 SimilarWeb: domain={domain}")
    data = get_website_rank(domain, api_key=api_key)
    print(json.dumps(data, ensure_ascii=False, indent=2, default=str))

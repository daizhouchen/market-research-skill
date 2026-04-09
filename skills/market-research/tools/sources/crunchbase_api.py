"""
Crunchbase 数据源 - 搜索公司融资和基本信息

功能:
- 按关键词搜索公司
- 获取公司名称、融资总额、最近融资日期、员工数和分类
- 使用 Crunchbase Basic API
"""

from typing import Any, Dict, List, Optional

try:
    import requests
except ImportError:
    requests = None
    print("[警告] 缺少 requests 依赖，请运行: pip install requests")

CRUNCHBASE_API_BASE = "https://api.crunchbase.com/api/v4"


def search_companies(
    query: str,
    api_key: Optional[str] = None,
    limit: int = 10,
) -> Dict[str, Any]:
    """搜索Crunchbase公司信息。

    Args:
        query: 搜索关键词
        api_key: Crunchbase API 密钥
        limit: 返回结果数量上限

    Returns:
        {companies: [{name, funding_total, last_funding_date, num_employees, categories}, ...]}
    """
    if requests is None:
        return {
            "error": "requests 未安装，请运行: pip install requests",
            "companies": [],
        }

    if not api_key:
        return {
            "error": "缺少 Crunchbase API 密钥",
            "companies": [],
        }

    # 使用 Crunchbase 搜索端点
    url = f"{CRUNCHBASE_API_BASE}/autocompletes"
    params = {
        "user_key": api_key,
        "query": query,
        "collection_ids": "organizations",
        "limit": min(limit, 25),
    }

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        # 解析自动补全结果
        entities = data.get("entities", [])
        company_ids = [
            entity.get("identifier", {}).get("permalink", "")
            for entity in entities
            if entity.get("identifier", {}).get("entity_def_id") == "organization"
        ]

        # 获取每个公司的详细信息
        companies: List[Dict[str, Any]] = []
        for permalink in company_ids[:limit]:
            if not permalink:
                continue
            detail = _get_company_detail(permalink, api_key)
            if detail:
                companies.append(detail)

        return {"companies": companies}

    except requests.exceptions.HTTPError as e:
        status = e.response.status_code if e.response is not None else "unknown"
        if status == 401:
            error_msg = "API密钥无效"
        elif status == 403:
            error_msg = "API权限不足，请检查订阅计划"
        elif status == 429:
            error_msg = "请求频率超限，请稍后重试"
        else:
            error_msg = f"HTTP错误 {status}"
        return {"error": error_msg, "companies": []}
    except requests.exceptions.RequestException as e:
        return {"error": f"请求失败: {str(e)}", "companies": []}
    except Exception as e:
        return {"error": f"未知错误: {str(e)}", "companies": []}


def _get_company_detail(
    permalink: str,
    api_key: str,
) -> Optional[Dict[str, Any]]:
    """获取单个公司的详细信息。

    Args:
        permalink: 公司在Crunchbase上的永久链接标识
        api_key: Crunchbase API 密钥

    Returns:
        公司信息字典，失败返回None
    """
    url = f"{CRUNCHBASE_API_BASE}/entities/organizations/{permalink}"
    params = {
        "user_key": api_key,
        "field_ids": [
            "short_description",
            "funding_total",
            "last_funding_at",
            "num_employees_enum",
            "categories",
            "location_identifiers",
            "founded_on",
            "website_url",
        ],
    }

    try:
        response = requests.get(url, params=params, timeout=20)
        if response.status_code != 200:
            return None

        data = response.json()
        properties = data.get("properties", {})

        # 解析融资总额
        funding_total_obj = properties.get("funding_total", {})
        if isinstance(funding_total_obj, dict):
            funding_total = funding_total_obj.get("value_usd", None)
            funding_currency = funding_total_obj.get("currency", "USD")
        else:
            funding_total = funding_total_obj
            funding_currency = "USD"

        # 解析分类
        categories_raw = properties.get("categories", [])
        if isinstance(categories_raw, list):
            categories = [
                cat.get("value", "") if isinstance(cat, dict) else str(cat)
                for cat in categories_raw
            ]
        else:
            categories = []

        # 解析员工数范围
        num_employees = properties.get("num_employees_enum", "未知")

        return {
            "name": data.get("properties", {}).get("identifier", {}).get("value", permalink),
            "description": properties.get("short_description", ""),
            "funding_total": funding_total,
            "funding_currency": funding_currency,
            "last_funding_date": properties.get("last_funding_at", None),
            "num_employees": num_employees,
            "categories": categories,
            "founded_on": properties.get("founded_on", None),
            "website": properties.get("website_url", ""),
            "crunchbase_url": f"https://www.crunchbase.com/organization/{permalink}",
        }

    except Exception as e:
        print(f"[Crunchbase] 获取公司详情失败({permalink}): {e}")
        return None


if __name__ == "__main__":
    import json
    import sys

    query = sys.argv[1] if len(sys.argv) > 1 else "smart watch"
    api_key = sys.argv[2] if len(sys.argv) > 2 else None

    print(f"正在搜索 Crunchbase: query={query}")
    data = search_companies(query, api_key=api_key)
    print(json.dumps(data, ensure_ascii=False, indent=2, default=str))

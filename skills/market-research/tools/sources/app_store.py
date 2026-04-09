"""
App Store 数据源 - 搜索 Apple App Store 应用信息

功能:
- 按关键词搜索App Store应用
- 优先使用 app-store-scraper (Node.js) 获取详细数据
- 若Node.js不可用，回退到 iTunes Search API
- 获取应用名称、开发者、评分、评论数、价格和描述
"""

import json as json_lib
import subprocess
import tempfile
from typing import Any, Dict, List, Optional

try:
    import requests
except ImportError:
    requests = None
    print("[警告] 缺少 requests 依赖，请运行: pip install requests")

# iTunes Search API 端点
ITUNES_SEARCH_URL = "https://itunes.apple.com/search"

# App Store 国家代码映射
COUNTRY_MAP = {
    "sg": "sg",
    "us": "us",
    "cn": "cn",
    "jp": "jp",
    "gb": "gb",
    "de": "de",
    "au": "au",
}


def search_app_store(
    term: str,
    country: str = "sg",
    num: int = 20,
) -> Dict[str, Any]:
    """搜索 App Store 应用。

    优先尝试 Node.js app-store-scraper，失败后回退到 iTunes Search API。

    Args:
        term: 搜索关键词
        country: 国家代码(如 "sg", "us")
        num: 返回结果数量上限

    Returns:
        {apps: [{name, developer, rating, reviews, price, description}, ...]}
    """
    # 尝试 Node.js scraper
    result = _try_node_scraper(term, country, num)
    if result is not None:
        return result

    # 回退到 iTunes Search API
    return _itunes_search(term, country, num)


def _try_node_scraper(
    term: str,
    country: str,
    num: int,
) -> Optional[Dict[str, Any]]:
    """尝试使用 Node.js app-store-scraper。

    Args:
        term: 搜索关键词
        country: 国家代码
        num: 返回结果数量

    Returns:
        搜索结果字典，Node.js不可用则返回None
    """
    js_code = f"""
    try {{
        const store = require('app-store-scraper');
        store.search({{
            term: {json_lib.dumps(term)},
            country: {json_lib.dumps(country)},
            num: {num}
        }}).then(results => {{
            const apps = results.map(app => ({{
                name: app.title || app.appName || '',
                developer: app.developer || '',
                rating: app.score || null,
                reviews: app.reviews || 0,
                price: app.free ? '免费' : (app.price ? `${{app.price}}` : '未知'),
                description: (app.description || '').substring(0, 300),
                app_id: app.id || '',
                url: app.url || ''
            }}));
            console.log(JSON.stringify({{apps: apps}}));
        }}).catch(err => {{
            console.log(JSON.stringify({{error: err.message, apps: []}}));
        }});
    }} catch(e) {{
        console.log(JSON.stringify({{error: e.message, apps: []}}));
    }}
    """

    try:
        result = subprocess.run(
            ["node", "-e", js_code],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0 and result.stdout.strip():
            data = json_lib.loads(result.stdout.strip())
            if "error" not in data or data.get("apps"):
                return data
    except FileNotFoundError:
        # Node.js 未安装
        pass
    except subprocess.TimeoutExpired:
        print("[App Store] Node.js scraper 超时")
    except (json_lib.JSONDecodeError, Exception) as e:
        print(f"[App Store] Node.js scraper 失败: {e}")

    return None


def _itunes_search(
    term: str,
    country: str,
    num: int,
) -> Dict[str, Any]:
    """使用 iTunes Search API 搜索应用(回退方案)。

    Args:
        term: 搜索关键词
        country: 国家代码
        num: 返回结果数量

    Returns:
        {apps: [{name, developer, rating, reviews, price, description}, ...]}
    """
    if requests is None:
        return {
            "error": "requests 未安装且 Node.js 不可用",
            "apps": [],
        }

    country_code = COUNTRY_MAP.get(country.lower(), country.lower())

    params = {
        "term": term,
        "country": country_code,
        "media": "software",
        "limit": min(num, 200),  # iTunes API 限制200
    }

    try:
        response = requests.get(ITUNES_SEARCH_URL, params=params, timeout=20)
        response.raise_for_status()
        data = response.json()

        apps: List[Dict[str, Any]] = []
        for item in data.get("results", []):
            price_value = item.get("price", 0)
            price_str = "免费" if price_value == 0 else f"${price_value}"

            apps.append({
                "name": item.get("trackName", ""),
                "developer": item.get("artistName", ""),
                "rating": round(item.get("averageUserRating", 0), 1) or None,
                "reviews": item.get("userRatingCount", 0),
                "price": price_str,
                "description": (item.get("description", "") or "")[:300],
                "app_id": item.get("trackId", ""),
                "url": item.get("trackViewUrl", ""),
            })

        return {"apps": apps}

    except requests.exceptions.RequestException as e:
        return {"error": f"iTunes Search API 请求失败: {str(e)}", "apps": []}
    except Exception as e:
        return {"error": f"未知错误: {str(e)}", "apps": []}


if __name__ == "__main__":
    import json
    import sys

    term = sys.argv[1] if len(sys.argv) > 1 else "smart watch"
    country = sys.argv[2] if len(sys.argv) > 2 else "sg"

    print(f"正在搜索 App Store: term={term}, country={country}")
    data = search_app_store(term, country=country)
    print(json.dumps(data, ensure_ascii=False, indent=2))

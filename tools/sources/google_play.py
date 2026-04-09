"""
Google Play 数据源 - 使用 google-play-scraper 搜索Google Play应用

功能:
- 按关键词搜索Google Play商店应用
- 获取应用名称、开发者、评分、评论数、价格、描述和安装量
"""

from typing import Any, Dict, List

try:
    from google_play_scraper import search as gplay_search
    from google_play_scraper import app as gplay_app
except ImportError:
    gplay_search = None
    gplay_app = None
    print("[警告] 缺少 google-play-scraper 依赖，请运行: pip install google-play-scraper")


def search_google_play(
    query: str,
    country: str = "sg",
    lang: str = "en",
    num: int = 20,
) -> Dict[str, Any]:
    """搜索Google Play商店应用。

    Args:
        query: 搜索关键词
        country: 国家代码(如 "sg", "us")
        lang: 语言代码(如 "en", "zh")
        num: 返回结果数量上限

    Returns:
        {apps: [{name, developer, rating, reviews, price, description, installs}, ...]}
    """
    if gplay_search is None:
        return {
            "error": "google-play-scraper 未安装，请运行: pip install google-play-scraper",
            "apps": [],
        }

    try:
        results = gplay_search(
            query,
            lang=lang,
            country=country,
            n_hits=num,
        )

        apps: List[Dict[str, Any]] = []
        for item in results:
            # 处理价格显示
            price_value = item.get("price", 0)
            if price_value is None or price_value == 0 or price_value == "0":
                price_str = "免费"
            else:
                price_str = f"${price_value}"

            apps.append({
                "name": item.get("title", ""),
                "developer": item.get("developer", ""),
                "rating": round(item.get("score", 0) or 0, 1) or None,
                "reviews": item.get("ratings", 0) or 0,
                "price": price_str,
                "description": (item.get("description", "") or "")[:300],
                "installs": item.get("installs", "未知"),
                "app_id": item.get("appId", ""),
                "icon": item.get("icon", ""),
            })

        return {"apps": apps}

    except Exception as e:
        return {"error": f"Google Play 搜索失败: {str(e)}", "apps": []}


def get_app_details(
    app_id: str,
    country: str = "sg",
    lang: str = "en",
) -> Dict[str, Any]:
    """获取单个应用的详细信息。

    Args:
        app_id: 应用包名(如 "com.example.app")
        country: 国家代码
        lang: 语言代码

    Returns:
        应用详细信息字典
    """
    if gplay_app is None:
        return {"error": "google-play-scraper 未安装"}

    try:
        details = gplay_app(app_id, lang=lang, country=country)

        price_value = details.get("price", 0)
        price_str = "免费" if (price_value is None or price_value == 0) else f"${price_value}"

        return {
            "name": details.get("title", ""),
            "developer": details.get("developer", ""),
            "rating": round(details.get("score", 0) or 0, 1) or None,
            "reviews": details.get("ratings", 0) or 0,
            "price": price_str,
            "description": (details.get("description", "") or "")[:500],
            "installs": details.get("installs", "未知"),
            "app_id": details.get("appId", ""),
            "icon": details.get("icon", ""),
            "genre": details.get("genre", ""),
            "content_rating": details.get("contentRating", ""),
            "updated": details.get("updated", ""),
            "version": details.get("version", ""),
            "developer_email": details.get("developerEmail", ""),
            "developer_website": details.get("developerWebsite", ""),
        }

    except Exception as e:
        return {"error": f"获取应用详情失败: {str(e)}"}


if __name__ == "__main__":
    import json
    import sys

    query = sys.argv[1] if len(sys.argv) > 1 else "smart watch"
    country = sys.argv[2] if len(sys.argv) > 2 else "sg"

    print(f"正在搜索 Google Play: query={query}, country={country}")
    data = search_google_play(query, country=country)
    print(json.dumps(data, ensure_ascii=False, indent=2))

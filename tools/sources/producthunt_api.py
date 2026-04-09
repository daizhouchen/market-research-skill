"""
Product Hunt 数据源 - 通过 GraphQL API 搜索产品

功能:
- 按主题搜索 Product Hunt 上的产品
- 获取产品名称、标语、投票数、评论数、话题和链接
- 支持时间过滤和分页
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

try:
    import requests
except ImportError:
    requests = None
    print("[警告] 缺少 requests 依赖，请运行: pip install requests")

PRODUCTHUNT_API_URL = "https://api.producthunt.com/v2/api/graphql"


def search_producthunt(
    topic: str,
    posted_after: Optional[str] = None,
    first: int = 20,
    access_token: Optional[str] = None,
) -> Dict[str, Any]:
    """搜索 Product Hunt 产品。

    Args:
        topic: 搜索主题/关键词
        posted_after: 发布时间过滤(ISO格式，如 "2024-01-01")
        first: 返回产品数量上限
        access_token: Product Hunt API 访问令牌

    Returns:
        {products: [{name, tagline, votes_count, comments_count, topics, url}, ...]}
    """
    if requests is None:
        return {
            "error": "requests 未安装，请运行: pip install requests",
            "products": [],
        }

    if not access_token:
        return {
            "error": "缺少 Product Hunt access_token",
            "products": [],
        }

    # 构建 GraphQL 查询
    query = """
    query SearchPosts($query: String!, $first: Int!, $postedAfter: DateTime) {
        posts(
            topic: $query,
            first: $first,
            postedAfter: $postedAfter,
            order: VOTES
        ) {
            edges {
                node {
                    id
                    name
                    tagline
                    votesCount
                    commentsCount
                    url
                    website
                    createdAt
                    topics {
                        edges {
                            node {
                                name
                            }
                        }
                    }
                }
            }
        }
    }
    """

    variables: Dict[str, Any] = {
        "query": topic,
        "first": min(first, 50),  # API限制
    }

    if posted_after:
        try:
            # 验证日期格式
            datetime.fromisoformat(posted_after)
            variables["postedAfter"] = f"{posted_after}T00:00:00Z"
        except ValueError:
            pass

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    try:
        response = requests.post(
            PRODUCTHUNT_API_URL,
            json={"query": query, "variables": variables},
            headers=headers,
            timeout=30,
        )
        response.raise_for_status()

        data = response.json()
        if "errors" in data:
            return {
                "error": f"GraphQL 错误: {data['errors']}",
                "products": [],
            }

        # 解析响应
        products: List[Dict[str, Any]] = []
        edges = data.get("data", {}).get("posts", {}).get("edges", [])

        for edge in edges:
            node = edge.get("node", {})
            topics = [
                t["node"]["name"]
                for t in node.get("topics", {}).get("edges", [])
            ]
            products.append({
                "name": node.get("name", ""),
                "tagline": node.get("tagline", ""),
                "votes_count": node.get("votesCount", 0),
                "comments_count": node.get("commentsCount", 0),
                "topics": topics,
                "url": node.get("url", ""),
                "website": node.get("website", ""),
                "created_at": node.get("createdAt", ""),
            })

        return {"products": products}

    except requests.exceptions.Timeout:
        return {"error": "请求超时(30s)", "products": []}
    except requests.exceptions.HTTPError as e:
        return {"error": f"HTTP 错误: {e.response.status_code} - {e.response.text[:200]}", "products": []}
    except requests.exceptions.RequestException as e:
        return {"error": f"请求失败: {str(e)}", "products": []}
    except Exception as e:
        return {"error": f"未知错误: {str(e)}", "products": []}


if __name__ == "__main__":
    import json
    import sys

    topic = sys.argv[1] if len(sys.argv) > 1 else "smart watch"
    token = sys.argv[2] if len(sys.argv) > 2 else None

    print(f"正在搜索 Product Hunt: topic={topic}")
    data = search_producthunt(topic, access_token=token)
    print(json.dumps(data, ensure_ascii=False, indent=2))

"""
Reddit 数据源 - 使用 praw 库搜索Reddit帖子和评论

功能:
- 按关键词搜索Reddit帖子
- 支持指定子版块、排序方式和时间范围
- 获取帖子及热门评论
- 完善的错误处理
"""

from typing import Any, Dict, List, Optional

try:
    import praw
except ImportError:
    praw = None
    print("[警告] 缺少 praw 依赖，请运行: pip install praw")


def search_reddit(
    query: str,
    subreddits: Optional[List[str]] = None,
    sort: str = "relevance",
    limit: int = 50,
    time_filter: str = "year",
    config: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """搜索Reddit帖子和评论。

    Args:
        query: 搜索关键词
        subreddits: 限定搜索的子版块列表(为None则搜索全站)
        sort: 排序方式("relevance", "hot", "top", "new", "comments")
        limit: 返回帖子数量上限
        time_filter: 时间范围("hour", "day", "week", "month", "year", "all")
        config: Reddit API 配置 {"client_id", "client_secret", "user_agent"}

    Returns:
        {
            posts: [{title, body, score, num_comments, created_utc, subreddit}, ...],
            top_comments: [{body, score, post_title, subreddit}, ...]
        }
    """
    if praw is None:
        return {
            "error": "praw 未安装，请运行: pip install praw",
            "posts": [],
            "top_comments": [],
        }

    if config is None:
        config = {}

    client_id = config.get("client_id", "")
    client_secret = config.get("client_secret", "")
    user_agent = config.get("user_agent", "market-research-tool/1.0")

    if not client_id or not client_secret:
        return {
            "error": "缺少 Reddit API 凭证(client_id, client_secret)",
            "posts": [],
            "top_comments": [],
        }

    try:
        reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent=user_agent,
        )

        posts: List[Dict[str, Any]] = []
        top_comments: List[Dict[str, Any]] = []

        # 决定搜索范围
        if subreddits:
            search_target = reddit.subreddit("+".join(subreddits))
        else:
            search_target = reddit.subreddit("all")

        # 执行搜索
        for submission in search_target.search(
            query, sort=sort, time_filter=time_filter, limit=limit
        ):
            post_data = {
                "title": submission.title,
                "body": (submission.selftext[:500] + "...") if len(submission.selftext) > 500 else submission.selftext,
                "score": submission.score,
                "num_comments": submission.num_comments,
                "created_utc": submission.created_utc,
                "subreddit": str(submission.subreddit),
                "url": f"https://reddit.com{submission.permalink}",
            }
            posts.append(post_data)

            # 获取每个帖子的热门评论(最多3条)
            try:
                submission.comment_sort = "top"
                submission.comments.replace_more(limit=0)
                for comment in submission.comments[:3]:
                    if hasattr(comment, "body") and comment.body:
                        top_comments.append({
                            "body": (comment.body[:300] + "...") if len(comment.body) > 300 else comment.body,
                            "score": comment.score,
                            "post_title": submission.title,
                            "subreddit": str(submission.subreddit),
                        })
            except Exception:
                # 评论获取失败不影响帖子数据
                pass

        # 按评分排序评论
        top_comments.sort(key=lambda x: x.get("score", 0), reverse=True)
        # 只保留前30条热门评论
        top_comments = top_comments[:30]

        return {"posts": posts, "top_comments": top_comments}

    except Exception as e:
        return {
            "error": f"Reddit API 请求失败: {str(e)}",
            "posts": [],
            "top_comments": [],
        }


if __name__ == "__main__":
    import json
    import sys

    query = sys.argv[1] if len(sys.argv) > 1 else "smart watch"

    print(f"正在搜索 Reddit: query={query}")
    print("[提示] 需要在 config 参数中提供 client_id 和 client_secret")

    # 示例: 无凭证时的输出
    data = search_reddit(query)
    print(json.dumps(data, ensure_ascii=False, indent=2))

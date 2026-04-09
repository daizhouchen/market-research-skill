# 数据源技术规格

本文档定义了市场研究技能中每个数据源模块的技术规格，包括依赖、认证方式、输入输出、速率限制、错误处理与降级策略。

---

## 1. google_trends

| 规格项 | 详情 |
|---|---|
| **依赖库** | `pytrends >= 4.9.0` |
| **认证方式** | 无需认证（基于浏览器模拟） |
| **基础 URL** | 通过 pytrends 内部处理 |

### 输入参数
```python
{
    "keywords": list[str],        # 搜索关键词列表，最多5个
    "timeframe": str,             # 时间范围，默认 "today 12-m"
    "geo": str,                   # 地区代码，默认 "" (全球)
    "category": int,              # 类别ID，默认 0 (所有类别)
    "language": str,              # 语言，默认 "en-US"
}
```

### 输出格式
```python
{
    "interest_over_time": {
        "dates": list[str],           # ISO 8601 日期列表
        "values": dict[str, list[int]], # 关键词 -> 搜索指数(0-100)
    },
    "related_queries": {
        "keyword": {
            "rising": list[dict],     # {"query": str, "value": int}
            "top": list[dict],        # {"query": str, "value": int}
        }
    },
    "interest_by_region": {
        "keyword": dict[str, int],    # 地区 -> 搜索指数
    },
    "metadata": {
        "source": "google_trends",
        "fetched_at": str,            # ISO 8601 时间戳
        "status": "success" | "partial" | "failed",
    }
}
```

### 速率限制
- 无官方限制
- **实际约束**：频繁请求触发 429 Too Many Requests
- **建议策略**：每次请求间隔 2-5 秒随机延迟，指数退避重试

### 错误处理
| 错误类型 | 处理方式 |
|---|---|
| `TooManyRequestsError` / HTTP 429 | 指数退避重试，最大等待 60 秒，最多 3 次 |
| `ResponseError` | 记录日志，重试 1 次 |
| 超时 | 重试 2 次，每次增加超时时间 |
| 数据为空 | 标记为 "no_data"，不阻断流程 |

### 降级策略
- **Level 1**：减少关键词数量，分批请求
- **Level 2**：缩短时间范围（12个月 → 6个月 → 3个月）
- **Level 3**：仅返回缓存数据（如有）
- **Level 4**：跳过该数据源，在报告中标注 "Google Trends 数据不可用"

---

## 2. reddit

| 规格项 | 详情 |
|---|---|
| **依赖库** | `praw >= 7.7.0` |
| **认证方式** | OAuth2（client_id + client_secret） |
| **基础 URL** | `https://oauth.reddit.com/` |

### 输入参数
```python
{
    "query": str,                  # 搜索关键词
    "subreddits": list[str],       # 目标 subreddit 列表，可选
    "sort": str,                   # "relevance" | "hot" | "new" | "top"
    "time_filter": str,            # "year" | "month" | "week" | "all"
    "limit": int,                  # 每个 subreddit 获取帖子数，默认 100
    "include_comments": bool,      # 是否获取评论，默认 True
    "comment_limit": int,          # 每帖评论数，默认 50
}
```

### 输出格式
```python
{
    "posts": [
        {
            "id": str,
            "title": str,
            "body": str,
            "subreddit": str,
            "score": int,
            "num_comments": int,
            "created_utc": float,
            "url": str,
            "comments": [
                {
                    "id": str,
                    "body": str,
                    "score": int,
                    "created_utc": float,
                }
            ]
        }
    ],
    "metadata": {
        "source": "reddit",
        "total_posts": int,
        "total_comments": int,
        "fetched_at": str,
        "status": "success" | "partial" | "failed",
    }
}
```

### 速率限制
- OAuth 认证：100 请求/分钟
- 无认证：10 请求/分钟
- 响应头 `X-Ratelimit-Remaining` 提供实时配额信息

### 错误处理
| 错误类型 | 处理方式 |
|---|---|
| HTTP 401 Unauthorized | 刷新 OAuth Token，重试 1 次 |
| HTTP 429 Rate Limit | 读取 `Retry-After` 头，等待后重试 |
| HTTP 403 Forbidden | 记录日志，跳过该 subreddit |
| HTTP 503 Service Unavailable | 退避重试，最多 3 次 |
| 超时 | 重试 2 次 |

### 降级策略
- **Level 1**：减少 subreddit 数量，减少评论获取量
- **Level 2**：仅获取帖子标题和分数，不获取评论
- **Level 3**：使用 Reddit 搜索页面抓取替代 API
- **Level 4**：跳过该数据源，报告中标注 "Reddit 数据不可用"

---

## 3. producthunt

| 规格项 | 详情 |
|---|---|
| **依赖库** | `httpx >= 0.24.0`（GraphQL 请求） |
| **认证方式** | Bearer Token（Developer Token） |
| **基础 URL** | `https://api.producthunt.com/v2/api/graphql` |

### 输入参数
```python
{
    "query": str,                  # 搜索关键词
    "topic": str,                  # 话题筛选，可选
    "order": str,                  # "RANKING" | "NEWEST" | "VOTES"
    "posted_after": str,           # ISO 8601 日期，可选
    "posted_before": str,          # ISO 8601 日期，可选
    "limit": int,                  # 获取数量，默认 20
}
```

### 输出格式
```python
{
    "products": [
        {
            "id": str,
            "name": str,
            "tagline": str,
            "description": str,
            "votes_count": int,
            "comments_count": int,
            "website": str,
            "topics": list[str],
            "created_at": str,
            "thumbnail_url": str,
            "makers": list[dict],     # {"name": str, "headline": str}
        }
    ],
    "metadata": {
        "source": "producthunt",
        "total_results": int,
        "fetched_at": str,
        "status": "success" | "partial" | "failed",
    }
}
```

### 速率限制
- 450 请求/15分钟（约 30 请求/分钟）
- 通过响应头 `X-Rate-Limit-Remaining` 监控

### 错误处理
| 错误类型 | 处理方式 |
|---|---|
| HTTP 401 | 检查 Token 有效性，提示用户重新配置 |
| HTTP 429 | 等待至速率限制重置，自动重试 |
| GraphQL 错误 | 解析错误信息，记录日志 |
| 超时 | 重试 2 次 |

### 降级策略
- **Level 1**：减少请求字段，简化 GraphQL 查询
- **Level 2**：分页获取，减小单次请求量
- **Level 3**：跳过该数据源，报告中标注 "Product Hunt 数据不可用"

---

## 4. amazon

| 规格项 | 详情 |
|---|---|
| **依赖库** | `paapi5-python-sdk >= 1.0.0` 或 `httpx` + 自定义签名 |
| **认证方式** | HMAC-SHA256 签名（Access Key + Secret Key） |
| **基础 URL** | `https://webservices.amazon.com/paapi5/` |

### 输入参数
```python
{
    "keywords": str,               # 搜索关键词
    "category": str,               # 商品类别，如 "Electronics"
    "sort_by": str,                # "Relevance" | "Price:LowToHigh" | "Price:HighToLow" | "AvgCustomerReviews"
    "min_price": int,              # 最低价格（分），可选
    "max_price": int,              # 最高价格（分），可选
    "item_count": int,             # 每页数量，最大 10
    "item_page": int,              # 页码，最大 10
    "marketplace": str,            # 默认 "www.amazon.com"
}
```

### 输出格式
```python
{
    "products": [
        {
            "asin": str,
            "title": str,
            "price": {
                "amount": float,
                "currency": str,
            },
            "rating": float,          # 0-5
            "total_reviews": int,
            "category": str,
            "features": list[str],
            "image_url": str,
            "url": str,
        }
    ],
    "metadata": {
        "source": "amazon",
        "total_results": int,
        "fetched_at": str,
        "status": "success" | "partial" | "failed",
    }
}
```

### 速率限制
- 初始：1 请求/秒
- 随 Associates 销售额增加：最高 10 请求/秒
- **重要**：超出限制返回 HTTP 429，需严格限速

### 错误处理
| 错误类型 | 处理方式 |
|---|---|
| HTTP 429 TooManyRequests | 严格限速至 1 req/s，退避重试 |
| HTTP 401 InvalidSignature | 检查密钥配置，提示用户 |
| HTTP 403 AccountNotActive | 检查 Associates 账号状态 |
| 无搜索结果 | 尝试放宽搜索条件，记录日志 |
| 超时 | 重试 2 次 |

### 降级策略
- **Level 1**：降低请求频率至 0.5 req/s
- **Level 2**：减少搜索页面数（仅获取前 2 页）
- **Level 3**：使用网页抓取替代（需遵守 robots.txt，风险较高）
- **Level 4**：跳过该数据源，报告中标注 "Amazon 数据不可用"

---

## 5. app_store

| 规格项 | 详情 |
|---|---|
| **依赖库** | `app-store-scraper >= 0.3.5` |
| **认证方式** | 无需认证 |
| **基础 URL** | 通过库内部处理（iTunes API） |

### 输入参数
```python
{
    "query": str,                  # 搜索关键词
    "country": str,                # 国家代码，默认 "us"
    "language": str,               # 语言代码，默认 "en"
    "num_results": int,            # 搜索结果数量，默认 20
    "fetch_reviews": bool,         # 是否获取评论，默认 True
    "review_count": int,           # 每个应用评论数，默认 100
}
```

### 输出格式
```python
{
    "apps": [
        {
            "app_id": str,
            "name": str,
            "developer": str,
            "price": float,
            "rating": float,           # 0-5
            "total_ratings": int,
            "description": str,
            "genre": str,
            "release_date": str,
            "last_updated": str,
            "version": str,
            "size_bytes": int,
            "reviews": [
                {
                    "title": str,
                    "content": str,
                    "rating": int,
                    "date": str,
                    "developer_response": str | None,
                }
            ]
        }
    ],
    "metadata": {
        "source": "app_store",
        "total_results": int,
        "fetched_at": str,
        "status": "success" | "partial" | "failed",
    }
}
```

### 速率限制
- 无官方限制
- **实际约束**：Apple 对频繁请求较为敏感
- **建议策略**：每次请求间隔 3-5 秒，评论获取间隔更长

### 错误处理
| 错误类型 | 处理方式 |
|---|---|
| HTTP 403 | 增加请求间隔，更换 User-Agent |
| HTTP 503 | 退避重试，最多 3 次 |
| 解析错误 | 记录日志，跳过该应用 |
| 评论获取失败 | 返回已获取的部分数据 |
| 超时 | 增加超时时间，重试 2 次 |

### 降级策略
- **Level 1**：减少评论获取数量（100 → 30）
- **Level 2**：仅获取应用基本信息，跳过评论
- **Level 3**：使用 iTunes Search API 作为替代（数据较少）
- **Level 4**：跳过该数据源，报告中标注 "App Store 数据不可用"

---

## 6. google_play

| 规格项 | 详情 |
|---|---|
| **依赖库** | `google-play-scraper >= 1.2.4` |
| **认证方式** | 无需认证 |
| **基础 URL** | 通过库内部处理 |

### 输入参数
```python
{
    "query": str,                  # 搜索关键词
    "country": str,                # 国家代码，默认 "us"
    "language": str,               # 语言代码，默认 "en"
    "num_results": int,            # 搜索结果数量，默认 20
    "fetch_reviews": bool,         # 是否获取评论，默认 True
    "review_count": int,           # 每个应用评论数，默认 100
    "review_sort": str,            # "MOST_RELEVANT" | "NEWEST" | "RATING"
}
```

### 输出格式
```python
{
    "apps": [
        {
            "app_id": str,             # 包名，如 "com.example.app"
            "name": str,
            "developer": str,
            "price": float,
            "rating": float,           # 0-5
            "total_ratings": int,
            "installs": str,           # 如 "1,000,000+"
            "description": str,
            "genre": str,
            "release_date": str,
            "last_updated": str,
            "version": str,
            "size": str,
            "reviews": [
                {
                    "content": str,
                    "rating": int,
                    "thumbs_up": int,
                    "date": str,
                    "reply_content": str | None,
                    "reply_date": str | None,
                }
            ]
        }
    ],
    "metadata": {
        "source": "google_play",
        "total_results": int,
        "fetched_at": str,
        "status": "success" | "partial" | "failed",
    }
}
```

### 速率限制
- 无官方限制
- **建议策略**：每次请求间隔 1-2 秒

### 错误处理
| 错误类型 | 处理方式 |
|---|---|
| `NotFoundError` | 跳过该应用，记录日志 |
| HTTP 429 | 增加间隔至 5 秒，退避重试 |
| 解析错误 | 记录日志，跳过该应用 |
| 评论获取失败 | 返回已获取的部分数据 |
| 超时 | 重试 2 次 |

### 降级策略
- **Level 1**：减少评论获取数量
- **Level 2**：仅获取应用基本信息，跳过评论
- **Level 3**：跳过该数据源，报告中标注 "Google Play 数据不可用"

---

## 7. similarweb

| 规格项 | 详情 |
|---|---|
| **依赖库** | `httpx >= 0.24.0` |
| **认证方式** | API Key（Query Parameter 或 Header） |
| **基础 URL** | `https://api.similarweb.com/v1/` |

### 输入参数
```python
{
    "domain": str,                 # 目标域名，如 "example.com"
    "country": str,                # 国家代码，默认 "world"
    "start_date": str,             # 开始月份 "2025-01"
    "end_date": str,               # 结束月份 "2025-12"
    "granularity": str,            # "monthly" | "weekly" | "daily"
    "metrics": list[str],          # 请求指标列表
    # 可选指标: "visits", "page_views", "bounce_rate",
    #          "avg_visit_duration", "traffic_sources",
    #          "top_keywords", "competitors"
}
```

### 输出格式
```python
{
    "website_data": {
        "domain": str,
        "global_rank": int,
        "country_rank": int,
        "category_rank": int,
        "visits": {
            "monthly": list[dict],     # {"date": str, "visits": int}
        },
        "traffic_sources": {
            "direct": float,           # 百分比
            "referral": float,
            "search": float,
            "social": float,
            "mail": float,
            "paid": float,
        },
        "top_keywords": {
            "organic": list[dict],     # {"keyword": str, "share": float}
            "paid": list[dict],
        },
        "competitors": list[dict],     # {"domain": str, "similarity": float}
    },
    "metadata": {
        "source": "similarweb",
        "fetched_at": str,
        "status": "success" | "partial" | "failed",
    }
}
```

### 速率限制
- 取决于订阅计划
- 免费版：无 API 访问
- 付费版：通常 10-100 请求/分钟

### 错误处理
| 错误类型 | 处理方式 |
|---|---|
| HTTP 401 | 检查 API Key，提示用户配置 |
| HTTP 403 | 订阅计划不支持该端点，记录日志 |
| HTTP 429 | 退避重试，等待限速重置 |
| 数据不足 | 返回可用数据，标记缺失字段 |
| 超时 | 增加超时至 90 秒，重试 1 次 |

### 降级策略
- **Level 1**：减少请求指标数量
- **Level 2**：仅请求核心指标（visits, traffic_sources）
- **Level 3**：使用公开可用的基础排名数据
- **Level 4**：跳过该数据源，报告中标注 "SimilarWeb 数据不可用（需付费 API）"

---

## 8. crunchbase

| 规格项 | 详情 |
|---|---|
| **依赖库** | `httpx >= 0.24.0` |
| **认证方式** | API Key（Header: `X-cb-user-key`） |
| **基础 URL** | `https://api.crunchbase.com/api/v4/` |

### 输入参数
```python
{
    "query": str,                  # 搜索关键词
    "entity_type": str,            # "organization" | "funding_round" | "person"
    "location": str,               # 地区筛选，可选
    "categories": list[str],       # 行业类别筛选，可选
    "founded_after": str,          # 成立时间筛选，可选
    "funding_total_min": int,      # 最低融资额（USD），可选
    "funding_total_max": int,      # 最高融资额（USD），可选
    "last_funding_type": str,      # 最近融资轮次，如 "seed", "series_a"
    "limit": int,                  # 结果数量，默认 25
}
```

### 输出格式
```python
{
    "organizations": [
        {
            "uuid": str,
            "name": str,
            "short_description": str,
            "website": str,
            "founded_on": str,
            "location": str,
            "num_employees_enum": str,   # 如 "c_011_050"
            "categories": list[str],
            "funding_total": {
                "value": float,
                "currency": str,
            },
            "funding_rounds": [
                {
                    "announced_on": str,
                    "funding_type": str,     # "seed", "series_a" 等
                    "money_raised": {
                        "value": float,
                        "currency": str,
                    },
                    "lead_investors": list[str],
                    "num_investors": int,
                }
            ],
            "last_funding_date": str,
            "status": str,               # "operating", "closed", "acquired"
        }
    ],
    "metadata": {
        "source": "crunchbase",
        "total_results": int,
        "fetched_at": str,
        "status": "success" | "partial" | "failed",
    }
}
```

### 速率限制
- Basic：200 请求/分钟
- Pro/Enterprise：更高限制（视计划而定）

### 错误处理
| 错误类型 | 处理方式 |
|---|---|
| HTTP 401 | 检查 API Key，提示用户配置 |
| HTTP 403 | 订阅计划限制，记录日志 |
| HTTP 429 | 读取 `Retry-After`，退避重试 |
| 搜索无结果 | 尝试放宽搜索条件（去除筛选项） |
| 超时 | 重试 2 次 |

### 降级策略
- **Level 1**：减少筛选条件，扩大搜索范围
- **Level 2**：仅获取组织基本信息，跳过融资详情
- **Level 3**：使用 Crunchbase 网页搜索页面抓取基础信息
- **Level 4**：跳过该数据源，报告中标注 "Crunchbase 数据不可用"

---

## 通用规格

### 统一状态码

所有数据源模块的 `metadata.status` 字段使用统一状态值：

| 状态 | 含义 |
|---|---|
| `success` | 数据完整获取 |
| `partial` | 部分数据获取成功（如评论获取失败但基本信息正常） |
| `failed` | 数据获取完全失败 |
| `skipped` | 数据源未配置或主动跳过 |
| `cached` | 返回的是缓存数据而非实时数据 |

### 统一超时策略
- 默认超时：30 秒
- 最大超时：90 秒（仅 SimilarWeb）
- 整体数据采集超时：10 分钟（所有数据源并行采集总耗时上限）

### 统一重试策略
```python
retry_config = {
    "max_retries": 3,
    "backoff_factor": 1.5,       # 退避系数
    "backoff_max": 60,           # 最大等待秒数
    "retry_on": [429, 500, 502, 503, 504],
}
```

### 缓存策略
- 缓存有效期：24 小时（同一关键词 + 同一数据源）
- 缓存存储：本地文件系统（`~/.market-research/cache/`）
- 缓存命名：`{source}_{md5(params)}.json`
- 强制刷新：支持 `force_refresh=True` 参数跳过缓存

### 并发策略
- 所有 8 个数据源并行采集（使用 `asyncio` / `httpx.AsyncClient`）
- 单个数据源失败不阻断其他数据源
- 等待所有数据源完成或超时后统一汇总结果

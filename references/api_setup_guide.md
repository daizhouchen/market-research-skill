# API 配置指南

本文档为市场研究技能所需的各平台 API 提供逐步配置说明。

---

## 1. Google Trends

| 项目 | 详情 |
|---|---|
| **费用** | 免费 |
| **注册地址** | 无需注册 |
| **审批时间** | 无需审批 |

### 配置步骤
1. 无需任何 API 配置
2. 使用 `pytrends` 库直接访问（非官方库，通过模拟浏览器请求）
3. 安装：`pip install pytrends`

### 配置字段
```yaml
google_trends:
  # 无需 API key
  timeout: 30          # 请求超时（秒）
  retries: 3           # 重试次数
  backoff_factor: 1.5  # 退避系数
```

### 限制与注意事项
- **速率限制**：无官方限制，但频繁请求会被 Google 临时封禁 IP
- **应对策略**：每次请求间隔 2-5 秒随机延迟
- **注意**：pytrends 为非官方库，Google 可能随时更改接口导致失效
- **代理**：建议配置代理池以应对 IP 封禁

---

## 2. Google Play Store

| 项目 | 详情 |
|---|---|
| **费用** | 免费 |
| **注册地址** | 无需注册 |
| **审批时间** | 无需审批 |

### 配置步骤
1. 无需任何 API 配置
2. 使用 `google-play-scraper` 库
3. 安装：`pip install google-play-scraper`

### 配置字段
```yaml
google_play:
  # 无需 API key
  language: "en"       # 语言
  country: "us"        # 国家/地区
  timeout: 30
  retries: 3
```

### 限制与注意事项
- **速率限制**：无官方限制，建议每次请求间隔 1-2 秒
- **注意**：抓取库为非官方，页面结构变化可能导致失效
- **数据范围**：可获取应用详情、评论、搜索结果、排行榜

---

## 3. App Store (Apple)

| 项目 | 详情 |
|---|---|
| **费用** | 免费 |
| **注册地址** | 无需注册 |
| **审批时间** | 无需审批 |

### 配置步骤
1. 无需任何 API 配置
2. 使用 `app-store-scraper` 库
3. 安装：`pip install app-store-scraper`

### 配置字段
```yaml
app_store:
  # 无需 API key
  country: "us"
  language: "en"
  timeout: 30
  retries: 3
```

### 限制与注意事项
- **速率限制**：Apple 对频繁请求较为敏感，建议间隔 3-5 秒
- **注意**：评论数据获取速度较慢，批量获取时需耐心等待
- **数据范围**：应用详情、评论、搜索结果

---

## 4. Reddit

| 项目 | 详情 |
|---|---|
| **费用** | 免费（API 基础访问） |
| **注册地址** | https://www.reddit.com/prefs/apps |
| **审批时间** | 1-2 天 |

### 配置步骤
1. 登录 Reddit 账号（无账号需先注册）
2. 访问 https://www.reddit.com/prefs/apps
3. 滚动到页面底部，点击 "create another app..."
4. 填写信息：
   - **name**：你的应用名称（如 `market-research-tool`）
   - **App type**：选择 `script`
   - **description**：可选
   - **about url**：可留空
   - **redirect uri**：填写 `http://localhost:8080`
5. 点击 "create app"
6. 记录 `client_id`（应用名下方的短字符串）和 `client_secret`

### 配置字段
```yaml
reddit:
  client_id: "你的client_id"
  client_secret: "你的client_secret"
  user_agent: "market-research:v1.0 (by /u/你的用户名)"
  username: "你的Reddit用户名"      # 可选，script 类型需要
  password: "你的Reddit密码"         # 可选，script 类型需要
  timeout: 30
  retries: 3
```

### 限制与注意事项
- **速率限制**：OAuth 认证后 100 请求/分钟（无认证 10 请求/分钟）
- **注意**：User-Agent 必须包含应用名称和版本号，否则可能被拒绝
- **注意**：2024 年后 Reddit 收紧了免费 API 访问，部分端点可能需要付费
- **数据范围**：帖子搜索、评论获取、subreddit 信息

---

## 5. Product Hunt

| 项目 | 详情 |
|---|---|
| **费用** | 免费 |
| **注册地址** | https://www.producthunt.com/v2/docs |
| **审批时间** | 即时（注册后立即可用） |

### 配置步骤
1. 登录 Product Hunt 账号
2. 访问 https://www.producthunt.com/v2/docs
3. 点击 "Get API Key" 或访问 API Dashboard
4. 创建新的 Application
5. 填写应用信息（名称、描述、回调 URL）
6. 获取 `Developer Token`（用于服务端访问）

### 配置字段
```yaml
producthunt:
  api_token: "你的Developer_Token"
  api_url: "https://api.producthunt.com/v2/api/graphql"
  timeout: 30
  retries: 3
```

### 限制与注意事项
- **速率限制**：每15分钟 450 次请求（GraphQL API）
- **注意**：Product Hunt 使用 GraphQL API，需构建查询语句
- **注意**：Developer Token 适用于服务端访问，不要暴露到客户端
- **数据范围**：产品列表、产品详情、投票数、评论

---

## 6. Amazon Product Advertising API (PA-API)

| 项目 | 详情 |
|---|---|
| **费用** | 免费（需有 Amazon Associates 账号） |
| **注册地址** | https://affiliate-program.amazon.com/ |
| **审批时间** | 1-3 天 |

### 配置步骤
1. 注册 Amazon Associates 账号（https://affiliate-program.amazon.com/）
2. 通过审核后（需要有活跃网站或社交媒体账号）
3. 登录 Associates Central
4. 进入 Tools → Product Advertising API
5. 点击 "Manage Your Credentials"
6. 生成 Access Key 和 Secret Key
7. 记录你的 Associate Tag（合作伙伴标签）

### 配置字段
```yaml
amazon:
  access_key: "你的Access_Key"
  secret_key: "你的Secret_Key"
  associate_tag: "你的Associate_Tag"
  region: "us-east-1"       # API 区域
  marketplace: "www.amazon.com"
  timeout: 30
  retries: 3
```

### 限制与注意事项
- **速率限制**：初始 1 请求/秒，随销售额增加而提升（最高 10 请求/秒）
- **重要前提**：需在180天内通过 Associates 产生至少 3 笔合格销售，否则账号会被关闭
- **注意**：PA-API 5.0 需要使用 HMAC-SHA256 签名请求
- **替代方案**：如无法获取 PA-API，可使用网页抓取作为降级策略（需遵守 robots.txt）
- **数据范围**：产品搜索、产品详情、价格信息、评分（不含评论全文）

---

## 7. SimilarWeb

| 项目 | 详情 |
|---|---|
| **费用** | 免费版极为有限；完整版 $15,000+/年 |
| **注册地址** | https://www.similarweb.com/ |
| **审批时间** | 免费版即时；付费版需联系销售 |

### 配置步骤
1. 访问 https://www.similarweb.com/ 注册账号
2. 免费版：注册后可在网页端查看有限数据
3. API 访问（付费）：
   - 联系 SimilarWeb 销售团队
   - 确认订阅计划后获取 API Key
   - API 文档：https://developers.similarweb.com/

### 配置字段
```yaml
similarweb:
  api_key: "你的API_Key"           # 付费版才有
  api_url: "https://api.similarweb.com/v1"
  timeout: 60                       # SimilarWeb 响应较慢
  retries: 2
```

### 限制与注意事项
- **速率限制**：取决于订阅计划（通常 10-100 请求/分钟）
- **免费版限制**：每月仅能查看少量网站数据，无 API 访问权限
- **降级策略**：无 API 时标记为不可用，该维度数据跳过
- **数据范围**（付费版）：网站流量、流量来源、受众画像、竞争对手、行业排名

---

## 8. Crunchbase

| 项目 | 详情 |
|---|---|
| **费用** | Basic 免费；Pro $49/月；Enterprise 需联系销售 |
| **注册地址** | https://www.crunchbase.com/ |
| **审批时间** | 即时（免费版） |

### 配置步骤
1. 访问 https://www.crunchbase.com/ 注册账号
2. 免费 Basic 版：注册后可通过网页查看基础数据
3. API 访问：
   - 访问 https://data.crunchbase.com/docs
   - 申请 Basic API Key（免费，但有限制）
   - 或升级到 Pro/Enterprise 获取完整 API 访问

### 配置字段
```yaml
crunchbase:
  api_key: "你的API_Key"
  api_url: "https://api.crunchbase.com/api/v4"
  timeout: 30
  retries: 3
```

### 限制与注意事项
- **速率限制**：Basic 200 请求/分钟；Pro/Enterprise 更高
- **免费版限制**：搜索结果有限，部分字段不可用
- **注意**：Crunchbase 数据以美国公司为主，其他地区覆盖较弱
- **数据范围**：公司信息、融资轮次、投资者、收购、人员信息

---

## 通用配置建议

### 环境变量管理
所有 API 密钥应通过环境变量或 `.env` 文件管理，切勿硬编码：

```bash
# .env 文件示例
REDDIT_CLIENT_ID=xxx
REDDIT_CLIENT_SECRET=xxx
PRODUCTHUNT_TOKEN=xxx
AMAZON_ACCESS_KEY=xxx
AMAZON_SECRET_KEY=xxx
AMAZON_ASSOCIATE_TAG=xxx
SIMILARWEB_API_KEY=xxx
CRUNCHBASE_API_KEY=xxx
```

### 优先级建议
如果无法一次性配置所有平台，建议按以下优先级逐步配置：

1. **必备（免费无需配置）**：Google Trends、Google Play、App Store
2. **高优先级（免费但需注册）**：Reddit、Product Hunt、Crunchbase (Basic)
3. **中优先级（需付费或额外条件）**：Amazon PA-API
4. **低优先级（费用较高）**：SimilarWeb

> 即使部分 API 未配置，系统也应能运行，对应数据源会自动降级处理（详见 `data_source_specs.md`）。

# 数据源状态

> 更新时间：{date}
> 调研关键词：{keyword}

---

## 可用数据源

{available_sources_section}

<!-- 示例格式：
- ✅ **Google Trends** — 搜索趋势数据，已获取 {google_trends_count} 条时间序列记录
- ✅ **Amazon** — 产品与评论数据，已获取 {amazon_product_count} 款产品，{amazon_review_count} 条评论
- ✅ **京东 (JD)** — 产品与评论数据，已获取 {jd_product_count} 款产品，{jd_review_count} 条评论
- ✅ **Reddit** — 用户讨论数据，已获取 {reddit_post_count} 条帖子
- ✅ **知乎** — 用户讨论数据，已获取 {zhihu_post_count} 条回答
-->

## 未配置数据源

{unconfigured_sources_section}

<!-- 示例格式：
- ⬜ **Semrush** — 竞争对手流量与关键词数据
  - 配置方法：设置环境变量 `SEMRUSH_API_KEY`，获取地址：https://www.semrush.com/api/
- ⬜ **SimilarWeb** — 网站流量对比数据
  - 配置方法：设置环境变量 `SIMILARWEB_API_KEY`
- ⬜ **社交媒体 API** — Twitter/微博舆情数据
  - 配置方法：设置对应平台的 API 凭证
-->

## 失败数据源

{failed_sources_section}

<!-- 示例格式：
- ❌ **淘宝** — 请求失败
  - 错误信息：{taobao_error}
  - 建议：检查网络连接或 API 凭证是否过期
- ❌ **Google Trends** — 速率限制
  - 错误信息：{google_trends_error}
  - 建议：等待 {retry_after} 秒后重试，或降低请求频率
-->

---

## 数据完整性评估

| 维度 | 状态 | 说明 |
|------|------|------|
| 搜索趋势 | {trend_data_status} | {trend_data_note} |
| 产品数据 | {product_data_status} | {product_data_note} |
| 用户评论 | {review_data_status} | {review_data_note} |
| 竞品信息 | {competitor_data_status} | {competitor_data_note} |
| 社交舆情 | {social_data_status} | {social_data_note} |

**综合数据充足度**：{data_sufficiency} / 5

> 💡 数据充足度越高，报告结论的可靠性越强。建议至少达到 3/5 再参考分析结论。

---

*提示：配置更多数据源可以提升报告的全面性和准确性。运行 `market-research config` 查看配置指南。*

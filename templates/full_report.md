# {keyword} 市场调研报告

> 生成日期：{date}
> 调研区域：{geo}
> 数据来源：{sources_summary}
> 置信等级：{confidence_level}

---

## 数据源状态

{data_source_status}

---

## 执行摘要

{executive_summary}

---

## 一、市场趋势分析

### 1.1 搜索热度趋势

- **趋势方向**：{trend_direction}
- **增长率**：{growth_rate}（近3个月均值 vs 前3个月均值）
- **增长加速度**：{acceleration}

{trend_chart_placeholder}

### 1.2 季节性特征

- **是否存在季节性**：{seasonality_exists}
- **高峰月份**：{peak_months}
- **低谷月份**：{trough_months}

### 1.3 机会关键词

| 关键词 | 增长率 | 说明 |
|--------|--------|------|
{opportunity_keywords_table}

---

## 二、产品竞争格局

### 2.1 竞品对比矩阵

| 产品 | 品牌 | 价格 | 评分 | {feature_columns} |
|------|------|------|------|{feature_separator}|
{competitor_matrix_table}

### 2.2 价格分析

- **价格区间**：{price_min} ~ {price_max}
- **中位价格**：{price_median}
- **均价**：{price_mean}
- **甜点价位**：{sweet_spot}

**价格分布：**

| 价格段 | 产品数 | 平均评分 |
|--------|--------|----------|
{price_distribution_table}

### 2.3 价格与评分相关性

- **相关系数**：{premium_correlation_coefficient}
- **解读**：{premium_correlation_interpretation}

### 2.4 市场空白

**空白价格段：**
{empty_price_segments}

**空白功能组合：**
{empty_feature_combinations}

---

## 三、用户需求与痛点

### 3.1 用户需求 TOP 10

| 排名 | 需求关键词 | 出现频次 | 来源 |
|------|-----------|----------|------|
{demand_top10_table}

### 3.2 用户痛点 TOP 10

| 排名 | 痛点关键词 | 出现频次 | 典型评论 |
|------|-----------|----------|----------|
{pain_points_top10_table}

### 3.3 未满足需求

{unmet_needs_list}

### 3.4 情感分析概览

- **正面评价占比**：{positive_pct}%
- **中性评价占比**：{neutral_pct}%
- **负面评价占比**：{negative_pct}%

**代表性正面评论：**

{representative_positive_quotes}

**代表性负面评论：**

{representative_negative_quotes}

---

## 四、竞争企业分析

### 4.1 主要玩家

| 品牌 | 市场份额 | 价格定位 | 核心优势 | 主要弱点 |
|------|---------|----------|---------|---------|
{players_table}

### 4.2 市场集中度

- **TOP3 市场份额**：{top3_share}%
- **HHI 指数**：{hhi_index}
- **市场格局判断**：{market_structure}

### 4.3 融资与新进入者

{funding_and_new_entrants}

---

## 五、洞察与建议

### 5.1 市场吸引力评估

| 维度 | 评分（1-5） | 说明 |
|------|-----------|------|
| 市场规模与增长 | {market_size_score} | {market_size_note} |
| 竞争激烈程度 | {competition_score} | {competition_note} |
| 利润空间 | {profit_score} | {profit_note} |
| 进入壁垒 | {barrier_score} | {barrier_note} |
| **综合评分** | **{overall_score}** | {overall_note} |

### 5.2 机会点

{opportunities_list}

### 5.3 风险提示

{risks_list}

### 5.4 差异化建议

{differentiation_suggestions}

### 5.5 行动项

| 优先级 | 行动项 | 预期效果 | 时间周期 |
|--------|--------|---------|---------|
{action_items_table}

---

## 附录

### A. 研究方法论

本报告采用以下数据收集和分析方法：

1. **搜索趋势**：基于 Google Trends 时间序列数据，使用线性回归分析趋势方向，月度聚合分析季节性（变异系数 > 0.3 判定为季节性存在）。
2. **竞品分析**：从多平台采集产品数据，构建功能对比矩阵，计算 HHI 指数评估市场集中度。
3. **情感分析**：基于中英文情感词典的关键词匹配方法，覆盖正面/负面关键词各 30+ 个。
4. **价格分析**：十分位分桶统计，皮尔逊相关系数评估价格-评分关系。

### B. 置信等级说明

| 等级 | 含义 |
|------|------|
| ★★★★★ | 多数据源交叉验证，样本充足，结论高度可信 |
| ★★★★☆ | 主要数据源可用，样本较充足，结论基本可信 |
| ★★★☆☆ | 部分数据源缺失，结论供参考 |
| ★★☆☆☆ | 数据源有限，结论仅作初步参考 |
| ★☆☆☆☆ | 数据严重不足，结论可靠性低 |

### C. 数据来源明细

{data_source_details}

### D. 待解决问题

{open_questions}

---

*本报告由 Market Research Skill 自动生成，数据采集时间截至 {date}。*
*报告中的分析结论基于公开数据，仅供参考，不构成商业决策的唯一依据。*

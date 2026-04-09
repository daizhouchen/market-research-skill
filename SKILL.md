---
name: market-research
description: "Adaptive market demand analysis skill for Claude Code. Dynamically generates API call strategies based on user-configured data sources, combines structured data collection with deep analysis frameworks, and outputs actionable market insight reports. Use this skill whenever the user mentions market analysis, market research, demand analysis, competitor analysis, product research, or asks questions like 'is there a market for X', 'is it worth building', 'market size', or wants to understand user needs, pain points, or competitive landscape for any product, category, or market direction — even if they don't explicitly say 'market research'."
---

# Market Research Skill — 自适应市场需求分析

根据用户已配置的 API 动态生成最优数据采集策略，结合结构化数据采集与深度分析框架，输出可落地的市场洞察报告。

## 核心理念

数据是手段，洞察是目的。本 Skill 聚焦于：

- **提出正确的问题**：用户说"分析智能手表市场"，Skill 应引导拆解为"谁在买、为什么买、买什么价位、哪些需求没被满足"
- **交叉验证**：同一个结论至少要有两个数据源佐证（如 Google Trends 显示增长 + Reddit 讨论量上升）
- **区分事实与推断**：数据是事实，洞察是推断，报告中必须标注清楚
- **指向行动**：每个发现都要回答"so what"——对用户的决策意味着什么

## 工作流概览

Skill 分为 5 个阶段运行：

```
阶段 1：环境准备 → 阶段 2：需求澄清 → 阶段 3：策略生成 → 阶段 4：数据采集与分析 → 阶段 5：报告生成
```

---

## 阶段 1：环境准备

1. 检查 `config/config.yaml` 是否存在
   - 不存在 → 从 `config/config.example.yaml` 复制，告知用户
2. 运行 `tools/config_loader.py` 检测可用数据源
   - 输出数据源状态汇总卡片
3. 如果可用数据源少于 3 个，主动建议配置
   - 读取 `references/api_setup_guide.md` 中对应章节
   - 引导用户完成配置
   - 配置后重新检测
4. 安装缺失的 Python 依赖：
   ```bash
   pip install pytrends praw google-play-scraper pyyaml requests numpy
   ```
   - 检查 Node.js 环境以支持 `app-store-scraper`（如需要）

## 阶段 2：需求澄清

与用户确认以下内容（如未明确指定则使用默认值，不逐一追问）：

1. **研究主题**：关键词 / 产品名 / 品类
2. **分析维度**（多选，默认全选）：
   - 市场趋势
   - 产品竞争格局
   - 用户需求与痛点
   - 竞品公司分析
3. **目标市场**：国家/地区（影响 API 参数和搜索语言）
4. **输出偏好**：快速摘要 / 完整报告，中文 / 英文

默认值：全部维度 + config 中的国家 + 完整报告 + 中文

## 阶段 3：策略生成

1. 读取 `config/dimensions.yaml` 获取维度与数据源的映射
2. 运行 `tools/strategy_engine.py` 生成调用计划
3. 向用户展示调用计划：
   - 将使用哪些 API
   - 将进行哪些 Web Search
   - 哪些维度因缺少数据源而降级
   - 预估耗时
4. 提示哪些维度可通过配置额外 API 来增强
5. 用户确认后进入阶段 4

## 阶段 4：数据采集与分析

1. 按调用计划依次执行数据采集
   - 每完成一个数据源，输出简短进度
   - 单个数据源失败 → 记录错误，标记降级，不中断流程
   - 如 `show_raw_data=true`，保存原始数据为 JSON

2. 数据清洗
   - 统一时间范围和地区范围
   - 标准化货币和评分量纲
   - 去除明显异常值和噪音

3. 读取 `references/analysis_framework.md`，按方法论逐维度分析：
   - 趋势分析 → `tools/analyzers/trend_analyzer.py`
   - 产品竞争 → `tools/analyzers/competitor_analyzer.py` + `tools/analyzers/pricing_analyzer.py`
   - 用户需求 → `tools/analyzers/sentiment_analyzer.py`
   - 竞品公司 → 结构化整理

4. 交叉验证：对每个初步结论检查是否有多数据源支撑，标注置信度

5. 按"五个关键问题"框架生成综合洞察（见 `references/analysis_framework.md`）

## 阶段 5：报告生成

1. 根据实际采集到的数据动态选择报告章节（无数据的维度跳过，不留空章节）
2. 使用 `templates/full_report.md` 或 `templates/quick_summary.md` 作为模板
3. 包含数据源状态卡片，保持完全透明
4. 输出后提示：
   - 哪些结论置信度较低需进一步验证
   - 配置更多 API 可以增强哪些维度
   - 用户可针对某个发现做深入追问

---

## 执行规则

1. **永远先读配置**：执行任何采集前必须先运行 `config_loader.py`
2. **缺配置要引导**：不只是标记"跳过"，要告知用户配置方法和收益
3. **展示计划再执行**：调用计划经用户确认后才执行
4. **错误不中断**：单个数据源失败 → 记录 → 降级 → 继续
5. **不造数据**：没采集到的维度跳过，不编造数据填充
6. **交叉验证**：写入"洞察"的结论必须有多数据源支撑
7. **标注来源**：每个数据点标注来自哪个数据源
8. **标注置信度**：每个推断标注 🟢(高) 🟡(中) 🔴(低)
9. **区分事实与推断**：数据是事实，分析是推断，不混淆
10. **指向行动**：每个发现回答"so what"
11. **引导深入**：报告结尾标注哪些问题需进一步验证
12. **中间数据可查**：原始采集数据保存为 JSON 供核查

---

## 资源索引

| 资源文件 | 何时读取 | 用途 |
|---------|---------|------|
| `config/config.example.yaml` | 阶段 1，config 缺失时 | API 配置模板 |
| `config/dimensions.yaml` | 阶段 3 | 分析维度与数据源映射 |
| `references/analysis_framework.md` | 阶段 4 | 核心分析方法论与推理框架 |
| `references/api_setup_guide.md` | 阶段 1，引导 API 配置时 | 各平台 API 配置指南 |
| `references/data_source_specs.md` | 阶段 4，调用 API 时 | 各数据源能力、限制、输出格式 |
| `templates/full_report.md` | 阶段 5 | 完整报告模板 |
| `templates/quick_summary.md` | 阶段 5 | 快速摘要模板 |
| `examples/` | 用户想看示例输出时 | 示例报告 |

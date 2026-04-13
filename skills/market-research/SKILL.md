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

Skill 分为 7 个阶段运行：

```
阶段 1：环境准备 → 阶段 2：需求澄清 → 阶段 3：策略生成 → 阶段 4：数据采集与基础分析 → 阶段 4.5：深度分析 → 阶段 5：报告生成（MD） → 阶段 6：格式转换（HTML/PDF）
```

---

## 阶段 1：环境准备

### 1.1 配置文件检查与生成

1. 检查 `config/config.yaml` 是否存在
   - **如果不存在**（首次使用）：
     a. **必须暂停工作流**，主动引导用户进行 API 配置
     b. 向用户展示可用数据源列表，分三个层级说明：
        - **免费无需配置**（Google Trends、Google Play、App Store、Reddit 公开接口）：告知用户这些数据源开箱即用
        - **免费但需注册**（Reddit API（更高限额）、Product Hunt、Crunchbase Basic）：告知注册地址和预计时间
        - **付费**（Amazon PA-API、SimilarWeb）：告知费用和是否值得配置
     c. 使用 AskUserQuestion 询问用户：
        - 是否要现在配置额外的 API 密钥？（推荐至少配置 Reddit 以获取用户讨论数据）
        - 还是先用免费数据源快速开始？
     d. **根据用户选择**：
        - 如果用户选择配置 → 读取 `references/api_setup_guide.md` 中对应章节，逐步引导配置，将用户提供的密钥写入 `config/config.yaml`
        - 如果用户选择跳过 → 从 `config/config.example.yaml` 复制为 `config/config.yaml`（保留免费数据源为 enabled，其余保持 disabled）
     e. **配置完成后，告知用户**：已生成配置文件 `config/config.yaml`，后续可随时编辑该文件添加更多 API 密钥
   - **如果已存在**：直接进入步骤 1.2（跳过引导流程）

### 1.2 数据源状态检测

2. 运行 `tools/config_loader.py` 检测可用数据源
   - 输出数据源状态汇总卡片（表格形式，包含 ✅/⚠️/❌ 状态图标）
3. 如果可用数据源少于 3 个，主动建议配置额外数据源
   - 读取 `references/api_setup_guide.md` 中对应章节
   - 明确告知用户：配置 Reddit 可获取真实用户讨论和痛点数据，配置 Crunchbase 可获取融资和公司数据
   - 用户选择不配置则继续，不阻塞流程

### 1.3 依赖安装

4. 安装缺失的 Python 依赖：
   ```bash
   pip install pytrends praw google-play-scraper pyyaml requests numpy
   ```
   - 检查 Node.js 环境以支持 `app-store-scraper`（如需要）

## 阶段 2：需求澄清

与用户确认以下内容（如未明确指定则使用默认值，不逐一追问）：

1. **研究主题**：关键词 / 产品名 / 品类
2. **分析维度**（多选，默认全选基础维度 + 按需启用深度维度）：
   - 基础维度（默认全选）：
     - 市场趋势
     - 产品竞争格局
     - 用户需求与痛点
     - 竞品公司分析
   - 深度维度（推荐在完整报告模式下启用）：
     - 市场规模估算（TAM/SAM/SOM）
     - 技术创新与壁垒分析
     - 供需先行信号分析（招聘、广告、供应链）
     - 用户深度洞察（JTBD + 旅程分析）
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

3. **Reddit 用户数据采集**（当 `reddit_public` 已启用且 `reddit` API 未配置时）：
   - 运行 `tools/sources/reddit_public.py --keyword {keyword}` 获取推荐的 subreddits 和搜索查询
   - 使用 WebSearch 执行 `site:reddit.com "{keyword}" pain points complaints` 等查询
   - 从搜索结果中提取 Reddit 用户的真实讨论、痛点、需求
   - 注意：Reddit 自 2024 年锁定了 .json 公开接口，因此通过 Web Search 间接获取

4. 读取 `references/analysis_framework.md`，按方法论逐维度分析：
   - 趋势分析 → `tools/analyzers/trend_analyzer.py`
   - 产品竞争 → `tools/analyzers/competitor_analyzer.py` + `tools/analyzers/pricing_analyzer.py`
   - 用户需求 → `tools/analyzers/sentiment_analyzer.py`
   - 竞品公司 → 结构化整理

4. 交叉验证：对每个初步结论检查是否有多数据源支撑，标注置信度

## 阶段 4.5：深度分析（v2 增强）

当用户选择了深度维度，或选择完整报告模式时执行。读取 `references/analysis_framework.md` 中的"深度分析方法论"章节。

1. **市场规模估算** → `tools/analyzers/market_sizer.py`
   - 自上而下法：从行业报告提取 TAM，按细分/地区缩减为 SAM/SOM
   - 自下而上法：从搜索量和竞品数据反推市场规模
   - 三角验证：取两种方法的范围交集
   - 判断市场生命周期阶段（萌芽/成长/成熟/衰退）

2. **竞争力学分析** → `tools/analyzers/innovation_tracker.py`
   - Porter 五力分析：对 5 个维度各评分 1-5，输出竞争强度评级
   - 蓝海画布：提取 6-10 个竞争要素，识别消除/减少/提升/创造方向
   - 技术采纳生命周期定位：判断市场处于创新者→落后者的哪个阶段
   - 技术壁垒评估：专利、开源、核心算法的护城河分析

3. **用户深度洞察** → `tools/analyzers/demand_deep_analyzer.py`
   - JTBD 分析：提取用户"任务"而非表面功能需求，计算机会分数
   - 主题聚类：评论/帖子的名词短语聚类，发现新兴主题
   - 特征共现分析：识别"必备组合"和"差异化组合"
   - 用户迁移路径：从"我从X换到Y"类评论中提取迁移网络
   - 价格敏感度分析：价格锚点、付费意愿分层、弹性估算

4. **先行信号扫描**（通过 Web Search 采集）
   - 招聘趋势：相关岗位的数量和薪资变化
   - 评论速度分析：评论/帖子数量的时间变化率 → `tools/analyzers/innovation_tracker.py`
   - 广告/投放信号：竞品的营销投入变化
   - 技术社区活跃度：GitHub Star 增长、技术博客热度

5. 按"五个关键问题"框架 + "综合深度分析输出框架"生成最终洞察

## 阶段 5：报告生成

1. 根据实际采集到的数据动态选择报告章节（无数据的维度跳过，不留空章节）
2. 使用 `templates/full_report.md` 或 `templates/quick_summary.md` 作为模板
3. 包含数据源状态卡片，保持完全透明
4. 输出后提示：
   - 哪些结论置信度较低需进一步验证
   - 配置更多 API 可以增强哪些维度
   - 用户可针对某个发现做深入追问

## 阶段 6：格式转换与输出（HTML/PDF）

在阶段 5 生成 Markdown 报告后，自动将其转换为美观的 HTML 网页报告，并引导用户获取 PDF。

### 6.1 安装依赖

```bash
pip install markdown
```

### 6.2 一键导出 HTML + PDF

运行 `tools/report_exporter.py`，**一条命令同时生成 HTML 和 PDF**：

```bash
python tools/report_exporter.py <报告.md>
```

脚本会自动完成以下全部步骤（无需用户干预）：
1. 从 MD 中提取标题和日期
2. 使用 `markdown` 库转换为 HTML 片段（含表格预处理修复）
3. 注入到 `templates/report_template.html` 模板中
4. 输出同名 `.html` 文件
5. **自动检测系统浏览器**（Edge → Chrome → Chromium，优先级依次递减）
6. **使用 headless 模式自动将 HTML 打印为 PDF**（无需打开浏览器窗口）
7. 输出同名 `.pdf` 文件

可选参数：
- `--output <目录>` / `-o <目录>`：指定输出目录
- `--no-pdf`：仅生成 HTML，跳过 PDF

如果系统无可用浏览器（极少见），脚本会输出警告并提示用户手动打印。

### 6.3 打开 HTML 供用户预览

HTML 和 PDF 生成后，尝试自动在浏览器中打开 HTML 文件供用户预览：
- Windows: `start "" "<html文件路径>"`
- Mac: `open "<html文件路径>"`
- Linux: `xdg-open "<html文件路径>"`

### 6.4 输出汇总

向用户展示最终输出文件列表：
- `{keyword}市场调研报告.md` — Markdown 原始报告（可编辑）
- `{keyword}市场调研报告.html` — HTML 网页报告（浏览器打开查看）
- `{keyword}市场调研报告.pdf` — PDF 报告（自动生成，可直接分享）

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
| `config/dimensions.yaml` | 阶段 3 | 分析维度与数据源映射（含深度维度） |
| `references/analysis_framework.md` | 阶段 4 & 4.5 | 核心方法论 + 深度分析框架（TAM/Porter/JTBD/蓝海等） |
| `references/api_setup_guide.md` | 阶段 1，引导 API 配置时 | 各平台 API 配置指南 |
| `references/data_source_specs.md` | 阶段 4，调用 API 时 | 各数据源能力、限制、输出格式 |
| `tools/analyzers/market_sizer.py` | 阶段 4.5 | 市场规模估算（TAM/SAM/SOM + 生命周期定位） |
| `tools/analyzers/innovation_tracker.py` | 阶段 4.5 | Porter 五力、蓝海画布、技术采纳定位、评论速度分析 |
| `tools/analyzers/demand_deep_analyzer.py` | 阶段 4.5 | JTBD 提取、主题聚类、迁移路径、价格敏感度 |
| `templates/full_report.md` | 阶段 5 | 完整报告模板（含深度分析章节） |
| `templates/quick_summary.md` | 阶段 5 | 快速摘要模板 |
| `templates/report_template.html` | 阶段 6 | HTML 报告模板（含内嵌 CSS 样式） |
| `tools/sources/reddit_public.py` | 阶段 4 | Reddit 数据辅助采集：生成 site:reddit.com 搜索查询 + subreddit 推荐（无需 API） |
| `tools/report_exporter.py` | 阶段 6 | MD→HTML 格式转换脚本 |
| `examples/` | 用户想看示例输出时 | 示例报告 |

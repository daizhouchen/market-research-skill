---
name: market-research
description: Research market demand, competitive landscape, pricing, and user needs using configured data sources and web research. Use when the user requests evidence-based market analysis for a product, category, or market decision. Produce a sourced report with assumptions and data gaps; ordinary product advice does not require the full workflow.
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

路径相对本次加载的 `SKILL.md` 所在目录（插件版位于 `skills/market-research/`），不要把配置写到其他安装副本。

1. 检查 `config/config.yaml`；缺失时从 `config/config.example.yaml` 复制，以默认无需密钥的数据源开始。无需为配置不存在暂停研究。
2. 用户明确希望配置额外 API 时，读取对应配置指南；凭据只保存在本地配置，报告与日志不输出密钥。
3. “无需密钥”不保证网络可达；请求失败时记录状态并按计划降级。

### 1.2 数据源状态检测

2. 运行 `tools/config_loader.py` 检查已启用的数据源和凭据字段；其 available 状态仅表示配置就绪，不验证网络、权限或配额
   - 输出数据源状态汇总卡片（表格形式，包含 ✅/⚠️/❌ 状态图标）
3. 如果可用数据源少于 3 个，主动建议配置额外数据源
   - 读取 `references/api_setup_guide.md` 中对应章节
   - 明确告知用户：配置 Reddit 可获取真实用户讨论和痛点数据，配置 Crunchbase 可获取融资和公司数据
   - 用户选择不配置则继续，不阻塞流程

### 1.3 依赖安装

4. 使用 Python 3.10+；按仓库根目录 `requirements.txt` 安装所需依赖：
   ```bash
   python -m pip install -r <仓库根目录>/requirements.txt
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
5. 已在用户授权范围内的公开检索直接进入阶段 4；额外费用或未授权 API 调用先说明具体计划并确认

## 阶段 4：数据采集与分析

1. 按调用计划依次执行数据采集
   - 每完成一个数据源，输出简短进度
   - 单个数据源失败 → 记录错误，标记降级，不中断流程；缺失值保留为未知，不用 0 代替，也不据此判断没有需求
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
   - 自下而上法：仅用有单位、地区、期间的绝对搜索量和竞品数据做情景估算；Google Trends 的 0–100 指数不能直接当搜索量
   - 脚本内置细分比例、触达率等启发式假设，未有数据支持时只作为明确标记的情景，不把计算结果称为观测事实
   - 三角验证：对照两种方法的估算范围和口径，说明分歧；只有一组数据时不能宣称已经交叉验证
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

1. 根据实际采集到的数据选择章节；无数据的维度不编造分析，在数据源状态卡片中保留缺口与对结论的影响
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

向用户展示实际生成成功的文件及失败原因；未生成的 PDF 不列为已交付：
- `{keyword}市场调研报告.md` — Markdown 原始报告（可编辑）
- `{keyword}市场调研报告.html` — HTML 网页报告（浏览器打开查看）
- `{keyword}市场调研报告.pdf` — PDF 报告（自动生成，可直接分享）

---

## 执行规则

1. **永远先读配置**：执行任何采集前必须先运行 `config_loader.py`
2. **缺配置不阻塞**：使用默认无需密钥的数据源，并说明可选配置方法
3. **展示计划再执行**：按已授权范围推进；额外付费或未授权调用单独确认
4. **错误不中断**：单个数据源失败 → 记录 → 降级 → 继续
5. **不造数据**：没采集到的维度跳过，不编造数据填充
6. **交叉验证**：核心判断尽量取得独立来源印证；单一来源明确标记局限，转载同一材料不算多源
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

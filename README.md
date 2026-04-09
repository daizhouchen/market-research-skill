# Market Research Skill

一个为 Claude Code 设计的自适应市场需求分析 Skill。根据用户已配置的 API 动态生成调用策略，结合结构化数据采集与深度分析框架，输出可落地的市场洞察报告。

## 特性

- **零配置可用**：Google Trends + App Store/Google Play 无需 API Key，加上 Web Search 兜底
- **动态策略引擎**：根据可用数据源自动生成最优采集方案
- **交叉验证**：每个结论至少有两个数据源佐证
- **置信度标注**：区分事实与推断，标注 🟢🟡🔴 置信度
- **渐进式增强**：配置更多 API 可解锁更深入的分析维度

## 支持的数据源

| 数据源 | 需要 API Key | 覆盖维度 |
|--------|------------|---------|
| Google Trends | 否 | 市场趋势 |
| Google Play | 否 | 产品竞争 |
| App Store | 否 | 产品竞争 |
| Reddit | 是（免费） | 用户需求 |
| Product Hunt | 是（免费） | 产品竞争 |
| Amazon PA-API | 是（免费） | 产品竞争 |
| SimilarWeb | 是（付费） | 流量分析 |
| Crunchbase | 是（免费） | 竞品公司 |

## 快速开始

1. 将 `config/config.example.yaml` 复制为 `config/config.yaml`
2. 填入你拥有的 API 凭据（没有的留空）
3. 在 Claude Code 中说："帮我分析智能手表市场"

## 安装依赖

```bash
pip install -r requirements.txt
```

## 文件结构

```
market-research/
├── SKILL.md                     # Skill 入口
├── config/
│   ├── config.example.yaml      # API 配置模板
│   └── dimensions.yaml          # 分析维度映射
├── references/
│   ├── analysis_framework.md    # 分析方法论
│   ├── api_setup_guide.md       # API 配置指南
│   └── data_source_specs.md     # 数据源技术规格
├── tools/
│   ├── config_loader.py         # 配置加载与检测
│   ├── strategy_engine.py       # 动态策略引擎
│   ├── sources/                 # 数据采集模块
│   └── analyzers/               # 数据分析模块
├── templates/                   # 报告模板
└── examples/                    # 示例输出
```

## License

MIT

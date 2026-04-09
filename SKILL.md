---
name: market-research
description: "Adaptive market demand analysis skill for Claude Code. Dynamically generates API call strategies based on user-configured data sources, combines structured data collection with deep analysis frameworks, and outputs actionable market insight reports. Use this skill whenever the user mentions market analysis, market research, demand analysis, competitor analysis, product research, or asks questions like 'is there a market for X', 'is it worth building', 'market size', or wants to understand user needs, pain points, or competitive landscape for any product, category, or market direction — even if they don't explicitly say 'market research'."
---

# Market Research Skill

An adaptive market demand analysis skill. Based on your configured APIs, it dynamically generates optimal data collection strategies, combines structured data with deep analysis frameworks, and outputs actionable market insight reports.

## Core Philosophy

Data is the means; insight is the purpose. This skill focuses on:

- **Asking the right questions**: "Analyze the smartwatch market" gets decomposed into "who's buying, why, at what price point, what needs are unmet"
- **Cross-validation**: Every conclusion needs at least two independent data sources
- **Distinguishing fact from inference**: Data is fact, insights are inference — the report must label them clearly
- **Action-oriented**: Every finding answers "so what" — what does it mean for the user's decision

## Workflow Overview

The skill operates in 5 phases:

```
Phase 1: Environment Setup → Phase 2: Requirements Clarification → Phase 3: Strategy Generation → Phase 4: Data Collection & Analysis → Phase 5: Report Generation
```

---

## Phase 1: Environment Setup

1. Check if `config/config.yaml` exists in the skill directory
   - If not, copy from `config/config.example.yaml` and inform the user
2. Run `tools/config_loader.py` to detect available data sources
   - Output a status summary card showing which sources are available
3. If fewer than 3 sources are available, proactively suggest configuration
   - Read the relevant section from `references/api_setup_guide.md`
   - Guide the user through setup
   - Re-detect after configuration
4. Install missing Python dependencies:
   ```bash
   pip install pytrends praw google-play-scraper pyyaml requests numpy
   ```
   - Check Node.js availability for `app-store-scraper` if needed

## Phase 2: Requirements Clarification

Confirm with the user (use defaults if not specified — don't ask one by one):

1. **Research topic**: keyword / product name / category
2. **Analysis dimensions** (multi-select, default all):
   - Market trends
   - Product competition landscape
   - User needs & pain points
   - Competitor company analysis
3. **Target market**: country/region (affects API params and search language)
4. **Output preference**: quick summary / full report, Chinese / English

Defaults: all dimensions + country from config + full report + Chinese

## Phase 3: Strategy Generation

1. Read `config/dimensions.yaml` for dimension-to-source mapping
2. Run `tools/strategy_engine.py` to generate a call plan
3. Present the plan to the user:
   - Which APIs will be called
   - Which web searches will be performed
   - Which dimensions are degraded due to missing sources
   - Estimated time
4. Highlight which dimensions could be enhanced by configuring additional APIs
5. Proceed to Phase 4 after user confirmation

## Phase 4: Data Collection & Analysis

1. Execute data collection per the call plan
   - Show brief progress after each source completes
   - Single source failure → log error, mark as degraded, continue (never abort)
   - Save raw data as JSON if `show_raw_data=true`

2. Data cleaning
   - Align time ranges and geographic scope across sources
   - Normalize currencies, rating scales
   - Remove obvious outliers and noise

3. Read `references/analysis_framework.md` and analyze each dimension:
   - Trends → `tools/analyzers/trend_analyzer.py`
   - Product competition → `tools/analyzers/competitor_analyzer.py` + `tools/analyzers/pricing_analyzer.py`
   - User needs → `tools/analyzers/sentiment_analyzer.py`
   - Competitor companies → structured organization

4. Cross-validate: check each preliminary conclusion against multiple sources, assign confidence levels

5. Synthesize using the "Five Key Questions" framework (see `references/analysis_framework.md`)

## Phase 5: Report Generation

1. Dynamically select report sections based on available data (skip dimensions with no data — no empty sections)
2. Use `templates/full_report.md` or `templates/quick_summary.md` as the template
3. Include data source status card for full transparency
4. After output, prompt:
   - Which conclusions have low confidence and need verification
   - Which dimensions could be enhanced by configuring more APIs
   - The user can deep-dive into any finding

---

## Execution Rules

1. **Always read config first**: Run `config_loader.py` before any data collection
2. **Guide on missing config**: Don't just mark "skipped" — tell the user how to configure and what they'd gain
3. **Show plan before executing**: Get user confirmation on the call plan
4. **Errors don't abort**: Single source failure → log → degrade → continue
5. **Never fabricate data**: Skip uncollected dimensions, never fill with made-up data
6. **Cross-validate**: Conclusions in "insights" must have multi-source support
7. **Cite sources**: Every data point labeled with its source
8. **Label confidence**: Every inference tagged 🟢(high) 🟡(medium) 🔴(low)
9. **Separate fact from inference**: Data is fact, analysis is inference — never mix
10. **Point to action**: Every finding answers "so what"
11. **Guide deeper exploration**: End report with questions needing further verification
12. **Auditable raw data**: Save collected data as JSON for verification

---

## Resource Map

| Resource | When to Read | Purpose |
|----------|-------------|---------|
| `config/config.example.yaml` | Phase 1, when config missing | API configuration template |
| `config/dimensions.yaml` | Phase 3 | Dimension-to-source mapping |
| `references/analysis_framework.md` | Phase 4 | Core analysis methodology & reasoning framework |
| `references/api_setup_guide.md` | Phase 1, when guiding API setup | Step-by-step API configuration guide |
| `references/data_source_specs.md` | Phase 4, when calling APIs | API capabilities, limits, output formats |
| `templates/full_report.md` | Phase 5 | Full report template |
| `templates/quick_summary.md` | Phase 5 | Quick summary template |
| `examples/` | When user wants to see sample output | Example reports |

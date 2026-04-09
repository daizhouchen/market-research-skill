"""
策略引擎 - 根据可用数据源和所选维度生成调研执行计划

功能:
- 接收可用数据源列表、选定维度、关键词和地区
- 读取 config/dimensions.yaml 中的维度-数据源映射
- 对每个维度按 primary -> secondary -> fallback 顺序匹配可用数据源
- 生成调研调用计划: API调用优先, Web搜索兜底
- 去重并排序输出
- 支持JSON输出和中文可读计划
"""

import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional

try:
    import yaml
except ImportError:
    print("[错误] 缺少 PyYAML 依赖，请运行: pip install pyyaml")
    yaml = None

# 避免循环导入，延迟引用
_config_loader = None


def _get_config_loader():
    """延迟加载 config_loader 模块。"""
    global _config_loader
    if _config_loader is None:
        try:
            from tools import config_loader as cl
            _config_loader = cl
        except ImportError:
            # 同目录导入
            script_dir = os.path.dirname(os.path.abspath(__file__))
            sys.path.insert(0, script_dir)
            try:
                import config_loader as cl
                _config_loader = cl
            finally:
                sys.path.pop(0)
    return _config_loader


def load_dimensions(dimensions_path: str) -> Optional[Dict[str, Any]]:
    """加载维度配置文件。

    Args:
        dimensions_path: dimensions.yaml 文件路径

    Returns:
        维度配置字典，失败返回None
    """
    if yaml is None:
        return None
    try:
        with open(dimensions_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        print(f"[错误] 维度配置文件不存在: {dimensions_path}")
        return None
    except yaml.YAMLError as e:
        print(f"[错误] YAML解析失败: {e}")
        return None


def _resolve_source_for_dimension(
    dimension_config: Dict[str, Any],
    available_sources: List[str],
) -> Optional[str]:
    """为单个维度解析最佳可用数据源。

    按 primary -> secondary -> fallback 顺序尝试。

    Args:
        dimension_config: 单个维度的配置
        available_sources: 可用数据源列表

    Returns:
        匹配到的数据源名称，无匹配返回None
    """
    for priority in ["primary", "secondary", "fallback"]:
        sources = dimension_config.get(priority, [])
        if isinstance(sources, str):
            sources = [sources]
        for source in sources:
            if source in available_sources or source == "web_search":
                return source
    return None


def _build_web_search_queries(
    keyword: str,
    geo: str,
    dimensions: List[str],
    dimensions_config: Dict[str, Any],
) -> List[str]:
    """为需要Web搜索兜底的维度生成搜索查询。

    Args:
        keyword: 调研关键词
        geo: 地区代码
        dimensions: 需要Web搜索的维度列表
        dimensions_config: 维度配置

    Returns:
        搜索查询字符串列表
    """
    query_templates = {
        "market_size": "{keyword} market size {geo} 2024 2025",
        "competitors": "{keyword} competitors analysis {geo}",
        "pricing": "{keyword} pricing comparison {geo}",
        "user_reviews": "{keyword} user reviews complaints {geo}",
        "trends": "{keyword} market trends forecast {geo}",
        "technology": "{keyword} technology stack features comparison",
        "funding": "{keyword} startup funding investment {geo}",
        "regulations": "{keyword} regulations policy {geo}",
        "supply_chain": "{keyword} supply chain manufacturers {geo}",
        "user_demographics": "{keyword} user demographics target audience {geo}",
    }
    queries = []
    for dim in dimensions:
        template = query_templates.get(dim, "{keyword} {dim} {geo}")
        query = template.format(keyword=keyword, geo=geo, dim=dim)
        queries.append(query.strip())
    return queries


def generate_call_plan(
    available_sources: List[str],
    selected_dimensions: List[str],
    keyword: str,
    geo: str,
    dimensions_path: str,
) -> Dict[str, Any]:
    """生成调研调用计划。

    Args:
        available_sources: 可用数据源列表
        selected_dimensions: 选定的调研维度列表
        keyword: 调研关键词
        geo: 地区代码
        dimensions_path: dimensions.yaml 文件路径

    Returns:
        {
            call_plan: [{source, dimension, action, params}],
            web_search_queries: [str],
            summary: {api_calls: int, web_searches: int, dimensions_covered: int}
        }
    """
    dim_config = load_dimensions(dimensions_path)
    if dim_config is None:
        return {"call_plan": [], "web_search_queries": [], "summary": {}}

    dimensions_map = dim_config.get("dimensions", dim_config)

    call_plan: List[Dict[str, Any]] = []
    web_search_dimensions: List[str] = []
    seen_sources: set = set()

    for dim_name in selected_dimensions:
        dim_def = dimensions_map.get(dim_name)
        if dim_def is None:
            print(f"[警告] 未知维度: {dim_name}，将使用Web搜索兜底")
            web_search_dimensions.append(dim_name)
            continue

        source = _resolve_source_for_dimension(dim_def, available_sources)
        if source is None or source == "web_search":
            web_search_dimensions.append(dim_name)
            continue

        # 构建调用条目
        action = dim_def.get("action", f"fetch_{dim_name}")
        params = {
            "keyword": keyword,
            "geo": geo,
        }
        # 合并维度特定参数
        extra_params = dim_def.get("params", {})
        if isinstance(extra_params, dict):
            params.update(extra_params)

        call_entry = {
            "source": source,
            "dimension": dim_name,
            "action": action,
            "params": params,
        }
        call_plan.append(call_entry)
        seen_sources.add(source)

    # 去重: 同一数据源的多个维度合并(保留各自的调用但记录去重)
    deduplicated_plan = _deduplicate_plan(call_plan)

    # 排序: API调用在前
    deduplicated_plan.sort(key=lambda x: (x["source"] == "web_search", x["source"]))

    # 生成Web搜索查询
    web_queries = _build_web_search_queries(
        keyword, geo, web_search_dimensions, dimensions_map
    )

    summary = {
        "api_calls": len(deduplicated_plan),
        "web_searches": len(web_queries),
        "dimensions_covered": len(selected_dimensions),
        "unique_sources": len(seen_sources),
    }

    return {
        "call_plan": deduplicated_plan,
        "web_search_queries": web_queries,
        "summary": summary,
    }


def _deduplicate_plan(plan: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """去除调用计划中完全重复的条目。

    Args:
        plan: 原始调用计划

    Returns:
        去重后的调用计划
    """
    seen = set()
    deduped = []
    for entry in plan:
        key = (entry["source"], entry["dimension"])
        if key not in seen:
            seen.add(key)
            deduped.append(entry)
    return deduped


def print_plan_summary(plan: Dict[str, Any], keyword: str, geo: str) -> None:
    """打印中文可读的调研执行计划。

    Args:
        plan: generate_call_plan 返回的计划字典
        keyword: 调研关键词
        geo: 地区代码
    """
    print("\n" + "=" * 60)
    print(f"  调研执行计划 - 关键词: {keyword} | 地区: {geo}")
    print("=" * 60)

    call_plan = plan.get("call_plan", [])
    web_queries = plan.get("web_search_queries", [])
    summary = plan.get("summary", {})

    if call_plan:
        print("\n  [API 调用计划]")
        for i, entry in enumerate(call_plan, 1):
            print(f"    {i}. [{entry['source']}] {entry['dimension']}")
            print(f"       动作: {entry['action']}")
            print(f"       参数: {json.dumps(entry['params'], ensure_ascii=False)}")
    else:
        print("\n  [无可用API调用]")

    if web_queries:
        print("\n  [Web搜索兜底查询]")
        for i, query in enumerate(web_queries, 1):
            print(f"    {i}. {query}")

    print("\n" + "-" * 60)
    print(f"  汇总: API调用 {summary.get('api_calls', 0)} 个 | "
          f"Web搜索 {summary.get('web_searches', 0)} 个 | "
          f"覆盖维度 {summary.get('dimensions_covered', 0)} 个 | "
          f"涉及数据源 {summary.get('unique_sources', 0)} 个")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="市场调研策略引擎")
    parser.add_argument("--config", type=str, help="config.yaml 文件路径")
    parser.add_argument("--dimensions-config", type=str, help="dimensions.yaml 文件路径")
    parser.add_argument("--keyword", type=str, default="智能手表", help="调研关键词")
    parser.add_argument("--geo", type=str, default="sg", help="地区代码")
    parser.add_argument(
        "--dims",
        type=str,
        nargs="*",
        default=["market_size", "competitors", "pricing", "user_reviews", "trends"],
        help="选定的调研维度",
    )
    args = parser.parse_args()

    # 确定配置文件路径
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.join(script_dir, "..")

    config_path = args.config or os.path.join(project_root, "config", "config.yaml")
    dim_path = args.dimensions_config or os.path.join(project_root, "config", "dimensions.yaml")

    # 获取可用数据源
    cl = _get_config_loader()
    available = cl.get_available_sources(config_path)
    print(f"可用数据源: {available}")

    # 生成调用计划
    plan = generate_call_plan(
        available_sources=available,
        selected_dimensions=args.dims,
        keyword=args.keyword,
        geo=args.geo,
        dimensions_path=dim_path,
    )

    # 输出
    print_plan_summary(plan, args.keyword, args.geo)
    print("JSON 调用计划:")
    print(json.dumps(plan, ensure_ascii=False, indent=2))

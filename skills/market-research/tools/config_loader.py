"""
配置加载器 - 读取并验证市场调研工具的API配置

功能:
- 读取 config/config.yaml 配置文件
- 检查各数据源的启用状态和凭证
- 对无需密钥的API(google_trends, google_play, app_store)直接标记为可用
- 对需要密钥的API检查凭证是否非空
- 输出JSON格式的状态报告和中文可读摘要
"""

import json
import os
import sys
from typing import Any, Dict, Optional

try:
    import yaml
except ImportError:
    print("[错误] 缺少 PyYAML 依赖，请运行: pip install pyyaml")
    yaml = None

# 无需API密钥即可使用的数据源
NO_KEY_SOURCES = {"google_trends", "google_play", "app_store", "reddit_public"}


def load_yaml(path: str) -> Optional[Dict[str, Any]]:
    """加载YAML配置文件。

    Args:
        path: YAML文件路径

    Returns:
        解析后的字典，失败返回None
    """
    if yaml is None:
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        print(f"[错误] 配置文件不存在: {path}")
        return None
    except yaml.YAMLError as e:
        print(f"[错误] YAML解析失败: {e}")
        return None


def _check_credentials(source_name: str, source_config: Dict[str, Any]) -> Dict[str, str]:
    """检查单个数据源的凭证状态。

    Args:
        source_name: 数据源名称
        source_config: 数据源配置字典

    Returns:
        包含 status 和 reason 的状态字典
    """
    enabled = source_config.get("enabled", False)
    if not enabled:
        return {"status": "unconfigured", "reason": "数据源未启用"}

    # 无需密钥的数据源
    if source_name in NO_KEY_SOURCES:
        return {"status": "available", "reason": "无需API密钥，可直接使用"}

    # 需要密钥的数据源 - 检查凭证字段
    credential_fields = _get_credential_fields(source_name)
    missing = []
    for field in credential_fields:
        value = source_config.get(field, "")
        if not value or str(value).strip() == "" or str(value).startswith("<"):
            missing.append(field)

    if missing:
        return {
            "status": "unconfigured",
            "reason": f"缺少凭证字段: {', '.join(missing)}",
        }

    return {"status": "available", "reason": "凭证已配置"}


def _get_credential_fields(source_name: str) -> list:
    """返回数据源需要的凭证字段名列表。

    Args:
        source_name: 数据源名称

    Returns:
        凭证字段名列表
    """
    field_map = {
        "reddit": ["client_id", "client_secret"],
        "producthunt": ["access_token"],
        "amazon": ["access_key", "secret_key", "partner_tag"],
        "amazon_paapi": ["access_key", "secret_key", "partner_tag"],
        "similarweb": ["api_key"],
        "crunchbase": ["api_key"],
        "statista": ["api_key"],
        "semrush": ["api_key"],
    }
    return field_map.get(source_name, ["api_key"])


def check_config(config_path: str) -> Dict[str, Dict[str, str]]:
    """检查配置文件中所有数据源的状态。

    Args:
        config_path: config.yaml 文件路径

    Returns:
        {source_name: {status: "available"|"unconfigured"|"auth_failed", reason: str}}
    """
    config = load_yaml(config_path)
    if config is None:
        return {}

    # 兼容多种配置文件格式：apis / sources / api_sources
    sources = config.get("apis", config.get("sources", config.get("api_sources", {})))
    if not isinstance(sources, dict):
        print("[错误] 配置文件中未找到有效的 apis / sources / api_sources 字段")
        return {}

    report: Dict[str, Dict[str, str]] = {}
    for source_name, source_config in sources.items():
        if not isinstance(source_config, dict):
            report[source_name] = {"status": "unconfigured", "reason": "配置格式无效"}
            continue
        report[source_name] = _check_credentials(source_name, source_config)

    return report


def print_status_summary(report: Dict[str, Dict[str, str]]) -> None:
    """打印中文可读状态摘要。

    Args:
        report: check_config 返回的状态报告
    """
    status_icons = {
        "available": "✅",
        "unconfigured": "⚠️",
        "auth_failed": "❌",
    }

    print("\n" + "=" * 50)
    print("  数据源配置状态检查报告")
    print("=" * 50)

    available_count = 0
    total_count = len(report)

    for source_name, info in report.items():
        status = info["status"]
        icon = status_icons.get(status, "❓")
        reason = info["reason"]
        print(f"  {icon} {source_name:20s} | {status:14s} | {reason}")
        if status == "available":
            available_count += 1

    print("-" * 50)
    print(f"  可用: {available_count}/{total_count} 个数据源")
    print("=" * 50 + "\n")


def get_available_sources(config_path: str) -> list:
    """返回可用数据源的名称列表。

    Args:
        config_path: config.yaml 文件路径

    Returns:
        可用数据源名称列表
    """
    report = check_config(config_path)
    return [name for name, info in report.items() if info["status"] == "available"]


if __name__ == "__main__":
    # 支持命令行指定配置文件路径
    if len(sys.argv) > 1:
        cfg_path = sys.argv[1]
    else:
        # 默认相对于项目根目录
        script_dir = os.path.dirname(os.path.abspath(__file__))
        cfg_path = os.path.join(script_dir, "..", "config", "config.yaml")

    report = check_config(cfg_path)
    if report:
        print_status_summary(report)
        print("JSON 状态报告:")
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("[错误] 无法生成状态报告，请检查配置文件路径")

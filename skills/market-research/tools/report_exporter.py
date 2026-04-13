"""
报告导出器 - 将 Markdown 报告转换为 HTML 网页和 PDF

功能:
- 读取 Markdown 报告文件
- 使用 Python markdown 库转换为 HTML 片段
- 注入到 HTML 模板中（含内嵌 CSS 样式）
- 输出自包含的 .html 文件
- 使用系统浏览器（Edge/Chrome）headless 模式自动导出 PDF

用法:
  python report_exporter.py <markdown_file> [--output <output_dir>] [--no-pdf]

示例:
  python report_exporter.py report.md                    # 输出 .html + .pdf
  python report_exporter.py report.md --no-pdf           # 仅输出 .html
  python report_exporter.py report.md -o /path/to/dir    # 指定输出目录
"""

import argparse
import os
import platform
import re
import shutil
import subprocess
import sys
import time
from datetime import date

try:
    import markdown
except ImportError:
    print("[错误] 缺少 markdown 依赖，请运行: pip install markdown")
    sys.exit(1)


def find_template() -> str:
    """定位 HTML 模板文件。

    Returns:
        模板文件的绝对路径
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    template_path = os.path.join(script_dir, "..", "templates", "report_template.html")
    template_path = os.path.normpath(template_path)

    if not os.path.exists(template_path):
        print(f"[错误] HTML 模板文件不存在: {template_path}")
        sys.exit(1)

    return template_path


def read_file(path: str, encoding: str = "utf-8") -> str:
    """读取文件内容。"""
    with open(path, "r", encoding=encoding) as f:
        return f.read()


def extract_title(md_text: str) -> str:
    """从 Markdown 内容中提取标题（第一个 # 标题）。

    Args:
        md_text: Markdown 原文

    Returns:
        标题文本，未找到则返回默认值
    """
    match = re.search(r"^#\s+(.+)$", md_text, re.MULTILINE)
    if match:
        return match.group(1).strip()
    return "市场调研报告"


def extract_date(md_text: str) -> str:
    """从 Markdown 内容中提取日期。

    优先从 metadata 行（> 生成日期：...）提取，否则返回今天日期。

    Args:
        md_text: Markdown 原文

    Returns:
        日期字符串
    """
    match = re.search(r"生成日期[：:]\s*(\d{4}-\d{2}-\d{2})", md_text)
    if match:
        return match.group(1)
    return date.today().isoformat()


def preprocess_md(md_text: str) -> str:
    """预处理 Markdown 文本，修复常见的解析问题。

    Python markdown 库要求表格前必须有空行，否则无法识别为表格。
    本函数确保每个表格（以 | 开头的行块）前面都有空行。

    Args:
        md_text: 原始 Markdown 文本

    Returns:
        预处理后的 Markdown 文本
    """
    lines = md_text.split("\n")
    result = []
    for i, line in enumerate(lines):
        # 当前行是表格行（以 | 开头），但上一行不是空行也不是表格行
        if (
            i > 0
            and line.startswith("|")
            and result
            and result[-1].strip() != ""
            and not result[-1].startswith("|")
        ):
            result.append("")  # 插入空行
        result.append(line)
    return "\n".join(result)


def md_to_html(md_text: str) -> str:
    """将 Markdown 文本转换为 HTML 片段。

    Args:
        md_text: Markdown 原文

    Returns:
        HTML 片段字符串
    """
    # 预处理：修复表格前缺少空行等问题
    md_text = preprocess_md(md_text)

    extensions = [
        "tables",
        "fenced_code",
        "codehilite",
        "toc",
        "sane_lists",
    ]
    extension_configs = {
        "codehilite": {"css_class": "highlight", "guess_lang": False},
        "toc": {"permalink": False},
    }
    html = markdown.markdown(
        md_text,
        extensions=extensions,
        extension_configs=extension_configs,
    )
    return html


def inject_into_template(template: str, content_html: str, title: str, report_date: str) -> str:
    """将 HTML 内容注入到模板中。

    Args:
        template: HTML 模板字符串
        content_html: 转换后的 HTML 正文
        title: 报告标题
        report_date: 报告日期

    Returns:
        完整的 HTML 页面字符串
    """
    result = template.replace("{{content}}", content_html)
    result = result.replace("{{title}}", title)
    result = result.replace("{{date}}", report_date)
    return result


def _find_browser() -> str:
    """查找系统中可用的浏览器（用于 headless PDF 导出）。

    按优先级尝试：Edge → Chrome → Chromium。

    Returns:
        浏览器可执行文件路径，未找到返回空字符串
    """
    system = platform.system()

    if system == "Windows":
        candidates = [
            # Edge (Windows 11 自带)
            os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
            os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
            # Chrome
            os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
        ]
    elif system == "Darwin":  # macOS
        candidates = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
            "/Applications/Chromium.app/Contents/MacOS/Chromium",
        ]
    else:  # Linux
        candidates = []
        for name in ["google-chrome", "google-chrome-stable", "chromium-browser", "chromium", "microsoft-edge"]:
            path = shutil.which(name)
            if path:
                candidates.append(path)

    for path in candidates:
        if os.path.isfile(path):
            return path

    return ""


def export_pdf(html_path: str, pdf_path: str = None) -> str:
    """使用系统浏览器 headless 模式将 HTML 转为 PDF。

    Args:
        html_path: HTML 文件的绝对路径
        pdf_path: 输出 PDF 文件路径（可选，默认同名 .pdf）

    Returns:
        PDF 文件的绝对路径，失败返回空字符串
    """
    if pdf_path is None:
        base, _ = os.path.splitext(html_path)
        pdf_path = base + ".pdf"

    browser = _find_browser()
    if not browser:
        print("[警告] 未找到 Edge/Chrome/Chromium，无法自动生成 PDF")
        print("[提示] 请手动在浏览器中打开 HTML 文件，按 Ctrl+P 打印为 PDF")
        return ""

    browser_name = os.path.basename(browser).lower()
    print(f"[PDF] 使用 {browser_name} headless 模式导出...")

    # 构建 file:// URL
    file_url = "file:///" + html_path.replace("\\", "/").replace(" ", "%20")

    # headless 打印命令
    cmd = [
        browser,
        "--headless",
        "--disable-gpu",
        "--no-sandbox",
        "--run-all-compositor-stages-before-draw",
        "--disable-extensions",
        f"--print-to-pdf={pdf_path}",
        "--print-to-pdf-no-header",
        file_url,
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
            encoding="utf-8",
            errors="replace",
        )
        # 等待文件写入完成
        for _ in range(10):
            if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 0:
                break
            time.sleep(0.5)

        if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 0:
            abs_pdf = os.path.abspath(pdf_path)
            size_kb = os.path.getsize(pdf_path) / 1024
            print(f"[成功] PDF 报告已生成: {abs_pdf} ({size_kb:.0f} KB)")
            return abs_pdf
        else:
            print(f"[警告] PDF 生成可能失败，请检查文件: {pdf_path}")
            if result.stderr:
                print(f"[调试] {result.stderr[:200]}")
            return ""

    except subprocess.TimeoutExpired:
        print("[警告] PDF 导出超时（60秒），请手动在浏览器中打印")
        return ""
    except Exception as e:
        print(f"[警告] PDF 导出失败: {e}")
        return ""


def export_html(md_path: str, output_path: str = None) -> str:
    """MD → HTML 导出。

    Args:
        md_path: Markdown 文件路径
        output_path: 输出 HTML 文件路径（可选，默认同名 .html）

    Returns:
        输出文件的绝对路径
    """
    if not os.path.exists(md_path):
        print(f"[错误] Markdown 文件不存在: {md_path}")
        sys.exit(1)

    # 确定输出路径
    if output_path is None:
        base, _ = os.path.splitext(md_path)
        output_path = base + ".html"

    # 读取源文件和模板
    md_text = read_file(md_path)
    template = read_file(find_template())

    # 提取元数据
    title = extract_title(md_text)
    report_date = extract_date(md_text)

    # 转换
    content_html = md_to_html(md_text)

    # 注入模板
    full_html = inject_into_template(template, content_html, title, report_date)

    # 写入输出
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(full_html)

    abs_path = os.path.abspath(output_path)
    print(f"[成功] HTML 报告已生成: {abs_path}")

    return abs_path


def export_all(md_path: str, output_dir: str = None, skip_pdf: bool = False):
    """完整导出流程：MD → HTML → PDF。

    Args:
        md_path: Markdown 文件路径
        output_dir: 输出目录（可选，默认与 MD 文件同目录）
        skip_pdf: 是否跳过 PDF 生成
    """
    md_path = os.path.abspath(md_path)
    base_name = os.path.splitext(os.path.basename(md_path))[0]

    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        html_path = os.path.join(output_dir, base_name + ".html")
        pdf_path = os.path.join(output_dir, base_name + ".pdf")
    else:
        html_path = None  # export_html 会自动用同名 .html
        pdf_path = None

    # 1. MD → HTML
    html_abs = export_html(md_path, html_path)

    # 2. HTML → PDF
    pdf_abs = ""
    if not skip_pdf:
        pdf_abs = export_pdf(html_abs, pdf_path)

    # 3. 输出汇总
    print("\n" + "=" * 50)
    print("  导出完成")
    print("=" * 50)
    print(f"  📄 Markdown: {md_path}")
    print(f"  🌐 HTML:     {html_abs}")
    if pdf_abs:
        print(f"  📑 PDF:      {pdf_abs}")
    else:
        print(f"  📑 PDF:      （未生成，可在浏览器中打开 HTML 后 Ctrl+P 打印）")
    print("=" * 50)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="市场调研报告导出器 (MD → HTML + PDF)")
    parser.add_argument("markdown_file", help="输入的 Markdown 报告文件路径")
    parser.add_argument("--output", "-o", help="输出目录（默认与 MD 文件同目录）")
    parser.add_argument("--no-pdf", action="store_true", help="跳过 PDF 生成，仅输出 HTML")
    args = parser.parse_args()

    export_all(args.markdown_file, args.output, args.no_pdf)

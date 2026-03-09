"""本机磁盘空间分布工具 - 计算剩余空间、系统/用户文件分布，返回数字、表格、图表"""
import os
import platform
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional

from backend.core.agent.tools.base import Tool, ToolResult, ToolParameter


def _get_dir_size_kb(path: str, timeout: int = 8, use_x: bool = False) -> Optional[int]:
    """获取目录大小（KB），失败返回 None。use_x=True 时加 -x 仅统计当前文件系统（可加速）。"""
    if not os.path.exists(path) or not os.path.isdir(path):
        return None
    try:
        cmd = ["du", "-sk"]
        if use_x:
            cmd.append("-x")
        cmd.append(path)
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode == 0 and result.stdout.strip():
            parts = result.stdout.strip().split("\t")
            if parts:
                return int(parts[0])
    except (subprocess.TimeoutExpired, ValueError, OSError):
        pass
    return None


def _enumerate_scan_candidates() -> List[tuple]:
    """枚举需要扫描的目录路径 (path, category)，用于详细占用分析"""
    home = os.path.expanduser("~")
    is_macos = platform.system() == "Darwin"
    candidates = []

    def add(p: str, cat: str) -> None:
        if os.path.exists(p) and os.path.isdir(p):
            candidates.append((p, cat))

    # 系统顶层
    add("/Applications", "应用程序")
    add("/Library", "系统库")
    add("/System", "系统文件")
    add("/Users", "用户")
    add("/usr", "系统程序")
    add("/usr/local", "本地程序")
    add("/var", "可变数据")
    add("/tmp", "临时文件")

    if is_macos:
        # /Applications 下每个应用
        try:
            for name in os.listdir("/Applications"):
                p = f"/Applications/{name}"
                if os.path.isdir(p) and not name.startswith("."):
                    candidates.append((p, "应用"))
        except OSError:
            pass
        # /Library 下子目录
        try:
            for name in os.listdir("/Library"):
                p = f"/Library/{name}"
                if os.path.isdir(p) and not name.startswith("."):
                    candidates.append((p, "系统库子目录"))
        except OSError:
            pass
        # /usr/local 下（Homebrew 等）
        try:
            for name in os.listdir("/usr/local"):
                p = f"/usr/local/{name}"
                if os.path.isdir(p) and not name.startswith("."):
                    candidates.append((p, "本地"))
        except OSError:
            pass
        # 用户主目录直接子目录
        for name in ["Desktop", "Documents", "Downloads", "Library", "Movies", "Music", "Pictures"]:
            add(f"{home}/{name}", "用户目录")
        # ~/Library 子目录
        for name in ["Application Support", "Caches", "Logs", "Developer", "Containers"]:
            add(f"{home}/Library/{name}", "用户库")
        # ~/Library/Application Support 下每个应用
        app_support = f"{home}/Library/Application Support"
        if os.path.isdir(app_support):
            try:
                for name in os.listdir(app_support):
                    p = f"{app_support}/{name}"
                    if os.path.isdir(p) and not name.startswith("."):
                        candidates.append((p, "应用数据"))
            except OSError:
                pass
        # ~/Library/Developer 子目录
        dev_dir = f"{home}/Library/Developer"
        if os.path.isdir(dev_dir):
            try:
                for name in os.listdir(dev_dir):
                    p = f"{dev_dir}/{name}"
                    if os.path.isdir(p) and not name.startswith("."):
                        candidates.append((p, "开发工具"))
            except OSError:
                pass
        # ~/Library/Caches 子目录
        caches_dir = f"{home}/Library/Caches"
        if os.path.isdir(caches_dir):
            try:
                for name in os.listdir(caches_dir):
                    p = f"{caches_dir}/{name}"
                    if os.path.isdir(p) and not name.startswith("."):
                        candidates.append((p, "缓存"))
            except OSError:
                pass
    else:
        # Linux
        add("/home", "用户")
        try:
            for name in os.listdir("/usr/local"):
                p = f"/usr/local/{name}"
                if os.path.isdir(p) and not name.startswith("."):
                    candidates.append((p, "本地"))
        except OSError:
            pass
        for name in ["Desktop", "Documents", "Downloads", ".local", ".cache"]:
            add(f"{home}/{name}", "用户目录")

    return candidates


def _filter_parent_paths(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """剔除父路径：若某路径是另一路径的父目录，则剔除父路径，避免重复统计"""
    paths = [x["path"] for x in items]

    def is_parent_of(parent: str, child: str) -> bool:
        if parent == child:
            return False
        prefix = parent.rstrip("/") + "/"
        return child.startswith(prefix)

    def should_keep(p: str) -> bool:
        for other in paths:
            if is_parent_of(p, other):
                return False  # p 是 other 的父，剔除 p
        return True

    return [x for x in items if should_keep(x["path"])]


def _collect_large_directories(total_gb: float, min_gb: float = 1.0) -> List[Dict[str, Any]]:
    """扫描所有候选目录，返回 >= min_gb 的详细清单，按大小降序。剔除父路径避免重复统计。"""
    candidates = _enumerate_scan_candidates()
    results = []

    def _run_du(full_path: str, category: str) -> Optional[Dict[str, Any]]:
        kb = _get_dir_size_kb(full_path, timeout=12)
        if kb is None or kb <= 0:
            return None
        size_gb = kb * 1024 / (1024 ** 3)
        if size_gb < min_gb:
            return None
        return {
            "path": full_path,
            "category": category,
            "size_gb": round(size_gb, 2),
        }

    with ThreadPoolExecutor(max_workers=10) as ex:
        futures = {}
        for full_path, category in candidates:
            futures[ex.submit(_run_du, full_path, category)] = (full_path, category)
        for fut in as_completed(futures, timeout=90):
            try:
                r = fut.result()
                if r:
                    results.append(r)
            except Exception:
                pass

    results = _filter_parent_paths(results)
    _add_pct_to_items(results, total_gb)
    return sorted(results, key=lambda x: -x["size_gb"])


def _collect_directory_breakdown(root_path: str) -> List[Dict[str, Any]]:
    """收集顶层目录大小分布（互斥，合计≈已用空间）。/System、/Users 等大目录需较长超时。"""
    if root_path not in ("/", ""):
        return []
    is_macos = platform.system() == "Darwin"
    if is_macos:
        candidates = [
            ("/tmp", "临时文件", 10),
            ("/var", "可变数据", 20),
            ("/usr", "系统程序", 90),
            ("/Library", "系统库", 45),
            ("/Applications", "应用程序", 20),
            ("/System", "系统文件", 120),
            ("/Users", "用户文件", 120),
        ]
    else:
        candidates = [
            ("/tmp", "临时文件", 8),
            ("/etc", "配置文件", 8),
            ("/opt", "可选软件", 15),
            ("/var", "可变数据", 15),
            ("/usr", "系统程序", 45),
            ("/home", "用户文件", 60),
        ]

    def _run(p: str, n: str, full: str, to: int) -> Optional[tuple]:
        kb = _get_dir_size_kb(full, timeout=to)
        if kb is not None and kb > 0:
            return (p, n, kb * 1024 / (1024 ** 3))
        return None

    results = []
    tasks = []
    for p, n, t in candidates:
        full = p if p.startswith("/") else os.path.join(root_path or "/", p)
        if os.path.exists(full):
            tasks.append((p, n, full, t))
    with ThreadPoolExecutor(max_workers=7) as ex:
        futures = {ex.submit(_run, p, n, f, t): (p, n) for p, n, f, t in tasks}
        for fut in as_completed(futures, timeout=180):
            try:
                r = fut.result()
                if r:
                    results.append(r)
            except Exception:
                pass

    return [
        {"path": p, "category": name, "size_gb": round(sz, 2)}
        for p, name, sz in sorted(results, key=lambda x: -x[2])
    ]


def _enumerate_system_data_candidates() -> List[tuple]:
    """枚举「系统数据」相关路径 (path, category, timeout_sec)，用于细分 500G+ 系统数据"""
    is_macos = platform.system() == "Darwin"
    # (path, category, timeout)
    if is_macos:
        return [
            # 顶层（互斥）
            ("/System", "系统文件", 120),
            ("/usr", "系统程序", 90),
            ("/Library", "系统库", 60),
            ("/var", "可变数据", 45),
            ("/tmp", "临时文件", 15),
            ("/private", "私有目录", 45),
            # 子目录（会剔除父路径）
            ("/System/Library", "系统框架库", 90),
            ("/System/Volumes/Preboot", "预启动卷", 30),
            ("/System/Volumes/VM", "虚拟机交换", 20),
            ("/System/Volumes/Update", "系统更新", 20),
            ("/usr/local", "本地程序", 30),
            ("/usr/lib", "系统库", 45),
            ("/Library/Caches", "系统缓存", 30),
            ("/Library/Logs", "系统日志", 20),
            ("/Library/Developer", "系统开发", 30),
            ("/Library/Application Support", "系统应用支持", 45),
            ("/var/log", "系统日志", 20),
            ("/var/db", "系统数据库", 30),
            ("/var/vm", "虚拟机", 15),
        ]
    else:
        return [
            ("/usr", "系统程序", 60),
            ("/var", "可变数据", 30),
            ("/tmp", "临时文件", 10),
            ("/opt", "可选软件", 20),
            ("/usr/local", "本地程序", 30),
            ("/var/log", "系统日志", 15),
            ("/var/cache", "系统缓存", 20),
        ]


def _collect_system_data_breakdown(total_gb: float) -> List[Dict[str, Any]]:
    """扫描「系统数据」各组件，返回细分清单。剔除父路径避免重复。"""
    candidates = _enumerate_system_data_candidates()
    results = []

    def _run(path: str, category: str, timeout_sec: int) -> Optional[Dict[str, Any]]:
        if not os.path.exists(path) or not os.path.isdir(path):
            return None
        # 顶层路径用 -x 加速，避免跨卷遍历
        use_x = path in ("/System", "/usr", "/Library", "/var", "/tmp", "/private")
        kb = _get_dir_size_kb(path, timeout=timeout_sec, use_x=use_x)
        if kb is None or kb <= 0:
            return None
        size_gb = round(kb * 1024 / (1024 ** 3), 2)
        return {"path": path, "category": category, "size_gb": size_gb}

    with ThreadPoolExecutor(max_workers=8) as ex:
        futures = {
            ex.submit(_run, p, c, t): (p, c)
            for p, c, t in candidates
        }
        for fut in as_completed(futures, timeout=240):
            try:
                r = fut.result()
                if r:
                    results.append(r)
            except Exception:
                pass

    results = _filter_parent_paths(results)
    _add_pct_to_items(results, total_gb)
    return sorted(results, key=lambda x: -x["size_gb"])


def _add_pct_to_items(items: List[Dict[str, Any]], total_gb: float) -> None:
    """为每个 item 添加 pct_of_total"""
    if total_gb <= 0:
        return
    for x in items:
        x["pct_of_total"] = round(100 * x["size_gb"] / total_gb, 1)


def _build_ascii_chart(items: List[Dict[str, Any]], max_width: int = 40) -> str:
    """构建 ASCII 条形图"""
    if not items:
        return ""
    max_gb = max(x["size_gb"] for x in items)
    if max_gb <= 0:
        return ""
    lines = []
    for x in items:
        gb = x["size_gb"]
        pct = (gb / max_gb) * 100 if max_gb > 0 else 0
        bar_len = int(max_width * gb / max_gb) if max_gb > 0 else 0
        bar = "█" * bar_len + "░" * (max_width - bar_len)
        lines.append(f"  {x['path']:12} {bar} {gb:.1f} GB ({pct:.0f}%)")
    return "\n".join(lines)


def _build_markdown_table(items: List[Dict[str, Any]], title: str) -> str:
    """构建 Markdown 表格"""
    if not items:
        return ""
    lines = [f"\n### {title}\n", "| 路径 | 分类 | 大小 (GB) |", "|------|------|----------|"]
    for x in items:
        lines.append(f"| {x['path']} | {x['category']} | {x['size_gb']} |")
    return "\n".join(lines)


def _collect_cleanup_targets() -> List[Dict[str, Any]]:
    """收集可人工清理的目录（缓存、日志、临时文件等），便于给出清理建议"""
    home = os.path.expanduser("~")
    is_macos = platform.system() == "Darwin"

    # (路径, 分类, 清理建议)
    if is_macos:
        targets = [
            (f"{home}/Library/Caches", "用户缓存", "可清理，应用会重建"),
            (f"{home}/Library/Logs", "用户日志", "可清理，仅影响历史日志"),
            (f"{home}/.cache", "通用缓存", "可清理"),
            (f"{home}/.npm", "npm 缓存", "可清理，npm 会重建"),
            (f"{home}/Library/Caches/pip", "pip 缓存", "可清理"),
            (f"{home}/Library/Caches/Homebrew", "Homebrew 缓存", "brew cleanup 可清理"),
            ("/tmp", "系统临时", "可清理，重启后自动清空"),
            ("/var/log", "系统日志", "需 sudo，谨慎清理"),
            (f"{home}/Downloads", "下载目录", "可手动整理大文件"),
            (f"{home}/Library/Developer/Xcode/DerivedData", "Xcode 构建", "可清理，重建会慢"),
            (f"{home}/Library/Developer/Xcode/Archives", "Xcode 归档", "可删除旧归档"),
            (f"{home}/.Trash", "废纸篓", "可清空"),
        ]
    else:
        targets = [
            (f"{home}/.cache", "用户缓存", "可清理"),
            (f"{home}/.npm", "npm 缓存", "可清理"),
            (f"{home}/.local/share/Trash", "回收站", "可清空"),
            ("/tmp", "系统临时", "可清理"),
            ("/var/log", "系统日志", "需 sudo，谨慎清理"),
            (f"{home}/Downloads", "下载目录", "可手动整理大文件"),
        ]

    results = []
    for path, name, tip in targets:
        if not os.path.exists(path):
            continue
        try:
            kb = _get_dir_size_kb(path, timeout=5)
        except Exception:
            kb = None
        if kb is not None and kb > 0:
            size_gb = round(kb * 1024 / (1024 ** 3), 2)
            if size_gb >= 0.01:  # 至少 10MB 才显示
                results.append({"path": path, "category": name, "size_gb": size_gb, "suggestion": tip})

    return sorted(results, key=lambda x: -x["size_gb"])


def _build_cleanup_suggestions(items: List[Dict[str, Any]]) -> str:
    """构建人工清理建议"""
    if not items:
        return ""
    lines = [
        "\n### 人工清理建议",
        "以下目录通常可安全清理或整理，按占用排序：",
        "",
        "| 路径 | 分类 | 大小 (GB) | 建议 |",
        "|------|------|----------|------|",
    ]
    for x in items:
        lines.append(f"| `{x['path']}` | {x['category']} | {x['size_gb']} | {x['suggestion']} |")
    lines.append("")
    lines.append("**注意**：清理前请确认无重要数据，系统目录需谨慎。")
    return "\n".join(lines)


class DiskUsageTool(Tool):
    """
    本机磁盘空间分布工具 - 类似天气预报，返回剩余空间、系统/用户文件分布。
    输出包含数字、表格、ASCII 图表。
    """

    def __init__(self):
        super().__init__(
            name="disk_usage",
            description=(
                "获取本机磁盘空间分布：剩余空间、系统/用户文件占用、可清理目录。"
                "返回数字汇总、Markdown 表格、ASCII 条形图、人工清理建议。"
                "适用于：查看磁盘占用、排查空间不足、获取清理建议。"
            ),
            parameters=[
                ToolParameter(
                    name="path",
                    type="string",
                    description="要分析的根路径，默认 /（根目录）",
                    required=False,
                    default="/",
                ),
            ],
        )

    def execute(self, **kwargs) -> ToolResult:
        path = (kwargs.get("path") or "/").strip() or "/"
        if not os.path.exists(path):
            return ToolResult(success=False, error=f"路径不存在: {path}")

        try:
            total, used, free = shutil.disk_usage(path)
            total_gb = total / (1024 ** 3)
            used_gb = used / (1024 ** 3)
            free_gb = free / (1024 ** 3)
            used_pct = (used / total * 100) if total > 0 else 0

            summary = {
                "total_gb": round(total_gb, 2),
                "used_gb": round(used_gb, 2),
                "free_gb": round(free_gb, 2),
                "used_percent": round(used_pct, 1),
            }

            large_dirs = _collect_large_directories(total_gb, min_gb=1.0)
            system_data_breakdown = _collect_system_data_breakdown(total_gb)
            cleanup_targets = _collect_cleanup_targets()

            _add_pct_to_items(cleanup_targets, total_gb)
            reclaimable_gb = round(sum(c["size_gb"] for c in cleanup_targets), 2)

            # 已列出 ≥1GB 目录合计（互斥，已剔除父路径）
            large_dirs_sum = round(sum(d["size_gb"] for d in large_dirs), 2)
            other_gb = round(max(0, used_gb - large_dirs_sum), 2)
            # 构建「合计≈已用」的 breakdown：large_dirs + 其他
            breakdown = [
                {"path": d["path"], "category": d["category"], "size_gb": d["size_gb"]}
                for d in large_dirs
            ]
            if other_gb > 0:
                breakdown.append({
                    "path": "其他（/System、/usr、<1GB 目录等）",
                    "category": "未统计",
                    "size_gb": other_gb,
                })
            _add_pct_to_items(breakdown, total_gb)
            breakdown.sort(key=lambda x: -x["size_gb"])  # 其他通常最大，排第一

            table_md = _build_markdown_table(breakdown, "空间占用分布") if breakdown else ""
            system_data_md = _build_markdown_table(system_data_breakdown, "系统数据细分") if system_data_breakdown else ""
            large_table_md = _build_markdown_table(large_dirs, "≥1GB 目录清单") if large_dirs else ""
            chart_ascii = _build_ascii_chart(breakdown) if breakdown else ""
            cleanup_md = _build_cleanup_suggestions(cleanup_targets) if cleanup_targets else ""

            numbers_text = (
                f"**磁盘空间汇总** ({path})\n"
                f"- 总容量: {summary['total_gb']} GB\n"
                f"- 已使用: {summary['used_gb']} GB ({summary['used_percent']}%)\n"
                f"- 剩余: {summary['free_gb']} GB\n"
            )

            report_parts = [numbers_text]
            if system_data_md:
                report_parts.append(system_data_md)
            if large_table_md:
                report_parts.append(large_table_md)
            if table_md:
                report_parts.append(table_md)
            if chart_ascii:
                report_parts.append("\n### 空间分布图\n```\n" + chart_ascii + "\n```")
            if cleanup_md:
                report_parts.append(cleanup_md)

            system_data_sum = round(sum(d["size_gb"] for d in system_data_breakdown), 2)

            result_data = {
                "path": path,
                "summary": {
                    **summary,
                    "reclaimable_gb": reclaimable_gb,
                    "large_dirs_sum_gb": large_dirs_sum,
                    "other_gb": other_gb,
                    "system_data_sum_gb": system_data_sum,
                },
                "numbers": numbers_text,
                "directory_breakdown": breakdown,
                "system_data_breakdown": system_data_breakdown,
                "large_directories": large_dirs,
                "cleanup_suggestions": cleanup_targets,
                "reclaimable_gb": reclaimable_gb,
                "table_markdown": table_md,
                "chart_ascii": chart_ascii,
                "cleanup_markdown": cleanup_md,
                "report": "\n".join(report_parts),
            }
            return ToolResult(success=True, data=result_data)
        except Exception as e:
            return ToolResult(success=False, error=str(e))

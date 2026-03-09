#!/usr/bin/env python3
"""
系统数据细分脚本 - 需 sudo 执行，定位 macOS 储存空间里约 500GB「系统数据」的来源。

策略：从 / 开始，逐层 find -maxdepth 1 拆子目录 + 并行 du。
超时目录自动递归拆分，直到能统计到每个子目录，消除「其他」。

用法:
  sudo python3 scripts/disk_system_data_breakdown.py
  sudo python3 scripts/disk_system_data_breakdown.py -o report.txt   # 输出到文件
  python3 scripts/disk_system_data_breakdown.py --json --user-only   # JSON 输出，供 API 调用
"""
import argparse
import json
import os
import platform
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# 确保能导入 backend
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

MAX_SPLIT_DEPTH = 5
DU_TIMEOUT_PER_LEVEL = 180


def list_immediate_subdirs(parent: str) -> list[str]:
    """列出 parent 下直接子目录（不含 . 开头，不含 parent 自身）"""
    if not os.path.isdir(parent):
        return []
    try:
        result = subprocess.run(
            ["find", parent, "-maxdepth", "1", "-type", "d"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            return []
        lines = [p.strip() for p in result.stdout.strip().split("\n") if p.strip()]
        return [p for p in lines if p != parent and not os.path.basename(p).startswith(".")]
    except Exception:
        return []


def get_total_used_gb() -> float:
    """获取数据卷已用空间（GB）。macOS APFS 下 df / 只显示系统卷(~16G)，需用 /System/Volumes/Data。"""
    for path in ["/System/Volumes/Data", "/Users", "/"]:
        try:
            r = subprocess.run(["df", "-k", path], capture_output=True, text=True, timeout=5)
            if r.returncode == 0 and r.stdout:
                lines = r.stdout.strip().split("\n")
                if len(lines) >= 2:
                    parts = lines[1].split()
                    if len(parts) >= 3:
                        return round(int(parts[2]) * 1024 / (1024**3), 2)
        except Exception:
            pass
    return 0


def get_dir_size_kb(path: str, timeout: int = 120, use_x: bool = True) -> int | None:
    """获取目录大小（KB），失败返回 None。use_x=False 时跨卷统计（数据卷路径用）。"""
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
    except (subprocess.TimeoutExpired, ValueError, OSError) as e:
        print(f"  [超时] {path}: {e}", file=sys.stderr)
    return None


def split_and_du(
    path: str,
    category: str,
    results: list,
    depth: int = 0,
    use_x: bool = False,
    verbose: bool = True,
) -> None:
    """
    尝试 du 目录；若超时则拆成子目录递归处理。
    results 会被原地追加 (path, category, size_gb)。
    """
    if depth >= MAX_SPLIT_DEPTH:
        print(f"  [已达最大深度] {path}", file=sys.stderr)
        return
    timeout = DU_TIMEOUT_PER_LEVEL
    kb = get_dir_size_kb(path, timeout=timeout, use_x=use_x)
    if kb is not None and kb > 0:
        size_gb = round(kb * 1024 / (1024**3), 2)
        results.append((path, category, size_gb))
        if verbose:
            print(f"  {path}: {size_gb} GB")
        return
    # 超时或失败，拆子目录
    subdirs = list_immediate_subdirs(path)
    if not subdirs:
        return
    for sub in subdirs:
        name = os.path.basename(sub)
        sub_cat = f"{category}/{name}" if category else name
        split_and_du(sub, sub_cat, results, depth + 1, use_x, verbose)


def run_scan(user_only: bool = False, verbose: bool = True) -> dict:
    """
    执行磁盘扫描，返回结构化数据。
    verbose=False 时不打印，供 API 调用。
    """
    if platform.system() != "Darwin":
        raise RuntimeError("当前仅支持 macOS")

    total_used = get_total_used_gb()
    is_root = os.geteuid() == 0

    # 非 root 时自动仅扫描用户主目录
    if not is_root:
        user_only = True

    results: list[tuple[str, str, float]] = []

    def is_parent_of(parent: str, child: str) -> bool:
        if parent == child:
            return False
        return child.startswith(parent.rstrip("/") + "/")

    # user_only 或非 root：仅扫描用户主目录
    if user_only:
        home = os.path.expanduser("~")
        if not home or not os.path.isdir(home):
            raise RuntimeError("无法获取用户主目录")
        if verbose:
            print(f"根分区已用: {total_used} GB (df 统计)")
            print(f"模式: 仅扫描用户主目录 {home}\n")
        split_and_du(home, "~", results, use_x=False, verbose=verbose)
    else:
        if verbose:
            print(f"根分区已用: {total_used} GB (df 统计)\n")

    # root 且非 user_only：从数据卷根扫描
    if is_root and not user_only:
        data_root = "/System/Volumes/Data"
        if os.path.isdir(data_root):
            if verbose:
                print("阶段 0: 从数据卷根 /System/Volumes/Data 拆分...")
            subdirs = list_immediate_subdirs(data_root)
            skip = {".", "..", ".Spotlight-V100", ".fseventsd", "System", "Volumes"}
            subdirs = [p for p in subdirs if os.path.basename(p) not in skip]
            if verbose:
                print(f"  子目录: {', '.join(os.path.basename(p) for p in subdirs)}")

            def process_one(item: tuple[str, str]) -> list[tuple[str, str, float]]:
                path, cat = item
                out: list[tuple[str, str, float]] = []
                split_and_du(path, cat, out, depth=0, use_x=False, verbose=False)
                return out

            tasks = [(p, f"Data/{os.path.basename(p)}") for p in subdirs]
            with ThreadPoolExecutor(max_workers=6) as ex:
                futures = {ex.submit(process_one, t): t for t in tasks}
                for fut in as_completed(futures, timeout=3600):
                    try:
                        for r in fut.result():
                            results.append(r)
                            if verbose:
                                print(f"  {r[0]}: {r[2]} GB")
                    except Exception as e:
                        if verbose:
                            print(f"  [失败] {futures[fut]}: {e}", file=sys.stderr)
        else:
            if verbose:
                print("阶段 0: 从 / 顶层分析...")
            top_dirs = list_immediate_subdirs("/")
            skip = {".", "..", ".Spotlight-V100", ".fseventsd"}
            top_dirs = [p for p in top_dirs if os.path.basename(p) not in skip]
            for path in top_dirs:
                split_and_du(path, f"顶层/{os.path.basename(path)}", results, use_x=False, verbose=verbose)
                if verbose and results:
                    for r in results[-1:]:
                        print(f"  {r[0]}: {r[2]} GB")

        for vol in ["/System/Volumes/VM", "/System/Volumes/Preboot", "/System/Volumes/xarts"]:
            if os.path.isdir(vol) and not any(p == vol for p, _, _ in results):
                kb = get_dir_size_kb(vol, timeout=120, use_x=False)
                if kb is not None and kb > 0:
                    results.append((vol, f"Volumes/{os.path.basename(vol)}", round(kb * 1024 / (1024**3), 2)))
                    if verbose:
                        print(f"  {vol}: {results[-1][2]} GB")

    # 剔除父路径：若 P 是 Q 的父目录，则剔除 P
    paths_in_results = [p for p, _, _ in results]

    def should_keep(path: str) -> bool:
        for other in paths_in_results:
            if other != path and is_parent_of(path, other):
                return False
        return True

    final = [(p, c, s) for p, c, s in results if should_keep(p)]
    final_sum = sum(s for _, _, s in final)

    # 仅当完整扫描且仍有明显缺口时才补「其他」
    if is_root and not user_only and final_sum < total_used - 2 and total_used > 0:
        other_gb = round(total_used - final_sum, 2)
        final.append((f"其他（未统计，约 {other_gb:.0f} GB）", "仍有目录 du 超时", other_gb))
        if verbose:
            print(f"\n  [警告] 仍有 {other_gb:.0f} GB 未统计到", file=sys.stderr)

    # 按大小降序
    final.sort(key=lambda x: -x[2])
    total = sum(s for _, _, s in final)

    if verbose:
        print()
        print("=" * 70)
        print("磁盘空间分布（合计应≈已用）")
        print(f"df 已用: {total_used} GB")
        print("=" * 70)
        for path, category, size_gb in final:
            pct = (100 * size_gb / total) if total > 0 else 0
            print(f"  {size_gb:>8.2f} GB ({pct:>5.1f}%)  {path}")
            print(f"           {category}")
        print("-" * 60)
        print(f"  合计: {total:.1f} GB")
        print()
        print_analysis_report(final, total_used, total, user_only=user_only)

    items = [{"path": p, "category": c, "size_gb": round(s, 2)} for p, c, s in final]
    large_items = [x for x in items if x["size_gb"] >= 1]
    return {
        "total_used_gb": round(total_used, 2),
        "scanned_total_gb": round(total, 2),
        "user_only": user_only,
        "items": items,
        "large_items": large_items,
    }


def print_analysis_report(final: list, total_used: float, total: float, user_only: bool = False) -> None:
    """输出分析报告：Top 占用、可清理项、建议"""
    lines = []
    lines.append("")
    lines.append("=" * 70)
    lines.append("分析报告")
    lines.append("=" * 70)

    # 1. 统计完整性
    if user_only:
        lines.append(f"\n模式: 仅用户主目录 | 全盘已用: {total_used:.0f} GB | 本目录合计: {total:.1f} GB")
    else:
        gap = total_used - total
        if abs(gap) <= 2:
            lines.append("\n✓ 统计完整，合计与 df 已用一致")
        elif gap > 2:
            lines.append(f"\n⚠ 约 {gap:.0f} GB 未统计到（du 超时），建议增大 DU_TIMEOUT_PER_LEVEL 后重跑")

    # 2. Top 5 占用
    lines.append("\n【Top 5 占用】")
    for path, _, size_gb in final[:5]:
        pct = (100 * size_gb / total) if total > 0 else 0
        lines.append(f"  {size_gb:>6.1f} GB ({pct:>4.1f}%)  {path}")

    # 3. 可清理项（按关键词匹配）
    cleanup_keywords = [
        ("Caches", "缓存，可清理"),
        ("Cache", "缓存，可清理"),
        ("Logs", "日志，可清理"),
        ("Log", "日志，可清理"),
        ("Downloads", "下载目录，可手动整理"),
        ("node_modules", "依赖，可 rm 后重装"),
        (".Trash", "废纸篓，可清空"),
        ("Trash", "废纸篓，可清空"),
        ("tmp", "临时文件，可清理"),
        ("temp", "临时文件，可清理"),
        ("Xcode", "Xcode 衍生数据/模拟器，可清理"),
        ("Developer", "开发工具数据，按需清理"),
        ("Docker", "Docker 镜像/容器，可 docker system prune"),
        ("Android", "Android 模拟器/SDK，按需清理"),
        ("npm", "npm 缓存，可 npm cache clean"),
        ("yarn", "yarn 缓存，可 yarn cache clean"),
        ("pip", "pip 缓存，可 pip cache purge"),
        ("conda", "conda 包缓存，可 conda clean"),
        ("Homebrew", "brew 缓存，可 brew cleanup"),
    ]
    cleanup_items = []
    for path, _, size_gb in final:
        for kw, desc in cleanup_keywords:
            if kw in path and size_gb >= 0.1:
                cleanup_items.append((path, size_gb, desc))
                break

    if cleanup_items:
        lines.append("\n【可清理项（≥0.1 GB）】")
        cleanup_items.sort(key=lambda x: -x[1])
        cleanup_total = sum(s for _, s, _ in cleanup_items)
        for path, size_gb, desc in cleanup_items[:15]:
            lines.append(f"  {size_gb:>6.1f} GB  {path}")
            lines.append(f"           → {desc}")
        lines.append(f"  可清理项合计约 {cleanup_total:.1f} GB")
    else:
        lines.append("\n【可清理项】未发现明显缓存/日志目录")

    # 4. 建议
    lines.append("\n【建议】")
    if cleanup_items:
        top_cleanup = cleanup_items[0]
        lines.append(f"  1. 优先清理 {top_cleanup[0]}（约 {top_cleanup[1]:.1f} GB）")
    else:
        lines.append("  1. 大占用主要在用户数据/应用，可手动整理 Documents、Downloads")
    lines.append("  2. 系统缓存：rm -rf ~/Library/Caches/*（谨慎）")
    lines.append("  3. 开发：npm/yarn/pip/conda 缓存、Docker 镜像、Xcode 衍生数据")
    lines.append("  4. 废纸篓：清空 ~/.Trash 及各卷的 .Trash")

    for line in lines:
        print(line)
    print()


def main(user_only: bool = False, verbose: bool = True) -> dict:
    """入口：执行扫描，verbose 时打印，返回结构化数据。"""
    return run_scan(user_only=user_only, verbose=verbose)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="磁盘空间细分 + 分析报告")
    parser.add_argument("-o", "--output", metavar="FILE", help="将完整输出保存到文件")
    parser.add_argument("--user-only", action="store_true", help="仅扫描用户主目录（无需 sudo）")
    parser.add_argument("--json", action="store_true", help="输出 JSON，供 API 调用")
    args = parser.parse_args()
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            orig_stdout, orig_stderr = sys.stdout, sys.stderr
            sys.stdout = f
            sys.stderr = f
            try:
                main(user_only=args.user_only)
            finally:
                sys.stdout, sys.stderr = orig_stdout, orig_stderr
        print(f"报告已保存到 {args.output}")
    elif args.json:
        result = main(user_only=args.user_only, verbose=False)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        main(user_only=args.user_only)

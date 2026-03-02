"""
写文章：应用 unified diff (patch) 到正文。
用于「LLM 输出 patch → 精确应用」的流程。
"""
import re
from typing import List, Tuple


def _parse_unified_hunk(line: str) -> Tuple[int, int, int, int] | None:
    """解析 @@ -old_start,old_count +new_start,new_count @@"""
    m = re.match(r"^@@\s+-(\d+)(?:,(\d+))?\s+\+(\d+)(?:,(\d+))?\s+@@", line)
    if not m:
        return None
    old_s, old_c, new_s, new_c = m.groups()
    return (
        int(old_s),
        int(old_c) if old_c else 1,
        int(new_s),
        int(new_c) if new_c else 1,
    )


def apply_unified_diff(content: str, patch: str) -> str:
    """
    将 unified diff 应用到 content，返回新内容。
    仅处理单文件、行导向的 diff；若应用失败则抛出 ValueError。
    """
    lines = content.splitlines()
    has_trailing_newline = content.endswith("\n") or content == ""

    patch_lines = patch.splitlines()
    i = 0
    output: List[str] = []
    pos_old = 0  # 0-based index in lines

    while i < len(patch_lines):
        line = patch_lines[i]
        if line.startswith("@@"):
            hunk = _parse_unified_hunk(line)
            if not hunk:
                i += 1
                continue
            old_start, old_count, _new_start, _new_count = hunk
            old_start_0 = old_start - 1

            # 输出 hunk 之前、尚未输出的原文件行
            while pos_old < old_start_0 and pos_old < len(lines):
                output.append(lines[pos_old])
                pos_old += 1

            if pos_old != old_start_0:
                raise ValueError(
                    f"patch 无法应用：期望从第 {old_start} 行开始，但当前已到第 {pos_old + 1} 行"
                )

            i += 1
            old_consumed = 0

            while i < len(patch_lines) and old_consumed < old_count:
                pl = patch_lines[i]
                if pl.startswith("@@"):
                    break
                prefix = pl[0] if pl else " "
                rest = pl[1:] if len(pl) > 1 else ""

                if prefix == " ":
                    if pos_old >= len(lines) or lines[pos_old] != rest:
                        raise ValueError("patch 上下文与当前文章不匹配，无法应用")
                    output.append(lines[pos_old])
                    pos_old += 1
                    old_consumed += 1
                elif prefix == "-":
                    if pos_old >= len(lines) or lines[pos_old] != rest:
                        raise ValueError("patch 要删除的行与当前文章不匹配")
                    pos_old += 1
                    old_consumed += 1
                elif prefix == "+":
                    output.append(rest)
                # 其他行（如 \ No newline at end of file）忽略，不纳入 old_consumed
                i += 1

            if old_consumed != old_count:
                raise ValueError("patch hunk 行数不足，无法应用")
            continue
        i += 1

    while pos_old < len(lines):
        output.append(lines[pos_old])
        pos_old += 1

    result = "\n".join(output)
    if has_trailing_newline and result != "":
        result += "\n"
    return result

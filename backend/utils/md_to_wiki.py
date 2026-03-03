"""
Markdown → MediaWiki wikitext 转换
与前端 wikiMdConvert.js 的 mdToWiki 逻辑保持一致，
供 url_to_wiki、pdf_to_wiki 等任务在写入 MediaWiki 时使用。
"""
import re
from typing import List, Tuple


MATH_PLACEHOLDER_PREFIX = "__WIKIMATH_"
MATH_PLACEHOLDER_SUFFIX = "__"


def _md_extract_math_to_placeholders(md: str) -> Tuple[str, List[dict]]:
    """提取 $$...$$ 与 $...$，替换为占位符"""
    math_list: List[dict] = []
    out = md

    def block_repl(match):
        body = match.group(1).strip()
        key = f"{MATH_PLACEHOLDER_PREFIX}{len(math_list)}{MATH_PLACEHOLDER_SUFFIX}"  # noqa: E501
        math_list.append({"block": True, "body": body})
        return key

    def inline_repl(match):
        body = match.group(1).strip()
        key = f"{MATH_PLACEHOLDER_PREFIX}{len(math_list)}{MATH_PLACEHOLDER_SUFFIX}"  # noqa: E501
        math_list.append({"block": False, "body": body})
        return key

    out = re.sub(r"\$\$([\s\S]*?)\$\$", block_repl, out)
    out = re.sub(r"\$([^$\n]+)\$", inline_repl, out)
    return out, math_list


def _md_restore_math_placeholders(text: str, math_list: List[dict]) -> str:
    """恢复公式占位符为 <math> 标签"""
    for i, m in enumerate(math_list):
        body = m["body"]
        if m["block"]:
            tag = f'<math display="block">{body}</math>'
        else:
            tag = f"<math>{body}</math>"
        key = f"{MATH_PLACEHOLDER_PREFIX}{i}{MATH_PLACEHOLDER_SUFFIX}"
        text = text.replace(key, tag)
    return text


def _md_headers_to_wiki(md: str) -> str:
    """## H2 → == H2 ==, ### H3 → === H3 === …"""

    def repl(match):
        hashes = match.group(1)
        title = match.group(2).strip()
        level = min(len(hashes), 6)
        eq = "=" * level
        return f"{eq} {title} {eq}"

    return re.sub(r"^(#{1,6})\s+(.+)$", repl, md, flags=re.MULTILINE)  # noqa: E501


def _md_emphasis_to_wiki(md: str) -> str:
    """**bold** → '''bold''', *italic* → ''italic''"""
    s = md
    s = re.sub(r"\*\*\*(.+?)\*\*\*", r"'''''\1'''''", s)
    s = re.sub(r"\*\*(.+?)\*\*", r"'''\1'''", s)
    s = re.sub(r"\*(.+?)\*", r"''\1''", s)
    s = re.sub(r"_(.+?)_", r"''\1''", s)
    s = re.sub(r"__(.+?)__", r"'''\1'''", s)
    return s


def _md_links_to_wiki(md: str) -> str:
    """[text](url) → 外部 [url text] 或内部 [[url|text]]"""

    def repl(match):
        text = match.group(1)
        url = match.group(2).strip()
        if re.match(r"^https?://", url, re.I):
            return f"[{url} {text}]"
        return f"[[{url}|{text}]]"

    return re.sub(r"\[([^\]]+)\]\(([^)]+)\)", repl, md)


def _md_lists_to_wiki(md: str) -> str:
    """- item → * item; 1. /2. /3. item → # item"""
    lines = md.split("\n")
    out = []
    for line in lines:
        ul_match = re.match(r"^(\s*)[-*+]\s+(.*)$", line)
        ol_match = re.match(r"^(\s*)\d+\.\s+(.*)$", line)
        if ul_match:
            indent = len(ul_match.group(1))
            depth = indent // 2 + 1
            out.append("*" * depth + " " + ul_match.group(2))
        elif ol_match:
            indent = len(ol_match.group(1))
            depth = indent // 2 + 1
            out.append("#" * depth + " " + ol_match.group(2))
        else:
            out.append(line)
    return "\n".join(out)


def md_to_wiki(md: str) -> str:
    """
    Markdown → MediaWiki wikitext
    覆盖：标题、粗/斜体、链接、列表、公式（$ / $$ → <math>）
    """
    if md is None or not isinstance(md, str):
        return ""
    s = md.strip()
    if not s:
        return ""
    s, math_list = _md_extract_math_to_placeholders(s)
    s = _md_headers_to_wiki(s)
    s = _md_links_to_wiki(s)
    s = _md_emphasis_to_wiki(s)
    s = _md_lists_to_wiki(s)
    return _md_restore_math_placeholders(s, math_list)

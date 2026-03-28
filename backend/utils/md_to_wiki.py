"""
Markdown → MediaWiki wikitext 转换
与前端 wikiMdConvert.js 的 mdToWiki 逻辑保持一致，
供 url_to_wiki、pdf_to_wiki 等任务在写入 MediaWiki 时使用。
"""
import re
from typing import List, Tuple


# 使用 \x01 避免被 _ 或 __ 的强调正则误匹配
MATH_PLACEHOLDER_PREFIX = "\x01WIKIMATH"
MATH_PLACEHOLDER_SUFFIX = "\x01"
CODE_PLACEHOLDER_PREFIX = "\x01WIKICODE"
CODE_PLACEHOLDER_SUFFIX = "\x01"

# 与 frontend wikiMdConvert.js MW_FILE_DEFAULT_DISPLAY_PARAMS 一致
MW_FILE_DEFAULT_DISPLAY_PARAMS = "500px|center|frame"


def _md_extract_code_to_placeholders(md: str) -> Tuple[str, List[dict]]:
    """提取 ```lang\\ncode``` 代码块，避免后续 emphasis/links 等正则破坏。转为占位符。"""
    code_list: List[dict] = []
    # 匹配 ```lang\ncode``` 或 ```\ncode```（无 lang）
    pattern = r"```([\w.+-]*)\s*\n([\s\S]*?)```\s*"

    def repl(match):
        lang = (match.group(1) or "").strip() or "text"
        code = match.group(2).rstrip("\n")
        key = f"{CODE_PLACEHOLDER_PREFIX}{len(code_list)}{CODE_PLACEHOLDER_SUFFIX}"
        code_list.append({"lang": lang, "code": code})
        return key

    out = re.sub(pattern, repl, md)
    return out, code_list


def _md_restore_code_placeholders(text: str, code_list: List[dict]) -> str:
    """恢复代码块占位符为 MediaWiki <syntaxhighlight lang="xxx"> 标签"""
    for i, c in enumerate(code_list):
        lang = c["lang"]
        code = c["code"]
        tag = f'<syntaxhighlight lang="{lang}">\n{code}\n</syntaxhighlight>'
        key = f"{CODE_PLACEHOLDER_PREFIX}{i}{CODE_PLACEHOLDER_SUFFIX}"
        text = text.replace(key, tag)
    return text


def _md_markdown_images_to_wiki(md: str) -> str:
    """![alt](url) → [[File:url|500px|center|frame|alt]]，与前端 mdToWikiWithImages 一致"""

    def repl(m: re.Match) -> str:
        alt = (m.group(1) or "").strip()
        url = (m.group(2) or "").strip()
        p = MW_FILE_DEFAULT_DISPLAY_PARAMS
        if alt:
            return f"[[File:{url}|{p}|{alt}]]"
        return f"[[File:{url}|{p}]]"

    return re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", repl, md)


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
    """恢复公式占位符为 $ / $$（MediaWiki 原生支持）"""
    for i, m in enumerate(math_list):
        body = m["body"]
        if m["block"]:
            tag = f"$${body}$$"
        else:
            tag = f"${body}$"
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
    覆盖：标题、粗/斜体、链接、列表、公式（$ / $$）、
    插图（![alt](url) → [[File:url|500px|center|frame|alt]]）、
    代码块（``` → <syntaxhighlight lang="xxx">）
    """
    if md is None or not isinstance(md, str):
        return ""
    s = md.strip()
    if not s:
        return ""
    s, code_list = _md_extract_code_to_placeholders(s)
    s, math_list = _md_extract_math_to_placeholders(s)
    s = _md_markdown_images_to_wiki(s)
    s = _md_headers_to_wiki(s)
    s = _md_links_to_wiki(s)
    s = _md_emphasis_to_wiki(s)
    s = _md_lists_to_wiki(s)
    s = _md_restore_math_placeholders(s, math_list)
    return _md_restore_code_placeholders(s, code_list)

#!/usr/bin/env python3
"""
将公众号草稿箱中所有草稿的正文用 GitHub 风格模板重写（行内样式），并写回。
用法（项目根）：python scripts/rewrite_wechat_drafts.py
可选：python scripts/rewrite_wechat_drafts.py --dry-run  仅列出草稿与预览，不写回。
依赖：.env 中 WECHAT_MP_APP_ID、WECHAT_MP_APP_SECRET，IP 白名单。
"""
import argparse
import os
import re
import sys

_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _root not in sys.path:
    sys.path.insert(0, _root)

try:
    from dotenv import load_dotenv
    _env = os.path.join(_root, ".env")
    if os.path.isfile(_env):
        load_dotenv(_env)
    else:
        load_dotenv()
except ImportError:
    pass


# GitHub 风格行内样式（与 docs/design/wechat-mp-article-template.html 一致）
GITHUB_STYLES = {
    "p": "color:#24292f; font-size:16px; line-height:1.6; margin:0 0 1em 0;",
    "h1": "color:#24292f; font-size:24px; font-weight:600; margin:0 0 0.6em 0; border-bottom:1px solid #d0d7de; padding-bottom:0.3em;",
    "h2": "color:#24292f; font-size:20px; font-weight:600; margin:1.2em 0 0.6em 0; border-bottom:1px solid #d0d7de; padding-bottom:0.3em;",
    "h3": "color:#24292f; font-size:17px; font-weight:600; margin:1em 0 0.5em 0;",
    "h4": "color:#24292f; font-size:16px; font-weight:600; margin:1em 0 0.5em 0;",
    "strong": "color:#24292f; font-weight:600;",
    "b": "color:#24292f; font-weight:600;",
    "em": "color:#57606a; font-style:italic;",
    "i": "color:#57606a; font-style:italic;",
    "a": "color:#0969da; text-decoration:none;",
    "code": "background-color:#f6f8fa; color:#24292f; font-family:monospace; font-size:14px; padding:0.2em 0.4em; border:1px solid #d0d7de; border-radius:4px;",
    "pre": "background-color:#f6f8fa; color:#24292f; font-family:monospace; font-size:14px; line-height:1.5; margin:0 0 1em 0; padding:12px; border:1px solid #d0d7de; border-radius:6px; overflow-x:auto;",
    "blockquote": "color:#57606a; font-size:15px; line-height:1.6; margin:0 0 1em 0; padding-left:12px; border-left:4px solid #d0d7de;",
    "ul": "color:#24292f; font-size:16px; line-height:1.6; margin:0 0 1em 0; padding-left:1.5em;",
    "ol": "color:#24292f; font-size:16px; line-height:1.6; margin:0 0 1em 0; padding-left:1.5em;",
    "li": "margin-bottom:0.25em;",
    "hr": "border:0; border-top:1px solid #d0d7de; margin:1.5em 0;",
    "img": "max-width:100%; height:auto; border:1px solid #d0d7de; border-radius:6px;",
    "div": "color:#24292f; font-size:16px; line-height:1.6; margin:0 0 1em 0;",
}


def _strip_style(attrs: str) -> str:
    """去掉现有 style 属性，便于统一替换为 GitHub 样式。"""
    if not attrs or not attrs.strip():
        return ""
    # 移除 style="..." 或 style='...'
    return re.sub(r'\s*style\s*=\s*["\'][^"\']*["\']', "", attrs, flags=re.I).strip()


def _apply_style_to_opening_tag(html: str, tag: str, style: str) -> str:
    """将指定标签的开头替换为带 GitHub 行内样式的版本（保留其他属性，去掉原 style）。"""
    # 匹配 <tag> 或 <tag attr="..." ...>
    pattern = re.compile(
        r"<" + re.escape(tag) + r"\b(\s[^>]*)?>",
        re.IGNORECASE | re.DOTALL,
    )

    def repl(m):
        attrs = m.group(1) or ""
        stripped = _strip_style(attrs)
        if stripped:
            return f"<{tag} {stripped} style=\"{style}\">"
        return f"<{tag} style=\"{style}\">"

    return pattern.sub(repl, html)


def apply_github_styles(html: str) -> str:
    """
    对现有正文 HTML 应用 GitHub 风格行内样式。
    保留原有结构和图片/链接，仅给块级与行内元素加上行内 style。
    """
    if not html or not html.strip():
        return html
    out = html
    # 按标签长度倒序，避免先替换 <p> 把 <pre> 里的东西误伤（pre 先于 p 处理）
    for tag in sorted(GITHUB_STYLES.keys(), key=len, reverse=True):
        out = _apply_style_to_opening_tag(out, tag, GITHUB_STYLES[tag])
    # pre 内的 code 常带 style，去掉 code 的 style 避免重复
    out = re.sub(
        r"<code\s+style=\"[^\"]*\"\s*>",
        "<code style=\"" + GITHUB_STYLES["code"] + "\">",
        out,
        flags=re.I,
    )
    return out


def main():
    parser = argparse.ArgumentParser(description="将公众号草稿正文用 GitHub 风格模板重写并写回")
    parser.add_argument("--dry-run", action="store_true", help="仅列出草稿并预览重写结果，不调用更新接口")
    args = parser.parse_args()

    from backend.services.wechat_mp_service import WeChatMPClient, WeChatMPClientError

    print("公众号草稿 · GitHub 风格重写")
    print("-" * 50)

    try:
        client = WeChatMPClient()
    except WeChatMPClientError as e:
        print(f"配置错误: {e}")
        sys.exit(1)

    all_drafts = []
    offset = 0
    count = 20
    while True:
        try:
            res = client.get_draft_list(offset=offset, count=count, no_content=0)
        except WeChatMPClientError as e:
            print(f"获取草稿列表失败: {e}")
            sys.exit(1)
        items = res.get("item") or []
        total = res.get("total_count", 0)
        if not items:
            break
        all_drafts.extend(items)
        if len(all_drafts) >= total or len(items) < count:
            break
        offset += len(items)

    if not all_drafts:
        print("草稿箱为空，无需重写。")
        return

    print(f"共 {len(all_drafts)} 篇草稿（media_id）。")

    updated = 0
    for draft in all_drafts:
        media_id = (draft.get("media_id") or "").strip()
        if not media_id:
            continue
        content = draft.get("content") or {}
        news_list = content.get("news_item") or []
        for idx, article in enumerate(news_list):
            title = (article.get("title") or "").strip()
            raw_content = article.get("content") or ""
            if not raw_content.strip():
                print(f"  [{media_id[:12]}...] 第 {idx + 1} 篇 无正文，跳过")
                continue
            new_content = apply_github_styles(raw_content)
            if args.dry_run:
                print(f"  [{media_id[:12]}...] 第 {idx + 1} 篇: {title[:30]}...")
                print(f"    正文长度: {len(raw_content)} -> {len(new_content)} 字符")
                continue
            try:
                client.update_draft(
                    media_id=media_id,
                    index=idx,
                    title=title,
                    content=new_content,
                    author=(article.get("author") or "").strip() or None,
                    digest=(article.get("digest") or "").strip() or None,
                    thumb_media_id=(article.get("thumb_media_id") or "").strip() or None,
                    content_source_url=(article.get("content_source_url") or "").strip() or None,
                )
                updated += 1
                print(f"  已更新: {media_id[:12]}... 第 {idx + 1} 篇 《{title[:28]}》")
            except WeChatMPClientError as e:
                msg = str(e)
                print(f"  更新失败 [{media_id[:12]}...] 第 {idx + 1} 篇: {msg}")
                if "20000" in msg or "1M" in msg or "1MB" in msg:
                    print(f"    提示: 正文超长，可缩短内容或使用「阅读原文」链接。")

    if args.dry_run:
        print("-" * 50)
        print(" dry-run 结束，未写回。去掉 --dry-run 执行实际更新。")
    else:
        print("-" * 50)
        print(f" 完成，已更新 {updated} 篇草稿。")


if __name__ == "__main__":
    main()

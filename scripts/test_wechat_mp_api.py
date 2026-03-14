#!/usr/bin/env python3
"""
测试微信公众号 API（个人号可用：token、草稿列表、草稿详情）。
用法（项目根目录）：python scripts/test_wechat_mp_api.py
需在 .env 中配置 WECHAT_MP_APP_ID、WECHAT_MP_APP_SECRET，并配置 IP 白名单。
"""
import os
import sys

_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _root not in sys.path:
    sys.path.insert(0, _root)

from pathlib import Path
from shared.load_env import load_env
load_env(Path(_root))


def main():
    from backend.services.wechat_mp_service import WeChatMPClient, WeChatMPClientError

    print("微信公众号 API 测试（token、草稿列表、草稿详情）")
    print("-" * 50)

    try:
        client = WeChatMPClient()
    except WeChatMPClientError as e:
        print(f"配置错误: {e}")
        sys.exit(1)

    # 1. 获取 token（内部会缓存）
    try:
        token = client._ensure_token()
        print(f"1. access_token: 已获取（前 20 位）{token[:20]}...")
    except WeChatMPClientError as e:
        print(f"1. access_token 失败: {e}")
        sys.exit(1)

    # 2. 草稿列表
    try:
        draft_res = client.get_draft_list(offset=0, count=5, no_content=1)
        total = draft_res.get("total_count", 0)
        items = draft_res.get("item") or []
        print(f"2. 草稿列表: 共 {total} 条，本次返回 {len(items)} 条")
        for i, it in enumerate(items[:3]):
            mid = it.get("media_id") or ""
            mid_pre = mid[:16] + "..." if len(mid) > 16 else mid
            print(f"   [{i+1}] media_id={mid_pre} update_time={it.get('update_time', '')}")
    except WeChatMPClientError as e:
        print(f"2. 草稿列表 失败: {e}")
        items = []

    # 3. 草稿详情（若有草稿则取第一条）
    if items:
        media_id = items[0].get("media_id")
        if media_id:
            try:
                detail = client.get_draft(media_id)
                content = detail.get("content") or detail
                news_list = content.get("news_item") or []
                news = news_list[0] if news_list else {}
                title = (news.get("title") or "")[:30]
                print(f"3. 草稿详情: title={title}{'...' if len(news.get('title') or '') > 30 else ''} author={news.get('author', '')}")
            except WeChatMPClientError as e:
                print(f"3. 草稿详情 失败: {e}")
    else:
        print("3. 草稿详情: 无草稿，跳过")

    print("-" * 50)
    print("测试完成。")


if __name__ == "__main__":
    main()

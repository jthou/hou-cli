"""微信公众号 API 服务（写文章 + 统计，当前仅实现只读接口用于联调）"""

from .client import WeChatMPClient, WeChatMPClientError

__all__ = ["WeChatMPClient", "WeChatMPClientError"]

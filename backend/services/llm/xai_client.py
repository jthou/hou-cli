"""xAI Grok 客户端（通过 TheTurbo.ai 网关，兼容 OpenAI API 格式）"""
import os
import logging
from typing import Optional
from openai import AsyncOpenAI
import httpx

logger = logging.getLogger(__name__)


class XAIClient:
    """xAI Grok 客户端（通过 TheTurbo.ai 网关，兼容 OpenAI API 格式）"""
    
    def __init__(self, api_key: str, base_url: Optional[str] = None):
        """
        初始化 xAI Grok 客户端
        
        Args:
            api_key: xAI API Key（通过 TheTurbo.ai 网关）
            base_url: API 基础 URL，默认使用 TheTurbo.ai 网关地址
        """
        self.api_key = api_key.strip()
        if not self.api_key or len(self.api_key) < 10:
            raise ValueError("xAI API Key 格式无效：长度不足或为空")
        
        # TheTurbo.ai 网关 API 地址（与 OpenAI 相同）
        default_base_url = os.getenv(
            "XAI_BASE_URL",
            "https://gateway.theturbo.ai/v1"
        )
        self.base_url = base_url or default_base_url
        
        # 配置 httpx 客户端
        http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(300.0, connect=30.0, read=300.0, write=30.0),
            trust_env=False
        )
        
        # 使用 OpenAI 兼容的客户端（Grok 支持 OpenAI 协议）
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            http_client=http_client
        )
        
        logger.info(f"xAI Grok 客户端已初始化，base_url: {self.base_url}")
    
    @property
    def chat(self):
        """返回聊天完成接口"""
        return self.client.chat.completions



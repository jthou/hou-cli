"""阿里云百炼平台客户端"""
import os
import logging
from typing import Optional
from openai import AsyncOpenAI
import httpx

logger = logging.getLogger(__name__)


class BailianClient:
    """阿里云百炼平台客户端（兼容 OpenAI API 格式）"""
    
    def __init__(self, api_key: str, base_url: Optional[str] = None):
        """
        初始化百炼平台客户端
        
        Args:
            api_key: 百炼平台 API Key
            base_url: API 基础 URL，默认使用百炼平台标准地址
        """
        self.api_key = api_key.strip()
        if not self.api_key or len(self.api_key) < 10:
            raise ValueError("百炼平台 API Key 格式无效：长度不足或为空")
        
        # 百炼平台 API 地址
        # 默认使用 dashscope（通义千问）的 API 地址
        # 如果需要使用其他百炼模型，可以通过环境变量配置
        default_base_url = os.getenv(
            "BAILIAN_BASE_URL",
            "https://dashscope.aliyuncs.com/compatible-mode/v1"
        )
        self.base_url = base_url or default_base_url
        
        # 配置 httpx 客户端
        http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(300.0, connect=30.0, read=300.0, write=30.0),
            trust_env=False
        )
        
        # 使用 OpenAI 兼容的客户端（百炼平台支持 OpenAI 兼容 API）
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            http_client=http_client
        )
        
        logger.info(f"百炼平台客户端已初始化，base_url: {self.base_url}")
    
    @property
    def chat(self):
        """返回聊天完成接口"""
        return self.client.chat.completions



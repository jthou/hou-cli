"""配置管理"""
import os
from dataclasses import dataclass

@dataclass
class Config:
    """配置类"""
    # 后端配置
    backend_host: str = os.getenv("BACKEND_HOST", "127.0.0.1")
    backend_port: int = int(os.getenv("BACKEND_PORT", "8000"))
    
    # LLM 配置
    deepseek_api_key: str = os.getenv("DEEPSEEK_API_KEY", "")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "deepseek-r1:14b")
    
    # 其他配置
    log_level: str = os.getenv("LOG_LEVEL", "INFO")


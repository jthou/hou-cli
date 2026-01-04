"""MCP 配置管理"""
import os
import logging
from typing import List, Optional
from dotenv import load_dotenv
from backend.core.agent.mcps.models import MCPServerConfig

logger = logging.getLogger(__name__)


class MCPConfig:
    """MCP 配置管理器"""
    
    @staticmethod
    def load_from_env() -> List[MCPServerConfig]:
        """
        从环境变量加载 MCP 服务器配置
        
        环境变量格式：
        - MCP_SERVERS=server1,server2,server3  # 服务器名称列表
        - MCP_SERVER1_NAME=filesystem
        - MCP_SERVER1_TYPE=stdio
        - MCP_SERVER1_COMMAND=node
        - MCP_SERVER1_ARGS=path/to/server.js
        - MCP_SERVER1_ENABLED=true
        
        Returns:
            MCP 服务器配置列表
        """
        # 确保加载 .env 文件
        load_dotenv()
        
        # 获取服务器名称列表
        servers_str = os.getenv("MCP_SERVERS", "")
        if not servers_str:
            logger.debug("未配置 MCP_SERVERS，跳过 MCP 服务器加载")
            return []
        
        server_names = [s.strip() for s in servers_str.split(",") if s.strip()]
        if not server_names:
            return []
        
        configs = []
        for server_name in server_names:
            config = MCPConfig._load_server_config(server_name)
            if config:
                configs.append(config)
        
        logger.info(f"加载了 {len(configs)} 个 MCP 服务器配置: {[c.name for c in configs]}")
        return configs
    
    @staticmethod
    def _load_server_config(server_key: str) -> Optional[MCPServerConfig]:
        """
        加载单个 MCP 服务器配置
        
        Args:
            server_key: 服务器键名（如 "server1"）
            
        Returns:
            MCPServerConfig 或 None
        """
        prefix = f"MCP_{server_key.upper()}_"
        
        name = os.getenv(f"{prefix}NAME")
        if not name:
            logger.warning(f"MCP 服务器 {server_key} 缺少 NAME 配置，跳过")
            return None
        
        server_type = os.getenv(f"{prefix}TYPE", "stdio").lower()
        enabled = os.getenv(f"{prefix}ENABLED", "true").lower() == "true"
        
        if not enabled:
            logger.debug(f"MCP 服务器 {name} 已禁用，跳过")
            return None
        
        config = MCPServerConfig(
            name=name,
            type=server_type,
            enabled=enabled,
            timeout=int(os.getenv(f"{prefix}TIMEOUT", "30")),
        )
        
        if server_type == "stdio":
            # stdio 模式需要 command 和 args
            command = os.getenv(f"{prefix}COMMAND")
            if not command:
                logger.warning(f"MCP 服务器 {name} (stdio) 缺少 COMMAND 配置，跳过")
                return None
            
            args_str = os.getenv(f"{prefix}ARGS", "")
            args = [arg.strip() for arg in args_str.split(",") if arg.strip()] if args_str else []
            
            config.command = command
            config.args = args
            
            # 加载环境变量（可选）
            env_prefix = f"{prefix}ENV_"
            env_vars = {}
            for key, value in os.environ.items():
                if key.startswith(env_prefix):
                    env_key = key[len(env_prefix):]
                    env_vars[env_key] = value
            if env_vars:
                config.env = env_vars
                
        elif server_type in ("http", "sse"):
            # http/sse 模式需要 URL
            url = os.getenv(f"{prefix}URL")
            if not url:
                logger.warning(f"MCP 服务器 {name} ({server_type}) 缺少 URL 配置，跳过")
                return None
            config.url = url
        else:
            logger.warning(f"MCP 服务器 {name} 不支持的连接类型: {server_type}，跳过")
            return None
        
        return config


def load_mcp_configs() -> List[MCPServerConfig]:
    """加载所有 MCP 服务器配置（便捷函数）"""
    return MCPConfig.load_from_env()


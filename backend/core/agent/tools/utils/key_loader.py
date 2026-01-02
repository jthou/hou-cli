"""私钥加载工具"""
import os
from typing import Optional


class KeyLoaderError(Exception):
    """私钥加载错误"""
    pass


class KeyLoader:
    """私钥加载器"""
    
    def __init__(self, env_var_name: str = "WEATHER_JWT_PRIVATE_KEY"):
        """
        初始化私钥加载器
        
        Args:
            env_var_name: 环境变量名称
        """
        self.env_var_name = env_var_name
    
    def load_private_key_from_env(self) -> str:
        """
        从环境变量加载私钥
        
        Returns:
            私钥字符串
            
        Raises:
            KeyLoaderError: 如果环境变量未设置或为空
        """
        key = os.getenv(self.env_var_name)
        if not key:
            raise KeyLoaderError(
                f"Environment variable '{self.env_var_name}' is not set or empty. "
                f"Please set it in your .env file."
            )
        return key
    
    def normalize_private_key(self, key: str) -> str:
        """
        规范化私钥格式
        
        处理以下情况：
        1. 单行格式（空格分隔）
        2. 多行格式（换行符分隔）
        3. 转义换行符（\\n）
        
        Args:
            key: 原始私钥字符串
            
        Returns:
            规范化后的私钥字符串（PEM 格式）
        """
        # 处理转义换行符
        key = key.replace("\\n", "\n")
        
        # 如果已经是多行格式，直接返回
        if "\n" in key:
            return key.strip()
        
        # 处理单行格式：在 BEGIN/END 标记前后添加换行符
        key = key.replace("-----BEGIN PRIVATE KEY-----", "-----BEGIN PRIVATE KEY-----\n")
        key = key.replace("-----END PRIVATE KEY-----", "\n-----END PRIVATE KEY-----")
        
        # 清理多余的空格和换行符
        lines = [line.strip() for line in key.split("\n") if line.strip()]
        
        # 重新组装，确保格式正确
        result = []
        for i, line in enumerate(lines):
            if line.startswith("-----"):
                result.append(line)
            else:
                # 密钥内容行
                result.append(line)
        
        return "\n".join(result).strip()


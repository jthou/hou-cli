"""JWT 认证模块"""
import time
from typing import Dict, Optional
from backend.core.agent.tools.utils.key_loader import KeyLoader, KeyLoaderError


class JWTAuthError(Exception):
    """JWT 认证错误"""
    pass


class JWTAuth:
    """JWT 认证类"""
    
    def __init__(
        self,
        private_key: str,
        issuer: str,
        audience: str,
        subject: str,
        expires_in: int = 3600
    ):
        """
        初始化 JWT 认证
        
        Args:
            private_key: RSA 私钥（PEM 格式）
            issuer: JWT 发行者（iss）
            audience: JWT 受众（aud）
            subject: JWT 主题（sub）
            expires_in: 过期时间（秒，默认 3600）
        """
        self.private_key = private_key
        self.issuer = issuer
        self.audience = audience
        self.subject = subject
        self.expires_in = expires_in
    
    @classmethod
    def from_env(
        cls,
        issuer: str,
        audience: str,
        subject: str,
        expires_in: Optional[int] = None,
        env_var_name: str = "WEATHER_JWT_PRIVATE_KEY"
    ) -> 'JWTAuth':
        """
        从环境变量创建 JWT 认证实例
        
        Args:
            issuer: JWT 发行者（iss）
            audience: JWT 受众（aud）
            subject: JWT 主题（sub）
            expires_in: 过期时间（秒），如果为 None 则从环境变量读取
            env_var_name: 环境变量名称
            
        Returns:
            JWTAuth 实例
            
        Raises:
            JWTAuthError: 如果私钥加载失败
        """
        try:
            key_loader = KeyLoader(env_var_name=env_var_name)
            raw_key = key_loader.load_private_key_from_env()
            private_key = key_loader.normalize_private_key(raw_key)
            
            # 如果 expires_in 为 None，尝试从环境变量读取
            if expires_in is None:
                import os
                expires_in_str = os.getenv("WEATHER_JWT_EXPIRES_IN", "3600")
                try:
                    expires_in = int(expires_in_str)
                except ValueError:
                    expires_in = 3600  # 默认值
            
            return cls(
                private_key=private_key,
                issuer=issuer,
                audience=audience,
                subject=subject,
                expires_in=expires_in
            )
        except KeyLoaderError as e:
            raise JWTAuthError(f"Failed to load private key: {str(e)}")
    
    def generate_token(self) -> str:
        """
        生成 JWT token
        
        Returns:
            JWT token 字符串
            
        Raises:
            JWTAuthError: 如果 token 生成失败
        """
        try:
            import jwt
            
            # 构建 payload
            now = int(time.time())
            payload = {
                "iss": self.issuer,
                "iat": now,
                "exp": now + self.expires_in,
                "aud": self.audience,
                "sub": self.subject
            }
            
            # 使用 RS256 算法签名
            token = jwt.encode(payload, self.private_key, algorithm="RS256")
            
            # jwt.encode 在 PyJWT 2.0+ 返回字符串，旧版本返回 bytes
            if isinstance(token, bytes):
                token = token.decode('utf-8')
            
            return token
        except Exception as e:
            raise JWTAuthError(f"Failed to generate JWT token: {str(e)}")
    
    def get_authorization_header(self) -> Dict[str, str]:
        """
        获取 Authorization 请求头
        
        Returns:
            包含 Authorization 头的字典
        """
        token = self.generate_token()
        return {
            "Authorization": f"Bearer {token}"
        }


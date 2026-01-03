"""JWT 认证模块"""
import time
from typing import Dict, Optional
from backend.core.agent.tools.utils.key_loader import KeyLoader, KeyLoaderError


class JWTAuthError(Exception):
    """JWT 认证错误"""
    pass


class JWTAuth:
    """JWT 认证类（符合和风天气 API 规范）"""
    
    def __init__(
        self,
        private_key: str,
        kid: str,  # 凭据ID（Credential ID）
        sub: str,  # 项目ID（Project ID）
        expires_in: int = 3600
    ):
        """
        初始化 JWT 认证
        
        Args:
            private_key: Ed25519 私钥（PEM 格式）
            kid: 凭据ID（Credential ID），在控制台-项目管理中查看
            sub: 项目ID（Project ID），在控制台-项目管理中查看
            expires_in: Token 过期时间（秒），默认 86400（24小时）
                       注意：和风天气 API 可能不检查此字段，此配置主要用于符合 JWT 标准
        """
        self.private_key = private_key
        self.kid = kid
        self.sub = sub
        self.expires_in = expires_in
    
    @classmethod
    def from_env(
        cls,
        kid: Optional[str] = None,  # 凭据ID，如果为 None 则从环境变量读取
        sub: Optional[str] = None,   # 项目ID，如果为 None 则从环境变量读取
        expires_in: Optional[int] = None,
        env_var_name: str = "WEATHER_JWT_PRIVATE_KEY"
    ) -> 'JWTAuth':
        """
        从环境变量创建 JWTAuth 实例
        
        Args:
            kid: 凭据ID（Credential ID），如果为 None 则从环境变量 QWEATHER_CREDENTIAL_ID 读取
            sub: 项目ID（Project ID），如果为 None 则从环境变量 QWEATHER_PROJECT_ID 读取
            expires_in: Token 过期时间（秒），如果为 None 则从环境变量读取
            env_var_name: 私钥环境变量名称
            
        Returns:
            JWTAuth 实例
            
        Raises:
            JWTAuthError: 如果私钥、kid 或 sub 未设置或加载失败
        """
        import os
        
        try:
            # 加载私钥
            key_loader = KeyLoader(env_var_name=env_var_name)
            raw_key = key_loader.load_private_key_from_env()
            private_key = key_loader.normalize_private_key(raw_key)
            
            # 获取 kid（凭据ID）
            if kid is None:
                kid = os.getenv("QWEATHER_CREDENTIAL_ID")
            if not kid:
                raise JWTAuthError("Credential ID (kid) is required. Set QWEATHER_CREDENTIAL_ID in .env file.")
            
            # 获取 sub（项目ID）
            if sub is None:
                sub = os.getenv("QWEATHER_PROJECT_ID")
            if not sub:
                raise JWTAuthError("Project ID (sub) is required. Set QWEATHER_PROJECT_ID in .env file.")
            
            # 如果 expires_in 为 None，尝试从环境变量读取
            if expires_in is None:
                expires_in_str = os.getenv("WEATHER_JWT_EXPIRES_IN", "3600")
                try:
                    expires_in = int(expires_in_str)
                except ValueError:
                    expires_in = 3600  # 默认值
            
            return cls(
                private_key=private_key,
                kid=kid,
                sub=sub,
                expires_in=expires_in
            )
        except KeyLoaderError as e:
            raise JWTAuthError(f"Failed to load private key: {str(e)}")
    
    def generate_token(self) -> str:
        """
        生成 JWT Token（符合和风天气 API 规范）
        
        Returns:
            JWT Token 字符串
            
        Raises:
            JWTAuthError: 如果 token 生成失败
        """
        try:
            import jwt
            
            # 构建 Payload（只包含 sub, iat, exp）
            # iat 设置为当前时间前30秒，防止时间误差
            now = int(time.time())
            iat = now - 30
            exp = iat + self.expires_in
            
            payload = {
                "sub": self.sub,  # 项目ID
                "iat": iat,       # 签发时间（当前时间-30秒）
                "exp": exp        # 过期时间
            }
            
            # 构建 Header（包含 alg 和 kid）
            headers = {
                "alg": "EdDSA",
                "kid": self.kid   # 凭据ID
            }
            
            # 使用 Ed25519 (EdDSA) 算法签名
            token = jwt.encode(
                payload,
                self.private_key,
                algorithm="EdDSA",
                headers=headers
            )
            
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

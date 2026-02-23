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
    
    def _get_ed25519_key(self):
        """将 PEM 字符串加载为 Ed25519 私钥对象，供 PyJWT EdDSA 使用"""
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import ed25519
        from cryptography.hazmat.backends import default_backend

        try:
            key_bytes = self.private_key.encode("utf-8") if isinstance(self.private_key, str) else self.private_key
            key = serialization.load_pem_private_key(key_bytes, password=None, backend=default_backend())
        except Exception as e:
            raise JWTAuthError(f"私钥格式无效: {e}")

        if not isinstance(key, ed25519.Ed25519PrivateKey):
            raise JWTAuthError(
                "和风天气 API 要求 Ed25519 私钥（EdDSA），当前不是。"
                "请在和风控制台生成 Ed25519 凭据，或本地执行："
                " openssl genpkey -algorithm Ed25519 -out key.pem ，"
                "将 PEM 填入 WEATHER_JWT_PRIVATE_KEY。"
            )
        return key

    def generate_token(self) -> str:
        """
        生成 JWT Token（符合和风天气 API 规范）。
        与官方文档一致：payload 含 iat/exp/sub，header 含 kid，算法 EdDSA。
        见 https://dev.qweather.com/docs/configuration/authentication
        """
        try:
            import jwt

            # 文档示例传 PEM 字符串；PyJWT EdDSA 需密钥对象，故用 cryptography 加载
            key = self._get_ed25519_key()

            now = int(time.time())
            iat = now - 30  # 文档建议 iat 设为当前时间前 30 秒
            exp = iat + self.expires_in

            payload = {"sub": self.sub, "iat": iat, "exp": exp}
            headers = {"alg": "EdDSA", "kid": self.kid}

            token = jwt.encode(
                payload,
                key,
                algorithm="EdDSA",
                headers=headers,
            )

            if isinstance(token, bytes):
                token = token.decode("utf-8")
            return token
        except JWTAuthError:
            raise
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

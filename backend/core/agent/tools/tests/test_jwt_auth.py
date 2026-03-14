"""JWT 认证测试"""
import pytest
import os
from unittest.mock import patch, MagicMock
from shared.load_env import load_env_for_file
from backend.core.agent.tools.auth.jwt_auth import JWTAuth, JWTAuthError
from backend.core.agent.tools.utils.key_loader import KeyLoader, KeyLoaderError

load_env_for_file(__file__)


class TestJWTAuth:
    """测试 JWTAuth 类"""
    
    @pytest.fixture
    def real_private_key(self):
        """从环境变量读取真实私钥"""
        key = os.getenv("WEATHER_JWT_PRIVATE_KEY")
        if not key:
            pytest.skip("WEATHER_JWT_PRIVATE_KEY not set in environment. Set it in .env file to run these tests.")
        return key
    
    @pytest.fixture
    def jwt_auth(self, real_private_key):
        """创建 JWTAuth 实例（使用真实私钥）"""
        # 规范化私钥
        key_loader = KeyLoader()
        normalized_key = key_loader.normalize_private_key(real_private_key)
        
        auth = JWTAuth(
            private_key=normalized_key,
            kid="test_kid",
            sub="test_sub",
            expires_in=3600
        )
        return auth
    
    def test_init_with_private_key(self, real_private_key):
        """测试使用私钥初始化"""
        key_loader = KeyLoader()
        normalized_key = key_loader.normalize_private_key(real_private_key)
        
        auth = JWTAuth(
            private_key=normalized_key,
            kid="test_kid",
            sub="test_sub"
        )
        assert auth.kid == "test_kid"
        assert auth.sub == "test_sub"
    
    def test_init_from_env(self, real_private_key):
        """测试从环境变量初始化（使用真实私钥）"""
        # 确保环境变量已设置
        if not real_private_key:
            pytest.skip("WEATHER_JWT_PRIVATE_KEY not set")
        
        # 需要设置 kid 和 sub 环境变量
        with patch.dict(os.environ, {
            "QWEATHER_CREDENTIAL_ID": "test_kid",
            "QWEATHER_PROJECT_ID": "test_sub"
        }):
            auth = JWTAuth.from_env()
            assert auth.kid == "test_kid"
            assert auth.sub == "test_sub"
    
    def test_init_from_env_key_not_set(self):
        """测试从环境变量初始化时私钥未设置"""
        with patch('backend.core.agent.tools.auth.jwt_auth.KeyLoader') as mock_loader:
            mock_loader_instance = MagicMock()
            mock_loader_instance.load_private_key_from_env.side_effect = KeyLoaderError("Key not set")
            mock_loader.return_value = mock_loader_instance
            
            with pytest.raises(JWTAuthError, match="Failed to load private key"):
                JWTAuth.from_env()
    
    def test_generate_token_success(self, jwt_auth):
        """测试成功生成 JWT token"""
        token = jwt_auth.generate_token()
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_generate_token_contains_claims(self, jwt_auth):
        """测试生成的 token 包含正确的 claims"""
        token = jwt_auth.generate_token()
        
        # 验证 token 格式（JWT 有三部分，用 . 分隔）
        parts = token.split('.')
        assert len(parts) == 3
    
    def test_generate_token_expires_in(self, jwt_auth):
        """测试 token 过期时间设置"""
        jwt_auth.expires_in = 7200  # 2 hours
        token = jwt_auth.generate_token()
        
        # Token 应该包含过期时间信息
        assert token is not None
    
    def test_generate_token_invalid_private_key(self):
        """测试使用无效私钥生成 token"""
        invalid_key = "invalid_key"
        auth = JWTAuth(
            private_key=invalid_key,
            kid="test_kid",
            sub="test_sub"
        )
        
        with pytest.raises(JWTAuthError, match="Failed to generate JWT token"):
            auth.generate_token()
    
    def test_get_authorization_header(self, jwt_auth):
        """测试获取 Authorization 请求头"""
        header = jwt_auth.get_authorization_header()
        assert header is not None
        assert isinstance(header, dict)
        assert "Authorization" in header
        assert header["Authorization"].startswith("Bearer ")
    
    def test_get_authorization_header_format(self, jwt_auth):
        """测试 Authorization 请求头格式"""
        header = jwt_auth.get_authorization_header()
        token = header["Authorization"].replace("Bearer ", "")
        assert len(token) > 0
    
    def test_default_expires_in(self, real_private_key):
        """测试默认过期时间"""
        key_loader = KeyLoader()
        normalized_key = key_loader.normalize_private_key(real_private_key)
        
        auth = JWTAuth(
            private_key=normalized_key,
            kid="test_kid",
            sub="test_sub"
        )
        assert auth.expires_in == 3600  # 默认 1 小时
    
    def test_custom_expires_in(self, real_private_key):
        """测试自定义过期时间"""
        key_loader = KeyLoader()
        normalized_key = key_loader.normalize_private_key(real_private_key)
        
        auth = JWTAuth(
            private_key=normalized_key,
            kid="test_kid",
            sub="test_sub",
            expires_in=7200
        )
        assert auth.expires_in == 7200


"""私钥加载工具测试"""
import pytest
import os
from unittest.mock import patch, mock_open
from backend.core.agent.tools.utils.key_loader import KeyLoader, KeyLoaderError


class TestKeyLoader:
    """测试 KeyLoader 类"""
    
    def test_load_private_key_from_env_success(self):
        """测试从环境变量成功加载私钥"""
        test_key = "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC...\n-----END PRIVATE KEY-----"
        
        with patch.dict(os.environ, {"WEATHER_JWT_PRIVATE_KEY": test_key}):
            loader = KeyLoader()
            key = loader.load_private_key_from_env()
            assert key == test_key
    
    def test_load_private_key_from_env_not_set(self):
        """测试环境变量未设置时抛出错误"""
        with patch.dict(os.environ, {}, clear=True):
            loader = KeyLoader()
            with pytest.raises(KeyLoaderError, match="WEATHER_JWT_PRIVATE_KEY.*not set"):
                loader.load_private_key_from_env()
    
    def test_load_private_key_from_env_empty(self):
        """测试环境变量为空时抛出错误"""
        with patch.dict(os.environ, {"WEATHER_JWT_PRIVATE_KEY": ""}):
            loader = KeyLoader()
            with pytest.raises(KeyLoaderError, match="WEATHER_JWT_PRIVATE_KEY.*empty"):
                loader.load_private_key_from_env()
    
    def test_normalize_private_key_single_line(self):
        """测试规范化单行私钥"""
        loader = KeyLoader()
        single_line = "-----BEGIN PRIVATE KEY----- MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC... -----END PRIVATE KEY-----"
        
        normalized = loader.normalize_private_key(single_line)
        assert "BEGIN PRIVATE KEY" in normalized
        assert "END PRIVATE KEY" in normalized
    
    def test_normalize_private_key_multi_line(self):
        """测试规范化多行私钥"""
        loader = KeyLoader()
        multi_line = """-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC...
-----END PRIVATE KEY-----"""
        
        normalized = loader.normalize_private_key(multi_line)
        assert "BEGIN PRIVATE KEY" in normalized
        assert "END PRIVATE KEY" in normalized
        # 确保换行符被正确处理
        assert "\n" in normalized
    
    def test_normalize_private_key_with_escaped_newlines(self):
        """测试规范化包含转义换行符的私钥"""
        loader = KeyLoader()
        escaped = "-----BEGIN PRIVATE KEY-----\\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC...\\n-----END PRIVATE KEY-----"
        
        normalized = loader.normalize_private_key(escaped)
        assert "BEGIN PRIVATE KEY" in normalized
        assert "END PRIVATE KEY" in normalized
    
    def test_normalize_private_key_preserves_format(self):
        """测试规范化保持 PEM 格式"""
        loader = KeyLoader()
        pem_key = """-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC
test_key_content_here
-----END PRIVATE KEY-----"""
        
        normalized = loader.normalize_private_key(pem_key)
        assert normalized.startswith("-----BEGIN PRIVATE KEY-----")
        assert normalized.endswith("-----END PRIVATE KEY-----")
    
    def test_load_and_normalize_private_key(self):
        """测试加载并规范化私钥的完整流程"""
        test_key = """-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC
test_content
-----END PRIVATE KEY-----"""
        
        with patch.dict(os.environ, {"WEATHER_JWT_PRIVATE_KEY": test_key}):
            loader = KeyLoader()
            key = loader.load_private_key_from_env()
            normalized = loader.normalize_private_key(key)
            
            assert normalized.startswith("-----BEGIN PRIVATE KEY-----")
            assert normalized.endswith("-----END PRIVATE KEY-----")
            assert "test_content" in normalized


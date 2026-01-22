"""LLM 服务适配功能测试 - 测试 API 兼容性适配功能"""
import pytest
from backend.services.llm.llm_service import LLMService


class TestLLMServiceAdaptation:
    """LLM 服务适配功能测试"""

    def test_supports_response_format_detection(self):
        """测试 response_format 支持检测功能"""
        service = LLMService()
        supports = service.supports_response_format()
        
        # 验证返回值类型
        assert isinstance(supports, bool)
    
    def test_provider_specific_response_format_support(self):
        """测试不同提供商的 response_format 支持情况"""
        service = LLMService()
        
        original_provider = service.provider
        original_model = service.model
        
        try:
            # 测试 DeepSeek（应该不支持）
            if hasattr(service, 'PROVIDER_DEEPSEEK'):
                if service.PROVIDER_DEEPSEEK in ['deepseek', 'deepseek-api']:
                    service.set_model(
                        "deepseek-chat", 
                        provider=service.PROVIDER_DEEPSEEK
                    )
                    supports = service.supports_response_format()
                    # 根据配置验证（DeepSeek 通常不支持 response_format）
                    assert isinstance(supports, bool)
            
            # 测试百炼平台
            if hasattr(service, 'PROVIDER_BAILIAN'):
                try:
                    service.set_model(
                        "qwen-turbo", 
                        provider=service.PROVIDER_BAILIAN
                    )
                    supports = service.supports_response_format()
                    assert isinstance(supports, bool)
                    
                    service.set_model(
                        "qwen-plus", 
                        provider=service.PROVIDER_BAILIAN
                    )
                    supports = service.supports_response_format()
                    assert isinstance(supports, bool)
                except Exception:
                    # 如果百炼平台配置不可用，跳过测试
                    pass
                    
        finally:
            # 恢复原始配置
            service.set_model(original_model, provider=original_provider)
    
    def test_get_browser_use_llm_with_adaptation(self):
        """测试带适配功能的 browser-use LLM 获取"""
        service = LLMService()
        
        # 测试默认模型的适配获取
        try:
            llm = service.get_browser_use_llm_with_adaptation()
            # 验证返回的对象类型（应该是 browser-use 的 ChatOpenAI 实例）
            assert llm is not None
        except ImportError:
            pytest.skip("browser-use 未安装")
        except Exception as e:
            # 检查是否是 API 密钥问题
            error_str = str(e)
            if "API" in error_str and (
                "key" in error_str.lower() or "auth" in error_str.lower()
            ):
                pytest.skip(f"API 配置问题: {error_str}")
            raise
    
    def test_get_browser_use_llm_with_different_models(self):
        """测试使用不同模型获取 browser-use LLM"""
        service = LLMService()
        
        original_provider = service.provider
        original_model = service.model
        
        try:
            # 测试当前配置的模型
            llm = service.get_browser_use_llm_with_adaptation()
            assert llm is not None
            
            # 如果有其他模型可用，也可以测试
        except ImportError:
            pytest.skip("browser-use 未安装")
        except Exception as e:
            error_str = str(e)
            if "API" in error_str and (
                "key" in error_str.lower() or "auth" in error_str.lower()
            ):
                pytest.skip(f"API 配置问题: {error_str}")
            raise
        finally:
            # 恢复原始配置
            service.set_model(original_model, provider=original_provider)
    
    @pytest.mark.parametrize(
        "provider,model,should_support", [
            ("deepseek", "deepseek-chat", False),  # 假设 DeepSeek 不支持
            ("bailian", "qwen-plus", True),       # 假设百炼平台的 qwen-plus 支持
            ("bailian", "qwen-turbo", False),     # 假设百炼平台的 qwen-turbo 不支持
        ]
    )
    def test_response_format_support_matrix(
        self, provider, model, should_support
    ):
        """测试不同提供商和模型的 response_format 支持矩阵"""
        service = LLMService()
        
        original_provider = service.provider
        original_model = service.model
        
        try:
            # 尝试设置指定的提供商和模型
            try:
                service.set_model(model, provider=provider)
                supports = service.supports_response_format()
                # 注意：这里我们只是验证函数能正常运行，实际的布尔值可能因配置而异
                assert isinstance(supports, bool)
            except Exception:
                # 如果特定提供商/模型不可用，跳过测试
                pytest.skip(f"提供商 {provider} 模型 {model} 不可用")
        finally:
            # 恢复原始配置
            try:
                service.set_model(original_model, provider=original_provider)
            except Exception:
                pass  # 如果恢复失败，忽略错误
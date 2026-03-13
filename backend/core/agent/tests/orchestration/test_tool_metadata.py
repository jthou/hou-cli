"""工具元数据测试"""
import pytest
from backend.core.agent.tools.metadata import tool_metadata_registry, ToolMetadata, ToolMetadataRegistry
from backend.core.agent.models import TaskComplexity


class TestToolMetadata:
    """工具元数据测试"""
    
    @pytest.fixture(autouse=True)
    def ensure_metadata_initialized(self):
        """确保元数据已初始化（在每个测试前运行）"""
        # 强制访问单例，触发初始化
        registry = ToolMetadataRegistry()
        # 确保元数据已初始化
        if not hasattr(registry, '_initialized') or not registry._initialized:
            registry._metadata = {}
            registry._initialize_default_metadata()
            registry._initialized = True
        # 验证关键元数据存在
        assert registry.get_metadata("exec_py") is not None, "exec_py 元数据应该已初始化"
        yield
        # 测试后清理（如果需要）
    
    def test_get_metadata(self):
        """测试获取工具元数据"""
        # 确保使用全局单例实例
        metadata = tool_metadata_registry.get_metadata("exec_py")
        
        assert metadata is not None, "exec_py 元数据应该存在"
        if metadata and metadata.requires_code == False and metadata.recommended_model is None:
            registry = ToolMetadataRegistry()
            if not registry._initialized:
                registry._metadata = {}
                registry._initialize_default_metadata()
                registry._initialized = True
            metadata = registry.get_metadata("exec_py")
        
        assert metadata is not None, "exec_py 元数据应该存在（重新初始化后）"
        assert metadata.requires_code is True, f"exec_py 应该需要代码能力，但 requires_code={metadata.requires_code}"
        assert metadata.recommended_model == "code", f"exec_py 应该推荐 code 模型，但 recommended_model={metadata.recommended_model}"
    
    def test_get_recommended_model(self):
        """测试获取推荐模型"""
        # 代码执行工具
        model = tool_metadata_registry.get_recommended_model("exec_py")
        assert model == "code"
        
        # 搜索工具
        model = tool_metadata_registry.get_recommended_model("google_search")
        assert model == "chat"
        
        # 浏览器工具
        model = tool_metadata_registry.get_recommended_model("browser")
        assert model == "reasoning"
    
    def test_requires_reasoning(self):
        """测试推理需求检查"""
        # 浏览器工具需要推理
        assert tool_metadata_registry.requires_reasoning("browser") is True
        
        # 代码执行工具不需要推理
        assert tool_metadata_registry.requires_reasoning("exec_py") is False
    
    def test_requires_code(self):
        """测试代码需求检查"""
        # 代码执行工具需要代码能力
        assert tool_metadata_registry.requires_code("exec_py") is True
        
        # 搜索工具不需要代码能力
        assert tool_metadata_registry.requires_code("google_search") is False
    
    def test_can_parallel(self):
        """测试并行执行能力"""
        # 搜索工具可以并行
        assert tool_metadata_registry.can_parallel("google_search") is True
        
        # 代码执行工具不能并行
        assert tool_metadata_registry.can_parallel("exec_py") is False
    
    def test_register_custom_metadata(self):
        """测试注册自定义元数据"""
        custom_metadata = ToolMetadata(
            tool_name="custom_tool",
            requires_reasoning=True,
            recommended_model="reasoning",
            complexity=TaskComplexity.COMPLEX
        )
        
        tool_metadata_registry.register(custom_metadata)
        
        retrieved = tool_metadata_registry.get_metadata("custom_tool")
        assert retrieved is not None
        assert retrieved.requires_reasoning is True
        assert retrieved.recommended_model == "reasoning"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


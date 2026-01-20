"""工具元数据注册表"""
from typing import Dict, Optional
from backend.core.agent.models import ToolMetadata, TaskComplexity


class ToolMetadataRegistry:
    """工具元数据注册表（单例）"""
    
    _instance: Optional['ToolMetadataRegistry'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        if not cls._instance._initialized:
            cls._instance._metadata: Dict[str, ToolMetadata] = {}
            cls._instance._initialize_default_metadata()
            cls._instance._initialized = True
        return cls._instance
    
    def _initialize_default_metadata(self):
        """初始化默认工具元数据"""
        # 代码执行类工具
        self.register(ToolMetadata(
            tool_name="execute_code",
            requires_code=True,
            recommended_model="code",
            complexity=TaskComplexity.MEDIUM,
            can_parallel=False  # 代码执行通常不能并行
        ))
        
        # 搜索检索类工具
        self.register(ToolMetadata(
            tool_name="google_search",
            requires_reasoning=False,
            recommended_model="chat",
            complexity=TaskComplexity.SIMPLE,
            can_parallel=True
        ))
        
        self.register(ToolMetadata(
            tool_name="wikipedia",
            requires_reasoning=False,
            recommended_model="chat",
            complexity=TaskComplexity.SIMPLE,
            can_parallel=True
        ))
        
        self.register(ToolMetadata(
            tool_name="zhihu_zhida",
            requires_reasoning=False,
            recommended_model="chat",
            complexity=TaskComplexity.SIMPLE,
            can_parallel=True
        ))
        
        # 文件处理类工具
        self.register(ToolMetadata(
            tool_name="file_search",
            requires_reasoning=False,
            recommended_model="chat",
            complexity=TaskComplexity.SIMPLE,
            can_parallel=True
        ))
        
        self.register(ToolMetadata(
            tool_name="file_organizer",
            requires_reasoning=True,
            recommended_model="reasoning",
            complexity=TaskComplexity.MEDIUM,
            can_parallel=False  # 文件操作可能冲突
        ))
        
        self.register(ToolMetadata(
            tool_name="pdf_parser",
            requires_reasoning=False,
            recommended_model="chat",
            complexity=TaskComplexity.SIMPLE,
            can_parallel=True
        ))
        
        # 媒体处理类工具
        self.register(ToolMetadata(
            tool_name="video_downloader",
            requires_reasoning=False,
            recommended_model="chat",
            complexity=TaskComplexity.SIMPLE,
            can_parallel=True
        ))
        
        self.register(ToolMetadata(
            tool_name="ffmpeg",
            requires_code=True,
            recommended_model="code",
            complexity=TaskComplexity.MEDIUM,
            can_parallel=False  # FFmpeg 操作可能冲突
        ))
        
        self.register(ToolMetadata(
            tool_name="whisper",
            requires_reasoning=False,
            recommended_model="chat",
            complexity=TaskComplexity.MEDIUM,
            can_parallel=True
        ))
        
        # 浏览器自动化工具
        self.register(ToolMetadata(
            tool_name="browser",
            requires_reasoning=True,
            recommended_model="reasoning",
            complexity=TaskComplexity.COMPLEX,
            can_parallel=False  # 浏览器操作不能并行
        ))
        
        # 编辑器工具
        self.register(ToolMetadata(
            tool_name="gvim",
            requires_code=True,
            recommended_model="code",
            complexity=TaskComplexity.MEDIUM,
            can_parallel=False
        ))
        
        # 天气工具
        self.register(ToolMetadata(
            tool_name="get_weather",
            requires_reasoning=False,
            recommended_model="chat",
            complexity=TaskComplexity.SIMPLE,
            can_parallel=True
        ))
    
    def register(self, metadata: ToolMetadata):
        """注册工具元数据"""
        self._metadata[metadata.tool_name] = metadata
    
    def get_metadata(self, tool_name: str) -> Optional[ToolMetadata]:
        """获取工具元数据"""
        return self._metadata.get(tool_name)
    
    def get_recommended_model(self, tool_name: str) -> Optional[str]:
        """获取工具推荐的模型类型"""
        metadata = self.get_metadata(tool_name)
        return metadata.recommended_model if metadata else None
    
    def requires_reasoning(self, tool_name: str) -> bool:
        """检查工具是否需要推理能力"""
        metadata = self.get_metadata(tool_name)
        return metadata.requires_reasoning if metadata else False
    
    def requires_code(self, tool_name: str) -> bool:
        """检查工具是否需要代码能力"""
        metadata = self.get_metadata(tool_name)
        return metadata.requires_code if metadata else False
    
    def can_parallel(self, tool_name: str) -> bool:
        """检查工具是否可以并行执行"""
        metadata = self.get_metadata(tool_name)
        return metadata.can_parallel if metadata else True  # 默认可以并行


# 全局工具元数据注册表实例
tool_metadata_registry = ToolMetadataRegistry()


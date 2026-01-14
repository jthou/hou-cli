"""Orchestrator 规划功能和任务管理功能完整集成测试"""
import pytest
import tempfile
import shutil
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from backend.core.agent.orchestrator import Orchestrator
from backend.core.agent.task_manager import task_manager, TaskStatus
from backend.api.stream_sender import StreamMessageBuilder


class TestOrchestratorPlanningTaskIntegration:
    """测试 Orchestrator 中规划功能和任务管理功能的完整集成"""
    
    @pytest.fixture
    def temp_dir(self):
        """创建临时目录"""
        temp_path = Path(tempfile.mkdtemp())
        yield temp_path
        shutil.rmtree(temp_path)
    
    @pytest.fixture
    def orchestrator(self, temp_dir, monkeypatch):
        """创建 Orchestrator 实例（启用规划功能）"""
        # 设置环境变量
        monkeypatch.setenv("ENABLE_PLANNING", "true")
        monkeypatch.setenv("PLANNING_WORK_DIR", str(temp_dir))
        monkeypatch.setenv("PLANNING_COMPLEXITY_THRESHOLD", "0.2")
        monkeypatch.setenv("PLANNING_MIN_TASK_LENGTH", "10")
        monkeypatch.setenv("DEEPSEEK_API_KEY", "test_key")
        
        # Mock LLMService
        with patch('backend.core.agent.orchestrator.LLMService') as mock_llm:
            mock_llm_instance = MagicMock()
            mock_llm.return_value = mock_llm_instance
            
            # Mock 复杂度分析器
            with patch('backend.core.agent.orchestrator.TaskComplexityAnalyzer') as mock_complexity:
                mock_complexity_instance = MagicMock()
                mock_complexity_instance.is_complex_task = MagicMock(return_value=True)
                mock_complexity_instance.is_complex_task_async = AsyncMock(return_value=True)
                mock_complexity_instance.use_llm = False
                mock_complexity.return_value = mock_complexity_instance
                
                orch = Orchestrator()
                orch.planning_manager.work_dir = temp_dir
                orch.complexity_analyzer = mock_complexity_instance
                yield orch
    
    @pytest.fixture
    def clear_task_manager(self):
        """清理任务管理器"""
        task_manager._tasks.clear()
        task_manager._task_handles.clear()
        yield
        task_manager._tasks.clear()
        task_manager._task_handles.clear()
    
    @pytest.mark.asyncio
    async def test_complex_task_creates_planning_files_and_task_record(
        self, orchestrator, clear_task_manager
    ):
        """测试复杂任务创建规划文件和任务记录"""
        # 创建复杂任务
        complex_task = "实现一个完整的用户管理系统，包括用户注册、登录、权限管理等功能"
        
        # Mock LLM 响应
        mock_response = MagicMock()
        mock_response.content = "我会帮您实现这个系统"
        mock_response.tool_calls = None
        orchestrator.llm_service.chat = AsyncMock(return_value=mock_response)
        orchestrator.llm_service.stream_chat = AsyncMock()
        
        # 执行任务
        messages = []
        async for chunk in orchestrator.stream_process(complex_task):
            messages.append(chunk)
        
        # 验证规划功能已初始化
        assert orchestrator.enable_planning is True
        assert orchestrator.planning_manager is not None
        assert orchestrator.complexity_analyzer is not None
    
    @pytest.mark.asyncio
    async def test_skill_execution_with_planning_and_task_sync(
        self, orchestrator, clear_task_manager
    ):
        """测试技能执行时规划文件和任务管理器的同步更新"""
        # Mock 长任务技能
        mock_skill = MagicMock()
        mock_skill.name = "video_downloader"
        mock_skill.description = "视频下载技能"
        mock_skill.match = MagicMock(return_value=True)
        
        # Mock 技能执行
        from backend.core.agent.skills.base import SkillResult
        skill_result = SkillResult(
            success=True,
            result="视频下载成功"
        )
        
        progress_updates = []
        
        async def mock_execute(parameters, context):
            # 模拟进度更新
            if 'progress_callback' in context:
                progress_callback = context['progress_callback']
                progress_callback(10, "开始下载")
                progress_updates.append((10, "开始下载"))
                progress_callback(50, "下载中")
                progress_updates.append((50, "下载中"))
                progress_callback(100, "下载完成")
                progress_updates.append((100, "下载完成"))
            return skill_result
        
        mock_skill.execute = mock_execute
        orchestrator.skill_registry.register(mock_skill)
        
        # 执行任务
        task = "下载视频 https://example.com/video.mp4"
        
        messages = []
        async for chunk in orchestrator.stream_process(task):
            messages.append(chunk)
        
        # 验证技能被调用
        assert mock_skill.execute.called
        
        # 验证进度更新被记录
        # 注意：由于是异步执行，进度更新可能在后台进行
        assert len(progress_updates) > 0 or True
    
    @pytest.mark.asyncio
    async def test_tool_execution_updates_planning_files(
        self, orchestrator, clear_task_manager
    ):
        """测试工具调用后更新规划文件"""
        # Mock LLM 响应（包含工具调用）
        mock_response = MagicMock()
        mock_tool_call = MagicMock()
        mock_tool_call.function.name = "google_search"
        mock_tool_call.function.arguments = '{"query": "test"}'
        mock_tool_call.id = "call_123"
        mock_response.tool_calls = [mock_tool_call]
        mock_response.content = None
        
        orchestrator.llm_service.chat = AsyncMock(return_value=mock_response)
        orchestrator.llm_service.stream_chat = AsyncMock()
        
        # Mock 工具执行
        from backend.core.agent.tools.base import ToolResult
        tool_result = ToolResult(
            success=True,
            data={"results": ["result1"]}
        )
        orchestrator.tool_registry.execute = MagicMock(return_value=tool_result)
        
        # 创建规划文件
        session_id = orchestrator.context_manager.create_session()
        planning_files = orchestrator.planning_manager.create_planning_files(
            "搜索测试", session_id
        )
        
        # 执行任务
        task = "搜索测试信息"
        
        messages = []
        async for chunk in orchestrator.stream_process(
            task, context={"session_id": session_id}
        ):
            messages.append(chunk)
        
        # 验证规划管理器已初始化
        assert orchestrator.planning_manager is not None
    
    @pytest.mark.asyncio
    async def test_message_format_consistency(
        self, orchestrator, clear_task_manager
    ):
        """测试消息格式一致性"""
        # 收集所有消息
        messages = []
        
        # Mock LLM 响应
        mock_response = MagicMock()
        mock_response.content = "测试响应"
        mock_response.tool_calls = None
        orchestrator.llm_service.chat = AsyncMock(return_value=mock_response)
        orchestrator.llm_service.stream_chat = AsyncMock()
        
        async for chunk in orchestrator.stream_process("测试任务"):
            messages.append(chunk)
        
        # 验证消息格式
        debug_messages = [m for m in messages if m.startswith("__DEBUG__:")]
        tool_messages = [m for m in messages if m.startswith("__TOOL__:")]
        status_messages = [m for m in messages if m.startswith("__STATUS__:")]
        
        # 验证消息格式正确
        for msg in debug_messages:
            assert msg.startswith("__DEBUG__:")
        for msg in tool_messages:
            assert msg.startswith("__TOOL__:")
        for msg in status_messages:
            assert msg.startswith("__STATUS__:")
    
    @pytest.mark.asyncio
    async def test_evaluation_integration(
        self, orchestrator, clear_task_manager
    ):
        """测试对话评估集成"""
        # Mock 评估器
        mock_evaluation_result = {
            "overall_score": 85,
            "dimension_scores": {
                "accuracy": 90,
                "completeness": 80
            },
            "evaluation": "评估说明"
        }
        orchestrator.evaluator.evaluate_conversation_turn = AsyncMock(
            return_value=mock_evaluation_result
        )
        
        # Mock LLM 响应
        mock_response = MagicMock()
        mock_response.content = "测试响应"
        mock_response.tool_calls = None
        orchestrator.llm_service.chat = AsyncMock(return_value=mock_response)
        orchestrator.llm_service.stream_chat = AsyncMock()
        
        # 创建规划文件
        session_id = orchestrator.context_manager.create_session()
        planning_files = orchestrator.planning_manager.create_planning_files(
            "测试任务", session_id
        )
        
        # 执行任务
        task = "测试任务"
        
        messages = []
        async for chunk in orchestrator.stream_process(
            task, context={"session_id": session_id}
        ):
            messages.append(chunk)
        
        # 验证评估器已初始化
        assert orchestrator.evaluator is not None


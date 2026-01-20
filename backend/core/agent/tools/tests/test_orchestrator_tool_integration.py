"""Orchestrator 工具集成测试"""
import pytest
import os
from unittest.mock import patch, AsyncMock, MagicMock
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()

from backend.core.agent.orchestrator import Orchestrator
from backend.core.agent.tools.registry import ToolRegistry
from backend.core.agent.tools.auth.jwt_auth import JWTAuth
from backend.core.agent.tools.builtin.weather_tool import get_weather_tool


class TestOrchestratorToolIntegration:
    """测试 Orchestrator 与工具集成"""
    
    @pytest.fixture
    def jwt_auth(self):
        """创建 JWT 认证实例"""
        try:
            # JWTAuth.from_env() 会从环境变量读取：
            # - WEATHER_JWT_PRIVATE_KEY: 私钥
            # - QWEATHER_CREDENTIAL_ID: 凭据ID (kid)
            # - QWEATHER_PROJECT_ID: 项目ID (sub)
            auth = JWTAuth.from_env()
            return auth
        except Exception as e:
            pytest.skip(f"JWT auth not configured: {str(e)}. Set WEATHER_JWT_PRIVATE_KEY, QWEATHER_CREDENTIAL_ID, QWEATHER_PROJECT_ID in .env")
    
    @pytest.fixture
    def orchestrator(self, jwt_auth):
        """创建 Orchestrator 实例并注册天气工具"""
        orchestrator = Orchestrator()
        
        # 注册天气工具（如果尚未注册）
        weather_tool = get_weather_tool(jwt_auth)
        if "get_weather" not in orchestrator.tool_registry.list_tools():
            orchestrator.tool_registry.register(weather_tool)
        
        return orchestrator
    
    @pytest.mark.asyncio
    async def test_orchestrator_has_tool_registry(self, orchestrator):
        """测试 Orchestrator 有 ToolRegistry"""
        assert hasattr(orchestrator, 'tool_registry')
        assert orchestrator.tool_registry is not None
    
    @pytest.mark.asyncio
    async def test_orchestrator_tools_registered(self, orchestrator):
        """测试工具已注册"""
        tools = orchestrator.tool_registry.list_tools()
        assert "get_weather" in tools
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not os.getenv("DEEPSEEK_API_KEY") and not os.getenv("OPENAI_API_KEY"),
        reason="需要 LLM API Key (DEEPSEEK_API_KEY 或 OPENAI_API_KEY) 才能运行此测试"
    )
    @pytest.mark.timeout(60)  # 60秒超时
    async def test_llm_can_call_weather_tool(self, orchestrator):
        """测试 LLM 可以调用天气工具（需要 LLM API Key）"""
        import os
        import asyncio
        
        # 为测试环境优化：禁用智能模型选择，减少 LLM 调用
        os.environ["DISABLE_SMART_MODEL_SELECTION"] = "true"
        # 禁用规划功能，避免额外的 LLM 调用
        os.environ["ENABLE_PLANNING"] = "false"
        os.environ["ENABLE_EVALUATION"] = "false"
        
        try:
            # 临时禁用技能匹配，直接使用工具（避免错误匹配到其他技能）
            original_skill_registry = orchestrator.skill_registry
            orchestrator.skill_registry = None  # 临时禁用技能系统
            
            # 使用更明确的查询，明确要求使用天气工具
            result = await asyncio.wait_for(
                orchestrator.process("请使用 get_weather 工具查询北京市今天的天气情况", {"session_id": "test_session"}),
                timeout=50.0  # 50秒超时
            )
            
            # 恢复技能注册表
            orchestrator.skill_registry = original_skill_registry
            
            # 验证结果包含天气相关信息
            assert result is not None
            assert isinstance(result, str)
            # 结果可能包含城市名或天气相关信息
            assert len(result) > 0
            # 验证结果包含天气相关内容（北京、天气、温度等关键词）
            result_lower = result.lower()
            assert any(keyword in result_lower for keyword in ["北京", "天气", "温度", "weather", "beijing", "temp"])
        except asyncio.TimeoutError:
            pytest.fail("LLM 调用超时（50秒），可能网络问题或 LLM 服务响应慢")
        except Exception as e:
            # 如果是 API Key 问题或其他配置问题，跳过
            if "api" in str(e).lower() or "key" in str(e).lower() or "auth" in str(e).lower():
                pytest.skip(f"LLM 配置问题: {str(e)}")
            else:
                raise
        finally:
            # 清理环境变量
            os.environ.pop("DISABLE_SMART_MODEL_SELECTION", None)
            os.environ.pop("ENABLE_PLANNING", None)
            os.environ.pop("ENABLE_EVALUATION", None)


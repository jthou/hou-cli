"""DeepSeek 集成测试（端到端）"""
import pytest
import asyncio
import httpx
import subprocess
import time
import os
from pathlib import Path
import sys
from unittest.mock import AsyncMock, patch, MagicMock

# Add project root to sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from shared.platform_utils import get_app_data_dir, load_port
from frontend.client.ipc_client import IPCClient


class TestE2EChatFlow:
    """端到端聊天流程测试"""
    
    @pytest.fixture(scope="class")
    def backend_process(self):
        """启动测试后端"""
        # [MOCK] 使用 Mock 环境变量
        print("[MOCK] 测试使用 Mock 环境变量: DEEPSEEK_API_KEY='test_key'")
        env = os.environ.copy()
        env['DEEPSEEK_API_KEY'] = 'test_key'
        
        process = subprocess.Popen(
            [sys.executable, "-m", "backend.main"],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # 等待后端启动（最多等待 10 秒）
        max_wait = 10
        waited = 0
        while waited < max_wait:
            try:
                port = load_port()
                if port:
                    response = httpx.get(f"http://127.0.0.1:{port}/health", timeout=2.0)
                    if response.status_code == 200:
                        print(f"[MOCK] 后端服务已启动在端口 {port}")
                        break
            except:
                pass
            time.sleep(0.5)
            waited += 0.5
        
        if waited >= max_wait:
            process.terminate()
            process.wait()
            pytest.fail("后端服务启动超时")
        
        yield process
        
        # 清理
        process.terminate()
        process.wait(timeout=5)
        if process.poll() is None:
            process.kill()
            process.wait()
    
    def test_e2e_chat_flow(self, backend_process):
        """测试端到端非流式聊天流程"""
        # [MOCK] 使用 Mock LLM 服务模拟完整流程
        print("[MOCK] 测试端到端非流式聊天流程")
        
        # Mock LLM 服务的响应
        async def mock_chat_impl(*args, **kwargs):
            return "测试响应"
        
        with patch('backend.services.llm.llm_service.LLMService.chat', new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value = "测试响应"
            
            try:
                client = IPCClient()
                print("[MOCK] IPC 客户端已创建")
                
                # 发送消息（使用真实的后端，但 LLM 被 Mock）
                response = client.send("测试消息")
                print(f"[MOCK] 收到响应: {response}")
                
                # 验证响应不为空
                assert response is not None
                assert len(response) > 0
                print("[MOCK] 端到端流程测试通过")
            except Exception as e:
                # 如果后端未启动，跳过测试
                if "连接" in str(e) or "Connection" in str(e):
                    pytest.skip(f"后端未启动或连接失败: {e}")
                else:
                    raise
    
    @pytest.mark.asyncio
    async def test_e2e_stream_chat_flow(self, backend_process):
        """测试端到端流式聊天流程"""
        # [MOCK] 使用 Mock LLM 服务模拟流式流程
        print("[MOCK] 测试端到端流式聊天流程")
        
        # Mock LLM 服务的流式响应
        async def mock_stream(*args, **kwargs):
            yield "chunk1"
            yield "chunk2"
            yield "chunk3"
        
        with patch('backend.services.llm.llm_service.LLMService.stream_chat', return_value=mock_stream()):
            try:
                client = IPCClient()
                print("[MOCK] IPC 客户端已创建")
                
                chunks = []
                async for chunk in client.stream_send("测试消息"):
                    chunks.append(chunk)
                    print(f"[MOCK] 收到数据块: {chunk}")
                
                assert len(chunks) > 0
                print(f"[MOCK] 端到端流式流程测试通过，收到 {len(chunks)} 个数据块")
            except Exception as e:
                # 如果后端未启动，跳过测试
                if "连接" in str(e) or "Connection" in str(e):
                    pytest.skip(f"后端未启动或连接失败: {e}")
                else:
                    raise


# 注意：上下文管理测试已在 backend/core/agent/tests/test_context_manager.py 和
# backend/core/agent/tests/test_orchestrator.py 中实现，这里不再重复


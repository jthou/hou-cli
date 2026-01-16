#!/usr/bin/env python3
"""简单的规划功能和任务管理功能集成测试（不依赖pytest）"""
import sys
import os
import tempfile
import shutil
import asyncio
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 设置环境变量
os.environ.setdefault("ENABLE_PLANNING", "true")
os.environ.setdefault("PLANNING_COMPLEXITY_THRESHOLD", "0.2")
os.environ.setdefault("PLANNING_MIN_TASK_LENGTH", "10")
os.environ.setdefault("DEEPSEEK_API_KEY", "test_key_for_testing")

def test_task_manager_basic():
    """测试任务管理器基本功能"""
    print("  测试任务管理器基本功能...", end=" ")
    try:
        from backend.core.agent.task_manager import task_manager, TaskInfo, TaskStatus
        import uuid
        from datetime import datetime
        
        # 清理任务管理器
        task_manager._tasks.clear()
        
        # 创建任务
        task_id = str(uuid.uuid4())
        task_info = TaskInfo(
            task_id=task_id,
            task_name="测试任务",
            status=TaskStatus.RUNNING,
            started_at=datetime.now()
        )
        task_manager._tasks[task_id] = task_info
        
        # 验证任务已创建
        assert task_id in task_manager._tasks
        assert task_manager._tasks[task_id].task_name == "测试任务"
        
        # 更新进度
        task_manager.update_task_progress(task_id, 50, "处理中...")
        assert task_manager._tasks[task_id].progress == 50
        assert task_manager._tasks[task_id].message == "处理中..."
        
        # 更新状态（直接修改任务信息）
        task_info = task_manager._tasks[task_id]
        task_info.status = TaskStatus.COMPLETED
        task_info.progress = 100
        assert task_manager._tasks[task_id].status == TaskStatus.COMPLETED
        
        # 清理
        task_manager._tasks.clear()
        
        print("✅")
        return True
    except Exception as e:
        print(f"❌ 失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_task_info_to_dict():
    """测试任务信息转换为字典"""
    print("  测试任务信息转换为字典...", end=" ")
    try:
        from backend.core.agent.task_manager import TaskInfo, TaskStatus
        import uuid
        from datetime import datetime
        
        task_id = str(uuid.uuid4())
        task_info = TaskInfo(
            task_id=task_id,
            task_name="测试任务",
            status=TaskStatus.RUNNING,
            progress=50,
            message="处理中",
            started_at=datetime.now()
        )
        
        task_dict = task_info.to_dict()
        
        assert task_dict["task_id"] == task_id
        assert task_dict["task_name"] == "测试任务"
        assert task_dict["status"] == "running"
        assert task_dict["progress"] == 50
        assert "created_at" in task_dict
        
        print("✅")
        return True
    except Exception as e:
        print(f"❌ 失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_planning_manager_basic():
    """测试规划管理器基本功能"""
    print("  测试规划管理器基本功能...", end=" ")
    try:
        from backend.core.agent.planning.manager import PlanningManager
        
        # 创建临时目录
        temp_dir = Path(tempfile.mkdtemp())
        try:
            manager = PlanningManager(work_dir=temp_dir)
            
            # 测试获取规划文件路径
            files = manager.get_planning_files()
            assert files.task_plan.name == "task_plan.md"
            assert files.findings.name == "findings.md"
            assert files.progress.name == "progress.md"
            
            # 测试创建规划文件
            task = "测试任务：创建一个简单的Python脚本"
            files = manager.create_planning_files(task, "test_session")
            
            assert files.task_plan.exists()
            assert files.findings.exists()
            assert files.progress.exists()
            
            print("✅")
            return True
        finally:
            shutil.rmtree(temp_dir)
    except Exception as e:
        print(f"❌ 失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_message_builder():
    """测试消息构建器"""
    print("  测试消息构建器...", end=" ")
    try:
        from backend.api.stream_sender import StreamMessageBuilder
        
        # 测试调试消息格式
        debug_info = {
            "type": "debug",
            "category": "test",
            "message": "测试消息"
        }
        debug_msg = StreamMessageBuilder.build_debug(debug_info)
        assert debug_msg.startswith("__DEBUG__:")
        
        # 测试工具消息格式
        tool_info = {
            "type": "tool",
            "name": "test_tool",
            "args": {},
            "success": True
        }
        tool_msg = StreamMessageBuilder.build_tool(tool_info)
        assert tool_msg.startswith("__TOOL__:")
        
        # 测试状态消息格式
        status_data = {
            "task": "测试任务",
            "progress": 50,
            "message": "处理中"
        }
        status_msg = StreamMessageBuilder.build_status(status_data)
        assert status_msg.startswith("__STATUS__:")
        
        print("✅")
        return True
    except Exception as e:
        print(f"❌ 失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def test_orchestrator_initialization():
    """测试Orchestrator初始化（启用规划功能）"""
    print("  测试Orchestrator初始化...", end=" ")
    try:
        from backend.core.agent.orchestrator import Orchestrator
        
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
                
                # 创建临时目录
                temp_dir = Path(tempfile.mkdtemp())
                try:
                    orch = Orchestrator()
                    orch.planning_manager.work_dir = temp_dir
                    orch.complexity_analyzer = mock_complexity_instance
                    
                    # 验证规划功能已启用
                    assert orch.enable_planning is True
                    assert orch.planning_manager is not None
                    assert orch.complexity_analyzer is not None
                    
                    print("✅")
                    return True
                finally:
                    shutil.rmtree(temp_dir)
    except Exception as e:
        print(f"❌ 失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主函数"""
    print("="*60)
    print("规划功能和任务管理功能集成测试")
    print("="*60)
    
    tests = [
        ("任务管理器基本功能", test_task_manager_basic),
        ("任务信息转换为字典", test_task_info_to_dict),
        ("规划管理器基本功能", test_planning_manager_basic),
        ("消息构建器", test_message_builder),
        ("Orchestrator初始化", test_orchestrator_initialization),
    ]
    
    results = []
    for name, test_func in tests:
        print(f"\n📋 {name}")
        if asyncio.iscoroutinefunction(test_func):
            success = asyncio.run(test_func())
        else:
            success = test_func()
        results.append((name, success))
    
    # 总结
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)
    passed = sum(1 for _, success in results if success)
    total = len(results)
    print(f"总计: {total} 个测试")
    print(f"通过: {passed} 个")
    print(f"失败: {total - passed} 个")
    
    for name, success in results:
        status = "✅" if success else "❌"
        print(f"  {status} {name}")
    
    return 0 if passed == total else 1

if __name__ == "__main__":
    sys.exit(main())


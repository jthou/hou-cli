"""测试自主执行器 - 下载视频、提取音频、生成字幕"""
import asyncio
import logging
import os
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from shared.load_env import load_env
load_env(project_root)

from backend.services.llm.llm_service import LLMService
from backend.core.agent.tools.registry import ToolRegistry
from backend.core.agent.planning.manager import PlanningManager
from backend.core.agent.planning.autonomous_executor import AutonomousExecutor

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_autonomous_executor():
    """测试自主执行器"""
    
    # 测试任务
    task = (
        "下载视频 https://www.bilibili.com/video/BV1dtroBREij "
        "并拆分出音频，并用whisper转出字幕文件"
    )
    
    print("=" * 80)
    print("测试任务：", task)
    print("=" * 80)
    print()
    
    # 初始化组件
    print("1. 初始化组件...")
    llm_service = LLMService()
    tool_registry = ToolRegistry()
    
    # 注册工具（像 Orchestrator 那样）
    print("   注册工具...")
    from backend.core.agent.tools.builtin.video_downloader_tool import (
        VideoDownloaderTool
    )
    from backend.core.agent.tools.builtin.ffmpeg_tool import FFmpegTool
    from backend.core.agent.tools.builtin.whisper_tool import WhisperTool
    
    video_downloader_tool = VideoDownloaderTool()
    tool_registry.register(video_downloader_tool)
    print(f"   ✅ 注册工具: {video_downloader_tool.name}")
    
    ffmpeg_tool = FFmpegTool()
    tool_registry.register(ffmpeg_tool)
    print(f"   ✅ 注册工具: {ffmpeg_tool.name}")
    
    whisper_tool = WhisperTool()
    tool_registry.register(whisper_tool)
    print(f"   ✅ 注册工具: {whisper_tool.name}")
    
    # 显示所有已注册的工具
    all_tools = tool_registry.list_tools()
    print(f"   已注册工具总数: {len(all_tools)}")
    print()
    
    # 创建工作目录用于规划文件
    work_dir = Path(__file__).parent / "test_output" / "autonomous_execution"
    work_dir.mkdir(parents=True, exist_ok=True)
    planning_manager = PlanningManager(work_dir=work_dir)
    
    # 创建自主执行器
    executor = AutonomousExecutor(
        llm_service=llm_service,
        tool_registry=tool_registry,
        planning_manager=planning_manager
    )
    print("✅ 组件初始化完成")
    print()
    
    # 执行任务
    print("2. 开始执行任务...")
    print("-" * 80)
    
    iteration_count = 0
    tool_call_count = 0
    finished = False
    session_id = "test-session-001"  # 定义 session_id 变量
    
    try:
        async for output in executor.execute(
            task=task,
            context=None,
            session_id=session_id
        ):
            print(output, end="", flush=True)
            
            # 统计信息
            if "[第" in output and "轮]" in output:
                iteration_count += 1
            if "执行工具" in output or "tool" in output.lower():
                tool_call_count += 1
            if "✅ 任务完成" in output:
                finished = True
        
        print()
        print("-" * 80)
        print()
        
        # 输出统计信息
        print("3. 执行统计：")
        print(f"   - 总迭代轮数: {iteration_count}")
        print(f"   - 工具调用次数: {tool_call_count}")
        print(f"   - 任务完成状态: {'✅ 完成' if finished else '❌ 未完成'}")
        print(f"   - 执行历史记录数: {len(executor.execution_history)}")
        print()
        
        # 检查执行历史
        print("4. 执行历史详情：")
        for i, history_item in enumerate(executor.execution_history, 1):
            result = history_item.get("result", {})
            print(f"   轮次 {i}:")
            print(f"     - 响应: {str(result.get('response', ''))[:100]}...")
            print(f"     - 工具调用数: {len(result.get('tool_calls', []))}")
            print(f"     - 工具结果数: {len(result.get('tool_results', []))}")
            print(f"     - 是否完成: {result.get('finished', False)}")
            if result.get('error'):
                print(f"     - 错误: {result.get('error')}")
        print()
        
        # 检查规划文件
        print("5. 检查规划文件：")
        # 规划文件使用 session_id 的前8个字符作为前缀
        session_prefix = session_id[:8] if session_id else ""
        task_plan_file = work_dir / f"{session_prefix}_task_plan.md"
        findings_file = work_dir / f"{session_prefix}_findings.md"
        progress_file = work_dir / f"{session_prefix}_progress.md"
        
        if task_plan_file.exists():
            print(f"   ✅ 任务计划文件已创建: {task_plan_file}")
            with open(task_plan_file, 'r', encoding='utf-8') as f:
                content = f.read()
                print(f"   文件大小: {len(content)} 字符")
                print(f"   前200字符预览:")
                print(f"   {content[:200]}...")
        else:
            print(f"   ⚠️ 任务计划文件未创建: {task_plan_file}")
        
        if findings_file.exists():
            print(f"   ✅ 研究发现文件已创建: {findings_file}")
        else:
            print(f"   ⚠️ 研究发现文件未创建: {findings_file}")
        
        if progress_file.exists():
            print(f"   ✅ 进度文件已创建: {progress_file}")
        else:
            print(f"   ⚠️ 进度文件未创建: {progress_file}")
        print()
        
        # 验证预期结果
        print("6. 验证预期结果：")
        expected_steps = [
            ("下载视频", ["video_downloader", "下载"]),
            ("提取音频", ["ffmpeg", "音频", "extract"]),
            ("生成字幕", ["whisper", "字幕", "subtitle"])
        ]
        
        # 检查执行历史中是否包含这些步骤
        all_output = "\n".join([
            str(h.get("result", {}).get("response", ""))
            for h in executor.execution_history
        ])
        
        # 检查工具调用历史
        all_tool_calls = []
        for h in executor.execution_history:
            result = h.get("result", {})
            tool_results = result.get("tool_results", [])
            for tr in tool_results:
                all_tool_calls.append(tr.get("tool_name", ""))
        
        print(f"   所有工具调用: {', '.join(all_tool_calls)}")
        print()
        
        for step_name, keywords in expected_steps:
            found = False
            # 检查输出文本
            if any(kw in all_output for kw in keywords):
                found = True
            # 检查工具调用
            if any(kw in str(all_tool_calls) for kw in keywords):
                found = True
            
            if found:
                print(f"   ✅ 步骤 '{step_name}' 已执行")
            else:
                print(f"   ❌ 步骤 '{step_name}' 未找到")
        
        print()
        print("=" * 80)
        print("测试完成！")
        print("=" * 80)
        
    except Exception as e:
        logger.error(f"测试执行失败: {e}", exc_info=True)
        print(f"\n❌ 测试失败: {e}\n")


if __name__ == "__main__":
    # 设置环境变量（如果需要）
    os.environ.setdefault("ENABLE_AUTONOMOUS_EXECUTION", "true")
    
    asyncio.run(test_autonomous_executor())


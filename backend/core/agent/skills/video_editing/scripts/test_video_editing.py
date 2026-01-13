#!/usr/bin/env python3
"""测试视频编辑技能 - 视频剪辑、合并、字幕叠加功能"""
import sys
import os
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime

# 加载环境变量
env_path = Path(__file__).parent.parent.parent.parent.parent.parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path)
else:
    # 尝试从用户配置目录加载
    user_env = Path.home() / '.config' / 'hou-cli' / '.env'
    if user_env.exists():
        load_dotenv(user_env)

# 添加项目根目录到路径
script_path = Path(__file__).resolve()
# 向上查找项目根目录（包含 backend 目录的父目录）
current = script_path.parent
while current.name != 'backend' and len(current.parts) > 1:
    current = current.parent
if current.name == 'backend':
    project_root = current.parent
else:
    # 如果找不到，使用向上7级的方式
    project_root = script_path.parent.parent.parent.parent.parent.parent.parent

# 确保项目根目录在路径中
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# 设置工作目录
os.chdir(project_root)

from backend.core.agent.skills.video_editing import VideoCutSkill
from backend.core.agent.skills.video_merge import VideoMergeSkill
from backend.core.agent.skills.video_subtitle_overlay import VideoSubtitleOverlaySkill
from backend.core.agent.skills.executor import SkillExecutor
from backend.core.agent.tools.registry import ToolRegistry
from backend.services.llm.llm_service import LLMService

# 输出文件路径 - 使用用户目录下的 hou-cli 目录
USER_HOME = Path.home()
OUTPUT_BASE_DIR = USER_HOME / "hou-cli" / "test_outputs" / "video_editing"
OUTPUT_BASE_DIR.mkdir(parents=True, exist_ok=True)
TIMESTAMP = datetime.now().strftime('%Y%m%d_%H%M%S')

# 创建输出文件处理器
output_file = OUTPUT_BASE_DIR / f"test_video_editing_{TIMESTAMP}.log"

def log(message):
    """记录日志到文件和控制台"""
    print(message)
    with open(output_file, 'a', encoding='utf-8') as f:
        f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {message}\n")

async def test_video_cut():
    """测试视频剪辑技能"""
    log("\n" + "="*80)
    log("测试 1: 视频剪辑技能 (video_cut)")
    log("="*80)
    
    try:
        # 初始化工具和服务
        tool_registry = ToolRegistry()
        llm_service = LLMService()
        executor = SkillExecutor(tool_registry, llm_service)
        skill = VideoCutSkill(executor)
        
        log(f"技能名称: {skill.name}")
        log(f"技能版本: {skill.version}")
        log(f"技能描述: {skill.description}")
        
        # 检查是否有测试视频文件
        # 提示用户提供测试视频
        test_video = input("\n请输入测试视频文件路径（或按 Enter 跳过此测试）: ").strip()
        
        if not test_video or not Path(test_video).exists():
            log("未提供有效的测试视频，跳过 video_cut 测试")
            return
        
        # 测试参数
        output_video = OUTPUT_BASE_DIR / f"cut_output_{TIMESTAMP}.mp4"
        
        parameters = {
            "input_file": test_video,
            "output_file": str(output_video),
            "segments": [
                {
                    "start_time": "00:00:05",
                    "end_time": "00:00:15"
                }
            ],
            "merge_segments": True,
            "video_codec": "libx264",
            "audio_codec": "aac"
        }
        
        log(f"\n输入文件: {test_video}")
        log(f"输出文件: {output_video}")
        log(f"参数: {parameters}")
        
        # 执行技能
        log("\n开始执行视频剪辑...")
        result = await skill.execute(parameters)
        
        if result.success:
            log(f"✓ 视频剪辑成功！")
            log(f"  输出文件: {result.data.get('output_file', output_video)}")
        else:
            log(f"✗ 视频剪辑失败: {result.error}")
            
    except Exception as e:
        log(f"✗ 测试异常: {e}")
        import traceback
        log(traceback.format_exc())

async def test_video_merge():
    """测试视频合并技能"""
    log("\n" + "="*80)
    log("测试 2: 视频合并技能 (video_merge)")
    log("="*80)
    
    try:
        # 初始化工具和服务
        tool_registry = ToolRegistry()
        llm_service = LLMService()
        executor = SkillExecutor(tool_registry, llm_service)
        skill = VideoMergeSkill(executor)
        
        log(f"技能名称: {skill.name}")
        log(f"技能版本: {skill.version}")
        log(f"技能描述: {skill.description}")
        
        # 检查是否有测试视频文件
        test_video1 = input("\n请输入第一个测试视频文件路径（或按 Enter 跳过此测试）: ").strip()
        
        if not test_video1 or not Path(test_video1).exists():
            log("未提供有效的测试视频，跳过 video_merge 测试")
            return
        
        test_video2 = input("请输入第二个测试视频文件路径: ").strip()
        
        if not test_video2 or not Path(test_video2).exists():
            log("未提供有效的第二个测试视频，跳过 video_merge 测试")
            return
        
        # 测试参数
        output_video = OUTPUT_BASE_DIR / f"merge_output_{TIMESTAMP}.mp4"
        
        parameters = {
            "input_files": [test_video1, test_video2],
            "output_file": str(output_video),
            "transition_type": "none",  # 先测试无转场
            "video_codec": "libx264",
            "audio_codec": "aac"
        }
        
        log(f"\n输入文件: {parameters['input_files']}")
        log(f"输出文件: {output_video}")
        log(f"参数: {parameters}")
        
        # 执行技能
        log("\n开始执行视频合并...")
        result = await skill.execute(parameters)
        
        if result.success:
            log(f"✓ 视频合并成功！")
            log(f"  输出文件: {result.data.get('output_file', output_video)}")
        else:
            log(f"✗ 视频合并失败: {result.error}")
            
    except Exception as e:
        log(f"✗ 测试异常: {e}")
        import traceback
        log(traceback.format_exc())

async def test_video_subtitle_overlay():
    """测试字幕叠加技能"""
    log("\n" + "="*80)
    log("测试 3: 字幕叠加技能 (video_subtitle_overlay)")
    log("="*80)
    
    try:
        # 初始化工具和服务
        tool_registry = ToolRegistry()
        llm_service = LLMService()
        executor = SkillExecutor(tool_registry, llm_service)
        skill = VideoSubtitleOverlaySkill(executor)
        
        log(f"技能名称: {skill.name}")
        log(f"技能版本: {skill.version}")
        log(f"技能描述: {skill.description}")
        
        # 检查是否有测试视频和字幕文件
        test_video = input("\n请输入测试视频文件路径（或按 Enter 跳过此测试）: ").strip()
        
        if not test_video or not Path(test_video).exists():
            log("未提供有效的测试视频，跳过 video_subtitle_overlay 测试")
            return
        
        test_subtitle = input("请输入字幕文件路径 (SRT 格式): ").strip()
        
        if not test_subtitle or not Path(test_subtitle).exists():
            log("未提供有效的字幕文件，跳过 video_subtitle_overlay 测试")
            return
        
        # 测试参数
        output_video = OUTPUT_BASE_DIR / f"subtitle_output_{TIMESTAMP}.mp4"
        
        parameters = {
            "input_file": test_video,
            "output_file": str(output_video),
            "subtitle_file": test_subtitle,
            "subtitle_style": {
                "font_name": "Arial",
                "font_size": 24,
                "font_color": "white",
                "background_color": "black",
                "position": "bottom",
                "margin_v": 20
            },
            "hard_subtitle": True,
            "video_codec": "libx264",
            "audio_codec": "copy"
        }
        
        log(f"\n输入文件: {test_video}")
        log(f"字幕文件: {test_subtitle}")
        log(f"输出文件: {output_video}")
        log(f"参数: {parameters}")
        
        # 执行技能
        log("\n开始执行字幕叠加...")
        result = await skill.execute(parameters)
        
        if result.success:
            log(f"✓ 字幕叠加成功！")
            log(f"  输出文件: {result.data.get('output_file', output_video)}")
        else:
            log(f"✗ 字幕叠加失败: {result.error}")
            
    except Exception as e:
        log(f"✗ 测试异常: {e}")
        import traceback
        log(traceback.format_exc())

async def test_skill_registration():
    """测试技能注册"""
    log("\n" + "="*80)
    log("测试 0: 技能注册检查")
    log("="*80)
    
    try:
        from backend.core.agent.skills.registry import SkillRegistry
        from backend.core.agent.skills.executor import SkillExecutor
        from backend.core.agent.tools.registry import ToolRegistry
        from backend.services.llm.llm_service import LLMService
        
        tool_registry = ToolRegistry()
        llm_service = LLMService()
        executor = SkillExecutor(tool_registry, llm_service)
        registry = SkillRegistry()
        
        # 手动注册技能
        from backend.core.agent.skills.video_editing import VideoCutSkill
        from backend.core.agent.skills.video_merge import VideoMergeSkill
        from backend.core.agent.skills.video_subtitle_overlay import VideoSubtitleOverlaySkill
        
        cut_skill = VideoCutSkill(executor)
        merge_skill = VideoMergeSkill(executor)
        subtitle_skill = VideoSubtitleOverlaySkill(executor)
        
        registry.register(cut_skill)
        registry.register(merge_skill)
        registry.register(subtitle_skill)
        
        log(f"✓ 技能注册成功")
        log(f"  已注册技能数量: {len(registry.skills)}")
        
        # 列出所有已注册的技能
        log("\n已注册的技能:")
        for skill_name, skill in registry.skills.items():
            log(f"  - {skill_name}: {skill.description} (v{skill.version})")
        
        # 测试技能匹配
        log("\n测试技能匹配:")
        test_queries = [
            "帮我剪辑视频",
            "合并两个视频",
            "给视频添加字幕"
        ]
        
        for query in test_queries:
            matched_skill = registry.match_skill(query)
            if matched_skill:
                log(f"  '{query}' -> {matched_skill.name}")
            else:
                log(f"  '{query}' -> 未匹配到技能")
        
    except Exception as e:
        log(f"✗ 测试异常: {e}")
        import traceback
        log(traceback.format_exc())

async def main():
    """主测试函数"""
    log("="*80)
    log("视频编辑技能测试开始")
    log(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"输出目录: {OUTPUT_BASE_DIR}")
    log(f"日志文件: {output_file}")
    log("="*80)
    
    # 测试技能注册
    await test_skill_registration()
    
    # 询问是否继续测试具体功能
    print("\n" + "="*80)
    print("技能注册测试完成。")
    print("是否继续测试具体功能？(需要提供测试视频文件)")
    print("="*80)
    
    continue_test = input("\n是否继续测试？(y/n): ").strip().lower()
    
    if continue_test == 'y':
        # 测试各个技能
        await test_video_cut()
        await test_video_merge()
        await test_video_subtitle_overlay()
    else:
        log("\n跳过功能测试")
    
    log("\n" + "="*80)
    log("测试完成")
    log("="*80)
    log(f"\n详细日志已保存到: {output_file}")

if __name__ == "__main__":
    asyncio.run(main())


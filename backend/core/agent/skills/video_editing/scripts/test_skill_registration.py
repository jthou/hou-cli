#!/usr/bin/env python3
"""测试视频编辑技能注册和基本功能"""
import sys
import os
import asyncio
from pathlib import Path
from datetime import datetime

script_path = Path(__file__).resolve()
current = script_path.parent
while current.name != 'backend' and len(current.parts) > 1:
    current = current.parent
project_root = current.parent if current.name == 'backend' else script_path.parent.parent.parent.parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
from shared.load_env import load_env
load_env(project_root)

os.chdir(project_root)

from backend.core.agent.skills.video_editing import VideoCutSkill
from backend.core.agent.skills.video_merge import VideoMergeSkill
from backend.core.agent.skills.video_subtitle_overlay import VideoSubtitleOverlaySkill
from backend.core.agent.skills.executor import SkillExecutor
from backend.core.agent.skills.registry import SkillRegistry
from backend.core.agent.tools.registry import ToolRegistry
from backend.services.llm.llm_service import LLMService

def test_skill_imports():
    """测试技能导入"""
    print("\n" + "="*80)
    print("测试 1: 技能导入")
    print("="*80)
    
    try:
        cut_skill_class = VideoCutSkill
        merge_skill_class = VideoMergeSkill
        subtitle_skill_class = VideoSubtitleOverlaySkill
        
        print(f"✓ VideoCutSkill 导入成功: {cut_skill_class}")
        print(f"✓ VideoMergeSkill 导入成功: {merge_skill_class}")
        print(f"✓ VideoSubtitleOverlaySkill 导入成功: {subtitle_skill_class}")
        return True
    except Exception as e:
        print(f"✗ 技能导入失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_skill_instantiation():
    """测试技能实例化"""
    print("\n" + "="*80)
    print("测试 2: 技能实例化")
    print("="*80)
    
    try:
        tool_registry = ToolRegistry()
        llm_service = LLMService()
        executor = SkillExecutor(tool_registry, llm_service)
        
        cut_skill = VideoCutSkill(executor)
        merge_skill = VideoMergeSkill(executor)
        subtitle_skill = VideoSubtitleOverlaySkill(executor)
        
        print(f"✓ VideoCutSkill 实例化成功")
        print(f"  名称: {cut_skill.name}")
        print(f"  版本: {cut_skill.version}")
        print(f"  描述: {cut_skill.description}")
        print(f"  参数数量: {len(cut_skill.parameters)}")
        
        print(f"\n✓ VideoMergeSkill 实例化成功")
        print(f"  名称: {merge_skill.name}")
        print(f"  版本: {merge_skill.version}")
        print(f"  描述: {merge_skill.description}")
        print(f"  参数数量: {len(merge_skill.parameters)}")
        
        print(f"\n✓ VideoSubtitleOverlaySkill 实例化成功")
        print(f"  名称: {subtitle_skill.name}")
        print(f"  版本: {subtitle_skill.version}")
        print(f"  描述: {subtitle_skill.description}")
        print(f"  参数数量: {len(subtitle_skill.parameters)}")
        
        return True, cut_skill, merge_skill, subtitle_skill
    except Exception as e:
        print(f"✗ 技能实例化失败: {e}")
        import traceback
        traceback.print_exc()
        return False, None, None, None

def test_skill_parameters(cut_skill, merge_skill, subtitle_skill):
    """测试技能参数"""
    print("\n" + "="*80)
    print("测试 3: 技能参数验证")
    print("="*80)
    
    try:
        print("\nVideoCutSkill 参数:")
        for param in cut_skill.parameters:
            print(f"  - {param.name}: {param.type} ({'必需' if param.required else '可选'})")
            if param.default is not None:
                print(f"    默认值: {param.default}")
        
        print("\nVideoMergeSkill 参数:")
        for param in merge_skill.parameters:
            print(f"  - {param.name}: {param.type} ({'必需' if param.required else '可选'})")
            if param.default is not None:
                print(f"    默认值: {param.default}")
        
        print("\nVideoSubtitleOverlaySkill 参数:")
        for param in subtitle_skill.parameters:
            print(f"  - {param.name}: {param.type} ({'必需' if param.required else '可选'})")
            if param.default is not None:
                print(f"    默认值: {param.default}")
        
        return True
    except Exception as e:
        print(f"✗ 参数验证失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_skill_registry(cut_skill, merge_skill, subtitle_skill):
    """测试技能注册"""
    print("\n" + "="*80)
    print("测试 4: 技能注册")
    print("="*80)
    
    try:
        registry = SkillRegistry()
        
        registry.register(cut_skill)
        registry.register(merge_skill)
        registry.register(subtitle_skill)
        
        print(f"✓ 技能注册成功")
        all_skills = registry.get_all()
        print(f"  已注册技能数量: {len(all_skills)}")
        
        print("\n已注册的技能:")
        for skill in all_skills:
            print(f"  - {skill.name}: {skill.description} (v{skill.version})")
        
        # 测试技能匹配
        print("\n测试技能匹配:")
        test_queries = [
            "帮我剪辑视频",
            "合并两个视频",
            "给视频添加字幕",
            "提取视频片段",
            "视频合并"
        ]
        
        for query in test_queries:
            matched_skill = registry.match(query)
            if matched_skill:
                print(f"  '{query}' -> {matched_skill.name}")
            else:
                print(f"  '{query}' -> 未匹配到技能")
        
        return True
    except Exception as e:
        print(f"✗ 技能注册失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_parameter_validation(cut_skill, merge_skill, subtitle_skill):
    """测试参数验证"""
    print("\n" + "="*80)
    print("测试 5: 参数验证")
    print("="*80)
    
    try:
        # 测试 video_cut 参数验证
        print("\n测试 VideoCutSkill 参数验证:")
        
        # 缺少必需参数
        is_valid, error = cut_skill.validate_parameters({})
        print(f"  空参数: {'✓ 正确拒绝' if not is_valid else '✗ 应该拒绝'}")
        if not is_valid:
            print(f"    错误信息: {error}")
        
        # 完整参数
        valid_params = {
            "input_file": "/path/to/video.mp4",
            "output_file": "/path/to/output.mp4",
            "segments": [{"start_time": "00:00:05", "end_time": "00:00:15"}]
        }
        is_valid, error = cut_skill.validate_parameters(valid_params)
        print(f"  完整参数: {'✓ 正确接受' if is_valid else f'✗ 应该接受: {error}'}")
        
        # 测试 video_merge 参数验证
        print("\n测试 VideoMergeSkill 参数验证:")
        
        # 缺少必需参数
        is_valid, error = merge_skill.validate_parameters({})
        print(f"  空参数: {'✓ 正确拒绝' if not is_valid else '✗ 应该拒绝'}")
        if not is_valid:
            print(f"    错误信息: {error}")
        
        # 完整参数
        valid_params = {
            "input_files": ["/path/to/video1.mp4", "/path/to/video2.mp4"],
            "output_file": "/path/to/output.mp4"
        }
        is_valid, error = merge_skill.validate_parameters(valid_params)
        print(f"  完整参数: {'✓ 正确接受' if is_valid else f'✗ 应该接受: {error}'}")
        
        # 测试 video_subtitle_overlay 参数验证
        print("\n测试 VideoSubtitleOverlaySkill 参数验证:")
        
        # 缺少必需参数
        is_valid, error = subtitle_skill.validate_parameters({})
        print(f"  空参数: {'✓ 正确拒绝' if not is_valid else '✗ 应该拒绝'}")
        if not is_valid:
            print(f"    错误信息: {error}")
        
        # 完整参数
        valid_params = {
            "input_file": "/path/to/video.mp4",
            "output_file": "/path/to/output.mp4",
            "subtitle_file": "/path/to/subtitle.srt"
        }
        is_valid, error = subtitle_skill.validate_parameters(valid_params)
        print(f"  完整参数: {'✓ 正确接受' if is_valid else f'✗ 应该接受: {error}'}")
        
        return True
    except Exception as e:
        print(f"✗ 参数验证测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_orchestrator_auto_registration():
    """测试 orchestrator 自动注册"""
    print("\n" + "="*80)
    print("测试 6: Orchestrator 自动注册")
    print("="*80)
    
    try:
        from backend.core.agent.orchestrator import Orchestrator
        
        # 创建 orchestrator 实例（会自动注册技能）
        orchestrator = Orchestrator()
        
        print(f"✓ Orchestrator 初始化成功")
        all_skills = orchestrator.skill_registry.get_all()
        print(f"  已注册技能数量: {len(all_skills)}")
        
        print("\nOrchestrator 自动发现的技能:")
        for skill in all_skills:
            print(f"  - {skill.name}: {skill.description} (v{skill.version})")
        
        # 检查我们的技能是否被注册
        expected_skills = ['video_cut', 'video_merge', 'video_subtitle_overlay']
        found_skills = []
        for skill_name in expected_skills:
            skill = orchestrator.skill_registry.get(skill_name)
            if skill:
                found_skills.append(skill_name)
                print(f"  ✓ {skill_name} 已自动注册")
            else:
                print(f"  ✗ {skill_name} 未找到")
        
        if len(found_skills) == len(expected_skills):
            print(f"\n✓ 所有技能都已自动注册")
            return True
        else:
            print(f"\n✗ 部分技能未注册（期望 {len(expected_skills)} 个，找到 {len(found_skills)} 个）")
            return False
            
    except Exception as e:
        print(f"✗ Orchestrator 自动注册测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主测试函数"""
    print("="*80)
    print("视频编辑技能测试")
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    results = []
    
    # 测试 1: 技能导入
    results.append(("技能导入", test_skill_imports()))
    
    # 测试 2: 技能实例化
    success, cut_skill, merge_skill, subtitle_skill = test_skill_instantiation()
    results.append(("技能实例化", success))
    
    if not success:
        print("\n✗ 技能实例化失败，无法继续测试")
        return
    
    # 测试 3: 技能参数
    results.append(("技能参数", test_skill_parameters(cut_skill, merge_skill, subtitle_skill)))
    
    # 测试 4: 技能注册
    results.append(("技能注册", test_skill_registry(cut_skill, merge_skill, subtitle_skill)))
    
    # 测试 5: 参数验证
    results.append(("参数验证", test_parameter_validation(cut_skill, merge_skill, subtitle_skill)))
    
    # 测试 6: Orchestrator 自动注册
    results.append(("Orchestrator 自动注册", test_orchestrator_auto_registration()))
    
    # 总结
    print("\n" + "="*80)
    print("测试总结")
    print("="*80)
    
    passed = 0
    failed = 0
    
    for test_name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print(f"\n总计: {passed} 通过, {failed} 失败")
    
    if failed == 0:
        print("\n🎉 所有测试通过！")
    else:
        print(f"\n⚠️  有 {failed} 个测试失败，请检查上述错误信息")

if __name__ == "__main__":
    main()


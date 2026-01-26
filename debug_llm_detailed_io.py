#!/usr/bin/env python3
"""详细查看LLM的输入输出调试"""

import json
import asyncio
from backend.core.agent.skills.registry import SkillRegistry
from backend.core.agent.skills.blog_writing.skill import BlogWritingSkill


# 导入视频相关技能
from backend.core.agent.skills.video_downloader.video_downloader_skill import (  # noqa: E501
    VideoDownloaderSkill,
)
from backend.core.agent.skills.video_extract_srt import VideoExtractSrtSkill  # noqa: E501
from backend.core.agent.skills.video_editing.video_cut_skill import VideoCutSkill  # noqa: E501
from backend.core.agent.skills.video_merge.video_merge_skill import VideoMergeSkill  # noqa: E501
from backend.core.agent.skills.video_subtitle_overlay.video_subtitle_overlay_skill import (  # noqa: E501
    VideoSubtitleOverlaySkill,
)
from backend.services.llm.llm_service import LLMService


async def debug_llm_detailed_io():
    """详细调试LLM的输入输出"""
    print("=== LLM 详细输入输出调试 ===\n")
    
    # 创建技能注册表并注册所有技能
    skill_registry = SkillRegistry()
    
    # 注册所有技能
    skills_to_register = [
        ("blog_writing", BlogWritingSkill()),
        ("video_downloader", VideoDownloaderSkill(None)),
        ("video_extract_srt", VideoExtractSrtSkill(None)),
        ("video_cut", VideoCutSkill(None)),
        ("video_merge", VideoMergeSkill(None)),
        ("video_subtitle_overlay", VideoSubtitleOverlaySkill(None)),
    ]
    
    for skill_name, skill in skills_to_register:
        skill_registry.register(skill)
        print(f"✓ 注册技能: {skill_name}")
    
    print(f"\n总共注册了 {len(skill_registry._skills)} 个技能")
    
    # 获取所有可用技能的信息
    available_skills = []
    for skill in skill_registry._skills.values():
        skill_info = {
            'name': skill.name,
            'description': skill.description,
            'version': skill.version,
            'author': getattr(skill, 'author', 'Unknown'),
        }
        available_skills.append(skill_info)
    
    print(f"\n可用技能列表: {[s['name'] for s in available_skills]}")
    
    # 测试输入
    test_inputs = [
        "点点点",
        "帮我写一个叫点点点的文章",
        "帮我下载这个视频 https://example.com/video"
    ]
    
    for user_input in test_inputs:
        print(f"\n{'='*60}")
        print(f"测试输入: {user_input}")
        print(f"{'='*60}")
        
        try:
            # 创建 LLM 服务实例
            llm_service = LLMService()
            
            # 构建提示词，让 LLM 从可用技能中选择最合适的
            system_prompt = (
                "你是一个技能匹配专家。请分析用户输入的意图，"
                "从提供的技能列表中选择最适合的技能。\n\n"
                "返回格式：{'skill_name': '技能名称'} 或 {'skill_name': null} "
                "如果没有技能适合用户的需求。"
            )
            
            user_prompt = (
                f"用户输入: {user_input}\n\n"
                f"可用技能列表: {available_skills}\n\n"
                "请返回最适合的技能。"
            )
            
            print("\n--- LLM 输入 ---")
            print(f"System Prompt:\n{system_prompt}")
            print(f"\nUser Prompt:\n{user_prompt}")
            
            # 直接调用 LLM 服务
            response = await llm_service.chat(
                system_prompt=system_prompt,
                user_prompt=user_prompt
            )
            
            print("\n--- LLM 输出 ---")
            print(f"原始响应:\n{response}")
            
            # 尝试解析 LLM 的响应
            print("\n--- 尝试解析响应 ---")
            import ast
            try:
                # 尝试解析标准JSON格式
                llm_analysis = json.loads(response)
                print(f"✓ JSON解析成功: {llm_analysis}")
            except (json.JSONDecodeError, TypeError):
                try:
                    # 如果标准JSON解析失败，尝试解析Python字典格式（ast.literal_eval）
                    llm_analysis = ast.literal_eval(response)
                    print(f"✓ Python字典解析成功: {llm_analysis}")
                except (ValueError, SyntaxError):
                    print("✗ 两种解析都失败")
                    llm_analysis = None
            
            if llm_analysis:
                selected_skill_name = llm_analysis.get('skill_name')
                print("\n--- 解析结果 ---")
                print(f"解析的skill_name: {selected_skill_name}")
                
                if (
                    selected_skill_name 
                    and selected_skill_name in skill_registry._skills
                ):
                    skill = skill_registry._skills[selected_skill_name]
                    print(f"匹配技能: {selected_skill_name}")
                else:
                    print(f"无匹配技能: {selected_skill_name}")
            
        except Exception as e:
            print("\n--- LLM 调用错误 ---")
            print(f"错误: {e}")
            import traceback
            print(f"堆栈跟踪:\n{traceback.format_exc()}")


if __name__ == "__main__":
    asyncio.run(debug_llm_detailed_io())
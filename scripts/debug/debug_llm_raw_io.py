#!/usr/bin/env python3
"""查看LLM的原始输入和输出"""

import json
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


async def debug_llm_raw_io():
    """调试LLM的原始输入输出"""
    print("=== LLM 原始输入输出调试 ===\n")
    
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
        print(f"\n{'='*50}")
        print(f"测试输入: {user_input}")
        print(f"{'='*50}")
        
        try:
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
            
            response = await llm_service.chat(
                system_prompt=system_prompt,
                user_prompt=user_prompt
            )
            
            print("\n--- LLM 输出 ---")
            print(f"原始响应:\n{response}")
            
            # 解析 LLM 的响应
            try:
                llm_analysis = json.loads(response)
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
            except (json.JSONDecodeError, TypeError) as e:
                print("\n--- 解析错误 ---")
                print(f"JSON解析失败: {e}")
                print(f"原始响应内容: {response}")
                
        except Exception as e:
            print("\n--- LLM 调用错误 ---")
            print(f"错误: {e}")
            print("由于错误，将回退到传统匹配")


if __name__ == "__main__":
    import asyncio
    asyncio.run(debug_llm_raw_io())
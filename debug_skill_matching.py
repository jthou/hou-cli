#!/usr/bin/env python3
"""调试技能匹配问题"""

import asyncio
import json
from backend.core.agent.skills.registry import SkillRegistry
from backend.core.agent.skills.blog_writing.skill import BlogWritingSkill


# 导入视频相关技能
from backend.core.agent.skills.video_downloader.video_downloader_skill import (  # noqa: E501
    VideoDownloaderSkill as VDSkill,
)

from backend.core.agent.skills.video_extract_srt import VideoExtractSrtSkill as VESkill  # noqa: E501

from backend.core.agent.skills.video_editing.video_cut_skill import VideoCutSkill as VCSkill  # noqa: E501

from backend.core.agent.skills.video_merge.video_merge_skill import VideoMergeSkill as VMSkill  # noqa: E501

from backend.core.agent.skills.video_subtitle_overlay.video_subtitle_overlay_skill import (  # noqa: E501
    VideoSubtitleOverlaySkill as VSOSkill,
)


async def test_skill_matching():
    """测试技能匹配逻辑"""
    print("=== 技能匹配调试 ===\n")
    
    # 创建技能注册表并注册所有技能
    skill_registry = SkillRegistry()
    
    # 注册所有技能
    skills_to_register = [
        ("blog_writing", BlogWritingSkill()),
        ("video_downloader", VDSkill(None)),
        ("video_extract_srt", VESkill(None)),
        ("video_cut", VCSkill(None)),
        ("video_merge", VMSkill(None)),
        ("video_subtitle_overlay", VSOSkill(None)),
    ]
    
    for skill_name, skill in skills_to_register:
        skill_registry.register(skill)
        print(f"✓ 注册技能: {skill_name}")
    
    print(f"\n总共注册了 {len(skill_registry._skills)} 个技能")
    
    # 测试不同的用户输入
    test_inputs = [
        "帮我写一篇关于人工智能的文章",
        "帮我写一篇文章，主题是点点点",
        "我想写一个文章，题目叫点点点",
        "写一个关于点点点的文章",
        "帮我下载这个视频 https://example.com/video",
        "提取这个视频的字幕",
        "剪辑这个视频从00:05:00到00:19:00",
    ]
    
    print("\n=== 测试技能匹配 ===")
    for user_input in test_inputs:
        print(f"\n输入: {user_input}")
        
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
        
        print(f"可用技能: {[s['name'] for s in available_skills]}")
        
        # 使用LLM匹配
        from backend.services.llm.llm_service import LLMService
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
            
            print(f"LLM 请求:\nSystem: {system_prompt}\nUser: {user_prompt}")
            
            response = await llm_service.chat(
                system_prompt=system_prompt,
                user_prompt=user_prompt
            )
            
            print(f"LLM 响应: {response}")
            
            # 解析 LLM 的响应
            try:
                llm_analysis = json.loads(response)
                selected_skill_name = llm_analysis.get('skill_name')
                
                if (
                    selected_skill_name 
                    and selected_skill_name in skill_registry._skills
                ):
                    skill = skill_registry._skills[selected_skill_name]
                    print(f"✓ LLM 匹配技能: {selected_skill_name}")
                else:
                    print(f"✗ LLM 判断无合适技能: {selected_skill_name}")
            except (json.JSONDecodeError, TypeError):
                print(f"✗ LLM 响应格式不符合预期: {response}")
                
        except Exception as e:
            print(f"✗ LLM 技能匹配失败: {e}")
        
        # 测试传统匹配
        traditional_match = skill_registry.match(user_input)
        if traditional_match:
            print(f"✓ 传统匹配结果: {traditional_match.name}")
        else:
            print("✗ 传统匹配无结果")


if __name__ == "__main__":
    asyncio.run(test_skill_matching())
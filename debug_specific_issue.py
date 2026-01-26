#!/usr/bin/env python3
"""调试特定问题：为什么会出现'没有匹配到任何技能'"""

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


def analyze_keyword_matching():
    """分析关键词匹配逻辑"""
    print("=== 关键词匹配分析 ===\n")
    
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
    
    # 测试有问题的输入
    problematic_inputs = [
        "点点点",
        "写文章，题目叫点点点",
        "帮我写一个叫点点点的文章",
    ]
    
    print("\n=== 测试问题输入 ===")
    for user_input in problematic_inputs:
        print(f"\n输入: '{user_input}'")
        
        # 手动执行关键词匹配逻辑
        user_input_lower = user_input.lower()
        
        # 检测是否为本地文件路径（优先于 URL 检测）
        import re

        # 检测本地文件路径模式
        local_file_patterns = [
            r'^[~/]',  # 以 ~ 或 / 开头
            r'\.mp4\b',  # 包含 .mp4 扩展名
            r'\.avi\b',  # 包含 .avi 扩展名
            r'\.mkv\b',  # 包含 .mkv 扩展名
            r'\.mov\b',  # 包含 .mov 扩展名
            r'^[a-z]:\\',  # Windows 路径（如 C:\\）
            r'/home/',  # Linux 路径
            r'/Users/',  # macOS 路径
        ]

        is_local_file = any(
            re.search(pattern, user_input, re.IGNORECASE) 
            for pattern in local_file_patterns
        )

        # 检测 URL 模式
        url_patterns = [
            r'https?://',  # HTTP/HTTPS URL
            r'www\.',  # www. 开头
            r'bilibili\.com',  # Bilibili 域名
            r'youtube\.com',  # YouTube 域名
        ]
        
        is_url = any(
            re.search(pattern, user_input, re.IGNORECASE) 
            for pattern in url_patterns
        )
        
        print(f"is_local_file: {is_local_file}")
        print(f"is_url: {is_url}")

        # 收集所有匹配的技能及其匹配分数
        matched_skills = []
        
        for skill in skill_registry._skills.values():
            score = 0
            
            # 1. 精确名称匹配（最高优先级）
            if skill.name.lower() in user_input_lower:
                score += 1000
                print(f"  {skill.name}: 精确名称匹配 +1000 = {score}")
                matched_skills.append((score, skill))
                continue
                
            # 2. 检查用户输入中的关键词
            download_keywords = ["下载", "download", "下", "获取视频"]
            summary_keywords = [
                "摘要", "总结", "summary", "分析", "analyze", "阅读", "read"
            ]
            video_keywords = ["视频", "video", "bilibili", "b站", "哔哩"]
            audio_keywords = ["音频", "audio", "分离", "提取"]
            subtitle_keywords = ["字幕", "subtitle", "srt", "转成", "转"]
            ffmpeg_keywords = ["ffmpeg"]
            whisper_keywords = ["whisper"]
            cut_keywords = [
                "剪辑", "cut", "trim", "slice", "裁剪", "截取",
                "提取片段", "片段"
            ]
            merge_keywords = ["合并", "merge", "拼接", "连接"]
            # edit_keywords = ["编辑", "edit", "处理"]  # noqa: F841
                
            has_download = any(
                kw in user_input_lower for kw in download_keywords
            )
            has_summary = any(
                kw in user_input_lower for kw in summary_keywords
            )
            has_video = any(
                kw in user_input_lower for kw in video_keywords
            )
            has_audio = any(
                kw in user_input_lower for kw in audio_keywords
            )
            has_subtitle = any(
                kw in user_input_lower for kw in subtitle_keywords
            )
            has_ffmpeg = any(
                kw in user_input_lower for kw in ffmpeg_keywords
            )
            has_whisper = any(
                kw in user_input_lower for kw in whisper_keywords
            )
            has_cut = any(
                kw in user_input_lower for kw in cut_keywords
            )
            has_merge = any(
                kw in user_input_lower for kw in merge_keywords
            )
            # has_edit = any(kw in user_input_lower for kw in edit_keywords)  # noqa: F841, E501
            
            # 检测写作相关的关键词
            writing_keywords = [
                "写", "写作", "文章", "大纲", "撰写", "创作", 
                "博客", "博文", "笔记", "总结", "整理", "梳理", 
                "草稿", "起草"
            ]
            has_writing = any(
                kw in user_input_lower 
                for kw in writing_keywords
            )
            
            # 检测时间范围（如 00:05:00 到 00:19:00）
            time_pattern = r'\d{1,2}:\d{2}:\d{2}'
            has_time_range = bool(re.search(time_pattern, user_input))
                
            # 3. 检查技能描述中的关键词
            skill_desc_lower = skill.description.lower()
            skill_has_download = any(
                kw in skill_desc_lower for kw in download_keywords
            )
            skill_has_summary = any(
                kw in skill_desc_lower for kw in summary_keywords
            )
            skill_has_video = any(
                kw in skill_desc_lower for kw in video_keywords
            )
            skill_has_audio = any(
                kw in skill_desc_lower for kw in audio_keywords
            )
            skill_has_subtitle = any(
                kw in skill_desc_lower for kw in subtitle_keywords
            )
            skill_has_ffmpeg = any(
                kw in skill_desc_lower for kw in ffmpeg_keywords
            )
            skill_has_whisper = any(
                kw in skill_desc_lower for kw in whisper_keywords
            )
            skill_has_cut = any(
                kw in skill_desc_lower for kw in cut_keywords
            )
            skill_has_merge = any(
                kw in skill_desc_lower for kw in merge_keywords
            )
            skill_has_writing = any(
                kw in skill_desc_lower for kw in writing_keywords
            )
            
            print(f"  {skill.name}:")
            print(f"    has_download: {has_download}, has_writing: {has_writing}")  # noqa: E501
            print(f"    skill_has_download: {skill_has_download}, skill_has_writing: {skill_has_writing}")  # noqa: E501
            
            # 4. 本地文件路径特殊处理
            if is_local_file:
                # 如果是本地文件路径，根据用户意图匹配技能
                # (略去这部分，因为当前不是本地文件)
                pass

            # 5. URL 特殊处理
            if is_url:
                # 如果是 URL，优先匹配下载技能
                # (略去这部分，因为当前不是URL)
                pass
                
            # 6. 计算匹配分数
            # 如果用户只要求下载，优先匹配专门的下载技能（但本地文件除外）
            # 避免因误判导致错误匹配，加强上下文理解
            download_and_not_writing = (
                has_writing and skill_has_download 
                and not skill_has_writing
            )
            if (has_download and not has_summary and not has_subtitle 
                    and not is_local_file):
                # 额外检查：确保下载关键词确实是用户的主要意图
                # 如果输入中包含明显的写作关键词，则降低下载技能的分数
                if download_and_not_writing:
                    score -= 400  # 写作意图但下载技能，降分
                    print(f"    写作意图但下载技能，降分 -400 = {score}")
                elif (skill_has_download and not skill_has_summary 
                        and not skill_has_subtitle):
                    # 专门的下载技能（如 video_downloader）
                    score += 500
                    print(f"    专门下载技能，加分 +500 = {score}")
                elif skill_has_download and (
                        skill_has_summary or skill_has_subtitle
                ):
                    # 复合技能（如 video_extract_srt），分数较低
                    score += 100
                    print(f"    复合下载技能，加分 +100 = {score}")

            # 如果用户要求字幕提取（不要求摘要），优先匹配 video_extract_srt
            if has_subtitle and not has_summary:
                if skill.name == 'video_extract_srt':
                    score += 600  # 高优先级
                    print(f"    字幕提取，加分 +600 = {score}")
                elif skill_has_subtitle and not skill_has_summary:
                    score += 400
                    print(f"    字幕技能，加分 +400 = {score}")
                elif skill_has_subtitle and skill_has_summary:
                    score += 200  # 复合技能优先级较低
                    print(f"    复合字幕技能，加分 +200 = {score}")

            # 如果用户要求摘要/分析，匹配摘要技能
            if has_summary:
                if skill_has_summary:
                    score += 300
                    print(f"    摘要技能，加分 +300 = {score}")

            # 如果用户要求音频提取/ffmpeg/whisper（但不要求摘要），匹配字幕提取技能
            if (has_audio or has_ffmpeg or has_whisper) and not has_summary:
                if skill.name == 'video_extract_srt':
                    score += 400
                    print(f"    音频/ffmpeg/whisper技能，加分 +400 = {score}")
                elif skill_has_audio or skill_has_ffmpeg or skill_has_whisper:
                    score += 200
                    print(f"    音频/ffmpeg/whisper相关技能，加分 +200 = {score}")
                    
            # 如果用户要求剪辑（cut/trim/slice），优先匹配 video_cut
            if has_cut or has_time_range:
                if skill.name == 'video_cut':
                    score += 800  # 高优先级
                    print(f"    剪辑技能，加分 +800 = {score}")
                elif skill_has_cut:
                    score += 400
                    print(f"    剪辑相关技能，加分 +400 = {score}")
                elif skill.name == 'video_extract_srt':
                    score -= 300  # 降低优先级（因为不是剪辑操作）
                    print(f"    非剪辑技能但需要剪辑，降分 -300 = {score}")
                    
            # 如果用户要求合并，优先匹配 video_merge
            if has_merge:
                if skill.name == 'video_merge':
                    score += 800  # 高优先级
                    print(f"    合并技能，加分 +800 = {score}")
                elif skill_has_merge:
                    score += 400
                    print(f"    合并相关技能，加分 +400 = {score}")
                    
            # 视频相关关键词匹配
            if has_video and skill_has_video:
                score += 50
                print(f"    视频相关技能，加分 +50 = {score}")
            
            # 写作相关关键词匹配
            if has_writing and skill_has_writing:
                score += 300  # 给写作相关技能较高优先级
                print(f"    写作相关技能，加分 +300 = {score}")
                
            # 7. 优先级加分（P0 > P1 > P2）
            # 注意：只有在有相关匹配（score > 0）时才给优先级加分，避免误匹配
            priority = getattr(skill, 'priority', 'P1')
            if score > 0:  # 只有在已有匹配分数时才给优先级加分
                if priority == 'P0':
                    score += 100
                    print(f"    优先级加分 +100 = {score}")
                elif priority == 'P1':
                    score += 50
                    print(f"    优先级加分 +50 = {score}")
                
            # 8. 如果分数大于 0，添加到匹配列表
            # 添加最低匹配阈值，避免完全无关的技能被匹配
            min_match_threshold = 50  # 最低匹配分数阈值
            if score >= min_match_threshold:
                matched_skills.append((score, skill))
                print(f"    最终分数 {score} >= {min_match_threshold}，加入候选")
            else:
                print(f"    最终分数 {score} < {min_match_threshold}，未加入候选")
        
        # 检查最终匹配结果
        if not matched_skills:
            print("  → 无匹配技能")
        else:
            # 按分数降序排序，返回最高分的技能
            matched_skills.sort(key=lambda x: x[0], reverse=True)
            best_match = matched_skills[0][1]
            print(f"  → 最佳匹配: {best_match.name} (分数: {matched_skills[0][0]})")
            
        # 测试实际的match方法
        actual_result = skill_registry.match(user_input)
        if actual_result:
            print(f"  → 实际匹配结果: {actual_result.name}")
        else:
            print("  → 实际匹配结果: None")


if __name__ == "__main__":
    analyze_keyword_matching()
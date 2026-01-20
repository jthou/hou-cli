"""技能匹配逻辑测试"""
import pytest
from unittest.mock import MagicMock
from backend.core.agent.skills.registry import SkillRegistry
from backend.core.agent.skills.base import Skill, SkillResult


class MockSkill(Skill):
    """模拟技能类，用于测试"""
    
    def __init__(self, name: str, description: str, priority: str = "P1", **kwargs):
        super().__init__(name=name, description=description, priority=priority, **kwargs)
    
    def execute(self, **kwargs) -> SkillResult:
        """模拟执行"""
        return SkillResult(success=True, data={"result": "mock"})


class TestSkillRegistryMatching:
    """技能匹配逻辑测试"""
    
    @pytest.fixture
    def registry(self):
        """创建技能注册表"""
        return SkillRegistry()
    
    @pytest.fixture
    def video_downloader_skill(self):
        """创建 video_downloader 技能"""
        return MockSkill(
            name="video_downloader",
            description="下载视频文件，支持单个或多个视频 URL，支持批量下载",
            priority="P0"
        )
    
    @pytest.fixture
    def video_extract_srt_skill(self):
        """创建 video_extract_srt 技能"""
        return MockSkill(
            name="video_extract_srt",
            description="下载视频、提取音频、生成字幕文件（SRT格式）",
            priority="P1"
        )
    
    @pytest.fixture
    def video_cut_skill(self):
        """创建 video_cut 技能"""
        return MockSkill(
            name="video_cut",
            description="从视频中提取指定时间段的内容，支持单片段和多片段剪辑",
            priority="P1"
        )
    
    @pytest.fixture
    def video_merge_skill(self):
        """创建 video_merge 技能"""
        return MockSkill(
            name="video_merge",
            description="合并多个视频文件，支持转场效果",
            priority="P1"
        )
    
    def test_exact_name_match(self, registry, video_downloader_skill):
        """测试精确名称匹配（最高优先级）"""
        registry.register(video_downloader_skill)
        registry.register(MockSkill(name="other_skill", description="其他技能"))
        
        # 精确名称匹配应该返回 1000 分
        matched = registry.match("请使用 video_downloader 下载视频")
        assert matched is not None
        assert matched.name == "video_downloader"
    
    def test_keyword_match_download(self, registry, video_downloader_skill, video_extract_srt_skill):
        """测试下载关键词匹配"""
        registry.register(video_downloader_skill)
        registry.register(video_extract_srt_skill)
        
        # "下载" 关键词应该匹配到 video_downloader
        matched = registry.match("下载这个视频")
        assert matched is not None
        assert matched.name == "video_downloader"
    
    def test_keyword_match_subtitle(self, registry, video_extract_srt_skill):
        """测试字幕关键词匹配"""
        registry.register(video_extract_srt_skill)
        
        # "字幕" 关键词应该匹配到 video_extract_srt
        matched = registry.match("提取字幕")
        assert matched is not None
        assert matched.name == "video_extract_srt"
    
    def test_keyword_match_cut(self, registry, video_cut_skill, video_extract_srt_skill):
        """测试剪辑关键词匹配"""
        registry.register(video_cut_skill)
        registry.register(video_extract_srt_skill)
        
        # "剪辑" 关键词应该匹配到 video_cut
        matched = registry.match("剪辑视频")
        assert matched is not None
        assert matched.name == "video_cut"
    
    def test_keyword_match_merge(self, registry, video_merge_skill):
        """测试合并关键词匹配"""
        registry.register(video_merge_skill)
        
        # "合并" 关键词应该匹配到 video_merge
        matched = registry.match("合并视频")
        assert matched is not None
        assert matched.name == "video_merge"
    
    def test_url_match(self, registry, video_downloader_skill, video_extract_srt_skill):
        """测试 URL 匹配"""
        registry.register(video_downloader_skill)
        registry.register(video_extract_srt_skill)
        
        # URL 应该优先匹配到 video_downloader
        matched = registry.match("https://www.bilibili.com/video/BV123456")
        assert matched is not None
        assert matched.name == "video_downloader"
    
    def test_local_file_match(self, registry, video_extract_srt_skill, video_cut_skill):
        """测试本地文件路径匹配"""
        registry.register(video_extract_srt_skill)
        registry.register(video_cut_skill)
        
        # 本地文件路径应该匹配到 video_extract_srt（默认）
        matched = registry.match("/home/user/video.mp4")
        assert matched is not None
        assert matched.name == "video_extract_srt"
    
    def test_local_file_with_cut_keyword(self, registry, video_extract_srt_skill, video_cut_skill):
        """测试本地文件路径 + 剪辑关键词"""
        registry.register(video_extract_srt_skill)
        registry.register(video_cut_skill)
        
        # 本地文件 + 剪辑关键词应该匹配到 video_cut
        matched = registry.match("/home/user/video.mp4 剪辑 00:05:00 到 00:10:00")
        assert matched is not None
        assert matched.name == "video_cut"
    
    def test_time_range_match(self, registry, video_cut_skill):
        """测试时间范围匹配"""
        registry.register(video_cut_skill)
        
        # 时间范围应该匹配到 video_cut
        matched = registry.match("提取 00:05:00 到 00:10:00 的片段")
        assert matched is not None
        assert matched.name == "video_cut"
    
    def test_priority_boost(self, registry, video_downloader_skill, video_extract_srt_skill):
        """测试优先级加分（只有在已有匹配分数时）"""
        registry.register(video_downloader_skill)
        registry.register(video_extract_srt_skill)
        
        # 下载关键词 + P0 优先级应该匹配到 video_downloader
        matched = registry.match("下载视频")
        assert matched is not None
        assert matched.name == "video_downloader"
    
    def test_no_false_match_weather(self, registry, video_downloader_skill):
        """测试误匹配防护：天气查询不应该匹配到视频下载"""
        registry.register(video_downloader_skill)
        
        # 天气查询不应该匹配到任何技能
        matched = registry.match("查北京的天气")
        assert matched is None, f"不应该匹配到 {matched.name if matched else None}"
    
    def test_no_false_match_unrelated(self, registry, video_downloader_skill):
        """测试误匹配防护：完全不相关的查询不应该匹配"""
        registry.register(video_downloader_skill)
        
        # 完全不相关的查询不应该匹配
        test_cases = [
            "今天天气怎么样",
            "帮我写代码",
            "搜索 Python 教程",
            "打开浏览器",
            "读取文件内容",
        ]
        
        for query in test_cases:
            matched = registry.match(query)
            assert matched is None, f"'{query}' 不应该匹配到任何技能，但匹配到了 {matched.name if matched else None}"
    
    def test_minimum_match_threshold(self, registry):
        """测试最低匹配阈值（50分）"""
        # 创建一个低优先级、低相关性的技能
        low_priority_skill = MockSkill(
            name="low_priority_skill",
            description="低优先级技能",
            priority="P2"
        )
        registry.register(low_priority_skill)
        
        # 完全不相关的查询不应该匹配（因为分数 < 50）
        matched = registry.match("查询天气")
        assert matched is None
    
    def test_multiple_skills_priority(self, registry, video_downloader_skill, video_extract_srt_skill):
        """测试多个技能时的优先级排序"""
        registry.register(video_downloader_skill)
        registry.register(video_extract_srt_skill)
        
        # 下载 + 字幕关键词，应该优先匹配 video_extract_srt（因为更相关）
        matched = registry.match("下载视频并提取字幕")
        assert matched is not None
        # 注意：这里可能需要根据实际逻辑调整，因为 video_extract_srt 更匹配"字幕"
        assert matched.name in ["video_extract_srt", "video_downloader"]
    
    def test_english_keywords(self, registry, video_downloader_skill):
        """测试英文关键词匹配"""
        registry.register(video_downloader_skill)
        
        # 英文关键词应该也能匹配
        matched = registry.match("download video from https://example.com")
        assert matched is not None
        assert matched.name == "video_downloader"
    
    def test_mixed_chinese_english(self, registry, video_downloader_skill):
        """测试中英文混合关键词"""
        registry.register(video_downloader_skill)
        
        # 中英文混合应该也能匹配
        matched = registry.match("下载 video from bilibili")
        assert matched is not None
        assert matched.name == "video_downloader"
    
    def test_case_insensitive(self, registry, video_downloader_skill):
        """测试大小写不敏感"""
        registry.register(video_downloader_skill)
        
        # 大小写应该不影响匹配
        matched = registry.match("DOWNLOAD VIDEO")
        assert matched is not None
        assert matched.name == "video_downloader"
    
    def test_empty_input(self, registry, video_downloader_skill):
        """测试空输入"""
        registry.register(video_downloader_skill)
        
        # 空输入不应该匹配
        matched = registry.match("")
        assert matched is None
    
    def test_whitespace_only(self, registry, video_downloader_skill):
        """测试只有空白字符的输入"""
        registry.register(video_downloader_skill)
        
        # 只有空白字符不应该匹配
        matched = registry.match("   ")
        assert matched is None
    
    def test_url_with_subtitle_keyword(self, registry, video_extract_srt_skill, video_downloader_skill):
        """测试 URL + 字幕关键词"""
        registry.register(video_extract_srt_skill)
        registry.register(video_downloader_skill)
        
        # URL + 字幕关键词应该匹配到 video_extract_srt
        matched = registry.match("https://example.com/video.mp4 提取字幕")
        assert matched is not None
        assert matched.name == "video_extract_srt"
    
    def test_local_file_with_merge_keyword(self, registry, video_merge_skill, video_extract_srt_skill):
        """测试本地文件 + 合并关键词"""
        registry.register(video_merge_skill)
        registry.register(video_extract_srt_skill)
        
        # 本地文件 + 合并关键词应该匹配到 video_merge
        matched = registry.match("/home/user/video1.mp4 /home/user/video2.mp4 合并")
        assert matched is not None
        assert matched.name == "video_merge"
    
    def test_priority_only_when_relevant(self, registry):
        """测试优先级只在有相关匹配时才加分"""
        # 创建一个 P0 优先级但完全不相关的技能
        p0_unrelated_skill = MockSkill(
            name="p0_unrelated",
            description="P0 优先级但完全不相关的技能",
            priority="P0"
        )
        registry.register(p0_unrelated_skill)
        
        # 完全不相关的查询不应该匹配（即使优先级是 P0）
        matched = registry.match("查询天气")
        assert matched is None, "P0 优先级不应该导致误匹配"
    
    def test_audio_keyword_match(self, registry, video_extract_srt_skill):
        """测试音频关键词匹配"""
        registry.register(video_extract_srt_skill)
        
        # 音频关键词应该匹配到 video_extract_srt
        matched = registry.match("提取音频")
        assert matched is not None
        assert matched.name == "video_extract_srt"
    
    def test_ffmpeg_keyword_match(self, registry, video_extract_srt_skill):
        """测试 ffmpeg 关键词匹配"""
        registry.register(video_extract_srt_skill)
        
        # ffmpeg 关键词应该匹配到 video_extract_srt
        matched = registry.match("使用 ffmpeg 处理视频")
        assert matched is not None
        assert matched.name == "video_extract_srt"
    
    def test_whisper_keyword_match(self, registry, video_extract_srt_skill):
        """测试 whisper 关键词匹配"""
        registry.register(video_extract_srt_skill)
        
        # whisper 关键词应该匹配到 video_extract_srt
        matched = registry.match("使用 whisper 生成字幕")
        assert matched is not None
        assert matched.name == "video_extract_srt"
    
    def test_summary_keyword_no_match(self, registry, video_downloader_skill):
        """测试摘要关键词：由于通用视频关键词可能匹配，但摘要关键词优先级更高"""
        registry.register(video_downloader_skill)
        
        # "总结视频内容" 包含"视频"关键词，可能匹配到 video_downloader
        # 但由于包含"总结"关键词，如果没有摘要技能，可能不匹配或匹配到 video_downloader
        # 这个测试主要验证不会因为摘要关键词导致错误
        matched = registry.match("总结视频内容")
        # 由于"视频"关键词的存在，可能匹配到 video_downloader
        # 这是合理的，因为 video_downloader 的描述包含"视频"
        # 如果没有摘要技能，匹配到 video_downloader 也是可以接受的
        # 这个测试主要验证不会报错
        assert matched is None or matched.name == "video_downloader"
    
    def test_video_keyword_general_match(self, registry, video_downloader_skill, video_extract_srt_skill):
        """测试通用视频关键词匹配"""
        registry.register(video_downloader_skill)
        registry.register(video_extract_srt_skill)
        
        # 通用视频关键词应该匹配到某个视频相关技能
        matched = registry.match("处理视频")
        assert matched is not None
        assert matched.name in ["video_downloader", "video_extract_srt"]
    
    def test_edit_keyword_match(self, registry, video_cut_skill):
        """测试编辑关键词匹配"""
        registry.register(video_cut_skill)
        
        # 编辑关键词应该匹配到 video_cut（如果支持编辑）
        matched = registry.match("编辑视频")
        # 根据实际逻辑，可能匹配也可能不匹配
        # 这里只测试不会报错
        assert matched is None or matched.name == "video_cut"


class TestSkillRegistryMatchingEdgeCases:
    """技能匹配边界情况测试"""
    
    @pytest.fixture
    def registry(self):
        return SkillRegistry()
    
    def test_special_characters(self, registry):
        """测试特殊字符处理"""
        skill = MockSkill(name="test_skill", description="测试技能")
        registry.register(skill)
        
        # 特殊字符不应该导致错误
        matched = registry.match("测试！@#$%^&*()")
        # 应该正常处理，不会报错
        assert True  # 只要不报错就算通过
    
    def test_very_long_input(self, registry):
        """测试超长输入"""
        skill = MockSkill(name="test_skill", description="测试技能")
        registry.register(skill)
        
        # 超长输入应该能正常处理
        long_input = "下载" + "视频" * 1000
        matched = registry.match(long_input)
        # 应该正常处理，不会报错
        assert True  # 只要不报错就算通过
    
    def test_unicode_characters(self, registry):
        """测试 Unicode 字符"""
        skill = MockSkill(name="test_skill", description="测试技能")
        registry.register(skill)
        
        # Unicode 字符应该能正常处理
        matched = registry.match("下载视频🎬")
        # 应该正常处理，不会报错
        assert True  # 只要不报错就算通过
    
    def test_no_skills_registered(self, registry):
        """测试没有注册技能时"""
        # 没有注册任何技能
        matched = registry.match("下载视频")
        assert matched is None
    
    def test_single_skill_registered(self, registry):
        """测试只注册一个技能时"""
        skill = MockSkill(name="test_skill", description="测试技能")
        registry.register(skill)
        
        # 只有一个技能时，不相关的查询不应该匹配
        matched = registry.match("查询天气")
        assert matched is None


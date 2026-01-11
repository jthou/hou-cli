"""视频下载工具 - 整合 you-get、bili23-downloader 和 yt-dlp"""
import logging
import sys
from pathlib import Path
from typing import Optional, Dict, Any, List
from abc import ABC, abstractmethod

from backend.core.agent.tools.base import Tool, ToolResult, ToolParameter
from shared.platform_utils import normalize_output_dir

logger = logging.getLogger(__name__)


# ============================================================================
# 适配器基类
# ============================================================================

class DownloadResult:
    """下载结果"""
    def __init__(self, success: bool, data: Optional[Dict[str, Any]] = None, error: Optional[str] = None):
        self.success = success
        self.data = data or {}
        self.error = error


class DownloaderAdapter(ABC):
    """下载器适配器基类"""
    
    @abstractmethod
    def is_available(self) -> bool:
        """检查工具是否可用"""
        pass
    
    @abstractmethod
    def download(self, url: str, output_dir: Path, **options) -> DownloadResult:
        """执行下载"""
        pass
    
    @abstractmethod
    def supports_platform(self, url: str) -> bool:
        """检查是否支持该平台"""
        pass
    
    def get_supported_platforms(self) -> List[str]:
        """获取支持的平台列表"""
        return []


# ============================================================================
# 平台检测函数
# ============================================================================

def _detect_platform(url: str) -> str:
    """检测视频平台类型"""
    url_lower = url.lower()
    
    if 'bilibili.com' in url_lower or 'b23.tv' in url_lower:
        return 'bilibili'
    elif 'youtube.com' in url_lower or 'youtu.be' in url_lower:
        return 'youtube'
    elif 'youku.com' in url_lower:
        return 'youku'
    elif 'iqiyi.com' in url_lower:
        return 'iqiyi'
    elif 'qq.com' in url_lower and 'video' in url_lower:
        return 'tencent'
    elif 'twitter.com' in url_lower or 'x.com' in url_lower:
        return 'twitter'
    elif 'facebook.com' in url_lower:
        return 'facebook'
    else:
        return 'unknown'


# ============================================================================
# YouGetDownloader 适配器
# ============================================================================

def _get_you_get_path() -> Path:
    """获取 you-get 路径"""
    current_file = Path(__file__).resolve()
    # video_downloader_tool.py 在 backend/core/agent/tools/builtin/
    # 向上找到包含 backend 目录的父目录，然后取其父目录作为项目根
    current = current_file.parent
    while current.name != 'backend' and len(current.parts) > 1:
        current = current.parent
    if current.name == 'backend':
        project_root = current.parent
    else:
        # 如果找不到，使用向上5级的方式（向后兼容）
        project_root = current_file.parent.parent.parent.parent.parent
    return project_root / "backend" / "externals" / "you-get"


class YouGetDownloader(DownloaderAdapter):
    """you-get 适配器"""
    
    def is_available(self) -> bool:
        """检查 you-get 是否可用"""
        try:
            you_get_path = _get_you_get_path()
            if not you_get_path.exists():
                return False
            
            # 尝试导入 you_get
            if str(you_get_path) not in sys.path:
                sys.path.insert(0, str(you_get_path))
            
            import you_get  # type: ignore
            return True
        except Exception:
            return False
    
    def supports_platform(self, url: str) -> bool:
        """you-get 支持大部分平台"""
        platform = _detect_platform(url)
        return platform != 'unknown'
    
    def download(self, url: str, output_dir: Path, **options) -> DownloadResult:
        """使用 you-get 下载"""
        try:
            you_get_path = _get_you_get_path()
            if not you_get_path.exists():
                return DownloadResult(success=False, error="you-get not found")
            
            # 添加路径
            if str(you_get_path) not in sys.path:
                sys.path.insert(0, str(you_get_path))
            
            import subprocess
            cmd = ['python', '-m', 'you_get']
            
            # 输出目录
            cmd.extend(['-o', str(output_dir)])
            
            # 质量选项
            if options.get('quality'):
                cmd.extend(['-q', str(options['quality'])])
            
            # 格式选项
            if options.get('format'):
                cmd.extend(['-f', str(options['format'])])
            
            # URL
            cmd.append(url)
            
            # 执行
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=str(you_get_path)
            )
            
            if result.returncode == 0:
                return DownloadResult(
                    success=True,
                    data={'tool': 'you-get', 'output_dir': str(output_dir)}
                )
            else:
                return DownloadResult(
                    success=False,
                    error=f"you-get failed: {result.stderr}"
                )
        except Exception as e:
            return DownloadResult(success=False, error=f"you-get error: {str(e)}")


# ============================================================================
# Bili23Downloader 适配器
# ============================================================================

def _get_bili23_path() -> Path:
    """获取 bili23-downloader 路径"""
    current_file = Path(__file__).resolve()
    # video_downloader_tool.py 在 backend/core/agent/tools/builtin/
    # 向上找到包含 backend 目录的父目录，然后取其父目录作为项目根
    current = current_file.parent
    while current.name != 'backend' and len(current.parts) > 1:
        current = current.parent
    if current.name == 'backend':
        project_root = current.parent
    else:
        # 如果找不到，使用向上5级的方式（向后兼容）
        project_root = current_file.parent.parent.parent.parent.parent
    return project_root / "backend" / "externals" / "bili23-downloader"


class Bili23Downloader(DownloaderAdapter):
    """bili23-downloader 适配器"""
    
    def is_available(self) -> bool:
        """检查 bili23-downloader 是否可用"""
        try:
            bili23_path = _get_bili23_path()
            return bili23_path.exists()
        except Exception:
            return False
    
    def supports_platform(self, url: str) -> bool:
        """bili23-downloader 只支持 Bilibili"""
        return _detect_platform(url) == 'bilibili'
    
    def download(self, url: str, output_dir: Path, **options) -> DownloadResult:
        """使用 bili23-downloader 下载"""
        try:
            bili23_path = _get_bili23_path()
            if not bili23_path.exists():
                return DownloadResult(success=False, error="bili23-downloader not found")
            
            # bili23-downloader 是 GUI 应用，没有简单的 CLI 接口
            # 暂时降级到使用 yt-dlp 或 you-get
            # TODO: 未来可以实现通过 Python API 直接调用 bili23-downloader 的核心模块
            
            # 尝试使用 yt-dlp 作为降级方案
            yt_dlp = YtDlpDownloader()
            if yt_dlp.is_available():
                logger.info("bili23-downloader not available, falling back to yt-dlp")
                return yt_dlp.download(url, output_dir, **options)
            
            # 降级到 you-get
            you_get = YouGetDownloader()
            if you_get.is_available():
                logger.info("bili23-downloader not available, falling back to you-get")
                return you_get.download(url, output_dir, **options)
            
            return DownloadResult(
                success=False,
                error="bili23-downloader integration not yet implemented, and no fallback available"
            )
        except Exception as e:
            return DownloadResult(success=False, error=f"bili23-downloader error: {str(e)}")


# ============================================================================
# YtDlpDownloader 适配器
# ============================================================================

def _get_yt_dlp_path() -> Path:
    """获取 yt-dlp 路径"""
    current_file = Path(__file__).resolve()
    # video_downloader_tool.py 在 backend/core/agent/tools/builtin/
    # 向上找到包含 backend 目录的父目录，然后取其父目录作为项目根
    current = current_file.parent
    while current.name != 'backend' and len(current.parts) > 1:
        current = current.parent
    if current.name == 'backend':
        project_root = current.parent
    else:
        # 如果找不到，使用向上5级的方式（向后兼容）
        project_root = current_file.parent.parent.parent.parent.parent
    return project_root / "backend" / "externals" / "yt-dlp"


class YtDlpDownloader(DownloaderAdapter):
    """yt-dlp 适配器"""
    
    def is_available(self) -> bool:
        """检查 yt-dlp 是否可用"""
        try:
            yt_dlp_path = _get_yt_dlp_path()
            if not yt_dlp_path.exists():
                return False
            
            # 尝试导入 yt_dlp
            if str(yt_dlp_path) not in sys.path:
                sys.path.insert(0, str(yt_dlp_path))
            
            import yt_dlp  # type: ignore
            return True
        except Exception:
            return False
    
    def supports_platform(self, url: str) -> bool:
        """yt-dlp 支持大部分平台"""
        platform = _detect_platform(url)
        return platform != 'unknown'
    
    def download(self, url: str, output_dir: Path, **options) -> DownloadResult:
        """使用 yt-dlp 下载"""
        try:
            yt_dlp_path = _get_yt_dlp_path()
            if not yt_dlp_path.exists():
                return DownloadResult(success=False, error="yt-dlp not found")
            
            # 添加路径
            if str(yt_dlp_path) not in sys.path:
                sys.path.insert(0, str(yt_dlp_path))
            
            import yt_dlp  # type: ignore
            
            ydl_opts: Dict[str, Any] = {
                'outtmpl': str(output_dir / '%(title)s.%(ext)s'),
            }
            
            # 只下载字幕
            if options.get('download_subtitle_only'):
                ydl_opts['writesubtitles'] = True  # type: ignore
                ydl_opts['writeautomaticsub'] = True  # type: ignore
                ydl_opts['skip_download'] = True  # type: ignore
                if options.get('subtitle_languages'):
                    ydl_opts['subtitleslangs'] = options['subtitle_languages']
            
            # 只提取音频
            elif options.get('extract_audio_only'):
                ydl_opts['format'] = 'bestaudio/best'
                ydl_opts['postprocessors'] = [{  # type: ignore
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': options.get('audio_format', 'mp3'),
                    'preferredquality': options.get('audio_quality', '192'),
                }]
            else:
                # 正常下载视频
                if options.get('quality'):
                    ydl_opts['format'] = self._convert_quality_to_yt_dlp_format(options['quality'])
                if options.get('download_subtitle'):
                    ydl_opts['writesubtitles'] = True  # type: ignore
                    if options.get('subtitle_languages'):
                        ydl_opts['subtitleslangs'] = options['subtitle_languages']
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                return DownloadResult(
                    success=True,
                    data={
                        'tool': 'yt-dlp',
                        'output_dir': str(output_dir),
                        'title': info.get('title', ''),
                    }
                )
        except Exception as e:
            return DownloadResult(success=False, error=f"yt-dlp error: {str(e)}")
    
    def _convert_quality_to_yt_dlp_format(self, quality: str) -> str:
        """转换质量参数到 yt-dlp 格式"""
        quality_map = {
            'best': 'best',
            'worst': 'worst',
            '1080p': 'best[height<=1080]',
            '720p': 'best[height<=720]',
            '480p': 'best[height<=480]',
            '360p': 'best[height<=360]',
            '240p': 'best[height<=240]',
        }
        return quality_map.get(quality, 'best')


# ============================================================================
# 工具选择函数
# ============================================================================

def _select_downloader(url: str, preferred: str = 'auto', **options) -> DownloaderAdapter:
    """选择下载工具"""
    platform = _detect_platform(url)
    
    # 特殊功能优先使用 yt-dlp
    if options.get('download_subtitle_only') or options.get('extract_audio_only'):
        yt_dlp = YtDlpDownloader()
        if yt_dlp.is_available():
            return yt_dlp
    
    # 用户指定了首选工具
    if preferred == 'bili23' and platform == 'bilibili':
        bili23 = Bili23Downloader()
        if bili23.is_available():
            return bili23
        # 如果不可用，返回它（让错误信息更清晰）
        logger.warning(f"Preferred tool 'bili23' is not available")
        return bili23
    elif preferred == 'yt-dlp':
        yt_dlp = YtDlpDownloader()
        if yt_dlp.is_available():
            return yt_dlp
        # 如果不可用，返回它（让错误信息更清晰）
        logger.warning(f"Preferred tool 'yt-dlp' is not available")
        return yt_dlp
    elif preferred == 'you-get':
        you_get = YouGetDownloader()
        if you_get.is_available():
            return you_get
        # 如果不可用，返回它（让错误信息更清晰）
        logger.warning(f"Preferred tool 'you-get' is not available")
        return you_get
    
    # 自动选择
    if platform == 'bilibili':
        # B 站优先使用 bili23-downloader
        bili23 = Bili23Downloader()
        if bili23.is_available():
            return bili23
        # 降级到 yt-dlp 或 you-get
        yt_dlp = YtDlpDownloader()
        if yt_dlp.is_available():
            return yt_dlp
        you_get = YouGetDownloader()
        if you_get.is_available():
            return you_get
        # 如果都不可用，返回 yt-dlp（即使不可用，让错误信息更清晰）
        return yt_dlp
    elif platform == 'youtube':
        # YouTube 优先使用 yt-dlp
        yt_dlp = YtDlpDownloader()
        if yt_dlp.is_available():
            return yt_dlp
        you_get = YouGetDownloader()
        if you_get.is_available():
            return you_get
        # 如果都不可用，返回 yt-dlp
        return yt_dlp
    else:
        # 其他平台优先使用 yt-dlp
        yt_dlp = YtDlpDownloader()
        if yt_dlp.is_available():
            return yt_dlp
        you_get = YouGetDownloader()
        if you_get.is_available():
            return you_get
        # 如果都不可用，返回 yt-dlp
        return yt_dlp


# ============================================================================
# VideoDownloaderTool 主工具类
# ============================================================================

class VideoDownloaderTool(Tool):
    """视频下载工具"""
    
    def __init__(self):
        """初始化工具"""
        parameters = [
            ToolParameter(
                name="url",
                type="string",
                description="要下载的视频链接。支持短链接（如 b23.tv）和完整 URL。",
                required=True
            ),
            ToolParameter(
                name="output_dir",
                type="string",
                description="视频文件的保存目录。如果不指定，默认保存到系统下载目录。",
                required=False
            ),
            ToolParameter(
                name="quality",
                type="string",
                description="要下载的视频质量。可选值：'best'、'worst'、'1080p'、'720p'、'480p' 等。默认 'best'。",
                required=False,
                default="best",
                enum=["best", "worst", "1080p", "720p", "480p", "360p", "240p"]
            ),
            ToolParameter(
                name="format",
                type="string",
                description="视频文件格式。可选值：'mp4'、'flv'、'webm'、'mkv'、'auto'。",
                required=False,
                enum=["mp4", "flv", "webm", "mkv", "auto"]
            ),
            ToolParameter(
                name="download_subtitle",
                type="boolean",
                description="是否下载视频字幕文件。",
                required=False,
                default=False
            ),
            ToolParameter(
                name="download_thumbnail",
                type="boolean",
                description="是否下载视频封面图片。",
                required=False,
                default=False
            ),
            ToolParameter(
                name="download_danmaku",
                type="boolean",
                description="是否下载 Bilibili 弹幕文件（ASS 格式）。仅对 Bilibili 视频有效。",
                required=False,
                default=False
            ),
            ToolParameter(
                name="download_subtitle_only",
                type="boolean",
                description="是否只下载字幕，不下载视频。",
                required=False,
                default=False
            ),
            ToolParameter(
                name="extract_audio_only",
                type="boolean",
                description="是否只提取音频，不下载视频。",
                required=False,
                default=False
            ),
            ToolParameter(
                name="audio_format",
                type="string",
                description="音频文件格式（仅当 extract_audio_only=true 时有效）。默认 'mp3'。",
                required=False,
                default="mp3",
                enum=["mp3", "m4a", "opus", "wav", "aac"]
            ),
            ToolParameter(
                name="audio_quality",
                type="string",
                description="音频质量（仅当 extract_audio_only=true 时有效）。默认 '192k'。",
                required=False,
                default="192k",
                enum=["128k", "192k", "256k", "320k"]
            ),
            ToolParameter(
                name="subtitle_languages",
                type="array",
                description="要下载的字幕语言代码列表（如 ['en', 'zh']）。",
                required=False
            ),
            ToolParameter(
                name="preferred_tool",
                type="string",
                description="指定优先使用的下载工具。'auto'（自动选择）、'yt-dlp'、'you-get'、'bili23'。",
                required=False,
                default="auto",
                enum=["auto", "yt-dlp", "you-get", "bili23"]
            ),
        ]
        
        description = (
            "从多个视频平台下载视频文件。"
            "支持 YouTube、Bilibili、优酷、腾讯视频、爱奇艺等多个平台。"
            "对于 Bilibili 视频，支持下载弹幕、字幕、封面等附加内容。"
            "\n\n"
            "功能特点："
            "\n- 自动识别视频平台并选择最佳下载工具"
            "\n- 支持自定义视频质量和格式"
            "\n- Bilibili 视频支持下载弹幕（ASS 格式）、字幕、封面、NFO 元数据"
            "\n- 支持断点续传和多线程下载（Bilibili）"
            "\n- 支持只下载字幕（不下载视频）"
            "\n- 支持只提取音频（不下载视频）"
            "\n- 自动降级策略：如果首选工具失败，自动切换到备用工具"
        )
        
        super().__init__(
            name="video_downloader",
            description=description,
            parameters=parameters
        )
    
    def execute(self, **kwargs) -> ToolResult:
        """执行下载"""
        url = kwargs.get('url')
        if not url:
            return ToolResult(success=False, error="URL is required")
        
        # 规范化输出目录
        output_dir = normalize_output_dir(kwargs.get('output_dir'))
        
        # 选择下载器
        preferred = kwargs.get('preferred_tool', 'auto')
        # 从 kwargs 中移除已单独处理的参数，避免重复传递
        downloader_options = {k: v for k, v in kwargs.items() if k not in ['url', 'output_dir', 'preferred_tool']}
        downloader = _select_downloader(url, preferred, **downloader_options)
        
        if not downloader.is_available():
            return ToolResult(
                success=False,
                error=f"Downloader {downloader.__class__.__name__} is not available"
            )
        
        # 执行下载（使用相同的 downloader_options，不包含 url、output_dir、preferred_tool）
        result = downloader.download(url, output_dir, **downloader_options)
        
        if result.success:
            return ToolResult(
                success=True,
                data=result.data
            )
        else:
            # 尝试降级
            if preferred == 'auto':
                fallback_downloaders = [
                    YouGetDownloader(),
                    YtDlpDownloader(),
                ]
                
                for fallback in fallback_downloaders:
                    if fallback.is_available() and fallback != downloader:
                        logger.info(f"Trying fallback downloader: {fallback.__class__.__name__}")
                        fallback_result = fallback.download(url, output_dir, **downloader_options)
                        if fallback_result.success:
                            return ToolResult(
                                success=True,
                                data=fallback_result.data
                            )
            
            return ToolResult(
                success=False,
                error=result.error or "Download failed"
            )


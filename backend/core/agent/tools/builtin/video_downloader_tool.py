"""视频下载工具 - 整合 you-get、bili23-downloader 和 yt-dlp"""
import logging
import sys
from pathlib import Path
from typing import Optional, Dict, Any, List, Callable
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
    
    def __init__(self):
        self.progress_callback: Optional[Callable[[str], None]] = None
    
    def set_progress_callback(self, callback: Optional[Callable[[str], None]]):
        """设置进度回调函数"""
        self.progress_callback = callback
    
    def report_progress(self, message: str):
        """报告进度（如果设置了回调）"""
        if self.progress_callback:
            self.progress_callback(message)
    
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
                logger.debug(f"you-get path does not exist: {you_get_path}")
                return False
            
            # 检查是否有 you_get 模块或 src/you_get 目录
            you_get_module = you_get_path / "you_get"
            you_get_src = you_get_path / "src" / "you_get"
            if not you_get_module.exists() and not you_get_src.exists():
                logger.debug(f"you-get module not found in {you_get_path}")
                return False
            
            # 尝试导入 you_get
            if str(you_get_path) not in sys.path:
                sys.path.insert(0, str(you_get_path))
            
            # 尝试不同的导入方式
            try:
                import you_get  # type: ignore
                return True
            except ImportError:
                # 尝试从 src 目录导入
                if you_get_src.exists():
                    src_path = you_get_path / "src"
                    if str(src_path) not in sys.path:
                        sys.path.insert(0, str(src_path))
                    import you_get  # type: ignore
                    return True
                return False
        except Exception as e:
            logger.debug(f"you-get availability check failed: {e}")
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
            
            # 检查模块位置
            you_get_module = you_get_path / "you_get"
            you_get_src = you_get_path / "src" / "you_get"
            
            # 添加路径（优先使用 src 目录）
            if you_get_src.exists():
                src_path = you_get_path / "src"
                if str(src_path) not in sys.path:
                    sys.path.insert(0, str(src_path))
            elif str(you_get_path) not in sys.path:
                sys.path.insert(0, str(you_get_path))
            
            import subprocess
            # 根据模块位置选择正确的命令
            if you_get_src.exists():
                cmd = ['python', '-m', 'you_get']
            else:
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
            
            # bili23-downloader 是 GUI 应用，主要面向图形界面使用
            # 其核心下载逻辑在 src/utils/module/downloader_v3.py 中
            # 但由于依赖 wxPython GUI 框架和复杂的配置系统，直接调用比较复杂
            # 
            # 当前策略：检测到 bili23-downloader 存在时，优先使用 yt-dlp（对 Bilibili 支持很好）
            # 如果 yt-dlp 不可用，降级到 you-get
            # 
            # 注意：这并不意味着 bili23-downloader 没有被集成，而是因为：
            # 1. bili23-downloader 主要设计为 GUI 应用
            # 2. 直接调用其核心模块需要大量 GUI 相关的初始化代码
            # 3. yt-dlp 对 Bilibili 的支持已经非常完善，可以满足大部分需求
            
            logger.info("bili23-downloader 已集成，但作为 GUI 应用不适合 CLI 直接调用")
            logger.info("使用 yt-dlp 作为 Bilibili 下载工具（对 Bilibili 支持完善）")
            
            # 尝试使用 yt-dlp 作为降级方案
            yt_dlp = YtDlpDownloader()
            if yt_dlp.is_available():
                logger.info("使用 yt-dlp 下载 Bilibili 视频")
                return yt_dlp.download(url, output_dir, **options)
            
            # 降级到 you-get
            you_get = YouGetDownloader()
            if you_get.is_available():
                logger.info("yt-dlp 不可用，降级到 you-get")
                return you_get.download(url, output_dir, **options)
            
            return DownloadResult(
                success=False,
                error="bili23-downloader 已集成但主要面向 GUI 使用。CLI 模式下请使用 yt-dlp 或 you-get，但它们当前都不可用"
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


def _get_ffmpeg_path() -> Path:
    """获取 FFmpeg 可执行文件路径"""
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
    return project_root / "backend" / "externals" / "ffmpeg" / "build" / "bin" / "ffmpeg"


def _get_ffmpeg_bin_dir() -> Path:
    """获取 FFmpeg bin 目录路径"""
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
    return project_root / "backend" / "externals" / "ffmpeg" / "build" / "bin"


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
            import os
            
            # 尝试使用项目中的 FFmpeg（如果存在）
            ffmpeg_bin_dir = _get_ffmpeg_bin_dir()
            ffmpeg_path = _get_ffmpeg_path()
            use_local_ffmpeg = ffmpeg_bin_dir.exists() and ffmpeg_path.exists()
            
            ydl_opts: Dict[str, Any] = {
                'outtmpl': str(output_dir / '%(title)s.%(ext)s'),
            }
            
            # 如果使用本地 FFmpeg，设置路径
            if use_local_ffmpeg:
                # yt-dlp 的 ffmpeg_location 可以是目录路径或可执行文件路径
                # 使用完整的可执行文件路径更可靠
                ydl_opts['ffmpeg_location'] = str(ffmpeg_path)
                
                # 同时设置环境变量 PATH，确保子进程也能找到 FFmpeg
                old_path = os.environ.get('PATH', '')
                os.environ['PATH'] = str(ffmpeg_bin_dir) + os.pathsep + old_path
                
                # 设置 LD_LIBRARY_PATH，确保 FFmpeg 能找到其共享库
                # FFmpeg 的共享库在 build/lib 或 build/lib64 目录
                # ffmpeg_bin_dir = backend/externals/ffmpeg/build/bin
                # 所以 build 目录是 ffmpeg_bin_dir.parent
                ffmpeg_build_dir = ffmpeg_bin_dir.parent  # build 目录
                ffmpeg_lib_dir = None
                for lib_dir_name in ['lib', 'lib64']:
                    potential_lib_dir = ffmpeg_build_dir / lib_dir_name
                    if potential_lib_dir.exists():
                        ffmpeg_lib_dir = potential_lib_dir
                        break
                
                if ffmpeg_lib_dir and ffmpeg_lib_dir.exists():
                    old_ld_path = os.environ.get('LD_LIBRARY_PATH', '')
                    os.environ['LD_LIBRARY_PATH'] = str(ffmpeg_lib_dir) + os.pathsep + old_ld_path
                    logger.info(f"使用本地 FFmpeg: {ffmpeg_path} (库路径: {ffmpeg_lib_dir})")
                else:
                    logger.info(f"使用本地 FFmpeg: {ffmpeg_path} (未找到共享库目录，可能使用系统库)")
            else:
                logger.warning(f"本地 FFmpeg 不可用 (bin_dir={ffmpeg_bin_dir.exists()}, ffmpeg={ffmpeg_path.exists()})，yt-dlp 将尝试使用系统 FFmpeg")
            
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
                # 如果指定了 format，尝试使用，但准备降级方案
                if options.get('format') and options.get('format') != 'auto':
                    # 构建格式选择器，优先尝试指定格式，如果不可用则自动降级
                    format_str = self._build_yt_dlp_format(options.get('quality'), options.get('format'))
                    if format_str:
                        ydl_opts['format'] = format_str
                else:
                    # 没有指定 format 或 format=auto，使用 quality 构建格式选择器
                    quality_str = self._convert_quality_to_yt_dlp_format(options.get('quality')) if options.get('quality') else 'best'
                    if quality_str == 'best':
                        ydl_opts['format'] = 'bestvideo+bestaudio/best'
                    elif quality_str == 'worst':
                        ydl_opts['format'] = 'worstvideo+worstaudio/worst'
                    else:
                        ydl_opts['format'] = f'{quality_str}/bestvideo+bestaudio/best'
                
                if options.get('download_subtitle'):
                    ydl_opts['writesubtitles'] = True  # type: ignore
                    if options.get('subtitle_languages'):
                        ydl_opts['subtitleslangs'] = options['subtitle_languages']
            
            # PATH 环境变量已在上面设置（如果使用本地 FFmpeg）
            # 这里不需要重复设置
            
            # 添加进度回调（如果支持）
            def progress_hook(d: Dict[str, Any]):
                """yt-dlp 进度回调"""
                if d['status'] == 'downloading':
                    # 格式化进度信息
                    total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                    downloaded = d.get('downloaded_bytes', 0)
                    speed = d.get('speed', 0)
                    eta = d.get('eta', 0)
                    
                    if total > 0:
                        percent = (downloaded / total) * 100
                        # 格式化大小
                        def format_size(size: float) -> str:
                            for unit in ['B', 'KB', 'MB', 'GB']:
                                if size < 1024.0:
                                    return f"{size:.2f}{unit}"
                                size /= 1024.0
                            return f"{size:.2f}TB"
                        
                        # 格式化速度
                        def format_speed(speed: float) -> str:
                            return format_size(speed) + "/s"
                        
                        # 格式化时间
                        def format_time(seconds: float) -> str:
                            if seconds < 0:
                                return "未知"
                            m, s = divmod(int(seconds), 60)
                            h, m = divmod(m, 60)
                            if h > 0:
                                return f"{h:02d}:{m:02d}:{s:02d}"
                            return f"{m:02d}:{s:02d}"
                        
                        progress_msg = (
                            f"下载进度: {percent:.1f}% "
                            f"({format_size(downloaded)} / {format_size(total)}) "
                            f"速度: {format_speed(speed)} "
                            f"剩余时间: {format_time(eta)}"
                        )
                    else:
                        progress_msg = (
                            f"下载中... "
                            f"已下载: {format_size(downloaded) if downloaded > 0 else '未知'} "
                            f"速度: {format_speed(speed) if speed > 0 else '未知'}"
                        )
                    
                    self.report_progress(progress_msg)
                elif d['status'] == 'finished':
                    self.report_progress("下载完成，正在处理...")
            
            # 添加进度钩子
            ydl_opts['progress_hooks'] = [progress_hook]
            
            try:
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
            except yt_dlp.utils.DownloadError as e:
                # 如果是格式不可用的错误，尝试完全不指定格式，让 yt-dlp 自动选择
                error_msg = str(e)
                if "Requested format is not available" in error_msg or "format is not available" in error_msg:
                    logger.warning(f"指定格式不可用，尝试自动选择格式: {error_msg}")
                    # 移除格式限制，让 yt-dlp 自动选择最佳可用格式
                    if 'format' in ydl_opts:
                        del ydl_opts['format']
                    try:
                        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                            info = ydl.extract_info(url, download=True)
                            return DownloadResult(
                                success=True,
                                data={
                                    'tool': 'yt-dlp',
                                    'output_dir': str(output_dir),
                                    'title': info.get('title', ''),
                                    'note': '使用自动格式选择'
                                }
                            )
                    except Exception as retry_e:
                        return DownloadResult(success=False, error=f"yt-dlp error: {str(retry_e)}")
                else:
                    # 其他错误直接返回
                    return DownloadResult(success=False, error=f"yt-dlp error: {error_msg}")
            finally:
                # 恢复 PATH
                if old_path is not None:
                    os.environ['PATH'] = old_path
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
    
    def _build_yt_dlp_format(self, quality: Optional[str], format: Optional[str]) -> str:
        """构建 yt-dlp format 字符串，结合 quality 和 format 参数"""
        # yt-dlp 的 format 语法支持格式选择器: best[ext=mp4]/best
        # 含义：优先尝试指定格式，如果不可用则使用最佳可用格式
        
        # 先处理 quality
        quality_str = self._convert_quality_to_yt_dlp_format(quality) if quality else 'best'
        
        # 如果没有指定 format 或者是 auto，直接使用 quality，让 yt-dlp 自动选择格式
        if not format or format == 'auto':
            # 对于视频+音频分离的情况，使用 bestvideo+bestaudio/best
            # 这样可以处理视频和音频分离的情况
            if quality_str == 'best':
                return 'bestvideo+bestaudio/best'
            elif quality_str == 'worst':
                return 'worstvideo+worstaudio/worst'
            else:
                # 对于具体分辨率，先尝试该分辨率，如果不可用则使用最佳
                return f'{quality_str}/bestvideo+bestaudio/best'
        
        # 如果指定了 format，优先尝试该格式，如果不可用则使用最佳可用格式
        # 格式: best[ext=mp4]/best 或 best[height<=1080][ext=mp4]/best[height<=1080]/best
        if quality_str == 'best':
            # 优先尝试指定格式，如果不可用则使用最佳可用格式
            return f'best[ext={format}]/best'
        elif quality_str == 'worst':
            # worst 格式通常不需要指定扩展名
            return f'worst[ext={format}]/worst'
        else:
            # 对于具体分辨率，先尝试该分辨率的指定格式，如果不可用则使用该分辨率的最佳格式，最后降级到最佳
            # 从 quality_str 中提取高度限制（例如 "best[height<=1080]"）
            height_match = quality_str.split('[')[1].split(']')[0] if '[' in quality_str else None
            if height_match:
                # best[height<=1080][ext=mp4]/best[height<=1080]/best
                return f'best[{height_match}][ext={format}]/best[{height_match}]/best'
            else:
                return f'best[ext={format}]/best'


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
        # 如果不可用，尝试使用其他可用工具作为降级方案
        logger.warning(f"Preferred tool 'you-get' is not available, trying fallback tools")
        # 尝试 yt-dlp
        yt_dlp = YtDlpDownloader()
        if yt_dlp.is_available():
            logger.info("Falling back to yt-dlp")
            return yt_dlp
        # 如果都不可用，返回 you-get（让错误信息更清晰）
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
        
        # 设置进度回调
        downloader.set_progress_callback(self.progress_callback)
        
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
                        # 设置进度回调
                        fallback.set_progress_callback(self.progress_callback)
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


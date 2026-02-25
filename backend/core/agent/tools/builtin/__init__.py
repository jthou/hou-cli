"""内置工具模块"""

from .weather_tool import WeatherTool
from .file_search_tool import FileSearchTool
from .mediawiki_tool import MediaWikiTool
from .gvim_tool import GvimTool
from .google_search_tool import GoogleSearchTool
from .wikipedia_tool import WikipediaTool

# 浏览器工具（可选，需要安装 browser-use）
try:
    from .browser_tool import BrowserTool
    _browser_available = True
except ImportError:
    _browser_available = False
    BrowserTool = None

# 文件整理工具（可选，需要安装 Local-File-Organizer）
try:
    from .file_organizer_tool import FileOrganizerTool
    _file_organizer_available = True
except ImportError:
    _file_organizer_available = False
    FileOrganizerTool = None

# PDF解析工具（可选，需要安装相应的后端）
try:
    from .pdf_parser_tool import PDFParserTool
    _pdf_parser_available = True
except ImportError:
    _pdf_parser_available = False
    PDFParserTool = None

# 知乎直达工具（需要 browser 工具支持）
try:
    from .zhihu_zhida_tool import ZhihuZhidaTool
    _zhihu_zhida_available = True
except ImportError:
    _zhihu_zhida_available = False
    ZhihuZhidaTool = None

# 视频下载工具（需要 you-get 或 yt-dlp）
try:
    from .video_downloader_tool import VideoDownloaderTool
    _video_downloader_available = True
except ImportError:
    _video_downloader_available = False
    VideoDownloaderTool = None

# FFmpeg 工具（需要 FFmpeg）
try:
    from .ffmpeg_tool import FFmpegTool
    _ffmpeg_available = True
except ImportError:
    _ffmpeg_available = False
    FFmpegTool = None

# Whisper 工具（需要 openai-whisper）
try:
    from .whisper_tool import WhisperTool
    _whisper_available = True
except ImportError:
    _whisper_available = False
    WhisperTool = None

# 构建 __all__ 列表
__all__ = [
    "WeatherTool",
    "FileSearchTool",
    "MediaWikiTool",
    "GvimTool",
    "GoogleSearchTool",
    "WikipediaTool",
]

if _browser_available:
    __all__.append("BrowserTool")

if _file_organizer_available:
    __all__.append("FileOrganizerTool")

if _pdf_parser_available:
    __all__.append("PDFParserTool")

if _zhihu_zhida_available:
    __all__.append("ZhihuZhidaTool")

if _video_downloader_available:
    __all__.append("VideoDownloaderTool")

if _ffmpeg_available:
    __all__.append("FFmpegTool")

if _whisper_available:
    __all__.append("WhisperTool")

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

# Jupyter 工具（可选，需要安装 jupyter-client）
try:
    from .jupyter_tool import JupyterTool
    _jupyter_available = True
except ImportError:
    _jupyter_available = False
    JupyterTool = None

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

if _jupyter_available:
    __all__.append("JupyterTool")

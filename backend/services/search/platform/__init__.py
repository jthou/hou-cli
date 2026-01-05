"""平台适配器"""
from backend.services.search.platform.base import PlatformAdapter
from backend.services.search.platform.macos_search import MacOSSearchAdapter

try:
    from backend.services.search.platform.linux_search import LinuxSearchAdapter
    __all__ = ["PlatformAdapter", "MacOSSearchAdapter", "LinuxSearchAdapter"]
except ImportError:
    __all__ = ["PlatformAdapter", "MacOSSearchAdapter"]


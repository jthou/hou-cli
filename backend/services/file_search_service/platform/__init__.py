"""平台适配器"""
from backend.services.file_search_service.platform.base import PlatformAdapter
from backend.services.file_search_service.platform.macos_search import MacOSSearchAdapter

try:
    from backend.services.file_search_service.platform.linux_search import LinuxSearchAdapter
    __all__ = ["PlatformAdapter", "MacOSSearchAdapter", "LinuxSearchAdapter"]
except ImportError:
    __all__ = ["PlatformAdapter", "MacOSSearchAdapter"]


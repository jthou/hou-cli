"""平台适配器模块"""

from .base import PlatformAdapter
from .macos_search import MacOSSearchAdapter

__all__ = [
    "PlatformAdapter",
    "MacOSSearchAdapter",
]



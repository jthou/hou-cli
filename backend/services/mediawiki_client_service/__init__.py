"""MediaWiki 服务模块"""

from .client import MediaWikiClientService
from .models import MediaWikiPage, MediaWikiSearchResult, UnifiedSearchResult
from .sync_service import MediaWikiSyncService
from .unified_search import UnifiedSearchService
from .utils import format_page_url, format_page_link, format_page_list_with_links

__all__ = [
    "MediaWikiClientService",
    "MediaWikiPage",
    "MediaWikiSearchResult",
    "UnifiedSearchResult",
    "MediaWikiSyncService",
    "UnifiedSearchService",
    "format_page_url",
    "format_page_link",
    "format_page_list_with_links",
]


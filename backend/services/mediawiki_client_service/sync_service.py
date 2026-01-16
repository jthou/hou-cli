"""MediaWiki 同步服务"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
import json

from .client import MediaWikiClientService
from .models import MediaWikiPage

logger = logging.getLogger(__name__)


class MediaWikiSyncService:
    """MediaWiki 知识库同步服务
    
    将 MediaWiki 页面同步到本地知识库，支持全量和增量同步。
    """
    
    def __init__(
        self,
        client: Optional[MediaWikiClientService] = None,
        sync_data_dir: Optional[Path] = None
    ):
        """初始化同步服务
        
        Args:
            client: MediaWiki 客户端（如果为 None，会创建新实例）
            sync_data_dir: 同步数据存储目录
        """
        self.client = client or MediaWikiClientService()
        if not self.client._connected:
            self.client.connect()
        
        # 同步数据目录
        from shared.platform_utils import get_app_data_dir
        self.sync_data_dir = sync_data_dir or (get_app_data_dir() / "mediawiki_sync")
        self.sync_data_dir.mkdir(parents=True, exist_ok=True)
        
        # 同步状态文件
        self.status_file = self.sync_data_dir / "sync_status.json"
        self.sync_status = self._load_sync_status()
    
    def _load_sync_status(self) -> Dict[str, Any]:
        """加载同步状态"""
        if self.status_file.exists():
            try:
                return json.loads(self.status_file.read_text())
            except Exception as e:
                logger.warning(f"Failed to load sync status: {e}")
        
        return {
            "last_sync": None,
            "synced_pages": {},
            "total_pages": 0,
            "last_full_sync": None
        }
    
    def _save_sync_status(self):
        """保存同步状态"""
        self.status_file.write_text(
            json.dumps(self.sync_status, indent=2, ensure_ascii=False, default=str)
        )
    
    def sync_all_pages(
        self,
        namespace: int = 0,
        force: bool = False
    ) -> Dict[str, Any]:
        """同步所有页面
        
        Args:
            namespace: 命名空间（0 为主命名空间）
            force: 是否强制全量同步（忽略已同步的页面）
            
        Returns:
            Dict: 同步结果统计
        """
        logger.info("Starting full sync of all pages...")
        
        all_pages = self.client.get_all_pages(namespace=namespace)
        total = len(all_pages)
        synced = 0
        updated = 0
        failed = 0
        
        for page_title in all_pages:
            try:
                result = self.sync_page(page_title, force=force)
                if result["status"] == "synced":
                    synced += 1
                elif result["status"] == "updated":
                    updated += 1
            except Exception as e:
                logger.error(f"Failed to sync page '{page_title}': {e}")
                failed += 1
        
        # 更新同步状态
        self.sync_status["last_sync"] = datetime.now().isoformat()
        self.sync_status["last_full_sync"] = datetime.now().isoformat()
        self.sync_status["total_pages"] = total
        self._save_sync_status()
        
        logger.info(f"Full sync completed: {synced} synced, {updated} updated, {failed} failed")
        
        return {
            "total": total,
            "synced": synced,
            "updated": updated,
            "failed": failed,
            "last_sync": self.sync_status["last_sync"]
        }
    
    def sync_page(
        self,
        title: str,
        force: bool = False
    ) -> Dict[str, Any]:
        """同步单个页面
        
        Args:
            title: 页面标题
            force: 是否强制同步（即使已同步）
            
        Returns:
            Dict: 同步结果
        """
        # 获取页面
        page = self.client.get_page(title)
        if not page:
            return {
                "status": "not_found",
                "title": title,
                "message": f"Page '{title}' not found"
            }
        
        # 检查是否需要同步
        if not force:
            synced_info = self.sync_status["synced_pages"].get(title)
            if synced_info:
                # 检查修订版本是否更新
                if synced_info.get("revision_id") == page.revision_id:
                    return {
                        "status": "unchanged",
                        "title": title,
                        "message": "Page is up to date"
                    }
        
        # 保存页面内容到本地
        page_file = self.sync_data_dir / f"{title.replace('/', '_')}.json"
        page_data = {
            "title": page.title,
            "content": page.content,
            "revision_id": page.revision_id,
            "last_modified": page.last_modified.isoformat(),
            "categories": page.categories,
            "links": page.links,
            "url": page.url,
            "synced_at": datetime.now().isoformat()
        }
        page_file.write_text(
            json.dumps(page_data, indent=2, ensure_ascii=False)
        )
        
        # 更新同步状态
        self.sync_status["synced_pages"][title] = {
            "revision_id": page.revision_id,
            "last_modified": page.last_modified.isoformat(),
            "synced_at": datetime.now().isoformat()
        }
        self._save_sync_status()
        
        # TODO: 将页面内容添加到知识库向量数据库
        # 这里需要调用知识库服务将页面内容向量化并存储
        
        status = "updated" if title in self.sync_status["synced_pages"] else "synced"
        
        return {
            "status": status,
            "title": title,
            "revision_id": page.revision_id,
            "message": f"Page '{title}' synced successfully"
        }
    
    def sync_category(
        self,
        category: str,
        force: bool = False
    ) -> Dict[str, Any]:
        """同步分类下的所有页面
        
        Args:
            category: 分类名称（如 "Category:技术文档"）
            force: 是否强制同步
            
        Returns:
            Dict: 同步结果统计
        """
        logger.info(f"Syncing category: {category}")
        
        # 获取分类下的所有页面
        # 注意：mwclient 可能需要特殊处理来获取分类下的页面
        # 这里使用搜索来查找分类下的页面
        search_query = f"incategory:{category}"
        search_results = self.client.search_pages(search_query, limit=1000)
        
        synced = 0
        updated = 0
        failed = 0
        
        for result in search_results:
            try:
                sync_result = self.sync_page(result.title, force=force)
                if sync_result["status"] == "synced":
                    synced += 1
                elif sync_result["status"] == "updated":
                    updated += 1
            except Exception as e:
                logger.error(f"Failed to sync page '{result.title}': {e}")
                failed += 1
        
        return {
            "category": category,
            "total": len(search_results),
            "synced": synced,
            "updated": updated,
            "failed": failed
        }
    
    def get_sync_status(self) -> Dict[str, Any]:
        """获取同步状态
        
        Returns:
            Dict: 同步状态信息
        """
        return {
            "last_sync": self.sync_status.get("last_sync"),
            "last_full_sync": self.sync_status.get("last_full_sync"),
            "total_pages": self.sync_status.get("total_pages", 0),
            "synced_pages_count": len(self.sync_status.get("synced_pages", {})),
            "synced_pages": list(self.sync_status.get("synced_pages", {}).keys())
        }
    
    def get_synced_page(self, title: str) -> Optional[Dict[str, Any]]:
        """获取已同步的页面内容
        
        Args:
            title: 页面标题
            
        Returns:
            Optional[Dict]: 页面数据，如果不存在返回 None
        """
        page_file = self.sync_data_dir / f"{title.replace('/', '_')}.json"
        if page_file.exists():
            return json.loads(page_file.read_text())
        return None


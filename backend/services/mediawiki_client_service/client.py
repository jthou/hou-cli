"""MediaWiki 客户端服务"""

import os
import logging
import time
import threading
from typing import List, Optional, Dict, Any
from datetime import datetime
from urllib.parse import urlparse
import mwclient
from mwclient.errors import APIError, LoginError

from .models import MediaWikiPage, MediaWikiSearchResult

logger = logging.getLogger(__name__)


class MediaWikiClientError(Exception):
    """MediaWiki 客户端错误"""

    def __init__(self, message, *, no_retry=False):
        super().__init__(message)
        self.no_retry = bool(no_retry)


class MediaWikiClientService:
    """MediaWiki API 客户端服务
    
    封装 mwclient 库，提供 MediaWiki 操作的统一接口。
    支持基本认证和 Bot 认证。
    """
    
    def __init__(
        self,
        url: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        bot_name: Optional[str] = None,
        bot_password: Optional[str] = None
    ):
        """初始化 MediaWiki 客户端
        
        Args:
            url: MediaWiki 网站 URL（如 http://www.jthou.com/mediawiki）
            username: 用户名（基本认证）
            password: 密码（基本认证）
            bot_name: Bot 用户名（优先使用）
            bot_password: Bot 密码（优先使用）
        """
        def _cred(v: Optional[str]) -> Optional[str]:
            if v is None:
                return None
            s = str(v).strip()
            return s if s else None

        self.url = (url or os.getenv("MEDIAWIKI_URL", "http://www.jthou.com/mediawiki") or "").strip()
        self.username = _cred(username or os.getenv("MEDIAWIKI_USERNAME"))
        self.password = _cred(password or os.getenv("MEDIAWIKI_PASSWORD"))
        self.bot_name = _cred(bot_name or os.getenv("MEDIAWIKI_BOT_NAME"))
        self.bot_password = _cred(bot_password or os.getenv("MEDIAWIKI_BOT_PASSWORD"))
        
        self.site: Optional[mwclient.Site] = None
        self._connected = False
        # mwclient.Site 维护 cookie/token 缓存，非线程安全；FastAPI 并发请求可能导致 token 竞态。
        # 用同一把锁串行化 connect/upload/edit 等写操作，降低 badtoken 概率。
        self._site_lock = threading.RLock()
    
    def connect(self) -> bool:
        """连接到 MediaWiki
        
        Returns:
            bool: 连接是否成功
            
        Raises:
            MediaWikiClientError: 连接失败时抛出
        """
        with self._site_lock:
            try:
                # 解析 URL，提取协议、主机和路径
                parsed = urlparse(self.url)
                scheme = parsed.scheme or "https"  # 默认使用 https
                host = parsed.netloc or parsed.hostname
                path = parsed.path.rstrip("/") or "/"

                # mwclient.Site() 需要 (host, path, scheme) 参数
                # 如果路径是 /mediawiki，API 端点应为 /mediawiki/api.php；此处确保 path 以 / 结尾
                logger.debug(
                    f"Connecting to MediaWiki: scheme={scheme}, host={host}, path={path}"
                )

                def _new_site() -> None:
                    if path == "/" or path == "":
                        self.site = mwclient.Site(host, scheme=scheme)
                    else:
                        path_with_slash = path if path.endswith("/") else path + "/"
                        self.site = mwclient.Site(host, path=path_with_slash, scheme=scheme)

                # MEDIAWIKI_USE_BOT_PASSWORD=false：完全不尝试机器人密码
                _use_bot_pw = (os.getenv("MEDIAWIKI_USE_BOT_PASSWORD") or "true").strip().lower() not in (
                    "0",
                    "false",
                    "no",
                    "off",
                )
                # 时间：2026-04-11；理由：MCP/脚本常遇「Bot 在 Wiki 侧须重置」导致整段失败，而主账号仍可用；方法：MEDIAWIKI_LOGIN_ORDER=user_first 时先主账号再 Bot；后端未设时默认 bot_first 保持兼容
                _order = (os.getenv("MEDIAWIKI_LOGIN_ORDER") or "bot_first").strip().lower()
                _user_first = _order in ("user_first", "user", "account_first")
                _has_user = bool(self.username and self.password)
                _has_bot = bool(_use_bot_pw and self.bot_name and self.bot_password)

                if not _has_user and not _has_bot:
                    _new_site()
                    logger.warning(
                        "Connected to MediaWiki without authentication. "
                        "Private wikis will fail with readapidenied. "
                        "Set MEDIAWIKI_BOT_NAME/MEDIAWIKI_BOT_PASSWORD or MEDIAWIKI_USERNAME/MEDIAWIKI_PASSWORD."
                    )
                elif _user_first:
                    if _has_user:
                        _new_site()
                        try:
                            self.site.login(self.username, self.password)
                            logger.info(f"Connected to MediaWiki as user: {self.username}")
                        except LoginError as e_user:
                            logger.warning(f"User login failed: {e_user}, trying bot if configured")
                            if _has_bot:
                                _new_site()
                                self.site.login(self.bot_name, self.bot_password)
                                logger.info(f"Connected to MediaWiki as bot: {self.bot_name}")
                            else:
                                raise MediaWikiClientError(f"Authentication failed: {e_user}") from e_user
                    elif _has_bot:
                        _new_site()
                        self.site.login(self.bot_name, self.bot_password)
                        logger.info(f"Connected to MediaWiki as bot: {self.bot_name}")
                    else:
                        _new_site()
                        logger.warning(
                            "Connected to MediaWiki without authentication (no valid credentials)."
                        )
                else:
                    # bot_first：与历史行为一致，Bot 失败后新建 Site 再试主账号
                    if _has_bot:
                        _new_site()
                        try:
                            self.site.login(self.bot_name, self.bot_password)
                            logger.info(f"Connected to MediaWiki as bot: {self.bot_name}")
                        except LoginError as e:
                            logger.warning(f"Bot login failed: {e}, trying regular login")
                            if _has_user:
                                _new_site()
                                self.site.login(self.username, self.password)
                                logger.info(f"Connected to MediaWiki as user: {self.username}")
                            else:
                                raise MediaWikiClientError(f"Authentication failed: {e}") from e
                    elif _has_user:
                        _new_site()
                        self.site.login(self.username, self.password)
                        logger.info(f"Connected to MediaWiki as user: {self.username}")
                    else:
                        _new_site()
                        logger.warning(
                            "Connected to MediaWiki without authentication (no valid credentials)."
                        )

                self._connected = True
                return True
            except Exception as e:
                logger.error(f"Failed to connect to MediaWiki: {e}")
                raise MediaWikiClientError(f"Connection failed: {str(e)}")
    
    def verify_read_access(self) -> tuple[bool, str]:
        """验证是否有读权限（私有 Wiki 无认证会 readapidenied）。
        时间：2025-03-14；理由：readapidenied 排查需区分连接成功与权限不足；方法：调用 query meta=siteinfo。
        Returns:
            (success, message)
        """
        self._ensure_connected()
        try:
            self.site.api("query", meta="siteinfo")
            return True, "ok"
        except Exception as e:
            return False, str(e)
    
    def _ensure_connected(self):
        """确保已连接"""
        if not self._connected or self.site is None:
            self.connect()
    
    def _retry_on_error(self, func, max_retries: int = 3, delay: float = 1.0):
        """错误重试装饰器。readapidenied 时强制重连（私有 Wiki 会话过期常见）"""
        for attempt in range(max_retries):
            try:
                # 串行化 mwclient 调用，避免并发下 token/cookie 竞态导致 badtoken
                with self._site_lock:
                    return func()
            except (APIError, ConnectionError, TimeoutError, MediaWikiClientError) as e:
                if isinstance(e, MediaWikiClientError) and getattr(e, "no_retry", False):
                    raise
                err_str = str(e).lower()
                api_code = getattr(e, "code", None)
                api_code_l = (str(api_code).lower() if api_code is not None else "")
                # 会话/权限相关：重连（含重新登录）后再试
                # - readapidenied: 私有 Wiki 未认证/会话过期
                # - badtoken: CSRF token 失效（常见于登录态丢失/过期）
                # - notloggedin: 会话过期或未登录
                if (
                    (
                        "readapidenied" in err_str
                        or "badtoken" in err_str
                        or "notloggedin" in err_str
                        or api_code_l in ("readapidenied", "badtoken", "notloggedin")
                    )
                    and (self.bot_name or self.username)
                    and attempt < max_retries - 1
                ):
                    logger.warning("MediaWiki 会话/权限异常（readapidenied/badtoken/notloggedin），重连后重试…")
                    with self._site_lock:
                        self._connected = False
                        self.site = None
                        self.connect()
                    time.sleep(delay * (attempt + 1))
                    continue
                if attempt < max_retries - 1:
                    logger.warning(f"Attempt {attempt + 1} failed: {e}, retrying...")
                    time.sleep(delay * (attempt + 1))
                else:
                    raise MediaWikiClientError(f"Operation failed after {max_retries} attempts: {str(e)}")
    
    def search_pages(
        self,
        query: str,
        limit: int = 20,
        namespace: int = 0
    ) -> List[MediaWikiSearchResult]:
        """搜索页面
        
        Args:
            query: 搜索关键词
            limit: 结果数量限制
            namespace: 命名空间（0 为主命名空间）
            
        Returns:
            List[MediaWikiSearchResult]: 搜索结果列表
        """
        self._ensure_connected()
        
        def _search():
            results = []
            for i, result in enumerate(self.site.search(query, namespace=namespace, limit=limit)):
                title = result.get("title", "")
                results.append(MediaWikiSearchResult(
                    title=title,
                    snippet=result.get("snippet", ""),
                    url=f"{self.url}/index.php/{title.replace(' ', '_')}",
                    score=1.0 / (i + 1),  # 排名分数：第 1 名 1.0，第 2 名 0.5，…（API 已按相关性排序）
                    size=result.get("size"),
                    word_count=result.get("wordcount")
                ))
            return results
        
        return self._retry_on_error(_search)
    
    def get_page(self, title: str) -> Optional[MediaWikiPage]:
        """获取页面内容
        
        Args:
            title: 页面标题
            
        Returns:
            Optional[MediaWikiPage]: 页面对象，如果不存在返回 None
        """
        self._ensure_connected()
        
        def _get_page():
            try:
                page = self.site.Pages[title]
                
                if not page.exists:
                    return None
                
                # 获取页面内容
                content = page.text()
                
                # 获取页面信息（使用 API 查询）
                page_info = self.site.api(
                    'query',
                    prop='info',
                    titles=title,
                    inprop='url|timestamp|revid'
                )
                
                # 解析页面信息
                pages_data = page_info.get('query', {}).get('pages', {})
                page_data = None
                for page_id, data in pages_data.items():
                    page_data = data
                    break
                
                if not page_data:
                    return None
                
                # 获取分类
                categories = [cat.name for cat in page.categories()]
                
                # 获取链接
                links = [link.name for link in page.links()]
                
                # 解析最后修改时间
                touched = page_data.get("touched", "")
                if touched:
                    try:
                        # MediaWiki 时间格式: 2024-01-01T12:00:00Z
                        last_modified = datetime.strptime(touched, "%Y-%m-%dT%H:%M:%SZ")
                    except ValueError:
                        last_modified = datetime.now()
                else:
                    last_modified = datetime.now()
                
                return MediaWikiPage(
                    title=title,
                    content=content,
                    revision_id=page_data.get("lastrevid", 0),
                    last_modified=last_modified,
                    categories=categories,
                    links=links,
                    url=page_data.get("fullurl", f"{self.url}/index.php/{title.replace(' ', '_')}")
                )
            except KeyError:
                return None
        
        return self._retry_on_error(_get_page)
    
    def edit_page(
        self,
        title: str,
        content: str,
        summary: str = "",
        minor: bool = False
    ) -> bool:
        """编辑页面
        
        Args:
            title: 页面标题
            content: 新内容（wikitext）
            summary: 编辑摘要
            minor: 是否为小编辑
            
        Returns:
            bool: 编辑是否成功
            
        Raises:
            MediaWikiClientError: 编辑失败时抛出
        """
        self._ensure_connected()
        
        def _edit():
            try:
                page = self.site.Pages[title]
                result = page.save(content, summary=summary, minor=minor)
                
                if result.get("result") == "Success":
                    logger.info(f"Successfully edited page: {title}")
                    return True
                else:
                    error = result.get("error", {}).get("info", "Unknown error")
                    raise MediaWikiClientError(f"Edit failed: {error}")
            except APIError as e:
                raise MediaWikiClientError(f"API error: {str(e)}")
        
        return self._retry_on_error(_edit)
    
    def create_page(
        self,
        title: str,
        content: str,
        summary: str = ""
    ) -> bool:
        """创建新页面
        
        Args:
            title: 页面标题
            content: 页面内容（wikitext）
            summary: 创建摘要
            
        Returns:
            bool: 创建是否成功
        """
        # 检查页面是否已存在
        existing_page = self.get_page(title)
        if existing_page:
            raise MediaWikiClientError(f"Page '{title}' already exists")
        
        return self.edit_page(title, content, summary)
    
    def upload_file(
        self,
        filename: str,
        file_path: str,
        description: str = "",
        ignore_warnings: bool = False
    ) -> bool:
        """上传文件
        
        Args:
            filename: 文件名（在 Wiki 中的名称）
            file_path: 本地文件路径
            description: 文件描述
            ignore_warnings: 是否忽略警告
            
        Returns:
            bool: 上传是否成功
        """
        self._ensure_connected()
        
        def _upload():
            try:
                with open(file_path, 'rb') as f:
                    result = self.site.upload(
                        file=f,
                        filename=filename,
                        description=description,
                        ignore=ignore_warnings
                    )
                
                if result.get("result") == "Success":
                    logger.info(f"Successfully uploaded file: {filename}")
                    return True
                else:
                    error = result.get("error", {}).get("info", "Unknown error")
                    raise MediaWikiClientError(f"Upload failed: {error}")
            except FileNotFoundError:
                raise MediaWikiClientError(f"File not found: {file_path}")
            except APIError as e:
                err = str(e)
                if "valid json" in err.lower() or "json response" in err.lower():
                    probe = f"{self.url.rstrip('/')}/api.php?action=query&meta=siteinfo&format=json"
                    raise MediaWikiClientError(
                        f"{err} — 多为 MEDIAWIKI_URL 路径不对、PHP/Wiki 报错输出 HTML、或反代返回 502/登录页。"
                        f" 请在浏览器打开「{probe}」应看到 JSON；若此处正常仅上传失败，查 PHP/nginx 日志与 $wgUploadDirectory 权限。",
                        no_retry=True,
                    ) from e
                raise MediaWikiClientError(f"API error: {err}") from e
            except Exception as e:
                err = str(e)
                if "valid json" in err.lower() or "json response" in err.lower():
                    probe = f"{self.url.rstrip('/')}/api.php?action=query&meta=siteinfo&format=json"
                    raise MediaWikiClientError(
                        f"{err} — 多为 MEDIAWIKI_URL 路径不对、PHP/Wiki 报错输出 HTML、或反代返回 502。"
                        f" 请在浏览器打开「{probe}」应看到 JSON。",
                        no_retry=True,
                    ) from e
                raise
        
        return self._retry_on_error(_upload)
    
    def get_categories(self, title: str) -> List[str]:
        """获取页面的分类
        
        Args:
            title: 页面标题
            
        Returns:
            List[str]: 分类列表
        """
        page = self.get_page(title)
        if page:
            return page.categories
        return []

    def parse_wikitext(self, wikitext: str, title: Optional[str] = None) -> str:
        """使用 MediaWiki parse API 将 wikitext 解析为 HTML。

        用于预览复杂表格、模板等，避免前端 wikiToMd 转换丢失内容。
        时间：2025-03-13；理由：复杂 MediaWiki 表格经 wikiToMd 后丢失列表、合并单元格等；
        方法：调用 action=parse，prop=text，contentmodel=wikitext。

        Args:
            wikitext: 要解析的 wikitext 内容
            title: 可选页面标题，用于 {{PAGENAME}} 等魔术字

        Returns:
            str: 解析后的 HTML 字符串

        Raises:
            MediaWikiClientError: 解析失败时抛出
        """
        self._ensure_connected()

        def _parse():
            params = {
                "text": wikitext,
                "contentmodel": "wikitext",
                "prop": "text",
                "format": "json",
            }
            if title:
                params["title"] = title
            data = self.site.api("parse", **params)
            parse_data = data.get("parse", {})
            text_data = parse_data.get("text", {})
            html = text_data.get("*", "")
            if not html:
                raise MediaWikiClientError("Parse API returned empty HTML")
            return html

        return self._retry_on_error(_parse)

    def get_recently_changed_pages(
        self,
        limit: int = 10,
        namespace: int = 0
    ) -> List[str]:
        """获取最近修改的页面标题列表（按修改时间倒序，去重）

        Args:
            limit: 返回的页面数量
            namespace: 命名空间（0 为主命名空间）

        Returns:
            List[str]: 页面标题列表
        """
        self._ensure_connected()

        def _get_recent():
            seen = set()
            result = []
            # 多请求一些以应对同一页面多次编辑
            rclimit = min(500, max(limit * 5, 50))
            data = self.site.api(
                "query",
                list="recentchanges",
                rcnamespace=namespace,
                rctype="edit|new",
                rclimit=rclimit,
                rcprop="title",
            )
            for rc in data.get("query", {}).get("recentchanges", []):
                title = rc.get("title", "").strip()
                if title and title not in seen:
                    seen.add(title)
                    result.append(title)
                    if len(result) >= limit:
                        break
            return result

        return self._retry_on_error(_get_recent)

    def get_all_pages(
        self,
        namespace: int = 0,
        limit: Optional[int] = None
    ) -> List[str]:
        """获取所有页面标题
        
        Args:
            namespace: 命名空间
            limit: 数量限制（None 表示不限制）
            
        Returns:
            List[str]: 页面标题列表
        """
        self._ensure_connected()
        
        def _get_all():
            pages = []
            count = 0
            for page in self.site.allpages(namespace=namespace):
                pages.append(page.name)
                count += 1
                if limit and count >= limit:
                    break
            return pages
        
        return self._retry_on_error(_get_all)
    
    def get_page_info(self, title: str) -> Optional[Dict[str, Any]]:
        """获取页面信息

        Args:
            title: 页面标题

        Returns:
            Optional[Dict]: 页面信息字典
        """
        page = self.get_page(title)
        if page:
            return {
                "title": page.title,
                "revision_id": page.revision_id,
                "last_modified": page.last_modified.isoformat(),
                "categories": page.categories,
                "links_count": len(page.links),
                "url": page.url
            }
        return None

    # -------------------------------------------------------------------------
    # 看板 API（KanbanBoard 扩展：action=kanban）
    # -------------------------------------------------------------------------

    def _kanban_api(self, kanban_action: str, **kwargs: Any) -> Dict[str, Any]:
        """调用看板扩展 API。需已 connect() 且已登录。"""
        self._ensure_connected()
        result = self.site.api(
            "kanban", kanban_action=kanban_action, **kwargs
        )
        if "error" in result:
            raise MediaWikiClientError(
                result.get("error", {}).get("info", str(result))
            )
        return result

    def kanban_get_boards(
        self, filter_status: str = "active"
    ) -> List[Dict[str, Any]]:
        """获取看板列表。filter_status: active|hidden|archived|deleted|all"""
        data = self._kanban_api("getboards", filter_status=filter_status)
        return data.get("boards", [])

    def kanban_get_board(self, board_id: int) -> Dict[str, Any]:
        """获取单个看板详情（含列、任务、里程碑）。"""
        data = self._kanban_api("getboard", board_id=board_id)
        board = data.get("board")
        if not board:
            raise MediaWikiClientError("Board not found or no permission")
        return board

    def kanban_create_task(
        self,
        board_id: int,
        column_id: int,
        title: str,
        description: str = "",
        priority: str = "medium",
        due_date: Optional[str] = None,
    ) -> int:
        """在看板指定列创建任务。priority: low|medium|high|urgent。返回 task_id。"""
        data = self._kanban_api(
            "createtask",
            board_id=board_id,
            column_id=column_id,
            title=title.strip(),
            description=(description or "").strip(),
            priority=priority,
            due_date=due_date or "",
        )
        tid = data.get("task_id")
        if tid is None:
            raise MediaWikiClientError(
                data.get("message", "Failed to create task")
            )
        return int(tid)

    def kanban_update_task(
        self,
        task_id: int,
        title: Optional[str] = None,
        description: Optional[str] = None,
        priority: Optional[str] = None,
        status_id: Optional[int] = None,
        due_date: Optional[str] = None,
    ) -> None:
        """更新任务。status_id 为列 ID，传入则移动任务到该列。"""
        kwargs: Dict[str, Any] = {"task_id": task_id}
        if title is not None:
            kwargs["title"] = title.strip()
        if description is not None:
            kwargs["description"] = description.strip()
        if priority is not None:
            kwargs["priority"] = priority
        if status_id is not None:
            kwargs["status_id"] = status_id
        if due_date is not None:
            kwargs["due_date"] = due_date
        self._kanban_api("updatetask", **kwargs)

    def kanban_delete_task(self, board_id: int, task_id: int) -> None:
        """删除任务。"""
        self._kanban_api("deletetask", board_id=board_id, task_id=task_id)


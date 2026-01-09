"""知乎直达工具实现

支持访问和提取知乎直达（zhida.zhihu.com）的问题和答案内容。
"""

import re
import json
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime
from backend.core.agent.tools.base import Tool, ToolResult, ToolParameter

logger = logging.getLogger(__name__)


class ZhihuZhidaTool(Tool):
    """知乎直达工具
    
    支持访问知乎直达页面，提取问题和答案内容。
    可以保存到本地知识库，支持缓存和离线访问。
    """
    
    def __init__(self):
        """初始化知乎直达工具"""
        parameters = [
            ToolParameter(
                name="url",
                type="string",
                description=(
                    "知乎直达 URL 或搜索 ID。"
                    "支持完整 URL（https://zhida.zhihu.com/search/{id}）或仅搜索 ID。"
                    "示例：'3707579171380201696' 或 'https://zhida.zhihu.com/search/3707579171380201696'"
                ),
                required=True
            ),
            ToolParameter(
                name="operation",
                type="string",
                description=(
                    "操作类型："
                    "'read'（读取并返回内容，默认）、"
                    "'extract'（提取结构化数据）、"
                    "'save'（保存到知识库）"
                ),
                required=False,
                default="read",
                enum=["read", "extract", "save"]
            ),
            ToolParameter(
                name="format",
                type="string",
                description="输出格式：'markdown'（默认）、'json'、'text'",
                required=False,
                default="markdown",
                enum=["markdown", "json", "text"]
            ),
            ToolParameter(
                name="save_to_kb",
                type="boolean",
                description="是否保存到知识库（默认 false，仅在 operation='read' 时有效）",
                required=False,
                default=False
            ),
        ]
        
        super().__init__(
            name="zhihu_zhida",
            description=(
                "访问和提取知乎直达（zhida.zhihu.com）的问题和答案内容。"
                "知乎直达是一个提问式的网页知识库，每个 URL 对应一个特定的问题和多个答案。"
                "\n功能："
                "- 读取问题和答案内容"
                "- 提取结构化数据"
                "- 保存到本地知识库（可选）"
                "\n使用示例："
                "- 读取内容：url='3707579171380201696' 或 url='https://zhida.zhihu.com/search/3707579171380201696'"
                "- 提取结构化：operation='extract', format='json'"
                "- 保存到知识库：save_to_kb=true"
                "\n注意："
                "- 需要确保浏览器工具已登录知乎（使用 user_data_dir='zhihu'）"
                "- 内容会缓存到本地，提高后续访问速度"
            ),
            parameters=parameters
        )
        
        # 初始化缓存目录
        from shared.platform_utils import get_app_data_dir
        self.cache_dir = get_app_data_dir() / "cache" / "zhihu_zhida"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # 知识库目录
        self.kb_dir = get_app_data_dir() / "knowledge" / "zhihu_zhida"
        self.kb_dir.mkdir(parents=True, exist_ok=True)
    
    def _extract_search_id(self, url_or_id: str) -> str:
        """从 URL 或 ID 中提取搜索 ID"""
        # 如果是完整 URL
        if url_or_id.startswith("http"):
            match = re.search(r'/search/(\d+)', url_or_id)
            if match:
                return match.group(1)
        # 如果只是 ID
        elif url_or_id.isdigit():
            return url_or_id
        
        raise ValueError(f"无效的 URL 或搜索 ID: {url_or_id}")
    
    def _get_url(self, search_id: str) -> str:
        """构建完整的 URL"""
        return f"https://zhida.zhihu.com/search/{search_id}"
    
    def _get_cache_file(self, search_id: str) -> Path:
        """获取缓存文件路径"""
        return self.cache_dir / f"{search_id}.json"
    
    def _get_kb_file(self, search_id: str) -> Path:
        """获取知识库文件路径"""
        return self.kb_dir / f"{search_id}.json"
    
    def _load_cache(self, search_id: str) -> Optional[Dict]:
        """加载缓存内容"""
        cache_file = self._get_cache_file(search_id)
        if cache_file.exists():
            try:
                data = json.loads(cache_file.read_text(encoding='utf-8'))
                logger.info(f"从缓存加载内容: {search_id}")
                return data
            except Exception as e:
                logger.warning(f"加载缓存失败: {e}")
        return None
    
    def _save_cache(self, search_id: str, data: Dict):
        """保存缓存"""
        cache_file = self._get_cache_file(search_id)
        cache_file.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding='utf-8'
        )
        logger.info(f"保存缓存: {search_id}")
    
    def _save_to_kb(self, search_id: str, data: Dict):
        """保存到知识库"""
        kb_file = self._get_kb_file(search_id)
        kb_data = {
            **data,
            "saved_at": datetime.now().isoformat(),
            "source": "zhihu_zhida"
        }
        kb_file.write_text(
            json.dumps(kb_data, ensure_ascii=False, indent=2),
            encoding='utf-8'
        )
        logger.info(f"保存到知识库: {search_id}")
    
    async def _fetch_content(self, search_id: str) -> Dict:
        """使用浏览器工具获取内容"""
        from backend.core.agent.tools.builtin.browser_tool import BrowserTool
        
        url = self._get_url(search_id)
        browser_tool = BrowserTool()
        
        task = f"""
        访问 {url}，然后使用 extract action 提取以下内容：
        1. 问题标题（question_title）
        2. 问题描述（question_content）
        3. 所有答案列表（answers），每个答案包括：
           - 作者（author）
           - 内容（content）
           - 点赞数（upvotes，如果有）
           - 回答时间（time，如果有）
        4. 页面元数据（metadata），如浏览量等
        
        请返回 JSON 格式的结构化数据，确保所有内容都提取完整。
        """
        
        try:
            result = await browser_tool._execute_async(
                task=task,
                user_data_dir="zhihu",
                headless=True,
                timeout=120  # 知乎页面可能需要更长时间加载
            )
            
            if not result.success:
                raise RuntimeError(f"浏览器工具执行失败: {result.error}")
            
            # 从结果中提取内容
            # browser-use 的 extract action 会返回结构化数据
            extracted_data = result.data.get("result", "")
            
            # 尝试解析 JSON（如果 extract 返回的是 JSON）
            try:
                content_data = json.loads(extracted_data)
            except json.JSONDecodeError:
                # 如果不是 JSON，使用 LLM 提取结构化数据
                content_data = self._parse_text_to_json(extracted_data)
            
            # 添加元数据
            content_data["search_id"] = search_id
            content_data["url"] = url
            content_data["fetched_at"] = datetime.now().isoformat()
            
            return content_data
            
        except Exception as e:
            logger.exception(f"获取内容失败: {e}")
            raise RuntimeError(f"获取知乎直达内容失败: {str(e)}")
    
    def _parse_text_to_json(self, text: str) -> Dict:
        """将文本解析为 JSON 结构（如果 extract 返回的是文本）"""
        # 这里可以使用 LLM 或正则表达式来提取结构化数据
        # 简化实现：返回基本结构
        return {
            "question_title": "（需要从页面提取）",
            "question_content": text[:500] if text else "",
            "answers": [],
            "raw_content": text
        }
    
    def _format_output(self, data: Dict, format: str) -> str:
        """格式化输出"""
        if format == "json":
            return json.dumps(data, ensure_ascii=False, indent=2)
        
        elif format == "markdown":
            return self._to_markdown(data)
        
        else:  # text
            return self._to_text(data)
    
    def _to_markdown(self, data: Dict) -> str:
        """转换为 Markdown 格式"""
        lines = []
        
        # 标题
        lines.append(f"# {data.get('question_title', '未知问题')}")
        lines.append("")
        
        # URL
        if "url" in data:
            lines.append(f"**链接**: [{data['url']}]({data['url']})")
            lines.append("")
        
        # 问题描述
        question_content = data.get("question_content", "")
        if question_content:
            lines.append("## 问题描述")
            lines.append("")
            lines.append(question_content)
            lines.append("")
        
        # 答案列表
        answers = data.get("answers", [])
        if answers:
            lines.append("## 答案")
            lines.append("")
            for i, answer in enumerate(answers, 1):
                lines.append(f"### 答案 {i}")
                if isinstance(answer, dict):
                    author = answer.get("author", "匿名用户")
                    content = answer.get("content", "")
                    upvotes = answer.get("upvotes")
                    time = answer.get("time")
                    
                    lines.append(f"**作者**: {author}")
                    if upvotes:
                        lines.append(f"**点赞数**: {upvotes}")
                    if time:
                        lines.append(f"**时间**: {time}")
                    lines.append("")
                    lines.append(content)
                else:
                    lines.append(str(answer))
                lines.append("")
        
        # 元数据
        if "metadata" in data:
            lines.append("---")
            lines.append("")
            lines.append("**元数据**:")
            lines.append(json.dumps(data["metadata"], ensure_ascii=False, indent=2))
        
        return "\n".join(lines)
    
    def _to_text(self, data: Dict) -> str:
        """转换为纯文本格式"""
        lines = []
        lines.append(f"问题: {data.get('question_title', '未知问题')}")
        lines.append("")
        lines.append(data.get("question_content", ""))
        lines.append("")
        
        answers = data.get("answers", [])
        for i, answer in enumerate(answers, 1):
            lines.append(f"答案 {i}:")
            if isinstance(answer, dict):
                lines.append(f"  作者: {answer.get('author', '匿名用户')}")
                lines.append(f"  内容: {answer.get('content', '')}")
            else:
                lines.append(f"  {answer}")
            lines.append("")
        
        return "\n".join(lines)
    
    async def _execute_async(self, **kwargs) -> ToolResult:
        """异步执行知乎直达操作"""
        try:
            url_or_id = kwargs.get("url")
            if not url_or_id:
                return ToolResult(
                    success=False,
                    error="url 参数是必需的"
                )
            
            operation = kwargs.get("operation", "read")
            format = kwargs.get("format", "markdown")
            save_to_kb = kwargs.get("save_to_kb", False)
            
            # 提取搜索 ID
            try:
                search_id = self._extract_search_id(url_or_id)
            except ValueError as e:
                return ToolResult(
                    success=False,
                    error=str(e)
                )
            
            # 检查缓存
            cached_data = self._load_cache(search_id)
            
            # 如果需要最新内容或缓存不存在，从网页获取
            if cached_data is None or operation == "extract":
                try:
                    content_data = await self._fetch_content(search_id)
                    # 保存缓存
                    self._save_cache(search_id, content_data)
                    data = content_data
                except Exception as e:
                    # 如果获取失败，尝试使用缓存
                    if cached_data:
                        logger.warning(f"获取最新内容失败，使用缓存: {e}")
                        data = cached_data
                    else:
                        return ToolResult(
                            success=False,
                            error=f"获取内容失败且无缓存: {str(e)}"
                        )
            else:
                data = cached_data
            
            # 保存到知识库（如果需要）
            if save_to_kb or operation == "save":
                self._save_to_kb(search_id, data)
            
            # 格式化输出
            if operation == "extract":
                # extract 操作返回 JSON
                output = json.dumps(data, ensure_ascii=False, indent=2)
            else:
                # read 操作返回格式化内容
                output = self._format_output(data, format)
            
            return ToolResult(
                success=True,
                data={
                    "content": output,
                    "search_id": search_id,
                    "url": self._get_url(search_id),
                    "format": format,
                    "cached": cached_data is not None
                }
            )
            
        except Exception as e:
            logger.exception("知乎直达工具执行失败")
            return ToolResult(
                success=False,
                error=f"执行失败: {str(e)}"
            )
    
    def execute(self, **kwargs) -> ToolResult:
        """同步执行（包装异步方法）"""
        import asyncio
        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run,
                    self._execute_async(**kwargs)
                )
                timeout = kwargs.get("timeout", 120) + 10
                return future.result(timeout=timeout)
        except RuntimeError:
            return asyncio.run(self._execute_async(**kwargs))


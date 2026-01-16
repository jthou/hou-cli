"""Gvim 编辑器工具实现"""

from typing import Dict, Any, Optional
from backend.core.agent.tools.base import Tool, ToolResult, ToolParameter
from backend.services.gvim_service import GvimService, GvimServiceError


class GvimTool(Tool):
    """Gvim 编辑器工具
    
    允许 AI 助手使用 gvim 打开和编辑文件，以及打开和编辑 MediaWiki 页面。
    """
    
    def __init__(self):
        """初始化 Gvim 工具"""
        parameters = [
            ToolParameter(
                name="file_path",
                type="string",
                description="文件路径（可选，与 mediawiki_page 二选一）",
                required=False
            ),
            ToolParameter(
                name="mediawiki_page",
                type="string",
                description="MediaWiki 页面标题（可选，与 file_path 二选一）",
                required=False
            ),
            ToolParameter(
                name="line_number",
                type="integer",
                description="行号（可选，用于定位到指定行）",
                required=False
            ),
            ToolParameter(
                name="read_only",
                type="boolean",
                description="只读模式（可选，默认 false）",
                required=False,
                default=False
            ),
            ToolParameter(
                name="content",
                type="string",
                description="要写入的内容（可选，用于编辑模式）",
                required=False
            ),
            ToolParameter(
                name="mode",
                type="string",
                description="编辑模式（可选：'open' 打开文件、'interactive' 交互式编辑、'edit' 通过临时文件编辑）",
                required=False,
                default="open",
                enum=["open", "interactive", "edit"]
            ),
            ToolParameter(
                name="save_to_mediawiki",
                type="boolean",
                description="是否保存回 MediaWiki（仅当打开 MediaWiki 页面时有效，默认 false）",
                required=False,
                default=False
            ),
        ]
        
        super().__init__(
            name="gvim",
            description=(
                "使用 gvim 编辑器打开和编辑文件，或打开和编辑 MediaWiki 页面。"
                "\n功能："
                "- 打开本地文件：使用 file_path 参数"
                "- 打开 MediaWiki 页面：使用 mediawiki_page 参数"
                "- 编辑文件：使用 content 参数或 interactive 模式"
                "- 保存回 MediaWiki：使用 save_to_mediawiki 参数"
                "\n参数说明："
                "- file_path: 本地文件路径（与 mediawiki_page 二选一）"
                "- mediawiki_page: MediaWiki 页面标题（与 file_path 二选一）"
                "- line_number: 行号，用于定位到指定行"
                "- read_only: 只读模式，默认 false"
                "- content: 要写入的内容（用于编辑模式）"
                "- mode: 编辑模式，'open'（打开）、'interactive'（交互式编辑）、'edit'（通过临时文件编辑）"
                "- save_to_mediawiki: 是否保存回 MediaWiki（仅当打开 MediaWiki 页面时有效）"
                "\n使用示例："
                "- 打开文件：file_path='/path/to/file.py', line_number=10"
                "- 打开 MediaWiki 页面：mediawiki_page='Test'"
                "- 编辑文件内容：file_path='/path/to/file.py', content='新内容', mode='edit'"
            ),
            parameters=parameters
        )
        
        # 延迟初始化服务（避免启动时失败）
        self._service: Optional[GvimService] = None
    
    def _get_service(self) -> GvimService:
        """获取服务实例（延迟初始化）"""
        if self._service is None:
            try:
                self._service = GvimService()
            except Exception as e:
                raise RuntimeError(f"Gvim 服务初始化失败: {str(e)}")
        return self._service
    
    def execute(self, **kwargs) -> ToolResult:
        """执行 Gvim 操作
        
        Args:
            file_path: 文件路径（可选）
            mediawiki_page: MediaWiki 页面标题（可选）
            line_number: 行号（可选）
            read_only: 只读模式（可选）
            content: 要写入的内容（可选）
            mode: 编辑模式（可选）
            save_to_mediawiki: 是否保存回 MediaWiki（可选）
            
        Returns:
            ToolResult: 执行结果
        """
        try:
            service = self._get_service()
            
            # 检查 gvim 是否可用
            if not service.check_availability():
                return ToolResult(
                    success=False,
                    error="gvim 不可用，请确保已安装 gvim。在 macOS 上可以使用 'brew install macvim' 安装。"
                )
            
            # 获取参数
            file_path = kwargs.get("file_path")
            mediawiki_page = kwargs.get("mediawiki_page")
            line_number = kwargs.get("line_number")
            read_only = kwargs.get("read_only", False)
            content = kwargs.get("content")
            mode = kwargs.get("mode", "open")
            save_to_mediawiki = kwargs.get("save_to_mediawiki", False)
            
            # 验证参数：file_path 和 mediawiki_page 至少需要一个
            if not file_path and not mediawiki_page:
                return ToolResult(
                    success=False,
                    error="必须提供 file_path 或 mediawiki_page 参数之一"
                )
            
            # 如果同时提供了两个参数，优先使用 mediawiki_page
            if file_path and mediawiki_page:
                file_path = None
            
            result_data = {}
            
            # 处理 MediaWiki 页面
            if mediawiki_page:
                if mode == "edit" and content:
                    # 编辑模式：创建临时文件，写入内容，打开编辑
                    result = service.edit_file_with_content(
                        file_path="",  # 不需要实际文件路径
                        content=content
                    )
                    result_data.update(result)
                    result_data["page_title"] = mediawiki_page
                    result_data["note"] = "编辑完成后，可以使用 save_to_mediawiki=true 保存回 MediaWiki"
                else:
                    # 打开 MediaWiki 页面
                    result = service.open_mediawiki_page(
                        page_title=mediawiki_page,
                        line_number=line_number,
                        read_only=read_only
                    )
                    result_data.update(result)
                    
                    if save_to_mediawiki:
                        # 保存回 MediaWiki（需要从临时文件读取）
                        if "file_path" in result:
                            save_result = service.save_mediawiki_page(
                                page_title=mediawiki_page,
                                file_path=result["file_path"]
                            )
                            result_data["save_result"] = save_result
                            result_data["message"] = f"已打开并保存 MediaWiki 页面: {mediawiki_page}"
            
            # 处理本地文件
            elif file_path:
                if mode == "edit" and content:
                    # 编辑模式：创建临时文件，写入内容，打开编辑
                    result = service.edit_file_with_content(
                        file_path=file_path,
                        content=content
                    )
                    result_data.update(result)
                elif mode == "interactive":
                    # 交互式编辑
                    result = service.edit_file_interactive(file_path)
                    result_data.update(result)
                else:
                    # 打开文件
                    result = service.open_file(
                        file_path=file_path,
                        line_number=line_number,
                        read_only=read_only
                    )
                    result_data.update(result)
            
            return ToolResult(
                success=True,
                data=result_data
            )
            
        except GvimServiceError as e:
            return ToolResult(
                success=False,
                error=str(e)
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Gvim 操作失败: {str(e)}"
            )


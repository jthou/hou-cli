"""PDF 解析工具实现

支持多种 PDF 解析后端：
1. pdfplumber（pypdf 同装）- 基础文本提取，使用 pdfminer 布局参数改善分栏
2. Camelot - 专业表格提取（金融年报等复杂表格）

自动选择最合适的后端，或根据用户需求指定。
"""

import logging
from typing import Dict, Any, Optional, List
from pathlib import Path
from backend.core.agent.tools.base import Tool, ToolResult, ToolParameter

logger = logging.getLogger(__name__)


class PDFParserTool(Tool):
    """PDF 解析工具
    
    支持多种PDF解析后端，自动选择最合适的工具进行解析。
    可以提取文本、表格、公式、图片等结构化内容。
    """
    
    def __init__(self):
        """初始化PDF解析工具"""
        parameters = [
            ToolParameter(
                name="file_path",
                type="string",
                description="PDF文件路径（必需）",
                required=True
            ),
            ToolParameter(
                name="output_format",
                type="string",
                description=(
                    "输出格式：'markdown'（Markdown格式）、'json'（结构化JSON）、"
                    "'excel'（Excel表格）、'text'（纯文本），默认 'markdown'"
                ),
                required=False,
                default="markdown",
                enum=["markdown", "json", "excel", "text"]
            ),
            ToolParameter(
                name="extract_mode",
                type="string",
                description=(
                    "提取模式：'full'（完整文本）、'text'（仅文本）、'table'（仅表格），默认 'full'"
                ),
                required=False,
                default="full",
                enum=["full", "text", "table"]
            ),
            ToolParameter(
                name="backend",
                type="string",
                description=(
                    "指定后端：'pypdf'（文本，pdfminer+pdfplumber）、'camelot'（表格）、'auto'（自动），默认 'auto'"
                ),
                required=False,
                default="auto",
                enum=["auto", "pypdf", "camelot"]
            ),
            ToolParameter(
                name="output_path",
                type="string",
                description="输出文件路径（可选，默认在PDF同目录下生成）",
                required=False
            ),
        ]
        
        super().__init__(
            name="pdf_parser",
            description=(
                "解析PDF文件，提取文本或表格。"
                "\n参数：file_path（必需）、output_format、extract_mode、backend、output_path"
                "\n示例：extract_mode='table' 用 Camelot 提取表格；默认用 pdfplumber 提取文本（含分栏优化）"
            ),
            parameters=parameters
        )
        
        # 延迟初始化后端（避免启动时失败）
        self._available_backends = None
    
    def _check_backend_availability(self) -> Dict[str, bool]:
        """
        检查各个后端的可用性
        
        Returns:
            后端可用性字典
        """
        if self._available_backends is not None:
            return self._available_backends
        
        backends = {
            "pypdf": False,
            "camelot": False,
        }
        
        # 检查 pdfplumber（文本提取，与 pdf_routes 共享 pdfminer 布局逻辑）
        try:
            import pdfplumber
            backends["pypdf"] = True
        except ImportError:
            pass
        
        # 检查 Camelot
        try:
            import camelot
            backends["camelot"] = True
        except ImportError:
            pass
        
        self._available_backends = backends
        return backends
    
    def _parse_with_pypdf(self, file_path: str, output_format: str, extract_mode: str, output_path: Optional[str]) -> Dict[str, Any]:
        """使用共享 pdf_extract 提取文本（pdfminer 布局 + pdfplumber 回退，含分栏优化）"""
        try:
            import pdfplumber
            from backend.utils.pdf_extract import extract_text_from_pdf

            pdf_path = Path(file_path)
            if not pdf_path.exists():
                raise FileNotFoundError(f"PDF文件不存在: {file_path}")

            with pdfplumber.open(str(pdf_path)) as pdf:
                page_count = len(pdf.pages)

            text_content = []
            for page_num in range(1, page_count + 1):
                page_text = extract_text_from_pdf(file_path, [page_num - 1], use_layout=True, fix_doubled=True)
                if page_text:
                    if output_format == "markdown":
                        text_content.append(f"## 第 {page_num} 页\n\n{page_text}\n")
                    else:
                        text_content.append(f"第 {page_num} 页:\n{page_text}\n")

            content = "\n".join(text_content)

            if not output_path:
                if output_format == "json":
                    output_path = str(pdf_path.parent / f"{pdf_path.stem}.json")
                elif output_format == "text":
                    output_path = str(pdf_path.parent / f"{pdf_path.stem}.txt")
                else:
                    output_path = str(pdf_path.parent / f"{pdf_path.stem}.md")

            # 根据输出格式保存
            output_file = Path(output_path)
            if output_format == "json":
                import json
                output_file.write_text(
                    json.dumps({"pages": page_count, "content": content}, ensure_ascii=False, indent=2),
                    encoding='utf-8'
                )
            else:
                output_file.write_text(content, encoding='utf-8')
            
            return {
                "success": True,
                "output_path": str(output_path),
                "content": content,
                "content_length": len(content),
                "backend": "pypdf"
            }
                
        except ImportError:
            raise RuntimeError("pypdf/pdfplumber未安装，请运行: pip install pypdf pdfplumber")
        except Exception as e:
            raise RuntimeError(f"PDF解析失败: {str(e)}")
    
    def _parse_with_camelot(self, file_path: str, output_format: str, extract_mode: str, output_path: Optional[str]) -> Dict[str, Any]:
        """使用 Camelot 提取表格"""
        try:
            import camelot
            
            pdf_path = Path(file_path)
            if not pdf_path.exists():
                raise FileNotFoundError(f"PDF文件不存在: {file_path}")
            
            # 提取表格
            tables = camelot.read_pdf(str(pdf_path), pages='all')
            
            if len(tables) == 0:
                return {
                    "success": True,
                    "tables_count": 0,
                    "message": "未找到表格",
                    "backend": "camelot"
                }
            
            # 确定输出路径
            if not output_path:
                if output_format == "excel":
                    output_path = str(pdf_path.parent / f"{pdf_path.stem}_tables.xlsx")
                else:
                    output_path = str(pdf_path.parent / f"{pdf_path.stem}_tables.csv")
            
            # 导出表格
            if output_format == "excel":
                tables.export(output_path, f='excel')
            else:
                tables.export(output_path, f='csv')
            
            # 汇总表格信息
            table_info = []
            for i, table in enumerate(tables):
                table_info.append({
                    "page": table.page,
                    "accuracy": table.accuracy,
                    "rows": table.shape[0],
                    "cols": table.shape[1]
                })
            
            return {
                "success": True,
                "output_path": output_path,
                "tables_count": len(tables),
                "tables": table_info,
                "backend": "camelot"
            }
            
        except ImportError:
            raise RuntimeError("Camelot未安装，请运行: pip install camelot-py[cv]")
        except Exception as e:
            raise RuntimeError(f"Camelot提取失败: {str(e)}")
    
    def _select_backend(self, backend: str, extract_mode: str, available: Dict[str, bool]) -> str:
        """选择最合适的后端"""
        if backend != "auto":
            if backend in available and available[backend]:
                return backend
            else:
                raise RuntimeError(f"指定的后端 '{backend}' 不可用")
        
        # 自动选择逻辑：优先使用稳定可靠的后端
        # 1. 表格提取优先使用 Camelot
        if extract_mode == "table" and available.get("camelot"):
            return "camelot"
        
        # 2. 文本提取优先使用 pypdf（pdfplumber + pdfminer 布局）
        if available.get("pypdf"):
            return "pypdf"
        
        # 3. Camelot：也可用于一般提取（表格模式已优先）
        if available.get("camelot"):
            return "camelot"
        
        raise RuntimeError(
            "没有可用的PDF解析后端。请安装：pip install pdfplumber 或 pip install camelot-py[cv]"
        )
    
    def execute(self, **kwargs) -> ToolResult:
        """
        执行PDF解析
        
        Args:
            file_path: PDF文件路径
            output_format: 输出格式
            extract_mode: 提取模式
            backend: 指定后端
            output_path: 输出路径
            
        Returns:
            ToolResult: 解析结果
        """
        try:
            # 获取参数
            file_path = kwargs.get("file_path")
            output_format = kwargs.get("output_format", "markdown")
            extract_mode = kwargs.get("extract_mode", "full")
            backend = kwargs.get("backend", "auto")
            output_path = kwargs.get("output_path")
            
            if not file_path:
                return ToolResult(
                    success=False,
                    error="file_path 参数是必需的"
                )
            
            # 验证文件存在
            pdf_path = Path(file_path)
            if not pdf_path.exists():
                return ToolResult(
                    success=False,
                    error=f"PDF文件不存在: {file_path}"
                )
            
            if not pdf_path.suffix.lower() == ".pdf":
                return ToolResult(
                    success=False,
                    error=f"文件不是PDF格式: {file_path}"
                )
            
            # 检查后端可用性
            available = self._check_backend_availability()
            
            # 选择后端
            selected_backend = self._select_backend(backend, extract_mode, available)
            
            # 根据后端执行解析
            if selected_backend == "pypdf":
                result = self._parse_with_pypdf(file_path, output_format, extract_mode, output_path)
            elif selected_backend == "camelot":
                result = self._parse_with_camelot(file_path, output_format, extract_mode, output_path)
            else:
                return ToolResult(
                    success=False,
                    error=f"未知的后端: {selected_backend}"
                )
            
            return ToolResult(
                success=True,
                data=result
            )
            
        except RuntimeError as e:
            return ToolResult(
                success=False,
                error=str(e)
            )
        except Exception as e:
            logger.exception("PDF解析失败")
            return ToolResult(
                success=False,
                error=f"PDF解析失败: {str(e)}"
            )


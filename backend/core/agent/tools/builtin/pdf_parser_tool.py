"""PDF 解析工具实现

支持多种PDF解析后端：
1. MinerU - 完全本地化，PDF转Markdown（学术文献、RAG知识库）
2. Logics-Parsing - 阿里Qwen2.5-VL模型，高质量解析（需要API密钥）
3. Camelot - 专业表格提取（金融年报等复杂表格）
4. PDF-Extract-Kit - 表格坐标提取（需配合OCR）

自动选择最合适的后端，或根据用户需求指定。
"""

import os
import subprocess
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
                    "提取模式：'full'（完整解析，包括文本、表格、公式、图片）、"
                    "'text'（仅文本）、'table'（仅表格）、'formula'（仅公式），默认 'full'"
                ),
                required=False,
                default="full",
                enum=["full", "text", "table", "formula"]
            ),
            ToolParameter(
                name="backend",
                type="string",
                description=(
                    "指定使用的后端（可选）：'mineru'（本地，免费）、'logics'（阿里API，需密钥）、"
                    "'camelot'（表格提取）、'auto'（自动选择），默认 'auto'"
                ),
                required=False,
                default="auto",
                enum=["auto", "mineru", "logics", "camelot"]
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
                "解析PDF文件，提取文本、表格、公式、图片等结构化内容。"
                "支持多种解析后端，自动选择最合适的工具。"
                "\n参数说明："
                "- file_path: PDF文件路径（必需）"
                "- output_format: 输出格式，'markdown'、'json'、'excel'、'text'，默认 'markdown'"
                "- extract_mode: 提取模式，'full'（完整）、'text'（仅文本）、'table'（仅表格）、'formula'（仅公式），默认 'full'"
                "- backend: 指定后端，'auto'（自动）、'mineru'（本地免费）、'logics'（阿里API）、'camelot'（表格），默认 'auto'"
                "- output_path: 输出文件路径（可选）"
                "\n使用示例："
                "- 解析PDF为Markdown：file_path='/path/to/file.pdf', output_format='markdown'"
                "- 提取表格：file_path='/path/to/file.pdf', extract_mode='table', output_format='excel'"
                "- 使用特定后端：file_path='/path/to/file.pdf', backend='mineru'"
                "\n后端说明："
                "- mineru: 完全本地化，免费，适合学术文献、RAG知识库"
                "- logics: 阿里Qwen2.5-VL API，高质量解析，需要API密钥，有免费额度"
                "- camelot: 专业表格提取，免费，适合金融年报等复杂表格"
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
            "mineru": False,
            "logics": False,
            "camelot": False,
        }
        
        # 检查 MinerU
        try:
            result = subprocess.run(
                ["mineru", "--version"],
                capture_output=True,
                timeout=5,
                text=True
            )
            if result.returncode == 0 or "mineru" in result.stdout.lower() or "mineru" in result.stderr.lower():
                backends["mineru"] = True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            try:
                # 尝试作为Python模块
                import mineru
                backends["mineru"] = True
            except ImportError:
                pass
        
        # 检查 Logics-Parsing（需要API密钥）
        try:
            # 检查是否有API密钥
            api_key = os.getenv("DASHSCOPE_API_KEY") or os.getenv("ALIBABA_CLOUD_API_KEY")
            if api_key:
                # 尝试导入
                try:
                    import logics_parsing
                    backends["logics"] = True
                except ImportError:
                    # 可能通过其他方式安装
                    pass
        except Exception:
            pass
        
        # 检查 Camelot
        try:
            import camelot
            backends["camelot"] = True
        except ImportError:
            pass
        
        self._available_backends = backends
        return backends
    
    def _parse_with_mineru(self, file_path: str, output_format: str, extract_mode: str, output_path: Optional[str]) -> Dict[str, Any]:
        """使用 MinerU 解析PDF"""
        try:
            pdf_path = Path(file_path)
            if not pdf_path.exists():
                raise FileNotFoundError(f"PDF文件不存在: {file_path}")
            
            # 确定输出路径
            if not output_path:
                output_path = str(pdf_path.parent / f"{pdf_path.stem}.md")
            
            # 构建命令
            cmd = ["mineru", "convert", str(pdf_path), "--output", output_path]
            
            # 根据提取模式添加参数
            if extract_mode == "table":
                cmd.append("--tables-only")
            elif extract_mode == "formula":
                cmd.append("--formulas-only")
            
            # 执行转换
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=300,  # 5分钟超时
                text=True
            )
            
            if result.returncode != 0:
                raise RuntimeError(f"MinerU转换失败: {result.stderr}")
            
            # 读取输出文件
            output_file = Path(output_path)
            if output_file.exists():
                content = output_file.read_text(encoding='utf-8')
                return {
                    "success": True,
                    "output_path": str(output_path),
                    "content": content,
                    "content_length": len(content),
                    "backend": "mineru"
                }
            else:
                raise RuntimeError("MinerU未生成输出文件")
                
        except subprocess.TimeoutExpired:
            raise RuntimeError("MinerU解析超时（超过5分钟）")
        except Exception as e:
            raise RuntimeError(f"MinerU解析失败: {str(e)}")
    
    def _parse_with_logics(self, file_path: str, output_format: str, extract_mode: str, output_path: Optional[str]) -> Dict[str, Any]:
        """使用 Logics-Parsing 解析PDF"""
        try:
            # 检查API密钥
            api_key = os.getenv("DASHSCOPE_API_KEY") or os.getenv("ALIBABA_CLOUD_API_KEY")
            if not api_key:
                raise RuntimeError("Logics-Parsing需要API密钥，请设置 DASHSCOPE_API_KEY 或 ALIBABA_CLOUD_API_KEY 环境变量")
            
            # 这里需要根据 Logics-Parsing 的实际API调整
            # 示例代码（需要根据实际API调整）
            try:
                from logics_parsing import PDFParser
                parser = PDFParser(api_key=api_key)
                result = parser.parse(file_path, format=output_format)
                
                # 保存输出
                if not output_path:
                    output_path = str(Path(file_path).parent / f"{Path(file_path).stem}.{output_format}")
                
                if output_format == "markdown":
                    Path(output_path).write_text(result.get("markdown", ""), encoding='utf-8')
                elif output_format == "json":
                    import json
                    Path(output_path).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
                
                return {
                    "success": True,
                    "output_path": output_path,
                    "content": result.get("markdown", ""),
                    "content_length": len(result.get("markdown", "")),
                    "backend": "logics"
                }
            except ImportError:
                raise RuntimeError("Logics-Parsing未安装，请运行: pip install logics-parsing")
                
        except Exception as e:
            raise RuntimeError(f"Logics-Parsing解析失败: {str(e)}")
    
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
        
        # 自动选择逻辑
        if extract_mode == "table":
            # 表格提取优先使用 Camelot
            if available.get("camelot"):
                return "camelot"
        
        # 优先使用本地免费工具
        if available.get("mineru"):
            return "mineru"
        
        # 其次使用API工具（如果有密钥）
        if available.get("logics"):
            return "logics"
        
        # 最后尝试 Camelot
        if available.get("camelot"):
            return "camelot"
        
        raise RuntimeError(
            "没有可用的PDF解析后端。\n"
            "请安装以下工具之一：\n"
            "1. MinerU: pip install mineru\n"
            "2. Camelot: pip install camelot-py[cv]\n"
            "3. Logics-Parsing: pip install logics-parsing（需要API密钥）"
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
            if selected_backend == "mineru":
                result = self._parse_with_mineru(file_path, output_format, extract_mode, output_path)
            elif selected_backend == "logics":
                result = self._parse_with_logics(file_path, output_format, extract_mode, output_path)
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


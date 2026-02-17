"""文件整理工具实现

使用 Local-File-Organizer 自动扫描、分类和重命名文件。
支持多种集成方式：
1. 作为 Python 包导入（如果发布在 PyPI）
2. 作为子模块导入（如果添加为 git submodule）
3. 通过命令行调用（如果只能作为独立脚本运行）
"""

import os
import subprocess
import logging
from typing import Dict, Any, Optional
from pathlib import Path
from backend.core.agent.tools.base import Tool, ToolResult, ToolParameter

logger = logging.getLogger(__name__)


class FileOrganizerTool(Tool):
    """文件整理工具
    
    使用 Local-File-Organizer 自动扫描、分类和重命名文件。
    通过 AI 模型智能识别文件类型、内容，并按照规则组织文件。
    """
    
    def __init__(self):
        """初始化文件整理工具"""
        parameters = [
            ToolParameter(
                name="source_path",
                type="string",
                description="需要整理的源文件夹路径（必需）",
                required=True
            ),
            ToolParameter(
                name="target_path",
                type="string",
                description=(
                    "整理后文件的存放路径（可选）。"
                    "如果不提供，将在源路径下创建 'organized' 子文件夹。"
                ),
                required=False
            ),
            ToolParameter(
                name="organize_mode",
                type="string",
                description=(
                    "整理模式：'move'（移动文件）或 'copy'（复制文件），默认 'move'。"
                    "move 模式会移动文件到新位置，copy 模式会保留原文件。"
                ),
                required=False,
                default="move",
                enum=["move", "copy"]
            ),
            ToolParameter(
                name="dry_run",
                type="boolean",
                description=(
                    "是否仅预览整理结果而不实际执行（默认 false）。"
                    "设置为 true 时，只返回整理计划，不移动或复制文件。"
                ),
                required=False,
                default=False
            ),
        ]
        
        super().__init__(
            name="file_organizer",
            description=(
                "自动整理本地文件系统中的文件（会移动/复制文件，修改文件系统结构）。"
                "使用 AI 模型智能扫描、分类和重命名文件，"
                "将文件按照类型、日期、内容等规则组织到不同文件夹中。"
                "注意：此工具会修改文件系统，与 file_search（只读搜索）不同。"
                "\n参数说明："
                "- source_path: 需要整理的源文件夹路径（必需）"
                "- target_path: 整理后文件的存放路径（可选，默认在源路径下创建 organized 文件夹）"
                "- organize_mode: 整理模式，'move'（移动）或 'copy'（复制），默认 'move'"
                "- dry_run: 是否仅预览整理结果而不实际执行（默认 false）"
                "\n使用示例："
                "- 整理 Downloads 文件夹：source_path='/Users/username/Downloads'"
                "- 整理并复制到指定位置：source_path='/path/to/source', target_path='/path/to/target', organize_mode='copy'"
                "- 预览整理计划：source_path='/path/to/source', dry_run=true"
                "\n注意："
                "- 确保源路径存在且可读"
                "- 如果使用 move 模式，原文件将被移动到新位置"
                "- 建议先使用 dry_run=true 预览整理计划"
            ),
            parameters=parameters
        )
        
        # 延迟初始化（避免启动时失败）
        self._organizer_available = None
        self._organizer_type = None  # 'package', 'submodule', 'command'
    
    def _check_organizer_availability(self) -> tuple[bool, str]:
        """
        检查 Local-File-Organizer 的可用性和集成方式
        
        Returns:
            (is_available, organizer_type): 是否可用，集成类型
        """
        if self._organizer_available is not None:
            return self._organizer_available, self._organizer_type
        
        # 方式 1: 尝试作为 Python 包导入（可能从 GitHub 安装）
        try:
            # 尝试不同的可能包名
            try:
                import local_file_organizer
            except ImportError:
                try:
                    import Local_File_Organizer
                except ImportError:
                    import LocalFileOrganizer as local_file_organizer
            
            self._organizer_available = True
            self._organizer_type = 'package'
            logger.info("Local-File-Organizer 可用（Python 包）")
            return True, 'package'
        except ImportError:
            pass
        
        # 方式 2: 尝试作为子模块导入
        try:
            project_root = Path(__file__).parent.parent.parent.parent.parent
            submodule_path = project_root / "backend" / "externals" / "local-file-organizer"
            if submodule_path.exists():
                import sys
                sys.path.insert(0, str(submodule_path))
                # 尝试导入主模块（根据实际结构调整）
                try:
                    from main import FileOrganizer  # 假设的主类
                    self._organizer_available = True
                    self._organizer_type = 'submodule'
                    logger.info("Local-File-Organizer 可用（子模块）")
                    return True, 'submodule'
                except ImportError:
                    # 如果导入失败，但路径存在，可能可以通过命令行调用
                    if (submodule_path / "main.py").exists():
                        self._organizer_available = True
                        self._organizer_type = 'command'
                        logger.info("Local-File-Organizer 可用（命令行）")
                        return True, 'command'
        except Exception as e:
            logger.debug(f"检查子模块时出错: {e}")
        
        # 方式 3: 检查是否可以通过命令行调用
        try:
            result = subprocess.run(
                ["python", "-m", "local_file_organizer", "--help"],
                capture_output=True,
                timeout=5,
                text=True
            )
            if result.returncode == 0 or "usage" in result.stderr.lower() or "usage" in result.stdout.lower():
                self._organizer_available = True
                self._organizer_type = 'command'
                logger.info("Local-File-Organizer 可用（命令行模块）")
                return True, 'command'
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
            pass
        
        self._organizer_available = False
        self._organizer_type = None
        logger.warning("Local-File-Organizer 不可用")
        return False, None
    
    def _organize_with_package(self, source_path: str, target_path: Optional[str], 
                               organize_mode: str, dry_run: bool) -> Dict[str, Any]:
        """使用 Python 包方式整理文件"""
        try:
            from local_file_organizer import FileOrganizer
            
            organizer = FileOrganizer()
            result = organizer.organize(
                source_path=source_path,
                target_path=target_path,
                mode=organize_mode,
                dry_run=dry_run
            )
            return result
        except Exception as e:
            raise RuntimeError(f"使用包方式整理文件失败: {str(e)}")
    
    def _organize_with_submodule(self, source_path: str, target_path: Optional[str],
                                  organize_mode: str, dry_run: bool) -> Dict[str, Any]:
        """使用子模块方式整理文件"""
        try:
            project_root = Path(__file__).parent.parent.parent.parent.parent
            submodule_path = project_root / "backend" / "externals" / "local-file-organizer"
            import sys
            sys.path.insert(0, str(submodule_path))
            
            # 根据实际项目结构调整导入
            from main import FileOrganizer
            
            organizer = FileOrganizer()
            result = organizer.organize(
                source_path=source_path,
                target_path=target_path,
                mode=organize_mode,
                dry_run=dry_run
            )
            return result
        except Exception as e:
            raise RuntimeError(f"使用子模块方式整理文件失败: {str(e)}")
    
    def _organize_with_command(self, source_path: str, target_path: Optional[str],
                               organize_mode: str, dry_run: bool) -> Dict[str, Any]:
        """使用命令行方式整理文件"""
        try:
            project_root = Path(__file__).parent.parent.parent.parent.parent
            submodule_path = project_root / "backend" / "externals" / "local-file-organizer"
            main_script = submodule_path / "main.py"
            
            if not main_script.exists():
                # 尝试作为模块运行
                cmd = ["python", "-m", "local_file_organizer"]
            else:
                cmd = ["python", str(main_script)]
            
            # 构建命令行参数
            cmd.extend(["--source", source_path])
            if target_path:
                cmd.extend(["--target", target_path])
            if organize_mode == "copy":
                cmd.append("--copy")
            if dry_run:
                cmd.append("--dry-run")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=300,  # 5 分钟超时
                text=True,
                cwd=str(submodule_path) if submodule_path.exists() else None
            )
            
            if result.returncode != 0:
                raise RuntimeError(
                    f"命令行执行失败 (退出码 {result.returncode}): "
                    f"{result.stderr or result.stdout}"
                )
            
            # 解析输出（根据实际输出格式调整）
            # 这里假设输出是 JSON 格式或可以解析的文本
            try:
                import json
                output = result.stdout.strip()
                # 尝试解析 JSON 输出
                if output.startswith("{"):
                    return json.loads(output)
            except:
                pass
            
            # 如果无法解析 JSON，返回文本输出
            return {
                "success": True,
                "output": result.stdout,
                "files_organized": 0,  # 需要从输出中提取
                "summary": result.stdout[:500]  # 截取前 500 字符
            }
        except subprocess.TimeoutExpired:
            raise RuntimeError("文件整理超时（超过 5 分钟）")
        except Exception as e:
            raise RuntimeError(f"使用命令行方式整理文件失败: {str(e)}")
    
    def execute(self, **kwargs) -> ToolResult:
        """
        执行文件整理
        
        Args:
            source_path: 源文件夹路径
            target_path: 目标文件夹路径（可选）
            organize_mode: 整理模式（move/copy）
            dry_run: 是否仅预览
            
        Returns:
            ToolResult: 整理结果
        """
        try:
            # 检查可用性
            is_available, organizer_type = self._check_organizer_availability()
            if not is_available:
                return ToolResult(
                    success=False,
                    error=(
                        "Local-File-Organizer 未安装或不可用。\n"
                        "请执行以下操作之一：\n"
                        "1. 安装包: pip install local-file-organizer\n"
                        "2. 添加子模块: git submodule add https://github.com/QiuYannnn/Local-File-Organizer.git backend/externals/local-file-organizer\n"
                        "3. 克隆到本地: git clone https://github.com/QiuYannnn/Local-File-Organizer.git"
                    )
                )
            
            # 获取参数
            source_path = kwargs.get("source_path")
            target_path = kwargs.get("target_path")
            organize_mode = kwargs.get("organize_mode", "move")
            dry_run = kwargs.get("dry_run", False)
            
            if not source_path:
                return ToolResult(
                    success=False,
                    error="source_path 参数是必需的"
                )
            
            # 验证源路径
            source = Path(source_path)
            if not source.exists():
                return ToolResult(
                    success=False,
                    error=f"源路径不存在: {source_path}"
                )
            if not source.is_dir():
                return ToolResult(
                    success=False,
                    error=f"源路径不是目录: {source_path}"
                )
            
            # 如果没有提供目标路径，使用默认路径
            if not target_path:
                target_path = str(source / "organized")
            
            # 根据集成方式调用相应的整理方法
            if organizer_type == 'package':
                result = self._organize_with_package(source_path, target_path, organize_mode, dry_run)
            elif organizer_type == 'submodule':
                result = self._organize_with_submodule(source_path, target_path, organize_mode, dry_run)
            elif organizer_type == 'command':
                result = self._organize_with_command(source_path, target_path, organize_mode, dry_run)
            else:
                return ToolResult(
                    success=False,
                    error=f"未知的集成方式: {organizer_type}"
                )
            
            # 格式化返回结果
            return ToolResult(
                success=True,
                data={
                    "source_path": source_path,
                    "target_path": result.get("target_path", target_path),
                    "organize_mode": organize_mode,
                    "dry_run": dry_run,
                    "files_organized": result.get("files_organized", result.get("count", 0)),
                    "categories": result.get("categories", []),
                    "summary": result.get("summary", "文件整理完成"),
                    "organizer_type": organizer_type
                }
            )
            
        except RuntimeError as e:
            return ToolResult(
                success=False,
                error=str(e)
            )
        except Exception as e:
            logger.exception("文件整理失败")
            return ToolResult(
                success=False,
                error=f"文件整理失败: {str(e)}"
            )


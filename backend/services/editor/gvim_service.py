"""Gvim 编辑器服务"""

import os
import subprocess
import logging
import tempfile
from pathlib import Path
from typing import Optional
from datetime import datetime

from backend.services.mediawiki import MediaWikiClientService

logger = logging.getLogger(__name__)


class GvimServiceError(Exception):
    """Gvim 服务错误"""
    pass


def remove_special_char(text: str) -> str:
    """移除文件名中的特殊字符（参考 mediawiki_editor.py 的 RemoveSpecialChar）"""
    return text.replace('\\', '_').replace(':', '-').replace('/', '_').replace("'", "_").replace("?", "%3F").replace("$", "")


class GvimService:
    """Gvim 编辑器服务
    
    封装 gvim 命令执行，支持打开文件、编辑文件、打开 MediaWiki 页面等功能。
    """
    
    def __init__(self, tmpdir: Optional[str] = None):
        """初始化 Gvim 服务
        
        Args:
            tmpdir: 临时文件目录，默认使用系统临时目录
        """
        self.tmpdir = tmpdir or os.getenv("TMPDIR") or tempfile.gettempdir()
        # 确保临时目录存在
        Path(self.tmpdir).mkdir(parents=True, exist_ok=True)
        
        self._mediawiki_client: Optional[MediaWikiClientService] = None
    
    def check_availability(self) -> bool:
        """检查 gvim 是否可用
        
        Returns:
            bool: gvim 是否可用
        """
        try:
            result = subprocess.run(
                ['gvim', '--version'],
                capture_output=True,
                check=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.CalledProcessError):
            return False
    
    def _get_mediawiki_client(self) -> MediaWikiClientService:
        """获取 MediaWiki 客户端（延迟初始化）"""
        if self._mediawiki_client is None:
            self._mediawiki_client = MediaWikiClientService()
            if not self._mediawiki_client.connect():
                raise GvimServiceError("无法连接到 MediaWiki")
        return self._mediawiki_client
    
    def open_file(
        self,
        file_path: str,
        line_number: Optional[int] = None,
        read_only: bool = False
    ) -> dict:
        """打开文件
        
        Args:
            file_path: 文件路径
            line_number: 行号（可选，用于定位）
            read_only: 只读模式
            
        Returns:
            dict: 执行结果
        """
        if not self.check_availability():
            raise GvimServiceError("gvim 不可用，请确保已安装 gvim")
        
        # 转换为绝对路径
        file_path = os.path.abspath(os.path.expanduser(file_path))
        
        # 如果文件不存在，创建空文件
        if not os.path.exists(file_path):
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)
            Path(file_path).touch()
        
        # 构建 gvim 命令
        cmd = ['gvim']
        if read_only:
            cmd.append('-R')  # 只读模式
        if line_number:
            cmd.extend(['+', str(line_number)])  # 定位到行号
        cmd.append(file_path)
        
        # 非阻塞执行
        try:
            subprocess.Popen(cmd)
            return {
                "success": True,
                "message": f"已打开文件: {file_path}",
                "file_path": file_path
            }
        except Exception as e:
            raise GvimServiceError(f"打开文件失败: {str(e)}")
    
    def open_mediawiki_page(
        self,
        page_title: str,
        line_number: Optional[int] = None,
        read_only: bool = False
    ) -> dict:
        """打开 MediaWiki 页面
        
        从 MediaWiki 获取页面内容，保存到临时文件，用 gvim 打开。
        参考 mediawiki_editor.py 的 mw_read 函数。
        
        Args:
            page_title: MediaWiki 页面标题
            line_number: 行号（可选，用于定位）
            read_only: 只读模式
            
        Returns:
            dict: 执行结果，包含临时文件路径和页面标题
        """
        if not self.check_availability():
            raise GvimServiceError("gvim 不可用，请确保已安装 gvim")
        
        try:
            # 获取 MediaWiki 页面内容
            client = self._get_mediawiki_client()
            page = client.get_page(page_title)
            
            if not page:
                raise GvimServiceError(f"MediaWiki 页面不存在: {page_title}")
            
            # 创建临时文件（参考 mw_read 的实现）
            safe_filename = remove_special_char(page_title)
            local_name = os.path.join(self.tmpdir, f"{safe_filename}.mediawiki")
            
            # 写入页面内容
            with open(local_name, 'w', encoding='utf-8') as f:
                f.write(page.content)
            
            # 在文件开头添加 vim 命令，设置文件类型和页面标题
            # 使用 vim modeline 或创建 .vimrc 文件来设置
            # 这里我们创建一个包含元数据的注释行
            with open(local_name, 'r+', encoding='utf-8') as f:
                content = f.read()
                # 在文件开头添加元数据注释
                metadata = f"<!-- MediaWiki Page: {page_title} -->\n"
                if not content.startswith(metadata):
                    f.seek(0)
                    f.write(metadata + content)
            
            # 构建 gvim 命令
            cmd = ['gvim']
            if read_only:
                cmd.append('-R')
            if line_number:
                cmd.extend(['+', str(line_number)])
            # 设置文件类型为 mediawiki
            cmd.extend(['-c', 'set ft=mediawiki'])
            # 设置页面标题到缓冲区变量（通过 vim 命令）
            # 转义双引号
            escaped_title = page_title.replace('"', '\\"')
            cmd.extend(['-c', f'let b:article_name = "{escaped_title}"'])
            cmd.append(local_name)
            
            # 非阻塞执行
            subprocess.Popen(cmd)
            
            return {
                "success": True,
                "message": f"已打开 MediaWiki 页面: {page_title}",
                "page_title": page_title,
                "file_path": local_name,
                "url": page.url
            }
            
        except Exception as e:
            raise GvimServiceError(f"打开 MediaWiki 页面失败: {str(e)}")
    
    def save_mediawiki_page(
        self,
        page_title: str,
        file_path: str,
        summary: str = "",
        minor: bool = True
    ) -> dict:
        """将编辑后的文件内容保存回 MediaWiki
        
        参考 mediawiki_editor.py 的 mw_write 函数。
        
        Args:
            page_title: MediaWiki 页面标题
            file_path: 临时文件路径
            summary: 编辑摘要
            minor: 是否为小编辑
            
        Returns:
            dict: 执行结果
        """
        try:
            # 读取文件内容
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 移除元数据注释（如果存在）
            if content.startswith("<!-- MediaWiki Page:"):
                lines = content.split('\n')
                if lines[0].startswith("<!-- MediaWiki Page:"):
                    content = '\n'.join(lines[1:])
            
            # 保存到 MediaWiki
            client = self._get_mediawiki_client()
            success = client.edit_page(page_title, content, summary=summary, minor=minor)
            
            if success:
                return {
                    "success": True,
                    "message": f"已保存 MediaWiki 页面: {page_title}",
                    "page_title": page_title
                }
            else:
                raise GvimServiceError(f"保存 MediaWiki 页面失败: {page_title}")
                
        except Exception as e:
            raise GvimServiceError(f"保存 MediaWiki 页面失败: {str(e)}")
    
    def edit_file_interactive(self, file_path: str) -> dict:
        """交互式编辑文件
        
        打开文件让用户编辑，返回文件路径。
        
        Args:
            file_path: 文件路径
            
        Returns:
            dict: 执行结果
        """
        return self.open_file(file_path, read_only=False)
    
    def edit_file_with_content(
        self,
        file_path: str,
        content: str
    ) -> dict:
        """通过临时文件编辑（AI 生成内容，用户确认）
        
        Args:
            file_path: 目标文件路径
            content: 要写入的内容
            
        Returns:
            dict: 执行结果，包含临时文件路径
        """
        if not self.check_availability():
            raise GvimServiceError("gvim 不可用，请确保已安装 gvim")
        
        # 创建临时文件
        temp_file = tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.tmp',
            delete=False,
            encoding='utf-8'
        )
        temp_file.write(content)
        temp_file.close()
        
        # 用 gvim 打开临时文件
        cmd = ['gvim', temp_file.name]
        subprocess.Popen(cmd)
        
        return {
            "success": True,
            "message": f"已打开临时文件进行编辑",
            "temp_file": temp_file.name,
            "target_file": file_path,
            "note": "编辑完成后，请确认是否替换原文件"
        }


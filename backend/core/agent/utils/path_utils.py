"""
统一的文件路径处理工具类
提供鲁棒的文件路径提取、验证和规范化功能
"""
import re
import os
from pathlib import Path
from typing import List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class PathExtractor:
    """文件路径提取器 - 鲁棒地提取和规范化文件路径"""
    
    # 支持的视频文件扩展名
    VIDEO_EXTENSIONS = {'.mp4', '.avi', '.mkv', '.mov', '.flv', '.webm', '.m4v'}
    # 支持的音频文件扩展名
    AUDIO_EXTENSIONS = {'.mp3', '.wav', '.m4a', '.aac', '.ogg', '.flac'}
    # 支持的字幕文件扩展名
    SUBTITLE_EXTENSIONS = {'.srt', '.vtt', '.ass', '.ssa'}
    # 所有支持的文件扩展名
    ALL_EXTENSIONS = VIDEO_EXTENSIONS | AUDIO_EXTENSIONS | SUBTITLE_EXTENSIONS
    
    @classmethod
    def extract_paths(cls, text: str) -> List[str]:
        """
        从文本中提取所有文件路径
        
        Args:
            text: 输入文本
            
        Returns:
            提取到的完整文件路径列表（已规范化）
        """
        paths = []
        
        # 策略1：查找目录路径和"目录下"提示词
        dir_path, dir_end_pos = cls._extract_directory_path(text)
        
        # 策略2：在目录路径之后提取文件名
        if dir_path:
            # 检查 dir_path 是否已经是完整文件路径（包含文件扩展名）
            # 如果是，直接使用它，不要尝试提取文件名
            if any(dir_path.endswith(ext) for ext in cls.ALL_EXTENSIONS):
                # dir_path 已经是完整路径，直接使用
                paths.append(dir_path)
            else:
                # dir_path 是目录路径，尝试提取文件名
                filenames = cls._extract_filenames_after_dir(text, dir_end_pos)
                for filename in filenames:
                    full_path = cls._join_path(dir_path, filename)
                    if full_path:
                        paths.append(full_path)
        
        # 如果策略1和2没有提取到路径，尝试直接提取完整路径
        if not paths:
            full_paths = cls._extract_full_paths(text)
            paths.extend(full_paths)
        
        # 策略3：规范化所有路径
        normalized_paths = []
        for path in paths:
            normalized = cls.normalize_path(path)
            if normalized and normalized not in normalized_paths:
                normalized_paths.append(normalized)
        
        return normalized_paths
    
    @classmethod
    def _extract_directory_path(cls, text: str) -> Tuple[Optional[str], int]:
        """
        提取目录路径
        
        Returns:
            (目录路径, 目录路径结束位置)
        """
        # 规范化：处理以 // 开头的路径
        normalized_text = text
        if text.startswith('//') and not text.startswith('///'):
            normalized_text = text[1:]  # 移除多余的 /
        
        # 查找"目录下"或"目录"提示词
        dir_hint_pattern = r'目录下?\s*'
        dir_hint_match = re.search(dir_hint_pattern, normalized_text, re.IGNORECASE)
        
        if dir_hint_match:
            # 在"目录下"之前提取目录路径
            prefix = normalized_text[:dir_hint_match.start()]
            dir_pattern = r'^((?:[~/]|//?|/home/|/Users/|[A-Za-z]:\\\\)[^\s"\'\),。，、]+(?:\s+[^\s"\'\),。，、]+)*)'
            dir_match = re.search(dir_pattern, prefix, re.IGNORECASE)
            if dir_match:
                dir_path = dir_match.group(1).rstrip('.,;:!?)\'"）').strip()
                # 规范化：处理以 // 开头的路径
                if dir_path.startswith('//') and not dir_path.startswith('///'):
                    dir_path = dir_path[1:]  # 移除多余的 /
                # 扩展 ~ 路径
                if dir_path.startswith('~'):
                    dir_path = str(Path(dir_path).expanduser())
                dir_end_pos = dir_hint_match.end()
                return dir_path, dir_end_pos
        
        # 如果没有"目录下"提示词，尝试从开头提取目录路径
        dir_pattern = r'^((?:[~/]|//?|/home/|/Users/|[A-Za-z]:\\\\)[^\s"\'\),。，、]+(?:\s+[^\s"\'\),。，、]+)*(?=\s+[【\w\u4e00-\u9fff]))'
        dir_match = re.search(dir_pattern, normalized_text, re.IGNORECASE)
        if dir_match:
            dir_path = dir_match.group(1).rstrip('.,;:!?)\'"）').strip()
            # 规范化：处理以 // 开头的路径
            if dir_path.startswith('//') and not dir_path.startswith('///'):
                dir_path = dir_path[1:]  # 移除多余的 /
            if dir_path.startswith('~'):
                dir_path = str(Path(dir_path).expanduser())
            return dir_path, len(dir_path)
        
        return None, 0
    
    @classmethod
    def _extract_filenames_after_dir(cls, text: str, start_pos: int) -> List[str]:
        """
        在指定位置之后提取文件名
        
        Args:
            text: 输入文本
            start_pos: 开始位置
            
        Returns:
            文件名列表
        """
        remaining_text = text[start_pos:]
        filenames = []
        
        # 文件名模式：从【或文件名开始字符到扩展名结束
        filename_pattern = r'([【][^\.]*?\.(?:mp4|avi|mkv|mov|flv|webm|m4a|mp3|wav|srt)|[\w\u4e00-\u9fff][^\.]*?\.(?:mp4|avi|mkv|mov|flv|webm|m4a|mp3|wav|srt))'
        matches = re.finditer(filename_pattern, remaining_text, re.IGNORECASE)
        
        for match in matches:
            filename = match.group(1).rstrip('.,;:!?)\'"）')
            if filename:
                filenames.append(filename)
        
        return filenames
    
    @classmethod
    def _extract_full_paths(cls, text: str) -> List[str]:
        """
        直接提取完整路径（不依赖目录提示词）
        
        Args:
            text: 输入文本
            
        Returns:
            完整路径列表
        """
        paths = []
        
        # 规范化：处理以 // 开头的路径（用户输入错误，应该是 /）
        normalized_text = text
        if text.startswith('//') and not text.startswith('///'):
            normalized_text = text[1:]  # 移除多余的 /
        
        # 匹配完整路径模式：/path/to/file.ext 或 ~/path/to/file.ext
        # 支持以 / 或 // 开头的路径（// 会在规范化后处理）
        # 支持路径中包含空格和中文字符，直到文件扩展名
        # 使用非贪婪匹配，匹配到第一个文件扩展名就停止
        full_path_pattern = r'(?:^|(?<=\s))((?:[~/]|//?|/home/|/Users/|[A-Za-z]:\\\\)[^\s"\'\),。，、]+(?:[^\s"\'\),。，、\d]+[^\s"\'\),。，、]*?)?\.(?:mp4|avi|mkv|mov|flv|webm|m4a|mp3|wav|srt))'
        matches = re.finditer(full_path_pattern, normalized_text, re.IGNORECASE)
        
        for match in matches:
            path = match.group(1).rstrip('.,;:!?)\'"）')
            # 规范化：处理以 // 开头的路径
            if path.startswith('//') and not path.startswith('///'):
                path = path[1:]  # 移除多余的 /
            # 移除"目录下"等提示词
            path = re.sub(r'\s+目录下?\s+', '/', path)
            path = re.sub(r'\s+目录下?$', '', path)
            if path.startswith('~'):
                path = str(Path(path).expanduser())
            if path:
                paths.append(path)
        
        # 如果上面的模式没有匹配到，尝试更宽松的模式：匹配包含空格的路径
        # 这个模式会匹配从 / 开始到文件扩展名结束的所有内容（包括空格）
        if not paths:
            # 找到第一个 / 的位置
            slash_pos = normalized_text.find('/')
            if slash_pos >= 0:
                # 从 / 开始，找到第一个文件扩展名
                ext_pattern = r'\.(?:mp4|avi|mkv|mov|flv|webm|m4a|mp3|wav|srt)'
                ext_match = re.search(ext_pattern, normalized_text[slash_pos:], re.IGNORECASE)
                if ext_match:
                    # 提取从 / 到扩展名结束的路径
                    path_end = slash_pos + ext_match.end()
                    potential_path = normalized_text[slash_pos:path_end].strip()
                    # 检查路径是否合理（至少包含目录分隔符或文件扩展名）
                    if '/' in potential_path[1:] or '.' in potential_path:
                        # 规范化：处理以 // 开头的路径
                        if potential_path.startswith('//') and not potential_path.startswith('///'):
                            potential_path = potential_path[1:]
                        if potential_path.startswith('~'):
                            potential_path = str(Path(potential_path).expanduser())
                        if potential_path:
                            paths.append(potential_path)
        
        return paths
    
    @classmethod
    def _join_path(cls, dir_path: str, filename: str) -> Optional[str]:
        """
        安全地组合目录路径和文件名
        
        Args:
            dir_path: 目录路径
            filename: 文件名
            
        Returns:
            完整路径，如果无效则返回 None
        """
        if not dir_path or not filename:
            return None
        
        # 清理路径
        dir_path = dir_path.rstrip('/')
        filename = filename.lstrip('/')
        
        # 组合路径
        full_path = f"{dir_path}/{filename}"
        
        # 规范化路径（处理多个连续斜杠）
        full_path = re.sub(r'/+', '/', full_path)
        
        return full_path
    
    @classmethod
    def normalize_path(cls, path: str) -> Optional[str]:
        """
        规范化文件路径
        
        Args:
            path: 原始路径
            
        Returns:
            规范化后的路径，如果无效则返回 None
        """
        if not path:
            return None
        
        # 移除多余的引号
        path = path.strip('"\'')
        
        # 扩展 ~ 路径
        if path.startswith('~'):
            path = str(Path(path).expanduser())
        
        # 规范化路径分隔符
        path = os.path.normpath(path)
        
        # 验证路径格式
        if not cls._is_valid_path(path):
            return None
        
        return path
    
    @classmethod
    def _is_valid_path(cls, path: str) -> bool:
        """
        验证路径是否有效
        
        Args:
            path: 路径字符串
            
        Returns:
            是否有效
        """
        if not path:
            return False
        
        # 检查是否包含有效的文件扩展名
        path_lower = path.lower()
        has_valid_extension = any(path_lower.endswith(ext) for ext in cls.ALL_EXTENSIONS)
        
        # 检查路径格式
        is_absolute = path.startswith('/') or path.startswith('~') or re.match(r'^[A-Za-z]:\\', path)
        is_relative = not is_absolute and '/' in path
        
        return has_valid_extension and (is_absolute or is_relative)
    
    @classmethod
    def validate_path(cls, path: str, must_exist: bool = False) -> Tuple[bool, Optional[str]]:
        """
        验证文件路径
        
        Args:
            path: 文件路径
            must_exist: 是否必须存在
            
        Returns:
            (是否有效, 错误信息)
        """
        if not path:
            return False, "路径为空"
        
        # 规范化路径
        normalized = cls.normalize_path(path)
        if not normalized:
            return False, "路径格式无效"
        
        # 检查文件是否存在
        if must_exist:
            path_obj = Path(normalized)
            if not path_obj.exists():
                return False, f"文件不存在: {normalized}"
            if not path_obj.is_file():
                return False, f"不是文件: {normalized}"
        
        return True, None
    
    @classmethod
    def resolve_relative_path(cls, base_path: str, relative_path: str) -> Optional[str]:
        """
        解析相对路径
        
        Args:
            base_path: 基础路径
            relative_path: 相对路径
            
        Returns:
            解析后的绝对路径
        """
        try:
            base = Path(base_path).resolve()
            if base.is_file():
                base = base.parent
            resolved = (base / relative_path).resolve()
            return str(resolved)
        except Exception as e:
            logger.warning(f"解析相对路径失败: {e}")
            return None


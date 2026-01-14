"""消息处理模块 - 负责解析和处理从后端接收的消息"""
import json
from typing import Optional, Dict, Any
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent


class MessageHandler:
    """消息处理器，负责解析和处理各种类型的消息"""
    
    @staticmethod
    def _clean_unicode(text: str) -> str:
        """清理无效的 Unicode 字符（代理对）"""
        try:
            return text.encode('utf-8', errors='surrogatepass').decode('utf-8', errors='replace')
        except Exception:
            return text.encode('utf-8', errors='replace').decode('utf-8', errors='replace')
    
    @staticmethod
    def parse_line(line: str) -> Optional[Dict[str, Any]]:
        """
        解析一行消息，返回消息类型和内容
        
        Returns:
            {
                "type": "debug" | "tool" | "confirm" | "evaluation" | "status" | "content",
                "data": {...} 或 str
            } 或 None（如果是普通内容）
        """
        line = MessageHandler._clean_unicode(line)
        
        # 调试信息
        if line.startswith("__DEBUG__:"):
            try:
                json_str = line[10:]  # 移除 "__DEBUG__:" 前缀
                json_str = MessageHandler._clean_unicode(json_str)
                data = json.loads(json_str)
                return {"type": "debug", "data": data}
            except (json.JSONDecodeError, KeyError, UnicodeDecodeError):
                return None
        
        # 工具调用
        elif line.startswith("__TOOL__:"):
            try:
                json_str = line[9:]  # 移除 "__TOOL__:" 前缀
                json_str = MessageHandler._clean_unicode(json_str)
                data = json.loads(json_str)
                return {"type": "tool", "data": data}
            except (json.JSONDecodeError, KeyError, UnicodeDecodeError):
                return None
        
        # 确认请求
        elif line.startswith("__CONFIRM__:"):
            try:
                json_str = line[11:]  # 移除 "__CONFIRM__:" 前缀
                json_str = MessageHandler._clean_unicode(json_str)
                data = json.loads(json_str)
                return {"type": "confirm", "data": data}
            except (json.JSONDecodeError, KeyError, UnicodeDecodeError):
                return None
        
        # 评估结果
        elif line.startswith("__EVALUATION__:"):
            try:
                json_str = line[15:]  # 移除 "__EVALUATION__:" 前缀
                json_str = MessageHandler._clean_unicode(json_str)
                data = json.loads(json_str)
                return {"type": "evaluation", "data": data}
            except (json.JSONDecodeError, KeyError, UnicodeDecodeError):
                return None
        
        # 状态更新（长任务）
        elif line.startswith("__STATUS__:"):
            try:
                json_str = line[11:]  # 移除 "__STATUS__:" 前缀
                json_str = MessageHandler._clean_unicode(json_str)
                data = json.loads(json_str)
                return {"type": "status", "data": data}
            except (json.JSONDecodeError, KeyError, UnicodeDecodeError):
                return None
        
        # 普通内容
        else:
            return {"type": "content", "data": line}
    
    @staticmethod
    def parse_chunk(chunk: str, buffer: str = "") -> tuple[list[Dict[str, Any]], str]:
        """
        解析数据块，返回解析后的消息列表和剩余的缓冲区
        
        Args:
            chunk: 新的数据块
            buffer: 之前的缓冲区内容
            
        Returns:
            (messages, new_buffer): 消息列表和新的缓冲区
        """
        messages = []
        buffer += MessageHandler._clean_unicode(chunk)
        
        # 按行分割处理
        while "\n" in buffer:
            line, buffer = buffer.split("\n", 1)
            if not line.strip():
                continue
            
            parsed = MessageHandler.parse_line(line)
            if parsed:
                messages.append(parsed)
        
        return messages, buffer


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

        # 工具进度（execute_code/exec 流式输出）
        elif line.startswith("__PROGRESS__:"):
            try:
                json_str = line[12:]  # 移除 "__PROGRESS__:" 前缀
                json_str = MessageHandler._clean_unicode(json_str)
                data = json.loads(json_str)
                return {"type": "progress", "data": data}
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
        
        # 先检查是否有特殊标记（可能在行中间）
        # 处理可能在同一行中包含多个消息的情况
        special_markers = ["__DEBUG__:", "__TOOL__:", "__CONFIRM__:", "__EVALUATION__:", "__STATUS__:", "__PROGRESS__:", "__ORCH_TRACE__:"]
        
        # 按行分割处理
        while "\n" in buffer:
            line, buffer = buffer.split("\n", 1)
            if not line.strip():
                continue
            
            # 检查行中是否包含特殊标记（可能在同一行有多个消息）
            # 例如: "some content__EVALUATION__:{...}"
            found_marker = False
            for marker in special_markers:
                if marker in line:
                    found_marker = True
                    # 分割：标记之前的内容和标记之后的内容
                    parts = line.split(marker, 1)
                    if len(parts) == 2:
                        # 标记之前的内容（如果有）作为普通内容
                        before_marker = parts[0].strip()
                        if before_marker:
                            messages.append({"type": "content", "data": before_marker})
                        
                        # 标记之后的内容（可能包含JSON和后续内容）
                        after_marker = parts[1]
                        
                        # 尝试提取JSON部分
                        # JSON可能跨多行，需要找到完整的JSON对象
                        json_str = ""
                        brace_count = 0
                        in_string = False
                        escape_next = False
                        json_end = 0
                        
                        for i, char in enumerate(after_marker):
                            if escape_next:
                                escape_next = False
                                continue
                            
                            if char == '\\':
                                escape_next = True
                                continue
                            
                            if char == '"' and not escape_next:
                                in_string = not in_string
                            
                            if not in_string:
                                if char == '{':
                                    brace_count += 1
                                elif char == '}':
                                    brace_count -= 1
                                    if brace_count == 0:
                                        json_end = i + 1
                                        json_str = after_marker[:json_end].strip()
                                        break
                            
                            # 如果遇到下一个标记且JSON未完成，停止
                            for other_marker in special_markers:
                                if after_marker[i:].startswith(other_marker) and brace_count > 0:
                                    # JSON未完成，保留在buffer中
                                    return messages, line  # 将整行放回buffer
                        
                        # 如果找到了完整的JSON
                        if json_str:
                            parsed = MessageHandler._parse_special_message(marker, json_str)
                            if parsed:
                                messages.append(parsed)
                            
                            # 处理剩余内容（在JSON之后）
                            remaining = after_marker[json_end:].strip()
                            if remaining:
                                # 递归处理剩余内容
                                remaining_messages, _ = MessageHandler.parse_chunk(remaining, "")
                                messages.extend(remaining_messages)
                        else:
                            # JSON不完整，保留在buffer中
                            return messages, line
                    
                    break
            
            if not found_marker:
                # 没有特殊标记，作为普通内容处理
                parsed = MessageHandler.parse_line(line)
                if parsed:
                    messages.append(parsed)
        
        return messages, buffer
    
    @staticmethod
    def _parse_special_message(marker: str, json_str: str) -> Optional[Dict[str, Any]]:
        """解析特殊标记的消息"""
        try:
            json_str = MessageHandler._clean_unicode(json_str)
            data = json.loads(json_str)
            
            marker_map = {
                "__DEBUG__:": "debug",
                "__TOOL__:": "tool",
                "__CONFIRM__:": "confirm",
                "__EVALUATION__:": "evaluation",
                "__STATUS__:": "status",
                "__PROGRESS__:": "progress",
                "__ORCH_TRACE__:": "orch_trace",
            }
            
            msg_type = marker_map.get(marker)
            if msg_type:
                return {"type": msg_type, "data": data}
        except (json.JSONDecodeError, KeyError, UnicodeDecodeError):
            pass
        return None


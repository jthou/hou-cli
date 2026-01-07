"""执行结果处理"""
from backend.infrastructure.execution.models import ExecutionResult, ResourceUsage


class ResultHandler:
    """结果处理器
    
    处理执行结果：输出截断、错误格式化、资源使用统计
    """
    
    # 输出大小限制（字节）
    MAX_OUTPUT_SIZE = 10 * 1024 * 1024  # 10MB
    
    def truncate_output(self, output: str) -> str:
        """截断输出（防止过大输出）"""
        # #region agent log
        try:
            import json
            with open('/System/Volumes/Data/justin/dev/hou-cli/.cursor/debug.log', 'a', encoding='utf-8') as f:
                json.dump({"sessionId":"debug-session","runId":"run1","hypothesisId":"D","location":"result_handler.py:truncate_output","message":"开始处理输出","data":{"output_type":type(output).__name__,"output_len":len(str(output)) if output else 0},"timestamp":int(__import__('time').time()*1000)}, f, ensure_ascii=False)
                f.write('\n')
        except: pass
        # #endregion
        if not output:
            return ""
        
        try:
            # 确保 output 是字符串
            if isinstance(output, bytes):
                # 如果是字节，先尝试解码
                output = output.decode('utf-8', errors='replace')
            elif not isinstance(output, str):
                output = str(output)
            
            # 清理无效字符：编码再解码
            try:
                output = output.encode('utf-8', errors='replace').decode('utf-8', errors='replace')
            except Exception as e:
                # #region agent log
                try:
                    import json
                    with open('/System/Volumes/Data/justin/dev/hou-cli/.cursor/debug.log', 'a', encoding='utf-8') as f:
                        json.dump({"sessionId":"debug-session","runId":"run1","hypothesisId":"D","location":"result_handler.py:truncate_output","message":"编码清理失败","data":{"error":str(e)[:200]},"timestamp":int(__import__('time').time()*1000)}, f, ensure_ascii=False)
                        f.write('\n')
                except: pass
                # #endregion
                # 如果编码失败，尝试其他方法
                output = output.encode('utf-8', errors='ignore').decode('utf-8', errors='replace')
            
            # 检查大小
            output_bytes = output.encode('utf-8', errors='replace')
            if len(output_bytes) > self.MAX_OUTPUT_SIZE:
                # #region agent log
                try:
                    import json
                    with open('/System/Volumes/Data/justin/dev/hou-cli/.cursor/debug.log', 'a', encoding='utf-8') as f:
                        json.dump({"sessionId":"debug-session","runId":"run1","hypothesisId":"D","location":"result_handler.py:truncate_output","message":"需要截断输出","data":{"output_bytes_len":len(output_bytes),"max_size":self.MAX_OUTPUT_SIZE},"timestamp":int(__import__('time').time()*1000)}, f, ensure_ascii=False)
                        f.write('\n')
                except: pass
                # #endregion
                # 安全截断：确保不截断多字节字符
                truncated = output_bytes[:self.MAX_OUTPUT_SIZE]
                # 尝试找到最后一个完整的 UTF-8 字符边界
                while truncated and (truncated[-1] & 0xC0) == 0x80:
                    truncated = truncated[:-1]
                truncated = truncated.decode('utf-8', errors='replace')
                return truncated + "\n... (输出已截断，超过 10MB)"
            
            return output
        except Exception as e:
            # #region agent log
            try:
                import json
                with open('/System/Volumes/Data/justin/dev/hou-cli/.cursor/debug.log', 'a', encoding='utf-8') as f:
                    json.dump({"sessionId":"debug-session","runId":"run1","hypothesisId":"D","location":"result_handler.py:truncate_output","message":"处理输出异常","data":{"error_type":type(e).__name__,"error_msg":str(e)[:200]},"timestamp":int(__import__('time').time()*1000)}, f, ensure_ascii=False)
                    f.write('\n')
            except: pass
            # #endregion
            # 如果所有方法都失败，返回清理后的错误信息
            try:
                error_msg = str(e).encode('utf-8', errors='replace').decode('utf-8', errors='replace')
                return f"[编码错误: 无法处理输出] {error_msg[:100]}"
            except Exception:
                return "[编码错误: 无法处理输出]"
    
    def format_error(self, error: str) -> str:
        """格式化错误信息"""
        if not error:
            return ""
        
        # 简单的错误格式化
        # 可以在这里添加更复杂的错误解析逻辑
        return f"错误: {error}"
    
    def format_resource_usage(self, usage: ResourceUsage) -> str:
        """格式化资源使用情况"""
        if not usage:
            return ""
        
        lines = []
        if usage.execution_time_seconds > 0:
            lines.append(f"执行时间: {usage.execution_time_seconds:.2f} 秒")
        if usage.memory_used_mb > 0:
            lines.append(f"内存使用: {usage.memory_used_mb:.2f} MB")
        if usage.cpu_used_percent > 0:
            lines.append(f"CPU 使用: {usage.cpu_used_percent:.2f}%")
        
        return "\n".join(lines)
    
    def process_result(self, result: ExecutionResult) -> ExecutionResult:
        """处理执行结果"""
        # 截断输出
        if result.output:
            result.output = self.truncate_output(result.output)
        
        # 格式化错误
        if result.error:
            result.error = self.format_error(result.error)
        
        return result

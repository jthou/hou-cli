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
        output_bytes = output.encode('utf-8')
        if len(output_bytes) > self.MAX_OUTPUT_SIZE:
            truncated = output_bytes[:self.MAX_OUTPUT_SIZE].decode('utf-8', errors='ignore')
            return truncated + "\n... (输出已截断，超过 10MB)"
        return output
    
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

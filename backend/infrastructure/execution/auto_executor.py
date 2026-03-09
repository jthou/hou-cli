"""自动代码执行器"""
import re
import logging
from typing import List, Dict, Any, Optional
from backend.infrastructure.execution.secure_executor import SecureExecutor
from backend.infrastructure.execution.models import ExecutionRequest

logger = logging.getLogger(__name__)


class CodeExtractor:
    """代码提取器
    
    从 LLM 输出中提取代码块
    """
    
    # 代码块模式
    CODE_BLOCK_PATTERNS = {
        "python": r"```python\s*([\s\S]*?)```",
        "bash": r"```bash\s*([\s\S]*?)```",
        "shell": r"```shell\s*([\s\S]*?)```",
        "sh": r"```sh\s*([\s\S]*?)```",
        "zsh": r"```zsh\s*([\s\S]*?)```",
        "powershell": r"```powershell\s*([\s\S]*?)```",
        "ps1": r"```ps1\s*([\s\S]*?)```",
        "batch": r"```batch\s*([\s\S]*?)```",
        "cmd": r"```cmd\s*([\s\S]*?)```",
    }
    
    # 语言名称映射（统一到 zsh，当前仅支持 python、zsh）
    LANGUAGE_MAPPING = {
        "shell": "zsh",
        "sh": "zsh",
        "bash": "zsh",
        "ps1": "zsh",   # 暂不支持 powershell，映射到 zsh 会执行失败
        "cmd": "zsh",   # 暂不支持 batch
    }
    
    def extract_code_blocks(self, llm_output: str) -> List[Dict[str, str]]:
        """从 LLM 输出中提取代码块"""
        code_blocks = []
        
        for pattern_name, pattern in self.CODE_BLOCK_PATTERNS.items():
            matches = re.findall(pattern, llm_output, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                code = self._clean_code(match)
                if code:
                    language = self._normalize_language(pattern_name)
                    code_blocks.append({
                        "language": language,
                        "code": code
                    })
        
        # 去重（相同的代码块只保留一个）
        seen = set()
        unique_blocks = []
        for block in code_blocks:
            key = (block["language"], block["code"].strip())
            if key not in seen:
                seen.add(key)
                unique_blocks.append(block)
        
        return unique_blocks
    
    def _clean_code(self, code: str) -> str:
        """清理代码"""
        # 去除首尾空白
        code = code.strip()
        
        # 去除开头的注释行（可选，可以根据需要调整）
        # lines = [line for line in code.split('\n') 
        #          if not line.strip().startswith('#')]
        # code = '\n'.join(lines)
        
        return code
    
    def _normalize_language(self, lang: str) -> str:
        """标准化语言名称"""
        return self.LANGUAGE_MAPPING.get(lang.lower(), lang.lower())


class AutoCodeExecutor:
    """自动代码执行器
    
    从 LLM 输出中自动检测并执行代码块
    """
    
    def __init__(self):
        """初始化自动执行器"""
        self.extractor = CodeExtractor()
        self.executor = SecureExecutor()
    
    async def process_llm_output(
        self,
        llm_output: str,
        auto_execute: bool = True,
        require_confirmation: bool = False
    ) -> Dict[str, Any]:
        """处理 LLM 输出，自动检测并执行代码"""
        
        # 提取代码块
        code_blocks = self.extractor.extract_code_blocks(llm_output)
        
        if not code_blocks:
            return {
                "output": llm_output,
                "code_executed": False,
                "execution_results": []
            }
        
        logger.info(f"Extracted {len(code_blocks)} code blocks from LLM output")
        
        # 如果需要确认
        if require_confirmation:
            # 这里可以添加用户确认逻辑
            # 暂时默认执行
            pass
        
        # 执行代码块
        execution_results = []
        for i, block in enumerate(code_blocks, 1):
            try:
                logger.info(f"Executing code block {i}/{len(code_blocks)}: {block['language']}")
                
                request = ExecutionRequest(
                    code=block["code"],
                    language=block["language"],
                    timeout=30
                )
                
                result = await self.executor.execute_code_safely(request)
                
                execution_results.append({
                    "index": i,
                    "language": block["language"],
                    "code": block["code"],
                    "result": {
                        "success": result.success,
                        "output": result.output,
                        "error": result.error,
                        "exit_code": result.exit_code,
                        "execution_time": result.resource_usage.execution_time_seconds if result.resource_usage else 0,
                        "memory_used": result.resource_usage.memory_used_mb if result.resource_usage else 0
                    }
                })
                
            except Exception as e:
                logger.error(f"Error executing code block {i}: {str(e)}", exc_info=True)
                execution_results.append({
                    "index": i,
                    "language": block["language"],
                    "code": block["code"],
                    "error": str(e)
                })
        
        # 构建增强的输出
        if auto_execute and execution_results:
            enhanced_output = self._build_enhanced_output(llm_output, execution_results)
        else:
            enhanced_output = llm_output
        
        return {
            "output": enhanced_output,
            "code_executed": len(execution_results) > 0,
            "execution_results": execution_results
        }
    
    def _build_enhanced_output(
        self,
        original_output: str,
        execution_results: List[Dict]
    ) -> str:
        """构建增强的输出（包含执行结果）"""
        enhanced = original_output + "\n\n"
        enhanced += "## 执行结果\n\n"
        
        for result in execution_results:
            enhanced += f"### 代码块 {result['index']} ({result['language']})\n\n"
            
            if "error" in result:
                enhanced += f"❌ 执行失败: {result['error']}\n\n"
            else:
                exec_result = result["result"]
                if exec_result["success"]:
                    enhanced += f"✅ 执行成功\n\n"
                    if exec_result.get("output"):
                        output = exec_result["output"]
                        # 限制输出长度
                        if len(output) > 500:
                            output = output[:500] + "\n... (输出已截断)"
                        enhanced += f"**输出：**\n```\n{output}\n```\n\n"
                else:
                    enhanced += f"❌ 执行失败\n\n"
                    if exec_result.get("error"):
                        error = exec_result["error"]
                        if len(error) > 500:
                            error = error[:500] + "\n... (错误信息已截断)"
                        enhanced += f"**错误：**\n```\n{error}\n```\n\n"
                
                if exec_result.get("execution_time", 0) > 0:
                    enhanced += f"执行时间: {exec_result['execution_time']:.2f} 秒\n"
                if exec_result.get("memory_used", 0) > 0:
                    enhanced += f"内存使用: {exec_result['memory_used']:.2f} MB\n"
                enhanced += "\n"
        
        return enhanced


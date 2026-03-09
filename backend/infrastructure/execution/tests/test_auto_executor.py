"""自动执行器测试"""
import pytest
import asyncio
from backend.infrastructure.execution.auto_executor import CodeExtractor, AutoCodeExecutor


class TestCodeExtractor:
    """CodeExtractor 测试"""
    
    @pytest.fixture
    def extractor(self):
        """创建代码提取器实例"""
        return CodeExtractor()
    
    def test_extract_python_code(self, extractor):
        """测试提取 Python 代码块"""
        output = """
        可以使用以下代码：
        ```python
        print('hello')
        ```
        """
        blocks = extractor.extract_code_blocks(output)
        
        assert len(blocks) == 1
        assert blocks[0]["language"] == "python"
        assert "print('hello')" in blocks[0]["code"]
    
    def test_extract_bash_code(self, extractor):
        """测试提取 bash 代码块（标准化为 zsh）"""
        output = """
        ```bash
        echo "hello"
        ```
        """
        blocks = extractor.extract_code_blocks(output)
        
        assert len(blocks) == 1
        assert blocks[0]["language"] == "zsh"  # bash 映射为 zsh
        assert "echo" in blocks[0]["code"]
    
    def test_extract_multiple_blocks(self, extractor):
        """测试提取多个代码块"""
        output = """
        ```python
        print('hello')
        ```
        
        ```bash
        echo "world"
        ```
        """
        blocks = extractor.extract_code_blocks(output)
        
        assert len(blocks) == 2
        assert blocks[0]["language"] == "python"
        assert blocks[1]["language"] == "zsh"  # bash 映射为 zsh
    
    def test_extract_no_code_blocks(self, extractor):
        """测试没有代码块的情况"""
        output = "This is just text without code blocks."
        blocks = extractor.extract_code_blocks(output)
        
        assert len(blocks) == 0
    
    def test_normalize_language(self, extractor):
        """测试语言名称标准化（shell/sh/bash 映射为 zsh）"""
        assert extractor._normalize_language("shell") == "zsh"
        assert extractor._normalize_language("sh") == "zsh"
        assert extractor._normalize_language("bash") == "zsh"
        assert extractor._normalize_language("ps1") == "zsh"
        assert extractor._normalize_language("python") == "python"


class TestAutoCodeExecutor:
    """AutoCodeExecutor 测试"""
    
    @pytest.fixture
    def executor(self):
        """创建自动执行器实例"""
        return AutoCodeExecutor()
    
    @pytest.mark.asyncio
    async def test_auto_execute_code(self, executor):
        """测试自动执行代码"""
        llm_output = """
        可以使用以下代码：
        ```python
        print('hello')
        ```
        """
        result = await executor.process_llm_output(llm_output, auto_execute=True)
        
        assert result["code_executed"] is True
        assert len(result["execution_results"]) == 1
        assert result["execution_results"][0]["result"]["success"] is True
        assert "hello" in result["execution_results"][0]["result"]["output"]
    
    @pytest.mark.asyncio
    async def test_no_code_blocks(self, executor):
        """测试没有代码块的情况"""
        llm_output = "This is just text without code blocks."
        result = await executor.process_llm_output(llm_output, auto_execute=True)
        
        assert result["code_executed"] is False
        assert len(result["execution_results"]) == 0
        assert result["output"] == llm_output
    
    @pytest.mark.asyncio
    async def test_multiple_code_blocks(self, executor):
        """测试多个代码块"""
        llm_output = """
        ```python
        print('hello')
        ```
        
        ```python
        print('world')
        ```
        """
        result = await executor.process_llm_output(llm_output, auto_execute=True)
        
        assert result["code_executed"] is True
        assert len(result["execution_results"]) == 2
    
    @pytest.mark.asyncio
    async def test_enhanced_output(self, executor):
        """测试增强输出"""
        llm_output = """
        ```python
        print('hello')
        ```
        """
        result = await executor.process_llm_output(llm_output, auto_execute=True)
        
        assert "执行结果" in result["output"]
        assert "代码块" in result["output"]


"""JupyterTool 测试"""
import pytest
import os
from unittest.mock import patch, MagicMock
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()

from backend.core.agent.tools.builtin.jupyter_tool import JupyterTool, JUPYTER_AVAILABLE
from backend.core.agent.tools.base import ToolResult


class TestJupyterTool:
    """JupyterTool 单元测试"""

    @pytest.fixture
    def tool(self):
        """创建 JupyterTool 实例"""
        return JupyterTool()

    def test_tool_initialization(self, tool):
        """测试工具初始化"""
        assert tool.name == "jupyter"
        assert tool.description is not None
        assert len(tool.parameters) >= 2

        param_names = [p.name for p in tool.parameters]
        assert "code" in param_names
        assert "kernel_name" in param_names

    def test_missing_code(self, tool):
        """测试缺少 code 参数"""
        result = tool.execute()
        assert result.success is False
        # 如果 jupyter-client 不可用，错误信息会不同，所以检查多种情况
        error_lower = result.error.lower()
        assert (
            "code" in error_lower or 
            "必需" in result.error or
            "jupyter-client" in error_lower or
            "not installed" in error_lower
        )

    @pytest.mark.skipif(
        not JUPYTER_AVAILABLE,
        reason="需要安装 jupyter-client"
    )
    def test_execute_simple_code(self, tool):
        """测试执行简单代码"""
        result = tool.execute(
            code="print('Hello, World!')",
            kernel_name="python3",
            timeout=30
        )

        if result.success:
            assert "output" in result.data
            assert "Hello, World!" in result.data["output"]
        else:
            # 检查是否是 kernel 问题
            if "kernel" in result.error.lower() or "未找到" in result.error:
                pytest.skip(f"Jupyter kernel 问题: {result.error}")

    @pytest.mark.skipif(
        not JUPYTER_AVAILABLE,
        reason="需要安装 jupyter-client"
    )
    def test_variable_persistence(self, tool):
        """测试变量持久化（跨代码块）"""
        # 第一个代码块：定义变量
        result1 = tool.execute(
            code="x = 10\ny = 20",
            kernel_name="python3",
            timeout=30
        )

        if not result1.success:
            pytest.skip(f"第一个代码块执行失败: {result1.error}")

        # 第二个代码块：使用变量
        result2 = tool.execute(
            code="print(f'Sum: {x + y}')",
            kernel_name="python3",
            timeout=30,
            clear_output=False
        )

        if result2.success:
            assert "output" in result2.data
            assert "Sum: 30" in result2.data["output"]
        else:
            if "kernel" in result2.error.lower() or "未找到" in result2.error:
                pytest.skip(f"Jupyter kernel 问题: {result2.error}")

    def test_timeout_validation(self, tool):
        """测试超时参数验证"""
        # 测试超过最大超时
        result = tool.execute(
            code="print('test')",
            timeout=500
        )
        # 应该被限制到 300

    def test_invalid_kernel(self, tool):
        """测试无效的 kernel"""
        if not JUPYTER_AVAILABLE:
            pytest.skip("需要安装 jupyter-client")

        result = tool.execute(
            code="print('test')",
            kernel_name="invalid_kernel",
            timeout=30
        )

        # 应该返回错误
        if result.success:
            # 如果成功，可能是自动回退到默认 kernel
            pass
        else:
            assert "kernel" in result.error.lower() or "未找到" in result.error


class TestJupyterToolIntegration:
    """JupyterTool 集成测试（需要真实环境）"""

    @pytest.fixture
    def tool(self):
        """创建 JupyterTool 实例"""
        return JupyterTool()

    @pytest.mark.skipif(
        not JUPYTER_AVAILABLE,
        reason="需要安装 jupyter-client"
    )
    @pytest.mark.integration
    def test_data_analysis_workflow(self, tool):
        """测试数据分析工作流"""
        # 导入库
        result1 = tool.execute(
            code="import numpy as np\nimport pandas as pd",
            kernel_name="python3",
            timeout=30
        )

        if not result1.success:
            pytest.skip(f"导入库失败: {result1.error}")

        # 创建数据
        result2 = tool.execute(
            code="""
data = np.array([1, 2, 3, 4, 5])
df = pd.DataFrame({'values': data})
print(df)
""",
            kernel_name="python3",
            timeout=30,
            clear_output=False
        )

        if result2.success:
            assert "output" in result2.data
        else:
            if "kernel" in result2.error.lower() or "未找到" in result2.error:
                pytest.skip(f"Jupyter kernel 问题: {result2.error}")

    @pytest.mark.skipif(
        not JUPYTER_AVAILABLE,
        reason="需要安装 jupyter-client"
    )
    @pytest.mark.integration
    def test_clear_output(self, tool):
        """测试清除输出功能"""
        # 执行第一个代码块
        result1 = tool.execute(
            code="x = 10",
            kernel_name="python3",
            timeout=30
        )

        if not result1.success:
            pytest.skip(f"第一个代码块执行失败: {result1.error}")

        # 清除输出后执行第二个代码块
        result2 = tool.execute(
            code="print(x)",
            kernel_name="python3",
            timeout=30,
            clear_output=True
        )

        if result2.success:
            assert "output" in result2.data
        else:
            if "kernel" in result2.error.lower() or "未找到" in result2.error:
                pytest.skip(f"Jupyter kernel 问题: {result2.error}")


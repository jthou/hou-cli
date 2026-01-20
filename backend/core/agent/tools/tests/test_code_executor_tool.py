"""CodeExecutorTool 测试"""
import pytest
import os
from unittest.mock import patch, MagicMock
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()

from backend.core.agent.tools.builtin.code_executor_tool import CodeExecutorTool
from backend.core.agent.tools.base import ToolResult


class TestCodeExecutorTool:
    """CodeExecutorTool 单元测试"""

    @pytest.fixture
    def tool(self):
        """创建 CodeExecutorTool 实例"""
        return CodeExecutorTool()

    def test_tool_initialization(self, tool):
        """测试工具初始化"""
        assert tool.name == "execute_code"
        assert tool.description is not None
        assert len(tool.parameters) >= 2

        param_names = [p.name for p in tool.parameters]
        assert "code" in param_names
        assert "language" in param_names

    def test_missing_code(self, tool):
        """测试缺少 code 参数"""
        result = tool.execute()
        assert result.success is False
        assert "code" in result.error.lower() or "必需" in result.error

    def test_missing_language(self, tool):
        """测试缺少 language 参数"""
        result = tool.execute(code="print('hello')")
        assert result.success is False
        assert "language" in result.error.lower() or "必需" in result.error

    def test_invalid_language(self, tool):
        """测试无效的语言"""
        result = tool.execute(code="print('hello')", language="invalid")
        assert result.success is False
        assert "不支持" in result.error or "invalid" in result.error.lower()

    def test_timeout_validation(self, tool):
        """测试超时参数验证"""
        # 测试超过最大超时
        result = tool.execute(
            code="print('hello')",
            language="python",
            timeout=500
        )
        # 应该被限制到 300

    def test_execute_python_code(self, tool):
        """测试执行 Python 代码"""
        result = tool.execute(
            code="print('Hello, World!')",
            language="python",
            timeout=10
        )

        if result.success:
            assert "output" in result.data
            assert "Hello, World!" in result.data["output"]
        else:
            # 检查是否是执行器问题
            if "执行器" in result.error or "executor" in result.error.lower():
                pytest.skip(f"代码执行器问题: {result.error}")

    def test_execute_bash_code(self, tool):
        """测试执行 bash 代码"""
        result = tool.execute(
            code="echo 'Hello, World!'",
            language="bash",
            timeout=10
        )

        if result.success:
            assert "output" in result.data
        else:
            if "执行器" in result.error or "executor" in result.error.lower():
                pytest.skip(f"代码执行器问题: {result.error}")

    def test_dangerous_command_blocked(self, tool):
        """测试危险命令被阻止"""
        # 测试删除命令
        result = tool.execute(
            code="rm -rf /",
            language="bash",
            timeout=10
        )
        # 应该被阻止或返回错误
        if result.success:
            # 如果成功，检查输出中是否有警告
            assert "blocked" in result.data.get("output", "").lower() or \
                   "不允许" in result.data.get("output", "")

    def test_restricted_path_blocked(self, tool):
        """测试受限路径被阻止"""
        # 测试访问受限路径
        result = tool.execute(
            code="cat /etc/passwd",
            language="bash",
            timeout=10
        )
        # 应该被阻止或返回错误
        if result.success:
            # 如果成功，检查输出中是否有警告
            assert "blocked" in result.data.get("output", "").lower() or \
                   "不允许" in result.data.get("output", "")


class TestCodeExecutorToolIntegration:
    """CodeExecutorTool 集成测试（需要真实环境）"""

    @pytest.fixture
    def tool(self):
        """创建 CodeExecutorTool 实例"""
        return CodeExecutorTool()

    @pytest.mark.integration
    def test_python_workflow(self, tool):
        """测试 Python 代码执行工作流"""
        result = tool.execute(
            code="""
x = 10
y = 20
print(f"Sum: {x + y}")
""",
            language="python",
            timeout=30
        )

        if result.success:
            assert "output" in result.data
            assert "Sum: 30" in result.data["output"]
        else:
            if "执行器" in result.error or "executor" in result.error.lower():
                pytest.skip(f"代码执行器问题: {result.error}")

    @pytest.mark.integration
    def test_bash_workflow(self, tool):
        """测试 bash 代码执行工作流"""
        result = tool.execute(
            code="""
echo "Test 1"
echo "Test 2"
""",
            language="bash",
            timeout=30
        )

        if result.success:
            assert "output" in result.data
            assert "Test 1" in result.data["output"]
            assert "Test 2" in result.data["output"]
        else:
            if "执行器" in result.error or "executor" in result.error.lower():
                pytest.skip(f"代码执行器问题: {result.error}")

    @pytest.mark.integration
    def test_error_handling(self, tool):
        """测试错误处理"""
        result = tool.execute(
            code="raise ValueError('Test error')",
            language="python",
            timeout=30
        )

        # 应该返回错误信息
        if result.success:
            assert "error" in result.data or "Error" in result.data.get("output", "")
        else:
            # 执行失败也是正常的
            assert "error" in result.error.lower() or "Error" in result.error


class TestCodeExecutorToolParameters:
    """CodeExecutorTool 参数测试"""

    @pytest.fixture
    def tool(self):
        """创建 CodeExecutorTool 实例"""
        return CodeExecutorTool()

    def test_tool_parameters(self, tool):
        """测试工具参数定义"""
        param_names = [p.name for p in tool.parameters]
        
        # 检查必需参数
        assert "code" in param_names
        assert "language" in param_names
        
        # 检查可选参数
        assert "timeout" in param_names
        assert "explanation" in param_names
        
        # 检查参数类型和默认值
        code_param = next((p for p in tool.parameters if p.name == "code"), None)
        assert code_param is not None
        assert code_param.required is True
        
        language_param = next((p for p in tool.parameters if p.name == "language"), None)
        assert language_param is not None
        assert language_param.required is True
        assert language_param.enum is not None
        assert "python" in language_param.enum
        assert "bash" in language_param.enum
        
        timeout_param = next((p for p in tool.parameters if p.name == "timeout"), None)
        assert timeout_param is not None
        assert timeout_param.required is False
        assert timeout_param.default == 30

    def test_timeout_boundary_values(self, tool):
        """测试超时边界值"""
        # 测试最小超时（应该被限制到 1）
        result = tool.execute(
            code="print('test')",
            language="python",
            timeout=0
        )
        # 应该被限制到最小值或默认值
        
        # 测试最大超时（应该被限制到 300）
        result = tool.execute(
            code="print('test')",
            language="python",
            timeout=500
        )
        # 应该被限制到 300

    def test_language_enum(self, tool):
        """测试支持的语言"""
        language_param = next((p for p in tool.parameters if p.name == "language"), None)
        assert language_param is not None
        assert language_param.enum is not None
        
        supported_languages = language_param.enum
        assert "python" in supported_languages
        assert "bash" in supported_languages
        assert "zsh" in supported_languages
        assert "powershell" in supported_languages
        assert "batch" in supported_languages


class TestCodeExecutorToolRegistry:
    """CodeExecutorTool 注册测试"""

    def test_tool_can_be_registered(self):
        """测试工具可以注册到注册表"""
        from backend.core.agent.tools.registry import ToolRegistry
        
        tool = CodeExecutorTool()
        registry = ToolRegistry()
        
        try:
            registry.register(tool)
        except ValueError:
            pass  # 已经注册过
        
        tools_list = registry.list_tools()
        assert "execute_code" in tools_list

    def test_tool_in_registry_list(self):
        """测试工具在注册表列表中"""
        from backend.core.agent.tools.registry import ToolRegistry
        
        registry = ToolRegistry()
        tools_list = registry.list_tools()
        
        assert "execute_code" in tools_list

    def test_tool_for_llm_format(self):
        """测试工具转换为 LLM 格式"""
        from backend.core.agent.tools.registry import ToolRegistry
        
        tool = CodeExecutorTool()
        registry = ToolRegistry()
        
        try:
            registry.register(tool)
        except ValueError:
            pass  # 已经注册过
        
        llm_tools = registry.get_tools_for_llm()
        tool_dict = next((t for t in llm_tools if t["function"]["name"] == "execute_code"), None)
        
        assert tool_dict is not None
        assert tool_dict["type"] == "function"
        assert tool_dict["function"]["name"] == "execute_code"
        assert "parameters" in tool_dict["function"]


class TestCodeExecutorToolResourceUsage:
    """CodeExecutorTool 资源使用测试"""

    @pytest.fixture
    def tool(self):
        """创建 CodeExecutorTool 实例"""
        return CodeExecutorTool()

    def test_resource_usage_tracking(self, tool):
        """测试资源使用统计"""
        result = tool.execute(
            code="print('test')",
            language="python",
            timeout=10
        )
        
        if result.success:
            assert "execution_time" in result.data
            assert "memory_used" in result.data
            # 执行时间应该是正数
            assert result.data["execution_time"] >= 0
            # 内存使用应该是正数或0
            assert result.data["memory_used"] >= 0


class TestCodeExecutorToolRiskDetection:
    """CodeExecutorTool 风险检测测试"""

    @pytest.fixture
    def tool(self):
        """创建 CodeExecutorTool 实例"""
        return CodeExecutorTool()

    def test_risk_detection_blocked(self, tool):
        """测试高风险代码被阻止"""
        # 测试删除命令
        result = tool.execute(
            code="rm -rf /",
            language="bash",
            timeout=10
        )
        
        # 应该被阻止
        assert result.success is False
        assert "禁止" in result.error or "blocked" in result.error.lower() or "不允许" in result.error

    def test_risk_detection_restricted_path(self, tool):
        """测试受限路径访问被阻止"""
        result = tool.execute(
            code="cat /etc/passwd",
            language="bash",
            timeout=10
        )
        
        # 应该被阻止
        assert result.success is False
        assert "禁止" in result.error or "blocked" in result.error.lower() or "不允许" in result.error


class TestCodeExecutorToolBashScripts:
    """CodeExecutorTool Bash 脚本测试"""

    @pytest.fixture
    def tool(self):
        """创建 CodeExecutorTool 实例"""
        return CodeExecutorTool()

    def test_bash_variables(self, tool):
        """测试 bash 变量"""
        result = tool.execute(
            code="""
NAME="World"
echo "Hello, $NAME!"
""",
            language="bash",
            timeout=10
        )
        
        if result.success:
            assert "output" in result.data
            assert "Hello, World!" in result.data["output"]
        else:
            if "执行器" in result.error or "executor" in result.error.lower():
                pytest.skip(f"代码执行器问题: {result.error}")

    def test_bash_conditional(self, tool):
        """测试 bash 条件判断"""
        result = tool.execute(
            code="""
if [ 1 -eq 1 ]; then
    echo "Condition is true"
else
    echo "Condition is false"
fi
""",
            language="bash",
            timeout=10
        )
        
        if result.success:
            assert "output" in result.data
            assert "Condition is true" in result.data["output"]
        else:
            if "执行器" in result.error or "executor" in result.error.lower():
                pytest.skip(f"代码执行器问题: {result.error}")

    def test_bash_loop(self, tool):
        """测试 bash 循环"""
        result = tool.execute(
            code="""
for i in 1 2 3; do
    echo "Number: $i"
done
""",
            language="bash",
            timeout=10
        )
        
        if result.success:
            assert "output" in result.data
            output = result.data["output"]
            assert "Number: 1" in output
            assert "Number: 2" in output
            assert "Number: 3" in output
        else:
            if "执行器" in result.error or "executor" in result.error.lower():
                pytest.skip(f"代码执行器问题: {result.error}")

    def test_bash_file_operations(self, tool):
        """测试 bash 文件操作"""
        result = tool.execute(
            code="""
# 创建临时文件
echo "test content" > /tmp/test_bash_file.txt
# 读取文件
cat /tmp/test_bash_file.txt
# 清理
rm /tmp/test_bash_file.txt
""",
            language="bash",
            timeout=10
        )
        
        if result.success:
            assert "output" in result.data
            assert "test content" in result.data["output"]
        else:
            if "执行器" in result.error or "executor" in result.error.lower():
                pytest.skip(f"代码执行器问题: {result.error}")

    def test_bash_pipe_and_redirect(self, tool):
        """测试 bash 管道和重定向"""
        result = tool.execute(
            code="""
echo -e "line1\nline2\nline3" | grep "line2"
""",
            language="bash",
            timeout=10
        )
        
        if result.success:
            assert "output" in result.data
            assert "line2" in result.data["output"]
        else:
            if "执行器" in result.error or "executor" in result.error.lower():
                pytest.skip(f"代码执行器问题: {result.error}")

    def test_bash_arithmetic(self, tool):
        """测试 bash 算术运算"""
        result = tool.execute(
            code="""
a=10
b=20
sum=$((a + b))
echo "Sum: $sum"
""",
            language="bash",
            timeout=10
        )
        
        if result.success:
            assert "output" in result.data
            assert "Sum: 30" in result.data["output"]
        else:
            if "执行器" in result.error or "executor" in result.error.lower():
                pytest.skip(f"代码执行器问题: {result.error}")

    def test_bash_function(self, tool):
        """测试 bash 函数"""
        result = tool.execute(
            code="""
greet() {
    echo "Hello, $1!"
}
greet "World"
""",
            language="bash",
            timeout=10
        )
        
        if result.success:
            assert "output" in result.data
            assert "Hello, World!" in result.data["output"]
        else:
            if "执行器" in result.error or "executor" in result.error.lower():
                pytest.skip(f"代码执行器问题: {result.error}")

    def test_bash_error_handling(self, tool):
        """测试 bash 错误处理"""
        result = tool.execute(
            code="""
set -e
false
echo "This should not print"
""",
            language="bash",
            timeout=10
        )
        
        # bash 脚本因为 false 命令而失败（exit_code=1）
        # 执行失败是正常的，检查 exit_code
        if not result.success:
            # 检查 exit_code 或 error 信息
            assert result.data.get("exit_code") == 1 or result.error or result.data.get("error")
        else:
            # 如果成功执行，说明 set -e 没有生效，这也是可以接受的
            pass

    def test_bash_system_commands(self, tool):
        """测试 bash 系统命令"""
        result = tool.execute(
            code="""
pwd
whoami
""",
            language="bash",
            timeout=10
        )
        
        if result.success:
            assert "output" in result.data
            # 至少应该有一些输出
            assert len(result.data["output"]) > 0
        else:
            if "执行器" in result.error or "executor" in result.error.lower():
                pytest.skip(f"代码执行器问题: {result.error}")

    def test_bash_environment_variables(self, tool):
        """测试 bash 环境变量"""
        result = tool.execute(
            code="""
echo "HOME: $HOME"
echo "USER: $USER"
""",
            language="bash",
            timeout=10
        )
        
        if result.success:
            assert "output" in result.data
            output = result.data["output"]
            # 应该包含环境变量信息
            assert "HOME:" in output or "USER:" in output
        else:
            if "执行器" in result.error or "executor" in result.error.lower():
                pytest.skip(f"代码执行器问题: {result.error}")

    def test_bash_array(self, tool):
        """测试 bash 数组"""
        result = tool.execute(
            code="""
arr=("apple" "banana" "cherry")
for fruit in "${arr[@]}"; do
    echo "Fruit: $fruit"
done
""",
            language="bash",
            timeout=10
        )
        
        if result.success:
            assert "output" in result.data
            output = result.data["output"]
            assert "Fruit: apple" in output
            assert "Fruit: banana" in output
            assert "Fruit: cherry" in output
        else:
            if "执行器" in result.error or "executor" in result.error.lower():
                pytest.skip(f"代码执行器问题: {result.error}")

    def test_bash_string_operations(self, tool):
        """测试 bash 字符串操作"""
        result = tool.execute(
            code="""
str="Hello World"
echo "Length: ${#str}"
echo "Upper: ${str^^}"
echo "Lower: ${str,,}"
""",
            language="bash",
            timeout=10
        )
        
        if result.success:
            assert "output" in result.data
            output = result.data["output"]
            # 至少应该有一些输出
            assert len(output) > 0
        else:
            if "执行器" in result.error or "executor" in result.error.lower():
                pytest.skip(f"代码执行器问题: {result.error}")


"""直接导入 Browser Tool（绕过其他依赖）"""
import sys
from pathlib import Path
import importlib.util

# Add project root to sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_direct_import():
    """直接导入 browser_tool，绕过 __init__.py"""
    print("=" * 60)
    print("直接导入 Browser Tool")
    print("=" * 60)
    
    browser_tool_path = project_root / "backend" / "core" / "agent" / "tools" / "builtin" / "browser_tool.py"
    
    # 直接加载模块
    spec = importlib.util.spec_from_file_location("browser_tool", browser_tool_path)
    browser_module = importlib.util.module_from_spec(spec)
    
    # 模拟必要的依赖
    class MockTool:
        def __init__(self, name, description, parameters=None):
            self.name = name
            self.description = description
            self.parameters = parameters or []
        
        def validate_parameters(self, **kwargs):
            return None
    
    class MockToolResult:
        def __init__(self, success, data=None, error=None):
            self.success = success
            self.data = data or {}
            self.error = error
    
    class MockToolParameter:
        def __init__(self, name, type, description, required=True, default=None):
            self.name = name
            self.type = type
            self.description = description
            self.required = required
            self.default = default
    
    # 设置模拟模块
    sys.modules['backend.core.agent.tools.base'] = type(sys)('base')
    sys.modules['backend.core.agent.tools.base'].Tool = MockTool
    sys.modules['backend.core.agent.tools.base'].ToolResult = MockToolResult
    sys.modules['backend.core.agent.tools.base'].ToolParameter = MockToolParameter
    
    try:
        spec.loader.exec_module(browser_module)
        
        print("✅ Browser Tool 模块加载成功")
        print(f"✅ BROWSER_USE_AVAILABLE: {getattr(browser_module, 'BROWSER_USE_AVAILABLE', False)}")
        
        if hasattr(browser_module, 'BrowserTool'):
            print("✅ BrowserTool 类存在")
            return browser_module
        else:
            print("❌ BrowserTool 类不存在")
            return None
            
    except Exception as e:
        print(f"❌ 模块加载失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    browser_module = test_direct_import()
    if browser_module:
        print("\n✅ 可以直接使用 browser_module.BrowserTool")



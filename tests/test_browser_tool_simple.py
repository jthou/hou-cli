"""Browser Tool 简单测试（不依赖完整导入）"""
import sys
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import os
import importlib.util


def test_browser_tool_direct():
    """直接测试 browser_tool 模块（避免导入依赖）"""
    print("=" * 60)
    print("Browser Tool 直接测试")
    print("=" * 60)
    
    # 直接加载 browser_tool 模块
    browser_tool_path = project_root / "backend" / "core" / "agent" / "tools" / "builtin" / "browser_tool.py"
    
    spec = importlib.util.spec_from_file_location("browser_tool", browser_tool_path)
    browser_module = importlib.util.module_from_spec(spec)
    
    # 模拟必要的依赖
    sys.modules['backend.core.agent.tools.base'] = type(sys)('base')
    sys.modules['backend.core.agent.tools.base'].Tool = type('Tool', (), {})
    sys.modules['backend.core.agent.tools.base'].ToolResult = type('ToolResult', (), {})
    sys.modules['backend.core.agent.tools.base'].ToolParameter = type('ToolParameter', (), {})
    
    try:
        spec.loader.exec_module(browser_module)
        
        # 测试 BROWSER_USE_AVAILABLE
        has_browser_use = getattr(browser_module, 'BROWSER_USE_AVAILABLE', False)
        print(f"✅ browser-use 可用: {has_browser_use}")
        
        # 测试工具类
        if hasattr(browser_module, 'BrowserTool'):
            print("✅ BrowserTool 类存在")
            
            # 测试初始化（不实际创建，避免依赖问题）
            print("✅ 模块加载成功")
        else:
            print("⚠️  BrowserTool 类不存在")
            
    except Exception as e:
        print(f"⚠️  模块加载失败: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print()


def test_backend_status():
    """测试后端状态"""
    print("=" * 60)
    print("后端状态检查")
    print("=" * 60)
    
    try:
        from shared.platform_utils import load_port
        import httpx
        
        port = load_port()
        print(f"✅ 后端端口: {port}")
        
        # 健康检查
        try:
            response = httpx.get(f'http://127.0.0.1:{port}/health', timeout=2.0)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ 后端健康检查通过: {data}")
            else:
                print(f"⚠️  后端健康检查失败: {response.status_code}")
        except Exception as e:
            print(f"⚠️  无法连接到后端: {str(e)}")
            
    except Exception as e:
        print(f"⚠️  无法检查后端状态: {str(e)}")
    
    print()


def test_logs():
    """检查日志"""
    print("=" * 60)
    print("日志分析")
    print("=" * 60)
    
    try:
        from shared.platform_utils import get_app_data_dir
        
        log_dir = get_app_data_dir() / 'logs'
        log_file = log_dir / 'backend.log'
        
        if log_file.exists():
            print(f"✅ 日志文件存在: {log_file}")
            print(f"✅ 日志文件大小: {log_file.stat().st_size / 1024:.2f} KB")
            
            # 统计
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                error_count = sum(1 for line in lines if 'ERROR' in line)
                warning_count = sum(1 for line in lines if 'WARNING' in line)
                info_count = sum(1 for line in lines if 'INFO' in line)
                
                print(f"📊 日志统计:")
                print(f"   总行数: {len(lines)}")
                print(f"   ERROR: {error_count}")
                print(f"   WARNING: {warning_count}")
                print(f"   INFO: {info_count}")
                
                # 最近的错误
                if error_count > 0:
                    error_lines = [line for line in lines if 'ERROR' in line]
                    print(f"\\n   最近的错误 ({len(error_lines[-3:])} 条):")
                    for line in error_lines[-3:]:
                        print(f"     {line.rstrip()[:80]}")
        else:
            print("⚠️  日志文件不存在")
            
    except Exception as e:
        print(f"⚠️  无法检查日志: {str(e)}")
    
    print()


def main():
    """运行所有测试"""
    print("\\n" + "=" * 60)
    print("Browser Tool 测试和系统状态检查")
    print("=" * 60 + "\\n")
    
    test_browser_tool_direct()
    test_backend_status()
    test_logs()
    
    print("=" * 60)
    print("测试完成")
    print("=" * 60 + "\\n")


if __name__ == "__main__":
    main()



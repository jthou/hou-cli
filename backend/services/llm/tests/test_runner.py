"""测试运行器 - 用于验证测试文件语法和逻辑"""
import sys
import os
import importlib.util

def test_imports():
    """测试所有测试文件是否可以正确导入"""
    test_files = [
        "test_deepseek.py",
        "test_turbogateway_openai.py",
        "test_turbogateway_anthropic.py",
        "test_turbogateway_google.py",
        "test_turbogateway_perplexity.py",
        "test_bailian.py",
    ]
    
    base_path = os.path.dirname(__file__)
    errors = []
    
    for test_file in test_files:
        file_path = os.path.join(base_path, test_file)
        if not os.path.exists(file_path):
            errors.append(f"❌ 文件不存在: {test_file}")
            continue
        
        try:
            spec = importlib.util.spec_from_file_location(
                test_file.replace(".py", ""),
                file_path
            )
            if spec is None or spec.loader is None:
                errors.append(f"❌ 无法加载: {test_file}")
                continue
            
            # 只检查语法，不实际导入（避免依赖问题）
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
                compile(code, file_path, 'exec')
            
            print(f"✅ {test_file} - 语法检查通过")
        except SyntaxError as e:
            errors.append(f"❌ {test_file} - 语法错误: {e}")
        except Exception as e:
            errors.append(f"❌ {test_file} - 错误: {e}")
    
    return errors

def check_test_structure():
    """检查测试文件结构"""
    test_files = [
        "test_deepseek.py",
        "test_turbogateway_openai.py",
        "test_turbogateway_anthropic.py",
        "test_turbogateway_google.py",
        "test_turbogateway_perplexity.py",
        "test_bailian.py",
    ]
    
    base_path = os.path.dirname(__file__)
    errors = []
    
    for test_file in test_files:
        file_path = os.path.join(base_path, test_file)
        if not os.path.exists(file_path):
            continue
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查必要的组件
        checks = {
            "包含 pytest 导入": "import pytest" in content,
            "包含 LLMService 导入": "from backend.services.llm.llm_service import LLMService" in content,
            "包含测试类": "class Test" in content,
            "包含 fixture": "@pytest.fixture" in content,
            "包含非流式测试": "chat_non_streaming" in content,
            "包含流式测试": "chat_streaming" in content,
            "包含测试问题": "hello，你是什么模型？" in content,
        }
        
        failed_checks = [name for name, passed in checks.items() if not passed]
        if failed_checks:
            errors.append(f"❌ {test_file} - 缺少: {', '.join(failed_checks)}")
        else:
            print(f"✅ {test_file} - 结构检查通过")
    
    return errors

if __name__ == "__main__":
    print("=" * 60)
    print("测试文件验证")
    print("=" * 60)
    
    print("\n1. 语法检查...")
    import_errors = test_imports()
    
    print("\n2. 结构检查...")
    structure_errors = check_test_structure()
    
    print("\n" + "=" * 60)
    if import_errors or structure_errors:
        print("❌ 发现问题:")
        for error in import_errors + structure_errors:
            print(f"  {error}")
        sys.exit(1)
    else:
        print("✅ 所有测试文件验证通过！")
        print("\n注意：")
        print("  - 这些测试需要相应的 API Key 环境变量")
        print("  - 如果 API Key 未设置，测试会自动跳过")
        print("  - 运行测试: pytest backend/services/llm/tests/")
        sys.exit(0)


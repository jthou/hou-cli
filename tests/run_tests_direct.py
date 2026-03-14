#!/usr/bin/env python3
"""直接运行测试并监控测试过程"""
import sys
import os
import traceback
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from shared.load_env import load_env
load_env(project_root)

# 设置环境变量
os.environ.setdefault("ENABLE_PLANNING", "true")
os.environ.setdefault("PLANNING_COMPLEXITY_THRESHOLD", "0.2")
os.environ.setdefault("PLANNING_MIN_TASK_LENGTH", "10")
os.environ.setdefault("DEEPSEEK_API_KEY", "test_key_for_testing")

def run_test_module(module_name, test_class=None, test_method=None):
    """运行测试模块"""
    print(f"\n{'='*60}")
    print(f"运行测试: {module_name}")
    if test_class:
        print(f"  测试类: {test_class}")
    if test_method:
        print(f"  测试方法: {test_method}")
    print(f"{'='*60}\n")
    
    try:
        # 动态导入测试模块
        module = __import__(module_name, fromlist=[''])
        
        if test_class and test_method:
            # 运行特定测试方法
            test_class_obj = getattr(module, test_class)
            test_instance = test_class_obj()
            test_method_obj = getattr(test_instance, test_method)
            test_method_obj()
            print(f"✅ {test_class}.{test_method} 通过")
        elif test_class:
            # 运行测试类的所有方法
            test_class_obj = getattr(module, test_class)
            test_instance = test_class_obj()
            methods = [m for m in dir(test_instance) if m.startswith('test_')]
            for method in methods:
                try:
                    print(f"  运行 {method}...", end=" ")
                    getattr(test_instance, method)()
                    print("✅")
                except Exception as e:
                    print(f"❌ 失败: {str(e)}")
                    traceback.print_exc()
        else:
            # 运行模块中的所有测试类
            classes = [c for c in dir(module) if c.startswith('Test')]
            for cls_name in classes:
                print(f"\n  测试类: {cls_name}")
                test_class_obj = getattr(module, cls_name)
                test_instance = test_class_obj()
                methods = [m for m in dir(test_instance) if m.startswith('test_')]
                for method in methods:
                    try:
                        print(f"    运行 {method}...", end=" ")
                        getattr(test_instance, method)()
                        print("✅")
                    except Exception as e:
                        print(f"❌ 失败: {str(e)}")
                        traceback.print_exc()
        
        return True
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        traceback.print_exc()
        return False

def main():
    """主函数"""
    print("="*60)
    print("规划功能和任务管理功能集成测试")
    print("="*60)
    
    # 测试列表
    tests = [
        {
            "module": "backend.core.agent.tests.test_task_manager_integration",
            "class": "TestTaskManagerIntegration",
            "description": "任务管理器集成测试"
        },
    ]
    
    results = []
    for test in tests:
        print(f"\n📋 {test['description']}")
        success = run_test_module(
            test["module"],
            test.get("class"),
            test.get("method")
        )
        results.append((test['description'], success))
    
    # 总结
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)
    passed = sum(1 for _, success in results if success)
    total = len(results)
    print(f"总计: {total} 个测试套件")
    print(f"通过: {passed} 个")
    print(f"失败: {total - passed} 个")
    
    for desc, success in results:
        status = "✅" if success else "❌"
        print(f"  {status} {desc}")
    
    return 0 if passed == total else 1

if __name__ == "__main__":
    sys.exit(main())


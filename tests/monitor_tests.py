#!/usr/bin/env python3
"""测试监控脚本 - 运行测试并显示详细进度"""
import sys
import os
import time
import subprocess
from pathlib import Path
from datetime import datetime

def run_test_with_monitoring(test_file, description):
    """运行测试并监控过程"""
    print(f"\n{'='*70}")
    print(f"📋 {description}")
    print(f"   文件: {test_file}")
    print(f"{'='*70}\n")
    
    start_time = time.time()
    
    # 运行测试
    try:
        result = subprocess.run(
            [sys.executable, test_file],
            capture_output=True,
            text=True,
            timeout=300  # 5分钟超时
        )
        
        elapsed = time.time() - start_time
        
        # 显示输出
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            # 过滤掉警告信息
            stderr_lines = [
                line for line in result.stderr.split('\n')
                if line and not any(
                    skip in line for skip in [
                        'PydanticDeprecatedSince20',
                        'INFO',
                        'DEBUG',
                        'WARNING'
                    ]
                )
            ]
            if stderr_lines:
                print("错误输出:")
                print('\n'.join(stderr_lines))
        
        # 显示结果
        print(f"\n{'─'*70}")
        if result.returncode == 0:
            print(f"✅ 测试通过 (耗时: {elapsed:.2f}秒)")
        else:
            print(f"❌ 测试失败 (退出码: {result.returncode}, 耗时: {elapsed:.2f}秒)")
        print(f"{'─'*70}\n")
        
        return result.returncode == 0, elapsed
    except subprocess.TimeoutExpired:
        print(f"⏱️  测试超时 (超过5分钟)")
        return False, time.time() - start_time
    except Exception as e:
        print(f"❌ 运行测试时出错: {str(e)}")
        return False, time.time() - start_time

def main():
    """主函数"""
    print("="*70)
    print("规划功能和任务管理功能集成测试监控")
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    
    # 设置环境变量
    os.environ.setdefault("ENABLE_PLANNING", "true")
    os.environ.setdefault("PLANNING_COMPLEXITY_THRESHOLD", "0.2")
    os.environ.setdefault("PLANNING_MIN_TASK_LENGTH", "10")
    os.environ.setdefault("DEEPSEEK_API_KEY", "test_key_for_testing")
    
    # 测试列表
    tests = [
        {
            "file": "tests/test_planning_integration_simple.py",
            "description": "简单集成测试（不依赖pytest）"
        },
    ]
    
    results = []
    total_start = time.time()
    
    for test in tests:
        test_file = Path(test["file"])
        if not test_file.exists():
            print(f"⚠️  测试文件不存在: {test_file}")
            results.append((test["description"], False, 0))
            continue
        
        success, elapsed = run_test_with_monitoring(
            str(test_file),
            test["description"]
        )
        results.append((test["description"], success, elapsed))
    
    # 总结
    total_elapsed = time.time() - total_start
    passed = sum(1 for _, success, _ in results if success)
    total = len(results)
    
    print("\n" + "="*70)
    print("测试总结")
    print("="*70)
    print(f"总计: {total} 个测试套件")
    print(f"通过: {passed} 个")
    print(f"失败: {total - passed} 个")
    print(f"总耗时: {total_elapsed:.2f}秒")
    print(f"结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n详细结果:")
    print("-"*70)
    
    for desc, success, elapsed in results:
        status = "✅" if success else "❌"
        print(f"  {status} {desc:50s} ({elapsed:.2f}秒)")
    
    print("="*70)
    
    return 0 if passed == total else 1

if __name__ == "__main__":
    sys.exit(main())


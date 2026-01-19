#!/usr/bin/env python3
"""模型配置验证脚本

使用方法：
    python scripts/validate_model_config.py

功能：
    1. 验证 .env 文件中的模型配置
    2. 测试所有配置的模型 API Key 是否可用
    3. 生成验证报告
"""
import sys
import os
import asyncio
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.core.agent.utils.model_config_validator import ModelConfigValidator


async def main():
    """主函数"""
    print("="*60)
    print("模型配置验证工具")
    print("="*60)
    print()
    
    validator = ModelConfigValidator()
    
    # 1. 验证配置
    print("步骤 1: 验证模型配置...")
    print("-" * 60)
    validation_results = validator.validate_all_configs()
    validator.print_validation_report(validation_results)
    
    # 检查是否有无效配置
    invalid_configs = [k for k, v in validation_results.items() if not v.get('valid', False)]
    if invalid_configs:
        print(f"\n⚠️  警告: 以下模型配置无效: {', '.join(invalid_configs)}")
        print("请检查 .env 文件中的配置")
        return 1
    
    # 2. 测试 API Key
    print("\n步骤 2: 测试 API Key 可用性...")
    print("-" * 60)
    print("注意: 这将进行实际的 API 调用，可能会产生费用")
    
    try:
        test_results = await validator.test_api_keys()
        validator.print_test_report(test_results)
        
        # 检查是否有测试失败
        failed_tests = [k for k, v in test_results.items() if not v.get('test_successful', False)]
        if failed_tests:
            print(f"\n❌ 以下模型 API Key 测试失败: {', '.join(failed_tests)}")
            return 1
        else:
            print("\n✅ 所有模型配置验证通过！")
            return 0
            
    except KeyboardInterrupt:
        print("\n\n⚠️  测试被用户中断")
        return 1
    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)


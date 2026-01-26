#!/usr/bin/env python3
"""测试 Claude 模型配置"""
import sys
import os
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.services.llm.model_config import get_model_config_manager

# 测试 Claude 模型配置
test_models = [
    'claude-opus-4-5-20251101',
    'claude-sonnet-4-5-20250929',
    'claude-3-5-haiku-20241022'
]

config_manager = get_model_config_manager()

print('Claude 模型配置测试:')
print('=' * 60)

for model in test_models:
    try:
        config = config_manager.get_model_config(model)
        print(f'\n模型: {model}')
        print(f'  提供商: {config.provider}')
        print(f'  API Key 环境变量: {config.api_key_env}')
        print(f'  Base URL: {config.default_base_url}')
        
        # 检查 API Key 是否设置（不实际获取，避免错误）
        api_key = os.getenv(config.api_key_env)
        if api_key:
            print(f'  ✅ API Key 已设置（长度: {len(api_key)}）')
        else:
            print(f'  ⚠️  API Key 未设置（需要设置 {config.api_key_env}）')
    except Exception as e:
        print(f'\n模型: {model}')
        print(f'  ❌ 配置错误: {e}')

print('\n' + '=' * 60)
print('测试完成！')


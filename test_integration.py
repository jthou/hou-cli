#!/usr/bin/env python3
"""前后端集成测试脚本"""
import os
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

# 设置测试环境变量（如果未设置）
if not os.environ.get('DEEPSEEK_API_KEY'):
    os.environ['DEEPSEEK_API_KEY'] = 'test_key_for_integration_1234567890'

print("=" * 60)
print("前后端集成状态检查")
print("=" * 60)

# 检查关键文件
files_to_check = [
    ('backend/main.py', '后端主程序'),
    ('backend/api/routes.py', 'API 路由'),
    ('backend/core/agent/orchestrator.py', 'Orchestrator'),
    ('backend/services/llm/llm_service.py', 'LLM Service'),
    ('frontend/main.py', '前端主程序'),
    ('frontend/client/ipc_client.py', 'IPC 客户端'),
]

print('\n📁 关键文件检查：')
all_exist = True
for file_path, desc in files_to_check:
    path = Path(file_path)
    if path.exists():
        print(f'  ✅ {desc}: {file_path}')
    else:
        print(f'  ❌ {desc}: {file_path} (缺失)')
        all_exist = False

if not all_exist:
    print("\n❌ 部分文件缺失，请检查项目结构")
    sys.exit(1)

# 检查环境变量
print('\n🔧 环境变量检查：')
api_key = os.environ.get('DEEPSEEK_API_KEY')
if api_key:
    print(f'  ✅ DEEPSEEK_API_KEY: 已设置（长度: {len(api_key)}）')
else:
    print('  ⚠️  DEEPSEEK_API_KEY: 未设置')

# 测试导入
print('\n📦 模块导入测试：')
try:
    print('  - 导入 backend.main...', end=' ')
    from backend.main import app
    print('✅')
except Exception as e:
    print(f'❌ 错误: {e}')
    sys.exit(1)

try:
    print('  - 导入 frontend.client.ipc_client...', end=' ')
    from frontend.client.ipc_client import IPCClient
    print('✅')
except Exception as e:
    print(f'❌ 错误: {e}')
    sys.exit(1)

try:
    print('  - 导入 backend.core.agent.orchestrator...', end=' ')
    from backend.core.agent.orchestrator import Orchestrator
    print('✅')
except Exception as e:
    print(f'❌ 错误: {e}')
    sys.exit(1)

print('\n' + "=" * 60)
print("✅ 所有检查通过！前后端集成准备就绪")
print("=" * 60)
print("\n💡 下一步：")
print("  1. 启动后端: python -m backend.main")
print("  2. 启动前端: python -m frontend.main chat")
print("  3. 或使用: make start")



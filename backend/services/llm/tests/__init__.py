"""LLM 服务模块测试"""
import os
from pathlib import Path
from dotenv import load_dotenv

# 加载 .env 文件（在导入测试模块之前）
# 优先级：1. 项目根目录 2. 当前目录
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
env_paths = [
    PROJECT_ROOT / '.env',  # 项目根目录
    Path.cwd() / '.env',  # 当前目录
]

env_loaded = False
for env_path in env_paths:
    if env_path.exists():
        load_dotenv(env_path, override=True)
        env_loaded = True
        print(f"✅ 已加载 .env 文件: {env_path}")
        break

if not env_loaded:
    # 如果都没找到，尝试从当前目录加载（兼容旧行为）
    load_dotenv()
    print("⚠️  未找到 .env 文件，使用系统环境变量")




"""pytest 配置文件 - 自动加载 .env 文件"""
import os
from pathlib import Path
from dotenv import load_dotenv

# 加载 .env 文件（在所有测试之前）
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
        break

if not env_loaded:
    # 如果都没找到，尝试从当前目录加载（兼容旧行为）
    load_dotenv()


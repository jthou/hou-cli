"""项目根 conftest：统一加载 .env，所有测试共享"""
from pathlib import Path

# 项目根（conftest.py 在项目根）
_ROOT = Path(__file__).resolve().parent
import sys
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from shared.load_env import load_env
load_env(_ROOT)

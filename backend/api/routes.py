"""主路由文件 - 聚合所有功能模块的路由"""
from pathlib import Path
from dotenv import load_dotenv
from fastapi import APIRouter

# 加载 .env 文件（在导入其他模块之前）
env_path = Path(__file__).parent.parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path)
else:
    # 尝试从当前目录加载
    load_dotenv()

# 导入各个功能模块的路由
from backend.api.chat_routes import router as chat_router
from backend.api.session_routes import router as session_router
from backend.api.search_routes import router as search_router
from backend.api.mediawiki_routes import router as mediawiki_router
from backend.api.tool_routes import router as tool_router
from backend.api.heartbeat_routes import router as heartbeat_router
from backend.api.storage_routes import router as storage_router
from backend.api.task_routes import router as task_router
from backend.api.test_routes import router as test_router

# 创建主路由器
router = APIRouter()

# 注册所有子路由
router.include_router(chat_router, tags=["chat"])
router.include_router(session_router, tags=["sessions"])
router.include_router(search_router, tags=["search"])
router.include_router(mediawiki_router, tags=["mediawiki"])
router.include_router(tool_router, tags=["tools"])
router.include_router(heartbeat_router, tags=["monitoring"])
router.include_router(storage_router, tags=["storage"])
router.include_router(task_router, tags=["tasks"])
router.include_router(test_router, tags=["tests"])

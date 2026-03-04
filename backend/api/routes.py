"""主路由文件 - 聚合所有功能模块的路由"""
from pathlib import Path

from dotenv import load_dotenv
from fastapi import APIRouter

# 加载 .env 文件（在导入其他模块之前）
env_path = Path(__file__).parent.parent.parent / ".env"
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
from backend.api.wechat_mp_routes import router as wechat_mp_router
from backend.api.latex_routes import router as latex_router
from backend.api.tool_routes import router as tool_router
from backend.api.kanban_routes import router as kanban_router
from backend.api.heartbeat_routes import router as heartbeat_router
from backend.api.storage_routes import router as storage_router
from backend.api.pdf_routes import router as pdf_router
from backend.api.web_reader_routes import router as web_reader_router
from backend.api.llm_audit_routes import router as llm_audit_router
from backend.api.model_config_routes import router as model_config_router
from backend.api.task_routes import router as task_router

# 导入任务队列路由（添加错误处理）
try:
    from backend.api.task_queue_routes import router as task_queue_router
except Exception as e:
    import logging
    logger = logging.getLogger(__name__)
    logger.warning(f"无法导入 task_queue_routes: {e}", exc_info=True)
    # 创建一个空的路由器作为占位符，避免后续代码出错
    from fastapi import APIRouter
    task_queue_router = APIRouter()

from backend.api.test_routes import router as test_router

# 创建主路由器
router = APIRouter()

# 注册所有子路由
router.include_router(chat_router, tags=["chat"])
router.include_router(session_router, tags=["sessions"])
router.include_router(search_router, tags=["search"])
router.include_router(mediawiki_router, tags=["mediawiki"])
router.include_router(wechat_mp_router, tags=["wechat-mp"])
router.include_router(latex_router, tags=["latex"])
router.include_router(tool_router, tags=["tools"])
router.include_router(heartbeat_router, tags=["monitoring"])
router.include_router(storage_router, tags=["storage"])
router.include_router(llm_audit_router, tags=["llm-audit"])
router.include_router(model_config_router, tags=["model-config"])
router.include_router(task_router, tags=["tasks"])
router.include_router(kanban_router, tags=["kanban"])
router.include_router(pdf_router, tags=["pdf"])
router.include_router(web_reader_router)

# 注册系统监控路由
try:
    from backend.api.system_monitor_routes import router as system_monitor_router
    router.include_router(system_monitor_router)
except ImportError as e:
    logger.warning(f"系统监控路由导入失败: {e}")

# 注册任务队列路由（添加错误处理）
try:
    router.include_router(task_queue_router, tags=["task-queue"])
except Exception as e:
    import logging
    logger = logging.getLogger(__name__)
    logger.error(f"注册 task_queue_router 失败: {e}", exc_info=True)

router.include_router(test_router, tags=["tests"])

"""工具相关路由"""
from fastapi import APIRouter
from backend.core.agent.orchestrator import Orchestrator
from shared.debug_utils import debug_log

router = APIRouter()

# 延迟创建 orchestrator
_orchestrator = None

def get_orchestrator():
    """获取 Orchestrator 实例（单例模式）"""
    global _orchestrator
    if _orchestrator is None:
        try:
            _orchestrator = Orchestrator()
        except Exception as e:
            debug_log(
                f"Failed to initialize Orchestrator: {str(e)}",
                level="error"
            )
            raise
    return _orchestrator

@router.get("/tools/list")
async def list_tools():
    """获取可用工具列表"""
    try:
        orchestrator = get_orchestrator()
        # 获取工具对象（不是名称列表）
        tool_registry = orchestrator.tool_registry
        tools = tool_registry._tools.values()  # 直接访问工具字典
        
        tools_info = []
        for tool in tools:
            tool_name = tool.name if hasattr(tool, 'name') else str(tool)
            tool_desc = tool.description if hasattr(tool, 'description') else ""
            
            # 如果描述为空，尝试从工具类获取
            if not tool_desc and hasattr(tool, '__class__'):
                # 尝试获取类的文档字符串
                if tool.__class__.__doc__:
                    tool_desc = tool.__class__.__doc__.strip().split('\n')[0]
            
            # 如果还是没有描述，使用默认描述
            if not tool_desc:
                tool_desc = f"{tool_name} 工具"
            
            # 只取第一行描述（去掉换行和多余空格）
            tool_desc = tool_desc.split('\n')[0].strip()
            
            tool_info = {
                "name": tool_name,
                "description": tool_desc
            }
            tools_info.append(tool_info)
        
        return {
            "success": True,
            "tools": tools_info,
            "count": len(tools_info)
        }
    except Exception as e:
        debug_log(
            f"获取工具列表失败: {str(e)}",
            level="error"
        )
        return {
            "success": False,
            "error": str(e)
        }


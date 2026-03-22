"""持久化浏览器工具 - 支持长时间运行的浏览器会话"""
import logging
import asyncio
from typing import Dict, Any
from queue import Queue

from backend.core.agent.tools.base import Tool, ToolResult, ToolParameter
from backend.services.llm.llm_service import LLMService
from backend.core.agent.tools.builtin.browser_llm_defaults import browser_default_chat_model


logger = logging.getLogger(__name__)


class PersistentBrowserTool(Tool):
    """持久化浏览器工具 - 保持浏览器会话长时间运行"""
    
    def __init__(self):
        parameters = [
            ToolParameter(
                name="action",
                type="string",
                description="要执行的操作，如: 'start_session', 'navigate', 'control_video', 'keep_alive', 'stop_session'",  # noqa: E501
                required=True
            ),
            ToolParameter(
                name="url",
                type="string",
                description="目标URL（对于navigate和control_video操作）",
                required=False
            ),
            ToolParameter(
                name="operation",
                type="string",
                description="视频控制操作，如: 'play', 'pause', 'seek', 'change_speed'",  # noqa: E501
                required=False
            ),
            ToolParameter(
                name="value",
                type="string",
                description="操作值（如进度位置、速度等）",
                required=False
            ),
            ToolParameter(
                name="duration",
                type="number",
                description="保持会话的时间（秒）",
                required=False
            )
        ]
        
        super().__init__(
            name="persistent_browser_control",
            description="持久化浏览器控制工具，支持长时间运行的浏览器会话",
            parameters=parameters
        )
        
        self.llm_service = LLMService()
        self.agent = None  # 保持agent实例
        self.browser_session = None  # 保持浏览器会话
        self.session_thread = None
        self.stop_event = None
        self.command_queue = Queue()  # noqa: F821
        self.result_queue = Queue()  # noqa: F821
    
    def execute(self, **kwargs) -> ToolResult:
        """执行浏览器操作（同步）"""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        async def run_async():
            return await self._execute_async(**kwargs)

        return loop.run_until_complete(run_async())

    async def _execute_async(self, **kwargs) -> ToolResult:
        """执行浏览器操作（异步）"""
        action = kwargs.get("action")
        
        try:
            if action == "start_session":
                return await self._start_session(kwargs)
            elif action == "navigate":
                return await self._navigate(kwargs)
            elif action == "control_video":
                return await self._control_video(kwargs)
            elif action == "keep_alive":
                return await self._keep_alive(kwargs)
            elif action == "stop_session":
                return await self._stop_session(kwargs)
            else:
                return ToolResult(
                    success=False,
                    error=f"不支持的操作: {action}"
                )
        except Exception as e:
            logger.error(f"持久化浏览器操作失败: {str(e)}", exc_info=True)
            return ToolResult(
                success=False,
                error=f"持久化浏览器操作失败: {str(e)}"
            )
    
    async def _start_session(self, kwargs: Dict[str, Any]) -> ToolResult:
        """启动持久化浏览器会话"""
        try:
            # 获取适配后的LLM
            llm = self.llm_service.get_browser_use_llm_with_adaptation(
                model=browser_default_chat_model(),
                disable_response_schema=True
            )
            
            # 创建agent但不立即运行，以保持会话
            from browser_use import Agent  # noqa: F811
            self.agent = Agent(
                task='保持浏览器会话运行',
                llm=llm,
                max_actions=1,
                use_vision=False
            )
            
            # 获取浏览器会话
            self.browser_session = self.agent.browser_session
            
            return ToolResult(
                success=True,
                data={
                    "message": "持久化浏览器会话已启动",
                    "session_id": id(self.browser_session),
                    "action": "start_session",
                    "browser_session_type": str(type(self.browser_session))
                }
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"启动浏览器会话失败: {str(e)}"
            )
    
    async def _navigate(self, kwargs: Dict[str, Any]) -> ToolResult:
        """导航到指定URL"""
        url = kwargs.get("url")
        if not url:
            return ToolResult(success=False, error="缺少URL参数")
        
        try:
            if not self.browser_session:
                return ToolResult(success=False, error="浏览器会话未启动")
            
            # 使用LLM和agent来导航
            llm = self.llm_service.get_browser_use_llm_with_adaptation(
                model=browser_default_chat_model(),
                disable_response_schema=True
            )
            
            from browser_use import Agent  # noqa: F811
            temp_agent = Agent(
                task=f'导航到 {url}',
                llm=llm,
                max_actions=1,
                use_vision=False
            )
            
            result = await temp_agent.run()
            
            return ToolResult(
                success=True,
                data={
                    "message": f"成功导航到 {url}",
                    "url": url,
                    "action": "navigate",
                    "result": str(result)[:200] + "..."
                }
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"导航失败: {str(e)}"
            )
    
    async def _control_video(self, kwargs: Dict[str, Any]) -> ToolResult:
        """控制视频播放"""
        operation = kwargs.get("operation")
        value = kwargs.get("value")
        
        if not operation:
            return ToolResult(success=False, error="缺少操作参数")
        
        try:
            if not self.browser_session:
                return ToolResult(success=False, error="浏览器会话未启动")
            
            # 使用LLM和agent来控制视频
            llm = self.llm_service.get_browser_use_llm_with_adaptation(
                model=browser_default_chat_model(),
                disable_response_schema=True
            )

            # 根据操作类型创建相应的任务
            if operation == "seek":
                task_desc = f"将视频进度跳转到 {float(value)*100}% 位置"  # noqa: E501
            elif operation == "change_speed":
                task_desc = f"将视频播放速度设置为 {value}x"  # noqa: E501
            elif operation == "play":
                task_desc = "播放视频"
            elif operation == "pause":
                task_desc = "暂停视频"
            else:
                return ToolResult(success=False, error=f"不支持的视频操作: {operation}")  # noqa: E501

            from browser_use import Agent  # noqa: F811
            temp_agent = Agent(
                task=task_desc,
                llm=llm,
                max_actions=2,
                use_vision=False
            )

            result = await temp_agent.run()

            return ToolResult(
                success=True,
                data={
                    "message": f"成功执行视频操作: {task_desc}",
                    "operation": operation,
                    "value": value,
                    "action": "control_video",
                    "result": str(result)[:200] + "..."
                }
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"视频控制失败: {str(e)}"
            )
    
    async def _keep_alive(self, kwargs: Dict[str, Any]) -> ToolResult:
        """保持会话活跃"""
        duration = kwargs.get("duration", 30)  # 默认保持30秒
        
        try:
            # 等待指定时间
            await asyncio.sleep(duration)
            
            return ToolResult(
                success=True,
                data={
                    "message": f"会话保持活跃 {duration} 秒",
                    "duration": duration,
                    "action": "keep_alive"
                }
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"保持会话活跃失败: {str(e)}"
            )
    
    async def _stop_session(self, kwargs: Dict[str, Any]) -> ToolResult:
        """停止浏览器会话"""
        try:
            # 如果有活动的agent，尝试清理
            if self.agent:
                try:
                    await self.agent.close()  # 如果有close方法
                except Exception:
                    pass  # 忽略关闭错误
                self.agent = None
            
            self.browser_session = None
            
            return ToolResult(
                success=True,
                data={
                    "message": "浏览器会话已停止",
                    "action": "stop_session"
                }
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"停止浏览器会话失败: {str(e)}"
            )
    
    async def execute_video_sequence(self, url: str, seek_position: float = 0.5, playback_speed: float = 1.5, duration: int = 10) -> ToolResult:  # noqa: E501
        """执行完整的视频操作序列"""
        
        try:
            # 1. 启动会话
            start_result = await self._start_session({})
            if not start_result.success:
                return start_result
            
            # 2. 导航到视频页面
            nav_result = await self._navigate({"url": url})
            if not nav_result.success:
                return nav_result
            
            await asyncio.sleep(3)  # 等待页面加载
            
            # 3. 跳转到指定位置
            seek_result = await self._control_video({
                "operation": "seek", 
                "value": str(seek_position)
            })
            if not seek_result.success:
                return seek_result
            
            await asyncio.sleep(1)  # 等待跳转完成
            
            # 4. 更改播放速度
            speed_result = await self._control_video({
                "operation": "change_speed", 
                "value": str(playback_speed)
            })
            if not speed_result.success:
                return speed_result
            
            await asyncio.sleep(1)  # 等待速度设置完成
            
            # 5. 播放指定时长
            play_result = await self._control_video({
                "operation": "play"
            })
            if not play_result.success:
                return play_result
            
            # 保持会话活跃指定时长
            await asyncio.sleep(duration)
            
            return ToolResult(
                success=True,
                data={
                    "message": f"成功完成视频操作序列: 打开 {url}, 跳转到 {int(seek_position*100)}%, 设置速度 {playback_speed}x, 播放 {duration} 秒",  # noqa: E501
                    "url": url,
                    "seek_position": seek_position,
                    "playback_speed": playback_speed,
                    "duration": duration,
                    "actions_completed": ["start_session", "navigate", "seek", "change_speed", "play", "wait_duration"]  # noqa: E501
                }
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"视频操作序列失败: {str(e)}"
            )
"""高级浏览器操作工具 - 支持视频控制等复杂操作"""
import logging
import asyncio
from typing import Dict, Any

from backend.core.agent.tools.base import Tool, ToolResult, ToolParameter
from backend.services.llm.llm_service import LLMService
from backend.core.agent.tools.builtin.browser_llm_defaults import browser_default_chat_model
from browser_use import Agent


logger = logging.getLogger(__name__)


class AdvancedBrowserTool(Tool):
    """高级浏览器操作工具 - 支持复杂操作如视频控制"""
    
    def __init__(self):
        parameters = [
            ToolParameter(
                name="task",
                type="string",
                description="要执行的浏览器任务，如: 'play_video', 'change_speed', 'seek_position', 'close_browser'",  # noqa: E501
                required=True
            ),
            ToolParameter(
                name="url",
                type="string",
                description="视频URL地址（对于play_video任务）",
                required=False
            ),
            ToolParameter(
                name="speed",
                type="number",
                description="播放速度（对于change_speed任务）",
                required=False
            ),
            ToolParameter(
                name="position",
                type="number",
                description="进度位置（0-1之间的数值，对于seek_position任务）",
                required=False
            ),
            ToolParameter(
                name="duration",
                type="number",
                description="播放持续时间（秒，对于play_video_with_duration任务）",
                required=False
            )
        ]
        
        super().__init__(
            name="advanced_browser_control",
            description="高级浏览器控制工具，支持视频播放、速度控制、进度控制等",
            parameters=parameters
        )
        
        self.llm_service = LLMService()
        self.browser_session = None  # 保持浏览器会话
    
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
        task = kwargs.get("task")
        
        try:
            if task == "play_video":
                return await self._play_video(kwargs)
            elif task == "change_speed":
                return await self._change_playback_speed(kwargs)
            elif task == "seek_position":
                return await self._seek_video_position(kwargs)
            elif task == "close_browser":
                return await self._close_browser(kwargs)
            elif task == "play_with_controls":
                return await self._play_video_with_controls(kwargs)
            else:
                return ToolResult(
                    success=False,
                    error=f"不支持的任务类型: {task}"
                )
        except Exception as e:
            logger.error(f"高级浏览器操作失败: {str(e)}", exc_info=True)
            return ToolResult(
                success=False,
                error=f"高级浏览器操作失败: {str(e)}"
            )
    
    async def _play_video(self, kwargs: Dict[str, Any]) -> ToolResult:
        """播放视频"""
        url = kwargs.get("url")
        if not url:
            return ToolResult(success=False, error="缺少视频URL")
        
        try:
            # 获取适配后的LLM
            llm = self.llm_service.get_browser_use_llm_with_adaptation(
                model=browser_default_chat_model(),
                disable_response_schema=True
            )
            
            # 创建 agent 打开视频页面
            agent = Agent(
                task=f"打开视频页面 {url}",
                llm=llm,
                max_actions=1,
                use_vision=False
            )
            
            result = await agent.run()
            
            # 检查是否成功打开页面
            result_str = str(result)
            if 'Navigated to' in result_str or url in result_str:
                return ToolResult(
                    success=True,
                    data={
                        "message": f"成功打开视频页面: {url}",
                        "url": url,
                        "action": "open_video_page",
                        "result": result_str[:200] + "..."
                    }
                )
            else:
                return ToolResult(
                    success=False,
                    error=f"未能成功打开视频页面: {result_str[:200]}..."
                )
                
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"播放视频失败: {str(e)}"
            )
    
    async def _change_playback_speed(self, kwargs: Dict[str, Any]) -> ToolResult:  # noqa: E501
        """更改播放速度"""
        speed = kwargs.get("speed", 1.0)
        
        try:
            # 获取适配后的LLM
            llm = self.llm_service.get_browser_use_llm_with_adaptation(
                model=browser_default_chat_model(),
                disable_response_schema=True
            )
            
            # 创建 agent 控制播放速度
            agent = Agent(
                task=f"将视频播放速度设置为 {speed}x",
                llm=llm,
                max_actions=2,
                use_vision=False
            )
            
            result = await agent.run()
            
            return ToolResult(
                success=True,
                data={
                    "message": f"成功设置播放速度为 {speed}x",
                    "speed": speed,
                    "action": "change_playback_speed",
                    "result": str(result)[:200] + "..."
                }
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"更改播放速度失败: {str(e)}"
            )
    
    async def _seek_video_position(self, kwargs: Dict[str, Any]) -> ToolResult:
        """跳转到视频指定位置"""
        position = kwargs.get("position", 0.5)  # 默认跳转到中间位置
        
        try:
            # 获取适配后的LLM
            llm = self.llm_service.get_browser_use_llm_with_adaptation(
                model=browser_default_chat_model(),
                disable_response_schema=True
            )
            
            # 创建 agent 控制视频进度
            percentage = int(position * 100)
            agent = Agent(
                task=f"将视频进度跳转到 {percentage}% 位置",
                llm=llm,
                max_actions=2,
                use_vision=False
            )
            
            result = await agent.run()
            
            return ToolResult(
                success=True,
                data={
                    "message": f"成功跳转到视频 {percentage}% 位置",
                    "position": position,
                    "percentage": percentage,
                    "action": "seek_video_position",
                    "result": str(result)[:200] + "..."
                }
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"跳转视频位置失败: {str(e)}"
            )
    
    async def _close_browser(self, kwargs: Dict[str, Any]) -> ToolResult:
        """关闭浏览器"""
        try:
            # 获取适配后的LLM
            llm = self.llm_service.get_browser_use_llm_with_adaptation(
                model=browser_default_chat_model(),
                disable_response_schema=True
            )
            
            # 创建 agent 关闭浏览器
            agent = Agent(
                task="关闭浏览器",
                llm=llm,
                max_actions=1,
                use_vision=False
            )
            
            result = await agent.run()
            
            return ToolResult(
                success=True,
                data={
                    "message": "成功关闭浏览器",
                    "action": "close_browser",
                    "result": str(result)[:200] + "..."
                }
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"关闭浏览器失败: {str(e)}"
            )
    
    async def _play_video_with_controls(self, kwargs: Dict[str, Any]) -> ToolResult:  # noqa: E501
        """播放视频并执行一系列控制操作"""
        url = kwargs.get("url")
        speed = kwargs.get("speed", 1.0)
        seek_position = kwargs.get("position", 0.5)
        duration = kwargs.get("duration", 10)  # 默认播放10秒
        
        try:
            # 步骤1: 打开视频
            open_result = await self._play_video({"url": url})
            if not open_result.success:
                return open_result
            
            await asyncio.sleep(2)  # 等待页面加载
            
            # 步骤2: 跳转到指定位置
            seek_result = await self._seek_video_position({"position": seek_position})  # noqa: E501
            if not seek_result.success:
                return seek_result
            
            await asyncio.sleep(1)  # 等待跳转完成
            
            # 步骤3: 更改播放速度
            speed_result = await self._change_playback_speed({"speed": speed})
            if not speed_result.success:
                return speed_result
            
            await asyncio.sleep(duration)  # 播放指定时长
            
            # 步骤4: 关闭浏览器
            close_result = await self._close_browser({})
            if not close_result.success:
                return close_result
            
            return ToolResult(
                success=True,
                data={
                    "message": f"成功完成视频播放控制任务: 打开 {url}, 跳转到 {int(seek_position*100)}%, 设置速度 {speed}x, 播放 {duration} 秒后关闭",  # noqa: E501
                    "url": url,
                    "speed": speed,
                    "seek_position": seek_position,
                    "duration": duration,
                    "actions_completed": ["open_video", "seek_position", "change_speed", "play_duration", "close_browser"]  # noqa: E501
                }
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"视频控制任务失败: {str(e)}"
            )
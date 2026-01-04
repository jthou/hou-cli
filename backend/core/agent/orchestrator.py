"""Agent 编排器"""
import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any, AsyncIterator
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# 加载 .env 文件（在导入 LLMService 之前）
env_path = Path(__file__).parent.parent.parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path)
else:
    # 尝试从当前目录加载
    load_dotenv()

from backend.core.agent.coordinator import AgentCoordinator
from backend.core.context.manager import ContextManager as FullContextManager
from backend.core.context.models import MessageRole
from backend.core.agent.tools.registry import ToolRegistry
from backend.core.agent.tools.auth.jwt_auth import JWTAuth, JWTAuthError
from backend.core.agent.tools.builtin.weather_tool import get_weather_tool
from backend.services.llm.llm_service import LLMService
from shared.debug_utils import DebugOutput
# from backend.core.workflow.workflow_identifier import WorkflowIdentifier
# from backend.core.workflow.workflow_engine import WorkflowEngine

class Orchestrator:
    """Agent 编排器，负责任务分解和 Agent 协调"""
    
    def __init__(self):
        self.coordinator = AgentCoordinator()
        self.llm_service = LLMService()
        self.context_manager = FullContextManager()
        self.tool_registry = ToolRegistry()
        self.debug = DebugOutput()  # 调试输出
        
        # 注册天气工具（如果配置了 JWT）
        self._register_tools()
        
        # self.workflow_identifier = WorkflowIdentifier()
        # self.workflow_engine = WorkflowEngine(self)
    
    def _register_tools(self):
        """注册所有可用工具"""
        try:
            # 从环境变量读取 kid 和 sub（如果未提供）
            jwt_auth = JWTAuth.from_env()
            weather_tool = get_weather_tool(jwt_auth)
            self.tool_registry.register(weather_tool)
            self.debug.log_orchestrator_step("注册工具", {"weather_tool": "registered"})
        except JWTAuthError as e:
            # JWT 认证配置错误，记录详细错误信息
            error_msg = f"JWT authentication configuration error: {str(e)}. Weather tool will not be available."
            self.debug.log_orchestrator_step("工具注册失败", {"error": error_msg})
            logger.warning(error_msg)
        except Exception as e:
            # 其他工具注册失败，记录但不中断
            error_msg = f"Failed to register weather tool: {str(e)}. Weather tool will not be available."
            self.debug.log_orchestrator_step("工具注册失败", {"error": error_msg})
            logger.warning(error_msg)
    
    async def process(self, task: str, context: Optional[Dict] = None) -> str:
        """处理任务，支持 SOP 和动态编排"""
        # TODO: 实现流程识别和 SOP 执行
        # 暂时使用动态编排
        return await self.process_dynamic(task, context)
    
    async def process_dynamic(self, task: str, context: Optional[Dict] = None) -> str:
        """
        动态编排执行
        
        Args:
            task: 用户任务/消息
            context: 上下文信息（可选，包含 session_id）
            
        Returns:
            LLM 生成的回复
        """
        self.debug.log_orchestrator_step("开始处理任务", {"task": task[:50] + "..." if len(task) > 50 else task})
        
        # 获取会话 ID（如果提供）
        session_id = context.get("session_id") if context else None
        self.debug.log_context_operation("获取会话ID", session_id or "new", {"provided": session_id is not None})
        
        # 如果没有会话 ID，创建新会话
        if not session_id:
            session_id = self.context_manager.create_session()
            self.debug.log_context_operation("创建新会话", session_id)
        
        # 获取历史消息（不压缩，保留完整历史）
        history = self.context_manager.get_messages_for_llm(
            session_id,
            max_messages=None,  # 不限制消息数量
            max_tokens=None     # 不限制 token 数量
        )
        self.debug.log_context_operation("获取历史消息", session_id, {"count": len(history), "has_history": len(history) > 0})
        
        # 构建消息列表
        system_prompt = """你是一个智能助手，能够帮助用户解决各种问题。当用户提供历史对话记录时，请基于历史对话内容来理解和回答当前问题。

重要：当用户询问天气信息时，你必须使用 get_weather 工具来获取实时天气数据。绝对不要编造或猜测天气信息。如果工具调用失败，请明确告诉用户工具调用失败，不要生成虚假的天气信息。

当展示天气信息时，请使用清晰、美观的 Markdown 格式，并添加天气和风力图标：

**天气图标对照表：**
- ☀️ 晴天
- ⛅ 多云
- ☁️ 阴天
- 🌧️ 雨天
- ⛈️ 雷雨
- 🌨️ 雪天
- 🌫️ 雾/霾
- 🌪️ 大风/龙卷风

**风力图标对照表：**
- 🍃 微风（1-3级）
- 💨 轻风（4-5级）
- 🌬️ 和风（6-7级）
- 💨💨 强风（8-9级）
- 🌪️ 狂风（10级以上）

**格式要求：**

1. **当前天气**：使用列表或简洁的段落展示，添加天气图标
   - 例如：☀️ 晴，温度 3°C，体感温度 0°C
   - 如果提供了空气质量数据，请显示雾霾指数（AQI）和空气质量等级
     * AQI 0-50：🟢 优
     * AQI 51-100：🟡 良
     * AQI 101-150：🟠 轻度污染
     * AQI 151-200：🔴 中度污染
     * AQI 201-300：🟣 重度污染
     * AQI >300：⚫ 严重污染
   - 例如：🌫️ 空气质量：AQI 85，🟡 良，PM2.5: 45μg/m³

2. **天气预报**：使用 Markdown 表格格式，在天气和风向列中添加图标，例如：
   | 日期 | 天气 | 最高温度 | 最低温度 | 风向 | 湿度 |
   |------|------|---------|---------|------|------|
   | 1月3日 | ☀️ 晴 | 6°C | -4°C | 🍃 西北风1-3级 | 24% |
   | 1月4日 | ☀️ 晴 | 5°C | -5°C | 🍃 东风1-3级 | 29% |
   | 1月5日 | ⛅ 多云 | 4°C | -4°C | 💨 西南风4-5级 | 35% |

3. **穿衣建议**：根据温度、天气状况和风力提供穿衣指数和建议
   - 使用温度范围判断：
     * 30°C以上：🔥 炎热，建议穿轻薄透气的短袖、短裤
     * 25-30°C：☀️ 温暖，建议穿T恤、薄长裤
     * 15-25°C：😊 舒适，建议穿长袖、薄外套
     * 5-15°C：🧥 凉爽，建议穿薄外套、长裤
     * 0-5°C：🧣 较冷，建议穿厚外套、毛衣
     * 0°C以下：❄️ 寒冷，建议穿羽绒服、厚毛衣、保暖内衣
   - 根据天气状况调整：
     * 雨天：🌧️ 建议穿防水外套或带雨具
     * 雪天：🌨️ 建议穿防滑鞋、保暖衣物
     * 大风：💨 建议穿防风外套

4. **带伞建议**：
   - 🌧️ 有雨：**建议带伞**
   - ⛈️ 雷雨：**强烈建议带伞**
   - 🌨️ 雪天：**建议带伞（防雪）**
   - ☀️ 晴天：无需带伞
   - ⛅ 多云：建议携带轻便雨具（以防突发降雨）

5. **总结**：使用标题（##）和列表（-）组织信息

请确保：
- 表格对齐整齐
- 信息层次清晰
- 使用适当的 Markdown 语法（标题、列表、表格、粗体）
- 根据实际天气状况选择合适的图标
- 根据风力等级选择合适的风力图标
- 穿衣建议和带伞建议要基于实际的温度、天气状况和降水概率"""
        
        # 构建 user_prompt（包含历史上下文）
        # 过滤掉 system 消息，只保留 user 和 assistant 消息
        filtered_history = [msg for msg in history if msg['role'] in ['user', 'assistant']]
        
        if filtered_history:
            # 将历史消息格式化为对话形式，明确标注历史对话
            history_text = "\n".join([
                f"{'用户' if msg['role'] == 'user' else '助手'}: {msg['content']}"
                for msg in filtered_history
            ])
            user_prompt = f"以下是历史对话记录：\n{history_text}\n\n当前用户问题：{task}"
            self.debug.log_orchestrator_step("构建用户提示", {"has_history": True, "history_count": len(filtered_history), "total_count": len(history)})
        else:
            user_prompt = task
            self.debug.log_orchestrator_step("构建用户提示", {"has_history": False})
        
        # 获取工具定义（LLM Function Calling 格式）
        tools = self.tool_registry.get_tools_for_llm()
        self.debug.log_orchestrator_step("准备工具", {"tool_count": len(tools)})
        
        # LLM 调用（支持工具调用）
        self.debug.log_llm_request(system_prompt, user_prompt, "deepseek-chat")
        response = await self._chat_with_tools(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            tools=tools if tools else None
        )
        self.debug.log_llm_response(response, "deepseek-chat")
        
        # 保存消息到历史
        self.context_manager.add_message(session_id, MessageRole.USER, task)
        self.context_manager.add_message(session_id, MessageRole.ASSISTANT, response)
        self.debug.log_context_operation("保存消息", session_id, {"user": True, "assistant": True})
        
        self.debug.log_orchestrator_step("任务处理完成", {"response_length": len(response)})
        return response
    
    async def stream_process(self, task: str, context: Optional[Dict] = None) -> AsyncIterator[str]:
        """
        流式处理任务
        
        Args:
            task: 用户任务/消息
            context: 上下文信息（可选，包含 session_id）
            
        Yields:
            流式数据块
        """
        self.debug.log_orchestrator_step("开始流式处理任务", {"task": task[:50] + "..." if len(task) > 50 else task})
        
        # 获取会话 ID（如果提供）
        session_id = context.get("session_id") if context else None
        self.debug.log_context_operation("获取会话ID", session_id or "new", {"provided": session_id is not None})
        
        # 如果没有会话 ID，创建新会话
        if not session_id:
            session_id = self.context_manager.create_session()
            self.debug.log_context_operation("创建新会话", session_id)
        
        # 获取历史消息（不压缩，保留完整历史）
        # 注意：当 max_messages 和 max_tokens 都为 None 时，get_messages_for_llm 会获取完整历史
        history = self.context_manager.get_messages_for_llm(
            session_id,
            max_messages=None,  # 不限制消息数量
            max_tokens=None     # 不限制 token 数量
        )
        self.debug.log_context_operation("获取历史消息", session_id, {"count": len(history), "has_history": len(history) > 0})
        
        # 构建消息列表（与 process 方法保持一致）
        system_prompt = """你是一个智能助手，能够帮助用户解决各种问题。当用户提供历史对话记录时，请基于历史对话内容来理解和回答当前问题。

重要：当用户询问天气信息时，你必须使用 get_weather 工具来获取实时天气数据。绝对不要编造或猜测天气信息，也不要从历史对话记录中提取旧的天气信息。如果工具调用失败，请明确告诉用户工具调用失败，不要生成虚假的天气信息。

当展示天气信息时，请使用清晰、美观的 Markdown 格式，并添加天气和风力图标：

**天气图标对照表：**
- ☀️ 晴天
- ⛅ 多云
- ☁️ 阴天
- 🌧️ 雨天
- ⛈️ 雷雨
- 🌨️ 雪天
- 🌫️ 雾/霾
- 🌪️ 大风/龙卷风

**风力图标对照表：**
- 🍃 微风（1-3级）
- 💨 轻风（4-5级）
- 🌬️ 和风（6-7级）
- 💨💨 强风（8-9级）
- 🌪️ 狂风（10级以上）

**格式要求：**

1. **当前天气**：使用列表或简洁的段落展示，添加天气图标
   - 例如：☀️ 晴，温度 3°C，体感温度 0°C
   - 如果提供了空气质量数据，请显示雾霾指数（AQI）和空气质量等级
     * AQI 0-50：🟢 优
     * AQI 51-100：🟡 良
     * AQI 101-150：🟠 轻度污染
     * AQI 151-200：🔴 中度污染
     * AQI 201-300：🟣 重度污染
     * AQI >300：⚫ 严重污染
   - 例如：🌫️ 空气质量：AQI 85，🟡 良，PM2.5: 45μg/m³

2. **天气预报**：使用 Markdown 表格格式，在天气和风向列中添加图标，例如：
   | 日期 | 天气 | 最高温度 | 最低温度 | 风向 | 湿度 |
   |------|------|---------|---------|------|------|
   | 1月3日 | ☀️ 晴 | 6°C | -4°C | 🍃 西北风1-3级 | 24% |
   | 1月4日 | ☀️ 晴 | 5°C | -5°C | 🍃 东风1-3级 | 29% |
   | 1月5日 | ⛅ 多云 | 4°C | -4°C | 💨 西南风4-5级 | 35% |

3. **穿衣建议**：根据温度、天气状况和风力提供穿衣指数和建议
   - 使用温度范围判断：
     * 30°C以上：🔥 炎热，建议穿轻薄透气的短袖、短裤
     * 25-30°C：☀️ 温暖，建议穿T恤、薄长裤
     * 15-25°C：😊 舒适，建议穿长袖、薄外套
     * 5-15°C：🧥 凉爽，建议穿薄外套、长裤
     * 0-5°C：🧣 较冷，建议穿厚外套、毛衣
     * 0°C以下：❄️ 寒冷，建议穿羽绒服、厚毛衣、保暖内衣
   - 根据天气状况调整：
     * 雨天：🌧️ 建议穿防水外套或带雨具
     * 雪天：🌨️ 建议穿防滑鞋、保暖衣物
     * 大风：💨 建议穿防风外套

4. **带伞建议**：
   - 🌧️ 有雨：**建议带伞**
   - ⛈️ 雷雨：**强烈建议带伞**
   - 🌨️ 雪天：**建议带伞（防雪）**
   - ☀️ 晴天：无需带伞
   - ⛅ 多云：建议携带轻便雨具（以防突发降雨）

5. **总结**：使用标题（##）和列表（-）组织信息

请确保：
- 表格对齐整齐
- 信息层次清晰
- 使用适当的 Markdown 语法（标题、列表、表格、粗体）
- 根据实际天气状况选择合适的图标
- 根据风力等级选择合适的风力图标"""
        
        # 构建 user_prompt（包含历史上下文）
        # 过滤掉 system 消息，只保留 user 和 assistant 消息
        filtered_history = [msg for msg in history if msg['role'] in ['user', 'assistant']]
        
        if filtered_history:
            # 将历史消息格式化为对话形式，明确标注历史对话
            history_text = "\n".join([
                f"{'用户' if msg['role'] == 'user' else '助手'}: {msg['content']}"
                for msg in filtered_history
            ])
            user_prompt = f"以下是历史对话记录：\n{history_text}\n\n当前用户问题：{task}"
            self.debug.log_orchestrator_step("构建用户提示", {"has_history": True, "history_count": len(filtered_history), "total_count": len(history)})
        else:
            user_prompt = task
            self.debug.log_orchestrator_step("构建用户提示", {"has_history": False})
        
        # 获取工具定义（LLM Function Calling 格式）
        tools = self.tool_registry.get_tools_for_llm()
        self.debug.log_orchestrator_step("准备工具", {"tool_count": len(tools), "tools": [t.get("function", {}).get("name", "unknown") for t in tools] if tools else []})
        
        # 如果有工具可用，先完成工具调用（非流式），然后流式返回最终结果
        if tools:
            try:
                # 使用工具调用获取完整响应
                full_response = await self._chat_with_tools(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    tools=tools
                )
                
                # 确保 full_response 是字符串
                if full_response is None:
                    full_response = ""
                else:
                    full_response = str(full_response)
                
                # 流式返回最终响应（模拟流式输出）
                self.debug.log_llm_response(full_response, "deepseek-chat")
                for char in full_response:
                    yield char
            except Exception as e:
                logger.error(f"流式处理工具调用失败: {str(e)}", exc_info=True)
                error_msg = f"处理请求时出错：{str(e)}"
                for char in error_msg:
                    yield char
                # 不重新抛出异常，让流式响应正常完成
        else:
            # 没有工具，直接流式调用 LLM
            self.debug.log_llm_request(system_prompt, user_prompt, "deepseek-chat")
            full_response = ""
            
            async for chunk in self.llm_service.stream_chat(
                system_prompt=system_prompt,
                user_prompt=user_prompt
            ):
                full_response += chunk
                yield chunk
            
            self.debug.log_llm_response(full_response, "deepseek-chat")
        
        # 保存消息到历史
        self.context_manager.add_message(session_id, MessageRole.USER, task)
        self.context_manager.add_message(session_id, MessageRole.ASSISTANT, full_response)
        self.debug.log_context_operation("保存消息", session_id, {"user": True, "assistant": True})
        
        self.debug.log_orchestrator_step("流式任务处理完成", {"response_length": len(full_response)})
    
    async def _chat_with_tools(
        self,
        system_prompt: str,
        user_prompt: str,
        tools: Optional[list] = None
    ) -> str:
        """
        带工具调用的聊天（处理工具调用循环）
        
        Args:
            system_prompt: 系统提示
            user_prompt: 用户提示
            tools: 工具定义列表
            
        Returns:
            LLM 生成的最终回复
        """
        import json
        
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": user_prompt})
            
            max_iterations = 5  # 最多 5 轮工具调用循环
            iteration = 0
            
            while iteration < max_iterations:
                iteration += 1
                self.debug.log_orchestrator_step(f"工具调用循环第 {iteration} 轮", {})
                
                try:
                    # 调用 LLM（使用 messages 而不是 system_prompt/user_prompt）
                    response = await self.llm_service.chat(messages=messages, tools=tools)
                except Exception as e:
                    logger.error(f"LLM 调用失败: {str(e)}", exc_info=True)
                    return f"抱歉，处理您的请求时出现错误：{str(e)}"
                
                # 检查响应类型
                if isinstance(response, str):
                    # 普通文本回复，直接返回
                    return response
                
                # 检查是否有工具调用
                if hasattr(response, 'tool_calls') and response.tool_calls:
                    self.debug.log_orchestrator_step("检测到工具调用", {"count": len(response.tool_calls)})
                    
                    # 执行所有工具调用
                    tool_results = []
                    for tool_call in response.tool_calls:
                        tool_name = tool_call.function.name
                    tool_args_str = tool_call.function.arguments
                    
                    self.debug.log_orchestrator_step("执行工具", {"name": tool_name, "args": tool_args_str})
                    
                    # 解析参数
                    try:
                        tool_args = json.loads(tool_args_str)
                    except json.JSONDecodeError:
                        tool_args = {}
                    
                    # 执行工具
                    try:
                        tool_result = self.tool_registry.execute(tool_name, **tool_args)
                    except Exception as e:
                        logger.error(f"工具执行失败: {tool_name}, 错误: {str(e)}", exc_info=True)
                        tool_result = ToolResult(
                            success=False,
                            error=f"工具执行失败: {str(e)}"
                        )
                    
                    # 记录详细的执行结果
                    if not tool_result.success:
                        self.debug.log_orchestrator_step("工具执行失败", {
                            "name": tool_name,
                            "error": tool_result.error
                        })
                    
                    # 构建工具结果消息
                    # 如果工具执行失败，确保错误信息清晰
                    if not tool_result.success:
                        tool_result_content = json.dumps({
                            "error": tool_result.error,
                            "success": False
                        }, ensure_ascii=False)
                    else:
                        tool_result_content = json.dumps(tool_result.data, ensure_ascii=False)
                    tool_results.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": tool_name,
                        "content": tool_result_content
                    })
                    
                    self.debug.log_orchestrator_step("工具执行完成", {
                        "name": tool_name,
                        "success": tool_result.success,
                        "error": tool_result.error if not tool_result.success else None
                    })
                
                    # 将助手消息添加到消息历史
                    assistant_message = {
                        "role": "assistant",
                        "content": response.content if response.content else None,
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "type": tc.type,
                                "function": {
                                    "name": tc.function.name,
                                    "arguments": tc.function.arguments
                                }
                            }
                            for tc in response.tool_calls
                        ]
                    }
                    messages.append(assistant_message)
                    
                    # 添加工具结果
                    messages.extend(tool_results)
                    
                    # 继续循环，让 LLM 基于工具结果生成回复
                    continue
                
                # 如果没有工具调用，返回内容
                if hasattr(response, 'content') and response.content:
                    return response.content
                
                # 如果都没有，返回空字符串
                return ""
            
            # 达到最大迭代次数，返回错误信息
            self.debug.log_orchestrator_step("达到最大工具调用迭代次数", {"max_iterations": max_iterations})
            return "抱歉，工具调用未能成功获取信息。"
        except Exception as e:
            logger.error(f"_chat_with_tools 执行失败: {str(e)}", exc_info=True)
            return f"抱歉，处理您的请求时出现错误：{str(e)}"

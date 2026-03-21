/**
 * 代码助手 - 编写、调试、执行代码，支持 execute_code 工具
 * 复用 GeneralChat，使用 general_chat 工具集（含 execute_code）
 * 2026-03-13：历史单条删除与会话删除与通用对话一致（GeneralChat → useDeleteSessionMessage + DELETE API）
 */
import GeneralChat from './GeneralChat'

export default function CodeAssistant() {
  return (
    <GeneralChat
      title="代码助手"
      subtitle="编写、调试、执行代码，支持 execute_code 工具；可调用搜索、浏览器等全部工具"
      sessionType="code_assistant"
      storageKey="code_assistant_selected_session"
      defaultPersona="你是一个代码助手，擅长编写、调试和执行代码。请优先使用 execute_code 工具执行用户提供的代码。"
    />
  )
}

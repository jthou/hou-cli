/**
 * 用户问题下方的操作按钮：重新回答、写回输入框、删除
 * 供 GeneralChat、WorkAssistant、ArticleWriting 等 LLM 对话页面复用
 *
 * 2026-03-21：移除「添加到参考」——与会话历史重复注入上下文，产品侧不再提供对话内入口
 *
 * @param {Object} props
 * @param {string} props.content - 用户问题内容
 * @param {string} [props.messageId] - 消息 ID，有则显示「重新回答」「删除」
 * @param {(messageId: string) => void} [props.onRegenerate] - 重新回答回调
 * @param {(content: string) => void} [props.onWriteToInput] - 写回输入框回调
 * @param {(messageId: string) => void} [props.onDeleteMessage] - 删除消息回调
 * @param {boolean} [props.loading=false] - 是否禁用「重新回答」
 * @param {string} [props.className=''] - 容器类名
 */
export default function UserMessageActionButtons({
  content = '',
  messageId,
  onRegenerate,
  onWriteToInput,
  onDeleteMessage,
  loading = false,
  className = '',
}) {
  const trimmed = (content || '').trim()
  if (!trimmed) return null

  const btnCls = 'px-2.5 py-1 text-xs rounded border border-border text-muted hover:text-accent hover:bg-white/5 disabled:opacity-50'

  return (
    <div className={`mt-1.5 flex items-center gap-2 flex-wrap justify-end ${className}`.trim()}>
      {messageId && onRegenerate && (
        <button
          type="button"
          onClick={() => onRegenerate(messageId)}
          disabled={loading}
          className={btnCls}
          title="要求 AI 重新回答此问题"
        >
          重新回答
        </button>
      )}
      {onWriteToInput && (
        <button
          type="button"
          onClick={() => onWriteToInput(trimmed)}
          className={btnCls}
          title="将问题写回输入框"
        >
          写回输入框
        </button>
      )}
      {messageId && onDeleteMessage && (
        <button
          type="button"
          onClick={() => onDeleteMessage(messageId)}
          className={btnCls}
          title="删除此消息"
        >
          删除
        </button>
      )}
    </div>
  )
}

/**
 * 用户问题下方的三个操作按钮：重新回答、写回输入框、添加到参考
 * 供 GeneralChat、WorkAssistant、ArticleWriting 等 LLM 对话页面复用
 *
 * @param {Object} props
 * @param {string} props.content - 用户问题内容
 * @param {string} [props.messageId] - 消息 ID，有则显示「重新回答」
 * @param {(messageId: string) => void} [props.onRegenerate] - 重新回答回调
 * @param {(content: string) => void} [props.onWriteToInput] - 写回输入框回调
 * @param {(content: string) => void} [props.onAddToReference] - 添加到参考回调
 * @param {boolean} [props.loading=false] - 是否禁用「重新回答」
 * @param {string} [props.className=''] - 容器类名
 */
export default function UserMessageActionButtons({
  content = '',
  messageId,
  onRegenerate,
  onWriteToInput,
  onAddToReference,
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
      {onAddToReference && (
        <button
          type="button"
          onClick={() => onAddToReference(trimmed)}
          className={btnCls}
          title="添加到参考信息"
        >
          添加到参考
        </button>
      )}
    </div>
  )
}

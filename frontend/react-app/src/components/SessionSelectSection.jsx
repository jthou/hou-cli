/**
 * 会话选择区块：新建会话 + 会话列表
 * 供 AddReference 等页面复用
 */
const SESSION_BTN_CLS = 'w-full text-left px-4 py-3 rounded-lg border border-border bg-white/5 hover:bg-white/10 text-white text-sm'

export default function SessionSelectSection({
  title,
  sessions = [],
  onSelect,
  onNewAndAdd,
  emptyMessage = '暂无会话',
}) {
  return (
    <section>
      <h3 className="text-sm font-medium text-fg mb-3">{title}</h3>
      <div className="space-y-2">
        <button type="button" onClick={onNewAndAdd} className={SESSION_BTN_CLS}>
          <span className="font-medium">新建会话</span>
          <span className="text-muted ml-2">并添加到此会话</span>
        </button>
        {sessions.map((s) => (
          <button
            key={s.session_id}
            type="button"
            onClick={() => onSelect(s.session_id)}
            className={SESSION_BTN_CLS}
          >
            <span className="font-medium truncate block">
              {(s.title || s.preview || '未命名会话').slice(0, 40)}
            </span>
            {s.updated_at && (
              <span className="text-muted text-xs block mt-0.5">
                {new Date(s.updated_at).toLocaleString()}
              </span>
            )}
          </button>
        ))}
        {sessions.length === 0 && (
          <p className="text-muted text-sm py-2">{emptyMessage}</p>
        )}
      </div>
    </section>
  )
}

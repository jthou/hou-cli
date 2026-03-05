import { useState, useEffect } from 'react'

export default function SettingsKanban() {
  const [boards, setBoards] = useState([])
  const [boardsLoading, setBoardsLoading] = useState(true)
  const [boardsError, setBoardsError] = useState(null)

  const [activeBoardId, setActiveBoardId] = useState(null)
  const [board, setBoard] = useState(null)
  const [boardLoading, setBoardLoading] = useState(false)
  const [boardError, setBoardError] = useState(null)

  useEffect(() => {
    setBoardsLoading(true)
    setBoardsError(null)
    fetch('/api/settings/kanban/boards')
      .then((r) => r.json())
      .then((d) => {
        if (d.success && Array.isArray(d.boards)) {
          setBoards(d.boards)
          if (d.boards.length > 0) {
            setActiveBoardId((prev) => prev ?? d.boards[0].board_id)
          }
        } else {
          setBoardsError(d.error || '加载看板列表失败')
          setBoards([])
        }
      })
      .catch((e) => {
        setBoardsError(e?.message || '加载看板列表失败')
        setBoards([])
      })
      .finally(() => setBoardsLoading(false))
  }, [])

  useEffect(() => {
    if (!activeBoardId) {
      setBoard(null)
      return
    }
    setBoardLoading(true)
    setBoardError(null)
    fetch(`/api/settings/kanban/board?board_id=${activeBoardId}`)
      .then((r) => r.json())
      .then((d) => {
        if (d.success && d.board) {
          setBoard(d.board)
        } else {
          setBoardError(d.error || '加载看板详情失败')
          setBoard(null)
        }
      })
      .catch((e) => {
        setBoardError(e?.message || '加载看板详情失败')
        setBoard(null)
      })
      .finally(() => setBoardLoading(false))
  }, [activeBoardId])

  return (
    <div className="flex flex-col h-full">
      <header className="shrink-0 px-6 py-4 border-b border-border">
        <h1 className="text-xl font-semibold text-white">Wiki看板</h1>
        <p className="text-[#94a3b8] text-sm mt-1">
          读取 MediaWiki 中的 KanbanBoard，看板 → 列 → 卡片，只读预览。
        </p>
      </header>

      <div className="flex-1 overflow-hidden flex flex-col min-h-0">
        <div className="flex-1 flex min-h-0 overflow-hidden">
          {/* 左侧：看板列表 */}
          <div className="w-60 shrink-0 border-r border-border overflow-y-auto p-2">
            {boardsLoading && (
              <div className="px-3 py-2 text-xs text-[#94a3b8]">加载看板列表中…</div>
            )}
            {boardsError && (
              <div className="px-3 py-2 text-xs text-red-400">{boardsError}</div>
            )}
            {!boardsLoading && !boardsError && boards.length === 0 && (
              <div className="px-3 py-2 text-xs text-[#94a3b8]">暂无看板</div>
            )}
            {!boardsLoading && !boardsError && boards.length > 0 && (
              <ul className="space-y-1">
                {boards.map((b) => (
                  <li key={b.board_id}>
                    <button
                      type="button"
                      onClick={() => setActiveBoardId(b.board_id)}
                      className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors ${
                        activeBoardId === b.board_id
                          ? 'bg-accent/20 text-accent border border-accent/40'
                          : 'text-[#94a3b8] hover:bg-white/5 hover:text-white border border-transparent'
                      }`}
                    >
                      <div className="flex items-center justify-between gap-2">
                        <span className="truncate">{b.board_name || `看板 #${b.board_id}`}</span>
                        {b.board_status && (
                          <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-white/5 text-[#64748b] border border-border">
                            {b.board_status}
                          </span>
                        )}
                      </div>
                      {b.board_description && (
                        <p className="mt-0.5 text-[11px] text-[#64748b] line-clamp-2">
                          {b.board_description}
                        </p>
                      )}
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>

          {/* 右侧：看板详情 */}
          <div className="flex-1 overflow-hidden flex flex-col min-w-0">
            <div className="shrink-0 px-6 py-3 border-b border-border flex items-center justify-between">
              {board ? (
                <>
                  <div>
                    <h2 className="text-lg font-semibold text-white">
                      {board.board_name || `看板 #${board.board_id || activeBoardId}`}
                    </h2>
                    {board.board_description && (
                      <p className="text-xs text-[#64748b] mt-1">
                        {board.board_description}
                      </p>
                    )}
                  </div>
                  <div className="flex items-center gap-3 text-xs text-[#64748b]">
                    <span>列：{Array.isArray(board.columns) ? board.columns.length : 0}</span>
                    <span>
                      任务：
                      {Array.isArray(board.columns)
                        ? board.columns.reduce(
                            (sum, c) => sum + (Array.isArray(c.cards) ? c.cards.length : 0),
                            0,
                          )
                        : 0}
                    </span>
                  </div>
                </>
              ) : (
                <div className="text-sm text-[#94a3b8]">
                  {boardLoading ? '加载看板详情中…' : '请选择左侧的一个看板'}
                </div>
              )}
            </div>

            <div className="flex-1 overflow-auto p-4">
              {boardError && (
                <div className="text-red-400 text-sm mb-3">{boardError}</div>
              )}
              {board && Array.isArray(board.columns) && board.columns.length > 0 ? (
                <div className="flex items-start gap-4 overflow-x-auto pb-4">
                  {board.columns.map((col) => (
                    <div
                      key={col.column_id}
                      className="w-72 shrink-0 bg-white/5 border border-border rounded-xl p-3 flex flex-col max-h-[calc(100vh-220px)]"
                    >
                      <div className="flex items-center justify-between gap-2 mb-2">
                        <div>
                          <h3 className="text-sm font-semibold text-white truncate">
                            {col.column_name || col.status_name || `列 #${col.column_id}`}
                          </h3>
                          <p className="text-[11px] text-[#64748b] mt-0.5">
                            {Array.isArray(col.cards) ? col.cards.length : 0} 个卡片
                          </p>
                        </div>
                      </div>
                      <div className="flex-1 overflow-y-auto space-y-2 mt-1 pr-1">
                        {Array.isArray(col.cards) && col.cards.length > 0 ? (
                          col.cards.map((card) => (
                            <div
                              key={card.card_id}
                              className="bg-surface/80 border border-border rounded-lg px-3 py-2 text-xs text-[#e2e8f0] shadow-sm"
                            >
                              <div className="font-medium text-[13px] text-white truncate">
                                {card.card_title || `卡片 #${card.card_id}`}
                              </div>
                              {card.card_description && (
                                <p className="text-[11px] text-[#94a3b8] mt-0.5 line-clamp-3">
                                  {card.card_description}
                                </p>
                              )}
                              <div className="flex items-center justify-between mt-1 text-[10px] text-[#64748b]">
                                {card.card_priority && (
                                  <span>{card.card_priority}</span>
                                )}
                                {card.card_due_date && (
                                  <span>截止：{String(card.card_due_date).slice(0, 10)}</span>
                                )}
                              </div>
                            </div>
                          ))
                        ) : (
                          <div className="text-[11px] text-[#64748b] py-2 text-center">
                            暂无卡片
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                !boardLoading &&
                !boardError && (
                  <div className="text-sm text-[#94a3b8]">
                    {board ? '该看板下暂无列' : '请选择左侧的一个看板'}
                  </div>
                )
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}


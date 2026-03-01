/**
 * 从公众号永久图片素材库中挑选一张，用于封面等。
 * 拉取 /api/wechat-mp/materials/images，展示缩略图网格，选中后回调 onSelect(media_id)。
 */
import { useState, useEffect } from 'react'

export default function WechatMaterialImagePicker({ onSelect }) {
  const [open, setOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const [items, setItems] = useState([])
  const [totalCount, setTotalCount] = useState(0)
  const [error, setError] = useState(null)
  const [offset, setOffset] = useState(0)
  const pageSize = 20

  const load = async (off = 0, append = false) => {
    setLoading(true)
    if (!append) setError(null)
    try {
      const r = await fetch(`/api/wechat-mp/materials/images?offset=${off}&count=${pageSize}`)
      const data = await r.json()
      if (!data.success) throw new Error(data.detail || '加载失败')
      const list = data.item || []
      setItems((prev) => (append ? [...prev, ...list] : list))
      setTotalCount(data.total_count ?? 0)
      setOffset(off)
    } catch (e) {
      setError(e?.message || '加载素材列表失败')
      if (!append) setItems([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (open && items.length === 0 && !loading) load(0)
  }, [open])

  const handleSelect = (mediaId) => {
    if (typeof onSelect === 'function') onSelect(mediaId)
    setOpen(false)
  }

  const hasMore = totalCount > offset + items.length
  const loadMore = () => load(offset + pageSize, true)

  return (
    <div className="mt-2">
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="px-3 py-1.5 text-sm rounded border border-border text-[#94a3b8] hover:text-white hover:border-accent"
      >
        从素材库选择
      </button>

      {open && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
          onClick={() => setOpen(false)}
        >
          <div
            className="bg-surface border border-border rounded-xl shadow-xl w-full max-w-2xl max-h-[80vh] overflow-hidden flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex justify-between items-center shrink-0 px-4 py-3 border-b border-border">
              <span className="text-white font-medium">选择素材库图片</span>
              <button
                type="button"
                onClick={() => setOpen(false)}
                className="text-[#94a3b8] hover:text-white text-xl leading-none"
              >
                ×
              </button>
            </div>
            <div className="flex-1 min-h-0 overflow-y-auto p-4">
              {loading && items.length === 0 ? (
                <p className="text-[#64748b] text-sm">加载中…</p>
              ) : error ? (
                <p className="text-amber-400/90 text-sm">{error}</p>
              ) : items.length === 0 ? (
                <p className="text-[#64748b] text-sm">暂无图片素材，请先上传</p>
              ) : (
                <>
                  <div className="grid grid-cols-4 sm:grid-cols-5 gap-3">
                    {items.map((it) => (
                      <button
                        type="button"
                        key={it.media_id}
                        onClick={() => handleSelect(it.media_id)}
                        className="rounded-lg border border-border overflow-hidden hover:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
                      >
                        <img
                          src={`/api/wechat-mp/cover-image?media_id=${encodeURIComponent(it.media_id)}`}
                          alt={it.name || it.media_id}
                          className="w-full aspect-square object-cover"
                        />
                        <p className="text-xs text-[#64748b] truncate px-1 py-0.5" title={it.media_id}>
                          {it.name || it.media_id}
                        </p>
                      </button>
                    ))}
                  </div>
                  {hasMore && (
                    <div className="mt-3 text-center">
                      <button
                        type="button"
                        onClick={loadMore}
                        disabled={loading}
                        className="px-3 py-1.5 text-sm rounded border border-border text-[#94a3b8] hover:text-white disabled:opacity-50"
                      >
                        {loading ? '加载中…' : '加载更多'}
                      </button>
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

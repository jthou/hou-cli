/**
 * 批量删除会话（POST /api/sessions/batch-delete + 可选 expected_type）
 *
 * 时间：2026-03-21；理由：四助手侧栏多选删会话与后端设计一致；方法：useCallback + fetch + loadSessions + IndexedDB 参考块清理
 */
import { useCallback } from 'react'
import { deleteReferenceBlocksForSessions } from '../utils/articleWritingIndexedDB'

/**
 * @param {Object} opts
 * @param {string} [opts.sessionType] - 传给 expected_type，防跨助手误删
 * @param {() => void} opts.loadSessions
 * @param {string|null} opts.selectedSessionId
 * @param {import('react').Dispatch<import('react').SetStateAction<string|null>>} opts.setSelectedSessionId
 * @param {import('react').Dispatch<import('react').SetStateAction<Array<unknown>>>} opts.setMessages
 * @param {string} opts.storageKey - sessionStorage 选中会话键，清空选中时移除
 * @param {{ error?: (msg: string) => void, info?: (msg: string) => void }|null|undefined} opts.toast
 */
export function useBatchDeleteSessions({
  sessionType,
  loadSessions,
  selectedSessionId,
  setSelectedSessionId,
  setMessages,
  storageKey,
  toast,
}) {
  return useCallback(
    async (sessionIds) => {
      if (!Array.isArray(sessionIds) || sessionIds.length === 0) return
      const body = { session_ids: sessionIds }
      if (sessionType) {
        body.expected_type = sessionType
      }
      try {
        const r = await fetch('/api/sessions/batch-delete', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        })
        let d
        try {
          d = await r.json()
        } catch (_) {
          toast?.error?.('响应解析失败')
          return
        }
        if (d?.success === false && d?.error) {
          toast?.error?.(d.error)
          return
        }
        const deleted = Array.isArray(d?.deleted) ? d.deleted : []
        const failed = Array.isArray(d?.failed) ? d.failed : []
        if (deleted.length > 0) {
          try {
            await deleteReferenceBlocksForSessions(
              deleted.map((sessionId) => ({ sessionId, type: sessionType || 'article_writing' }))
            )
          } catch (e) {
            console.warn('[useBatchDeleteSessions] IndexedDB 参考块清理失败:', e)
          }
        }
        loadSessions?.()
        const deletedSet = new Set(deleted)
        if (selectedSessionId && deletedSet.has(selectedSessionId)) {
          setSelectedSessionId(null)
          setMessages([])
          try {
            sessionStorage.removeItem(storageKey)
          } catch (_) {}
        }
        if (failed.length > 0 && deleted.length === 0) {
          const msg = failed.slice(0, 3).map((f) => f.session_id || f.error).join('；')
          toast?.error?.(`删除失败（${failed.length} 个）${msg ? `：${msg}` : ''}`)
        } else if (failed.length > 0) {
          toast?.info?.(`已删除 ${deleted.length} 个会话，${failed.length} 个失败`)
        } else if (deleted.length > 0) {
          toast?.info?.(`已删除 ${deleted.length} 个会话`)
        }
      } catch (err) {
        toast?.error?.(err?.message || '批量删除失败')
      }
    },
    [
      sessionType,
      loadSessions,
      selectedSessionId,
      setSelectedSessionId,
      setMessages,
      storageKey,
      toast,
    ]
  )
}

/**
 * 批量删除当前会话内消息（POST .../messages/batch-delete）
 *
 * 时间：2026-03-21；理由：四助手对话区多选删消息；方法：useCallback + fetch + setMessages 按 deleted 过滤
 */
import { useCallback } from 'react'

/**
 * @param {Object} opts
 * @param {string|null} opts.selectedSessionId
 * @param {import('react').Dispatch<import('react').SetStateAction<Array<{ message_id?: string }>>>} opts.setMessages
 * @param {{ error?: (msg: string) => void, info?: (msg: string) => void }|null|undefined} opts.toast
 */
export function useBatchDeleteMessages({ selectedSessionId, setMessages, toast }) {
  return useCallback(
    async (messageIds) => {
      if (!selectedSessionId || !Array.isArray(messageIds) || messageIds.length === 0) return
      const url = `/api/sessions/${encodeURIComponent(selectedSessionId)}/messages/batch-delete`
      try {
        const r = await fetch(url, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message_ids: messageIds }),
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
        const deletedSet = new Set(deleted)
        if (deletedSet.size > 0) {
          setMessages((prev) => prev.filter((m) => m.message_id && !deletedSet.has(m.message_id)))
        }
        if (failed.length > 0 && deleted.length === 0) {
          toast?.error?.(`${failed.length} 条消息未能删除`)
        } else if (failed.length > 0) {
          toast?.info?.(`已删除 ${deleted.length} 条，${failed.length} 条未找到`)
        } else if (deleted.length > 0) {
          toast?.info?.(`已删除 ${deleted.length} 条消息`)
        }
      } catch (err) {
        toast?.error?.(err?.message || '批量删除失败')
      }
    },
    [selectedSessionId, setMessages, toast]
  )
}

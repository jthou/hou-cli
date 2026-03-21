/**
 * 单条会话消息删除（与通用对话一致）
 *
 * 时间：2026-03-13；理由：工作助手、写作助手、通用对话等多页共用同一后端 DELETE 与会话模型；方法：useCallback + fetch DELETE + setMessages filter
 */
import { useCallback } from 'react'

/**
 * @param {Object} opts
 * @param {string|null} opts.selectedSessionId
 * @param {import('react').Dispatch<import('react').SetStateAction<Array<{ message_id?: string }>>>} opts.setMessages
 * @param {{ confirm?: (msg: string) => Promise<boolean>, error?: (msg: string) => void, info?: (msg: string) => void }|null|undefined} opts.toast
 */
export function useDeleteSessionMessage({ selectedSessionId, setMessages, toast }) {
  return useCallback(
    async (messageId) => {
      if (!selectedSessionId || !messageId) return
      const confirmFn =
        typeof toast?.confirm === 'function' ? toast.confirm : (msg) => Promise.resolve(window.confirm(msg))
      const ok = await confirmFn('确定删除这条消息？删除后不可恢复。')
      if (!ok) return
      const url = `/api/sessions/${encodeURIComponent(selectedSessionId)}/messages/${encodeURIComponent(messageId)}`
      try {
        const r = await fetch(url, { method: 'DELETE' })
        let d
        try {
          d = await r.json()
        } catch (_) {
          toast?.error?.('响应解析失败')
          return
        }
        if (d?.success) {
          setMessages((prev) => prev.filter((m) => m.message_id !== messageId))
          toast?.info?.('已删除')
        } else {
          toast?.error?.(d?.error || '删除失败')
        }
      } catch (err) {
        toast?.error?.(err?.message || '删除失败')
      }
    },
    [selectedSessionId, setMessages, toast]
  )
}

/**
 * 批量删除会话消息（与通用对话一致）
 *
 * 时间：2026-03-21；理由：工作助手、写作助手、通用对话等多页共用同一后端批量删除 API 与会话模型；方法：useCallback + fetch POST + setMessages filter
 */

/**
 * @param {Object} opts
 * @param {string|null} opts.selectedSessionId
 * @param {import('react').Dispatch<import('react').SetStateAction<Array<{ message_id?: string }>>>} opts.setMessages
 * @param {{ confirm?: (msg: string) => Promise<boolean>, error?: (msg: string) => void, info?: (msg: string) => void, success?: (msg: string) => void }|null|undefined} opts.toast
 */
export function useBatchDeleteSessionMessages({ selectedSessionId, setMessages, toast }) {
  return useCallback(
    async (messageIds) => {
      if (!selectedSessionId || !Array.isArray(messageIds) || messageIds.length === 0) return

      const confirmMsg = `确定删除选中的 ${messageIds.length} 条消息？删除后不可恢复。`
      const confirmFn =
        typeof toast?.confirm === 'function' ? toast.confirm : (msg) => Promise.resolve(window.confirm(msg))
      const ok = await confirmFn(confirmMsg)
      if (!ok) return

      const url = `/api/sessions/${encodeURIComponent(selectedSessionId)}/messages/batch-delete`
      try {
        const response = await fetch(url, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ message_ids: messageIds })
        })

        let data
        try {
          data = await response.json()
        } catch (_) {
          toast?.error?.('响应解析失败')
          return
        }

        if (data?.success) {
          // 从前端状态中过滤掉被删除的消息
          setMessages((prev) => prev.filter((m) => !messageIds.includes(m.message_id)))

          if (data.failed && data.failed.length > 0) {
            const failedCount = data.failed.length
            const successCount = data.deleted.length
            toast?.info?.(`成功删除 ${successCount} 条，${failedCount} 条失败`)
          } else {
            toast?.success?.(`成功删除 ${data.deleted.length} 条消息`)
          }
        } else {
          toast?.error?.(data?.error || '批量删除失败')
        }
      } catch (err) {
        toast?.error?.(err?.message || '批量删除失败')
      }
    },
    [selectedSessionId, setMessages, toast]
  )
}

/**
 * 批量删除会话
 *
 * @param {Object} opts
 * @param {Function} opts.loadSessions - 重新加载会话列表的函数
 * @param {Function} opts.setSelectedSessionId - 设置当前选中会话的函数
 * @param {string|null} opts.selectedSessionId - 当前选中的会话 ID
 * @param {{ confirm?: (msg: string) => Promise<boolean>, error?: (msg: string) => void, info?: (msg: string) => void, success?: (msg: string) => void }|null|undefined} opts.toast
 */
export function useBatchDeleteSessions({ loadSessions, setSelectedSessionId, selectedSessionId, toast }) {
  return useCallback(
    async (sessionIds) => {
      if (!Array.isArray(sessionIds) || sessionIds.length === 0) return

      const confirmMsg = `确定删除选中的 ${sessionIds.length} 个会话？删除后不可恢复。`
      const confirmFn =
        typeof toast?.confirm === 'function' ? toast.confirm : (msg) => Promise.resolve(window.confirm(msg))
      const ok = await confirmFn(confirmMsg)
      if (!ok) return

      const url = '/api/sessions/batch-delete'
      try {
        const response = await fetch(url, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ session_ids: sessionIds })
        })

        let data
        try {
          data = await response.json()
        } catch (_) {
          toast?.error?.('响应解析失败')
          return
        }

        if (data?.success) {
          // 重新加载会话列表
          if (loadSessions) {
            await loadSessions()
          }

          // 如果当前选中的会话被删除，清空选中状态
          if (selectedSessionId && sessionIds.includes(selectedSessionId)) {
            setSelectedSessionId(null)
          }

          // 清理对应的 IndexedDB 参考块
          if (Array.isArray(data.deleted_session_info)) {
            try {
              const { deleteReferenceBlocksForSessions } = await import('../utils/articleWritingIndexedDB');
              await deleteReferenceBlocksForSessions(data.deleted_session_info);
            } catch (e) {
              console.warn('清理 IndexedDB 参考块失败:', e);
            }
          }

          if (data.failed && data.failed.length > 0) {
            const failedCount = data.failed.length
            const successCount = data.deleted.length
            toast?.info?.(`成功删除 ${successCount} 个会话，${failedCount} 个失败`)
          } else {
            toast?.success?.(`成功删除 ${data.deleted.length} 个会话`)
          }
        } else {
          toast?.error?.(data?.error || '批量删除失败')
        }
      } catch (err) {
        toast?.error?.(err?.message || '批量删除失败')
      }
    },
    [loadSessions, setSelectedSessionId, selectedSessionId, toast]
  )
}
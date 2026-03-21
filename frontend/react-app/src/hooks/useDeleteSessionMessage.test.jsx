/**
 * 时间：2026-03-13；理由：单条删除为跨页关键路径；方法：mock fetch + renderHook 调用回调
 * @vitest-environment jsdom
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useDeleteSessionMessage } from './useDeleteSessionMessage'

describe('useDeleteSessionMessage', () => {
  beforeEach(() => {
    global.fetch = vi.fn()
  })
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('确认后发起 DELETE 并在 success 时过滤消息', async () => {
    global.fetch.mockResolvedValue({
      json: () => Promise.resolve({ success: true }),
    })
    const setMessages = vi.fn()
    const toast = { confirm: vi.fn(() => Promise.resolve(true)), info: vi.fn(), error: vi.fn() }
    const { result } = renderHook(() =>
      useDeleteSessionMessage({
        selectedSessionId: 'sess-1',
        setMessages,
        toast,
      })
    )
    await act(async () => {
      await result.current('b')
    })
    expect(global.fetch).toHaveBeenCalledWith(
      '/api/sessions/sess-1/messages/b',
      expect.objectContaining({ method: 'DELETE' })
    )
    expect(toast.info).toHaveBeenCalledWith('已删除')
    expect(setMessages).toHaveBeenCalled()
    const updater = setMessages.mock.calls[0][0]
    expect(updater([{ message_id: 'a' }, { message_id: 'b' }])).toEqual([{ message_id: 'a' }])
  })

  it('无 session 或 messageId 时不请求', async () => {
    const setMessages = vi.fn()
    const { result } = renderHook(() =>
      useDeleteSessionMessage({ selectedSessionId: null, setMessages, toast: {} })
    )
    await act(async () => {
      await result.current('x')
    })
    expect(global.fetch).not.toHaveBeenCalled()
  })
})

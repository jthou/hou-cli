/**
 * @vitest-environment jsdom
 * 时间：2026-03-21；理由：批量删消息 API 与 setMessages 过滤；方法：mock fetch + renderHook
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useBatchDeleteMessages } from './useBatchDeleteMessages'

describe('useBatchDeleteMessages', () => {
  beforeEach(() => {
    global.fetch = vi.fn()
  })
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('POST message_ids 并从列表移除已删 id', async () => {
    global.fetch.mockResolvedValue({
      json: () =>
        Promise.resolve({
          success: true,
          deleted: ['m1', 'm2'],
          failed: [],
        }),
    })
    const setMessages = vi.fn((fn) => {
      if (typeof fn === 'function') {
        const prev = [
          { message_id: 'm1', role: 'user', content: 'a' },
          { message_id: 'm2', role: 'user', content: 'b' },
          { message_id: 'm3', role: 'assistant', content: 'c' },
        ]
        return fn(prev)
      }
    })
    const toast = { error: vi.fn(), info: vi.fn() }
    const { result } = renderHook(() =>
      useBatchDeleteMessages({
        selectedSessionId: 'sess-1',
        setMessages,
        toast,
      })
    )
    await act(async () => {
      await result.current(['m1', 'm2'])
    })
    expect(global.fetch).toHaveBeenCalledWith(
      '/api/sessions/sess-1/messages/batch-delete',
      expect.objectContaining({ method: 'POST' })
    )
    const body = JSON.parse(global.fetch.mock.calls[0][1].body)
    expect(body.message_ids).toEqual(['m1', 'm2'])
    expect(setMessages).toHaveBeenCalled()
    const updater = setMessages.mock.calls[0][0]
    const next = updater([
      { message_id: 'm1', content: '' },
      { message_id: 'm2', content: '' },
      { message_id: 'm3', content: '' },
    ])
    expect(next).toEqual([{ message_id: 'm3', content: '' }])
    expect(toast.info).toHaveBeenCalled()
  })
})

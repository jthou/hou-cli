/**
 * @vitest-environment jsdom
 * 时间：2026-03-21；理由：批量删会话含 expected_type 与 IndexedDB 调用；方法：mock fetch + deleteReferenceBlocksForSessions
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useBatchDeleteSessions } from './useBatchDeleteSessions'

vi.mock('../utils/articleWritingIndexedDB', () => ({
  deleteReferenceBlocksForSessions: vi.fn(() => Promise.resolve()),
}))

import { deleteReferenceBlocksForSessions } from '../utils/articleWritingIndexedDB'

describe('useBatchDeleteSessions', () => {
  beforeEach(() => {
    global.fetch = vi.fn()
  })
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('请求体包含 expected_type 并在成功后清理参考块', async () => {
    global.fetch.mockResolvedValue({
      json: () =>
        Promise.resolve({
          success: true,
          deleted: ['s-a'],
          failed: [],
        }),
    })
    const loadSessions = vi.fn()
    const setSelectedSessionId = vi.fn()
    const setMessages = vi.fn()
    const toast = { error: vi.fn(), info: vi.fn() }

    const { result } = renderHook(() =>
      useBatchDeleteSessions({
        sessionType: 'work_assistant',
        loadSessions,
        selectedSessionId: 'other',
        setSelectedSessionId,
        setMessages,
        storageKey: 'k',
        toast,
      })
    )

    await act(async () => {
      await result.current(['s-a'])
    })

    expect(global.fetch).toHaveBeenCalledWith(
      '/api/sessions/batch-delete',
      expect.objectContaining({ method: 'POST' })
    )
    const raw = global.fetch.mock.calls[0][1].body
    expect(JSON.parse(raw)).toEqual({
      session_ids: ['s-a'],
      expected_type: 'work_assistant',
    })
    expect(deleteReferenceBlocksForSessions).toHaveBeenCalledWith([
      { sessionId: 's-a', type: 'work_assistant' },
    ])
    expect(loadSessions).toHaveBeenCalled()
    expect(toast.info).toHaveBeenCalled()
  })

  it('success false 时提示错误且不调用 loadSessions', async () => {
    global.fetch.mockResolvedValue({
      json: () => Promise.resolve({ success: false, error: '类型不符' }),
    })
    const loadSessions = vi.fn()
    const toast = { error: vi.fn(), info: vi.fn() }
    const { result } = renderHook(() =>
      useBatchDeleteSessions({
        sessionType: 'general_chat',
        loadSessions,
        selectedSessionId: null,
        setSelectedSessionId: vi.fn(),
        setMessages: vi.fn(),
        storageKey: 'k',
        toast,
      })
    )
    await act(async () => {
      await result.current(['x'])
    })
    expect(toast.error).toHaveBeenCalledWith('类型不符')
    expect(loadSessions).not.toHaveBeenCalled()
  })
})

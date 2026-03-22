/**
 * 时间：2026-03-13；理由：SSE 分块逻辑三页共用，须回归；方法：vitest 断言 append 与副作用
 */
import { describe, expect, it, vi } from 'vitest'
import { shouldAppendStreamingPlainText } from './streamSseContent'
import { stripAgentStatusPrefix } from './streamUi'
import { parseContextMetaChunk } from './streamContextMeta'

describe('shouldAppendStreamingPlainText', () => {
  it('strips tool and does not append', () => {
    const onToolCall = vi.fn()
    const raw = '__TOOL__:' + JSON.stringify({ name: 'x', success: true })
    expect(shouldAppendStreamingPlainText(raw, { onToolCall })).toBe(false)
    expect(onToolCall).toHaveBeenCalledWith(expect.objectContaining({ name: 'x' }))
  })

  it('parses __CTX_META__ and does not append', () => {
    const onContextMeta = vi.fn()
    const payload = {
      type: 'context_selection',
      strategy: 'hybrid',
      items: [],
      used_count: 0,
      total_in_session: 3,
    }
    const raw = '__CTX_META__:' + JSON.stringify(payload)
    expect(shouldAppendStreamingPlainText(raw, { onContextMeta })).toBe(false)
    expect(onContextMeta).toHaveBeenCalledWith(expect.objectContaining({ type: 'context_selection' }))
  })

  it('filters __DEBUG__ and does not append', () => {
    expect(shouldAppendStreamingPlainText('__DEBUG__:{}', {})).toBe(false)
  })

  it('appends plain text', () => {
    expect(shouldAppendStreamingPlainText('你好', {})).toBe(true)
  })
})

describe('parseContextMetaChunk', () => {
  it('returns null for wrong type', () => {
    expect(parseContextMetaChunk('__CTX_META__:' + JSON.stringify({ type: 'other' }))).toBe(null)
  })
})

describe('stripAgentStatusPrefix', () => {
  it('splits agent preamble', () => {
    const { status, content } = stripAgentStatusPrefix('执行 写作助手Agent 代理...\n\n正文')
    expect(status).toContain('执行')
    expect(content.trimStart()).toMatch(/^正文/)
  })
})

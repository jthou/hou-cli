/**
 * 时间：2026-03-13；理由：控制帧过滤与重复 done 防重依赖稳定前缀；方法：vitest 快照式断言
 */
import { describe, expect, it } from 'vitest'
import { isOrchestratorControlChunk } from './streamChunkFilters'

describe('isOrchestratorControlChunk', () => {
  it('filters evaluation and debug prefixes', () => {
    expect(isOrchestratorControlChunk('__EVALUATION__:{"type":"evaluation"}')).toBe(true)
    expect(isOrchestratorControlChunk('__DEBUG__:{}')).toBe(true)
    expect(isOrchestratorControlChunk('__CTX_META__:{"type":"context_selection"}')).toBe(true)
    expect(isOrchestratorControlChunk('正文')).toBe(false)
  })
})

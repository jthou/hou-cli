/**
 * 与 backend/core/agent/article_writing_message_contract.py 行为对齐（改契约请双端同改）。
 * 时间：2026-03-21；理由：单次对话格式组件化后需回归；方法：vitest
 */
import { describe, it, expect } from 'vitest'
import {
  buildArticleWritingMessageForModel,
  formatReferenceContext,
  ARTICLE_WRITING_USER_QUESTION_MARKER,
} from './referenceUtils.js'

describe('referenceUtils / 单次对话契约', () => {
  it('无参考块时消息仅为用户原文（trim）', () => {
    expect(buildArticleWritingMessageForModel([], '  x  ')).toBe('x')
    expect(buildArticleWritingMessageForModel([{ content: '  ' }], 'y')).toBe('y')
  })

  it('有参考时带【用户本次提问】且格式与 formatReferenceContext 一致', () => {
    const blocks = [{ title: 'T', content: 'C' }]
    const ref = formatReferenceContext(blocks)
    const full = buildArticleWritingMessageForModel(blocks, 'Q')
    expect(full).toBe(`${ref}${ARTICLE_WRITING_USER_QUESTION_MARKER}\nQ`)
    expect(full).toContain('【参考1：T】')
  })
})

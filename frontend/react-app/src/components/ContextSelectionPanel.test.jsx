/**
 * 时间：2026-03-13；理由：article_writing strategy 与 display_role 需回归；方法：vitest + RTL 快照式断言文案
 * @vitest-environment jsdom
 */
import { describe, expect, it, afterEach } from 'vitest'
import { render, screen, cleanup } from '@testing-library/react'
import ContextSelectionPanel from './ContextSelectionPanel'

afterEach(cleanup)

describe('ContextSelectionPanel', () => {
  it('renders article_writing strategy and reference source label', () => {
    const meta = {
      type: 'context_selection',
      strategy: 'article_writing',
      used_count: 2,
      total_in_session: 5,
      query_preview: '续写一句',
      article_writing_note: '会话内聊天记录未注入模型；上列为并入本次 user 提示的素材摘要。',
      items: [
        {
          display_role: '参考',
          role: 'user',
          source: 'injected_reference',
          preview: '用户提供的参考块已并入本条消息（与 Web 参考面板一致）',
          message_id: null,
          index: 0,
        },
        {
          display_role: '指令',
          role: 'user',
          source: 'user_turn',
          preview: '续写一句',
          message_id: null,
          index: 1,
        },
      ],
    }
    render(<ContextSelectionPanel meta={meta} />)
    expect(screen.getByText(/写作助手（会话聊天未注入）/)).toBeInTheDocument()
    expect(screen.getByText('参考块')).toBeInTheDocument()
    expect(screen.getByText(/用户指令（摘要）：/)).toBeInTheDocument()
    expect(screen.getByText(meta.article_writing_note)).toBeInTheDocument()
  })
})

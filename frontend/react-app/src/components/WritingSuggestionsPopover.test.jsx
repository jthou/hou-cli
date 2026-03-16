/**
 * WritingSuggestionsPopover 单元测试：写作建议浮窗显示
 * @vitest-environment jsdom
 */
import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, screen, within, cleanup } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import WritingSuggestionsPopover from './WritingSuggestionsPopover.jsx'

afterEach(cleanup)

describe('WritingSuggestionsPopover', () => {
  const defaultProps = {
    visible: true,
    suggestions: [],
    loading: false,
    position: { top: 100, left: 50 },
    onSelect: vi.fn(),
    onClose: vi.fn(),
    selectedIndex: 0,
  }

  it('visible=false 时不渲染', () => {
    const { container } = render(<WritingSuggestionsPopover {...defaultProps} visible={false} />)
    expect(container.firstChild).toBeNull()
  })

  it('loading=true 时显示「生成中…」', () => {
    render(<WritingSuggestionsPopover {...defaultProps} loading={true} />)
    expect(screen.getByText('生成中…')).toBeInTheDocument()
  })

  it('loading=false 且 suggestions 为空时显示「暂无建议」', () => {
    render(<WritingSuggestionsPopover {...defaultProps} suggestions={[]} />)
    expect(screen.getByText('暂无建议')).toBeInTheDocument()
  })

  it('有 suggestions 时渲染列表项', () => {
    const suggestions = ['续写建议一', '续写建议二', '续写建议三']
    render(<WritingSuggestionsPopover {...defaultProps} suggestions={suggestions} />)
    expect(screen.getByText('续写建议一')).toBeInTheDocument()
    expect(screen.getByText('续写建议二')).toBeInTheDocument()
    expect(screen.getByText('续写建议三')).toBeInTheDocument()
  })

  it('点击某条建议时调用 onSelect', async () => {
    const onSelect = vi.fn()
    const suggestions = ['建议A', '建议B']
    render(<WritingSuggestionsPopover {...defaultProps} suggestions={suggestions} onSelect={onSelect} />)
    await userEvent.click(screen.getByText('建议B'))
    expect(onSelect).toHaveBeenCalledWith('建议B')
  })

  it('selectedIndex 高亮对应项', () => {
    const suggestions = ['A', 'B', 'C']
    render(<WritingSuggestionsPopover {...defaultProps} suggestions={suggestions} selectedIndex={1} />)
    const items = screen.getAllByRole('option')
    expect(items[0]).toHaveAttribute('aria-selected', 'false')
    expect(items[1]).toHaveAttribute('aria-selected', 'true')
    expect(items[2]).toHaveAttribute('aria-selected', 'false')
  })

  it('position 应用到浮窗样式', () => {
    render(
      <WritingSuggestionsPopover {...defaultProps} position={{ top: 200, left: 80, fixed: true }} />
    )
    const popover = document.body.querySelector('[role="listbox"]')
    expect(popover).toBeInTheDocument()
    expect(popover.style.position).toBe('fixed')
    expect(parseInt(popover.style.top, 10)).toBeGreaterThanOrEqual(16)
    expect(parseInt(popover.style.left, 10)).toBeGreaterThanOrEqual(16)
  })

  it('position 为空时使用默认值', () => {
    render(<WritingSuggestionsPopover {...defaultProps} position={null} />)
    const popover = document.body.querySelector('[role="listbox"]')
    expect(popover).toBeInTheDocument()
    expect(parseInt(popover.style.top, 10)).toBeGreaterThanOrEqual(16)
    expect(parseInt(popover.style.left, 10)).toBeGreaterThanOrEqual(16)
  })

  it('显示「写作建议」标题', () => {
    render(<WritingSuggestionsPopover {...defaultProps} />)
    const listbox = screen.getByRole('listbox')
    expect(within(listbox).getByText('写作建议')).toBeInTheDocument()
  })
})

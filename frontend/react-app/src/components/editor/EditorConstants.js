/**
 * 编辑控件公共常量与样式
 * 供 MarkdownEditorPreview、WikitextEditorPreview 等复用
 */

export const TEXTAREA_CLS =
  'flex-1 min-h-[200px] w-full rounded-lg bg-[#1e293b] border border-border px-4 py-3 text-sm text-[#e2e8f0] placeholder-[#64748b] focus:outline-none focus:ring-1 focus:ring-cyan-500 resize-none font-mono leading-relaxed'

export const tabCls = (active) =>
  `px-2 py-1 rounded text-xs ${active ? 'bg-accent text-white' : 'border border-border text-muted hover:bg-white/10'}`

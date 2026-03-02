/**
 * 文章差异对比：展示 oldText 与 newText 的逐行 diff。
 * 红色为仅存在于左侧（旧），绿色为仅存在于右侧（新）。
 */
import { useMemo } from 'react'
import * as Diff from 'diff'

function LinePart({ lines, type }) {
  if (!lines.length) return null
  const bg = type === 'add' ? 'bg-emerald-500/20' : type === 'remove' ? 'bg-red-500/20' : 'bg-transparent'
  const border = type === 'add' ? 'border-l-2 border-emerald-500' : type === 'remove' ? 'border-l-2 border-red-500' : ''
  const prefix = type === 'add' ? '+' : type === 'remove' ? '-' : ' '
  return (
    <div className={`${bg} ${border} pl-2 py-0.5 font-mono text-xs`}>
      {lines.map((line, i) => (
        <div key={i} className="whitespace-pre-wrap break-words">
          <span className="select-none text-[#64748b] mr-2">{prefix}</span>
          {line === '' ? '\u00a0' : line}
        </div>
      ))}
    </div>
  )
}

export default function ArticleDiffView({ oldText = '', newText = '', className = '' }) {
  const parts = useMemo(() => {
    const changes = Diff.diffLines(oldText || '', newText || '')
    return changes.map((part) => {
      const lines = part.value.split(/\n/)
      if (part.added) return { type: 'add', lines }
      if (part.removed) return { type: 'remove', lines }
      return { type: 'same', lines }
    })
  }, [oldText, newText])

  return (
    <div className={`rounded overflow-hidden border border-border ${className}`}>
      <div className="flex items-center gap-4 px-3 py-2 border-b border-border bg-black/20 text-xs text-[#94a3b8]">
        <span><span className="inline-block w-3 h-3 rounded bg-red-500/50 mr-1" />删除（当前有）</span>
        <span><span className="inline-block w-3 h-3 rounded bg-emerald-500/50 mr-1" />新增（该版本有）</span>
      </div>
      <div className="max-h-[70vh] overflow-y-auto bg-[#1e293b] text-[#e2e8f0]">
        {parts.map((part, i) => (
          <LinePart key={i} lines={part.lines} type={part.type} />
        ))}
      </div>
    </div>
  )
}

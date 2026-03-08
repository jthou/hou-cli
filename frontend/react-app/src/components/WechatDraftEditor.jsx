/**
 * 公众号草稿正文：Markdown 编辑 + 预览（与写作助手页共用 MarkdownPreview 组件）
 * 「插入图片」会调用微信「上传图文消息内的图片」接口，得到的 URL 插入正文（公众号仅接受该来源的图片）。
 */
import { useRef, useState } from 'react'
import MarkdownPreview from './MarkdownPreview'
import { formatWechatMpError } from '../utils/wechatMpError'

const inputCls =
  'w-full px-3 py-2 bg-white/5 border border-border rounded-lg text-white placeholder-[#64748b] focus:border-accent focus:outline-none font-mono text-sm resize-y min-h-[320px]'

/**
 * @param {Object} props
 * @param {string} [props.value] - Markdown 文本（受控）
 * @param {(v: string) => void} [props.onChange] - 内容变化回调
 * @param {string} [props.placeholder] - 输入框占位
 * @param {string} [props.className] - 容器类名
 */
export default function WechatDraftEditor({ value = '', onChange, placeholder = '', className = '' }) {
  const textareaRef = useRef(null)
  const fileInputRef = useRef(null)
  const [uploading, setUploading] = useState(false)
  const [uploadError, setUploadError] = useState('')

  const insertImageMarkdown = (url) => {
    const text = value || ''
    const el = textareaRef.current
    const start = el ? el.selectionStart : text.length
    const end = el ? el.selectionEnd : text.length
    const before = text.slice(0, start)
    const after = text.slice(end)
    const insert = `\n![图片](${url})\n`
    onChange?.(before + insert + after)
    setUploadError('')
    if (el) {
      setTimeout(() => {
        el.focus()
        const newPos = start + insert.length
        el.setSelectionRange(newPos, newPos)
      }, 0)
    }
  }

  const onFileChange = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    e.target.value = ''
    setUploadError('')
    setUploading(true)
    try {
      const form = new FormData()
      form.append('file', file)
      const res = await fetch('/api/wechat-mp/upload-article-image', { method: 'POST', body: form })
      const data = await res.json().catch(() => ({}))
      if (!res.ok || !data?.url) {
        setUploadError(formatWechatMpError('正文图片上传失败', new Error(data?.detail || data?.message || '上传失败')))
        return
      }
      insertImageMarkdown(data.url)
    } catch (err) {
      setUploadError(formatWechatMpError('正文图片上传失败', err))
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className={`grid grid-cols-1 md:grid-cols-2 gap-5 min-h-[360px] ${className}`.trim()}>
      <div className="flex flex-col min-h-[320px]">
        <div className="flex items-center justify-between mb-1">
          <span className="text-xs text-muted">正文（Markdown）</span>
          <div className="flex items-center gap-2">
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              className="hidden"
              onChange={onFileChange}
              disabled={uploading}
            />
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              disabled={uploading}
              className="text-xs px-2 py-1 rounded border border-border bg-white/5 text-muted hover:border-accent hover:text-accent disabled:opacity-50"
            >
              {uploading ? '上传中…' : '插入图片'}
            </button>
          </div>
        </div>
        {uploadError && <div className="text-xs text-red-400 mb-1">{uploadError}</div>}
        <textarea
          ref={textareaRef}
          value={value}
          onChange={e => onChange?.(e.target.value)}
          placeholder={placeholder || '支持 **加粗**、# 标题、列表、[链接](url)、![图片](url)...'}
          className={`${inputCls} flex-1`}
          rows={18}
          spellCheck="false"
        />
      </div>
      <div className="flex flex-col min-h-[320px]">
        <div className="text-xs text-muted mb-1">预览（公众号效果）</div>
        <MarkdownPreview
          markdown={value}
          className="rounded-lg p-4 border-2 border-[#d0d7de] shadow-sm flex-1 min-h-[300px]"
        />
      </div>
    </div>
  )
}

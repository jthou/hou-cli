/**
 * 根据 metadata_schema 渲染任务参数表单字段
 * 与 TaskManagement 的 CreateTaskModal、CreateScheduledTaskModal、EditScheduledTaskModal 保持一致
 */
import { useRef, useState } from 'react'
import { useToast } from '../ToastModal'
import {
  getClipboardImageFile,
  insertSnippetAtTextareaCursor,
  snippetForWikitext,
  uploadMediaWikiImageFile,
} from '../../utils/mediawikiPasteImage'

const inputCls = 'w-full px-3 py-2 bg-white/5 border border-border rounded-lg text-white placeholder-[#64748b] focus:border-accent focus:outline-none'
const labelCls = 'block text-sm text-muted mb-1'

function ArrayFieldWithChips({ fieldKey, fieldIdPrefix, label, required, items, onItemsChange, placeholder }) {
  const [inputValue, setInputValue] = useState('')
  const addItem = () => {
    const s = (inputValue || '').trim()
    if (!s) return
    if (items.includes(s)) {
      setInputValue('')
      return
    }
    onItemsChange([...items, s])
    setInputValue('')
  }
  return (
    <div>
      <label className={labelCls} htmlFor={`${fieldIdPrefix}-${fieldKey}-add`}>{label}{required ? ' *' : ''}</label>
      <div className="flex flex-wrap items-center gap-2">
        {items.map((item, i) => (
          <span
            key={`${item}-${i}`}
            className="inline-flex items-center gap-1.5 pl-2.5 pr-1 py-1 rounded-full text-sm bg-cyan-500/20 text-cyan-700 border border-cyan-500/40 dark:text-cyan-200 dark:border-cyan-500/40"
          >
            <span>{item}</span>
            <button
              type="button"
              onClick={() => onItemsChange(items.filter((_, idx) => idx !== i))}
              className="w-5 h-5 flex items-center justify-center rounded-full text-cyan-600 hover:text-fg hover:bg-cyan-500/30 dark:text-cyan-400/80 dark:hover:bg-cyan-500/50 transition-colors flex-shrink-0"
              title="删除"
              aria-label="删除"
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>
            </button>
          </span>
        ))}
        <div className="flex items-center gap-1.5 min-w-0 flex-1">
          <input
            id={`${fieldIdPrefix}-${fieldKey}-add`}
            type="text"
            value={inputValue}
            onChange={e => setInputValue(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); addItem() } }}
            placeholder={placeholder || '输入标签后回车添加'}
            className={`${inputCls} py-1.5 text-sm max-w-[180px]`}
          />
          <button
            type="button"
            onClick={addItem}
            className="px-2.5 py-1.5 rounded-full text-sm border border-cyan-500/50 text-cyan-600 hover:bg-cyan-500/20 hover:text-cyan-800 dark:text-cyan-400 dark:hover:text-cyan-200 dark:hover:bg-cyan-500/20 whitespace-nowrap"
          >
            添加
          </button>
        </div>
      </div>
    </div>
  )
}

/** 支持文件上传的字段：{ fieldKey: accept }；customFieldRender: (fieldKey, { value, onChange, spec, required, label }) => ReactNode | null 可替代默认渲染；fieldsToHide 不渲染的字段 */
export default function TaskMetadataFormFields({
  schema,
  metadata,
  setMetadata,
  fieldIdPrefix = 'meta',
  isInputFileTask = false,
  inputFileAccept = '*',
  fileUploadFields = null, // { [fieldKey]: accept }，优先于 isInputFileTask
  customFieldRender = null, // (fieldKey, { value, onChange, spec, required, label }) => ReactNode | null
  fieldsToHide = null, // string[] 不渲染的字段（如从上游任务绑定时隐藏 input_file）
  /** mediawiki_write：正文(content) 支持粘贴截图上传并插入 [[File:…]] */
  enableMediaWikiPasteImage = false,
}) {
  const toast = useToast()
  const fileInputRefs = useRef({})
  const [pasteUploadingField, setPasteUploadingField] = useState(null)

  const handleMediaWikiPasteImage = async (e, fieldKey) => {
    const file = getClipboardImageFile(e)
    if (!file || pasteUploadingField) return
    e.preventDefault()
    const ta = e.target
    const start = ta.selectionStart ?? 0
    const end = ta.selectionEnd ?? start
    const prev = (metadata[fieldKey] ?? '').toString()
    setPasteUploadingField(fieldKey)
    try {
      const { filename } = await uploadMediaWikiImageFile(file)
      const snippet = snippetForWikitext(filename)
      const r = insertSnippetAtTextareaCursor(prev, start, end, snippet)
      setMetadata((m) => ({ ...m, [fieldKey]: r.nextValue }))
      setTimeout(() => {
        ta.focus()
        ta.setSelectionRange(r.caret, r.caret)
      }, 0)
      toast?.info?.(`已上传 ${filename} 并插入引用`)
    } catch (err) {
      toast?.error?.(err?.message || '图片上传失败')
    } finally {
      setPasteUploadingField(null)
    }
  }

  const getFileAccept = (fieldKey) => {
    if (fileUploadFields && fieldKey in fileUploadFields) return fileUploadFields[fieldKey]
    if (fieldKey === 'input_file' && isInputFileTask) return inputFileAccept
    return null
  }

  const uploadFileAndSet = (fieldKey) => async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    try {
      const form = new FormData()
      form.append('file', file)
      const res = await fetch('/api/task-queue/upload-input-file', { method: 'POST', body: form })
      const data = await res.json()
      if (data.success && data.path) setMetadata(m => ({ ...m, [fieldKey]: data.path }))
      else throw new Error(data.detail || '上传失败')
    } catch (err) {
      toast.error('上传失败: ' + (err?.message || String(err)))
    }
    e.target.value = ''
  }

  if (!schema || typeof schema !== 'object') return null

  return (
    <div className="space-y-4">
      {Object.entries(schema).map(([fieldKey, spec]) => {
        if (!spec || typeof spec !== 'object') return null
        if (fieldsToHide && fieldsToHide.includes(fieldKey)) return null
        const label = spec.description || fieldKey
        const required = spec.required
        const value = metadata[fieldKey] ?? (spec.default ?? (spec.type === 'boolean' ? false : ''))
        const onChange = (v) => setMetadata(m => ({ ...m, [fieldKey]: v }))
        const custom = customFieldRender?.(fieldKey, { value, onChange, spec, required, label })
        if (custom != null) return <div key={fieldKey}>{custom}</div>

        const hasFileUpload = getFileAccept(fieldKey) != null
        const useTextarea = spec.multiline || (fieldKey === 'content' && spec.type === 'string')

        if (spec.enum && Array.isArray(spec.enum)) {
          const selectValue = value != null ? String(value) : ''
          return (
            <div key={fieldKey}>
              <label className={labelCls} htmlFor={`${fieldIdPrefix}-${fieldKey}`}>{label}{required ? ' *' : ''}</label>
              <select
                id={`${fieldIdPrefix}-${fieldKey}`}
                value={selectValue}
                onChange={e => {
                  const v = e.target.value
                  setMetadata(m => ({ ...m, [fieldKey]: v === '' ? undefined : (spec.type === 'number' ? Number(v) : v) }))
                }}
                className={inputCls}
                required={required}
              >
                {!required && <option value="">请选择</option>}
                {spec.enum.map(opt => (
                  <option key={String(opt.value)} value={String(opt.value)}>{opt.label ?? opt.value}</option>
                ))}
              </select>
            </div>
          )
        }

        if (spec.type === 'boolean') {
          return (
            <div key={fieldKey} className="flex items-center gap-2">
              <input
                type="checkbox"
                id={`${fieldIdPrefix}-${fieldKey}`}
                checked={!!value}
                onChange={e => setMetadata(m => ({ ...m, [fieldKey]: e.target.checked }))}
                className="rounded border-border bg-white/5 text-accent focus:ring-accent"
              />
              <label htmlFor={`${fieldIdPrefix}-${fieldKey}`} className="text-sm text-muted cursor-pointer">{label}{required ? ' *' : ''}</label>
            </div>
          )
        }

        if (spec.type === 'array') {
          const arr = Array.isArray(value) ? [...value] : (value ? [value] : [])
          const setArr = (next) => setMetadata(m => ({ ...m, [fieldKey]: next }))
          return (
            <ArrayFieldWithChips
              key={fieldKey}
              fieldKey={fieldKey}
              fieldIdPrefix={fieldIdPrefix}
              label={label}
              required={required}
              items={arr}
              onItemsChange={setArr}
              placeholder={spec.placeholder}
            />
          )
        }

        const accept = getFileAccept(fieldKey)
        return (
          <div key={fieldKey}>
            <label className={labelCls} htmlFor={`${fieldIdPrefix}-${fieldKey}`}>{label}{required ? ' *' : ''}</label>
            <div className="flex gap-2">
              {useTextarea ? (
                <textarea
                  id={`${fieldIdPrefix}-${fieldKey}`}
                  value={value}
                  onChange={e => setMetadata(m => ({ ...m, [fieldKey]: e.target.value }))}
                  onPaste={
                    enableMediaWikiPasteImage && fieldKey === 'content'
                      ? (ev) => handleMediaWikiPasteImage(ev, fieldKey)
                      : undefined
                  }
                  disabled={pasteUploadingField === fieldKey}
                  placeholder={
                    enableMediaWikiPasteImage && fieldKey === 'content'
                      ? (spec.placeholder || '') + '（可粘贴截图上传）'
                      : spec.placeholder || ''
                  }
                  rows={8}
                  className={`${inputCls} flex-1 resize-y min-h-[120px] ${pasteUploadingField === fieldKey ? 'opacity-60' : ''}`}
                  required={required}
                />
              ) : (
                <input
                  id={`${fieldIdPrefix}-${fieldKey}`}
                  type={spec.type === 'number' ? 'number' : 'text'}
                  value={value}
                  onChange={e => setMetadata(m => ({ ...m, [fieldKey]: spec.type === 'number' ? (Number(e.target.value) || 0) : e.target.value }))}
                  placeholder={spec.placeholder || ''}
                  className={`${inputCls} flex-1`}
                  required={required}
                />
              )}
              {hasFileUpload && (
                <>
                  <input
                    ref={el => { fileInputRefs.current[fieldKey] = el }}
                    type="file"
                    accept={accept}
                    className="hidden"
                    onChange={uploadFileAndSet(fieldKey)}
                  />
                  <button
                    type="button"
                    onClick={() => fileInputRefs.current[fieldKey]?.click()}
                    className="px-3 py-2 rounded-lg border border-border text-muted hover:text-fg hover:border-accent whitespace-nowrap"
                  >
                    选择文件
                  </button>
                </>
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
}

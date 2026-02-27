/**
 * 根据 metadata_schema 渲染任务参数表单字段
 * 与 TaskManagement 的 CreateTaskModal、CreateScheduledTaskModal、EditScheduledTaskModal 保持一致
 */
import { useRef } from 'react'
import { useToast } from '../ToastModal'

const inputCls = 'w-full px-3 py-2 bg-white/5 border border-border rounded-lg text-white placeholder-[#64748b] focus:border-accent focus:outline-none'
const labelCls = 'block text-sm text-[#94a3b8] mb-1'

/** 支持文件上传的字段：{ fieldKey: accept }，如 { input_file: '.mp3,...', content_file: '.txt,...' } */
export default function TaskMetadataFormFields({
  schema,
  metadata,
  setMetadata,
  fieldIdPrefix = 'meta',
  isInputFileTask = false,
  inputFileAccept = '*',
  fileUploadFields = null, // { [fieldKey]: accept }，优先于 isInputFileTask
}) {
  const toast = useToast()
  const fileInputRefs = useRef({})

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
        const label = spec.description || fieldKey
        const required = spec.required
        const value = metadata[fieldKey] ?? (spec.default ?? (spec.type === 'boolean' ? false : ''))
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
              <label htmlFor={`${fieldIdPrefix}-${fieldKey}`} className="text-sm text-[#94a3b8] cursor-pointer">{label}{required ? ' *' : ''}</label>
            </div>
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
                  placeholder={spec.placeholder || ''}
                  rows={8}
                  className={`${inputCls} flex-1 resize-y min-h-[120px]`}
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
                    className="px-3 py-2 rounded-lg border border-border text-[#94a3b8] hover:text-white hover:border-accent whitespace-nowrap"
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

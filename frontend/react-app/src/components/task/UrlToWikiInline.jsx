import { useEffect, useState } from 'react'
import { useToast } from '../ToastModal'
import TaskMetadataFormFields from './TaskMetadataFormFields'
import { getDefaultMetadata, getDateCategoryStrings } from './taskFormUtils'
import { prepareMetadataForSubmitAsync } from '../../utils/mdToHtml'

const TASK_TYPE = 'url_to_wiki'

export default function UrlToWikiInline({
  defaultUrl = '',
  defaultWikiTitle = '',
  onClose,
  onCreated,
}) {
  const toast = useToast()
  const [schema, setSchema] = useState(null)
  const [metadata, setMetadata] = useState({})
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    let cancelled = false
    fetch('/api/task-queue/task-types')
      .then((r) => r.json())
      .then((d) => {
        if (cancelled) return
        const types = d.task_types || []
        const info = types.find((t) => t.type === TASK_TYPE)
        const s = info?.metadata_schema || {}
        setSchema(s)
        let meta = getDefaultMetadata(s)
        if (Array.isArray(meta.categories)) {
          meta = { ...meta, categories: [...meta.categories, ...getDateCategoryStrings()] }
        }
        meta = {
          ...meta,
          url: defaultUrl || meta.url || '',
          wiki_title: defaultWikiTitle || meta.wiki_title || '',
          auto_write: false,
        }
        setMetadata(meta)
        setLoading(false)
      })
      .catch(() => {
        if (!cancelled) {
          setSchema({})
          setMetadata({})
          setLoading(false)
        }
      })
    return () => {
      cancelled = true
    }
  }, [defaultUrl, defaultWikiTitle])

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!schema || typeof schema !== 'object') {
      toast.error('任务类型元数据加载失败')
      return
    }
    for (const [key, spec] of Object.entries(schema)) {
      if (spec?.required) {
        const v = metadata[key]
        if (v === undefined || v === null || (typeof v === 'string' && !v.trim())) {
          toast.warning(`请填写必填项: ${spec.description || key}`)
          return
        }
      }
    }
    setSubmitting(true)
    try {
      const meta = await prepareMetadataForSubmitAsync(TASK_TYPE, metadata)
      const res = await fetch('/api/task-queue/tasks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task_type: TASK_TYPE, metadata: meta }),
      })
      const data = await res.json()
      if (data.success) {
        toast.info('已创建网文抓取任务')
        onCreated?.(data.task_id)
        onClose?.()
      } else {
        toast.error(data.detail || data.message || '创建任务失败')
      }
    } catch (err) {
      toast.error(err?.message || '创建任务失败')
    }
    setSubmitting(false)
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
      onClick={onClose}
    >
      <div
        className="bg-surface border border-border rounded-xl shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex justify-between items-center shrink-0 px-6 py-4 border-b border-border">
          <h3 className="text-lg font-semibold text-white">网文抓取（生成 Markdown 草稿）</h3>
          <button
            type="button"
            onClick={onClose}
            className="text-muted hover:text-fg text-2xl leading-none"
          >
            ×
          </button>
        </div>
        <div className="flex-1 min-h-0 overflow-y-auto p-6">
          {loading ? (
            <p className="text-sm text-muted">正在加载任务配置…</p>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4">
              <p className="text-xs text-muted">
                抓取指定 URL 的正文并生成 Markdown 草稿，不会直接写入 MediaWiki。任务完成后可在任务详情中发送到写作助手或选择写入 Wiki。
              </p>
              <TaskMetadataFormFields
                schema={schema}
                metadata={metadata}
                setMetadata={setMetadata}
                fieldIdPrefix="inline-url-to-wiki"
                fieldsToHide={!metadata?.translate ? ['language'] : []}
              />
              <div className="flex justify-end gap-3 pt-4 border-t border-border">
                <button
                  type="button"
                  onClick={onClose}
                  className="px-4 py-2 border border-border rounded-lg text-sm text-muted hover:text-white"
                >
                  取消
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-4 py-2 bg-accent hover:bg-accent-hover text-white rounded-lg text-sm font-medium disabled:opacity-50"
                >
                  {submitting ? '提交中…' : '提交抓取'}
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  )
}


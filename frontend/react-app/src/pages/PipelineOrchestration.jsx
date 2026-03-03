import { useState, useRef } from 'react'
import { Link } from 'react-router-dom'
import { useToast } from '../components/ToastModal'
import { formStyles } from '../components/task/taskFormUtils'
import TaskListByTypePanel from '../components/TaskListByTypePanel'
import { PIPELINE_TEMPLATES } from '../config/pipelineTemplates'

const TASK_API = {
  create: (payload) =>
    fetch('/api/task-queue/tasks', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }).then((r) => r.json()),
}

export default function PipelineOrchestration() {
  const toast = useToast()
  const [step, setStep] = useState('choose') // 'choose' | 'fill'
  const [selectedId, setSelectedId] = useState(null)
  const [formValues, setFormValues] = useState({})
  const [submitting, setSubmitting] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [createdIds, setCreatedIds] = useState(null) // { task1Id, task2Id } after success
  const fileInputRef = useRef(null)

  const template = PIPELINE_TEMPLATES.find((t) => t.id === selectedId)
  const fields = template?.form?.fields || []

  const getInitialFormValues = (t) => {
    const fds = t?.form?.fields || []
    return Object.fromEntries(fds.map((f) => [f.id, '']))
  }

  const handleSelectTemplate = (id) => {
    const t = PIPELINE_TEMPLATES.find((x) => x.id === id)
    setSelectedId(id)
    setStep('fill')
    setCreatedIds(null)
    setFormValues(getInitialFormValues(t))
  }

  const handleBack = () => {
    setStep('choose')
    setSelectedId(null)
    setCreatedIds(null)
  }

  const setField = (fieldId, value) => {
    setFormValues((prev) => ({ ...prev, [fieldId]: value }))
  }

  const handleUpload = async (e, fieldId) => {
    const file = e.target.files?.[0]
    if (!file) return
    setUploading(true)
    try {
      const form = new FormData()
      form.append('file', file)
      const res = await fetch('/api/task-queue/upload-input-file', { method: 'POST', body: form })
      const data = await res.json()
      if (data.success && data.path) setField(fieldId, data.path)
      else throw new Error(data.detail || '上传失败')
    } catch (err) {
      toast.error('上传失败: ' + (err?.message || String(err)))
    }
    setUploading(false)
    e.target.value = ''
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!template?.createTasks) return
    setSubmitting(true)
    setCreatedIds(null)
    try {
      const result = await template.createTasks(formValues, TASK_API)
      setCreatedIds(result)
    } catch (err) {
      toast.error('创建失败: ' + (err?.message || String(err)))
    }
    setSubmitting(false)
  }

  const handleCreateAnother = () => {
    setCreatedIds(null)
    setStep('choose')
    setSelectedId(null)
    setFormValues({})
  }

  const { inputCls, labelCls } = formStyles

  return (
    <div className="flex flex-col h-full">
      <header className="shrink-0 px-6 py-4 border-b border-border">
        <h1 className="text-xl font-semibold text-white">管道编排</h1>
      </header>

      <div className="flex-1 overflow-hidden flex">
        <div className="flex-1 overflow-y-auto p-6 max-w-2xl shrink-0">
        <p className="text-muted mb-6">
          选择一条多任务链路并填写入口参数，系统将按顺序创建任务并自动绑定上下游输出与输入。创建后可在
          <Link to="/" className="text-accent hover:underline ml-1">任务管理</Link>
          中查看执行进度。
        </p>

        {step === 'choose' && !createdIds && (
          <div className="space-y-3">
            <p className="text-sm text-muted">选择一条管道链路，下一步只需填写该链路需要的输入参数。</p>
            {PIPELINE_TEMPLATES.map((t) => (
              <button
                key={t.id}
                type="button"
                onClick={() => handleSelectTemplate(t.id)}
                className="w-full text-left p-4 rounded-xl border border-border bg-white/5 hover:border-cyan-500/50 hover:bg-cyan-500/5 transition-colors"
              >
                <div className="font-medium text-white">{t.name}</div>
                <div className="text-sm text-muted mt-1">{t.description}</div>
                {t.steps && (
                  <div className="flex flex-wrap gap-2 mt-2">
                    {t.steps.map((s, i) => (
                      <span key={i} className="text-xs px-2 py-0.5 rounded bg-white/10 text-muted">
                        {s.label}
                      </span>
                    ))}
                  </div>
                )}
              </button>
            ))}
          </div>
        )}

        {step === 'fill' && template && !createdIds && (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="flex items-center gap-2 mb-4">
              <button
                type="button"
                onClick={handleBack}
                className="px-3 py-1.5 text-sm border border-border rounded-lg text-muted hover:text-fg"
              >
                ← 上一步
              </button>
              <span className="text-muted">填写参数：{template.name}</span>
            </div>
            <p className="text-sm text-muted">
              以下仅需填写<strong className="text-white">第一步</strong>的输入；后续步骤的输入将按链路自动绑定。
            </p>
            {fields.map((field) => (
              <div key={field.id}>
                <label className={labelCls}>
                  {field.label}
                  {field.required ? ' *' : ''}
                </label>
                {field.type === 'file' ? (
                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={formValues[field.id] ?? ''}
                      onChange={(e) => setField(field.id, e.target.value)}
                      placeholder={field.placeholder || ''}
                      className={inputCls + ' flex-1'}
                    />
                    <input
                      type="file"
                      accept={field.accept || '*'}
                      className="hidden"
                      ref={fileInputRef}
                      onChange={(e) => handleUpload(e, field.id)}
                    />
                    <button
                      type="button"
                      onClick={() => fileInputRef.current?.click()}
                      disabled={uploading}
                      className="px-3 py-2 rounded-lg border border-border text-muted hover:text-fg whitespace-nowrap disabled:opacity-50"
                    >
                      {uploading ? '上传中…' : '上传'}
                    </button>
                  </div>
                ) : (
                  <input
                    type="text"
                    value={formValues[field.id] ?? ''}
                    onChange={(e) => setField(field.id, e.target.value)}
                    placeholder={field.placeholder || ''}
                    className={inputCls}
                  />
                )}
              </div>
            ))}
            <div className="flex gap-3 pt-2">
              <button
                type="button"
                onClick={handleBack}
                className="px-4 py-2 border border-border rounded-lg text-muted hover:text-fg"
              >
                上一步
              </button>
              <button
                type="submit"
                disabled={submitting}
                className="px-4 py-2 bg-accent hover:bg-accent-hover text-white rounded-lg disabled:opacity-50"
              >
                {submitting ? '创建中...' : '创建管道'}
              </button>
            </div>
          </form>
        )}

        {createdIds && (
          <div className="p-4 rounded-xl bg-green-500/10 border border-green-500/20 text-green-400 space-y-3">
            <p className="font-medium">管道已创建</p>
            <p className="text-sm">
              任务 ID：{Object.entries(createdIds)
                .filter(([k]) => k.startsWith('task') && k.endsWith('Id'))
                .sort(([a], [b]) => a.localeCompare(b))
                .map(([, v]) => v?.slice(0, 8))
                .join(' → ')}
            </p>
            <div className="flex flex-wrap gap-2">
              <Link
                to="/"
                className="px-4 py-2 bg-accent hover:bg-accent-hover text-white rounded-lg text-sm font-medium"
              >
                去任务管理查看
              </Link>
              <button
                type="button"
                onClick={handleCreateAnother}
                className="px-4 py-2 border border-border rounded-lg text-muted hover:text-fg text-sm"
              >
                再建一条
              </button>
            </div>
          </div>
        )}
        </div>
        <div className="min-w-0 flex-1 border-l border-border overflow-y-auto bg-white/[0.02]">
          <TaskListByTypePanel
            pipelineOnly
            title="管道编排任务"
            emptyText="暂无管道编排任务"
          />
        </div>
      </div>
    </div>
  )
}

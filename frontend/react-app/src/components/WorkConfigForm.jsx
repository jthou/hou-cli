/**
 * 工作配置表单：工作规则、工作上下文、术语表。
 * 工作助手会根据此配置遵循规则、了解工作内容、提示工作建议。
 */
import { useEffect, useState, useCallback, forwardRef, useImperativeHandle } from 'react'
import { useToast } from './ToastModal'

const INPUT_CLASS =
  'w-full min-h-[2.25rem] px-2.5 py-1.5 rounded-md border border-border bg-surface text-fg text-base placeholder:text-muted focus:outline-none focus:ring-1 focus:ring-accent leading-normal font-sans'
const TEXTAREA_CLASS =
  'w-full min-h-[6rem] px-2.5 py-1.5 rounded-md border border-border bg-surface text-fg text-base placeholder:text-muted focus:outline-none focus:ring-1 focus:ring-accent resize-y leading-relaxed font-sans'
const LABEL_CLASS = 'block text-xs font-medium text-fg mb-1'

const WorkConfigForm = forwardRef(function WorkConfigForm({
  className = '',
  showConfigPath = true,
  showSaveButton = true,
  onSaveSuccess,
  onSavingChange,
  onLoad,
  autoLoad = true,
}, ref) {
  const toast = useToast()
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)
  const [configPath, setConfigPath] = useState('')
  const [rules, setRules] = useState([])
  const [workContext, setWorkContext] = useState('')
  const [terms, setTerms] = useState([])

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch('/api/settings/work-config')
      const ct = res.headers.get('content-type') || ''
      if (!ct.includes('application/json')) {
        throw new Error('后端未返回 JSON，可能未启动或 API 不可用。')
      }
      const json = await res.json()
      if (!json.success) throw new Error(json.detail || '获取工作配置失败')
      setConfigPath(json.config_path || '')
      const c = json.config || {}
      setRules(c.rules || [])
      setWorkContext(c.work_context || '')
      setTerms(c.terms || [])
      onLoad?.(json.config)
    } catch (e) {
      setError(e.message || String(e))
    } finally {
      setLoading(false)
    }
  }, [onLoad])

  useEffect(() => {
    if (autoLoad) load()
  }, [autoLoad, load])

  const handleSave = async () => {
    setSaving(true)
    onSavingChange?.(true)
    try {
      const res = await fetch('/api/settings/work-config', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          rules,
          work_context: workContext,
          terms,
          extra: {},
        }),
      })
      const ct = res.headers.get('content-type') || ''
      if (!ct.includes('application/json')) {
        throw new Error('后端未返回 JSON，请确认后端已启动')
      }
      const json = await res.json()
      if (!json.success) throw new Error(json.detail || '保存失败')
      toast?.success?.('工作配置已保存')
      onSaveSuccess?.()
    } catch (e) {
      toast?.error?.(e.message || '保存失败')
    } finally {
      setSaving(false)
      onSavingChange?.(false)
    }
  }

  useImperativeHandle(ref, () => ({
    save: handleSave,
    load,
  }), [handleSave, load])

  const addRule = () => setRules((prev) => [...prev, ''])
  const removeRule = (i) => setRules((prev) => prev.filter((_, idx) => idx !== i))
  const updateRule = (i, v) =>
    setRules((prev) => {
      const next = [...prev]
      next[i] = v
      return next
    })

  const addTerm = () => setTerms((prev) => [...prev, ''])
  const removeTerm = (i) => setTerms((prev) => prev.filter((_, idx) => idx !== i))
  const updateTerm = (i, v) =>
    setTerms((prev) => {
      const next = [...prev]
      next[i] = v
      return next
    })

  if (loading) {
    return (
      <div className={className}>
        <p className="text-muted text-xs">加载中…</p>
      </div>
    )
  }

  return (
    <div className={`space-y-6 ${className}`}>
      {error && (
        <p className="text-xs text-red-400">获取工作配置失败：{error}</p>
      )}
      {showConfigPath && configPath && (
        <p className="text-xs text-muted">
          配置文件：<code className="break-all">{configPath}</code>
        </p>
      )}

      <section className="space-y-2">
        <h3 className={LABEL_CLASS}>工作规则</h3>
        <p className="text-[11px] text-muted mb-1.5">
          必须遵守的规范，如：安全红线、合规要求、评审标准
        </p>
        <ul className="space-y-2.5">
          {rules.map((r, i) => (
            <li key={i} className="flex gap-2 items-center">
              <input
                type="text"
                value={r}
                onChange={(e) => updateRule(i, e.target.value)}
                placeholder={`规则 ${i + 1}`}
                className={`${INPUT_CLASS} flex-1 min-w-0`}
              />
              <button
                type="button"
                onClick={() => removeRule(i)}
                className="px-2 py-1 text-xs rounded border border-border text-muted hover:bg-white/10 shrink-0"
                title="删除"
              >
                删除
              </button>
            </li>
          ))}
        </ul>
        <button
          type="button"
          onClick={addRule}
          className="mt-1.5 px-2.5 py-1 text-xs rounded border border-border text-muted hover:bg-white/10"
        >
          + 添加规则
        </button>
      </section>

      <section className="space-y-2">
        <h3 className={LABEL_CLASS}>工作上下文</h3>
        <p className="text-[11px] text-muted mb-1.5">
          当前项目/任务、目标、时间线，便于助手了解工作内容
        </p>
        <textarea
          value={workContext}
          onChange={(e) => setWorkContext(e.target.value)}
          placeholder="例如：当前负责 XX 项目的架构设计，目标 Q2 完成技术选型，团队 5 人，使用敏捷开发。"
          rows={5}
          className={TEXTAREA_CLASS}
        />
      </section>

      <section className="space-y-2">
        <h3 className={LABEL_CLASS}>术语表</h3>
        <p className="text-[11px] text-muted mb-1.5">
          团队/公司专用术语、缩写，保证表述一致
        </p>
        <ul className="space-y-2.5">
          {terms.map((t, i) => (
            <li key={i} className="flex gap-2 items-center">
              <input
                type="text"
                value={t}
                onChange={(e) => updateTerm(i, e.target.value)}
                placeholder={`术语 ${i + 1}`}
                className={`${INPUT_CLASS} flex-1 min-w-0`}
              />
              <button
                type="button"
                onClick={() => removeTerm(i)}
                className="px-2 py-1 text-xs rounded border border-border text-muted hover:bg-white/10 shrink-0"
                title="删除"
              >
                删除
              </button>
            </li>
          ))}
        </ul>
        <button
          type="button"
          onClick={addTerm}
          className="mt-1.5 px-2.5 py-1 text-xs rounded border border-border text-muted hover:bg-white/10"
        >
          + 添加术语
        </button>
      </section>

      {showSaveButton && (
        <div className="pt-1">
          <button
            type="button"
            onClick={handleSave}
            disabled={saving}
            className="px-3 py-1.5 rounded bg-accent text-white text-xs font-medium hover:bg-accent/90 disabled:opacity-50"
          >
            {saving ? '保存中…' : '保存'}
          </button>
        </div>
      )}
    </div>
  )
})

export default WorkConfigForm

/**
 * 写作画像表单组件：用户喜好、表述习惯、范文。
 * 可在设置页或写作助手等页面内嵌使用。
 *
 * @param {Object} props
 * @param {React.Ref} [props.ref] - 可透传 ref，通过 ref.current.save() / ref.current.load() 调用
 * @param {string} [props.className] - 容器额外 class
 * @param {boolean} [props.showProfilePath=true] - 是否显示配置文件路径
 * @param {boolean} [props.showSaveButton=true] - 是否显示保存按钮
 * @param {function} [props.onSaveSuccess] - 保存成功回调
 * @param {function} [props.onSavingChange] - 保存中状态变化 (saving: boolean) => void，供父组件同步 header 按钮等
 * @param {function} [props.onLoad] - 加载完成后回调 (profile) => void
 * @param {boolean} [props.autoLoad=true] - 是否自动加载
 */
import { useEffect, useState, useCallback, forwardRef, useImperativeHandle } from 'react'
import { useToast } from './ToastModal'

const INPUT_CLASS =
  'w-full min-h-[2.25rem] px-2.5 py-1.5 rounded-md border border-border bg-surface text-fg text-base placeholder:text-muted focus:outline-none focus:ring-1 focus:ring-accent leading-normal font-sans'
const TEXTAREA_CLASS =
  'w-full min-h-[6rem] px-2.5 py-1.5 rounded-md border border-border bg-surface text-fg text-base placeholder:text-muted focus:outline-none focus:ring-1 focus:ring-accent resize-y leading-relaxed font-sans'
const LABEL_CLASS = 'block text-xs font-medium text-fg mb-1'

const WritingProfileForm = forwardRef(function WritingProfileForm({
  className = '',
  showProfilePath = true,
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
  const [profilePath, setProfilePath] = useState('')
  const [preferences, setPreferences] = useState([])
  const [styleNotes, setStyleNotes] = useState('')
  const [sampleArticles, setSampleArticles] = useState([])

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch('/api/settings/writing-profile')
      const ct = res.headers.get('content-type') || ''
      if (!ct.includes('application/json')) {
        throw new Error(
          '后端未返回 JSON，可能未启动或 API 不可用。请确认已执行 make start 或后端在配置端口运行。'
        )
      }
      const json = await res.json()
      if (!json.success) throw new Error(json.detail || '获取写作画像失败')
      setProfilePath(json.profile_path || '')
      const p = json.profile || {}
      setPreferences(p.preferences || [])
      setStyleNotes(p.style_notes || '')
      setSampleArticles(p.sample_articles || [])
      onLoad?.(json.profile)
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
      const res = await fetch('/api/settings/writing-profile', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          preferences,
          style_notes: styleNotes,
          sample_articles: sampleArticles,
          extra: {},
        }),
      })
      const ct = res.headers.get('content-type') || ''
      if (!ct.includes('application/json')) {
        throw new Error('后端未返回 JSON，请确认后端已启动')
      }
      const json = await res.json()
      if (!json.success) throw new Error(json.detail || '保存失败')
      toast?.success?.('写作画像已保存')
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

  const addPreference = () => setPreferences((prev) => [...prev, ''])
  const removePreference = (i) => setPreferences((prev) => prev.filter((_, idx) => idx !== i))
  const updatePreference = (i, v) =>
    setPreferences((prev) => {
      const next = [...prev]
      next[i] = v
      return next
    })

  const addSampleArticle = () =>
    setSampleArticles((prev) => [...prev, { title: '', content: '', path: '' }])
  const removeSampleArticle = (i) =>
    setSampleArticles((prev) => prev.filter((_, idx) => idx !== i))
  const updateSampleArticle = (i, field, value) =>
    setSampleArticles((prev) => {
      const next = prev.map((s, idx) =>
        idx === i ? { ...s, [field]: value } : s
      )
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
        <p className="text-xs text-red-400">获取写作画像失败：{error}</p>
      )}
      {showProfilePath && profilePath && (
        <p className="text-xs text-muted">
          配置文件：<code className="break-all">{profilePath}</code>
        </p>
      )}

      <section className="space-y-2">
        <h3 className={LABEL_CLASS}>用户喜好</h3>
        <p className="text-[11px] text-muted mb-1.5">
          每条一句话，如：少用「的」、偏好短句、技术文要贴代码
        </p>
        <ul className="space-y-2.5">
          {preferences.map((p, i) => (
            <li key={i} className="flex gap-2 items-center">
              <input
                type="text"
                value={p}
                onChange={(e) => updatePreference(i, e.target.value)}
                placeholder={`喜好 ${i + 1}`}
                className={`${INPUT_CLASS} flex-1 min-w-0`}
              />
              <button
                type="button"
                onClick={() => removePreference(i)}
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
          onClick={addPreference}
          className="mt-1.5 px-2.5 py-1 text-xs rounded border border-border text-muted hover:bg-white/10"
        >
          + 添加喜好
        </button>
      </section>

      <section className="space-y-2">
        <h3 className={LABEL_CLASS}>表述习惯</h3>
        <p className="text-[11px] text-muted mb-1.5">
          一段文字描述你平时的语气、用词、结构习惯
        </p>
        <textarea
          value={styleNotes}
          onChange={(e) => setStyleNotes(e.target.value)}
          placeholder="例如：习惯用口语化但不随便的表述；专业术语第一次出现时用括号略作解释；结论要给出可操作建议。"
          rows={5}
          className={TEXTAREA_CLASS}
        />
      </section>

      <section className="space-y-2">
        <h3 className={LABEL_CLASS}>范文参考</h3>
        <p className="text-[11px] text-muted mb-1.5">
          你过去写过的文章，Agent 会模仿其风格与表述。可填正文或本地文件路径（支持 ~）
        </p>
        <ul className="space-y-4">
          {sampleArticles.map((s, i) => (
            <li
              key={i}
              className="p-3 rounded-lg border border-border bg-white/[0.03] space-y-2.5"
            >
              <div className="flex gap-2">
                <input
                  type="text"
                  value={s.title}
                  onChange={(e) =>
                    updateSampleArticle(i, 'title', e.target.value)
                  }
                  placeholder="范文标题"
                  className={`${INPUT_CLASS} flex-1`}
                />
                <button
                  type="button"
                  onClick={() => removeSampleArticle(i)}
                  className="px-2 py-1 text-xs rounded border border-border text-muted hover:bg-white/10 shrink-0"
                  title="删除"
                >
                  删除
                </button>
              </div>
              <div>
                <label className="text-[11px] text-muted mb-1 block">
                  正文（直接粘贴）或 文件路径（如 ~/path/to/article.md）
                </label>
                <textarea
                  value={s.content || ''}
                  onChange={(e) =>
                    updateSampleArticle(i, 'content', e.target.value)
                  }
                  placeholder="正文内容，或留空并在下方填路径"
                  rows={4}
                  className={TEXTAREA_CLASS}
                />
                <input
                  type="text"
                  value={s.path || ''}
                  onChange={(e) =>
                    updateSampleArticle(i, 'path', e.target.value)
                  }
                  placeholder="或：本地文件路径，如 ~/docs/sample.md"
                  className={`${INPUT_CLASS} mt-2`}
                />
              </div>
            </li>
          ))}
        </ul>
        <button
          type="button"
          onClick={addSampleArticle}
          className="mt-1.5 px-2.5 py-1 text-xs rounded border border-border text-muted hover:bg-white/10"
        >
          + 添加范文
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

export default WritingProfileForm

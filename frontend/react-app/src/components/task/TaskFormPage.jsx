/**
 * 任务创建页面布局：标题、描述、schema 驱动的表单、提交、结果展示
 * 与 TaskManagement 的 CreateTaskModal 表单逻辑保持一致
 */
import { useState, useEffect } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { useToast } from '../ToastModal'
import TaskMetadataFormFields from './TaskMetadataFormFields'
import WikiTitlePreviewHint from './WikiTitlePreviewHint'
import { getDefaultMetadata, getApiErrorMessage, getDateCategoryStrings } from './taskFormUtils'
import { prepareMetadataForSubmitAsync } from '../../utils/mdToHtml'
import { requestCookiesFromExtension } from '../../utils/extensionCookies'

const INPUT_FILE_TASKS = ['speech_to_text', 'video_extract_audio']
const INPUT_FILE_ACCEPT = {
  speech_to_text: '.mp3,.wav,.m4a,.flac,.ogg,.webm,audio/*',
  video_extract_audio: '.mp4,.mkv,.avi,.mov,.webm,video/*',
}

const TASK_API = {
  list: (params) => {
    const q = new URLSearchParams({ limit: 100, offset: 0 })
    if (params?.status) q.set('status', params.status)
    return fetch(`/api/task-queue/tasks?${q}`).then(r => r.json())
  },
}

export default function TaskFormPage({ taskType, title, description, submitLabel = '提交任务', rightContent, topContent, onTaskCreated }) {
  const toast = useToast()
  const [taskTypes, setTaskTypes] = useState([])
  const [metadata, setMetadata] = useState({})
  const [submitting, setSubmitting] = useState(false)
  const [result, setResult] = useState(null)
  const location = useLocation()
  const [inputSource, setInputSource] = useState('manual')
  const [completedTasks, setCompletedTasks] = useState([])
  const [linkableUpstreams, setLinkableUpstreams] = useState({ linkable_task_types: [], suggested_bindings: {} })
  const [dependsOnTaskId, setDependsOnTaskId] = useState('')
  const [inputBindings, setInputBindings] = useState({})

  const typeInfo = taskTypes.find(t => t.type === taskType) || null
  const schema = typeInfo?.metadata_schema || {}
  const isInputFileTask = INPUT_FILE_TASKS.includes(taskType)
  const inputFileAccept = INPUT_FILE_ACCEPT[taskType] || '*'
  const fileUploadFields = taskType === 'pdf_to_wiki' ? { file_path: '.pdf,application/pdf' } : null
  const supportsUpstream = isInputFileTask

  useEffect(() => {
    fetch('/api/task-queue/task-types')
      .then(r => r.json())
      .then(d => {
        const types = d.task_types || []
        setTaskTypes(types)
        const info = types.find(t => t.type === taskType)
        let meta = getDefaultMetadata(info?.metadata_schema)
        if (taskType === 'url_to_wiki') {
          if (Array.isArray(meta.categories)) {
            meta = { ...meta, categories: [...meta.categories, ...getDateCategoryStrings()] }
          }
          // 默认先生成 Markdown 草稿，不直接写入 MediaWiki
          meta = { ...meta, auto_write: false }
          // 若通过 URL 携带了参数，则用于预填
          const search = new URLSearchParams(location.search)
          const urlFromQuery = (search.get('url') || search.get('source_url') || '').trim()
          const titleFromQuery = (search.get('wiki_title') || search.get('suggest_title') || '').trim()
          if (urlFromQuery) {
            meta = { ...meta, url: urlFromQuery }
          }
          if (titleFromQuery) {
            meta = { ...meta, wiki_title: titleFromQuery }
          }
        }
        setMetadata(meta)
        setInputSource('manual')
        setDependsOnTaskId('')
        setInputBindings({})
      })
      .catch(() => setTaskTypes([]))
  }, [taskType, location.search])

  useEffect(() => {
    if (!supportsUpstream || !taskType) return
    fetch(`/api/task-queue/task-types/${encodeURIComponent(taskType)}/linkable-upstreams`)
      .then(r => r.json())
      .then(d => {
        if (d.success && d.linkable_task_types) {
          setLinkableUpstreams({ linkable_task_types: d.linkable_task_types || [], suggested_bindings: d.suggested_bindings || {} })
        } else {
          setLinkableUpstreams({ linkable_task_types: [], suggested_bindings: {} })
        }
      })
      .catch(() => setLinkableUpstreams({ linkable_task_types: [], suggested_bindings: {} }))
  }, [taskType, supportsUpstream])

  useEffect(() => {
    if (inputSource !== 'from_task') return
    TASK_API.list({ status: 'completed' })
      .then(d => { if (d.success && d.tasks) setCompletedTasks(d.tasks); else setCompletedTasks([]) })
      .catch(() => setCompletedTasks([]))
  }, [inputSource])

  const tasksForUpstream = linkableUpstreams.linkable_task_types?.length > 0
    ? completedTasks.filter(t => linkableUpstreams.linkable_task_types.includes(t.task_type))
    : completedTasks

  const onDependsOnTaskChange = (taskId) => {
    setDependsOnTaskId(taskId)
    if (!taskId) { setInputBindings({}); return }
    const selected = completedTasks.find(t => t.task_id === taskId)
    if (!selected?.task_type) return
    const suggested = linkableUpstreams.suggested_bindings?.[selected.task_type]
    if (Array.isArray(suggested) && suggested.length) {
      const next = {}
      suggested.forEach(({ downstream_field, upstream_path }) => { if (downstream_field && upstream_path) next[downstream_field] = upstream_path })
      setInputBindings(next)
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (inputSource === 'from_task') {
      if (!dependsOnTaskId?.trim()) {
        toast.warning('请选择要依赖的已完成任务')
        return
      }
    } else {
      for (const [key, spec] of Object.entries(schema)) {
        if (spec?.required) {
          const v = metadata[key]
          if (v === undefined || v === null || (typeof v === 'string' && !v.trim())) {
            toast.warning(`请填写必填项: ${spec.description || key}`)
            return
          }
        }
      }
    }
    setSubmitting(true)
    setResult(null)
    try {
      let meta = { ...metadata }
      if (taskType === 'video_download' && metadata.cookies_from_extension) {
        const url = (metadata.url || '').trim().toLowerCase()
        const domain = url.includes('youtube.com') || url.includes('youtu.be') ? 'youtube.com'
          : url.includes('bilibili.com') || url.includes('b23.tv') ? 'bilibili.com'
          : 'youtube.com'
        const res = await requestCookiesFromExtension(domain)
        if (res.success && res.content) {
          meta = { ...meta, cookies_content: res.content }
        } else {
          toast.warning(res.error || '未能从扩展获取 cookies')
          setSubmitting(false)
          return
        }
        delete meta.cookies_from_extension
      }
      const prepared = await prepareMetadataForSubmitAsync(taskType, meta)
      const payload = { task_type: taskType, metadata: prepared }
      if (inputSource === 'from_task' && dependsOnTaskId?.trim()) {
        payload.depends_on_task_id = dependsOnTaskId.trim()
        const bindings = {}
        Object.entries(inputBindings || {}).forEach(([k, v]) => { if (v && String(v).trim()) bindings[k] = String(v).trim() })
        if (Object.keys(bindings).length) payload.input_bindings = bindings
      }
      const res = await fetch('/api/task-queue/tasks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      const data = await res.json()
      if (data.success) {
        setResult({ taskId: data.task_id, success: true })
        onTaskCreated?.()
      } else {
        throw new Error(getApiErrorMessage(data))
      }
    } catch (err) {
      setResult({ error: err.message, success: false })
    }
    setSubmitting(false)
  }

  return (
    <div className="flex flex-col h-full">
      <header className="shrink-0 px-6 py-4 border-b border-border">
        <h1 className="text-xl font-semibold text-white">{title}</h1>
      </header>

      <div className={`flex-1 overflow-hidden flex ${rightContent ? 'flex-row' : 'flex-col'}`}>
        <div className={`flex-1 overflow-y-auto p-6 ${rightContent ? 'max-w-2xl shrink-0' : 'max-w-2xl'}`}>
        {topContent}
        <p className="text-muted mb-6">
          {description}
          <Link to="/tasks" className="text-accent hover:underline ml-1">任务管理</Link>
          中查看进度。
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          {supportsUpstream && (
            <div>
              <label className="block text-sm text-muted mb-2">输入来源</label>
              <div className="flex gap-4">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    name="inputSource"
                    checked={inputSource === 'manual'}
                    onChange={() => { setInputSource('manual'); setDependsOnTaskId(''); setInputBindings({}) }}
                    className="text-accent focus:ring-accent"
                  />
                  <span className="text-white">手动填写 / 上传</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    name="inputSource"
                    checked={inputSource === 'from_task'}
                    onChange={() => setInputSource('from_task')}
                    className="text-accent focus:ring-accent"
                  />
                  <span className="text-white">来自已有任务</span>
                </label>
              </div>
              {inputSource === 'from_task' && (
                <div className="mt-3 p-3 bg-white/5 border border-border rounded-lg space-y-3">
                  <div>
                    <label className="block text-xs text-muted mb-1">
                      选择已完成任务
                      {linkableUpstreams.linkable_task_types?.length > 0 && (
                        <span className="ml-2 text-cyan-400/90">（仅显示可链接类型）</span>
                      )}
                    </label>
                    <select
                      value={dependsOnTaskId}
                      onChange={e => onDependsOnTaskChange(e.target.value)}
                      className="w-full px-3 py-2 bg-white/5 border border-border rounded-lg text-white focus:border-accent focus:outline-none text-sm"
                    >
                      <option value="">请选择</option>
                      {tasksForUpstream.map(t => (
                        <option key={t.task_id} value={t.task_id}>
                          {t.task_name || t.task_id?.slice(0, 8)} · {t.task_type} · {t.result_summary ? t.result_summary.slice(0, 30) + '…' : ''}
                        </option>
                      ))}
                    </select>
                  </div>
                  {dependsOnTaskId && Object.keys(inputBindings).length > 0 && (
                    <div className="text-xs text-muted">
                      字段映射：{Object.entries(inputBindings).map(([k, v]) => `${k} ← ${v}`).join(', ')}
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
          <TaskMetadataFormFields
            schema={schema}
            metadata={metadata}
            setMetadata={setMetadata}
            fieldIdPrefix={`${taskType}-page`}
            isInputFileTask={isInputFileTask}
            inputFileAccept={inputFileAccept}
            fileUploadFields={fileUploadFields}
            fieldsToHide={[
              ...(inputSource === 'from_task' ? ['input_file'] : []),
              ...(taskType === 'url_to_wiki' && !metadata?.translate ? ['language'] : []),
            ]}
          />
          {taskType === 'video_download' && (
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={!!metadata.cookies_from_extension}
                onChange={e => setMetadata(m => ({ ...m, cookies_from_extension: e.target.checked }))}
                className="text-accent focus:ring-accent rounded"
              />
              <span className="text-sm text-muted">使用扩展获取 cookies（YouTube/Bilibili 需登录时勾选，需安装 Hou CLI 扩展）</span>
            </label>
          )}
          {taskType === 'mediawiki_write' && (
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={!!metadata._contentIsMarkdown}
                onChange={e => setMetadata(m => ({ ...m, _contentIsMarkdown: e.target.checked }))}
                className="text-accent focus:ring-accent rounded"
              />
              <span className="text-sm text-muted">正文为 Markdown（提交时转为 Wiki 语法）</span>
            </label>
          )}
          {taskType === 'url_to_wiki' && (
            <p className="text-xs text-amber-400/90">下方分类即写入 Wiki 的标签，可添加、可删除；默认含网文抓取、hou-cli。</p>
          )}
          {(taskType === 'pdf_to_wiki' || taskType === 'url_to_wiki') && (
            <WikiTitlePreviewHint taskType={taskType} metadata={metadata} />
          )}
          <button
            type="submit"
            disabled={submitting}
            className="px-4 py-2 bg-accent hover:bg-accent-hover text-white rounded-lg font-medium disabled:opacity-50 transition-colors"
          >
            {submitting ? '提交中...' : submitLabel}
          </button>
        </form>

        {result && (
          <div className={`mt-6 p-4 rounded-lg ${result.success ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400'}`}>
            {result.success ? (
              <p>
                任务已创建：<Link to="/tasks" className="underline">{result.taskId}</Link>
                ，请在任务管理中查看结果。
              </p>
            ) : (
              <p>失败：{result.error}</p>
            )}
          </div>
        )}
        </div>
        {rightContent && (
          <div className="min-w-0 flex-1 border-l border-border overflow-y-auto bg-white/[0.02]">
            {rightContent}
          </div>
        )}
      </div>
    </div>
  )
}

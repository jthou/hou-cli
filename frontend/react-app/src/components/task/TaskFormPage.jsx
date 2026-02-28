/**
 * 任务创建页面布局：标题、描述、schema 驱动的表单、提交、结果展示
 * 与 TaskManagement 的 CreateTaskModal 表单逻辑保持一致
 */
import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useToast } from '../ToastModal'
import TaskMetadataFormFields from './TaskMetadataFormFields'
import { getDefaultMetadata, getApiErrorMessage } from './taskFormUtils'
import { prepareMetadataForSubmitAsync } from '../../utils/mdToHtml'

const INPUT_FILE_TASKS = ['speech_to_text', 'video_extract_audio']
const INPUT_FILE_ACCEPT = {
  speech_to_text: '.mp3,.wav,.m4a,.flac,.ogg,.webm,audio/*',
  video_extract_audio: '.mp4,.mkv,.avi,.mov,.webm,video/*',
}

export default function TaskFormPage({ taskType, title, description, submitLabel = '提交任务' }) {
  const toast = useToast()
  const [taskTypes, setTaskTypes] = useState([])
  const [metadata, setMetadata] = useState({})
  const [submitting, setSubmitting] = useState(false)
  const [result, setResult] = useState(null)

  const typeInfo = taskTypes.find(t => t.type === taskType) || null
  const schema = typeInfo?.metadata_schema || {}
  const isInputFileTask = INPUT_FILE_TASKS.includes(taskType)
  const inputFileAccept = INPUT_FILE_ACCEPT[taskType] || '*'

  useEffect(() => {
    fetch('/api/task-queue/task-types')
      .then(r => r.json())
      .then(d => {
        const types = d.task_types || []
        setTaskTypes(types)
        const info = types.find(t => t.type === taskType)
        setMetadata(getDefaultMetadata(info?.metadata_schema))
      })
      .catch(() => setTaskTypes([]))
  }, [taskType])

  const handleSubmit = async (e) => {
    e.preventDefault()
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
    setResult(null)
    try {
      const meta = await prepareMetadataForSubmitAsync(taskType, metadata)
      const res = await fetch('/api/task-queue/tasks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task_type: taskType, metadata: meta }),
      })
      const data = await res.json()
      if (data.success) {
        setResult({ taskId: data.task_id, success: true })
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

      <div className="flex-1 overflow-y-auto p-6 max-w-2xl">
        <p className="text-[#94a3b8] mb-6">
          {description}
          <Link to="/" className="text-accent hover:underline ml-1">任务管理</Link>
          中查看进度。
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <TaskMetadataFormFields
            schema={schema}
            metadata={metadata}
            setMetadata={setMetadata}
            fieldIdPrefix={`${taskType}-page`}
            isInputFileTask={isInputFileTask}
            inputFileAccept={inputFileAccept}
          />
          {taskType === 'mediawiki_write' && (
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={!!metadata._contentIsMarkdown}
                onChange={e => setMetadata(m => ({ ...m, _contentIsMarkdown: e.target.checked }))}
                className="text-accent focus:ring-accent rounded"
              />
              <span className="text-sm text-[#94a3b8]">正文为 Markdown（提交时转为 Wiki 语法）</span>
            </label>
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
                任务已创建：<Link to="/" className="underline">{result.taskId}</Link>
                ，请在任务管理中查看结果。
              </p>
            ) : (
              <p>失败：{result.error}</p>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

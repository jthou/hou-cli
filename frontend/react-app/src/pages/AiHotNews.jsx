/**
 * 今日 AI 热点：阅读工具内直跑（不入任务队列）。
 * 时间：2026-04-04；理由：产品要求点击即执行、不写入任务列表；方法：POST /api/ai-hot-news/run + 复用 TaskResultDisplay
 */
import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import PageHeader from '../components/PageHeader'
import TaskMetadataFormFields from '../components/task/TaskMetadataFormFields'
import TaskResultDisplay from '../components/TaskResultDisplay'
import { useToast } from '../components/ToastModal'
import { getDefaultMetadata, getApiErrorMessage } from '../components/task/taskFormUtils'
import { prepareMetadataForSubmitAsync } from '../utils/mdToHtml'

const TASK_TYPE = 'ai_hot_news_digest'
/** 多轮检索 + LLM，可能超过默认 fetch；显式长超时（秒） */
const RUN_TIMEOUT_MS = 900_000

export default function AiHotNews() {
  const toast = useToast()
  const [taskTypes, setTaskTypes] = useState([])
  const [metadata, setMetadata] = useState({})
  const [running, setRunning] = useState(false)
  const [displayResult, setDisplayResult] = useState(null)

  const typeInfo = taskTypes.find((t) => t.type === TASK_TYPE) || null
  const schema = typeInfo?.metadata_schema || {}

  useEffect(() => {
    fetch('/api/task-queue/task-types')
      .then((r) => r.json())
      .then((d) => {
        const types = d.task_types || []
        setTaskTypes(types)
        const info = types.find((t) => t.type === TASK_TYPE)
        setMetadata(getDefaultMetadata(info?.metadata_schema))
      })
      .catch(() => setTaskTypes([]))
  }, [])

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
    setRunning(true)
    setDisplayResult(null)
    const controller = new AbortController()
    const t = setTimeout(() => controller.abort(), RUN_TIMEOUT_MS)
    try {
      const prepared = await prepareMetadataForSubmitAsync(TASK_TYPE, { ...metadata })
      const res = await fetch('/api/ai-hot-news/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ metadata: prepared }),
        signal: controller.signal,
      })
      const data = await res.json()
      if (!res.ok) {
        throw new Error(data?.detail || getApiErrorMessage(data) || res.statusText)
      }
      if (!data.success || !data.result) {
        throw new Error(getApiErrorMessage(data) || '执行失败')
      }
      setDisplayResult(data.result)
      toast.success('摘要已生成')
    } catch (err) {
      const msg = err?.name === 'AbortError' ? '请求超时，请稍后重试或检查网络' : err?.message || '执行失败'
      toast.error(msg)
      setDisplayResult({
        status: 'error',
        summary: '执行失败',
        error: { code: 'RUN_FAILED', message: msg },
      })
    } finally {
      clearTimeout(t)
      setRunning(false)
    }
  }

  return (
    <div className="flex flex-col h-full">
      <PageHeader title="今日 AI 热点" />
      <div className="flex-1 overflow-y-auto p-6 max-w-4xl mx-auto w-full space-y-6">
        <div className="p-3 bg-white/5 border border-border rounded-lg text-sm text-muted space-y-2">
          <p>
            由后台在当前请求内执行多轮网页检索（AI 资讯 / 模型发布 / 融资 / 监管 / 中文大模型等），再调用 LLM 生成中文深度摘要。配置{' '}
            <code className="text-cyan-300/90">TAVILY_API_KEY</code> 时优先 Tavily，否则使用 DuckDuckGo。
          </p>
          <p>
            <strong className="text-fg/90">本页不创建任务队列条目</strong>：点击「生成热点摘要」后在此页等待结果。与 Cursor Skill{' '}
            <code className="text-cyan-300/90">ai-hot-news-summary</code> 口径一致。
          </p>
          <p>
            生成后点「去写作助手（热点摘要→参考）」可将摘要写入写作会话参考块（与 MCP{' '}
            <code className="text-cyan-300/90">hot_news_digest_markdown</code> 路径一致）。
          </p>
          <p className="text-xs text-muted/80">
            若仍需异步排队、在任务中心追踪进度，可到{' '}
            <Link to="/tasks" className="text-accent hover:underline">
              任务中心
            </Link>{' '}
            手动创建类型 <code className="text-cyan-300/80">ai_hot_news_digest</code> 的任务。
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <TaskMetadataFormFields
            schema={schema}
            metadata={metadata}
            setMetadata={setMetadata}
            fieldIdPrefix="ai-hot-news-page"
            isInputFileTask={false}
          />
          <button
            type="submit"
            disabled={running || !typeInfo}
            className="px-4 py-2 bg-accent hover:bg-accent-hover text-white rounded-lg font-medium disabled:opacity-50 transition-colors"
          >
            {running ? '正在生成（请耐心等待）…' : '生成热点摘要'}
          </button>
        </form>

        {displayResult && (
          <div className="rounded-xl border border-border bg-surface/50 p-4">
            <h2 className="text-sm font-semibold text-white mb-3">生成结果</h2>
            <TaskResultDisplay taskType={TASK_TYPE} result={displayResult} taskId={null} />
          </div>
        )}
      </div>
    </div>
  )
}

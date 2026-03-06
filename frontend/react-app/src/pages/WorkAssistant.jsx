/**
 * 工作助手 - 通用对话入口，支持模型选择（具体模型名）、会话持久化
 */
import { useState, useRef, useEffect, useCallback } from 'react'
import PageHeader from '../components/PageHeader'
import ChatInput from '../components/ChatInput'
import MarkdownPreview from '../components/MarkdownPreview'
import { useSelectableModels } from '../hooks/useSelectableModels'

const SESSION_TYPE = 'work_assistant'
const STORAGE_KEY = 'work_assistant_selected_session'

export default function WorkAssistant() {
  const [sessions, setSessions] = useState([])
  const [sessionsLoading, setSessionsLoading] = useState(false)
  const [selectedSessionId, setSelectedSessionId] = useState(() => {
    try {
      return sessionStorage.getItem(STORAGE_KEY) || null
    } catch {
      return null
    }
  })
  const [messages, setMessages] = useState([])
  const [detailLoading, setDetailLoading] = useState(false)
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [streamingContent, setStreamingContent] = useState('')
  const [streamingToolCalls, setStreamingToolCalls] = useState([])
  const [selectedModel, setSelectedModel] = useState('auto')
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const { models: selectableModels } = useSelectableModels()
  const messagesEndRef = useRef(null)
  const abortControllerRef = useRef(null)
  const streamingContentRef = useRef('')

  const loadSessions = useCallback(() => {
    setSessionsLoading(true)
    fetch(`/api/sessions/list?type=${encodeURIComponent(SESSION_TYPE)}&limit=50`)
      .then((r) => r.json())
      .then((d) => {
        if (d.sessions) setSessions(d.sessions)
      })
      .catch(() => {})
      .finally(() => setSessionsLoading(false))
  }, [])

  useEffect(() => {
    loadSessions()
  }, [loadSessions])

  useEffect(() => {
    if (sessions.length === 0) {
      setSelectedSessionId(null)
      return
    }
    const ids = new Set(sessions.map((s) => s.session_id))
    if (!selectedSessionId || !ids.has(selectedSessionId)) {
      const first = sessions[0]?.session_id
      if (first) {
        setSelectedSessionId(first)
        try {
          sessionStorage.setItem(STORAGE_KEY, first)
        } catch (_) {}
      }
    }
  }, [sessions, selectedSessionId])

  useEffect(() => {
    try {
      if (selectedSessionId) {
        sessionStorage.setItem(STORAGE_KEY, selectedSessionId)
      } else {
        sessionStorage.removeItem(STORAGE_KEY)
      }
    } catch (_) {}
  }, [selectedSessionId])

  useEffect(() => {
    if (!selectedSessionId) {
      setMessages([])
      setDetailLoading(false)
      return
    }
    setDetailLoading(true)
    setMessages([])
    fetch(`/api/sessions/${encodeURIComponent(selectedSessionId)}`)
      .then((r) => r.json())
      .then((d) => {
        if (d.success && Array.isArray(d.messages)) {
          setMessages(d.messages.map((m) => ({ role: m.role, content: m.content })))
        }
      })
      .catch(() => {})
      .finally(() => setDetailLoading(false))
  }, [selectedSessionId])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streamingContent])

  const handleNewSession = () => {
    fetch('/api/sessions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ metadata: { type: SESSION_TYPE } }),
    })
      .then((r) => r.json())
      .then((d) => {
        if (d.success && d.session_id) {
          loadSessions()
          setSelectedSessionId(d.session_id)
        }
      })
      .catch(() => {})
  }

  const handleStop = () => {
    abortControllerRef.current?.abort()
  }

  const handleSubmit = async (e) => {
    e?.preventDefault?.()
    const text = (input || '').trim()
    if (!text) return

    let sessionId = selectedSessionId
    if (!sessionId) {
      const createRes = await fetch('/api/sessions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ metadata: { type: SESSION_TYPE } }),
      }).then((r) => r.json())
      if (!createRes.success || !createRes.session_id) return
      sessionId = createRes.session_id
      setSelectedSessionId(sessionId)
      loadSessions()
    }

    setInput('')
    setMessages((prev) => [...prev, { role: 'user', content: text }])
    setStreamingContent('')
    setStreamingToolCalls([])
    setLoading(true)
    const isFirstMessage = messages.length === 0
    const ac = new AbortController()
    abortControllerRef.current = ac

    try {
      const res = await fetch('/api/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: text,
          session_id: sessionId,
          context_type: SESSION_TYPE,
          ...(selectedModel !== 'auto' ? { model: selectedModel } : {}),
        }),
        signal: ac.signal,
      })
      if (!res.ok) {
        setMessages((prev) => [...prev, { role: 'assistant', content: `错误：${res.statusText || res.status}` }])
        return
      }
      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let fullContent = ''
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const parts = buffer.split('\n\n')
        buffer = parts.pop() ?? ''
        for (const block of parts) {
          const dataLines = block.split('\n').filter((l) => l.startsWith('data: '))
          for (const dataLine of dataLines) {
            try {
              const obj = JSON.parse(dataLine.slice(6))
              if (obj.status === 'streaming' && obj.content != null) {
                const raw = String(obj.content)
                if (raw.startsWith('__DEBUG__:') || raw.startsWith('__STATUS__:')) {
                  // 忽略
                } else if (raw.startsWith('__TOOL__:')) {
                  try {
                    const toolData = JSON.parse(raw.slice(9).trim())
                    if (toolData?.name) {
                      setStreamingToolCalls((prev) => [...prev, {
                        name: toolData.name,
                        args: toolData.args || {},
                        success: toolData.success,
                        result: toolData.result,
                        error: toolData.error,
                      }])
                    }
                  } catch (_) {}
                } else {
                  fullContent += raw
                  streamingContentRef.current = fullContent
                  setStreamingContent(fullContent)
                }
              } else if (obj.status === 'done') {
                const finalContent = fullContent.trim() || '（助手未返回内容）'
                setMessages((prev) => [...prev, { role: 'assistant', content: finalContent }])
                setStreamingContent('')
                setStreamingToolCalls([])
                streamingContentRef.current = ''
                if (isFirstMessage && text) {
                  fetch(`/api/sessions/${encodeURIComponent(sessionId)}`, {
                    method: 'PATCH',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ title: text.slice(0, 30).trim() || text.slice(0, 30) }),
                  })
                    .then((r) => r.json())
                    .then((d) => { if (d.success) loadSessions() })
                    .catch(() => {})
                }
                fullContent = ''
              } else if (obj.status === 'error') {
                setMessages((prev) => [...prev, { role: 'assistant', content: `错误：${obj.error || '请求失败'}` }])
                setStreamingContent('')
                setStreamingToolCalls([])
                streamingContentRef.current = ''
                fullContent = ''
              }
            } catch (_) {}
          }
        }
      }
      if (buffer.trim()) {
        try {
          const dataLines = buffer.split('\n').filter((l) => l.startsWith('data: '))
          for (const dataLine of dataLines) {
            const obj = JSON.parse(dataLine.slice(6))
            if (obj.status === 'streaming' && obj.content != null) {
              const raw = String(obj.content)
              if (raw.startsWith('__TOOL__:')) {
                try {
                  const toolData = JSON.parse(raw.slice(9).trim())
                  if (toolData?.name) {
                    setStreamingToolCalls((prev) => [...prev, {
                      name: toolData.name,
                      args: toolData.args || {},
                      success: toolData.success,
                      result: toolData.result,
                      error: toolData.error,
                    }])
                  }
                } catch (_) {}
              } else if (!raw.startsWith('__DEBUG__:') && !raw.startsWith('__STATUS__:')) {
                fullContent += raw
                streamingContentRef.current = fullContent
                setStreamingContent(fullContent)
              }
            } else if (obj.status === 'done') {
              const finalContent = fullContent.trim() || '（助手未返回内容）'
              setMessages((prev) => [...prev, { role: 'assistant', content: finalContent }])
              if (isFirstMessage && text) {
                fetch(`/api/sessions/${encodeURIComponent(sessionId)}`, {
                  method: 'PATCH',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({ title: text.slice(0, 30).trim() || text.slice(0, 30) }),
                })
                  .then((r) => r.json())
                  .then((d) => { if (d.success) loadSessions() })
                  .catch(() => {})
              }
              setStreamingToolCalls([])
              fullContent = ''
            } else if (obj.status === 'error') {
              setMessages((prev) => [...prev, { role: 'assistant', content: `错误：${obj.error || '请求失败'}` }])
              setStreamingToolCalls([])
              fullContent = ''
            }
          }
          setStreamingContent('')
          streamingContentRef.current = ''
        } catch (_) {}
      }
    } catch (err) {
      if (err?.name === 'AbortError') return
      setMessages((prev) => [...prev, { role: 'assistant', content: `错误：${err?.message || '请求失败'}` }])
    } finally {
      setLoading(false)
      abortControllerRef.current = null
    }
  }

  return (
    <div className="flex flex-col h-full">
      <PageHeader title="工作助手" subtitle="通用对话入口，可指定具体模型" />
      <div className="flex-1 flex min-h-0 overflow-hidden">
        {/* 左侧会话列表（可收缩） */}
        <div
          className={`shrink-0 flex flex-col border-r border-border bg-surface/30 transition-[width] ${
            sidebarCollapsed ? 'w-8' : 'w-52'
          }`}
        >
          {sidebarCollapsed ? (
            <div className="flex flex-col items-center py-2">
              <button
                type="button"
                onClick={() => setSidebarCollapsed(false)}
                className="p-2 rounded text-muted hover:text-fg hover:bg-white/5"
                title="展开会话列表"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </button>
            </div>
          ) : (
            <>
              <div className="shrink-0 p-2 border-b border-border flex justify-between items-center">
                <span className="text-xs font-medium text-muted">会话</span>
                <div className="flex items-center gap-1">
                  <button
                    type="button"
                    onClick={handleNewSession}
                    className="text-xs px-2 py-1 rounded border border-border text-muted hover:text-fg hover:bg-white/5"
                  >
                    + 新建
                  </button>
                  <button
                    type="button"
                    onClick={() => setSidebarCollapsed(true)}
                    className="p-1 rounded text-muted hover:text-fg hover:bg-white/5"
                    title="收起会话列表"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                    </svg>
                  </button>
                </div>
              </div>
              <div className="flex-1 overflow-y-auto py-2">
            {sessionsLoading && (
              <div className="px-3 py-2 text-xs text-muted">加载中…</div>
            )}
            {!sessionsLoading && sessions.length === 0 && (
              <div className="px-3 py-2 text-xs text-muted">暂无会话</div>
            )}
            {!sessionsLoading &&
              sessions.map((s) => (
                <button
                  key={s.session_id}
                  type="button"
                  onClick={() => setSelectedSessionId(s.session_id)}
                  className={`w-full text-left px-3 py-2 text-xs truncate ${
                    selectedSessionId === s.session_id
                      ? 'bg-accent/20 text-accent'
                      : 'text-muted hover:bg-white/5 hover:text-fg'
                  }`}
                  title={s.title || s.preview || s.session_id}
                >
                  {s.title || s.preview || `会话 ${s.session_id?.slice(0, 8)}`}
                </button>
              ))}
              </div>
            </>
          )}
        </div>
        {/* 右侧对话区 */}
        <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {detailLoading && (
              <div className="text-center py-8 text-muted text-sm">加载会话…</div>
            )}
            {!detailLoading && messages.length === 0 && !streamingContent && (
              <div className="text-center py-12 text-muted text-sm">
                输入消息开始对话，支持智能选择或指定具体模型。
              </div>
            )}
          {messages.map((msg, i) => (
            <div
              key={i}
              className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[85%] rounded-lg px-4 py-2.5 ${
                  msg.role === 'user'
                    ? 'bg-accent/20 text-fg'
                    : 'bg-white/5 text-fg'
                }`}
              >
                {msg.role === 'user' ? (
                  <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                ) : (
                  <div className="prose prose-invert prose-sm max-w-none">
                    <MarkdownPreview markdown={msg.content} theme="dark" />
                  </div>
                )}
              </div>
            </div>
          ))}
          {streamingToolCalls.length > 0 && (
            <div className="flex justify-start w-full max-w-[85%]">
              <div className="space-y-1.5 w-full">
                {streamingToolCalls.map((tc, idx) => (
                  <div
                    key={idx}
                    className={`text-xs rounded-lg px-3 py-2 border ${
                      tc.success ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-200' : 'bg-amber-500/10 border-amber-500/30 text-amber-200'
                    }`}
                  >
                    <span className="font-medium">🔧 {tc.name}</span>
                    <span className="text-muted ml-1">{tc.success ? '→ 成功' : '→ 失败'}</span>
                    <div className="mt-1 text-muted truncate" title={
                      tc.success && tc.result != null
                        ? (typeof tc.result === 'string' ? tc.result : JSON.stringify(tc.result))
                        : tc.error || ''
                    }>
                      {tc.success && tc.result != null
                        ? (() => {
                            const r = typeof tc.result === 'string' ? tc.result : JSON.stringify(tc.result)
                            return r.length > 120 ? r.slice(0, 120) + '…' : r
                          })()
                        : tc.error || '（无结果）'}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
          {streamingContent && (
            <div className="flex justify-start">
              <div className="max-w-[85%] rounded-lg px-4 py-2.5 bg-white/5">
                <div className="prose prose-invert prose-sm max-w-none">
                  <MarkdownPreview markdown={streamingContent} theme="dark" />
                </div>
              </div>
            </div>
          )}
            <div ref={messagesEndRef} />
          </div>
          <div className="shrink-0 border-t border-border bg-surface/50">
          <div className="flex items-center gap-2 px-4 py-2">
            <label className="text-xs text-muted shrink-0">模型</label>
            <select
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              className="text-xs rounded border border-border bg-white/5 px-2 py-1.5 text-fg focus:outline-none focus:ring-1 focus:ring-accent"
            >
              {selectableModels.map((m) => (
                <option key={m.value} value={m.value}>{m.label}</option>
              ))}
            </select>
            {loading && (
              <button
                type="button"
                onClick={handleStop}
                className="text-xs px-2 py-1 rounded border border-red-500/50 text-red-400 hover:bg-red-500/10"
              >
                停止
              </button>
            )}
          </div>
          <ChatInput
            value={input}
            onChange={setInput}
            onSubmit={handleSubmit}
            placeholder="输入消息，Enter 换行，Ctrl+Enter 发送"
            disabled={loading || detailLoading}
            submitLabel="发送"
          />
          </div>
        </div>
      </div>
    </div>
  )
}
